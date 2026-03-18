"""
Browser Client — 浏览器自动化客户端。

使用 DrissionPageBrowserClient 驱动本地 Chrome / BitBrowser。
"""

from __future__ import annotations

from typing import Any

from src.core.error_handler import BrowserError


async def create_browser_client(config: dict[str, Any] | None = None):
    """创建并连接浏览器客户端（DrissionPage）。"""
    try:
        from src.core.drissionpage_client import DrissionPageBrowserClient
    except Exception as exc:
        raise BrowserError(
            "DrissionPage is required. Install with: pip install DrissionPage"
        ) from exc

    client = DrissionPageBrowserClient(config)
    connected = await client.connect()
    if not connected:
        raise BrowserError(
            "Failed to start DrissionPage browser. Run: pip install DrissionPage"
        )
    return client


__all__ = ["BrowserError", "create_browser_client"]
