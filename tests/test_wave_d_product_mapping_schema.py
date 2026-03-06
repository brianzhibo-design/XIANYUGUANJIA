from __future__ import annotations

import sqlite3
from pathlib import Path

from src.modules.virtual_goods.store import VirtualGoodsStore


def test_wave_d_listing_product_mappings_constraints_and_indexes(temp_dir) -> None:
    db_path = temp_dir / "wave_d_mapping.db"
    store = VirtualGoodsStore(db_path=str(db_path))

    created = store.upsert_listing_product_mapping(
        xianyu_product_id="product-1",
        internal_listing_id="listing-1",
        supply_goods_no="goods-1",
        mapping_status="mapped",
        last_sync_at="2026-03-06T00:00:00Z",
    )
    assert created["xianyu_product_id"] == "product-1"
    assert created["internal_listing_id"] == "listing-1"
    assert created["mapping_status"] == "mapped"

    conn = sqlite3.connect(db_path)
    try:
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(listing_product_mappings)").fetchall()
        }
        assert "xianyu_product_id" in columns
        assert "internal_listing_id" in columns
        assert "supply_goods_no" in columns
        assert "mapping_status" in columns
        assert "last_sync_at" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='listing_product_mappings'"
            ).fetchall()
        }
        assert "idx_lpm_internal_listing_id" in indexes
        assert "idx_lpm_mapping_status_updated" in indexes
        assert "idx_lpm_supply_goods_no_updated" in indexes

        failed = False
        try:
            conn.execute(
                "INSERT INTO listing_product_mappings(xianyu_product_id,internal_listing_id,supply_goods_no,mapping_status,created_at,updated_at) "
                "VALUES('product-2','listing-2','goods-2','bad_status','2026-03-06T00:00:00Z','2026-03-06T00:00:00Z')"
            )
        except sqlite3.IntegrityError:
            failed = True
        assert failed is True

        duplicate_internal_failed = False
        try:
            conn.execute(
                "INSERT INTO listing_product_mappings(xianyu_product_id,internal_listing_id,supply_goods_no,mapping_status,created_at,updated_at) "
                "VALUES('product-3','listing-1','goods-3','mapped','2026-03-06T00:00:00Z','2026-03-06T00:00:00Z')"
            )
        except sqlite3.IntegrityError:
            duplicate_internal_failed = True
        assert duplicate_internal_failed is True
    finally:
        conn.close()


def test_wave_d_listing_product_mappings_migration_upgrades_old_schema(temp_dir) -> None:
    db_path = temp_dir / "wave_d_mapping_migration.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE listing_product_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                xianyu_product_id TEXT NOT NULL UNIQUE,
                xianyu_listing_id TEXT,
                supply_goods_no TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            );
            INSERT INTO listing_product_mappings(
                xianyu_product_id,xianyu_listing_id,supply_goods_no,is_active,created_at,updated_at
            ) VALUES
                ('p-1','l-1','g-1',1,'2026-03-06T00:00:00Z','2026-03-06T00:00:00Z'),
                ('p-2',NULL,'g-2',0,'2026-03-06T00:01:00Z','2026-03-06T00:01:00Z');
            """
        )
        conn.executescript(Path("database/migrations/20260306_wave_d_listing_product_mappings.sql").read_text(encoding="utf-8"))

        rows = conn.execute(
            "SELECT xianyu_product_id, internal_listing_id, mapping_status FROM listing_product_mappings ORDER BY xianyu_product_id"
        ).fetchall()
        assert rows == [("p-1", "l-1", "mapped"), ("p-2", None, "disabled")]
    finally:
        conn.close()
