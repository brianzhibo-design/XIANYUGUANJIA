"""
DrissionPage Lite Browser Client

本地轻量浏览器客户端：
- 不依赖 Playwright
- 使用 DrissionPage 驱动 Chromium
- 兼容现有服务层常用方法签名（PlaywrightBrowserClient 的直接替代）
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import uuid
from pathlib import Path
from typing import Any

from src.core.error_handler import BrowserError
from src.core.logger import get_logger

try:
    from DrissionPage import Chromium, ChromiumOptions
except ImportError:
    Chromium = None  # type: ignore[assignment,misc]
    ChromiumOptions = None  # type: ignore[assignment,misc]


def _css(selector: str) -> str:
    """Auto-prepend ``css:`` for bare CSS selectors."""
    if selector.startswith(("css:", "xpath:", "@", "text:", "tag:", "t:", "tx:")):
        return selector
    return f"css:{selector}"


class DrissionPageBrowserClient:
    """Lite 模式浏览器客户端（DrissionPage 实现）。

    所有公开方法签名与原 PlaywrightBrowserClient 完全兼容。
    DrissionPage 是同步库，内部通过 ``asyncio.to_thread`` 桥接为 async。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        from src.core.config import get_config

        app_config = get_config()
        browser_cfg = app_config.browser

        self.logger = get_logger()
        self.config = config or {}
        self.headless = bool(self.config.get("headless", browser_cfg.get("headless", True)))
        self.timeout = int(self.config.get("timeout", 30))

        delay_cfg = browser_cfg.get("delay", {})
        self.delay_min = float(self.config.get("delay_min", delay_cfg.get("min", 1.0)))
        self.delay_max = float(self.config.get("delay_max", delay_cfg.get("max", 3.0)))

        viewport_cfg = browser_cfg.get("viewport", {"width": 1280, "height": 800})
        self.viewport = {
            "width": int(viewport_cfg.get("width", 1280)),
            "height": int(viewport_cfg.get("height", 800)),
        }
        self.user_agent = str(browser_cfg.get("user_agent", "") or "").strip()

        cookie_seed = str(os.getenv("XIANYU_COOKIE_1", "") or "").strip()
        if not cookie_seed:
            for account in app_config.accounts:
                if bool(account.get("enabled", True)):
                    raw_cookie = str(account.get("cookie", "") or "").strip()
                    if raw_cookie:
                        cookie_seed = raw_cookie
                        break
        self._cookies_seed = cookie_seed

        self._browser: Any | None = None
        self._tabs: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def random_delay(self) -> float:
        return random.uniform(self.delay_min, self.delay_max)

    def _get_tab(self, page_id: str) -> Any:
        tab = self._tabs.get(page_id)
        if tab is None:
            raise BrowserError(f"Tab not found: {page_id}")
        return tab

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        if Chromium is None:
            self.logger.error(
                "DrissionPage is not installed. Run: pip install DrissionPage"
            )
            return False

        if self._browser is not None:
            return True

        try:

            def _connect() -> Any:
                co = ChromiumOptions()
                co.auto_port()
                if self.headless:
                    co.headless()
                if self.user_agent:
                    co.set_user_agent(self.user_agent)
                co.set_argument(
                    "--window-size",
                    f'{self.viewport["width"]},{self.viewport["height"]}',
                )
                exe = os.getenv("CHROME_EXECUTABLE_PATH", "").strip()
                if exe:
                    co.set_browser_path(exe)
                return Chromium(co)

            self._browser = await asyncio.to_thread(_connect)

            if self._cookies_seed:
                await self.set_cookies_for_domain(self._cookies_seed)

            self.logger.info("Connected to DrissionPage Lite browser")
            return True
        except Exception as exc:
            self.logger.error(f"DrissionPage connect failed: {exc}")
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        for page_id in list(self._tabs):
            await self.close_page(page_id)
        if self._browser is not None:
            try:
                await asyncio.to_thread(self._browser.quit)
            except Exception:
                pass
            self._browser = None

    async def is_connected(self) -> bool:
        return self._browser is not None

    async def ensure_connected(self) -> bool:
        if await self.is_connected():
            return True
        return await self.connect()

    # ------------------------------------------------------------------
    # tab management
    # ------------------------------------------------------------------

    async def new_page(self) -> str:
        if not await self.ensure_connected() or self._browser is None:
            raise BrowserError("DrissionPage browser is not connected")
        tab = await asyncio.to_thread(self._browser.new_tab)
        page_id = f"dp_{uuid.uuid4().hex[:12]}"
        self._tabs[page_id] = tab
        return page_id

    async def close_page(self, page_id: str) -> bool:
        tab = self._tabs.pop(page_id, None)
        if tab is None:
            return False
        try:
            await asyncio.to_thread(tab.close)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # navigation
    # ------------------------------------------------------------------

    async def navigate(self, page_id: str, url: str, wait_load: bool = True) -> bool:
        tab = self._get_tab(page_id)
        try:
            await asyncio.to_thread(tab.get, url, timeout=self.timeout)
            if wait_load:
                await asyncio.sleep(self.random_delay())
            return True
        except Exception as exc:
            self.logger.warning(f"Navigate failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # interactions
    # ------------------------------------------------------------------

    async def click(
        self,
        page_id: str,
        selector: str,
        timeout: int = 10000,
        retry: bool = True,
    ) -> bool:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        attempts = 3 if retry else 1
        t_sec = timeout / 1000

        for _ in range(attempts):
            try:

                def _click() -> bool:
                    ele = tab.ele(dp_sel, timeout=t_sec)
                    if ele:
                        ele.click()
                        return True
                    return False

                if await asyncio.to_thread(_click):
                    await asyncio.sleep(self.random_delay())
                    return True
            except Exception:
                await asyncio.sleep(0.2)
        return False

    async def type_text(
        self,
        page_id: str,
        selector: str,
        text: str,
        clear: bool = True,
    ) -> bool:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        try:

            def _type() -> bool:
                ele = tab.ele(dp_sel, timeout=self.timeout)
                if not ele:
                    return False
                if clear:
                    ele.clear()
                ele.input(text)
                return True

            result = await asyncio.to_thread(_type)
            if result:
                await asyncio.sleep(self.random_delay())
            return bool(result)
        except Exception as exc:
            self.logger.warning(f"Type text failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    async def find_elements(
        self, page_id: str, selector: str
    ) -> list[dict[str, Any]]:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        try:

            def _find() -> list[dict[str, Any]]:
                eles = tab.eles(dp_sel, timeout=3)
                return [{"selector": selector, "index": i} for i in range(len(eles))]

            return await asyncio.to_thread(_find)
        except Exception:
            return []

    async def find_element(
        self, page_id: str, selector: str
    ) -> dict[str, Any] | None:
        items = await self.find_elements(page_id, selector)
        return items[0] if items else None

    async def get_text(self, page_id: str, selector: str) -> str | None:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        try:

            def _text() -> str | None:
                ele = tab.ele(dp_sel, timeout=5)
                return ele.text if ele else None

            return await asyncio.to_thread(_text)
        except Exception:
            return None

    async def get_value(self, page_id: str, selector: str) -> str | None:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        try:

            def _value() -> str | None:
                ele = tab.ele(dp_sel, timeout=5)
                return ele.value if ele else None

            return await asyncio.to_thread(_value)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # waits
    # ------------------------------------------------------------------

    async def wait_for_selector(
        self,
        page_id: str,
        selector: str,
        timeout: int = 10000,
        visible: bool = True,
    ) -> bool:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        try:

            def _wait() -> bool:
                ele = tab.ele(dp_sel, timeout=timeout / 1000)
                return bool(ele)

            return await asyncio.to_thread(_wait)
        except Exception:
            return False

    async def wait_for_url(
        self, page_id: str, pattern: str, timeout: int = 30000
    ) -> bool:
        tab = self._get_tab(page_id)
        deadline = asyncio.get_event_loop().time() + timeout / 1000
        while asyncio.get_event_loop().time() < deadline:
            try:
                if pattern in (tab.url or ""):
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    # ------------------------------------------------------------------
    # file upload
    # ------------------------------------------------------------------

    async def upload_file(
        self, page_id: str, selector: str, file_path: str
    ) -> bool:
        return await self.upload_files(page_id, selector, [file_path])

    async def upload_files(
        self, page_id: str, selector: str, file_paths: list[str]
    ) -> bool:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        normalized = [str(Path(p).resolve()) for p in file_paths if str(p).strip()]
        if not normalized:
            return False
        try:

            def _upload() -> bool:
                ele = tab.ele(dp_sel, timeout=self.timeout)
                if not ele:
                    return False
                ele.input(normalized if len(normalized) > 1 else normalized[0])
                return True

            result = await asyncio.to_thread(_upload)
            if result:
                await asyncio.sleep(self.random_delay())
            return bool(result)
        except Exception as exc:
            self.logger.warning(f"Upload failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # scroll
    # ------------------------------------------------------------------

    async def scroll_to_element(self, page_id: str, selector: str) -> bool:
        tab = self._get_tab(page_id)
        dp_sel = _css(selector)
        try:

            def _scroll() -> bool:
                ele = tab.ele(dp_sel, timeout=5)
                if ele:
                    ele.scroll.to_see()
                    return True
                return False

            return await asyncio.to_thread(_scroll)
        except Exception:
            return False

    async def scroll_to_top(self, page_id: str) -> bool:
        return await self.execute_script(page_id, "window.scrollTo(0, 0); true;") is True

    async def scroll_to_bottom(self, page_id: str) -> bool:
        return (
            await self.execute_script(
                page_id, "window.scrollTo(0, document.body.scrollHeight); true;"
            )
            is True
        )

    async def scroll_by(self, page_id: str, x: int, y: int) -> bool:
        return (
            await self.execute_script(page_id, f"window.scrollBy({x}, {y}); true;")
            is True
        )

    # ------------------------------------------------------------------
    # JS execution
    # ------------------------------------------------------------------

    async def execute_script(self, page_id: str, script: str) -> Any:
        tab = self._get_tab(page_id)
        try:

            def _exec() -> Any:
                return tab.run_js(script, as_expr=True)

            return await asyncio.to_thread(_exec)
        except Exception as exc:
            self.logger.debug(f"Script execute failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # screenshot
    # ------------------------------------------------------------------

    async def take_screenshot(self, page_id: str, path: str) -> bool:
        tab = self._get_tab(page_id)
        try:

            def _shot() -> bool:
                out = Path(path)
                out.parent.mkdir(parents=True, exist_ok=True)
                tab.get_screenshot(path=str(out), full_page=False)
                return True

            return await asyncio.to_thread(_shot)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # cookies  (uses CDP directly for maximum reliability)
    # ------------------------------------------------------------------

    async def get_cookies(self, page_id: str = "") -> list[dict[str, Any]]:
        if self._browser is None:
            return []
        try:
            tab = self._tabs.get(page_id)
            if tab is None:
                tab = self._browser.latest_tab

            def _cookies() -> list[dict[str, Any]]:
                result = tab.run_cdp("Network.getAllCookies")
                return result.get("cookies", [])

            return await asyncio.to_thread(_cookies)
        except Exception:
            return []

    async def add_cookie(self, page_id: str, cookie: dict[str, Any]) -> bool:
        if self._browser is None:
            return False
        try:
            tab = self._tabs.get(page_id) or self._browser.latest_tab

            def _add() -> None:
                tab.run_cdp("Network.setCookie", **cookie)

            await asyncio.to_thread(_add)
            return True
        except Exception:
            return False

    async def delete_cookies(
        self, page_id: str = "", name: str | None = None
    ) -> bool:
        if self._browser is None:
            return False
        try:
            tab = self._tabs.get(page_id) or self._browser.latest_tab

            def _clear() -> None:
                tab.run_cdp("Network.clearBrowserCookies")

            await asyncio.to_thread(_clear)
            return True
        except Exception:
            return False

    async def set_cookies_for_domain(
        self, cookies_str: str, domain: str = ".goofish.com"
    ) -> None:
        if self._browser is None:
            return

        name_re = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
        parsed: dict[str, str] = {}

        for item in re.split(r"[;\n\r]+", str(cookies_str or "")):
            item = item.strip()
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and name_re.fullmatch(k):
                parsed[k] = v

        for line in str(cookies_str or "").splitlines():
            cols = [c.strip() for c in re.split(r"\t+", line) if c.strip()]
            if len(cols) < 2:
                continue
            k, v = cols[0], cols[1]
            if name_re.fullmatch(k):
                parsed[k] = v

        if not parsed:
            self.logger.warning(
                "No valid cookies parsed from seed; skip cookie seeding"
            )
            return

        tab = self._browser.latest_tab

        def _inject() -> int:
            ok = 0
            for k, v in parsed.items():
                try:
                    tab.run_cdp(
                        "Network.setCookie",
                        name=k,
                        value=v,
                        domain=domain,
                        path="/",
                    )
                    ok += 1
                except Exception:
                    continue
            return ok

        accepted = await asyncio.to_thread(_inject)
        if accepted < len(parsed):
            self.logger.warning(
                f"Partially accepted cookies for {domain}: {accepted}/{len(parsed)}"
            )
