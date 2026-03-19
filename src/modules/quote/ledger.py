"""QuoteLedger — 持久化报价记录，支持跨进程查询。

解决的问题：MessagesService 的 _quote_context_memory 是纯内存字典，
dashboard_server 的回调处理器无法访问。QuoteLedger 通过 SQLite
持久化报价记录，使订单回调可以查找匹配的聊天报价。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_DIR = Path(__file__).resolve().parents[3] / "data"
_DB_NAME = "quote_ledger.db"


class QuoteLedger:
    """SQLite-backed quote record store."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
            db_path = _DEFAULT_DB_DIR / _DB_NAME
        self._db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quote_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    peer_name TEXT NOT NULL DEFAULT '',
                    sender_user_id TEXT NOT NULL DEFAULT '',
                    item_id TEXT NOT NULL DEFAULT '',
                    origin TEXT NOT NULL DEFAULT '',
                    destination TEXT NOT NULL DEFAULT '',
                    weight REAL,
                    courier_choice TEXT NOT NULL DEFAULT '',
                    quote_rows_json TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qr_peer_name
                ON quote_records (peer_name, created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qr_peer_item
                ON quote_records (peer_name, item_id, created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qr_sender_user_id
                ON quote_records (sender_user_id, created_at DESC)
            """)

    def record_quote(
        self,
        *,
        session_id: str,
        peer_name: str = "",
        sender_user_id: str = "",
        item_id: str = "",
        origin: str = "",
        destination: str = "",
        weight: float | None = None,
        courier_choice: str = "",
        quote_rows: list[dict[str, Any]] | None = None,
    ) -> int:
        """Write a quote record. Returns the row id."""
        now = time.time()
        rows_json = json.dumps(quote_rows or [], ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO quote_records
                   (session_id, peer_name, sender_user_id, item_id,
                    origin, destination, weight, courier_choice,
                    quote_rows_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    peer_name,
                    sender_user_id,
                    item_id,
                    origin,
                    destination,
                    weight,
                    courier_choice,
                    rows_json,
                    now,
                ),
            )
            return cur.lastrowid or 0

    def find_by_buyer(
        self,
        buyer_nick: str,
        *,
        item_id: str = "",
        max_age_seconds: int = 7200,
        sender_user_id: str = "",
    ) -> dict[str, Any] | None:
        """Find the most recent quote matching buyer nick (+ optional item_id).

        Tries in order: (peer_name + item_id) -> (peer_name) -> (sender_user_id).
        The sender_user_id fallback handles cases where peer_name (IM nickname)
        differs from buyer_nick (order nickname).
        """
        cutoff = time.time() - max_age_seconds
        with self._connect() as conn:
            if item_id:
                row = conn.execute(
                    """SELECT * FROM quote_records
                       WHERE peer_name = ? AND item_id = ? AND created_at > ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (buyer_nick, item_id, cutoff),
                ).fetchone()
                if row:
                    return self._row_to_dict(row)

            row = conn.execute(
                """SELECT * FROM quote_records
                   WHERE peer_name = ? AND created_at > ?
                   ORDER BY created_at DESC LIMIT 1""",
                (buyer_nick, cutoff),
            ).fetchone()
            if row:
                return self._row_to_dict(row)

            if sender_user_id:
                row = conn.execute(
                    """SELECT * FROM quote_records
                       WHERE sender_user_id = ? AND created_at > ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (sender_user_id, cutoff),
                ).fetchone()
                if row:
                    return self._row_to_dict(row)

            return None

    def find_by_session(
        self,
        session_id: str,
        *,
        max_age_seconds: int = 7200,
    ) -> dict[str, Any] | None:
        cutoff = time.time() - max_age_seconds
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM quote_records
                   WHERE session_id = ? AND created_at > ?
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id, cutoff),
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def cleanup(self, max_age_seconds: int = 86400) -> int:
        """Remove records older than max_age_seconds. Returns deleted count."""
        cutoff = time.time() - max_age_seconds
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM quote_records WHERE created_at < ?", (cutoff,))
            return cur.rowcount

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        try:
            d["quote_rows"] = json.loads(d.pop("quote_rows_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            d["quote_rows"] = []
        return d


_instance: QuoteLedger | None = None


def get_quote_ledger(db_path: str | Path | None = None) -> QuoteLedger:
    """Module-level singleton accessor."""
    global _instance
    if _instance is None:
        _instance = QuoteLedger(db_path)
    return _instance
