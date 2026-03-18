"""BitBrowser CDP 公共工具 — 提供 CDP 连接、Cookie 直读和并发锁。

供 ws_live.py（Cookie 恢复）和 slider_solver.py（DrissionPage 连接）共用。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BB_LOCK = asyncio.Lock()

_COOKIE_DOMAINS = (".goofish.com", ".taobao.com", ".mmstat.com", ".alibaba.com")


def _domain_matches(domain: str, patterns: tuple[str, ...] = _COOKIE_DOMAINS) -> bool:
    for p in patterns:
        if domain.endswith(p) or domain == p.lstrip("."):
            return True
    return False


async def get_cdp_ws_url(api_url: str, browser_id: str) -> str | None:
    """调用 BitBrowser /browser/open 获取 CDP WebSocket URL。"""
    if not api_url or not browser_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{api_url.rstrip('/')}/browser/open",
                json={"id": browser_id},
            )
            data = resp.json()
            if not data.get("success"):
                logger.debug("BitBrowser open failed: %s", data)
                return None
            ws_url = data.get("data", {}).get("ws")
            if not ws_url:
                logger.debug("BitBrowser returned no ws URL")
                return None
            return ws_url
    except Exception as exc:
        logger.debug("BitBrowser API error: %s", exc)
        return None


async def read_cookies_via_cdp(
    cdp_ws_url: str,
    domains: tuple[str, ...] = _COOKIE_DOMAINS,
) -> str | None:
    """通过 CDP Network.getAllCookies 读取 cookie，过滤指定域名。

    返回 'key=value; key=value' 格式字符串，或 None（失败时）。
    使用 websockets 库直接发送 CDP 命令，不依赖 Playwright / DrissionPage。
    """
    try:
        import websockets
    except ImportError:
        logger.debug("websockets not installed, cannot read cookies via CDP")
        return None

    try:
        async with websockets.connect(cdp_ws_url, open_timeout=10, close_timeout=5) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            resp = json.loads(raw)
            cookies: list[dict[str, Any]] = resp.get("result", {}).get("cookies", [])
    except Exception as exc:
        logger.debug("CDP cookie read failed: %s", exc)
        return None

    if not cookies:
        return None

    seen: dict[str, tuple[str, str]] = {}
    for c in cookies:
        domain = c.get("domain", "")
        if not _domain_matches(domain, domains):
            continue
        name = c.get("name", "")
        value = c.get("value", "")
        if not name or not value:
            continue
        path = c.get("path", "/")
        if name not in seen or len(path) >= len(seen[name][1]):
            seen[name] = (value, path)

    if not seen:
        return None

    return "; ".join(f"{k}={v}" for k, (v, _) in seen.items())


def get_fp_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """从 ws config 中提取 fingerprint_browser 配置。"""
    ws_cfg = config or {}
    slider_cfg = ws_cfg.get("slider_auto_solve", {})
    if not isinstance(slider_cfg, dict):
        slider_cfg = {}
    fp_cfg = slider_cfg.get("fingerprint_browser", {})
    if not isinstance(fp_cfg, dict):
        fp_cfg = {}
    return {
        "enabled": bool(fp_cfg.get("enabled", False)),
        "api_url": str(fp_cfg.get("api_url", "http://127.0.0.1:54345")).rstrip("/"),
        "browser_id": str(fp_cfg.get("browser_id", "")),
    }
