"""
Cookie 健康监控模块
Cookie Health Monitor

定期探测闲鱼 Cookie 有效性，失效时通过飞书告警。
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from src.core.logger import get_logger

logger = get_logger()

_PROBE_URL = "https://www.goofish.com/im"
_LOGIN_URL_FRAGMENT = "login"
_LOGIN_BODY_MARKERS = ("newlogin", "login-form", "qrcode-img", "请登录", "sign in")
_LOGGED_IN_BODY_MARKERS = ("消息", "im-page", "chatList", "message-list")
_M_H5_TK_EXPIRY_THRESHOLD = 1200


def m_h5_tk_seconds_until_expiry(cookie_text: str) -> float | None:
    """Parse _m_h5_tk expiry from cookie text. Returns seconds left or None."""
    for pair in str(cookie_text or "").split(";"):
        pair = pair.strip()
        if pair.startswith("_m_h5_tk="):
            val = pair[len("_m_h5_tk=") :]
            parts = val.split("_")
            if len(parts) >= 2:
                try:
                    return (int(parts[1]) / 1000.0) - time.time()
                except (ValueError, OverflowError):
                    pass
    return None


class CookieHealthChecker:
    """Cookie 有效性探测 + 飞书告警。

    通过请求闲鱼个人页判断 Cookie 是否有效：
    - HTTP 200 且响应体包含登录态标记 → 有效
    - HTTP 200 但响应体包含登录页标记 → 无效（SPA 登录态丢失）
    - HTTP 302 / 跳转到登录页 / 请求失败 → 无效

    同时检查 _m_h5_tk TTL，即使 HTTP 健康但 token 即将过期也视为不健康。
    集成飞书告警：Cookie 失效时即时通知，恢复后发送恢复消息。
    """

    def __init__(
        self,
        cookie_text: str | None = None,
        *,
        check_interval_seconds: float = 300.0,
        alert_cooldown_seconds: float = 1800.0,
        timeout_seconds: float = 10.0,
        notifier: Any | None = None,
    ):
        self._cookie_text = cookie_text or os.getenv("XIANYU_COOKIE_1", "")
        self._check_interval = max(60.0, float(check_interval_seconds))
        self._alert_cooldown = max(60.0, float(alert_cooldown_seconds))
        self._timeout = max(3.0, float(timeout_seconds))
        self._notifier = notifier

        self._last_check_ts: float = 0.0
        self._last_healthy: bool | None = None
        self._last_alert_ts: float = 0.0
        self._cached_result: dict[str, Any] | None = None

    @property
    def cookie_text(self) -> str:
        return self._cookie_text

    @cookie_text.setter
    def cookie_text(self, value: str) -> None:
        self._cookie_text = value or ""
        # 清除缓存使下次检查立即执行
        self._last_check_ts = 0.0
        self._cached_result = None

    def _needs_check(self) -> bool:
        """是否到了需要再次检查的时间。"""
        if not self._cookie_text:
            return True
        return (time.time() - self._last_check_ts) >= self._check_interval

    def check_sync(self, force: bool = False) -> dict[str, Any]:
        """同步检查 Cookie 健康状态。

        Args:
            force: 强制检查，忽略 TTL 缓存。

        Returns:
            包含 healthy, message, checked_at 等字段的字典。
        """
        if not force and not self._needs_check() and self._cached_result is not None:
            return self._cached_result

        result = self._do_check_sync()
        self._last_check_ts = time.time()
        self._cached_result = result
        return result

    async def check_async(self, force: bool = False) -> dict[str, Any]:
        """异步检查 Cookie 健康状态。

        Args:
            force: 强制检查，忽略 TTL 缓存。

        Returns:
            包含 healthy, message, checked_at 等字段的字典。
        """
        if not force and not self._needs_check() and self._cached_result is not None:
            return self._cached_result

        result = await self._do_check_async()

        # 不健康时尝试级联刷新：闲管家 IM -> CookieCloud -> cookie_grabber
        if not result.get("healthy"):
            refreshed = await self._run_cascade_refresh()
            if refreshed:
                self.cookie_text = os.getenv("XIANYU_COOKIE_1", "")
                result = await self._do_check_async()
                if result.get("healthy"):
                    logger.info("Cookie 级联刷新成功，健康检查已恢复")

        self._last_check_ts = time.time()
        self._cached_result = result

        # 状态变化时触发告警 / 恢复通知（全部失败时飞书告警）
        await self._handle_state_change(result)

        return result

    async def _run_cascade_refresh(self) -> bool:
        """级联刷新：IM (30s 冷却) -> CookieCloud (120s) -> grabber (300s)。任一成功即返回 True。"""
        try:
            from src.modules.messages.ws_live import get_ws_transport_instance, run_cascade_cookie_refresh

            transport = get_ws_transport_instance()
            if transport is None:
                return False
            return await run_cascade_cookie_refresh(transport)
        except Exception as exc:
            logger.debug("Cookie 级联刷新异常: %s", exc)
            return False

    def _do_check_sync(self) -> dict[str, Any]:
        """同步 HTTP 探测 + _m_h5_tk TTL 检查。"""
        if not self._cookie_text:
            return self._build_result(False, "Cookie 未配置")

        ttl_result = self._check_m_h5_tk_ttl()
        if ttl_result is not None:
            return ttl_result

        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=False,
                headers={"Cookie": self._cookie_text, "User-Agent": "Mozilla/5.0"},
            ) as client:
                resp = client.get(_PROBE_URL)
                return self._evaluate_response(resp)
        except httpx.TimeoutException:
            return self._build_result(False, "探测超时")
        except Exception as exc:
            return self._build_result(False, f"探测异常: {type(exc).__name__}")

    async def _do_check_async(self) -> dict[str, Any]:
        """异步 HTTP 探测 + _m_h5_tk TTL 检查。"""
        if not self._cookie_text:
            return self._build_result(False, "Cookie 未配置")

        ttl_result = self._check_m_h5_tk_ttl()
        if ttl_result is not None:
            return ttl_result

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=False,
                headers={"Cookie": self._cookie_text, "User-Agent": "Mozilla/5.0"},
            ) as client:
                resp = await client.get(_PROBE_URL)
                return self._evaluate_response(resp)
        except httpx.TimeoutException:
            return self._build_result(False, "探测超时")
        except Exception as exc:
            return self._build_result(False, f"探测异常: {type(exc).__name__}")

    def _check_m_h5_tk_ttl(self) -> dict[str, Any] | None:
        """检查 _m_h5_tk TTL，过低时直接返回不健康。"""
        ttl = m_h5_tk_seconds_until_expiry(self._cookie_text)
        if ttl is not None and ttl < _M_H5_TK_EXPIRY_THRESHOLD:
            if ttl <= 0:
                return self._build_result(False, f"_m_h5_tk 已过期 (过期 {abs(int(ttl))}s / {abs(int(ttl / 60))} 分钟)")
            return self._build_result(False, f"_m_h5_tk 即将过期 (剩余 {int(ttl)}s / {int(ttl / 60)} 分钟)")
        return None

    def _evaluate_response(self, resp: httpx.Response) -> dict[str, Any]:
        """根据 HTTP 响应 + 响应体判断 Cookie 是否有效。"""
        if resp.status_code in {301, 302, 303, 307, 308}:
            location = resp.headers.get("location", "")
            if _LOGIN_URL_FRAGMENT in location.lower():
                return self._build_result(False, "Cookie 已过期（被重定向到登录页）")
            return self._build_result(False, f"非预期跳转: {location[:80]}")

        if resp.status_code == 200:
            body = ""
            try:
                body = resp.text[:4096]
            except Exception:
                pass
            body_lower = body.lower()
            if body_lower and any(m in body_lower for m in _LOGIN_BODY_MARKERS):
                if not any(m in body_lower for m in _LOGGED_IN_BODY_MARKERS):
                    return self._build_result(False, "Cookie 无效（页面为登录表单）")
            return self._build_result(True, "Cookie 有效")

        if resp.status_code in {403, 401}:
            return self._build_result(False, "Cookie 已过期或无效")

        if resp.status_code == 404:
            return self._build_result(False, "探测页面返回 404，无法判断登录态")

        return self._build_result(False, f"HTTP {resp.status_code}")

    def _build_result(self, healthy: bool, message: str) -> dict[str, Any]:
        return {
            "healthy": healthy,
            "message": message,
            "checked_at": time.time(),
            "previous_healthy": self._last_healthy,
        }

    async def _handle_state_change(self, result: dict[str, Any]) -> None:
        """状态变化时触发飞书告警或恢复通知。"""
        healthy = result["healthy"]
        prev = self._last_healthy
        self._last_healthy = healthy

        if self._notifier is None:
            return

        now = time.time()

        # 从健康变为不健康 → 告警
        if prev is not False and not healthy:
            if (now - self._last_alert_ts) >= self._alert_cooldown:
                msg = (
                    "【闲鱼自动化】⚠️ Cookie 失效告警\n"
                    f"状态: {result['message']}\n"
                    "请尽快在 Dashboard 或 .env 中更新 Cookie\n"
                    "更新后系统将自动恢复运行"
                )
                try:
                    await self._notifier.send_text(msg)
                    self._last_alert_ts = now
                    logger.warning(f"Cookie 健康告警已发送: {result['message']}")
                except Exception as exc:
                    logger.error(f"发送 Cookie 告警失败: {exc}")

        # 从不健康恢复为健康 → 恢复通知
        elif prev is False and healthy:
            msg = "【闲鱼自动化】✅ Cookie 已恢复\nCookie 有效性检测通过，系统恢复正常运行"
            try:
                await self._notifier.send_text(msg)
                logger.info("Cookie 恢复通知已发送")
            except Exception as exc:
                logger.error(f"发送 Cookie 恢复通知失败: {exc}")
