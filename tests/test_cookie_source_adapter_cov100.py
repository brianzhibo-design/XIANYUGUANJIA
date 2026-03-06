from __future__ import annotations

import hashlib
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.lite.cookie_source_adapter import (
    BrowserSessionCookieSource,
    CookieSnapshot,
    CookieSourceAdapter,
    FileEnvCookieSource,
    _cookie_fingerprint,
    _join_goofish_cookie_pairs,
)


class TestCookieSnapshot:
    def test_dataclass_fields(self):
        snap = CookieSnapshot(cookie_text="a=b", fingerprint="fp", updated_at=1.0, source="test")
        assert snap.cookie_text == "a=b"
        assert snap.fingerprint == "fp"
        assert snap.updated_at == 1.0
        assert snap.source == "test"


class TestCookieFingerprint:
    def test_fingerprint(self):
        result = _cookie_fingerprint("hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    def test_empty(self):
        result = _cookie_fingerprint("")
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected


class TestJoinGoofishCookiePairs:
    def test_empty_list(self):
        assert _join_goofish_cookie_pairs([]) == ""

    def test_not_list(self):
        assert _join_goofish_cookie_pairs(None) == ""
        assert _join_goofish_cookie_pairs("string") == ""

    def test_filters_by_domain(self):
        cookies = [
            {"name": "a", "value": "1", "domain": ".goofish.com"},
            {"name": "b", "value": "2", "domain": ".taobao.com"},
            {"name": "c", "value": "3", "domain": ".google.com"},
            {"name": "d", "value": "4", "domain": ".xianyu.com"},
        ]
        result = _join_goofish_cookie_pairs(cookies)
        assert "a=1" in result
        assert "b=2" in result
        assert "c=3" not in result
        assert "d=4" in result

    def test_skips_empty_name_or_value(self):
        cookies = [
            {"name": "", "value": "1", "domain": ".goofish.com"},
            {"name": "a", "value": "", "domain": ".goofish.com"},
        ]
        assert _join_goofish_cookie_pairs(cookies) == ""

    def test_skips_non_dict(self):
        cookies = [123, "str", {"name": "a", "value": "1", "domain": ".goofish.com"}]
        result = _join_goofish_cookie_pairs(cookies)
        assert result == "a=1"


class TestBrowserSessionCookieSource:
    @pytest.mark.asyncio
    async def test_returns_snapshot(self):
        mock_client = AsyncMock()
        mock_client.get_cookies = AsyncMock(return_value=[
            {"name": "sid", "value": "xyz", "domain": ".goofish.com"},
        ])
        mock_client.disconnect = AsyncMock()

        with patch("src.lite.cookie_source_adapter.create_browser_client", new_callable=AsyncMock, return_value=mock_client):
            source = BrowserSessionCookieSource()
            snap = await source.get_latest_cookie()
            assert snap is not None
            assert snap.cookie_text == "sid=xyz"
            assert snap.source == "browser_session"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_cookies(self):
        mock_client = AsyncMock()
        mock_client.get_cookies = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("src.lite.cookie_source_adapter.create_browser_client", new_callable=AsyncMock, return_value=mock_client):
            source = BrowserSessionCookieSource()
            snap = await source.get_latest_cookie()
            assert snap is None


class TestFileEnvCookieSource:
    @pytest.mark.asyncio
    async def test_from_file(self, tmp_path):
        cf = tmp_path / "cookie.txt"
        cf.write_text("session=abc123", encoding="utf-8")
        source = FileEnvCookieSource(cookie_file=str(cf))
        snap = await source.get_latest_cookie()
        assert snap is not None
        assert snap.cookie_text == "session=abc123"
        assert snap.source == "file_or_env"

    @pytest.mark.asyncio
    async def test_from_file_mtime_error(self, tmp_path):
        cf = tmp_path / "cookie.txt"
        cf.write_text("abc", encoding="utf-8")
        source = FileEnvCookieSource(cookie_file=str(cf))

        original_stat = Path.stat
        call_count = 0

        def patched_stat(self_path):
            nonlocal call_count
            call_count += 1
            if str(self_path) == str(cf) and call_count > 1:
                raise OSError("stat failed")
            return original_stat(self_path)

        with patch.object(Path, "stat", patched_stat):
            snap = await source.get_latest_cookie()
            assert snap is not None
            assert snap.cookie_text == "abc"

    @pytest.mark.asyncio
    async def test_from_env(self, monkeypatch):
        monkeypatch.setenv("LITE_COOKIE", "env_cookie_val")
        source = FileEnvCookieSource()
        snap = await source.get_latest_cookie()
        assert snap is not None
        assert snap.cookie_text == "env_cookie_val"

    @pytest.mark.asyncio
    async def test_from_xianyu_cookie_env(self, monkeypatch):
        monkeypatch.delenv("LITE_COOKIE", raising=False)
        monkeypatch.setenv("XIANYU_COOKIE_1", "xy_cookie")
        source = FileEnvCookieSource()
        snap = await source.get_latest_cookie()
        assert snap is not None
        assert snap.cookie_text == "xy_cookie"

    @pytest.mark.asyncio
    async def test_from_inline(self, monkeypatch):
        monkeypatch.delenv("LITE_COOKIE", raising=False)
        monkeypatch.delenv("XIANYU_COOKIE_1", raising=False)
        source = FileEnvCookieSource(inline_cookie="inline_val")
        snap = await source.get_latest_cookie()
        assert snap is not None
        assert snap.cookie_text == "inline_val"

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, monkeypatch):
        monkeypatch.delenv("LITE_COOKIE", raising=False)
        monkeypatch.delenv("XIANYU_COOKIE_1", raising=False)
        source = FileEnvCookieSource()
        snap = await source.get_latest_cookie()
        assert snap is None

    @pytest.mark.asyncio
    async def test_file_not_exist_fallback_env(self, monkeypatch):
        monkeypatch.setenv("LITE_COOKIE", "fallback")
        source = FileEnvCookieSource(cookie_file="/nonexistent/path.txt")
        snap = await source.get_latest_cookie()
        assert snap is not None
        assert snap.cookie_text == "fallback"

    @pytest.mark.asyncio
    async def test_file_empty_fallback_env(self, tmp_path, monkeypatch):
        cf = tmp_path / "empty.txt"
        cf.write_text("", encoding="utf-8")
        monkeypatch.setenv("LITE_COOKIE", "from_env")
        source = FileEnvCookieSource(cookie_file=str(cf))
        snap = await source.get_latest_cookie()
        assert snap is not None
        assert snap.cookie_text == "from_env"


class TestCookieSourceAdapter:
    @pytest.mark.asyncio
    async def test_browser_source_success(self):
        browser = AsyncMock()
        snap = CookieSnapshot(cookie_text="bsc", fingerprint="f", updated_at=1.0, source="browser")
        browser.get_latest_cookie = AsyncMock(return_value=snap)
        fallback = AsyncMock()
        adapter = CookieSourceAdapter(browser_source=browser, fallback_source=fallback)
        result = await adapter.get_latest_cookie()
        assert result is snap

    @pytest.mark.asyncio
    async def test_browser_returns_none_uses_fallback(self):
        browser = AsyncMock()
        browser.get_latest_cookie = AsyncMock(return_value=None)
        fallback = AsyncMock()
        fb_snap = CookieSnapshot(cookie_text="fb", fingerprint="f2", updated_at=2.0, source="file")
        fallback.get_latest_cookie = AsyncMock(return_value=fb_snap)
        adapter = CookieSourceAdapter(browser_source=browser, fallback_source=fallback)
        result = await adapter.get_latest_cookie()
        assert result is fb_snap

    @pytest.mark.asyncio
    async def test_browser_empty_cookie_text_uses_fallback(self):
        browser = AsyncMock()
        empty_snap = CookieSnapshot(cookie_text="", fingerprint="", updated_at=1.0, source="b")
        browser.get_latest_cookie = AsyncMock(return_value=empty_snap)
        fallback = AsyncMock()
        fb_snap = CookieSnapshot(cookie_text="real", fingerprint="r", updated_at=2.0, source="f")
        fallback.get_latest_cookie = AsyncMock(return_value=fb_snap)
        adapter = CookieSourceAdapter(browser_source=browser, fallback_source=fallback)
        result = await adapter.get_latest_cookie()
        assert result is fb_snap

    @pytest.mark.asyncio
    async def test_no_getter_methods(self):
        adapter = CookieSourceAdapter(browser_source=object(), fallback_source=object())
        result = await adapter.get_latest_cookie()
        assert result is None

    @pytest.mark.asyncio
    async def test_no_fallback_getter(self):
        browser = AsyncMock()
        browser.get_latest_cookie = AsyncMock(return_value=None)
        adapter = CookieSourceAdapter(browser_source=browser, fallback_source=object())
        result = await adapter.get_latest_cookie()
        assert result is None
