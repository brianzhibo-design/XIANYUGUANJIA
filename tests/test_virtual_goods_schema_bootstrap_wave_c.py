from __future__ import annotations

import sqlite3
from pathlib import Path

from src.modules.virtual_goods.store import VirtualGoodsStore


def test_wave_c_bootstrap_init_db_creates_event_tables(temp_dir) -> None:
    db_path = temp_dir / "wave_c_bootstrap.db"
    VirtualGoodsStore(db_path=str(db_path))

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'virtual_goods_%'"
            ).fetchall()
        }
        assert "virtual_goods_manual_takeover_events" in tables
        assert "virtual_goods_order_events" in tables
    finally:
        conn.close()


def test_wave_c_migrations_create_event_tables_on_upgrade_path(temp_dir) -> None:
    db_path = temp_dir / "wave_c_upgrade.db"
    conn = sqlite3.connect(db_path)
    try:
        base_sql = Path("database/migrations/20260306_wave_b1_virtual_goods_tables.sql").read_text(encoding="utf-8")
        conn.executescript(base_sql)

        conn.executescript(Path("database/migrations/20260306_wave_c_manual_takeover_events.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_c_order_events.sql").read_text(encoding="utf-8"))

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'virtual_goods_%'"
            ).fetchall()
        }
        assert "virtual_goods_manual_takeover_events" in tables
        assert "virtual_goods_order_events" in tables

        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name IN ('virtual_goods_manual_takeover_events','virtual_goods_order_events')"
            ).fetchall()
        }
        assert "idx_vg_manual_takeover_events_order_created" in indexes
        assert "idx_vg_order_events_order_created" in indexes
        assert "idx_vg_order_events_exception_created" in indexes
    finally:
        conn.close()
