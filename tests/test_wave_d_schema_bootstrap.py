from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.modules.virtual_goods.service import VirtualGoodsService
from src.modules.virtual_goods.store import VirtualGoodsStore


def test_wave_d_bootstrap_init_db_creates_new_tables(temp_dir) -> None:
    db_path = temp_dir / "wave_d_bootstrap.db"
    VirtualGoodsStore(db_path=str(db_path))

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "listing_product_mappings" in tables
        assert "ops_funnel_stage_daily" in tables
        assert "ops_item_daily_snapshot" in tables
        assert "ops_exception_pool" in tables
        assert "ops_exception_transition_log" in tables
        assert "ops_fulfillment_eff_daily" in tables
    finally:
        conn.close()


def _build_wave_d_migration_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(Path("database/migrations/20260306_wave_b1_virtual_goods_tables.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_b4_callbacks_lease_and_dims.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_c_manual_takeover_events.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_c_order_events.sql").read_text(encoding="utf-8"))

        conn.executescript(Path("database/migrations/20260306_wave_d_listing_product_mappings.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_d_ops_funnel_stage_daily.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_d_ops_item_daily_snapshot.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_d_ops_exception_pool.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_d_ops_exception_transition_log.sql").read_text(encoding="utf-8"))
        conn.executescript(Path("database/migrations/20260306_wave_d_ops_fulfillment_eff_daily.sql").read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def test_wave_d_migrations_upgrade_path_and_service_queries(temp_dir) -> None:
    db_path = temp_dir / "wave_d_upgrade.db"
    _build_wave_d_migration_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO ops_funnel_stage_daily(stat_date,stage,xianyu_product_id,xianyu_listing_id,metric_count,updated_at) VALUES(?,?,?,?,?,?)",
            ("2026-03-06", "paid", "p-1", "l-1", 3, "2026-03-06T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO ops_item_daily_snapshot(stat_date,xianyu_product_id,xianyu_listing_id,exposure_count,paid_order_count,paid_amount_cents,refund_order_count,exception_count,manual_takeover_count,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("2026-03-06", "p-1", "l-1", 100, 10, 5000, 1, 2, 1, "2026-03-06T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO ops_fulfillment_eff_daily(stat_date,xianyu_product_id,xianyu_listing_id,total_orders,fulfilled_orders,failed_orders,avg_fulfillment_seconds,p95_fulfillment_seconds,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            ("2026-03-06", "p-1", "l-1", 10, 9, 1, 20, 60, "2026-03-06T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO ops_exception_pool(xianyu_order_id,event_kind,exception_code,severity,status,first_seen_at,last_seen_at,occurrence_count,detail_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ("o-1", "unknown_kind", "unknown_event_kind", "P1", "open", "2026-03-06T00:00:00Z", "2026-03-06T00:00:00Z", 1, json.dumps({"k": 1}), "2026-03-06T00:00:00Z", "2026-03-06T00:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()

    svc = VirtualGoodsService(db_path=str(db_path), config={"xianguanjia": {"app_key": "ak", "app_secret": "as"}})

    assert svc.get_funnel_metrics(limit=10)["metrics"]["source"] == "ops_funnel_stage_daily"
    assert svc.get_product_operation_metrics(limit=10)["metrics"]["source"] == "ops_item_daily_snapshot"
    assert svc.get_fulfillment_efficiency_metrics(limit=10)["metrics"]["source"] == "ops_fulfillment_eff_daily"
    ex = svc.list_priority_exceptions(limit=10)
    assert ex["metrics"]["source"] == "ops_exception_pool"
    assert ex["data"]["items"]


def test_wave_d_fresh_bootstrap_and_migrations_are_schema_isomorphic_for_ops_tables(temp_dir) -> None:
    fresh_db = temp_dir / "wave_d_fresh_schema.db"
    migrated_db = temp_dir / "wave_d_migrated_schema.db"

    VirtualGoodsStore(db_path=str(fresh_db))
    _build_wave_d_migration_db(migrated_db)

    targets = {
        "ops_funnel_stage_daily",
        "ops_item_daily_snapshot",
        "ops_exception_pool",
        "ops_exception_transition_log",
        "ops_fulfillment_eff_daily",
    }

    def collect_schema(path: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
        conn = sqlite3.connect(path)
        try:
            table_sql = {
                row[0]: " ".join((row[1] or "").split())
                for row in conn.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ({})".format(
                        ",".join("?" for _ in targets)
                    ),
                    tuple(sorted(targets)),
                ).fetchall()
            }
            index_sql = {
                table: sorted(
                    " ".join((idx_row[0] or "").split())
                    for idx_row in conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND name NOT LIKE 'sqlite_autoindex_%' AND sql IS NOT NULL ORDER BY name",
                        (table,),
                    ).fetchall()
                )
                for table in targets
            }
            return table_sql, index_sql
        finally:
            conn.close()

    fresh_tables, fresh_indexes = collect_schema(fresh_db)
    migrated_tables, migrated_indexes = collect_schema(migrated_db)

    assert set(fresh_tables) == targets
    assert set(migrated_tables) == targets
    assert fresh_tables == migrated_tables
    assert fresh_indexes == migrated_indexes


def test_wave_d_unknown_event_kind_goes_to_exception_pool(temp_dir) -> None:
    svc = VirtualGoodsService(db_path=str(temp_dir / "wave_d_unknown.db"), config={"xianguanjia": {"app_key": "ak", "app_secret": "as"}})

    svc.store.upsert_order(xianyu_order_id="o-wave-d-1", order_status="paid_waiting_delivery")
    svc.store.insert_callback(
        callback_type="totally_new_kind",
        external_event_id="evt-wave-d-1",
        dedupe_key="dk-wave-d-1",
        xianyu_order_id="o-wave-d-1",
        payload={"id": 1},
        raw_body=json.dumps({"id": 1}),
        headers={},
        signature="sig",
        verify_passed=True,
        source_family="unknown",
        event_kind="totally_new_kind",
    )

    out = svc.list_priority_exceptions(limit=10)
    assert out["ok"] is True
    assert any(item["exception_code"] == "unknown_event_kind" for item in out["data"]["items"])
