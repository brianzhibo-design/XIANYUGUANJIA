"""闲鱼 IM WebSocket 通道（参考实战可用链路）。"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import random
import re
import struct
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from src.core.error_handler import BrowserError
from src.core.logger import get_logger
from src.modules.messages.manual_mode import ManualModeStore

_MTOP_APP_KEY = "34839810"
_MTOP_APP_SECRET = "444e9908a51d1cb236a27862abc769c9"

try:
    import websockets
except Exception:  # pragma: no cover - optional dependency path
    websockets = None  # type: ignore[assignment]


def parse_cookie_header(cookie_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in re.split(r";\s*", str(cookie_text or "").strip()):
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = str(key or "").strip()
        value = str(value or "").strip()
        if key:
            result[key] = value
    return result


def generate_sign(timestamp_ms: str, token: str, data: str, app_key: str = _MTOP_APP_KEY) -> str:
    raw = f"{token}&{timestamp_ms}&{app_key}&{data}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def generate_mid() -> str:
    ts = int(time.time() * 1000)
    prefix = random.randint(100, 999)
    return f"{prefix}{ts} 0"


def generate_uuid() -> str:
    return f"-{int(time.time() * 1000)}1"


def generate_device_id(user_id: str) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    out: list[str] = []
    for i in range(36):
        if i in {8, 13, 18, 23}:
            out.append("-")
        elif i == 14:
            out.append("4")
        elif i == 19:
            rv = random.randint(0, 15)
            out.append(chars[(rv & 0x3) | 0x8])
        else:
            out.append(chars[random.randint(0, 15)])
    return "".join(out) + "-" + str(user_id or "")


class MessagePackDecoder:
    """轻量 MessagePack 解码器（仅覆盖当前闲鱼消息场景）。"""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.length = len(data)

    def _read_byte(self) -> int:
        if self.pos >= self.length:
            raise ValueError("Unexpected end of data")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def _read_bytes(self, count: int) -> bytes:
        if self.pos + count > self.length:
            raise ValueError("Unexpected end of data")
        buf = self.data[self.pos : self.pos + count]
        self.pos += count
        return buf

    def _read_uint8(self) -> int:
        return self._read_byte()

    def _read_uint16(self) -> int:
        return struct.unpack(">H", self._read_bytes(2))[0]

    def _read_uint32(self) -> int:
        return struct.unpack(">I", self._read_bytes(4))[0]

    def _read_uint64(self) -> int:
        return struct.unpack(">Q", self._read_bytes(8))[0]

    def _read_int8(self) -> int:
        return struct.unpack(">b", self._read_bytes(1))[0]

    def _read_int16(self) -> int:
        return struct.unpack(">h", self._read_bytes(2))[0]

    def _read_int32(self) -> int:
        return struct.unpack(">i", self._read_bytes(4))[0]

    def _read_int64(self) -> int:
        return struct.unpack(">q", self._read_bytes(8))[0]

    def _read_float32(self) -> float:
        return struct.unpack(">f", self._read_bytes(4))[0]

    def _read_float64(self) -> float:
        return struct.unpack(">d", self._read_bytes(8))[0]

    def _read_string(self, length: int) -> str:
        return self._read_bytes(length).decode("utf-8")

    def _decode_array(self, size: int) -> list[Any]:
        out: list[Any] = []
        for _ in range(size):
            out.append(self.decode_value())
        return out

    def _decode_map(self, size: int) -> dict[Any, Any]:
        out: dict[Any, Any] = {}
        for _ in range(size):
            key = self.decode_value()
            value = self.decode_value()
            out[key] = value
        return out

    def decode_value(self) -> Any:
        b = self._read_byte()
        if b <= 0x7F:
            return b
        if 0x80 <= b <= 0x8F:
            return self._decode_map(b & 0x0F)
        if 0x90 <= b <= 0x9F:
            return self._decode_array(b & 0x0F)
        if 0xA0 <= b <= 0xBF:
            return self._read_string(b & 0x1F)
        if b == 0xC0:
            return None
        if b == 0xC2:
            return False
        if b == 0xC3:
            return True
        if b == 0xC4:
            return self._read_bytes(self._read_uint8())
        if b == 0xC5:
            return self._read_bytes(self._read_uint16())
        if b == 0xC6:
            return self._read_bytes(self._read_uint32())
        if b == 0xCA:
            return self._read_float32()
        if b == 0xCB:
            return self._read_float64()
        if b == 0xCC:
            return self._read_uint8()
        if b == 0xCD:
            return self._read_uint16()
        if b == 0xCE:
            return self._read_uint32()
        if b == 0xCF:
            return self._read_uint64()
        if b == 0xD0:
            return self._read_int8()
        if b == 0xD1:
            return self._read_int16()
        if b == 0xD2:
            return self._read_int32()
        if b == 0xD3:
            return self._read_int64()
        if b == 0xD9:
            return self._read_string(self._read_uint8())
        if b == 0xDA:
            return self._read_string(self._read_uint16())
        if b == 0xDB:
            return self._read_string(self._read_uint32())
        if b == 0xDC:
            return self._decode_array(self._read_uint16())
        if b == 0xDD:
            return self._decode_array(self._read_uint32())
        if b == 0xDE:
            return self._decode_map(self._read_uint16())
        if b == 0xDF:
            return self._decode_map(self._read_uint32())
        if b >= 0xE0:
            return b - 256
        raise ValueError(f"Unknown MessagePack byte: 0x{b:02x}")

    def decode(self) -> Any:
        return self.decode_value()


def decode_sync_payload(raw_text: str) -> Any | None:
    text = "".join(
        ch for ch in str(raw_text or "") if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_"
    )
    if not text:
        return None
    while len(text) % 4 != 0:
        text += "="

    try:
        buf = base64.b64decode(text)
    except Exception:
        try:
            buf = base64.urlsafe_b64decode(text)
        except Exception:
            return None

    try:
        return json.loads(buf.decode("utf-8"))
    except Exception:
        pass

    try:
        return MessagePackDecoder(buf).decode()
    except Exception:
        pass

    return None


def extract_chat_event(message: Any) -> dict[str, Any] | None:
    def _pick(obj: Any, *keys: Any) -> Any:
        if not isinstance(obj, dict):
            return None
        for key in keys:
            if key in obj:
                return obj[key]
        return None

    if not isinstance(message, dict):
        return None
    body = _pick(message, "1", 1)
    if not isinstance(body, dict):
        return None
    content = _pick(body, "10", 10)
    if not isinstance(content, dict):
        return None

    text = str(_pick(content, "reminderContent", "content", "text") or "").strip()
    sender_user_id = str(_pick(content, "senderUserId", "fromUserId", "senderId") or "").strip()
    sender_name = str(_pick(content, "reminderTitle", "senderNick", "senderName") or "").strip()
    chat_ref = str(_pick(body, "2", 2, "cid", "chatId") or "").strip()
    chat_id = chat_ref.split("@")[0] if "@" in chat_ref else chat_ref
    if not text or not sender_user_id or not chat_id:
        return None

    create_time = int(time.time() * 1000)
    try:
        create_time = int(_pick(body, "5", 5, "createTime") or create_time)
    except Exception:
        pass

    reminder_url = str(_pick(content, "reminderUrl", "url") or "")
    item_id = ""
    m = re.search(r"[?&]itemId=(\d+)", reminder_url)
    if m:
        item_id = str(m.group(1))

    return {
        "chat_id": chat_id,
        "sender_user_id": sender_user_id,
        "sender_name": sender_name or "买家",
        "text": text,
        "item_id": item_id,
        "create_time": create_time,
    }


class GoofishWsTransport:
    """闲鱼消息 WebSocket 收发通道。"""

    def __init__(
        self,
        cookie_text: str,
        config: dict[str, Any] | None = None,
        cookie_supplier: Callable[[], str] | None = None,
    ):
        if websockets is None:
            raise BrowserError("WebSocket transport requires `websockets`. Install: pip install websockets")

        self.logger = get_logger()
        self.config = config or {}
        self.base_url = str(self.config.get("base_url", "wss://wss-goofish.dingtalk.com/")).strip()
        self.heartbeat_interval = int(self.config.get("heartbeat_interval_seconds", 15))
        self.heartbeat_timeout = int(self.config.get("heartbeat_timeout_seconds", 30))
        self.reconnect_delay = float(self.config.get("reconnect_delay_seconds", 3.0))
        self.event_expire_ms = int(self.config.get("message_expire_ms", 5 * 60 * 1000))
        self.max_queue_size = int(self.config.get("max_queue_size", 200))
        self.queue_wait_seconds = float(self.config.get("queue_wait_seconds", 0.3))
        self.token_refresh_interval_seconds = int(self.config.get("token_refresh_interval_seconds", 3600))
        self.token_retry_seconds = int(self.config.get("token_retry_seconds", 300))
        self.cookie_watch_interval_seconds = float(self.config.get("cookie_watch_interval_seconds", 5.0))
        self.max_reconnect_delay_seconds = float(self.config.get("max_reconnect_delay_seconds", 90.0))
        self.auth_failure_backoff_seconds = float(
            self.config.get("auth_failure_backoff_seconds", max(30.0, float(self.token_retry_seconds)))
        )
        self.auth_hold_until_cookie_update = bool(self.config.get("auth_hold_until_cookie_update", True))

        self.cookie_supplier = cookie_supplier
        self.cookie_text = ""
        self.cookies: dict[str, str] = {}
        self.my_user_id = ""
        self.device_id = ""
        self._cookie_fp = ""
        self._apply_cookie_text(cookie_text, reason="init")

        manual_timeout = int(self.config.get("manual_mode_timeout", 600))
        manual_resume = int(self.config.get("manual_mode_resume_seconds", 300))
        db_path = os.path.join("data", "manual_mode.db")
        self._manual_mode_store = ManualModeStore(
            db_path, timeout_seconds=manual_timeout, resume_after_seconds=manual_resume
        )
        self._on_manual_takeover: Any | None = None

        from src.modules.messages.bot_sig_store import BotSigStore

        self._bot_sig_store = BotSigStore()
        self._bot_sent_sigs: dict[str, float] = self._bot_sig_store._cache
        self._BOT_SIG_TTL = 7200.0
        self._recent_msgs_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._RECENT_MSGS_CACHE_TTL = 30.0

        self._token: str = ""
        self._token_ts: float = 0.0

        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max(10, self.max_queue_size))
        self._queue_event: asyncio.Event = asyncio.Event()
        self._session_peer: dict[str, str] = {}
        self._peer_to_session: dict[str, str] = {}
        self._nick_to_session: dict[str, str] = {}
        self._seen_event: dict[str, float] = {}

        self._ws: Any | None = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._run_task: asyncio.Task[Any] | None = None
        self._ready: asyncio.Event = asyncio.Event()
        self._last_heartbeat_sent = 0.0
        self._last_heartbeat_ack = 0.0
        self._connect_failures = 0
        self._rgv587_consecutive = 0
        self._active_refresh_401_streak = 0
        self._last_disconnect_reason = ""
        self._cookie_changed = threading.Event()
        self._last_cookie_check: float = 0.0
        self._last_im_refresh_at: float = 0.0
        self._last_haslogin_heartbeat_at: float = 0.0
        self.haslogin_heartbeat_interval = int(self.config.get("haslogin_heartbeat_interval_seconds", 30 * 60))

    def notify_cookie_changed(self) -> None:
        """Thread-safe signal: external cookie update detected."""
        self._cookie_changed.set()

    def _ensure_async_primitives(self) -> None:
        pass

    def _apply_cookie_text(self, cookie_text: str, reason: str = "") -> bool:
        text = str(cookie_text or "").strip()
        if not text:
            raise BrowserError("Invalid XIANYU_COOKIE_1. Missing cookie text.")

        parsed = parse_cookie_header(text)
        user_id = str(parsed.get("unb", "") or "").strip()
        if not user_id:
            raise BrowserError("Invalid XIANYU_COOKIE_1. Missing `unb`.")

        fingerprint = hashlib.sha1(text.encode("utf-8")).hexdigest()
        changed = fingerprint != self._cookie_fp
        self.cookie_text = text
        self.cookies = parsed
        self.my_user_id = user_id
        self.device_id = generate_device_id(self.my_user_id)
        self._cookie_fp = fingerprint
        if changed:
            self._token = ""
            self._token_ts = 0.0
            self._last_cookie_applied_at = time.time()
            if reason:
                self.logger.info(
                    f"WS cookie applied ({reason}), uid={self.my_user_id[:10]}..., fields={len(self.cookies)}"
                )
        return changed

    def _maybe_reload_cookie(self, reason: str = "") -> bool:
        supplier = self.cookie_supplier
        if supplier is None:
            return False
        try:
            latest = str(supplier() or "").strip()
        except Exception as exc:
            self.logger.debug(f"WS cookie supplier failed: {exc}")
            return False
        if not latest:
            return False

        latest_fp = hashlib.sha1(latest.encode("utf-8")).hexdigest()
        if latest_fp == self._cookie_fp:
            return False

        try:
            changed = self._apply_cookie_text(latest, reason=reason or "reload")
            if changed:
                # 清理映射，避免新登录账号复用旧会话的对端映射
                self._session_peer.clear()
                self._seen_event.clear()
            return changed
        except Exception as exc:
            self.logger.warning(f"WS cookie reload ignored ({reason}): {exc}")
            return False

    @staticmethod
    def _is_auth_related_error(exc: Exception) -> bool:
        lowered = str(exc or "").lower()
        markers = (
            "fail_sys_user_validate",
            "rgv587",
            "token api failed",
            "cookie missing `_m_h5_tk`",
            "invalid xianyu_cookie_1",
            "http 400",
            "http 401",
            "http 403",
            "forbidden",
            "unauthorized",
        )
        return any(marker in lowered for marker in markers)

    def _next_reconnect_delay(self, auth_error: bool = False) -> float:
        if auth_error:
            return max(5.0, float(self.auth_failure_backoff_seconds))
        base = max(0.5, float(self.reconnect_delay))
        delay = base * (2 ** min(self._connect_failures, 5))
        return min(delay, max(5.0, float(self.max_reconnect_delay_seconds)))

    async def _wait_for_cookie_update(self, timeout_seconds: float) -> bool:
        deadline = time.time() + max(1.0, float(timeout_seconds))
        interval = max(1.0, float(self.cookie_watch_interval_seconds))
        while time.time() < deadline and not self._stop_event.is_set():
            if self._cookie_changed.is_set():
                self._cookie_changed.clear()
            if self._maybe_reload_cookie(reason="watch"):
                return True
            await asyncio.sleep(min(interval, max(0.5, deadline - time.time())))
        return False

    async def _wait_for_cookie_update_forever(self) -> bool:
        interval = max(1.0, float(self.cookie_watch_interval_seconds))
        cc_poll_interval = 30.0
        cc_last_poll = 0.0
        cc_not_configured = False
        fp_poll_interval = 120.0
        fp_last_poll = 0.0
        fp_not_configured = False
        im_poll_interval = 90.0
        im_last_poll = 0.0
        rk_poll_interval = 180.0
        rk_last_poll = 0.0
        wait_start = time.time()
        escalation_notified = False
        escalation_timeout = float(self.config.get("cookie_wait_escalation_timeout_seconds", 10 * 60))
        self.logger.info("进入 Cookie 更新等待循环 (检测: env/config, CookieCloud, 指纹浏览器, 闲管家IM, rookiepy)")
        while not self._stop_event.is_set():
            if self._cookie_changed.is_set():
                self._cookie_changed.clear()
            if self._maybe_reload_cookie(reason="watch"):
                return True
            now = time.time()

            if not escalation_notified and (now - wait_start) >= escalation_timeout:
                escalation_notified = True
                elapsed_min = int((now - wait_start) / 60)
                self.logger.warning(f"Cookie 等待已超过 {elapsed_min} 分钟，所有自动恢复手段未成功")
                try:
                    from src.core.notify import send_system_notification

                    send_system_notification(
                        f"【闲鱼自动化】⚠️ Cookie 等待已超 {elapsed_min} 分钟\n"
                        "所有自动恢复手段均未成功（CookieCloud/闲管家IM/浏览器DB/滑块验证）。\n"
                        "请手动打开 Dashboard 更新 Cookie，或确保闲管家IM正在运行。",
                        event="cookie_expire",
                    )
                except Exception:
                    pass

            if not cc_not_configured and (now - cc_last_poll) >= cc_poll_interval:
                cc_last_poll = now
                refreshed = await self._try_cookiecloud_poll()
                if refreshed is True:
                    return True
                if refreshed is None:
                    cc_not_configured = True

            if (now - im_last_poll) >= im_poll_interval:
                im_last_poll = now
                if await self._try_goofish_im_refresh(urgent=True):
                    self.logger.info("Cookie wait: 闲管家IM刷新成功")
                    return True

            if (now - rk_last_poll) >= rk_poll_interval:
                rk_last_poll = now
                if await self._try_active_cookie_refresh():
                    self.logger.info("Cookie wait: rookiepy主动刷新成功")
                    return True

            if not fp_not_configured and (now - fp_last_poll) >= fp_poll_interval:
                fp_last_poll = now
                recovered = await self._try_slider_recovery()
                if recovered:
                    return True
                slider_cfg = self.config.get("slider_auto_solve", {})
                fp_cfg = slider_cfg.get("fingerprint_browser", {}) if isinstance(slider_cfg, dict) else {}
                if not (isinstance(fp_cfg, dict) and fp_cfg.get("enabled")):
                    fp_not_configured = True
            await asyncio.sleep(interval)
        return False

    async def _try_cookiecloud_poll(self) -> bool | None:
        """Poll CookieCloud for fresh cookies. Returns True=applied, False=no change, None=not configured."""
        try:
            from src.core.cookie_grabber import CookieGrabber

            asyncio.get_running_loop()
            grabber = CookieGrabber()

            os.environ.get("COOKIE_CLOUD_HOST", "").strip()
            uuid_val = os.environ.get("COOKIE_CLOUD_UUID", "").strip()
            pwd = os.environ.get("COOKIE_CLOUD_PASSWORD", "").strip()
            if not uuid_val or not pwd:
                return None

            cookie = await grabber._grab_from_cookiecloud()
            if not cookie:
                return False

            new_fp = hashlib.sha1(cookie.encode("utf-8")).hexdigest()
            if new_fp == self._cookie_fp:
                return False

            changed = self._apply_cookie_text(cookie, reason="cookiecloud_poll")
            if changed:
                os.environ["XIANYU_COOKIE_1"] = cookie
                self._session_peer.clear()
                self._seen_event.clear()
                self.logger.info("CookieCloud poll: new cookie applied")
            return changed
        except Exception as exc:
            self.logger.debug(f"CookieCloud poll failed: {exc}")
            return False

    _IM_REFRESH_COOLDOWN = 60.0
    _last_im_cookie_refresh_at: float = 0.0

    async def _try_goofish_im_refresh(self, urgent: bool = False) -> bool:
        """从闲管家IM Electron应用直接读取最新Cookie（首选恢复方式）。

        内置 60s 冷却期，避免 RGV587 场景下无限快速循环。
        urgent=True 时使用更低的 min_ttl (60s)，接受短 TTL 的 cookie。
        """
        now = time.time()
        if (now - self._last_im_cookie_refresh_at) < self._IM_REFRESH_COOLDOWN:
            return False

        try:
            from src.core.goofish_im_cookie import merge_cookies, read_goofish_im_cookies
        except ImportError:
            return False

        self._last_im_cookie_refresh_at = now

        min_ttl = 60 if urgent else 300
        result = read_goofish_im_cookies(user_id=self.my_user_id, min_ttl=min_ttl)
        if not result:
            self.logger.debug("goofish_im refresh: no valid cookies from IM app")
            return False

        if result.get("low_ttl_warning"):
            self.logger.warning(f"goofish_im refresh: using low-TTL cookie (urgent={urgent})")

        existing_cookie = os.environ.get("XIANYU_COOKIE_1", "") or self.cookie_text
        merged = merge_cookies(result["cookies"], existing_cookie)

        changed = self._apply_cookie_text(merged, reason="goofish_im")
        if changed:
            self._last_cookie_applied_at = time.time()
            os.environ["XIANYU_COOKIE_1"] = merged
            self._session_peer.clear()
            self._seen_event.clear()
            ttl = result.get("m_h5_tk_ttl")
            ttl_str = f", _m_h5_tk TTL={ttl:.0f}s" if ttl else ""
            self.logger.info(f"goofish_im refresh succeeded{ttl_str}")
        return changed

    async def _try_active_cookie_refresh(self) -> bool:
        """主动调用 rookiepy 从浏览器 DB 读取最新 Cookie（含 _m_h5_tk）。

        在 auth 失败时调用，避免因 _m_h5_tk 过期而永久挂起。
        rookiepy 同步读取在 executor 中运行；如需 Playwright 补全 _m_h5_tk，
        在当前事件循环中直接 await，避免嵌套事件循环。
        """
        self.logger.info("WS auth failed, attempting active cookie refresh via rookiepy...")
        try:
            loop = asyncio.get_running_loop()
            new_cookie = await loop.run_in_executor(None, self._sync_rookiepy_read_only)
        except Exception as exc:
            self.logger.info(f"Active cookie refresh failed: {exc}")
            return False

        if not new_cookie:
            self.logger.info("Active cookie refresh: no cookie obtained from browser DB")
            return False

        try:
            from src.core.cookie_grabber import CookieGrabber

            if not CookieGrabber._has_session_fields(new_cookie):
                self.logger.info("Active cookie refresh: missing session fields, trying Playwright enrichment...")
                grabber = CookieGrabber()
                enriched = await grabber._enrich_with_session_cookies(new_cookie)
                if enriched:
                    new_cookie = enriched
        except Exception as exc:
            self.logger.debug(f"Playwright session enrichment failed: {exc}")

        new_fp = hashlib.sha1(new_cookie.encode("utf-8")).hexdigest()
        if new_fp == self._cookie_fp:
            self.logger.debug("Active cookie refresh: cookie unchanged (same fingerprint)")
            return False

        try:
            changed = self._apply_cookie_text(new_cookie, reason="active_refresh")
            if changed:
                os.environ["XIANYU_COOKIE_1"] = new_cookie
                self._session_peer.clear()
                self._seen_event.clear()
                self.logger.info("Active cookie refresh succeeded, new cookie applied")
            return changed
        except Exception as exc:
            self.logger.warning(f"Active cookie refresh apply failed: {exc}")
            return False

    @staticmethod
    def _sync_rookiepy_read_only() -> str | None:
        """同步调用 rookiepy 读取浏览器 Cookie DB（纯同步，不启动 Playwright）。"""
        try:
            from src.core.cookie_grabber import CookieGrabber
        except ImportError:
            return None

        import asyncio as _asyncio

        _loop = _asyncio.new_event_loop()
        try:
            grabber = CookieGrabber()
            return _loop.run_until_complete(grabber._grab_from_browser_db())
        except Exception:
            return None
        finally:
            _loop.close()

    def _send_risk_control_notification(self) -> None:
        """Send alert via Feishu/WeCom when RGV587 triggers infinite wait."""
        try:
            from src.core.notify import send_system_notification

            slider_cfg = self.config.get("slider_auto_solve", {})
            slider_on = bool(slider_cfg.get("enabled")) if isinstance(slider_cfg, dict) else False
            cc_uuid = os.environ.get("COOKIE_CLOUD_UUID", "").strip()
            cc_pwd = os.environ.get("COOKIE_CLOUD_PASSWORD", "").strip()
            if not cc_uuid or not cc_pwd:
                try:
                    from src.dashboard.config_service import read_system_config

                    cc_cfg = read_system_config().get("cookie_cloud", {})
                    if isinstance(cc_cfg, dict):
                        cc_uuid = cc_uuid or str(cc_cfg.get("cookie_cloud_uuid", "")).strip()
                        cc_pwd = cc_pwd or str(cc_cfg.get("cookie_cloud_password", "")).strip()
                except Exception:
                    pass
            cc_on = bool(cc_uuid and cc_pwd)

            lines = [
                "【闲鱼自动化】⚠️ 风控滑块触发 (RGV587)",
                f"连续触发次数: {self._rgv587_consecutive}",
            ]
            if slider_on:
                lines.append("系统将自动尝试滑块验证，请稍候...")
                lines.append("如自动验证失败，会弹出浏览器窗口，请手动完成滑块拖动")
            else:
                lines.append("请在浏览器打开 https://www.goofish.com/im 完成滑块验证")
            if cc_on:
                lines.append("验证后在 CookieCloud 扩展点「手动同步」，系统将秒级自动恢复")
            else:
                lines.append("验证后请手动复制 Cookie 粘贴到系统中")
                lines.append("提示：配置 CookieCloud 可免手动复制，实现秒级自动恢复")

            send_system_notification("\n".join(lines), event="risk_control")
        except Exception:
            pass

    _last_slider_recovery_at: float = 0.0
    _last_cookie_applied_at: float = 0.0
    _SLIDER_RECOVERY_COOLDOWN = 60.0
    _slider_recovery_attempts: int = 0
    _SLIDER_MAX_ATTEMPTS_PER_CYCLE = 3
    _RGV587_BACKOFF_CAP = 300.0

    def _record_slider_events(self, result: dict[str, Any], trigger_source: str) -> None:
        """Persist slider attempt data to SliderEventStore."""
        try:
            from src.core.slider_store import SliderEventStore

            store = SliderEventStore.get_instance()

            prev_ts = store.get_last_cookie_apply_ts()
            cookie_ttl = None
            if self._last_cookie_applied_at > 0:
                cookie_ttl = int(time.time() - self._last_cookie_applied_at)

            attempts = result.get("attempts", [])
            if not attempts:
                store.record_event(
                    trigger_source=trigger_source,
                    rgv587_consecutive=self._rgv587_consecutive,
                    browser_strategy=result.get("browser_strategy", "none"),
                    browser_connect_ms=result.get("browser_connect_ms"),
                    result="error" if result.get("error") else "no_attempts",
                    error_message=result.get("error"),
                    total_duration_ms=result.get("total_duration_ms"),
                    prev_cookie_applied_at=prev_ts,
                    cookie_ttl_seconds=cookie_ttl,
                )
                return

            for att in attempts:
                cookie_applied = bool(result.get("cookie")) and att is attempts[-1]
                cookie_str = result.get("cookie") or ""
                cookie_keys = (
                    {p.split("=")[0].strip() for p in cookie_str.split(";") if "=" in p} if cookie_str else set()
                )

                store.record_event(
                    trigger_source=trigger_source,
                    rgv587_consecutive=self._rgv587_consecutive,
                    browser_strategy=att.get("browser_strategy", result.get("browser_strategy", "none")),
                    browser_connect_ms=att.get("browser_connect_ms", result.get("browser_connect_ms")),
                    attempt_num=att.get("attempt_num", 0),
                    slider_type=att.get("slider_type"),
                    nc_track_width=att.get("nc_track_width"),
                    nc_drag_distance=att.get("nc_drag_distance"),
                    puzzle_bg_found=int(att.get("puzzle_bg_found", False)),
                    puzzle_slice_found=int(att.get("puzzle_slice_found", False)),
                    puzzle_gap_x=att.get("puzzle_gap_x"),
                    puzzle_match_score=att.get("puzzle_match_score"),
                    result=att.get("result", "failed"),
                    fail_reason=att.get("fail_reason"),
                    screenshot_path=att.get("screenshot_path"),
                    cookie_applied=int(cookie_applied),
                    cookie_fields_count=len(cookie_keys) if cookie_applied else None,
                    cookie_has_h5tk=int("_m_h5_tk" in cookie_keys) if cookie_applied else None,
                    total_duration_ms=result.get("total_duration_ms"),
                    prev_cookie_applied_at=prev_ts,
                    cookie_ttl_seconds=cookie_ttl,
                )
        except Exception as exc:
            self.logger.debug(f"Failed to record slider events: {exc}")

    async def _try_slider_recovery(self, trigger_source: str = "rgv587") -> bool:
        """Phase 2+3: open browser for slider verification, optionally auto-solve."""
        now = time.time()
        if now - self._last_slider_recovery_at < self._SLIDER_RECOVERY_COOLDOWN:
            elapsed = now - self._last_slider_recovery_at
            self.logger.info(
                f"Slider recovery cooldown: {self._SLIDER_RECOVERY_COOLDOWN - elapsed:.0f}s remaining, skipping"
            )
            return False
        self._last_slider_recovery_at = now

        try:
            from src.core.slider_solver import try_slider_recovery
        except ImportError:
            self.logger.debug("slider_solver not available, skipping auto slider recovery")
            return False
        try:
            result = await try_slider_recovery(
                cookie_text=self.cookie_text,
                config=self.config,
                logger=self.logger,
            )
            if not result:
                return False

            self._record_slider_events(result, trigger_source)

            cookie_str = result.get("cookie")
            if not cookie_str:
                return False

            _required = {"sgcookie", "unb", "cookie2", "_m_h5_tk"}
            cookie_keys = {p.split("=")[0].strip() for p in cookie_str.split(";") if "=" in p}
            missing = _required - cookie_keys
            is_complete = not missing

            if is_complete:
                changed = self._apply_cookie_text(cookie_str, reason="slider_recovery")
                if changed:
                    self._last_cookie_applied_at = time.time()
                    os.environ["XIANYU_COOKIE_1"] = cookie_str
                    self._session_peer.clear()
                    self._seen_event.clear()
                    try:
                        from src.core.notify import send_system_notification

                        send_system_notification(
                            "【闲鱼自动化】✅ 风控滑块验证已通过\nCookie 已自动恢复，WS 即将重连",
                            event="risk_control",
                        )
                    except Exception:
                        pass
                return changed

            self.logger.info(
                f"Slider recovery: cookie incomplete (missing: {missing}), "
                f"got {len(cookie_keys)} fields. Trying hasLogin to generate _m_h5_tk..."
            )

            if "_m_h5_tk" in missing and len(missing) == 1:
                self._apply_cookie_text(cookie_str, reason="slider_partial")
                os.environ["XIANYU_COOKIE_1"] = self.cookie_text
                try:
                    hl_ok = await self._preflight_has_login()
                    if hl_ok and self.cookies.get("_m_h5_tk"):
                        self.logger.info("hasLogin 补全 _m_h5_tk 成功，WS 即将重连")
                        self._last_cookie_applied_at = time.time()
                        self._session_peer.clear()
                        self._seen_event.clear()
                        try:
                            from src.core.notify import send_system_notification

                            send_system_notification(
                                "【闲鱼自动化】✅ hasLogin 补全 _m_h5_tk 成功\nCookie 已自动恢复，WS 即将重连",
                                event="risk_control",
                            )
                        except Exception:
                            pass
                        return True
                    self.logger.info("hasLogin 未能补全 _m_h5_tk，回退 CookieCloud 轮询")
                except Exception as exc:
                    self.logger.info(f"hasLogin 补全失败: {exc}")

            try:
                from src.core.notify import send_system_notification

                send_system_notification(
                    "【闲鱼自动化】⚠️ 滑块页面无验证码，但提取的 Cookie 不完整\n"
                    "缺少字段: " + ", ".join(sorted(missing)) + "\n"
                    "请在 CookieCloud 扩展中点「手动同步」或在闲鱼网页重新登录",
                    event="risk_control",
                )
            except Exception:
                pass
            for _ in range(20):
                refreshed = await self._try_cookiecloud_poll()
                if refreshed is True:
                    self._last_cookie_applied_at = time.time()
                    self.logger.info("CookieCloud provided complete cookie after slider solve")
                    return True
                await asyncio.sleep(15)
            return False
        except Exception as exc:
            self.logger.info(f"Slider recovery failed: {exc}")
            return False

    def _base_headers(self, *, include_cookie: bool = False) -> dict[str, str]:
        h: dict[str, str] = {
            "accept": "application/json",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "origin": "https://www.goofish.com",
            "pragma": "no-cache",
            "referer": "https://www.goofish.com/",
            "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
        }
        if include_cookie:
            h["Cookie"] = self.cookie_text
        return h

    def _dedup_cookies(self) -> None:
        """去除 self.cookies 中的重复项并重建 cookie_text。

        对齐 XianyuAutoAgent 的 clear_duplicate_cookies() 逻辑。
        """
        deduped: dict[str, str] = {}
        for k, v in self.cookies.items():
            k = str(k).strip()
            v = str(v).strip()
            if k and v:
                deduped[k] = v
        if deduped != self.cookies:
            self.cookies = deduped
            self.cookie_text = "; ".join(f"{k}={v}" for k, v in deduped.items())

    def _absorb_set_cookies(self, client: httpx.AsyncClient, reason: str = "") -> bool:
        """Merge Set-Cookie values from an httpx client into self.cookies."""
        merged = dict(self.cookies)
        changed = False
        for ck in client.cookies.jar:
            name = str(getattr(ck, "name", "") or "").strip()
            value = str(getattr(ck, "value", "") or "").strip()
            if not name or not value:
                continue
            if merged.get(name) != value:
                changed = True
            merged[name] = value
        if changed:
            merged_text = "; ".join(f"{k}={v}" for k, v in merged.items() if str(k).strip() and str(v).strip())
            self._apply_cookie_text(merged_text, reason=reason)
            self._dedup_cookies()
            os.environ["XIANYU_COOKIE_1"] = self.cookie_text
            self.logger.debug(f"Absorbed Set-Cookie from {reason}")
        return changed

    def _absorb_set_cookies_from_resp(self, resp: httpx.Response, reason: str = "") -> bool:
        """Merge Set-Cookie values from a single httpx response."""
        merged = dict(self.cookies)
        changed = False
        for name, value in resp.cookies.items():
            n = str(name or "").strip()
            v = str(value or "").strip()
            if not n or not v:
                continue
            if merged.get(n) != v:
                changed = True
            merged[n] = v
        if changed:
            merged_text = "; ".join(f"{k}={v}" for k, v in merged.items() if str(k).strip() and str(v).strip())
            self._apply_cookie_text(merged_text, reason=reason)
            self._dedup_cookies()
            os.environ["XIANYU_COOKIE_1"] = self.cookie_text
            self.logger.debug(f"Absorbed Set-Cookie from response ({reason})")
        return changed

    async def _preflight_has_login(self) -> bool:
        """调用 hasLogin 预热会话，并吸收服务端补发的关键 cookie。

        对齐 XianyuAutoAgent: 只通过 cookies 参数传 cookie，不手动设 cookie header，
        并在完成后执行去重。
        """
        params = {"appName": "xianyu", "fromSite": "77"}
        data = {
            "hid": self.cookies.get("unb", ""),
            "ltl": "true",
            "appName": "xianyu",
            "appEntrance": "web",
            "_csrf_token": self.cookies.get("XSRF-TOKEN", ""),
            "umidToken": "",
            "hsiz": self.cookies.get("cookie2", ""),
            "bizParams": "taobaoBizLoginFrom=web",
            "mainPage": "false",
            "isMobile": "false",
            "lang": "zh_CN",
            "returnUrl": "",
            "fromSite": "77",
            "isIframe": "true",
            "documentReferer": "https://www.goofish.com/",
            "defaultView": "hasLogin",
            "umidTag": "SERVER",
            "deviceId": self.cookies.get("cna", "") or self.device_id,
        }

        headers = self._base_headers()
        async with httpx.AsyncClient(
            timeout=12.0,
            headers=headers,
            cookies=self.cookies,
            follow_redirects=True,
        ) as client:
            resp = await client.post("https://passport.goofish.com/newlogin/hasLogin.do", params=params, data=data)
            try:
                payload = resp.json()
            except Exception:
                payload = {}

            content = payload.get("content", {}) if isinstance(payload, dict) else {}
            success = bool(content.get("success")) if isinstance(content, dict) else False
            if not success:
                return False

            merged = dict(self.cookies)
            for ck in client.cookies.jar:
                name = str(getattr(ck, "name", "") or "").strip()
                value = str(getattr(ck, "value", "") or "").strip()
                if not name or not value:
                    continue
                merged[name] = value

            if merged != self.cookies:
                merged_text = "; ".join(f"{k}={v}" for k, v in merged.items() if str(k).strip() and str(v).strip())
                self._apply_cookie_text(merged_text, reason="has_login_refresh")
                self._dedup_cookies()
                os.environ["XIANYU_COOKIE_1"] = self.cookie_text
            return True

    def _m_h5_tk_seconds_until_expiry(self) -> float | None:
        """Parse the expiry timestamp from _m_h5_tk (format: {hex}_{epoch_ms}).

        Returns seconds until expiry, or None if unparseable.
        """
        raw = str(self.cookies.get("_m_h5_tk", "") or "")
        parts = raw.split("_")
        if len(parts) < 2:
            return None
        try:
            expire_ms = int(parts[1])
            return (expire_ms / 1000.0) - time.time()
        except (ValueError, OverflowError):
            return None

    async def _fetch_token(self) -> str:
        self._maybe_reload_cookie(reason="token_fetch")

        ttl = self._m_h5_tk_seconds_until_expiry()
        if ttl is not None and ttl < 600:
            self.logger.info(f"_m_h5_tk expires in {ttl:.0f}s, proactively refreshing via hasLogin")
            try:
                await self._preflight_has_login()
            except Exception as exc:
                self.logger.debug(f"Proactive hasLogin refresh failed: {exc}")
        else:
            try:
                await self._preflight_has_login()
            except Exception as exc:
                self.logger.debug(f"WS hasLogin preflight failed: {exc}")

        now = time.time()
        if self._token and (now - self._token_ts) < self.token_refresh_interval_seconds:
            return self._token

        max_attempts = max(1, int(self.config.get("token_max_attempts", 3)))
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            token_cookie = str(self.cookies.get("_m_h5_tk", "") or "")
            token_seed = token_cookie.split("_")[0].strip()
            if not token_seed:
                self._maybe_reload_cookie(reason="missing_m_h5_tk")
                token_cookie = str(self.cookies.get("_m_h5_tk", "") or "")
                token_seed = token_cookie.split("_")[0].strip()
                if not token_seed:
                    raise BrowserError("Cookie missing `_m_h5_tk`.")

            t = str(int(time.time() * 1000))
            data_val = json.dumps(
                {"appKey": _MTOP_APP_SECRET, "deviceId": self.device_id},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            params = {
                "jsv": "2.7.2",
                "appKey": _MTOP_APP_KEY,
                "t": t,
                "sign": generate_sign(t, token_seed, data_val),
                "v": "1.0",
                "type": "originaljson",
                "accountSite": "xianyu",
                "dataType": "json",
                "timeout": "20000",
                "api": "mtop.taobao.idlemessage.pc.login.token",
                "sessionOption": "AutoLoginOnly",
                "spm_cnt": "a21ybx.im.0.0",
            }

            headers = self._base_headers()
            data = {"data": data_val}
            try:
                async with httpx.AsyncClient(
                    timeout=12.0,
                    headers=headers,
                    cookies=self.cookies,
                ) as client:
                    resp = await client.post(
                        "https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/",
                        params=params,
                        data=data,
                    )
                    payload = resp.json()

                    self._absorb_set_cookies(client, reason="token_api")
            except Exception as exc:
                last_error = BrowserError(f"Token API request failed: {exc}")
                await asyncio.sleep(min(2.0 * attempt, 6.0))
                continue

            ret = payload.get("ret", []) if isinstance(payload, dict) else []
            if not any("SUCCESS::调用成功" in str(item) for item in ret):
                ret_text = " | ".join(str(item) for item in ret)
                last_error = BrowserError(f"Token API failed: {ret}")

                self._absorb_set_cookies_from_resp(resp, reason="token_api_fail")

                if "FAIL_SYS_USER_VALIDATE" in ret_text or "RGV587" in ret_text:
                    self._maybe_reload_cookie(reason="token_ret_fail")
                    try:
                        await self._preflight_has_login()
                    except Exception as exc:
                        self.logger.debug(f"WS hasLogin retry failed: {exc}")
                    # 认证/风控错误快速失败，交由上层进入“仅等待 Cookie 更新”流程，避免持续重试加重风险。
                    break
                if attempt < max_attempts:
                    await asyncio.sleep(min(2.0 * attempt, 6.0))
                    continue
                break

            token = str(payload.get("data", {}).get("accessToken", "") or "").strip()
            if not token:
                last_error = BrowserError("Token API success but accessToken missing.")
                if attempt < max_attempts:
                    await asyncio.sleep(min(2.0 * attempt, 6.0))
                    continue
                break

            self._token = token
            self._token_ts = time.time()
            return token

        if last_error is not None:
            raise last_error
        raise BrowserError("Token fetch failed.")

    async def _send_reg(self) -> None:
        if self._ws is None:
            raise BrowserError("WebSocket not connected.")
        token = await self._fetch_token()
        reg_msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": _MTOP_APP_SECRET,
                "token": token,
                "ua": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5)"
                ),
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid(),
            },
        }
        await self._ws.send(json.dumps(reg_msg, ensure_ascii=False))
        await asyncio.sleep(1.0)
        ack_diff = {
            "lwp": "/r/SyncStatus/ackDiff",
            "headers": {"mid": generate_mid()},
            "body": [
                {
                    "pipeline": "sync",
                    "tooLong2Tag": "PNM,1",
                    "channel": "sync",
                    "topic": "sync",
                    "highPts": 0,
                    "pts": int(time.time() * 1000) * 1000,
                    "seq": 0,
                    "timestamp": int(time.time() * 1000),
                }
            ],
        }
        await self._ws.send(json.dumps(ack_diff, ensure_ascii=False))

    async def _send_heartbeat(self) -> None:
        if self._ws is None:
            return
        msg = {"lwp": "/!", "headers": {"mid": generate_mid()}}
        await self._ws.send(json.dumps(msg, ensure_ascii=False))
        self._last_heartbeat_sent = time.time()

    async def _ack_packet(self, packet: dict[str, Any]) -> None:
        if self._ws is None:
            return
        headers = packet.get("headers", {})
        if not isinstance(headers, dict):
            return
        mid = headers.get("mid")
        if not mid:
            return
        ack = {"code": 200, "headers": {"mid": mid, "sid": headers.get("sid", "")}}
        for key in ("app-key", "ua", "dt"):
            if key in headers:
                ack["headers"][key] = headers[key]
        await self._ws.send(json.dumps(ack, ensure_ascii=False))

    def _cleanup_seen(self) -> None:
        now = time.time()
        expire = max(120.0, self.event_expire_ms / 1000.0 * 2.0)
        dead = [k for k, ts in self._seen_event.items() if (now - ts) > expire]
        for k in dead:
            self._seen_event.pop(k, None)
        self._cleanup_bot_sigs()
        stale_cache = [
            k for k, (ts, _) in self._recent_msgs_cache.items() if (now - ts) > self._RECENT_MSGS_CACHE_TTL * 4
        ]
        for k in stale_cache:
            self._recent_msgs_cache.pop(k, None)

    _SYSTEM_MSG_PATTERNS: list[str] = [
        # 价格 / 付款
        "已修改价格",
        "我已修改价格",
        "等待你付款",
        "请确认价格",
        "待付款",
        "付款成功",
        "已拍下",
        "买家已付款",
        # 发货 / 物流
        "已发货",
        "你已发货",
        "等待你发货",
        "待发货",
        "物流已更新",
        "快递已签收",
        "包裹已揽收",
        "已填写物流",
        "请尽快发货",
        # 收货 / 交易完成
        "记得及时确认收货",
        "已确认收货",
        "交易成功",
        "订单已完成",
        "交易完成",
        # 退款 / 关闭
        "已退款",
        "申请退款",
        "同意退款",
        "退款成功",
        "退款已到账",
        "拒绝退款",
        "订单已关闭",
        "交易已关闭",
        "已取消订单",
        "订单已取消",
        # 验货 / 鉴定
        "验货担保",
        "验货报告",
        "鉴定结果",
        "已通过鉴定",
        "鉴定为正品",
        "验货中",
        # 平台提醒 / 通知
        "请在24小时内",
        "系统消息",
        "平台提醒",
        "温馨提示",
        "安全提醒",
        "请注意交易安全",
        "请勿线下交易",
        "请勿私下转账",
        "请通过平台交易",
        "闲鱼小法庭",
        "对方已读",
        # 评价
        "给你一个评价",
        "已评价",
        "请及时评价",
    ]

    def _is_system_message(self, text: str) -> bool:
        """Check if text matches a platform system message pattern."""
        for pattern in self._SYSTEM_MSG_PATTERNS:
            if pattern in text:
                return True
        return False

    async def _push_event(self, event: dict[str, Any]) -> None:
        chat_id = str(event.get("chat_id", "") or "")
        sender_id = str(event.get("sender_user_id", "") or "")
        text = str(event.get("text", "") or "")
        create_time = int(event.get("create_time", int(time.time() * 1000)) or int(time.time() * 1000))
        if not chat_id or not sender_id or not text:
            return

        if sender_id == self.my_user_id:
            if not self.is_bot_sent(chat_id, text):
                if self._is_system_message(text):
                    self.logger.debug(f"[人工介入] 跳过平台系统消息: session={chat_id}, text={text[:30]}")
                    return
                try:
                    self._manual_mode_store.set_state(chat_id, True)
                    self._manual_mode_store.record_seller_activity(chat_id)
                    if self._on_manual_takeover is not None:
                        try:
                            self._on_manual_takeover(chat_id, True)
                        except Exception:
                            pass
                    self.logger.info(f"[人工介入] 检测到卖家手动消息: session={chat_id}, text={text[:30]}")
                except Exception as exc:
                    self.logger.warning(f"[人工介入] set_state failed: session={chat_id}, err={exc}")
            return

        if int(time.time() * 1000) - create_time > self.event_expire_ms:
            return

        dedupe_key = hashlib.sha1(f"{chat_id}:{create_time}:{text}".encode()).hexdigest()[:20]
        if dedupe_key in self._seen_event:
            return

        self._seen_event[dedupe_key] = time.time()
        self._cleanup_seen()

        try:
            self._manual_mode_store.record_buyer_activity(chat_id)
        except Exception:
            pass

        self._session_peer[chat_id] = sender_id
        if sender_id:
            self._peer_to_session[sender_id] = chat_id
        sender_name = str(event.get("sender_name", "") or "买家")
        if sender_name and sender_name != "买家":
            self._nick_to_session[sender_name] = chat_id
        _SESSION_PEER_MAX = 1000
        if len(self._session_peer) > _SESSION_PEER_MAX:
            oldest_keys = list(self._session_peer.keys())[: len(self._session_peer) - _SESSION_PEER_MAX]
            for k in oldest_keys:
                peer = self._session_peer.pop(k, None)
                if peer:
                    self._peer_to_session.pop(peer, None)
        if len(self._nick_to_session) > _SESSION_PEER_MAX:
            oldest = list(self._nick_to_session.keys())[: len(self._nick_to_session) - _SESSION_PEER_MAX]
            for k in oldest:
                self._nick_to_session.pop(k, None)
        payload = {
            "session_id": chat_id,
            "peer_name": sender_name,
            "item_title": str(event.get("item_id", "") or ""),
            "last_message": text,
            "unread_count": 1,
            "sender_user_id": sender_id,
            "create_time": create_time,
            "source": "ws",
        }

        if self._queue.full():
            try:
                _ = self._queue.get_nowait()
            except Exception:
                pass
        await self._queue.put(payload)
        self._queue_event.set()

    async def _handle_sync(self, packet: dict[str, Any]) -> None:
        body = packet.get("body", {})
        if not isinstance(body, dict):
            return
        sync_pkg = body.get("syncPushPackage", {})
        if not isinstance(sync_pkg, dict):
            if body:
                body_keys = list(body.keys())[:10]
                if body_keys and body_keys != ["code"]:
                    self.logger.debug(f"WS sync: no syncPushPackage, body keys={body_keys}")
            return
        data_arr = sync_pkg.get("data", [])
        if not isinstance(data_arr, list):
            return

        if data_arr:
            self.logger.debug(f"WS sync push: {len(data_arr)} items")
        for idx, item in enumerate(data_arr):
            if not isinstance(item, dict):
                continue
            raw = item.get("data")
            if not raw:
                continue
            decoded = decode_sync_payload(str(raw))
            if decoded is None:
                self.logger.debug(f"WS sync item[{idx}] decode failed, raw_len={len(str(raw))}")
                continue
            event = extract_chat_event(decoded)
            if event:
                self.logger.info(
                    f"WS chat event: chat={event.get('chat_id', '?')}, sender={event.get('sender_user_id', '?')}, text={event.get('text', '')[:50]}"
                )
                await self._push_event(event)
            else:
                top_keys = list(decoded.keys())[:6] if isinstance(decoded, dict) else type(decoded).__name__
                self.logger.debug(f"WS sync item[{idx}] not a chat event, keys={top_keys}")

    async def _run(self) -> None:
        if websockets is None:
            raise BrowserError("WebSocket transport requires `websockets`. Install: pip install websockets")

        self._ensure_async_primitives()
        while not self._stop_event.is_set():
            try:
                self._maybe_reload_cookie(reason="connect")
                headers = self._base_headers(include_cookie=True)
                try:
                    self._ws = await websockets.connect(
                        self.base_url,
                        extra_headers=headers,
                        ping_interval=None,
                        close_timeout=5,
                        max_size=8 * 1024 * 1024,
                    )
                except TypeError as connect_error:
                    # websockets>=14 renamed `extra_headers` to `additional_headers`.
                    if "extra_headers" not in str(connect_error):
                        raise
                    self._ws = await websockets.connect(
                        self.base_url,
                        additional_headers=headers,
                        ping_interval=None,
                        close_timeout=5,
                        max_size=8 * 1024 * 1024,
                    )
                self._last_heartbeat_ack = time.time()
                self._last_heartbeat_sent = 0.0
                await self._send_reg()
                self._ready.set()
                self._connect_failures = 0
                self._rgv587_consecutive = 0
                self._active_refresh_401_streak = 0
                self.logger.info("Connected to Goofish WebSocket transport")

                while not self._stop_event.is_set():
                    now = time.time()
                    if (now - self._last_heartbeat_sent) >= max(1.0, float(self.heartbeat_interval)):
                        await self._send_heartbeat()

                    if (now - self._last_heartbeat_ack) > (self.heartbeat_interval + self.heartbeat_timeout):
                        raise BrowserError("WebSocket heartbeat timeout")

                    if self._token_ts > 0 and (now - self._token_ts) >= self.token_refresh_interval_seconds * 0.95:
                        self.logger.info("Token approaching expiry, forcing WS reconnect for renewal")
                        self._token = ""
                        self._token_ts = 0.0
                        self._connect_failures = 0
                        raise BrowserError("Token refresh: reconnect required")

                    if self._cookie_changed.is_set():
                        self._cookie_changed.clear()
                        if self._maybe_reload_cookie(reason="notified"):
                            self.logger.info("Cookie update notified, forcing reconnect")
                            self._ready.clear()
                            self._token = ""
                            self._token_ts = 0.0
                            self._connect_failures = 0
                            break
                    if (now - self._last_cookie_check) >= 60.0:
                        self._last_cookie_check = now
                        if self._maybe_reload_cookie(reason="periodic"):
                            self.logger.info("Periodic cookie check detected update, forcing reconnect")
                            self._ready.clear()
                            self._token = ""
                            self._token_ts = 0.0
                            self._connect_failures = 0
                            break

                    im_refresh_interval = 15 * 60
                    if (now - self._last_im_refresh_at) >= im_refresh_interval:
                        ttl = self._m_h5_tk_seconds_until_expiry()
                        if ttl is not None and ttl < 900:
                            self.logger.info(f"_m_h5_tk TTL={ttl:.0f}s < 900s, proactive IM refresh")
                            if await self._try_goofish_im_refresh():
                                self._last_im_refresh_at = now
                                self.logger.info("Proactive IM cookie refresh succeeded")
                                self._ready.clear()
                                self._token = ""
                                self._token_ts = 0.0
                                self._connect_failures = 0
                                break
                        self._last_im_refresh_at = now

                    if (now - self._last_haslogin_heartbeat_at) >= self.haslogin_heartbeat_interval:
                        self._last_haslogin_heartbeat_at = now
                        try:
                            hl_ok = await self._preflight_has_login()
                            if hl_ok:
                                ttl_after = self._m_h5_tk_seconds_until_expiry()
                                self.logger.info(
                                    f"hasLogin heartbeat succeeded, _m_h5_tk TTL={ttl_after:.0f}s"
                                    if ttl_after is not None
                                    else "hasLogin heartbeat succeeded"
                                )
                            else:
                                self.logger.debug("hasLogin heartbeat: server returned non-success")
                        except Exception as exc:
                            self.logger.debug(f"hasLogin heartbeat failed: {exc}")

                    try:
                        msg_text = await asyncio.wait_for(self._ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue

                    packet = json.loads(msg_text)
                    if isinstance(packet, dict):
                        if packet.get("code") == 200:
                            self._last_heartbeat_ack = time.time()
                        await self._ack_packet(packet)
                        await self._handle_sync(packet)

            except asyncio.CancelledError:  # pragma: no cover - cooperative cancel path
                break
            except Exception as exc:
                self._ready.clear()
                self._connect_failures += 1
                auth_error = self._is_auth_related_error(exc)
                reason = str(exc or "").strip() or "unknown error"
                self._last_disconnect_reason = reason
                self.logger.warning(f"Goofish WebSocket disconnected, retrying: {reason}")

                is_rgv587 = "RGV587" in reason
                if auth_error:
                    if is_rgv587:
                        self._rgv587_consecutive += 1
                        slider_cfg = self.config.get("slider_auto_solve", {})
                        slider_enabled = bool(slider_cfg.get("enabled")) if isinstance(slider_cfg, dict) else False

                        rgv_backoff = min(
                            self._RGV587_BACKOFF_CAP,
                            60.0 * (2 ** (self._rgv587_consecutive - 1)),
                        )

                        self.logger.warning(
                            f"RGV587 风控检测 ({self._rgv587_consecutive}), "
                            f"slider_attempts={self._slider_recovery_attempts}/{self._SLIDER_MAX_ATTEMPTS_PER_CYCLE}, "
                            f"退避 {rgv_backoff:.0f}s..."
                        )

                        if self._rgv587_consecutive <= 2 and await self._try_goofish_im_refresh(urgent=True):
                            self._connect_failures = 0
                            self.logger.info(f"闲管家IM Cookie刷新成功，退避 {rgv_backoff:.0f}s 后重试 WS 连接")
                            await asyncio.sleep(rgv_backoff)
                            continue

                        can_try_slider = (
                            slider_enabled and self._slider_recovery_attempts < self._SLIDER_MAX_ATTEMPTS_PER_CYCLE
                        )

                        if can_try_slider:
                            self._send_risk_control_notification()
                            self._slider_recovery_attempts += 1
                            recovered = await self._try_slider_recovery(trigger_source="rgv587")
                            if recovered:
                                self._connect_failures = 0
                                self._rgv587_consecutive = 0
                                self._slider_recovery_attempts = 0
                                self.logger.info("滑块验证恢复成功，立即重试 WS 连接")
                                continue
                            self.logger.warning(
                                f"滑块自动恢复失败 ({self._slider_recovery_attempts}/{self._SLIDER_MAX_ATTEMPTS_PER_CYCLE})，"
                                f"退避 {rgv_backoff:.0f}s..."
                            )
                            await asyncio.sleep(rgv_backoff)
                            continue
                        elif not slider_enabled and self._rgv587_consecutive <= 3:
                            self.logger.warning(
                                f"RGV587 风控检测 ({self._rgv587_consecutive}/3)，退避 {rgv_backoff:.0f}s 后重试..."
                            )
                            await self._try_goofish_im_refresh(urgent=True)
                            if await self._try_active_cookie_refresh():
                                self.logger.info("Active cookie refresh succeeded during RGV587 backoff")
                            await asyncio.sleep(rgv_backoff)
                            continue

                        self.logger.warning(
                            "RGV587 风控持续触发（slider %d/%d 次已耗尽），"
                            "请在浏览器打开闲鱼消息页(https://www.goofish.com/im)完成滑块验证后更新 Cookie。"
                            " 暂停自动重连，等待 Cookie 更新...",
                            self._slider_recovery_attempts,
                            self._SLIDER_MAX_ATTEMPTS_PER_CYCLE,
                        )
                        self._send_risk_control_notification()

                        if await self._wait_for_cookie_update_forever():
                            self._connect_failures = 0
                            self._rgv587_consecutive = 0
                            self._slider_recovery_attempts = 0
                            self.logger.info("检测到 Cookie 更新，立即重试 WS 连接")
                            continue
                    elif await self._try_goofish_im_refresh(urgent=True):
                        self._active_refresh_401_streak = 0
                        self._connect_failures = 0
                        self.logger.info("闲管家IM Cookie刷新成功 (401恢复)，立即重试 WS 连接")
                        continue
                    elif await self._try_active_cookie_refresh():
                        self._active_refresh_401_streak += 1
                        if self._active_refresh_401_streak >= 3:
                            self.logger.warning(
                                "Active refresh 连续 %d 次仍 401，升级到 slider_recovery",
                                self._active_refresh_401_streak,
                            )
                            if await self._try_slider_recovery(trigger_source="401_streak"):
                                self._active_refresh_401_streak = 0
                                self._connect_failures = 0
                                self.logger.info("slider_recovery 成功，立即重试 WS 连接")
                                continue
                            if await self._wait_for_cookie_update_forever():
                                self._active_refresh_401_streak = 0
                                self._connect_failures = 0
                                continue
                        self._connect_failures = 0
                        self.logger.info("Active cookie refresh succeeded, retrying WS immediately")
                        continue
                    elif self.auth_hold_until_cookie_update:
                        self.logger.warning("Auth failure detected, suspend reconnect until cookie is updated")
                        if await self._wait_for_cookie_update_forever():
                            self._connect_failures = 0
                            self.logger.info("Detected cookie update, retrying WS connection immediately")
                            continue
                    elif await self._wait_for_cookie_update(self.auth_failure_backoff_seconds):
                        self._connect_failures = 0
                        self.logger.info("Detected cookie update, retrying WS connection immediately")
                        continue

                await asyncio.sleep(self._next_reconnect_delay(auth_error=auth_error))
            finally:
                if self._ws is not None:
                    try:
                        await self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

    async def start(self) -> None:
        self._ensure_async_primitives()
        if self._run_task and not self._run_task.done():
            return
        self._stop_event.clear()
        self._run_task = asyncio.create_task(self._run())

    def is_ready(self) -> bool:
        return bool(self._ready.is_set() and self._ws is not None)

    async def stop(self) -> None:
        self._stop_event.set()
        self._ready.clear()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._run_task is not None:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._run_task = None

    async def _wait_event_with_timeout(self, event: asyncio.Event, timeout: float) -> bool:
        waiter = asyncio.create_task(event.wait())
        try:
            await asyncio.wait_for(waiter, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            if not waiter.done():
                waiter.cancel()
                try:
                    await waiter
                except asyncio.CancelledError:
                    pass

    async def get_unread_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        self._ensure_async_primitives()
        await self.start()
        if not self._ready.is_set() and not await self._wait_event_with_timeout(self._ready, 10.0):
            return []

        if self._queue.empty():
            self._queue_event.clear()
            if not await self._wait_event_with_timeout(self._queue_event, max(0.05, self.queue_wait_seconds)):
                return []

        out: list[dict[str, Any]] = []
        seen_session: set[str] = set()
        safe_limit = max(1, int(limit or 20))
        while len(out) < safe_limit and not self._queue.empty():
            try:
                item = self._queue.get_nowait()
            except Exception:
                break
            sid = str(item.get("session_id", "") or "")
            if not sid or sid in seen_session:
                continue
            seen_session.add(sid)
            out.append(item)
        return out

    async def send_text(self, session_id: str, text: str) -> bool:
        if not (text or "").strip():
            return False

        self._ensure_async_primitives()
        await self.start()
        if not self._ready.is_set() and not await self._wait_event_with_timeout(self._ready, 10.0):
            return False

        chat_id = str(session_id or "").strip()
        if not chat_id:
            return False

        to_user_id = str(self._session_peer.get(chat_id, "") or "").strip()
        if not to_user_id:
            self.logger.info(f"WS send: peer mapping miss for `{chat_id}`, falling back to mtop send")
            return await self._send_text_via_mtop(chat_id, text)

        if self._ws is None:
            return await self._send_text_via_mtop(chat_id, text)

        payload = {
            "contentType": 1,
            "text": {"text": str(text or "")},
        }
        content_b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("utf-8")
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {"mid": generate_mid()},
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{chat_id}@goofish",
                    "conversationType": 1,
                    "content": {"contentType": 101, "custom": {"type": 1, "data": content_b64}},
                    "redPointPolicy": 0,
                    "extension": {"extJson": "{}"},
                    "ctx": {"appVersion": "1.0", "platform": "web"},
                    "mtags": {},
                    "msgReadStatusSetting": 1,
                },
                {"actualReceivers": [f"{to_user_id}@goofish", f"{self.my_user_id}@goofish"]},
            ],
        }
        try:
            await self._ws.send(json.dumps(msg, ensure_ascii=False))
            self._record_bot_sig(chat_id, text)
            return True
        except Exception as exc:
            self.logger.warning(f"WS send failed: {exc}, falling back to mtop")
            return await self._send_text_via_mtop(chat_id, text)

    async def _send_text_via_mtop(self, chat_id: str, text: str) -> bool:
        """通过 mtop HTTP API 发送消息（WS 不可用或 peer 映射缺失时的回退路径）。"""
        cid = f"{chat_id}@goofish" if "@" not in chat_id else chat_id
        payload_inner = {
            "contentType": 1,
            "text": {"text": str(text or "")},
        }
        content_b64 = base64.b64encode(json.dumps(payload_inner, ensure_ascii=False).encode("utf-8")).decode("utf-8")
        data_dict = {
            "uuid": generate_uuid(),
            "cid": cid,
            "content": json.dumps(
                {"contentType": 101, "custom": {"type": 1, "data": content_b64}},
                ensure_ascii=False,
            ),
        }
        try:
            result = await self._mtop_call(
                "mtop.taobao.idle.pc.im.msg.send",
                "1.0",
                data_dict,
            )
            ret = result.get("ret", []) if isinstance(result, dict) else []
            success = any("SUCCESS" in str(item) for item in ret) if ret else bool(result.get("data"))
            if success:
                self._record_bot_sig(chat_id, text)
                self.logger.info(f"mtop send succeeded for session `{chat_id}`")
            else:
                self.logger.warning(f"mtop send response not successful for `{chat_id}`: ret={ret}")
            return success
        except Exception as exc:
            self.logger.warning(f"mtop send failed for `{chat_id}`: {exc}")
            return False

    def _record_bot_sig(self, chat_id: str, text: str) -> None:
        self._bot_sig_store.record(chat_id, text)

    def is_bot_sent(self, chat_id: str, text: str) -> bool:
        return self._bot_sig_store.is_bot_sent(chat_id, text)

    def _cleanup_bot_sigs(self) -> None:
        self._bot_sig_store.cleanup()

    def find_session_by_peer(self, user_id: str) -> str:
        """Reverse lookup: sender_user_id -> chat_id."""
        return self._peer_to_session.get(str(user_id or "").strip(), "")

    def find_session_by_nick(self, nick: str) -> str:
        """Reverse lookup: buyer nick -> chat_id."""
        return self._nick_to_session.get(str(nick or "").strip(), "")

    async def _mtop_call(self, api: str, version: str, data_dict: dict[str, Any]) -> dict[str, Any]:
        """Make a signed mtop API call using current cookies."""
        self._maybe_reload_cookie(reason="mtop_call")
        token_cookie = str(self.cookies.get("_m_h5_tk", "") or "")
        token_seed = token_cookie.split("_")[0].strip()
        if not token_seed:
            return {}

        t = str(int(time.time() * 1000))
        data_val = json.dumps(data_dict, ensure_ascii=False, separators=(",", ":"))
        params = {
            "jsv": "2.7.2",
            "appKey": _MTOP_APP_KEY,
            "t": t,
            "sign": generate_sign(t, token_seed, data_val),
            "v": version,
            "type": "originaljson",
            "accountSite": "xianyu",
            "dataType": "json",
            "timeout": "10000",
            "api": api,
        }
        headers = self._base_headers()
        try:
            async with httpx.AsyncClient(
                timeout=8.0,
                headers=headers,
                cookies=self.cookies,
            ) as client:
                resp = await client.post(
                    f"https://h5api.m.goofish.com/h5/{api}/{version}/",
                    params=params,
                    data={"data": data_val},
                )
                self._absorb_set_cookies(client, reason="mtop_call")
                return resp.json() if resp.status_code == 200 else {}
        except Exception as exc:
            self.logger.debug(f"mtop call {api} failed: {exc}")
            return {}

    async def fetch_recent_messages(self, chat_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent messages for a conversation via mtop API, with caching."""
        if not chat_id:
            return []

        now = time.time()
        cached = self._recent_msgs_cache.get(chat_id)
        if cached and (now - cached[0]) < self._RECENT_MSGS_CACHE_TTL:
            return cached[1]

        cid = f"{chat_id}@goofish" if "@" not in chat_id else chat_id
        payload = await self._mtop_call(
            "mtop.taobao.idle.pc.im.conversation.message.list",
            "1.0",
            {"cid": cid, "pageSize": limit, "order": "desc"},
        )

        result: list[dict[str, Any]] = []
        data = payload.get("data", {})
        if not isinstance(data, dict):
            self._recent_msgs_cache[chat_id] = (now, result)
            return result

        messages = data.get("messageList") or data.get("messages") or data.get("data") or []
        if not isinstance(messages, list):
            self._recent_msgs_cache[chat_id] = (now, result)
            return result

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            sender = str(msg.get("senderUserId") or msg.get("fromUserId") or msg.get("senderId") or "")
            content = msg.get("content", {})
            if isinstance(content, dict):
                text = str(content.get("text") or content.get("reminderContent") or "")
            elif isinstance(content, str):
                text = content
            else:
                text = ""
            ts = 0
            try:
                ts = int(msg.get("createTime") or msg.get("gmtCreate") or msg.get("timestamp") or 0)
            except (ValueError, TypeError):
                pass
            if sender and text:
                result.append({"sender_id": sender, "text": text, "timestamp": ts})

        self._recent_msgs_cache[chat_id] = (now, result)
        return result


_ws_transport_instance: GoofishWsTransport | None = None


def set_ws_transport_instance(transport: GoofishWsTransport | None) -> None:
    global _ws_transport_instance
    _ws_transport_instance = transport


def get_session_by_buyer_nick(nick: str) -> str:
    """Module-level helper: find chat session_id by buyer nick."""
    if not _ws_transport_instance or not nick:
        return ""
    return _ws_transport_instance.find_session_by_nick(nick)


def notify_ws_cookie_changed() -> None:
    """Thread-safe: notify WS transport that cookie has been updated externally."""
    if _ws_transport_instance is not None:
        _ws_transport_instance.notify_cookie_changed()
