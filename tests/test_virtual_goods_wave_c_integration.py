from __future__ import annotations

import json

from src.modules.virtual_goods.service import VirtualGoodsService


CONTRACT_KEYS = {"ok", "action", "code", "message", "data", "metrics", "errors", "ts"}


def _service(temp_dir):
    return VirtualGoodsService(
        db_path=str(temp_dir / "wave_c_integration.db"),
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


def _seed_order_and_callback(svc: VirtualGoodsService, *, order_id: str, event_id: str, event_kind: str):
    svc.store.upsert_order(
        xianyu_order_id=order_id,
        order_status="paid_waiting_delivery",
        callback_status="received",
        fulfillment_status="pending",
    )
    callback_id, _ = svc.store.insert_callback(
        callback_type=event_kind,
        external_event_id=event_id,
        dedupe_key=f"dk-{event_id}",
        xianyu_order_id=order_id,
        payload={"order_id": order_id, "status": "已付款", "event_id": event_id},
        raw_body=json.dumps({"order_id": order_id, "status": "已付款", "event_id": event_id}, ensure_ascii=False),
        headers={"x-sign": "sig", "x-timestamp": "1", "query_params": {}},
        signature="sig",
        verify_passed=True,
        source_family="open_platform",
        event_kind=event_kind,
    )
    return callback_id


def test_dashboard_cli_scheduler_can_all_use_service_interfaces(temp_dir, monkeypatch):
    svc = _service(temp_dir)
    _seed_order_and_callback(svc, order_id="o-int-1", event_id="evt-int-1", event_kind="unknown")

    dashboard_out = svc.get_dashboard_metrics(timeout_seconds=0)
    cli_out = svc.list_replay_candidates(limit=20)
    scheduler_out = svc.run_timeout_scan(timeout_seconds=0, limit=20)

    assert set(dashboard_out.keys()) == CONTRACT_KEYS
    assert set(cli_out.keys()) == CONTRACT_KEYS
    assert set(scheduler_out.keys()) == CONTRACT_KEYS

    # unknown event_kind 必须进入异常指标，不可静默
    assert dashboard_out["metrics"]["unknown_event_kind"] >= 1
    assert any(err.get("code") == "UNKNOWN_EVENT_KIND" for err in dashboard_out["errors"])
    assert scheduler_out["metrics"]["unknown_event_kind"] >= 1

    # scheduler 写入必须落库（经 service）
    row = svc.store.get_order("o-int-1")
    assert row is not None
    assert row["callback_status"] == "failed"

    # replay 也通过 service 并写入 callback_status
    monkeypatch.setattr(
        svc.callbacks,
        "process",
        lambda **kwargs: {"ok": True, "processed": True, "processed_state": "processed", "duplicate": False},
    )
    replay_out = svc.replay_callback_by_event_id("evt-int-1")
    assert set(replay_out.keys()) == CONTRACT_KEYS
    assert replay_out["ok"] is True

    row2 = svc.store.get_order("o-int-1")
    assert row2 is not None
    assert row2["callback_status"] == "processed"


def test_service_query_execute_full_chain_contract_and_manual_takeover_write(temp_dir):
    svc = _service(temp_dir)
    _seed_order_and_callback(svc, order_id="o-int-2", event_id="evt-int-2", event_kind="order")

    manual1 = svc.set_manual_takeover("o-int-2", True)
    manual2 = svc.list_manual_takeover_orders(limit=10)
    inspect = svc.inspect_order("o-int-2")
    backlog = svc.list_timeout_backlog(timeout_seconds=0, limit=10)

    for out in (manual1, manual2, inspect, backlog):
        assert set(out.keys()) == CONTRACT_KEYS

    order = svc.store.get_order("o-int-2")
    assert order is not None
    assert int(order["manual_takeover"]) == 1
