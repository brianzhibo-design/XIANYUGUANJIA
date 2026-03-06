from __future__ import annotations

import json

from src.modules.virtual_goods.service import VirtualGoodsService


def _service(temp_dir):
    return VirtualGoodsService(db_path=str(temp_dir / "wave_c_service.db"), config={"xianguanjia": {"app_key": "ak", "app_secret": "as"}})


def _seed_order(service: VirtualGoodsService, order_id: str, *, manual_takeover: bool = False):
    service.store.upsert_order(
        xianyu_order_id=order_id,
        order_status="paid_waiting_delivery",
        callback_status="received",
        fulfillment_status="pending",
        manual_takeover=manual_takeover,
    )


def _seed_callback(
    service: VirtualGoodsService,
    *,
    event_id: str,
    dedupe_key: str,
    order_id: str,
    event_kind: str = "order",
    processed: bool = False,
    verify_passed: bool = True,
):
    callback_id, _ = service.store.insert_callback(
        callback_type=event_kind,
        external_event_id=event_id,
        dedupe_key=dedupe_key,
        xianyu_order_id=order_id,
        payload={"order_id": order_id, "status": "已付款", "event_id": event_id},
        raw_body=json.dumps({"order_id": order_id, "status": "已付款", "event_id": event_id}, ensure_ascii=False),
        headers={"x-sign": "sig", "x-timestamp": "1", "query_params": {}},
        signature="sig",
        verify_passed=verify_passed,
        source_family="open_platform",
        event_kind=event_kind,
    )
    if processed:
        service.store.mark_callback_processed(callback_id, processed=True)
    return callback_id


def test_wave_c_query_interfaces_contract(temp_dir):
    svc = _service(temp_dir)
    _seed_order(svc, "o-wave-c-1", manual_takeover=True)
    _seed_callback(svc, event_id="evt-wave-c-1", dedupe_key="dk-wave-c-1", order_id="o-wave-c-1", event_kind="unknown")

    for out in (
        svc.list_timeout_backlog(timeout_seconds=0, limit=10),
        svc.list_replay_candidates(limit=10),
        svc.list_manual_takeover_orders(limit=10),
        svc.inspect_order("o-wave-c-1"),
        svc.get_dashboard_metrics(timeout_seconds=0),
    ):
        assert set(out.keys()) == {"ok", "action", "code", "message", "data", "metrics", "errors", "ts"}
        assert isinstance(out["errors"], list)

    dashboard = svc.get_dashboard_metrics(timeout_seconds=0)
    assert dashboard["metrics"]["unknown_event_kind"] >= 1
    assert any(e.get("code") == "UNKNOWN_EVENT_KIND" for e in dashboard["errors"])


def test_wave_c_set_manual_takeover_write_via_service(temp_dir):
    svc = _service(temp_dir)
    _seed_order(svc, "o-wave-c-2", manual_takeover=False)

    out = svc.set_manual_takeover("o-wave-c-2", True)
    assert out["ok"] is True

    row = svc.store.get_order("o-wave-c-2")
    assert row is not None
    assert int(row["manual_takeover"]) == 1


def test_wave_c_timeout_scan_writes_callback_and_order_state(temp_dir):
    svc = _service(temp_dir)
    _seed_order(svc, "o-wave-c-3")
    cbid = _seed_callback(svc, event_id="evt-wave-c-3", dedupe_key="dk-wave-c-3", order_id="o-wave-c-3", event_kind="unknown")

    out = svc.run_timeout_scan(timeout_seconds=0, limit=10)
    assert out["ok"] is True
    assert out["metrics"]["timed_out"] >= 1
    assert out["metrics"]["unknown_event_kind"] >= 1

    cb = svc.store.get_callback(cbid)
    od = svc.store.get_order("o-wave-c-3")
    assert cb is not None and od is not None
    assert cb["last_process_error"] == "timeout_scan"
    assert od["callback_status"] == "failed"


def test_wave_c_replay_by_event_and_dedupe(temp_dir, monkeypatch):
    svc = _service(temp_dir)
    _seed_order(svc, "o-wave-c-4")
    _seed_callback(svc, event_id="evt-wave-c-4", dedupe_key="dk-wave-c-4", order_id="o-wave-c-4")

    monkeypatch.setattr(
        svc.callbacks,
        "process",
        lambda **kwargs: {"ok": True, "processed": True, "processed_state": "processed", "duplicate": False},
    )

    out1 = svc.replay_callback_by_event_id("evt-wave-c-4")
    out2 = svc.replay_callback_by_dedupe_key("dk-wave-c-4")

    assert out1["ok"] is True and out2["ok"] is True
    assert out1["action"] == "replay_callback_by_event_id"
    assert out2["action"] == "replay_callback_by_dedupe_key"

    od = svc.store.get_order("o-wave-c-4")
    assert od is not None
    assert od["callback_status"] == "processed"
