"""Manual takeover mode management for message sessions."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ManualModeState:
    session_id: str
    enabled: bool
    updated_at: float
    expires_at: float | None


@dataclass
class ManualModeResult:
    state: ManualModeState
    toggled: bool = False
    timeout_recovered: bool = False
    smart_recovered: bool = False


class ManualModeStore:
    """Session-scoped manual takeover state persisted in SQLite."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        toggle_keyword: str = "。",
        timeout_seconds: int = 600,
        resume_after_seconds: int = 300,
    ) -> None:
        self.db_path = Path(db_path)
        self.toggle_keyword = toggle_keyword
        self.timeout_seconds = max(0, int(timeout_seconds))
        self.resume_after_seconds = max(0, int(resume_after_seconds))
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_manual_mode (
                    session_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL,
                    last_seller_msg_at REAL,
                    last_buyer_msg_at REAL
                )
                """
            )
            # Migrate: add columns if missing (for existing DBs)
            try:
                conn.execute("SELECT last_seller_msg_at FROM message_manual_mode LIMIT 0")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE message_manual_mode ADD COLUMN last_seller_msg_at REAL")
            try:
                conn.execute("SELECT last_buyer_msg_at FROM message_manual_mode LIMIT 0")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE message_manual_mode ADD COLUMN last_buyer_msg_at REAL")
            conn.commit()

    def _now(self, now: float | None = None) -> float:
        return float(now if now is not None else time.time())

    def _upsert(self, session_id: str, enabled: bool, now_ts: float) -> ManualModeState:
        expires_at = (now_ts + self.timeout_seconds) if (enabled and self.timeout_seconds > 0) else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO message_manual_mode(session_id, enabled, updated_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    enabled=excluded.enabled,
                    updated_at=excluded.updated_at,
                    expires_at=excluded.expires_at
                """,
                (session_id, 1 if enabled else 0, now_ts, expires_at),
            )
            conn.commit()
        return ManualModeState(session_id=session_id, enabled=enabled, updated_at=now_ts, expires_at=expires_at)

    def _get_raw(self, session_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id, enabled, updated_at, expires_at, "
                "last_seller_msg_at, last_buyer_msg_at "
                "FROM message_manual_mode WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row

    def get_state(self, session_id: str, *, now: float | None = None) -> ManualModeResult:
        now_ts = self._now(now)
        row = self._get_raw(session_id)
        if row is None:
            state = ManualModeState(session_id=session_id, enabled=False, updated_at=now_ts, expires_at=None)
            return ManualModeResult(state=state)

        enabled = bool(row["enabled"])
        expires_at = row["expires_at"]

        if enabled and expires_at is not None and float(expires_at) <= now_ts:
            state = self._upsert(session_id, False, now_ts)
            return ManualModeResult(state=state, timeout_recovered=True)

        if enabled and self.resume_after_seconds > 0:
            last_seller = row["last_seller_msg_at"]
            last_buyer = row["last_buyer_msg_at"]
            if last_buyer is not None and last_seller is not None:
                if float(last_buyer) > float(last_seller) and (now_ts - float(last_buyer)) >= self.resume_after_seconds:
                    state = self._upsert(session_id, False, now_ts)
                    return ManualModeResult(state=state, smart_recovered=True)

        state = ManualModeState(
            session_id=row["session_id"],
            enabled=enabled,
            updated_at=float(row["updated_at"]),
            expires_at=float(expires_at) if expires_at is not None else None,
        )
        return ManualModeResult(state=state)

    def set_state(self, session_id: str, enabled: bool, *, now: float | None = None) -> ManualModeState:
        now_ts = self._now(now)
        return self._upsert(session_id, enabled, now_ts)

    def record_seller_activity(self, session_id: str, *, now: float | None = None) -> None:
        """Record seller message timestamp for smart resume logic."""
        now_ts = self._now(now)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO message_manual_mode(session_id, enabled, updated_at, last_seller_msg_at)
                VALUES (?, 0, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_seller_msg_at=excluded.last_seller_msg_at
                """,
                (session_id, now_ts, now_ts),
            )
            conn.commit()

    def record_buyer_activity(self, session_id: str, *, now: float | None = None) -> None:
        """Record buyer message timestamp for smart resume logic."""
        now_ts = self._now(now)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO message_manual_mode(session_id, enabled, updated_at, last_buyer_msg_at)
                VALUES (?, 0, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_buyer_msg_at=excluded.last_buyer_msg_at
                """,
                (session_id, now_ts, now_ts),
            )
            conn.commit()

    def toggle(self, session_id: str, *, now: float | None = None) -> ManualModeState:
        current = self.get_state(session_id, now=now).state
        return self.set_state(session_id, not current.enabled, now=now)

    def disable(self, session_id: str, *, now: float | None = None) -> ManualModeState:
        return self.set_state(session_id, False, now=now)

    def list_active(self, *, now: float | None = None) -> list[ManualModeState]:
        now_ts = self._now(now)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id, enabled, updated_at, expires_at, "
                "last_seller_msg_at, last_buyer_msg_at "
                "FROM message_manual_mode WHERE enabled = 1"
            ).fetchall()
        result: list[ManualModeState] = []
        for row in rows:
            expires_at = row["expires_at"]
            if expires_at is not None and float(expires_at) <= now_ts:
                self._upsert(row["session_id"], False, now_ts)
                continue
            result.append(ManualModeState(
                session_id=row["session_id"],
                enabled=True,
                updated_at=float(row["updated_at"]),
                expires_at=float(expires_at) if expires_at is not None else None,
            ))
        return result

    def process_message(self, session_id: str, message: str, *, now: float | None = None) -> ManualModeResult:
        now_ts = self._now(now)
        baseline = self.get_state(session_id, now=now_ts)
        if str(message or "").strip() == self.toggle_keyword:
            state = self.toggle(session_id, now=now_ts)
            return ManualModeResult(state=state, toggled=True, timeout_recovered=baseline.timeout_recovered)
        return baseline
