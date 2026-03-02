from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.lite.cookie_renewal import CookieRenewalManager, build_cookie_loader


class _Api:
    def __init__(self):
        self.cookie_text = "old"
        self.has_login_ok = True
        self.token_called = 0
        self.device_id = "dev-old"
        self.user_id = "u-old"

    def update_cookie(self, cookie_text: str) -> None:
        self.cookie_text = cookie_text
        self.device_id = "dev-new"
        self.user_id = "u-new"

    async def has_login(self) -> bool:
        return self.has_login_ok

    async def get_token(self, *, force_refresh: bool = False) -> str:
        self.token_called += 1
        return "tok"


class _Ws:
    def __init__(self):
        self.cookie = "old"
        self.reconnect_called = 0
        self.device_id = "dev-old"
        self.my_user_id = "u-old"

    def update_cookie(self, cookie: str) -> None:
        self.cookie = cookie

    def update_auth_context(self, *, cookie: str, device_id: str, my_user_id: str) -> None:
        self.cookie = cookie
        self.device_id = device_id
        self.my_user_id = my_user_id

    async def force_reconnect(self, reason: str = "manual") -> None:
        self.reconnect_called += 1


@pytest.mark.asyncio
async def test_cookie_renewal_success(tmp_path: Path):
    api = _Api()
    ws = _Ws()
    audit = tmp_path / "audit.log"

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "new_cookie",
        audit_log_path=str(audit),
        check_interval_seconds=30,
    )
    ok = await mgr.renew(reason="test")
    assert ok is True
    assert api.cookie_text == "new_cookie"
    assert ws.cookie == "new_cookie"
    assert ws.reconnect_called == 1
    rows = [json.loads(x) for x in audit.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows[-1]["event"] == "renew_ok"


@pytest.mark.asyncio
async def test_cookie_renewal_failed_login(tmp_path: Path):
    api = _Api()
    api.has_login_ok = False
    ws = _Ws()
    audit = tmp_path / "audit.log"

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "new_cookie",
        audit_log_path=str(audit),
        check_interval_seconds=30,
    )
    ok = await mgr.renew(reason="test_fail")
    assert ok is False
    rows = [json.loads(x) for x in audit.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows[-1]["event"] == "renew_failed"


def test_build_cookie_loader_file_priority(tmp_path: Path):
    cookie_file = tmp_path / "cookie.txt"
    cookie_file.write_text("file_cookie", encoding="utf-8")

    loader = build_cookie_loader(inline_cookie="inline_cookie", cookie_file=str(cookie_file))
    assert loader() == "file_cookie"


@pytest.mark.asyncio
async def test_cookie_renewal_updates_ws_auth_context_for_reconnect(tmp_path: Path):
    api = _Api()
    ws = _Ws()
    audit = tmp_path / "audit.log"

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "new_cookie",
        audit_log_path=str(audit),
        check_interval_seconds=30,
    )

    ok = await mgr.renew(reason="auth_fail_after_cookie_recover")
    assert ok is True
    assert ws.cookie == "new_cookie"
    assert ws.device_id == "dev-new"
    assert ws.my_user_id == "u-new"
    assert ws.reconnect_called == 1


class _Adapter:
    def __init__(self, cookie_text: str = ""):
        self.cookie_text = cookie_text

    async def get_latest_cookie(self):
        if not self.cookie_text:
            return None
        return {
            "cookie_text": self.cookie_text,
            "fingerprint": "fp-adapter",
            "updated_at": 123.0,
        }


@pytest.mark.asyncio
async def test_cookie_renewal_uses_cookie_source_adapter(tmp_path: Path):
    api = _Api()
    ws = _Ws()
    audit = tmp_path / "audit.log"

    mgr = CookieRenewalManager(
        api_client=api,
        ws_client=ws,
        cookie_loader=lambda: "loader_cookie",
        cookie_source_adapter=_Adapter("adapter_cookie"),
        audit_log_path=str(audit),
        check_interval_seconds=30,
    )
    ok = await mgr.renew(reason="test_adapter")

    assert ok is True
    assert api.cookie_text == "adapter_cookie"
    assert ws.cookie == "adapter_cookie"
