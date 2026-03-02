from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.browser_client import create_browser_client


@dataclass
class CookieSnapshot:
    cookie_text: str
    fingerprint: str
    updated_at: float
    source: str


class BrowserSessionCookieSource:
    """Read goofish cookie from local logged-in browser session."""

    async def get_latest_cookie(self) -> CookieSnapshot | None:
        client = await create_browser_client({"runtime": "auto"})
        try:
            cookies = await client.get_cookies()
        finally:
            await client.disconnect()

        cookie_text = _join_goofish_cookie_pairs(cookies)
        if not cookie_text:
            return None
        now = time.time()
        return CookieSnapshot(
            cookie_text=cookie_text,
            fingerprint=_cookie_fingerprint(cookie_text),
            updated_at=now,
            source="browser_session",
        )


class FileEnvCookieSource:
    """Fallback cookie source from cookie file then env/inline."""

    def __init__(self, *, inline_cookie: str = "", cookie_file: str = ""):
        self.inline_cookie = str(inline_cookie or "").strip()
        self.cookie_file = str(cookie_file or "").strip()

    async def get_latest_cookie(self) -> CookieSnapshot | None:
        cookie_text = ""
        updated_at = time.time()

        if self.cookie_file:
            p = Path(self.cookie_file)
            if p.exists():
                cookie_text = p.read_text(encoding="utf-8").strip()
                if cookie_text:
                    try:
                        updated_at = p.stat().st_mtime
                    except Exception:
                        updated_at = time.time()

        if not cookie_text:
            import os

            cookie_text = str(os.getenv("LITE_COOKIE") or os.getenv("XIANYU_COOKIE_1") or self.inline_cookie or "").strip()

        if not cookie_text:
            return None

        return CookieSnapshot(
            cookie_text=cookie_text,
            fingerprint=_cookie_fingerprint(cookie_text),
            updated_at=updated_at,
            source="file_or_env",
        )


class CookieSourceAdapter:
    """Unified adapter for cookie_renewal: browser first, fallback to file/env."""

    def __init__(self, *, browser_source: Any, fallback_source: Any):
        self.browser_source = browser_source
        self.fallback_source = fallback_source

    async def get_latest_cookie(self) -> CookieSnapshot | None:
        browser_getter = getattr(self.browser_source, "get_latest_cookie", None)
        if callable(browser_getter):
            snap = await browser_getter()
            if snap and getattr(snap, "cookie_text", ""):
                return snap

        fallback_getter = getattr(self.fallback_source, "get_latest_cookie", None)
        if callable(fallback_getter):
            return await fallback_getter()

        return None


def _cookie_fingerprint(cookie_text: str) -> str:
    return hashlib.sha256(str(cookie_text or "").strip().encode("utf-8")).hexdigest()


def _join_goofish_cookie_pairs(cookies: Any) -> str:
    if not isinstance(cookies, list) or not cookies:
        return ""

    pairs: list[str] = []
    for c in cookies:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "") or "").strip()
        value = str(c.get("value", "") or "").strip()
        domain = str(c.get("domain", "") or "").strip().lower()
        if not name or not value:
            continue
        if ("goofish" in domain) or ("taobao" in domain) or ("xianyu" in domain):
            pairs.append(f"{name}={value}")
    return "; ".join(pairs)
