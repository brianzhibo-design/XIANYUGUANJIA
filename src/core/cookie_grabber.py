"""
自动获取闲鱼 Cookie 模块

降级策略：
  Level 0   — CookieCloud 远程拉取（如果已配置）
  Level 1   — rookiepy 直读本地浏览器 Cookie 数据库（零操作）
  Level IM  — 闲管家IM直读（CookieAutoRefresher 使用）
  Level BB  — BitBrowser CDP 直读（ws_live.py 使用）

已移除的策略（Playwright 依赖，已不再使用）：
  Level 1.5 — Playwright persistent context 复用 Chrome Profile
  Level 2   — Playwright 全新窗口让用户扫码登录
  Level 1+  — Playwright 注入 Cookie 补全会话字段
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from collections.abc import Callable

from src.core.logger import get_logger

logger = get_logger()

_GOOFISH_DOMAINS = [".goofish.com", ".taobao.com", ".tmall.com"]
_MY_PAGE_URL = "https://www.goofish.com/personal"
_LOGIN_TIMEOUT_MS = 300_000  # 5 minutes
_AUTH_COOKIES = {"unb", "cookie2", "sgcookie"}
_WEAK_LOGIN_COOKIES = {"_m_h5_tk", "_tb_token_"}
_SESSION_COOKIES = {"_m_h5_tk", "_m_h5_tk_enc"}


class GrabStage(str, Enum):
    IDLE = "idle"
    READING_DB = "reading_db"
    READING_PROFILE = "reading_profile"
    VALIDATING = "validating"
    LOGIN_REQUIRED = "login_required"
    WAITING_LOGIN = "waiting_login"
    SAVING = "saving"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GrabProgress:
    stage: GrabStage = GrabStage.IDLE
    message: str = ""
    hint: str = ""
    progress: int = 0
    cookie_preview: str = ""
    error: str = ""


@dataclass
class GrabResult:
    ok: bool = False
    cookie_str: str = ""
    source: str = ""
    message: str = ""
    error: str = ""


class CookieGrabber:
    """自动获取闲鱼 Cookie — CookieCloud + rookiepy 降级策略。"""

    def __init__(self) -> None:
        self._cancel = False
        self._progress = GrabProgress()
        self._listeners: list[Any] = []

    @property
    def progress(self) -> GrabProgress:
        return self._progress

    def cancel(self) -> None:
        self._cancel = True
        self._update(GrabStage.CANCELLED, "已取消")

    def add_listener(self, fn: Any) -> None:
        self._listeners.append(fn)

    def _update(self, stage: GrabStage, message: str, hint: str = "", progress: int = 0) -> None:
        self._progress = GrabProgress(stage=stage, message=message, hint=hint, progress=progress)
        for fn in self._listeners:
            try:
                fn(self._progress)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Main flow
    # ------------------------------------------------------------------

    async def auto_grab(self) -> GrabResult:
        """组合 Level 0 (CookieCloud) → Level 1 (rookiepy) 的获取流程。"""
        self._cancel = False

        # Level 0: CookieCloud 远程拉取（如果已配置）
        cookie = await self._grab_from_cookiecloud()
        if self._cancel:
            return GrabResult(ok=False, error="已取消")
        if cookie:
            valid = await self._validate(cookie)
            if valid:
                self._save(cookie, source="cookiecloud")
                self._update(GrabStage.SUCCESS, "Cookie 获取成功！", "从 CookieCloud 远程同步获取", 100)
                return GrabResult(ok=True, cookie_str=cookie, source="cookiecloud", message="从 CookieCloud 同步成功")

        # Level 1: rookiepy 直读浏览器 Cookie DB
        cookie = await self._grab_from_browser_db()
        if self._cancel:
            return GrabResult(ok=False, error="已取消")
        if cookie:
            valid = await self._validate(cookie)
            if valid:
                self._save(cookie, source="browser_db")
                self._update(
                    GrabStage.SUCCESS, "Cookie 获取成功！", "从浏览器数据库直接读取，Cookie 有效期约 7-30 天", 100
                )
                return GrabResult(ok=True, cookie_str=cookie, source="browser_db", message="从浏览器数据库获取成功")

        self._update(
            GrabStage.FAILED,
            "Cookie 获取失败",
            "自动方式未成功。请在 BitBrowser 中登录闲鱼，或手动粘贴 Cookie",
        )

        from src.core.notify import send_system_notification

        send_system_notification(
            "【闲鱼自动化】⚠️ Cookie 自动获取失败\n"
            "CookieCloud 和浏览器数据库均未获取到有效 Cookie。\n"
            "请在 BitBrowser 中登录闲鱼，或手动打开 Dashboard 更新 Cookie。",
            event="cookie_expire",
        )
        return GrabResult(ok=False, error="所有获取方式均失败")

    # ------------------------------------------------------------------
    # Level 0: CookieCloud 远程拉取
    # ------------------------------------------------------------------

    async def _grab_from_cookiecloud(self) -> str | None:
        """从 CookieCloud 服务拉取 Cookie（需配置环境变量或 system_config）。"""
        host = os.environ.get("COOKIE_CLOUD_HOST", "").strip()
        uuid = os.environ.get("COOKIE_CLOUD_UUID", "").strip()
        password = os.environ.get("COOKIE_CLOUD_PASSWORD", "").strip()

        if not host or not uuid or not password:
            try:
                import json

                cfg_path = Path("data/system_config.json")
                if cfg_path.exists():
                    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                    cc = cfg.get("cookie_cloud", {}) if isinstance(cfg.get("cookie_cloud"), dict) else {}
                    host = host or str(cc.get("cookie_cloud_host") or cfg.get("cookie_cloud_host", "")).strip()
                    uuid = uuid or str(cc.get("cookie_cloud_uuid") or cfg.get("cookie_cloud_uuid", "")).strip()
                    password = (
                        password or str(cc.get("cookie_cloud_password") or cfg.get("cookie_cloud_password", "")).strip()
                    )
            except Exception:
                pass

        if not host and uuid and password:
            host = "http://localhost:8091/cookie-cloud"

        if not host or not uuid or not password:
            return None

        logger.info("Level 0: 正在从 CookieCloud 拉取 Cookie...")
        try:
            import hashlib
            import json
            import httpx

            url = f"{host.rstrip('/')}/get/{uuid}"

            key_raw = f"{uuid}-{password}"
            key_hash = hashlib.md5(key_raw.encode("utf-8")).hexdigest()[:16]

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"password": password})
                if resp.status_code != 200:
                    logger.info(f"CookieCloud 请求失败: HTTP {resp.status_code}")
                    return None

                data = resp.json()

            encrypted = data.get("encrypted")
            if encrypted:
                cookie_data = self._decrypt_cookiecloud(encrypted, key_hash)
            else:
                cookie_data = data.get("cookie_data", {})

            if not cookie_data:
                logger.info("CookieCloud 返回空数据")
                return None

            parts: list[str] = []
            target_domains = {".goofish.com", ".taobao.com", ".tmall.com", "goofish.com", "taobao.com"}
            for domain, cookies_list in cookie_data.items():
                domain_lower = domain.lower().strip(".")
                if not any(domain_lower.endswith(d.strip(".")) for d in target_domains):
                    continue
                if isinstance(cookies_list, list):
                    for ck in cookies_list:
                        name = str(ck.get("name", "")).strip()
                        value = str(ck.get("value", "")).strip()
                        if name and value:
                            parts.append(f"{name}={value}")
                elif isinstance(cookies_list, dict):
                    for name, value in cookies_list.items():
                        n = str(name).strip()
                        v = str(value).strip()
                        if n and v:
                            parts.append(f"{n}={v}")

            if not parts:
                logger.info("CookieCloud 未找到闲鱼相关 Cookie")
                return None

            cookie_str = "; ".join(parts)
            logger.info(f"CookieCloud 获取到 {len(parts)} 个 Cookie 条目")
            return cookie_str

        except Exception as exc:
            logger.info(f"CookieCloud 拉取失败: {exc}")
            return None

    @staticmethod
    def _decrypt_cookiecloud(encrypted: str, key: str) -> dict[str, Any]:
        """Decrypt CookieCloud AES-CBC encrypted data.

        Supports both legacy (CryptoJS passphrase mode with Salted__ header,
        EVP_BytesToKey for key derivation) and aes-128-cbc-fixed (zero IV,
        direct key) modes.
        """
        try:
            import base64
            import json
            from hashlib import md5 as _md5

            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding as sym_padding

            raw = base64.b64decode(encrypted)

            if raw[:8] == b"Salted__":
                salt = raw[8:16]
                ct = raw[16:]
                passphrase = key.encode("utf-8")

                d = b""
                last = b""
                while len(d) < 48:
                    last = _md5(last + passphrase + salt).digest()
                    d += last
                derived_key, iv = d[:32], d[32:48]
            else:
                ct = raw
                derived_key = key.encode("utf-8")[:16]
                iv = b"\x00" * 16

            cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded = decryptor.update(ct) + decryptor.finalize()

            unpadder = sym_padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded) + unpadder.finalize()

            return json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            logger.debug(f"CookieCloud 解密失败: {exc}")
            return {}

    # ------------------------------------------------------------------
    # Level 1: rookiepy 直读浏览器 Cookie DB
    # ------------------------------------------------------------------

    async def _grab_from_browser_db(self) -> str | None:
        self._update(
            GrabStage.READING_DB, "正在读取浏览器 Cookie 数据库...", '如果弹出"钥匙串访问"弹窗，请点击"允许"', 5
        )

        browsers = [
            ("Chrome", self._read_chrome),
            ("Edge", self._read_edge),
            ("Firefox", self._read_firefox),
        ]

        for name, reader in browsers:
            if self._cancel:
                return None
            try:
                cookie_str = reader()
                if cookie_str and len(cookie_str) > 50:
                    logger.info(f"从 {name} 浏览器数据库读取到 Cookie ({len(cookie_str)} chars)")
                    return cookie_str
            except Exception as exc:
                logger.debug(f"{name} Cookie 读取失败: {exc}")
                continue

        logger.info("Level 1: 本地浏览器数据库中未找到有效 Cookie")
        return None

    def _read_chrome(self) -> str | None:
        try:
            import rookiepy

            cookies = rookiepy.chrome(domains=[".goofish.com", ".taobao.com", ".tmall.com"])
            return self._format_cookies(cookies)
        except Exception as exc:
            logger.debug(f"Chrome rookiepy: {exc}")
            return None

    def _read_edge(self) -> str | None:
        try:
            import rookiepy

            cookies = rookiepy.edge(domains=[".goofish.com", ".taobao.com", ".tmall.com"])
            return self._format_cookies(cookies)
        except Exception as exc:
            logger.debug(f"Edge rookiepy: {exc}")
            return None

    def _read_firefox(self) -> str | None:
        try:
            import rookiepy

            cookies = rookiepy.firefox(domains=[".goofish.com", ".taobao.com", ".tmall.com"])
            return self._format_cookies(cookies)
        except Exception as exc:
            logger.debug(f"Firefox rookiepy: {exc}")
            return None


    # ------------------------------------------------------------------
    # Cookie extraction & login detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_cookies(cookies: list[dict[str, Any]]) -> str | None:
        if not cookies:
            return None
        pairs = []
        for c in cookies:
            name = c.get("name", "")
            value = c.get("value", "")
            if name and value:
                pairs.append(f"{name}={value}")
        return "; ".join(pairs) if pairs else None

    @staticmethod
    def _extract_goofish_cookies(all_cookies: list[dict[str, Any]]) -> str | None:
        goofish = [c for c in all_cookies if any(d in (c.get("domain", "")) for d in _GOOFISH_DOMAINS)]
        if not goofish:
            return None
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in goofish if c.get("name"))
        return cookie_str if len(cookie_str) > 50 else None

    @staticmethod
    def _has_login_cookies(cookies: list[dict[str, Any]]) -> bool:
        """检查是否包含登录后才会出现的 Cookie（unb=用户ID, cookie2, sgcookie）。"""
        names = {c.get("name", "") for c in cookies}
        return bool(names & _AUTH_COOKIES)

    @staticmethod
    def _is_logged_in(url: str) -> bool:
        url_lower = url.lower()
        if "login" in url_lower or "signin" in url_lower:
            return False
        if "goofish.com/personal" in url_lower:
            return True
        return False

    @staticmethod
    def _is_login_page(url: str) -> bool:
        url_lower = url.lower()
        return "login" in url_lower or "signin" in url_lower or "passport" in url_lower or "qrcode" in url_lower

    @staticmethod
    def _has_session_fields(cookie_str: str) -> bool:
        """检查 cookie_str 是否包含 _m_h5_tk 会话字段。"""
        pairs = {p.split("=", 1)[0].strip() for p in cookie_str.split(";") if "=" in p}
        return bool(pairs & _SESSION_COOKIES)

    # ------------------------------------------------------------------
    # Validation & persistence
    # ------------------------------------------------------------------

    async def _validate(self, cookie_str: str) -> bool:
        self._update(GrabStage.VALIDATING, "正在验证 Cookie 有效性...", "", 92)
        try:
            from src.core.cookie_health import CookieHealthChecker

            checker = CookieHealthChecker(cookie_str, timeout_seconds=10.0)
            result = checker.check_sync(force=True)
            if not result.get("healthy"):
                logger.warning(f"Cookie 验证失败: {result.get('message', 'unknown')}")
                return False
            logger.info("Cookie 在线探测通过，检查字段完整性...")
        except Exception as exc:
            logger.warning(f"Cookie 验证异常，跳过在线探测: {exc}")

        try:
            from src.dashboard_server import MimicOps

            ops = MimicOps.__new__(MimicOps)
            diag = ops.diagnose_cookie(cookie_str)
            grade = diag.get("grade", "")
            if grade == "不可用":
                missing = diag.get("required_missing", [])
                logger.warning(f"Cookie 完整性诊断不可用，缺少: {missing}")
                return False
            logger.info(f"Cookie 完整性诊断: {grade}")
        except Exception as exc:
            logger.debug(f"Cookie 完整性诊断跳过: {exc}")

        return True

    def _save(self, cookie_str: str, source: str = "auto") -> None:
        self._update(GrabStage.SAVING, "正在保存 Cookie...", "", 95)

        from src.core.cookie_store import save_cookie

        save_cookie(cookie_str, persist=True, source=source)


# ======================================================================
# 后台静默 Cookie 自动刷新器
# ======================================================================


@dataclass
class AutoRefreshStatus:
    """自动刷新器的运行状态快照。"""

    enabled: bool = False
    interval_minutes: int = 30
    last_check_at: float = 0.0
    last_check_ok: bool | None = None
    last_check_message: str = ""
    last_refresh_at: float = 0.0
    last_refresh_ok: bool | None = None
    last_refresh_source: str = ""
    total_checks: int = 0
    total_refreshes: int = 0
    next_check_in_seconds: int = 0


class CookieAutoRefresher:
    """后台静默 Cookie 刷新器 — 仅使用 Level 1 (rookiepy)。

    在守护线程中定期检查 Cookie 健康状态，失效时自动尝试从浏览器
    Cookie 数据库静默读取新的 Cookie，无需用户交互。
    """

    def __init__(
        self,
        interval_minutes: int = 30,
        on_refreshed: Callable[[str], Any] | None = None,
    ) -> None:
        self._interval = max(5, interval_minutes) * 60  # 最小 5 分钟
        self._interval_minutes = max(5, interval_minutes)
        self._on_refreshed = on_refreshed
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self._last_check_at: float = 0.0
        self._last_check_ok: bool | None = None
        self._last_check_msg: str = ""
        self._last_refresh_at: float = 0.0
        self._last_refresh_ok: bool | None = None
        self._last_refresh_source: str = ""
        self._total_checks: int = 0
        self._total_refreshes: int = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> AutoRefreshStatus:
        elapsed = time.time() - self._last_check_at if self._last_check_at else 0
        remaining = max(0, int(self._interval - elapsed)) if self._last_check_at else 0
        return AutoRefreshStatus(
            enabled=self.running,
            interval_minutes=self._interval_minutes,
            last_check_at=self._last_check_at,
            last_check_ok=self._last_check_ok,
            last_check_message=self._last_check_msg,
            last_refresh_at=self._last_refresh_at,
            last_refresh_ok=self._last_refresh_ok,
            last_refresh_source=self._last_refresh_source,
            total_checks=self._total_checks,
            total_refreshes=self._total_refreshes,
            next_check_in_seconds=remaining,
        )

    def start(self) -> None:
        if self.running:
            logger.debug("CookieAutoRefresher 已在运行")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="cookie-auto-refresh")
        self._thread.start()
        logger.info(f"Cookie 静默自动刷新已启动 (间隔 {self._interval_minutes} 分钟)")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Cookie 静默自动刷新已停止")

    def _loop(self) -> None:
        # 启动后等待 60 秒再做第一次检查，避免和服务启动竞争
        self._stop_event.wait(60)

        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.error(f"Cookie 自动刷新异常: {exc}")
            self._stop_event.wait(self._interval)

    @staticmethod
    def _m_h5_tk_seconds_until_expiry(cookie_text: str) -> float | None:
        from src.core.cookie_health import m_h5_tk_seconds_until_expiry

        return m_h5_tk_seconds_until_expiry(cookie_text)

    def _tick(self) -> None:
        self._total_checks += 1
        self._last_check_at = time.time()

        cookie_text = os.environ.get("XIANYU_COOKIE_1", "")

        healthy, msg = self._check_health(cookie_text)
        self._last_check_ok = healthy
        self._last_check_msg = msg

        if healthy:
            logger.debug(f"Cookie 自动检查: 健康 ({msg})")
            return

        logger.info(f"Cookie 自动检查: 不健康 ({msg})，尝试静默刷新...")

        # 2) 多级静默获取: 闲管家IM -> CookieCloud -> rookiepy -> Chrome Profile
        new_cookie: str | None = None

        # Level IM: 闲管家IM直读（最可靠来源）
        try:
            from src.core.goofish_im_cookie import read_goofish_im_cookies, merge_cookies

            im_result = read_goofish_im_cookies(min_ttl=60)
            if im_result:
                im_cookie = im_result["cookie_str"]
                existing = cookie_text or ""
                if existing:
                    im_cookie = merge_cookies(im_result["cookies"], existing)
                new_cookie = im_cookie
                self._last_refresh_source = "goofish_im"
                logger.info("自动刷新: 闲管家IM获取成功")
        except Exception as im_exc:
            logger.debug(f"自动刷新: 闲管家IM失败: {im_exc}")

        loop = asyncio.new_event_loop()
        try:
            grabber = CookieGrabber()
            # Level 0: CookieCloud（如已配置）
            if not new_cookie:
                try:
                    cc_cookie = loop.run_until_complete(grabber._grab_from_cookiecloud())
                    if cc_cookie:
                        new_cookie = cc_cookie
                        self._last_refresh_source = "cookiecloud"
                        logger.info("自动刷新: CookieCloud 获取成功")
                except Exception as cc_exc:
                    logger.debug(f"自动刷新: CookieCloud 失败: {cc_exc}")
            # Level 1: rookiepy 降级
            if not new_cookie:
                new_cookie = loop.run_until_complete(grabber._grab_from_browser_db())
                if new_cookie:
                    self._last_refresh_source = "browser_db"
        finally:
            loop.close()

        if not new_cookie:
            logger.info("Cookie 静默刷新: 所有静默方式均未获取到 Cookie")
            self._last_refresh_ok = False
            self._last_refresh_source = ""
            self._send_notification(
                "⚠️ Cookie 已失效且自动刷新失败",
                f"【闲鱼自动化】Cookie 过期告警\n状态: {msg}\n"
                "静默刷新: 闲管家IM/CookieCloud/浏览器DB 均未获取到新 Cookie\n"
                "请在 BitBrowser 中登录闲鱼，或手动打开 Dashboard 更新 Cookie",
                event="cookie_expire",
            )
            return

        # 3) 验证新 Cookie
        valid = self._validate_sync(new_cookie)
        if not valid:
            logger.info("Cookie 静默刷新: 新 Cookie 验证失败")
            self._last_refresh_ok = False
            self._send_notification(
                "⚠️ Cookie 自动刷新失败",
                f"【闲鱼自动化】Cookie 过期告警\n状态: {msg}\n静默刷新: 获取到新 Cookie 但验证失败\n请手动打开 Dashboard 更新 Cookie",
                event="cookie_expire",
            )
            return

        # 4) 保存并通知
        self._total_refreshes += 1
        self._last_refresh_at = time.time()
        self._last_refresh_ok = True
        self._last_check_ok = True
        self._last_check_msg = "静默刷新成功"

        from src.core.cookie_store import save_cookie

        save_cookie(new_cookie, persist=True, source=self._last_refresh_source)

        _source_labels = {
            "goofish_im": "闲管家IM",
            "cookiecloud": "CookieCloud",
            "browser_db": "浏览器数据库",
        }
        source_label = _source_labels.get(self._last_refresh_source, self._last_refresh_source)
        logger.info(f"Cookie 静默刷新成功 (来源={source_label}, length={len(new_cookie)})")

        self._send_notification(
            "Cookie 自动刷新成功",
            f"【闲鱼自动化】✅ Cookie 已自动刷新\n来源: {source_label}\n状态: 验证通过\n系统已恢复正常运行",
            event="cookie_refresh",
        )

        if self._on_refreshed:
            try:
                self._on_refreshed(new_cookie)
            except Exception as exc:
                logger.error(f"Cookie 刷新回调失败: {exc}")

    @staticmethod
    def _send_notification(title: str, body: str, *, event: str = "") -> None:
        from src.core.notify import send_system_notification

        send_system_notification(body, event=event)

    @staticmethod
    def _check_health(cookie_text: str) -> tuple[bool, str]:
        if not cookie_text:
            return False, "Cookie 未配置"
        try:
            from src.core.cookie_health import CookieHealthChecker

            checker = CookieHealthChecker(cookie_text, timeout_seconds=10.0)
            result = checker.check_sync(force=True)
            return bool(result.get("healthy")), result.get("message", "")
        except Exception as exc:
            return False, f"检查异常: {exc}"

    @staticmethod
    def _validate_sync(cookie_str: str) -> bool:
        try:
            from src.core.cookie_health import CookieHealthChecker

            checker = CookieHealthChecker(cookie_str, timeout_seconds=10.0)
            result = checker.check_sync(force=True)
            return bool(result.get("healthy"))
        except Exception:
            return True  # 验证异常时放行

    @staticmethod
    def _save_to_env(cookie_str: str) -> None:
        from src.core.cookie_store import save_cookie

        save_cookie(cookie_str, persist=True)
