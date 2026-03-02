from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from src.core.logger import get_logger


class CookieRenewalManager:
    """Cookie 续期闭环：失效检测 -> 刷新替换 -> token重取 -> WS重连 -> 审计。"""

    def __init__(
        self,
        *,
        api_client: Any,
        ws_client: Any,
        cookie_loader: Callable[[], str],
        audit_log_path: str,
        check_interval_seconds: int = 300,
        min_renew_interval_seconds: int = 30,
        failure_backoff_base_seconds: float = 2.0,
        failure_backoff_max_seconds: float = 120.0,
        failure_jitter_seconds: float = 0.6,
        risk_retry_budget: int = 5,
        risk_cooldown_seconds: float = 300.0,
        browser_cookie_provider: Callable[[], Awaitable[str]] | None = None,
        cookie_file_path: str = "",
        cookie_source_adapter: Any | None = None,
    ):
        self.api_client = api_client
        self.ws_client = ws_client
        self.cookie_loader = cookie_loader
        self.browser_cookie_provider = browser_cookie_provider
        self.cookie_file_path = Path(cookie_file_path).expanduser() if str(cookie_file_path or "").strip() else None
        self.cookie_source_adapter = cookie_source_adapter
        self.audit_log_path = Path(audit_log_path)
        self.check_interval_seconds = max(30, int(check_interval_seconds or 300))
        self.min_renew_interval_seconds = max(1, int(min_renew_interval_seconds or 30))
        self.failure_backoff_base_seconds = max(0.1, float(failure_backoff_base_seconds or 2.0))
        self.failure_backoff_max_seconds = max(1.0, float(failure_backoff_max_seconds or 120.0))
        self.failure_jitter_seconds = max(0.0, float(failure_jitter_seconds or 0.0))
        self.risk_retry_budget = max(1, int(risk_retry_budget or 1))
        self.risk_cooldown_seconds = max(1.0, float(risk_cooldown_seconds or 300.0))

        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self.logger = get_logger()

        self._last_renew_attempt_at = 0.0
        self._last_cookie_refresh_at: float | None = None
        self._last_token_refresh_at: float | None = None
        self._recover_count = 0
        self._consecutive_failures = 0
        self._last_cookie_fp = ""
        self._state = "idle"

        self._risk_fail_count = 0
        self._last_risk_code: str | None = None
        self._next_retry_at: float | None = None

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                # 周期式：主动从统一源抓 cookie（浏览器优先，失败降级）
                await self._get_latest_cookie_snapshot(reason="periodic_cookie_probe")
                ok = await self.api_client.has_login()
                if not ok:
                    await self.renew(reason="periodic_has_login_failed")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._state = "failed_detect"
                await self._audit(event="periodic_check_error", ok=False, reason=str(exc), state="failed_detect")
            await asyncio.sleep(self.check_interval_seconds)

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        """状态接口：可用于 dashboard/status 输出。"""

        return {
            "state": self._state,
            "last_cookie_refresh": self._fmt_ts(self._last_cookie_refresh_at),
            "last_token_refresh": self._fmt_ts(self._last_token_refresh_at),
            "recover_count": int(self._recover_count),
            "consecutive_failures": int(self._consecutive_failures),
            "risk_fail_count": int(self._risk_fail_count),
            "last_risk_code": self._last_risk_code,
            "next_retry_at": self._fmt_ts(self._next_retry_at),
        }

    async def handle_auth_failure(self, reason: str) -> bool:
        return await self.renew(reason=reason)

    async def renew(self, *, reason: str) -> bool:
        async with self._lock:
            now = time.time()
            if (now - self._last_renew_attempt_at) < float(self.min_renew_interval_seconds):
                self._state = "suppressed"
                await self._audit(
                    event="renew_suppressed",
                    ok=False,
                    reason=f"{reason}:min_interval",
                    state="suppressed",
                )
                return False
            self._last_renew_attempt_at = now

            # 触发式：失败时先尝试统一 cookie source adapter（浏览器优先，失败降级）
            snap = await self._get_latest_cookie_snapshot(reason=f"triggered_cookie_probe:{reason}")
            auto_cookie = str((getattr(snap, "cookie_text", "") if snap is not None else "") or (snap.get("cookie_text", "") if isinstance(snap, dict) else "") or "").strip()
            cookie_text = str(auto_cookie or self.cookie_loader() or "").strip()
            if not cookie_text:
                self._consecutive_failures += 1
                self._state = "waiting_new_cookie"
                await self._schedule_retry(self._consecutive_failures)
                await self._audit(
                    event="renew_waiting_cookie",
                    ok=False,
                    reason=f"{reason}:empty_cookie_source",
                    state="waiting_new_cookie",
                )
                await self._sleep_until_retry()
                return False

            fp = self._cookie_fingerprint(cookie_text)
            changed = bool(cookie_text != str(getattr(self.api_client, "cookie_text", "") or "").strip())
            if (not changed) and self._last_cookie_fp and fp == self._last_cookie_fp and self._consecutive_failures > 0:
                self._state = "waiting_new_cookie"
                await self._schedule_retry(self._consecutive_failures)
                await self._audit(
                    event="renew_waiting_cookie",
                    ok=False,
                    reason=f"{reason}:same_cookie_fingerprint",
                    changed=False,
                    state="waiting_new_cookie",
                )
                await self._sleep_until_retry()
                return False

            # 原子替换前备份，失败可回滚
            prev_cookie = str(getattr(self.api_client, "cookie_text", "") or "").strip()
            prev_device_id = str(getattr(self.api_client, "device_id", "") or "")
            prev_user_id = str(getattr(self.api_client, "user_id", "") or "")

            try:
                self._state = "detected_invalid"
                await self._audit(event="renew_start", ok=True, reason=reason, changed=changed, state="detected_invalid")

                # 先校验 token，再提交替换（避免脏 cookie 覆盖现网）
                await self._validate_candidate_cookie(cookie_text)

                await self._apply_cookie_atomically(cookie_text)
                self._last_cookie_fp = fp
                self._last_cookie_refresh_at = time.time()
                self._persist_cookie(cookie_text)

                self._recover_count += 1
                self._consecutive_failures = 0
                self._risk_fail_count = 0
                self._last_risk_code = None
                self._next_retry_at = None
                self._state = "recovered"
                await self._audit(event="renew_ok", ok=True, reason=reason, changed=changed, state="recovered")
                self.logger.info(
                    f"Cookie renewal success, reason={reason}, changed={changed}, "
                    f"recover_count={self._recover_count}, last_cookie_refresh={self.status()['last_cookie_refresh']}, "
                    f"last_token_refresh={self.status()['last_token_refresh']}"
                )
                return True
            except Exception as exc:
                self._consecutive_failures += 1
                await self._rollback_cookie_context(prev_cookie, prev_device_id, prev_user_id)

                code, category = self._classify_failure(reason=reason, exc=exc)
                self._last_risk_code = code

                if category == "transient_risk":
                    self._risk_fail_count += 1
                    budget_exhausted = self._risk_fail_count >= self.risk_retry_budget
                    self._state = "waiting_new_cookie" if budget_exhausted else "recoverable_backoff"
                    retry_seed = max(self._consecutive_failures, self._risk_fail_count)
                    await self._schedule_retry(retry_seed, cooldown=budget_exhausted)
                    await self._audit(
                        event="renew_failed_risk",
                        ok=False,
                        reason=f"{reason}:{exc}",
                        changed=changed,
                        state=self._state,
                    )
                    await self._sleep_until_retry()
                    return False

                if category == "cookie_invalid":
                    self._state = "waiting_new_cookie"
                    await self._schedule_retry(self._consecutive_failures)
                    await self._audit(
                        event="renew_failed",
                        ok=False,
                        reason=f"{reason}:{exc}",
                        changed=changed,
                        state="waiting_new_cookie",
                    )
                    await self._sleep_until_retry()
                    return False

                self._state = "failed_reconnect"
                await self._schedule_retry(self._consecutive_failures)
                await self._audit(
                    event="renew_failed",
                    ok=False,
                    reason=f"{reason}:{exc}",
                    changed=changed,
                    state="failed_reconnect",
                )
                self.logger.warning(f"Cookie renewal failed: {reason}, err={exc}")
                await self._sleep_until_retry()
                return False

    async def _validate_candidate_cookie(self, cookie_text: str) -> None:
        old_cookie = str(getattr(self.api_client, "cookie_text", "") or "").strip()
        try:
            self.api_client.update_cookie(cookie_text)
            ok = await self.api_client.has_login()
            if not ok:
                raise RuntimeError("cookie_invalid_or_expired")
            await self.api_client.get_token(force_refresh=True)
            self._last_token_refresh_at = time.time()
        finally:
            self.api_client.update_cookie(old_cookie)

    async def _apply_cookie_atomically(self, cookie_text: str) -> None:
        self.api_client.update_cookie(cookie_text)
        ws_update_auth = getattr(self.ws_client, "update_auth_context", None)
        if callable(ws_update_auth):
            ws_update_auth(
                cookie=cookie_text,
                device_id=str(getattr(self.api_client, "device_id", "") or ""),
                my_user_id=str(getattr(self.api_client, "user_id", "") or ""),
            )
        else:
            self.ws_client.update_cookie(cookie_text)
        await self.ws_client.force_reconnect("cookie_renewed")

    async def _rollback_cookie_context(self, cookie_text: str, device_id: str, user_id: str) -> None:
        try:
            self.api_client.update_cookie(cookie_text)
            ws_update_auth = getattr(self.ws_client, "update_auth_context", None)
            if callable(ws_update_auth):
                ws_update_auth(cookie=cookie_text, device_id=device_id, my_user_id=user_id)
            else:
                self.ws_client.update_cookie(cookie_text)
        except Exception:
            return


    async def _get_latest_cookie_snapshot(self, *, reason: str) -> Any | None:
        adapter_getter = getattr(self.cookie_source_adapter, "get_latest_cookie", None)
        if callable(adapter_getter):
            try:
                snap = await adapter_getter()
                cookie_text = str((getattr(snap, "cookie_text", "") if snap is not None else "") or (snap.get("cookie_text", "") if isinstance(snap, dict) else "") or "").strip()
                if cookie_text:
                    self._persist_cookie(cookie_text)
                    await self._audit(
                        event="cookie_source_refreshed",
                        ok=True,
                        reason=reason,
                        state=self._state,
                    )
                    return snap
            except Exception as exc:
                await self._audit(
                    event="cookie_source_refresh_failed",
                    ok=False,
                    reason=f"{reason}:{exc}",
                    state=self._state,
                )

        cookie_text = await self._try_auto_refresh_cookie_source(reason=reason)
        if not cookie_text:
            return None
        return {
            "cookie_text": cookie_text,
            "fingerprint": self._cookie_fingerprint(cookie_text),
            "updated_at": time.time(),
        }

    async def _try_auto_refresh_cookie_source(self, *, reason: str) -> str:
        if not callable(self.browser_cookie_provider):
            return ""
        try:
            cookie_text = str(await self.browser_cookie_provider() or "").strip()
            if not cookie_text:
                return ""
            self._persist_cookie(cookie_text)
            await self._audit(
                event="cookie_source_refreshed",
                ok=True,
                reason=reason,
                state=self._state,
            )
            return cookie_text
        except Exception as exc:
            await self._audit(
                event="cookie_source_refresh_failed",
                ok=False,
                reason=f"{reason}:{exc}",
                state=self._state,
            )
            return ""

    def _persist_cookie(self, cookie_text: str) -> None:
        if self.cookie_file_path is None:
            return
        self.cookie_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.cookie_file_path.write_text(str(cookie_text or "").strip(), encoding="utf-8")

    async def _schedule_retry(self, fail_count: int, *, cooldown: bool = False) -> None:
        if cooldown:
            wait_seconds = self.risk_cooldown_seconds
        else:
            wait_seconds = min(
                self.failure_backoff_base_seconds * (2 ** max(0, int(fail_count) - 1)),
                self.failure_backoff_max_seconds,
            )
            if self.failure_jitter_seconds > 0:
                wait_seconds += random.uniform(0.0, self.failure_jitter_seconds)
        self._next_retry_at = time.time() + max(0.1, wait_seconds)

    async def _sleep_until_retry(self) -> None:
        if self._next_retry_at is None:
            return
        sleep_seconds = max(0.0, self._next_retry_at - time.time())
        await asyncio.sleep(sleep_seconds)

    @staticmethod
    def _classify_failure(*, reason: str, exc: Exception) -> tuple[str, str]:
        text = f"{reason} {exc}".strip()
        lower = text.lower()

        has_validate = "fail_sys_user_validate" in lower or "rgv587" in lower
        has_invalid = any(k in lower for k in ["cookie_invalid", "cookie expired", "session_expired", "login required"])

        if has_validate and has_invalid:
            return "FAIL_SYS_USER_VALIDATE", "cookie_invalid"
        if has_validate:
            return "FAIL_SYS_USER_VALIDATE", "transient_risk"
        if has_invalid:
            return "COOKIE_INVALID", "cookie_invalid"
        return "UNKNOWN", "unknown"

    async def _audit(
        self,
        *,
        event: str,
        ok: bool,
        reason: str,
        changed: bool | None = None,
        state: str,
    ) -> None:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": int(time.time()),
            "event": event,
            "ok": bool(ok),
            "state": state,
            "reason": reason,
            "last_cookie_refresh": self._fmt_ts(self._last_cookie_refresh_at),
            "last_token_refresh": self._fmt_ts(self._last_token_refresh_at),
            "recover_count": int(self._recover_count),
            "risk_fail_count": int(self._risk_fail_count),
            "last_risk_code": self._last_risk_code,
            "next_retry_at": self._fmt_ts(self._next_retry_at),
        }
        if changed is not None:
            row["changed"] = bool(changed)
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _fmt_ts(ts: float | None) -> str | None:
        if ts is None:
            return None
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

    @staticmethod
    def _cookie_fingerprint(cookie_text: str) -> str:
        return hashlib.sha256(str(cookie_text or "").strip().encode("utf-8")).hexdigest()


def build_cookie_loader(*, inline_cookie: str, cookie_file: str) -> Callable[[], str]:
    inline_cookie = str(inline_cookie or "").strip()
    cookie_file = str(cookie_file or "").strip()

    def _loader() -> str:
        if cookie_file:
            p = Path(cookie_file)
            if p.exists():
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    return text
        return str(os.getenv("LITE_COOKIE") or os.getenv("XIANYU_COOKIE_1") or inline_cookie or "").strip()

    return _loader
