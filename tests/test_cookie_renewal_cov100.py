from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.lite.cookie_renewal import CookieRenewalManager, build_cookie_loader


def _ensure_event_loop():
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _make_manager(tmp_path, **kwargs):
    _ensure_event_loop()
    defaults = {
        "api_client": MagicMock(),
        "ws_client": MagicMock(),
        "cookie_loader": lambda: "test_cookie",
        "audit_log_path": str(tmp_path / "audit.jsonl"),
        "check_interval_seconds": 30,
        "min_renew_interval_seconds": 1,
        "failure_backoff_base_seconds": 0.01,
        "failure_backoff_max_seconds": 0.05,
        "failure_jitter_seconds": 0.0,
        "risk_retry_budget": 2,
        "risk_cooldown_seconds": 0.01,
        "cookie_file_path": str(tmp_path / "cookie.txt"),
    }
    defaults.update(kwargs)
    return CookieRenewalManager(**defaults)


class TestInit:
    def test_defaults(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr._state == "idle"
        assert mgr._recover_count == 0
        assert mgr._consecutive_failures == 0

    def test_empty_cookie_file_path(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_file_path="")
        assert mgr.cookie_file_path is None


class TestStatus:
    def test_status_dict(self, tmp_path):
        mgr = _make_manager(tmp_path)
        s = mgr.status()
        assert "state" in s
        assert "recover_count" in s
        assert s["state"] == "idle"


class TestStop:
    def test_stop_sets_event(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.stop()
        assert mgr._stop.is_set()


class TestHandleAuthFailure:
    @pytest.mark.asyncio
    async def test_delegates_to_renew(self, tmp_path):
        mgr = _make_manager(tmp_path)
        with patch.object(mgr, "renew", new_callable=AsyncMock, return_value=True) as mock_renew:
            result = await mgr.handle_auth_failure("test_reason")
            assert result is True
            mock_renew.assert_called_once_with(reason="test_reason")


class TestRunForever:
    @pytest.mark.asyncio
    async def test_periodic_check_success(self, tmp_path):
        mgr = _make_manager(tmp_path, check_interval_seconds=30)
        mgr.api_client.has_login = AsyncMock(return_value=True)

        call_count = 0
        original_get = mgr._get_latest_cookie_snapshot

        async def patched_get(reason=""):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                mgr.stop()
            return None

        mgr._get_latest_cookie_snapshot = patched_get
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await mgr.run_forever()

    @pytest.mark.asyncio
    async def test_periodic_check_login_failed(self, tmp_path):
        mgr = _make_manager(tmp_path, check_interval_seconds=30)
        mgr.api_client.has_login = AsyncMock(return_value=False)

        call_count = 0

        async def patched_get(reason=""):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                mgr.stop()
            return None

        mgr._get_latest_cookie_snapshot = patched_get
        with patch.object(mgr, "renew", new_callable=AsyncMock, return_value=False):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await mgr.run_forever()

    @pytest.mark.asyncio
    async def test_periodic_check_exception(self, tmp_path):
        mgr = _make_manager(tmp_path, check_interval_seconds=30)

        call_count = 0

        async def patched_get(reason=""):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                mgr.stop()
            raise RuntimeError("check failed")

        mgr._get_latest_cookie_snapshot = patched_get
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await mgr.run_forever()
        assert mgr._state == "failed_detect"


class TestRenew:
    @pytest.mark.asyncio
    async def test_suppressed_by_min_interval(self, tmp_path):
        mgr = _make_manager(tmp_path, min_renew_interval_seconds=9999)
        mgr._last_renew_attempt_at = time.time()
        result = await mgr.renew(reason="test")
        assert result is False
        assert mgr._state == "suppressed"

    @pytest.mark.asyncio
    async def test_empty_cookie_source(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "")
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mgr.renew(reason="test")
        assert result is False
        assert mgr._state == "waiting_new_cookie"
        assert mgr._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_same_fingerprint_failure(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "same_cookie")
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        mgr.api_client.cookie_text = "same_cookie"
        mgr._last_cookie_fp = mgr._cookie_fingerprint("same_cookie")
        mgr._consecutive_failures = 1
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mgr.renew(reason="test")
        assert result is False

    @pytest.mark.asyncio
    async def test_successful_renewal(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "new_cookie")
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        mgr.api_client.cookie_text = "old_cookie"
        mgr.api_client.has_login = AsyncMock(return_value=True)
        mgr.api_client.get_token = AsyncMock()
        mgr.api_client.update_cookie = MagicMock()
        mgr.api_client.device_id = "dev1"
        mgr.api_client.user_id = "user1"
        mgr.ws_client.update_auth_context = MagicMock()
        mgr.ws_client.force_reconnect = AsyncMock()
        result = await mgr.renew(reason="test")
        assert result is True
        assert mgr._state == "recovered"
        assert mgr._recover_count == 1

    @pytest.mark.asyncio
    async def test_transient_risk_failure(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "new_cookie")
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        mgr.api_client.cookie_text = "old_cookie"
        mgr.api_client.has_login = AsyncMock(side_effect=RuntimeError("FAIL_SYS_USER_VALIDATE rgv587"))
        mgr.api_client.update_cookie = MagicMock()
        mgr.api_client.device_id = ""
        mgr.api_client.user_id = ""
        mgr.ws_client.update_cookie = MagicMock()
        mgr.ws_client.force_reconnect = AsyncMock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mgr.renew(reason="test")
        assert result is False
        assert mgr._last_risk_code == "FAIL_SYS_USER_VALIDATE"

    @pytest.mark.asyncio
    async def test_cookie_invalid_failure(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "new_cookie")
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        mgr.api_client.cookie_text = "old_cookie"
        mgr.api_client.has_login = AsyncMock(side_effect=RuntimeError("cookie_invalid"))
        mgr.api_client.update_cookie = MagicMock()
        mgr.api_client.device_id = ""
        mgr.api_client.user_id = ""
        mgr.ws_client.update_cookie = MagicMock()
        mgr.ws_client.force_reconnect = AsyncMock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mgr.renew(reason="test")
        assert result is False
        assert mgr._state == "waiting_new_cookie"

    @pytest.mark.asyncio
    async def test_unknown_failure(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "new_cookie")
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        mgr.api_client.cookie_text = "old_cookie"
        mgr.api_client.has_login = AsyncMock(side_effect=RuntimeError("network timeout"))
        mgr.api_client.update_cookie = MagicMock()
        mgr.api_client.device_id = ""
        mgr.api_client.user_id = ""
        mgr.ws_client.update_cookie = MagicMock()
        mgr.ws_client.force_reconnect = AsyncMock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mgr.renew(reason="test")
        assert result is False
        assert mgr._state == "failed_reconnect"

    @pytest.mark.asyncio
    async def test_risk_budget_exhausted(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_loader=lambda: "new_cookie", risk_retry_budget=1)
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = None
        mgr.api_client.cookie_text = "old_cookie"
        mgr.api_client.has_login = AsyncMock(side_effect=RuntimeError("FAIL_SYS_USER_VALIDATE"))
        mgr.api_client.update_cookie = MagicMock()
        mgr.api_client.device_id = ""
        mgr.api_client.user_id = ""
        mgr.ws_client.update_cookie = MagicMock()
        mgr.ws_client.force_reconnect = AsyncMock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await mgr.renew(reason="test")
        assert mgr._state == "waiting_new_cookie"


class TestValidateCandidateCookie:
    @pytest.mark.asyncio
    async def test_validate_restores_old_cookie(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.api_client.cookie_text = "old"
        mgr.api_client.has_login = AsyncMock(return_value=True)
        mgr.api_client.get_token = AsyncMock()
        mgr.api_client.update_cookie = MagicMock()
        await mgr._validate_candidate_cookie("new")
        calls = mgr.api_client.update_cookie.call_args_list
        assert calls[-1].args[0] == "old"


class TestApplyCookieAtomically:
    @pytest.mark.asyncio
    async def test_with_update_auth_context(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.api_client.device_id = "d1"
        mgr.api_client.user_id = "u1"
        mgr.ws_client.update_auth_context = MagicMock()
        mgr.ws_client.force_reconnect = AsyncMock()
        await mgr._apply_cookie_atomically("new_cookie")
        mgr.ws_client.update_auth_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_without_update_auth_context(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.ws_client = MagicMock(spec=["update_cookie", "force_reconnect"])
        mgr.ws_client.force_reconnect = AsyncMock()
        await mgr._apply_cookie_atomically("new_cookie")
        mgr.ws_client.update_cookie.assert_called_once_with("new_cookie")


class TestRollbackCookieContext:
    @pytest.mark.asyncio
    async def test_rollback_with_auth(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.ws_client.update_auth_context = MagicMock()
        await mgr._rollback_cookie_context("old", "d1", "u1")
        mgr.ws_client.update_auth_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_without_auth(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.ws_client = MagicMock(spec=["update_cookie"])
        await mgr._rollback_cookie_context("old", "d1", "u1")
        mgr.ws_client.update_cookie.assert_called_once_with("old")

    @pytest.mark.asyncio
    async def test_rollback_exception_swallowed(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.api_client.update_cookie = MagicMock(side_effect=Exception("rollback failed"))
        await mgr._rollback_cookie_context("old", "d1", "u1")


class TestGetLatestCookieSnapshot:
    @pytest.mark.asyncio
    async def test_adapter_success(self, tmp_path):
        mgr = _make_manager(tmp_path)
        snap = MagicMock()
        snap.cookie_text = "adapter_cookie"
        adapter = AsyncMock()
        adapter.get_latest_cookie = AsyncMock(return_value=snap)
        mgr.cookie_source_adapter = adapter
        result = await mgr._get_latest_cookie_snapshot(reason="test")
        assert result is snap

    @pytest.mark.asyncio
    async def test_adapter_empty_cookie(self, tmp_path):
        mgr = _make_manager(tmp_path)
        snap = MagicMock()
        snap.cookie_text = ""
        adapter = AsyncMock()
        adapter.get_latest_cookie = AsyncMock(return_value=snap)
        mgr.cookie_source_adapter = adapter
        mgr.browser_cookie_provider = None
        result = await mgr._get_latest_cookie_snapshot(reason="test")
        assert result is None

    @pytest.mark.asyncio
    async def test_adapter_exception(self, tmp_path):
        mgr = _make_manager(tmp_path)
        adapter = AsyncMock()
        adapter.get_latest_cookie = AsyncMock(side_effect=Exception("adapter err"))
        mgr.cookie_source_adapter = adapter
        mgr.browser_cookie_provider = None
        result = await mgr._get_latest_cookie_snapshot(reason="test")
        assert result is None

    @pytest.mark.asyncio
    async def test_adapter_dict_snap(self, tmp_path):
        mgr = _make_manager(tmp_path)
        adapter = AsyncMock()
        adapter.get_latest_cookie = AsyncMock(return_value={"cookie_text": "dict_cookie"})
        mgr.cookie_source_adapter = adapter
        result = await mgr._get_latest_cookie_snapshot(reason="test")
        assert result == {"cookie_text": "dict_cookie"}

    @pytest.mark.asyncio
    async def test_no_adapter_browser_provider(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.cookie_source_adapter = None
        mgr.browser_cookie_provider = AsyncMock(return_value="browser_cookie")
        result = await mgr._get_latest_cookie_snapshot(reason="test")
        assert result is not None
        assert result["cookie_text"] == "browser_cookie"


class TestTryAutoRefreshCookieSource:
    @pytest.mark.asyncio
    async def test_no_provider(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.browser_cookie_provider = None
        result = await mgr._try_auto_refresh_cookie_source(reason="test")
        assert result == ""

    @pytest.mark.asyncio
    async def test_empty_result(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.browser_cookie_provider = AsyncMock(return_value="")
        result = await mgr._try_auto_refresh_cookie_source(reason="test")
        assert result == ""

    @pytest.mark.asyncio
    async def test_success(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.browser_cookie_provider = AsyncMock(return_value="fresh_cookie")
        result = await mgr._try_auto_refresh_cookie_source(reason="test")
        assert result == "fresh_cookie"

    @pytest.mark.asyncio
    async def test_exception(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.browser_cookie_provider = AsyncMock(side_effect=Exception("browser error"))
        result = await mgr._try_auto_refresh_cookie_source(reason="test")
        assert result == ""


class TestPersistCookie:
    def test_no_path(self, tmp_path):
        mgr = _make_manager(tmp_path, cookie_file_path="")
        mgr._persist_cookie("test")

    def test_writes_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._persist_cookie("my_cookie")
        content = mgr.cookie_file_path.read_text(encoding="utf-8")
        assert content == "my_cookie"


class TestScheduleRetry:
    @pytest.mark.asyncio
    async def test_normal_backoff(self, tmp_path):
        mgr = _make_manager(tmp_path)
        await mgr._schedule_retry(1)
        assert mgr._next_retry_at is not None

    @pytest.mark.asyncio
    async def test_cooldown(self, tmp_path):
        mgr = _make_manager(tmp_path)
        await mgr._schedule_retry(1, cooldown=True)
        assert mgr._next_retry_at is not None

    @pytest.mark.asyncio
    async def test_with_jitter(self, tmp_path):
        mgr = _make_manager(tmp_path, failure_jitter_seconds=0.5)
        await mgr._schedule_retry(1)
        assert mgr._next_retry_at is not None


class TestSleepUntilRetry:
    @pytest.mark.asyncio
    async def test_no_retry(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._next_retry_at = None
        await mgr._sleep_until_retry()

    @pytest.mark.asyncio
    async def test_with_retry(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._next_retry_at = time.time() + 0.001
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await mgr._sleep_until_retry()
            mock_sleep.assert_called_once()


class TestClassifyFailure:
    def test_validate_and_invalid(self):
        code, cat = CookieRenewalManager._classify_failure(
            reason="test", exc=RuntimeError("FAIL_SYS_USER_VALIDATE cookie_invalid")
        )
        assert code == "FAIL_SYS_USER_VALIDATE"
        assert cat == "cookie_invalid"

    def test_validate_only(self):
        code, cat = CookieRenewalManager._classify_failure(
            reason="test", exc=RuntimeError("FAIL_SYS_USER_VALIDATE")
        )
        assert cat == "transient_risk"

    def test_invalid_only(self):
        code, cat = CookieRenewalManager._classify_failure(
            reason="test", exc=RuntimeError("cookie_invalid")
        )
        assert code == "COOKIE_INVALID"
        assert cat == "cookie_invalid"

    def test_unknown(self):
        code, cat = CookieRenewalManager._classify_failure(
            reason="test", exc=RuntimeError("something else")
        )
        assert cat == "unknown"


class TestAudit:
    @pytest.mark.asyncio
    async def test_writes_log(self, tmp_path):
        mgr = _make_manager(tmp_path)
        await mgr._audit(event="test", ok=True, reason="r", state="idle")
        log_path = Path(mgr.audit_log_path)
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        data = json.loads(lines[0])
        assert data["event"] == "test"

    @pytest.mark.asyncio
    async def test_with_changed(self, tmp_path):
        mgr = _make_manager(tmp_path)
        await mgr._audit(event="test", ok=True, reason="r", changed=True, state="idle")
        log_path = Path(mgr.audit_log_path)
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        data = json.loads(lines[0])
        assert data["changed"] is True


class TestFmtTs:
    def test_none(self):
        assert CookieRenewalManager._fmt_ts(None) is None

    def test_value(self):
        result = CookieRenewalManager._fmt_ts(0)
        assert "1970" in result


class TestCookieFingerprint:
    def test_fingerprint(self):
        import hashlib
        result = CookieRenewalManager._cookie_fingerprint("test")
        expected = hashlib.sha256(b"test").hexdigest()
        assert result == expected


class TestBuildCookieLoader:
    def test_from_file(self, tmp_path):
        cf = tmp_path / "cookie.txt"
        cf.write_text("file_cookie", encoding="utf-8")
        loader = build_cookie_loader(inline_cookie="inline", cookie_file=str(cf))
        assert loader() == "file_cookie"

    def test_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LITE_COOKIE", "env_cookie")
        loader = build_cookie_loader(inline_cookie="", cookie_file="")
        assert loader() == "env_cookie"

    def test_from_inline(self, monkeypatch):
        monkeypatch.delenv("LITE_COOKIE", raising=False)
        monkeypatch.delenv("XIANYU_COOKIE_1", raising=False)
        loader = build_cookie_loader(inline_cookie="inline_val", cookie_file="")
        assert loader() == "inline_val"

    def test_file_not_exist(self, monkeypatch):
        monkeypatch.setenv("LITE_COOKIE", "env")
        loader = build_cookie_loader(inline_cookie="", cookie_file="/nonexistent/path.txt")
        assert loader() == "env"

    def test_empty_file(self, tmp_path, monkeypatch):
        cf = tmp_path / "empty.txt"
        cf.write_text("", encoding="utf-8")
        monkeypatch.setenv("XIANYU_COOKIE_1", "xy_cookie")
        monkeypatch.delenv("LITE_COOKIE", raising=False)
        loader = build_cookie_loader(inline_cookie="", cookie_file=str(cf))
        assert loader() == "xy_cookie"
