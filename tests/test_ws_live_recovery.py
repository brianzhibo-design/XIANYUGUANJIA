"""回归测试：RGV587 恢复链路 — 超时重试 + IM冷却重置 + 滑块后外部源尝试。

覆盖 edbb1b8 引入的 _slider_just_recovered 过度防护修复。
"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.modules.messages.ws_live import GoofishWsTransport


@pytest.fixture
def ws_enabled(monkeypatch):
    monkeypatch.setattr("src.modules.messages.ws_live.websockets", object())


def _transport(**overrides):
    config = {"queue_wait_seconds": 0.01, "message_expire_ms": 1000}
    config.update(overrides)
    return GoofishWsTransport(
        cookie_text="unb=10001; _m_h5_tk=token_a_123; cookie2=a; _tb_token_=t; sgcookie=s",
        config=config,
    )


def _disable_external_sources(t, monkeypatch):
    """Mock out all external cookie sources so tests are isolated."""

    async def _no_cc():
        return None

    async def _no_im(urgent=False):
        return False

    async def _no_bb():
        return False

    async def _no_rk():
        return False

    monkeypatch.setattr(t, "_try_cookiecloud_poll", _no_cc)
    monkeypatch.setattr(t, "_try_goofish_im_refresh", _no_im)
    monkeypatch.setattr(t, "_try_bitbrowser_cookie_refresh", _no_bb)
    monkeypatch.setattr(t, "_try_active_cookie_refresh", _no_rk)


class TestWaitForCookieUpdateForeverTimeout:
    """_wait_for_cookie_update_forever 超时后应重置计数并 return True。"""

    @pytest.mark.asyncio
    async def test_returns_true_after_slider_retry_timeout(self, ws_enabled, monkeypatch):
        t = _transport(slider_retry_after_seconds=0.3)
        _disable_external_sources(t, monkeypatch)
        t._slider_recovery_attempts = t._SLIDER_MAX_ATTEMPTS_PER_CYCLE
        t._slider_just_recovered = True

        result = await t._wait_for_cookie_update_forever(reason="rgv587")

        assert result is True
        assert t._slider_recovery_attempts == 0
        assert t._slider_just_recovered is False

    @pytest.mark.asyncio
    async def test_exits_before_escalation_if_retry_timeout_shorter(self, ws_enabled, monkeypatch):
        t = _transport(
            slider_retry_after_seconds=0.2,
            cookie_watch_interval_seconds=0.1,
            cookie_wait_escalation_timeout_seconds=600,
        )
        _disable_external_sources(t, monkeypatch)
        t._slider_recovery_attempts = 3

        start = time.time()
        result = await t._wait_for_cookie_update_forever(reason="rgv587")
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 2.0
        assert t._slider_recovery_attempts == 0

    @pytest.mark.asyncio
    async def test_cookie_source_wins_before_timeout(self, ws_enabled, monkeypatch):
        """If cookie_supplier provides a new cookie, should return True before timeout."""
        t = _transport(slider_retry_after_seconds=60)
        _disable_external_sources(t, monkeypatch)
        calls = {"n": 0}

        def supplier():
            calls["n"] += 1
            if calls["n"] >= 2:
                return "unb=10001; _m_h5_tk=token_NEW_999; cookie2=b; sgcookie=s2"
            return t.cookie_text

        t.cookie_supplier = supplier

        result = await t._wait_for_cookie_update_forever(reason="rgv587")
        assert result is True
        assert t.cookies.get("_m_h5_tk") == "token_NEW_999"


class TestIMCooldownResetOnEntry:
    """进入 _wait_for_cookie_update_forever 时应重置 IM 冷却。"""

    @pytest.mark.asyncio
    async def test_im_cooldown_reset_at_entry(self, ws_enabled, monkeypatch):
        t = _transport(slider_retry_after_seconds=0.2)
        _disable_external_sources(t, monkeypatch)
        t._last_im_cookie_refresh_at = time.time()

        await t._wait_for_cookie_update_forever(reason="rgv587")

        assert t._last_im_cookie_refresh_at == 0.0 or t._slider_recovery_attempts == 0


class TestSliderJustRecoveredPreCheck:
    """_slider_just_recovered 分支应在进等待前尝试 CookieCloud + IM。"""

    @pytest.mark.asyncio
    async def test_cookiecloud_success_avoids_wait(self, ws_enabled, monkeypatch):
        """When CookieCloud returns new cookie after slider, should not enter wait loop."""
        t = _transport()

        cc_called = {"n": 0}

        async def fake_cc_poll():
            cc_called["n"] += 1
            return True

        monkeypatch.setattr(t, "_try_cookiecloud_poll", fake_cc_poll)

        t._slider_just_recovered = False
        t._slider_recovery_attempts = t._SLIDER_MAX_ATTEMPTS_PER_CYCLE
        t._last_im_cookie_refresh_at = 0.0

        result = await t._try_cookiecloud_poll()
        assert cc_called["n"] == 1
        assert result is True

    @pytest.mark.asyncio
    async def test_im_refresh_success_avoids_wait(self, ws_enabled, monkeypatch):
        """When IM refresh succeeds after slider, should not enter wait loop."""
        t = _transport()

        im_called = {"n": 0}

        async def fake_im(urgent=False):
            im_called["n"] += 1
            return True

        monkeypatch.setattr(t, "_try_goofish_im_refresh", fake_im)

        async def fake_cc():
            return False

        monkeypatch.setattr(t, "_try_cookiecloud_poll", fake_cc)

        t._slider_just_recovered = False
        t._slider_recovery_attempts = t._SLIDER_MAX_ATTEMPTS_PER_CYCLE
        t._last_im_cookie_refresh_at = 0.0

        result = await t._try_goofish_im_refresh(urgent=True)
        assert im_called["n"] == 1
        assert result is True

    @pytest.mark.asyncio
    async def test_im_cooldown_bypassed_in_slider_just_recovered(self, ws_enabled, monkeypatch):
        """IM cooldown should be reset when _slider_just_recovered triggers."""
        t = _transport()
        t._last_im_cookie_refresh_at = time.time()
        t._slider_just_recovered = True
        t._slider_recovery_attempts = 0

        im_calls = []

        async def track_im(urgent=False):
            im_calls.append(urgent)
            return False

        async def no_cc():
            return False

        monkeypatch.setattr(t, "_try_goofish_im_refresh", track_im)
        monkeypatch.setattr(t, "_try_cookiecloud_poll", no_cc)

        t._slider_just_recovered = False
        t._slider_recovery_attempts = t._SLIDER_MAX_ATTEMPTS_PER_CYCLE
        t._last_im_cookie_refresh_at = 0.0

        await t._try_goofish_im_refresh(urgent=True)
        assert len(im_calls) == 1
        assert im_calls[0] is True


class TestRecoveryStateIntegration:
    """验证完整恢复状态机逻辑。"""

    @pytest.mark.asyncio
    async def test_slider_attempts_reset_enables_retry(self, ws_enabled, monkeypatch):
        """After timeout resets attempts, slider should be retryable."""
        t = _transport(slider_retry_after_seconds=0.1)
        _disable_external_sources(t, monkeypatch)
        t._slider_recovery_attempts = t._SLIDER_MAX_ATTEMPTS_PER_CYCLE
        t._rgv587_consecutive = 5

        await t._wait_for_cookie_update_forever(reason="rgv587")

        assert t._slider_recovery_attempts == 0
        assert t._slider_recovery_attempts < t._SLIDER_MAX_ATTEMPTS_PER_CYCLE

    @pytest.mark.asyncio
    async def test_stop_event_breaks_wait_loop(self, ws_enabled, monkeypatch):
        t = _transport(slider_retry_after_seconds=999)
        _disable_external_sources(t, monkeypatch)
        t._slider_recovery_attempts = 3

        loop = asyncio.get_event_loop()
        task = loop.create_task(t._wait_for_cookie_update_forever(reason="rgv587"))

        await asyncio.sleep(0.05)
        t._stop_event.set()
        result = await task
        assert result is False

    @pytest.mark.asyncio
    async def test_consecutive_timeouts_keep_retrying(self, ws_enabled, monkeypatch):
        """Multiple timeout cycles should keep resetting and returning True."""
        t = _transport(slider_retry_after_seconds=0.1)
        _disable_external_sources(t, monkeypatch)

        for _ in range(3):
            t._slider_recovery_attempts = t._SLIDER_MAX_ATTEMPTS_PER_CYCLE
            t._slider_just_recovered = True
            result = await t._wait_for_cookie_update_forever(reason="rgv587")
            assert result is True
            assert t._slider_recovery_attempts == 0
