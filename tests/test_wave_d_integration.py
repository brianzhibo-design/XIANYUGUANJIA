from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from src.dashboard_server import MimicOps
from src.modules.virtual_goods.service import VirtualGoodsService
from src.modules.virtual_goods.store import (
    CALLBACK_EVENT_KIND_VALUES,
    CALLBACK_SOURCE_FAMILY_VALUES,
    VirtualGoodsStore,
)

CONTRACT_KEYS = {"ok", "action", "code", "message", "data", "metrics", "errors", "ts"}


def _service(temp_dir):
    return VirtualGoodsService(
        db_path=str(temp_dir / "wave_d_integration.db"),
        config={
            "xianguanjia": {
                "app_key": "ak",
                "app_secret": "as",
                "vs_app_id": "app",
                "vs_mch_id": "mch",
                "vs_mch_secret": "sec",
            }
        },
    )


def _seed_callback(
    svc: VirtualGoodsService,
    *,
    callback_type: str,
    event_id: str,
    dedupe_key: str,
    order_id: str,
) -> int:
    svc.store.upsert_order(
        xianyu_order_id=order_id,
        order_status="paid_waiting_delivery",
        callback_status="received",
        fulfillment_status="pending",
    )
    cbid, inserted = svc.store.insert_callback(
        callback_type=callback_type,
        external_event_id=event_id,
        dedupe_key=dedupe_key,
        xianyu_order_id=order_id,
        payload={"order_id": order_id, "status": "已付款", "event_id": event_id},
        raw_body=json.dumps({"order_id": order_id, "status": "已付款", "event_id": event_id}, ensure_ascii=False),
        headers={"x-sign": "sig", "x-timestamp": "1", "query_params": {}},
        signature="sig",
        verify_passed=True,
    )
    assert inserted is True
    return cbid


def test_wave_d_mapping_schema_and_schema_bootstrap(temp_dir) -> None:
    db_path = temp_dir / "wave_d_bootstrap.db"
    store = VirtualGoodsStore(db_path=str(db_path))

    # mapping schema: source family + event kind 枚举与推导
    assert {"open_platform", "virtual_supply", "unknown"}.issubset(CALLBACK_SOURCE_FAMILY_VALUES)
    assert {"order", "refund", "voucher", "coupon", "code", "unknown"}.issubset(CALLBACK_EVENT_KIND_VALUES)
    assert store._infer_source_family("order") == "open_platform"
    assert store._infer_source_family("refund") == "open_platform"
    assert store._infer_source_family("coupon") == "virtual_supply"
    assert store._infer_source_family("code") == "virtual_supply"
    assert store._infer_source_family("not-defined") == "unknown"
    assert store._infer_event_kind("coupon") == "coupon"
    assert store._infer_event_kind("invalid-kind") == "unknown"

    # schema bootstrap: 关键表与索引必须存在
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'virtual_goods_%'"
            ).fetchall()
        }
        assert {
            "virtual_goods_products",
            "virtual_goods_orders",
            "virtual_goods_callbacks",
            "virtual_goods_manual_takeover_events",
            "virtual_goods_order_events",
        }.issubset(tables)

        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_vg_%'"
            ).fetchall()
        }
        assert {
            "idx_vg_callbacks_dedupe_no_event",
            "idx_vg_callbacks_order_created",
            "idx_vg_orders_status_updated",
            "idx_vg_manual_takeover_events_order_created",
            "idx_vg_order_events_exception_created",
        }.issubset(indexes)
    finally:
        conn.close()


def test_wave_d_action_routing_matrix_execution_contract_and_dashboard_contract(temp_dir, monkeypatch) -> None:
    svc = _service(temp_dir)

    _seed_callback(svc, callback_type="order", event_id="evt-d-order", dedupe_key="dk-d-order", order_id="o-d-1")
    _seed_callback(svc, callback_type="coupon", event_id="evt-d-coupon", dedupe_key="dk-d-coupon", order_id="o-d-2")

    routed: list[tuple[str, str]] = []

    def _fake_process(**kwargs):
        routed.append((str(kwargs.get("source_family")), str(kwargs.get("event_kind"))))
        return {"ok": True, "processed": True, "processed_state": "processed", "duplicate": False}

    monkeypatch.setattr(svc.callbacks, "process", _fake_process)

    out_event = svc.replay_callback_by_event_id("evt-d-order")
    out_dedupe = svc.replay_callback_by_dedupe_key("dk-d-coupon")
    dashboard = svc.get_dashboard_metrics(timeout_seconds=0)
    product_ops = svc.get_product_operation_metrics(limit=50)

    for out in (out_event, out_dedupe, dashboard):
        assert set(out.keys()) == CONTRACT_KEYS

    assert product_ops["action"] == "get_product_operation_metrics"
    assert product_ops["data"]["optional_fields"]["views"]["state"] == "placeholder_disabled"
    assert product_ops["data"]["optional_fields"]["views"]["reason"] == "no_stable_source"
    # 动作路由矩阵: order -> open_platform/order, coupon -> virtual_supply/coupon
    assert ("open_platform", "order") in routed
    assert ("virtual_supply", "coupon") in routed

    # 执行契约：action 与写库副作用
    assert out_event["ok"] is True and out_event["action"] == "replay_callback_by_event_id"
    assert out_dedupe["ok"] is True and out_dedupe["action"] == "replay_callback_by_dedupe_key"
    assert svc.store.get_order("o-d-1")["callback_status"] == "processed"
    assert svc.store.get_order("o-d-2")["callback_status"] == "processed"

    # dashboard 契约：稳定字段 + 指标结构
    assert dashboard["action"] == "get_dashboard_metrics"
    assert dashboard["code"] == "OK"
    assert isinstance(dashboard["metrics"], dict)
    for key in (
        "total_orders",
        "manual_takeover_orders",
        "total_callbacks",
        "pending_callbacks",
        "processed_callbacks",
        "failed_callbacks",
        "timeout_backlog",
        "unknown_event_kind",
        "timeout_seconds",
    ):
        assert key in dashboard["metrics"]

    # dashboard server 契约（cockpit）：/api 虚拟商品查询返回 success/module 结构
    ops = MimicOps(project_root=Path(temp_dir), module_console=SimpleNamespace())

    class _Svc:
        def __init__(self, db_path: str, config: dict | None = None):
            self.db_path = db_path
            self.config = config or {}

        def get_dashboard_metrics(self):
            return {
                "ok": True,
                "action": "get_dashboard_metrics",
                "code": "OK",
                "metrics": {"total_orders": 2, "pending_callbacks": 0},
            }

        def list_manual_takeover_orders(self):
            return [{"xianyu_order_id": "o-d-1"}]

        def inspect_order(self, *, order_id: str):
            return {"order": {"xianyu_order_id": order_id}, "callbacks": []}

    monkeypatch.setattr("src.dashboard_server.VirtualGoodsService", _Svc)

    payload_metrics = ops.get_virtual_goods_metrics()
    payload_inspect = ops.inspect_virtual_goods_order("o-d-1")

    assert payload_metrics["success"] is True
    assert payload_metrics["module"] == "virtual_goods"
    assert "dashboard_panels" in payload_metrics

    panels = payload_metrics["dashboard_panels"]
    for panel_key in (
        "operations_funnel_overview",
        "exception_priority_pool",
        "fulfillment_efficiency",
        "product_operations",
        "drill_down",
    ):
        assert panel_key in panels

    assert payload_inspect["success"] is True
    assert payload_inspect["module"] == "virtual_goods"
    assert payload_inspect["order_id"] == "o-d-1"
    assert payload_inspect["drill_down_view"]["order"]["xianyu_order_id"] == "o-d-1"
