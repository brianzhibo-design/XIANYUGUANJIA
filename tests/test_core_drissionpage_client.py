"""Tests for DrissionPageBrowserClient.

Rewritten from test_core_playwright_client_full.py.
DrissionPage uses sync API via asyncio.to_thread — mocks must be sync (Mock, not AsyncMock).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.error_handler import BrowserError
from src.core.drissionpage_client import DrissionPageBrowserClient


class DummyEle:
    """Mock DrissionPage element (tab.ele() result)."""

    def __init__(self, text="txt", value="val", raise_click=False, raise_scroll=False):
        self.text = text
        self.value = value
        self._raise_click = raise_click
        self._raise_scroll = raise_scroll
        self.scroll = Mock()
        self.scroll.to_see = Mock(side_effect=(RuntimeError("scroll_err") if raise_scroll else None))

    def click(self):
        if self._raise_click:
            raise RuntimeError("click_err")

    def clear(self):
        pass

    def input(self, _val):
        pass


class DummyTab:
    """Mock DrissionPage tab (browser.latest_tab / new_tab)."""

    def __init__(self):
        self.url = "https://old"
        self.raise_on = set()
        self.last_get = None
        self.last_ele_selector = None
        self.last_run_js = None
        self.last_screenshot = None
        self.last_cdp = None
        self.closed = False
        self._ele_count = 2
        self._ele_text = "txt"
        self._ele_value = "val"
        self._run_js_result = "EVAL_OK"

    def get(self, url, timeout=None):
        if "get" in self.raise_on:
            raise RuntimeError("get_err")
        self.last_get = (url, timeout)

    def ele(self, selector, timeout=5):
        if "ele" in self.raise_on:
            raise RuntimeError("ele_err")
        self.last_ele_selector = selector
        raise_scroll = "scroll" in self.raise_on
        raise_click = "click" in self.raise_on
        return DummyEle(
            text=self._ele_text,
            value=self._ele_value,
            raise_click=raise_click,
            raise_scroll=raise_scroll,
        )

    def eles(self, selector, timeout=3):
        if "eles" in self.raise_on:
            raise RuntimeError("eles_err")
        return [DummyEle(text=self._ele_text, value=self._ele_value) for _ in range(self._ele_count)]

    def run_js(self, script, as_expr=True):
        if "run_js" in self.raise_on:
            raise RuntimeError("run_js_err")
        self.last_run_js = script
        return self._run_js_result if "true;" not in script else True

    def get_screenshot(self, path=None, full_page=False):
        if "screenshot" in self.raise_on:
            raise RuntimeError("shot_err")
        self.last_screenshot = (path, full_page)

    def close(self):
        if "close" in self.raise_on:
            raise RuntimeError("close_err")
        self.closed = True

    def run_cdp(self, method, **kwargs):
        self.last_cdp = (method, kwargs)
        if method == "Network.getAllCookies":
            return {"cookies": [{"name": "k"}]}
        return None


@pytest.fixture
def patch_cfg(monkeypatch):
    cfg = SimpleNamespace(
        browser={
            "headless": False,
            "delay": {"min": 0.1, "max": 0.2},
            "viewport": {"width": 800, "height": 600},
            "user_agent": "UA",
        },
        accounts=[{"enabled": False, "cookie": ""}, {"enabled": True, "cookie": "acc_cookie=v"}],
    )
    monkeypatch.setattr("src.core.config.get_config", lambda: cfg)


@pytest.mark.asyncio
async def test_connect_no_drissionpage(monkeypatch, patch_cfg):
    monkeypatch.setattr("src.core.drissionpage_client.Chromium", None)
    monkeypatch.setattr("src.core.drissionpage_client.ChromiumOptions", None)
    c = DrissionPageBrowserClient()
    assert await c.connect() is False


@pytest.mark.asyncio
async def test_connect_success_and_disconnect(monkeypatch, patch_cfg):
    tab = DummyTab()
    browser = Mock()
    browser.new_tab = Mock(return_value=tab)
    browser.latest_tab = tab
    browser.quit = Mock()

    def _fake_chromium(co):
        return browser

    monkeypatch.setattr("src.core.drissionpage_client.Chromium", _fake_chromium)
    monkeypatch.setattr("src.core.drissionpage_client.ChromiumOptions", Mock)
    monkeypatch.setenv("CHROME_EXECUTABLE_PATH", "/tmp/chrome")

    c = DrissionPageBrowserClient({"headless": True, "timeout": 9, "delay_min": 0.0, "delay_max": 0.0})
    c.set_cookies_for_domain = AsyncMock()

    assert await c.connect() is True
    assert c._browser is browser

    c._tabs["dp_abc"] = tab
    assert await c.close_page("dp_abc") is True
    assert tab.closed is True

    await c.disconnect()
    browser.quit.assert_called_once()
    c.set_cookies_for_domain.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_failure_calls_disconnect(monkeypatch, patch_cfg):
    def _raise(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.core.drissionpage_client.Chromium", _raise)
    monkeypatch.setattr("src.core.drissionpage_client.ChromiumOptions", Mock)

    c = DrissionPageBrowserClient()
    c.disconnect = AsyncMock()
    assert await c.connect() is False
    c.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_connection_helpers_and_page_lifecycle(monkeypatch, patch_cfg):
    c = DrissionPageBrowserClient()
    assert await c.is_connected() is False

    async def _conn():
        return True

    c.connect = _conn
    assert await c.ensure_connected() is True

    tab = DummyTab()
    c._browser = Mock()
    c._browser.new_tab = Mock(return_value=tab)
    page_id = await c.new_page()
    assert page_id.startswith("dp_")
    assert await c.ensure_connected() is True

    with pytest.raises(BrowserError):
        c._get_tab("missing")

    assert await c.close_page("none") is False
    bad = DummyTab()
    bad.raise_on.add("close")
    c._tabs["bad"] = bad
    assert await c.close_page("bad") is False


@pytest.mark.asyncio
async def test_page_actions_and_failures(monkeypatch, patch_cfg, tmp_path):
    c = DrissionPageBrowserClient({"timeout": 1, "delay_min": 0.0, "delay_max": 0.0})
    tab = DummyTab()
    c._tabs["p"] = tab
    c._browser = Mock()

    assert await c.navigate("p", "https://new", wait_load=False) is True
    assert tab.last_get[0] == "https://new"

    assert await c.navigate("p", "", wait_load=False) is True
    assert tab.last_get[0] == ""  # DrissionPage passes url as-is; '' stays as ''

    tab.raise_on.add("get")
    assert await c.navigate("p", "x", wait_load=False) is False
    tab.raise_on.discard("get")

    assert await c.click("p", "#a", retry=False) is True
    tab.raise_on.add("click")
    assert await c.click("p", "#a", retry=False) is False
    tab.raise_on.discard("click")

    assert await c.type_text("p", "#i", "abc", clear=True) is True
    assert await c.type_text("p", "#i", "abc", clear=False) is True
    tab.raise_on.add("ele")
    assert await c.type_text("p", "#i", "abc", clear=True) is False
    tab.raise_on.discard("ele")

    tab._ele_count = 3
    assert await c.find_elements("p", ".x") == [
        {"selector": ".x", "index": 0},
        {"selector": ".x", "index": 1},
        {"selector": ".x", "index": 2},
    ]
    assert await c.find_element("p", ".x") == {"selector": ".x", "index": 0}
    tab._ele_count = 0
    assert await c.find_element("p", ".x") is None
    tab.raise_on.add("eles")
    assert await c.find_elements("p", ".x") == []
    tab.raise_on.discard("eles")

    tab._ele_text = "T"
    tab._ele_value = "V"
    assert await c.get_text("p", ".x") == "T"
    assert await c.get_value("p", ".x") == "V"
    tab.raise_on.add("ele")
    assert await c.get_text("p", ".x") is None
    assert await c.get_value("p", ".x") is None
    tab.raise_on.discard("ele")

    assert await c.wait_for_selector("p", ".x", visible=True) is True
    assert await c.wait_for_selector("p", ".x", visible=False) is True
    tab.raise_on.add("ele")
    assert await c.wait_for_selector("p", ".x") is False
    tab.raise_on.discard("ele")

    tab.url = "https://foo/bar"
    assert await c.wait_for_url("p", "foo", timeout=100) is True
    tab.url = "https://other"
    assert await c.wait_for_url("p", "foo", timeout=100) is False

    assert await c.upload_file("p", "#f", str(tmp_path / "a.txt")) is True
    assert await c.upload_files("p", "#f", ["", " "]) is False
    tab.raise_on.add("ele")
    assert await c.upload_files("p", "#f", [str(tmp_path / "b.txt")]) is False
    tab.raise_on.discard("ele")

    assert await c.scroll_to_element("p", ".x") is True
    tab.raise_on.add("scroll")
    assert await c.scroll_to_element("p", ".x") is False
    tab.raise_on.discard("scroll")

    tab._run_js_result = "EVAL_OK"
    assert await c.execute_script("p", "1+1") == "EVAL_OK"
    tab.raise_on.add("run_js")
    assert await c.execute_script("p", "1+1") is None
    tab.raise_on.discard("run_js")

    tab._run_js_result = True
    assert await c.scroll_to_top("p") is True
    assert await c.scroll_to_bottom("p") is True
    assert await c.scroll_by("p", 1, 2) is True

    out = tmp_path / "shots" / "a.png"
    assert await c.take_screenshot("p", str(out)) is True
    tab.raise_on.add("screenshot")
    assert await c.take_screenshot("p", str(out)) is False


@pytest.mark.asyncio
async def test_cookie_helpers_and_set_cookie_parsing(monkeypatch, patch_cfg):
    c = DrissionPageBrowserClient()
    assert await c.get_cookies() == []
    assert await c.add_cookie("", {"a": 1}) is False
    assert await c.delete_cookies() is False
    await c.set_cookies_for_domain("a=b")

    tab = DummyTab()
    c._browser = Mock()
    c._browser.latest_tab = tab
    c._tabs[""] = tab
    assert await c.get_cookies("") == [{"name": "k"}]

    tab.run_cdp = Mock(side_effect=RuntimeError("cookies_err"))
    assert await c.get_cookies("") == []

    tab.run_cdp = Mock(return_value=None)
    assert await c.add_cookie("", {"name": "n"}) is True
    tab.run_cdp = Mock(side_effect=RuntimeError("add_err"))
    assert await c.add_cookie("", {"name": "n"}) is False

    tab.run_cdp = Mock(return_value=None)
    assert await c.delete_cookies("") is True
    tab.run_cdp = Mock(side_effect=RuntimeError("clear_err"))
    assert await c.delete_cookies("") is False

    c.logger = Mock()
    c._browser = Mock()
    c._browser.latest_tab = DummyTab()
    await c.set_cookies_for_domain("invalid line\n@bad=v")
    c.logger.warning.assert_called()

    tab2 = DummyTab()
    c._browser.latest_tab = tab2
    tab2.run_cdp = Mock(return_value=None)
    await c.set_cookies_for_domain("a=1; b=2\nname\tvalue")
    assert tab2.run_cdp.call_count >= 1

    # Partial cookie failure
    tab3 = DummyTab()
    tab3.run_cdp = Mock(side_effect=[RuntimeError("first_fail"), None])
    c._browser.latest_tab = tab3
    c.logger = Mock()
    await c.set_cookies_for_domain("c=3; d=4")
    assert c.logger.warning.call_count >= 1

    c.logger = Mock()
    await c.set_cookies_for_domain("@bad\t1")
    c.logger.warning.assert_called()


def test_random_delay_and_init_cookie_env(monkeypatch, patch_cfg):
    monkeypatch.setenv("XIANYU_COOKIE_1", "env_cookie=v")
    c = DrissionPageBrowserClient({"delay_min": 1.5, "delay_max": 1.5})
    assert c.random_delay() == 1.5
    assert c._cookies_seed == "env_cookie=v"


@pytest.mark.asyncio
async def test_extra_uncovered_branches(monkeypatch, patch_cfg):
    monkeypatch.delenv("XIANYU_COOKIE_1", raising=False)
    monkeypatch.setattr("src.core.drissionpage_client.Chromium", Mock())  # ensure not None for short-circuit
    monkeypatch.setattr("src.core.drissionpage_client.ChromiumOptions", Mock())
    c = DrissionPageBrowserClient()
    assert c._cookies_seed == "acc_cookie=v"

    c._browser = object()
    assert await c.connect() is True

    c2 = DrissionPageBrowserClient()
    async def _no():
        return False

    c2.ensure_connected = _no
    with pytest.raises(BrowserError):
        await c2.new_page()

    c3 = DrissionPageBrowserClient({"delay_min": 0, "delay_max": 0})
    tab = DummyTab()
    c3._tabs["p"] = tab
    c3._browser = Mock()
    assert await c3.navigate("p", "https://ok", wait_load=True) is True

    c4 = DrissionPageBrowserClient()
    c4._tabs = {"a": DummyTab()}
    close_calls = []

    async def _track_close(pid):
        close_calls.append(pid)
        return True

    c4.close_page = _track_close
    await c4.disconnect()
    assert "a" in close_calls
