"""报价上下文存储 — 管理会话级报价上下文的 SQLite 持久化 + 内存缓存。

支持进程重启后上下文恢复、双向 chat_history 记录、TTL 自动过期。
通过 context_persistence_enabled 开关可回退到纯内存模式。
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from src.core.logger import get_logger

_logger = get_logger()

_CONTEXT_DB_PATH = "data/session_context.db"
_SERIALIZED_FIELDS = ("last_quote_rows", "chat_history", "pending_missing_fields")


class QuoteContextStore:
    """管理会话级报价上下文的 SQLite 持久化 + 内存 write-through 缓存。"""

    def __init__(
        self,
        *,
        context_memory_enabled: bool = True,
        context_memory_ttl_seconds: int = 86400,
        context_persistence_enabled: bool = True,
        db_path: str = _CONTEXT_DB_PATH,
    ):
        self.context_memory_enabled = context_memory_enabled
        self.context_memory_ttl_seconds = context_memory_ttl_seconds
        self.context_persistence_enabled = context_persistence_enabled
        self.logger = _logger
        self._memory: dict[str, dict[str, Any]] = {}
        self._ledger_miss_cache: set[str] = set()
        self._db_path = db_path
        if self.context_persistence_enabled:
            self._init_db()

    def _init_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=3000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_context (
                    session_id TEXT PRIMARY KEY,
                    origin TEXT DEFAULT '',
                    destination TEXT DEFAULT '',
                    weight REAL,
                    courier_choice TEXT DEFAULT '',
                    last_quote_rows TEXT DEFAULT '[]',
                    phase TEXT DEFAULT 'presale',
                    pending_missing_fields TEXT DEFAULT '',
                    item_name TEXT DEFAULT '',
                    peer_name TEXT DEFAULT '',
                    last_intent TEXT DEFAULT '',
                    chat_history TEXT DEFAULT '[]',
                    updated_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ctx_updated ON session_context(updated_at)"
            )
            conn.commit()
        finally:
            conn.close()

    def _db_get(self, session_id: str) -> dict[str, Any] | None:
        if not self.context_persistence_enabled:
            return None
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "SELECT * FROM session_context WHERE session_id = ? AND updated_at > ?",
                    (session_id, time.time() - self.context_memory_ttl_seconds),
                ).fetchone()
                if not row:
                    return None
                payload: dict[str, Any] = {}
                for key in row.keys():
                    if key == "session_id":
                        continue
                    val = row[key]
                    if key in _SERIALIZED_FIELDS and isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if val is not None and val != "":
                        payload[key] = val
                return payload if payload else None
            finally:
                conn.close()
        except Exception as exc:
            self.logger.warning("session_context db_get error: %s", exc)
            return None

    def _db_upsert(self, session_id: str, payload: dict[str, Any]) -> None:
        if not self.context_persistence_enabled:
            return
        try:
            now = time.time()
            data = dict(payload)
            for field in _SERIALIZED_FIELDS:
                if field in data and not isinstance(data[field], str):
                    data[field] = json.dumps(data[field], ensure_ascii=False)
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """INSERT INTO session_context
                        (session_id, origin, destination, weight, courier_choice,
                         last_quote_rows, phase, pending_missing_fields,
                         item_name, peer_name, last_intent, chat_history,
                         updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        origin = COALESCE(NULLIF(excluded.origin, ''), origin),
                        destination = COALESCE(NULLIF(excluded.destination, ''), destination),
                        weight = COALESCE(excluded.weight, weight),
                        courier_choice = COALESCE(NULLIF(excluded.courier_choice, ''), courier_choice),
                        last_quote_rows = CASE
                            WHEN excluded.last_quote_rows != '[]' THEN excluded.last_quote_rows
                            ELSE last_quote_rows END,
                        phase = COALESCE(NULLIF(excluded.phase, ''), phase),
                        pending_missing_fields = excluded.pending_missing_fields,
                        item_name = COALESCE(NULLIF(excluded.item_name, ''), item_name),
                        peer_name = COALESCE(NULLIF(excluded.peer_name, ''), peer_name),
                        last_intent = COALESCE(NULLIF(excluded.last_intent, ''), last_intent),
                        chat_history = excluded.chat_history,
                        updated_at = excluded.updated_at
                    """,
                    (
                        session_id,
                        str(data.get("origin", "") or ""),
                        str(data.get("destination", "") or ""),
                        data.get("weight"),
                        str(data.get("courier_choice", "") or ""),
                        str(data.get("last_quote_rows", "[]") or "[]"),
                        str(data.get("phase", "presale") or "presale"),
                        str(data.get("pending_missing_fields", "") or ""),
                        str(data.get("item_name", "") or ""),
                        str(data.get("peer_name", "") or ""),
                        str(data.get("last_intent", "") or ""),
                        str(data.get("chat_history", "[]") or "[]"),
                        now,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            self.logger.warning("session_context db_upsert error: %s", exc)

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
        if self.context_persistence_enabled and stale_ids:
            try:
                cutoff = now_ts - self.context_memory_ttl_seconds
                conn = sqlite3.connect(self._db_path)
                try:
                    conn.execute(
                        "DELETE FROM session_context WHERE updated_at < ?", (cutoff,)
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception:
                pass

    def get(self, session_id: str) -> dict[str, Any]:
        if not self.context_memory_enabled or not session_id:
            return {}
        self.prune()
        payload = self._memory.get(session_id)
        if isinstance(payload, dict):
            return dict(payload)

        db_payload = self._db_get(session_id)
        if db_payload:
            self._memory[session_id] = db_payload
            return dict(db_payload)

        if session_id not in self._ledger_miss_cache:
            recovered = self._recover_from_ledger(session_id)
            if recovered:
                self._memory[session_id] = recovered
                self._db_upsert(session_id, recovered)
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
        self._db_upsert(session_id, payload)

    def append_chat_history(self, session_id: str, role: str, text: str) -> None:
        if not self.context_memory_enabled or not session_id or not text:
            return
        payload = dict(self._memory.get(session_id) or {})
        history = list(payload.get("chat_history") or [])
        history.append({"role": role, "text": text[:500], "ts": time.time()})
        if len(history) > 20:
            history = history[-20:]
        payload["chat_history"] = history
        payload["updated_at"] = time.time()
        self._memory[session_id] = payload
        self._db_upsert(session_id, payload)

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
