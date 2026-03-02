from __future__ import annotations

import pytest

from src.lite.cookie_source_adapter import CookieSnapshot, CookieSourceAdapter


class _BrowserSource:
    def __init__(self, snap: CookieSnapshot | None):
        self.snap = snap

    async def get_latest_cookie(self):
        return self.snap


class _FallbackSource:
    def __init__(self, snap: CookieSnapshot | None):
        self.snap = snap

    async def get_latest_cookie(self):
        return self.snap


@pytest.mark.asyncio
async def test_cookie_source_adapter_prefers_browser_snapshot():
    browser = _BrowserSource(CookieSnapshot(cookie_text="a=1", fingerprint="fp1", updated_at=1.0, source="browser_session"))
    fallback = _FallbackSource(CookieSnapshot(cookie_text="b=2", fingerprint="fp2", updated_at=2.0, source="file_or_env"))
    adapter = CookieSourceAdapter(browser_source=browser, fallback_source=fallback)

    snap = await adapter.get_latest_cookie()
    assert snap is not None
    assert snap.cookie_text == "a=1"
    assert snap.source == "browser_session"


@pytest.mark.asyncio
async def test_cookie_source_adapter_fallback_when_browser_empty():
    browser = _BrowserSource(None)
    fallback = _FallbackSource(CookieSnapshot(cookie_text="b=2", fingerprint="fp2", updated_at=2.0, source="file_or_env"))
    adapter = CookieSourceAdapter(browser_source=browser, fallback_source=fallback)

    snap = await adapter.get_latest_cookie()
    assert snap is not None
    assert snap.cookie_text == "b=2"
    assert snap.source == "file_or_env"
