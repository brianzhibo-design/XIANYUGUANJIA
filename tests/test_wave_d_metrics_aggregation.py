from __future__ import annotations

import json

from src.modules.virtual_goods.service import VirtualGoodsService


def _svc(temp_dir) -> VirtualGoodsService:
    return VirtualGoodsService(
        db_path=str(temp_dir / "wave_d_metrics_agg.db"), config={"xianguanjia": {"app_key": "ak", "app_secret": "as"}}
    )


def test_wave_d_aggregate_metrics_use_ops_tables_and_include_unknown_event_kind(temp_dir) -> None:
    svc = _svc(temp_dir)

    with svc._connect() as conn:  # noqa: SLF001 - test fixture insertion
        conn.execute(
            "INSERT INTO ops_funnel_stage_daily(stat_date,stage,xianyu_product_id,xianyu_listing_id,metric_count,updated_at) VALUES(?,?,?,?,?,?)",
            ("2026-03-06", "paid", "p-1", "l-1", 4, "2026-03-06T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO ops_funnel_stage_daily(stat_date,stage,xianyu_product_id,xianyu_listing_id,metric_count,updated_at) VALUES(?,?,?,?,?,?)",
            ("2026-03-06", "delivered", "p-1", "l-1", 3, "2026-03-06T00:00:00Z"),
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
            (
                "o-1",
                "unknown",
                "unknown_event_kind",
                "P0",
                "open",
                "2026-03-06T00:00:00Z",
                "2026-03-06T00:00:00Z",
                2,
                json.dumps({"k": 1}),
                "2026-03-06T00:00:00Z",
                "2026-03-06T00:00:00Z",
            ),
        )
        conn.commit()

    funnel = svc.get_funnel_metrics(limit=50)
    assert funnel["metrics"]["source"] == "ops_funnel_stage_daily"
    assert funnel["metrics"]["total_metric_count"] == 7
    assert funnel["metrics"]["unknown_event_kind"] == 1
    assert funnel["data"]["stage_totals"]["paid"] == 4

    product = svc.get_product_operation_metrics(limit=50)
    assert product["metrics"]["source"] == "ops_item_daily_snapshot"
    assert product["metrics"]["has_ops_snapshot_data"] is True
    assert product["data"]["summary"]["paid_order_count"] == 10
    assert product["data"]["summary"]["conversion_rate_pct"] == 10.0
    assert product["data"]["field_state"]["paid_order_count"] == "available"
    assert product["data"]["field_class"]["paid_order_count"] == "real_source"
    assert product["data"]["optional_fields"]["views"]["state"] == "placeholder_disabled"
    assert product["data"]["optional_fields"]["views"]["reason"] == "no_stable_source"
    assert product["metrics"]["unknown_event_kind"] == 1

    fulfillment = svc.get_fulfillment_efficiency_metrics(limit=50)
    assert fulfillment["metrics"]["source"] == "ops_fulfillment_eff_daily"
    assert fulfillment["data"]["summary"]["fulfillment_rate_pct"] == 90.0
    assert fulfillment["data"]["summary"]["failure_rate_pct"] == 10.0
    assert fulfillment["metrics"]["unknown_event_kind"] == 1

    exceptions = svc.list_priority_exceptions(limit=50)
    assert exceptions["metrics"]["source"] == "ops_exception_pool"
    assert exceptions["metrics"]["unknown_event_kind"] == 2
    assert exceptions["data"]["items"][0]["type"] == "UNKNOWN_EVENT_KIND"


def test_wave_d_product_metrics_empty_snapshot_must_be_placeholder_not_fake_zero(temp_dir) -> None:
    svc = _svc(temp_dir)

    out = svc.get_product_operation_metrics(limit=50)

    assert out["metrics"]["source"] == "ops_item_daily_snapshot"
    assert out["metrics"]["has_ops_snapshot_data"] is False
    assert out["data"]["summary"]["exposure_count"] is None
    assert out["data"]["summary"]["conversion_rate_pct"] is None
    assert out["data"]["field_state"]["exposure_count"] == "placeholder"
    assert out["data"]["field_class"]["exposure_count"] == "placeholder_disabled"
    assert out["data"]["optional_fields"]["sales"]["state"] == "placeholder_disabled"
    assert out["data"]["optional_fields"]["sales"]["reason"] == "no_stable_source"
