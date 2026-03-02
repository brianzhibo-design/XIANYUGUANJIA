from __future__ import annotations

import json

import pytest

from src.lite.cookie_renewal import CookieRenewalManager


class _API:
    def __init__(self, cookie: str = "unb=u1;_m_h5_tk=t_1"):
        self.cookie_text = cookie
        self.login_ok = True
        self.token_ok = True

    def update_cookie(self, cookie_text: str) -> None:
        self.cookie_text = cookie_text

    async def has_login(self) -> bool:
        return self.login_ok

    async def get_token(self, *, force_refresh: bool = False) -> str:
        if not self.token_ok:
            raise ValueError("token failed")
        return "tk"


class _WS:
    def __init__(self):
        self.cookie = ""
        self.reconnect_called = 0

    def update_cookie(self, cookie: str) -> None:
        self.cookie = cookie

    async def force_reconnect(self, reason: str = "manual") -> None:
        self.reconnect_called += 1


@pytest.mark.asyncio
async def test_cookie_renewal_success_flow(tmp_path):
    api = _API()
    ws = _WS()
    audit = tmp_path / "audit.log"

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "unb=u1;_m_h5_tk=t2_1",
        audit_log_path=str(audit),
        min_renew_interval_seconds=0,
        failure_jitter_seconds=0,
    )

    ok = await mgr.renew(reason="sim_auth_invalid")
    assert ok is True
    assert ws.reconnect_called == 1
    status = mgr.status()
    assert status["last_cookie_refresh"] is not None
    assert status["last_token_refresh"] is not None
    assert status["recover_count"] == 1


@pytest.mark.asyncio
async def test_cookie_renewal_failure_backoff(tmp_path, monkeypatch):
    api = _API()
    api.login_ok = False
    ws = _WS()
    audit = tmp_path / "audit.log"

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("src.lite.cookie_renewal.asyncio.sleep", _fake_sleep)

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "unb=u1;_m_h5_tk=t3_1",
        audit_log_path=str(audit),
        min_renew_interval_seconds=0,
        failure_backoff_base_seconds=2,
        failure_jitter_seconds=0,
    )

    ok = await mgr.renew(reason="sim_login_fail")
    assert ok is False
    assert slept and slept[-1] >= 1.9
    assert mgr.status()["recover_count"] == 0


@pytest.mark.asyncio
async def test_cookie_renewal_duplicate_recovery_waiting_cookie(tmp_path, monkeypatch):
    api = _API("unb=u1;_m_h5_tk=same_1")
    api.login_ok = False
    ws = _WS()
    audit = tmp_path / "audit.log"

    async def _fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("src.lite.cookie_renewal.asyncio.sleep", _fake_sleep)

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "unb=u1;_m_h5_tk=same_1",
        audit_log_path=str(audit),
        min_renew_interval_seconds=0,
        failure_jitter_seconds=0,
    )

    first = await mgr.renew(reason="sim_fail_1")
    mgr._last_renew_attempt_at = 0
    second = await mgr.renew(reason="sim_fail_2")

    assert first is False
    assert second is False
    assert ws.reconnect_called == 0

    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any((r.get("state") == "waiting_new_cookie") and ("same_cookie_fingerprint" in str(r.get("reason")) or "cookie_invalid_or_expired" in str(r.get("reason"))) for r in rows)


@pytest.mark.asyncio
async def test_risk_branch_backoff_and_budget_to_waiting_cookie(tmp_path, monkeypatch):
    api = _API("old_cookie")
    ws = _WS()
    audit = tmp_path / "audit.log"

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("src.lite.cookie_renewal.asyncio.sleep", _fake_sleep)

    class _RiskAPI(_API):
        async def get_token(self, *, force_refresh: bool = False) -> str:
            raise RuntimeError("FAIL_SYS_USER_VALIDATE::risk_busy")

    api2 = _RiskAPI("old_cookie")
    mgr = CookieRenewalManager(
        api_client=api2,
        ws_client=ws,
        cookie_loader=lambda: "new_cookie",
        audit_log_path=str(audit),
        min_renew_interval_seconds=0,
        failure_backoff_base_seconds=2,
        failure_jitter_seconds=0,
        risk_retry_budget=2,
        risk_cooldown_seconds=30,
    )

    first = await mgr.renew(reason="token_fetch_failed")
    mgr._last_renew_attempt_at = 0
    second = await mgr.renew(reason="token_fetch_failed")

    assert first is False and second is False
    assert mgr.status()["last_risk_code"] == "FAIL_SYS_USER_VALIDATE"
    assert mgr.status()["risk_fail_count"] >= 1.9
    assert mgr.status()["state"] == "waiting_new_cookie"
    assert slept[0] >= 1.9
    assert slept[1] >= 2.90


@pytest.mark.asyncio
async def test_empty_cookie_source_enters_waiting_state_not_loop(tmp_path, monkeypatch):
    api = _API("old_cookie")
    ws = _WS()
    audit = tmp_path / "audit.log"

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("src.lite.cookie_renewal.asyncio.sleep", _fake_sleep)

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "",
        audit_log_path=str(audit),
        min_renew_interval_seconds=0,
        failure_backoff_base_seconds=3,
        failure_jitter_seconds=0,
    )

    ok = await mgr.renew(reason="token_fetch_failed")

    assert ok is False
    assert mgr.status()["state"] == "waiting_new_cookie"
    assert mgr.status()["next_retry_at"] is not None
    assert slept and slept[-1] >= 2.9
    assert ws.reconnect_called == 0


@pytest.mark.asyncio
async def test_auto_fetch_cookie_and_persist_file(tmp_path, monkeypatch):
    api = _API("old_cookie")
    ws = _WS()
    audit = tmp_path / "audit.log"
    cookie_file = tmp_path / "lite_cookie.txt"

    async def _fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("src.lite.cookie_renewal.asyncio.sleep", _fake_sleep)

    async def _provider() -> str:
        return "auto_cookie=v1; _m_h5_tk=t1"

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "",
        browser_cookie_provider=_provider,
        cookie_file_path=str(cookie_file),
        audit_log_path=str(audit),
        min_renew_interval_seconds=0,
        failure_jitter_seconds=0,
    )

    ok = await mgr.renew(reason="token_fetch_failed")
    assert ok is True
    assert cookie_file.read_text(encoding="utf-8").strip().startswith("auto_cookie=v1")
    assert ws.reconnect_called == 1
