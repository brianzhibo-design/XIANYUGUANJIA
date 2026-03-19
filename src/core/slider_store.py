"""Persistent storage for slider verification events.

Records every slider trigger, attempt, and result into SQLite
so we can analyze success rates, failure patterns, and cookie TTL.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "slider_events.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS slider_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_ts TEXT NOT NULL,
    trigger_source TEXT,
    rgv587_consecutive INTEGER DEFAULT 0,

    browser_strategy TEXT,
    browser_connect_ms INTEGER,

    attempt_num INTEGER DEFAULT 0,
    slider_type TEXT,

    nc_track_width INTEGER,
    nc_drag_distance INTEGER,

    puzzle_bg_found INTEGER DEFAULT 0,
    puzzle_slice_found INTEGER DEFAULT 0,
    puzzle_gap_x INTEGER,
    puzzle_match_score REAL,

    result TEXT NOT NULL,
    fail_reason TEXT,
    error_message TEXT,
    screenshot_path TEXT,

    cookie_applied INTEGER DEFAULT 0,
    cookie_fields_count INTEGER,
    cookie_has_h5tk INTEGER DEFAULT 0,

    prev_cookie_applied_at TEXT,
    cookie_ttl_seconds INTEGER,

    total_duration_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_slider_trigger_ts ON slider_events(trigger_ts);
CREATE INDEX IF NOT EXISTS idx_slider_result ON slider_events(result);
CREATE INDEX IF NOT EXISTS idx_slider_created ON slider_events(created_at);
"""


class SliderEventStore:
    _instance: SliderEventStore | None = None
    _lock = threading.Lock()

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = os.path.abspath(db_path or _DB_PATH)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._local = threading.local()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> SliderEventStore:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        conn = self._conn
        conn.executescript(_SCHEMA)
        conn.commit()

    def record_event(self, **kwargs: Any) -> int:
        """Insert a slider event. Returns the row id."""
        if "trigger_ts" not in kwargs:
            kwargs["trigger_ts"] = datetime.now(timezone.utc).isoformat()

        columns = list(kwargs.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_str = ", ".join(columns)
        values = [kwargs[c] for c in columns]

        try:
            conn = self._conn
            cur = conn.execute(
                f"INSERT INTO slider_events ({col_str}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
            return cur.lastrowid or 0
        except sqlite3.Error as exc:
            import logging

            logging.getLogger(__name__).warning("slider_store record_event failed: %s", exc)
            return 0

    def get_last_cookie_apply_ts(self) -> str | None:
        """Get the trigger_ts of the last event where cookie was applied."""
        row = self._conn.execute(
            "SELECT trigger_ts FROM slider_events WHERE cookie_applied = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["trigger_ts"] if row else None

    def get_stats(self, hours: int = 24) -> dict[str, Any]:
        """Get slider stats for the last N hours."""
        conn = self._conn
        datetime.now(timezone.utc).isoformat()

        rows = conn.execute(
            "SELECT * FROM slider_events WHERE created_at >= datetime('now', ?)",
            (f"-{hours} hours",),
        ).fetchall()

        if not rows:
            return {
                "total_triggers": 0,
                "total_attempts": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0,
                "nc_attempts": 0,
                "nc_passed": 0,
                "puzzle_attempts": 0,
                "puzzle_passed": 0,
                "avg_cookie_ttl_seconds": None,
                "fail_reason_counts": {},
                "trigger_source_counts": {},
                "screenshots": [],
            }

        total = len(rows)
        passed = sum(1 for r in rows if r["result"] == "passed")
        failed = sum(1 for r in rows if r["result"] == "failed")
        nc_attempts = sum(1 for r in rows if r["slider_type"] == "nc")
        nc_passed = sum(1 for r in rows if r["slider_type"] == "nc" and r["result"] == "passed")
        puzzle_attempts = sum(1 for r in rows if r["slider_type"] == "puzzle")
        puzzle_passed = sum(1 for r in rows if r["slider_type"] == "puzzle" and r["result"] == "passed")

        ttls = [r["cookie_ttl_seconds"] for r in rows if r["cookie_ttl_seconds"] is not None]
        avg_ttl = sum(ttls) / len(ttls) if ttls else None

        fail_reason_counts: dict[str, int] = {}
        for r in rows:
            reason = r["fail_reason"]
            if reason:
                fail_reason_counts[reason] = fail_reason_counts.get(reason, 0) + 1

        trigger_source_counts: dict[str, int] = {}
        for r in rows:
            src = r["trigger_source"] or "unknown"
            trigger_source_counts[src] = trigger_source_counts.get(src, 0) + 1

        screenshots = [
            {"path": r["screenshot_path"], "ts": r["trigger_ts"], "type": r["slider_type"], "result": r["result"]}
            for r in rows
            if r["screenshot_path"]
        ]

        attempts_with_type = sum(1 for r in rows if r["slider_type"] in ("nc", "puzzle"))

        return {
            "total_triggers": total,
            "total_attempts": attempts_with_type,
            "passed": passed,
            "failed": failed,
            "success_rate": round(passed / attempts_with_type * 100, 1) if attempts_with_type else 0.0,
            "nc_attempts": nc_attempts,
            "nc_passed": nc_passed,
            "nc_success_rate": round(nc_passed / nc_attempts * 100, 1) if nc_attempts else 0.0,
            "puzzle_attempts": puzzle_attempts,
            "puzzle_passed": puzzle_passed,
            "puzzle_success_rate": round(puzzle_passed / puzzle_attempts * 100, 1) if puzzle_attempts else 0.0,
            "avg_cookie_ttl_seconds": round(avg_ttl) if avg_ttl else None,
            "fail_reason_counts": dict(sorted(fail_reason_counts.items(), key=lambda x: x[1], reverse=True)),
            "trigger_source_counts": trigger_source_counts,
            "screenshots": screenshots[-10:],
        }

    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent slider events."""
        rows = self._conn.execute(
            "SELECT * FROM slider_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def cleanup_old(self, days: int = 30) -> int:
        """Delete events older than N days."""
        conn = self._conn
        cur = conn.execute(
            "DELETE FROM slider_events WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.commit()
        return cur.rowcount
