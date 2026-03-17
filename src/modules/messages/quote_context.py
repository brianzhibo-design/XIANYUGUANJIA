"""报价上下文存储 — 管理会话级报价上下文的内存缓存与 Ledger 恢复。

从 MessagesService 中抽取，负责 _quote_context_memory 字典的读写、
过期清理、从 QuoteLedger 恢复历史上下文。
"""

from __future__ import annotations

import time
from typing import Any

from src.core.logger import get_logger

_logger = get_logger()


class QuoteContextStore:
    """管理会话级报价上下文的内存缓存。"""

    def __init__(
        self,
        *,
        context_memory_enabled: bool = True,
        context_memory_ttl_seconds: int = 3600,
    ):
        self.context_memory_enabled = context_memory_enabled
        self.context_memory_ttl_seconds = context_memory_ttl_seconds
        self.logger = _logger
        self._memory: dict[str, dict[str, Any]] = {}
        self._ledger_miss_cache: set[str] = set()

    def prune(self) -> None:
        if not self.context_memory_enabled or not self._memory:
            return
        now_ts = time.time()
        stale_ids = [
            session_id
            for session_id, payload in self._memory.items()
            if (now_ts - float(payload.get("updated_at", 0.0))) > self.context_memory_ttl_seconds
        ]
        for session_id in stale_ids:
            self._memory.pop(session_id, None)

    def get(self, session_id: str) -> dict[str, Any]:
        if not self.context_memory_enabled or not session_id:
            return {}
        self.prune()
        payload = self._memory.get(session_id)
        if isinstance(payload, dict):
            return dict(payload)
        if session_id not in self._ledger_miss_cache:
            recovered = self._recover_from_ledger(session_id)
            if recovered:
                self._memory[session_id] = recovered
                return dict(recovered)
            self._ledger_miss_cache.add(session_id)
        return {}

    def _recover_from_ledger(self, session_id: str) -> dict[str, Any] | None:
        """尝试从 QuoteLedger 恢复报价上下文（进程重启后内存丢失的场景）。"""
        try:
            from src.modules.quote.ledger import get_quote_ledger

            ledger = get_quote_ledger()
            record = ledger.find_by_session(session_id, max_age_seconds=self.context_memory_ttl_seconds)
            if not record:
                return None
            recovered: dict[str, Any] = {"updated_at": record.get("created_at", time.time())}
            for field in ("origin", "destination", "weight", "courier_choice"):
                val = record.get(field)
                if val and (not isinstance(val, str) or val.strip()):
                    recovered[field] = val
            quote_rows = record.get("quote_rows")
            if isinstance(quote_rows, list) and quote_rows:
                recovered["last_quote_rows"] = quote_rows
            self.logger.info(
                "从 QuoteLedger 恢复会话上下文: session=%s, origin=%s, dest=%s, rows=%d",
                session_id,
                recovered.get("origin", ""),
                recovered.get("destination", ""),
                len(recovered.get("last_quote_rows", [])),
            )
            return recovered if len(recovered) > 1 else None
        except Exception as exc:
            self.logger.warning("QuoteLedger 恢复失败: %s", exc)
            return None

    def update(self, session_id: str, **kwargs: Any) -> None:
        if not self.context_memory_enabled or not session_id:
            return
        self.prune()
        payload = dict(self._memory.get(session_id) or {})
        for key, value in kwargs.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            payload[key] = value
        payload["updated_at"] = time.time()
        self._memory[session_id] = payload

    def append_chat_history(self, session_id: str, role: str, text: str) -> None:
        if not self.context_memory_enabled or not session_id or not text:
            return
        payload = dict(self._memory.get(session_id) or {})
        history = list(payload.get("chat_history") or [])
        history.append({"role": role, "text": text[:200], "ts": time.time()})
        if len(history) > 5:
            history = history[-5:]
        payload["chat_history"] = history
        payload["updated_at"] = time.time()
        self._memory[session_id] = payload

    def has_context(self, session_id: str) -> bool:
        context = self.get(session_id)
        if not context:
            return False
        return bool(
            context.get("origin")
            or context.get("destination")
            or context.get("weight")
            or context.get("pending_missing_fields")
            or context.get("last_quote_rows")
            or context.get("courier_choice")
        )
