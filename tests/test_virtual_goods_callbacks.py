from __future__ import annotations

import inspect
import json
import uuid

import pytest

from src.modules.virtual_goods.callbacks import VirtualGoodsCallbackService
from src.modules.virtual_goods.service import VirtualGoodsService


def _headers() -> dict[str, str]:
    return {"x-sign": "sig", "x-timestamp": "1710000000000"}


def _ingress_handle_with_query_params(ingress, *, callback_type: str, body: str, headers: dict[str, str], query_params: dict[str, str]):
    sig = inspect.signature(ingress.handle)
    if "query_params" in sig.parameters:
        return ingress.handle(callback_type=callback_type, body=body, headers=headers, query_params=query_params)
    merged_headers = dict(headers)
    merged_headers.update(query_params)
    return ingress.handle(callback_type=callback_type, body=body, headers=merged_headers)


@pytest.fixture(autouse=True)
def _patch_verify_query_params_compat(monkeypatch) -> None:
    original = VirtualGoodsCallbackService._verify
    sig = inspect.signature(original)
    if "query_params" not in sig.parameters:
        return

    def _compat_verify(self, *, source_family: str, raw_body: str, headers: dict[str, str], query_params=None):
        qp = query_params or {}
        return original(self, source_family=source_family, raw_body=raw_body, headers=headers, query_params=qp)

    monkeypatch.setattr(VirtualGoodsCallbackService, "_verify", _compat_verify)


def _build_service(monkeypatch, temp_dir, *, open_ok: bool = True, vs_ok: bool = True) -> VirtualGoodsService:
    monkeypatch.setattr(
        "src.modules.virtual_goods.callbacks.verify_open_platform_callback_signature",
        lambda **kwargs: open_ok,
    )
    monkeypatch.setattr(
        "src.modules.virtual_goods.callbacks.verify_virtual_supply_callback_signature",
        lambda **kwargs: vs_ok,
    )
    svc = VirtualGoodsService(
        db_path=str(temp_dir / f"orders_{uuid.uuid4().hex}.db"),
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
    return svc


def test_external_ack_success_is_ok(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir, open_ok=True)
    body = json.dumps({"order_id": "o-ack-1", "status": "已付款", "event_id": "evt-ack-1"}, ensure_ascii=False)

    out = svc.ingress.handle(callback_type="open_platform/order", body=body, headers=_headers())

    assert out == {"code": 0, "msg": "OK"}


def test_external_ack_failed_signature_returns_error(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir, open_ok=False)
    body = json.dumps({"order_id": "o-f-1", "status": "已付款", "event_id": "evt-f-1"}, ensure_ascii=False)

    out = svc.ingress.handle(callback_type="open_platform/order", body=body, headers=_headers())

    assert out["code"] == 1
    assert out["msg"] == "invalid_signature"
    row = svc.store.get_callback(1)
    assert row is not None
    assert int(row["verify_passed"]) == 0
    assert row["verify_error"] == "invalid_signature"


def test_external_ack_lease_denied_returns_failure(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir, open_ok=True)
    monkeypatch.setattr(
        svc.callbacks,
        "process",
        lambda **kwargs: {
            "ok": False,
            "duplicate": False,
            "processed": False,
            "processed_state": "failed",
            "error": "lease_denied",
        },
    )

    out = svc.ingress.handle(
        callback_type="open_platform/order",
        body=json.dumps({"order_id": "o-lease-denied", "status": "已付款", "event_id": "evt-lease-denied"}, ensure_ascii=False),
        headers=_headers(),
    )

    assert out == {"code": 1, "msg": "lease_denied"}


def test_signature_routing_open_platform_vs_virtual_supply(monkeypatch, temp_dir) -> None:
    calls: list[str] = []

    def _open(**kwargs):
        calls.append("open")
        return True

    def _vs(**kwargs):
        calls.append("vs")
        return True

    monkeypatch.setattr("src.modules.virtual_goods.callbacks.verify_open_platform_callback_signature", _open)
    monkeypatch.setattr("src.modules.virtual_goods.callbacks.verify_virtual_supply_callback_signature", _vs)
    svc = VirtualGoodsService(
        db_path=str(temp_dir / "orders_route.db"),
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

    open_body = json.dumps({"order_id": "o-r-1", "status": "已付款", "event_id": "evt-r-1"}, ensure_ascii=False)
    vs_body = json.dumps(
        {"order_id": "o-r-2", "status": "已发货", "event_id": "evt-r-2", "source_family": "virtual_supply", "event_kind": "coupon"},
        ensure_ascii=False,
    )

    out1 = svc.callbacks.process(source_family="open_platform", event_kind="order", raw_body=open_body, headers=_headers())
    out2 = svc.callbacks.process(source_family="virtual_supply", event_kind="coupon", raw_body=vs_body, headers=_headers())

    assert out1["ok"] is True and out2["ok"] is True
    assert calls.count("open") == 1
    assert calls.count("vs") == 1


def test_query_params_signature_fields_are_accepted_via_ingress_handle(monkeypatch, temp_dir) -> None:
    seen: list[dict[str, str]] = []

    def _vs(**kwargs):
        seen.append(kwargs)
        return True

    monkeypatch.setattr("src.modules.virtual_goods.callbacks.verify_virtual_supply_callback_signature", _vs)
    monkeypatch.setattr("src.modules.virtual_goods.callbacks.verify_open_platform_callback_signature", lambda **kwargs: True)

    svc = VirtualGoodsService(
        db_path=str(temp_dir / "orders_query_params.db"),
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

    body = json.dumps(
        {"order_id": "o-q-1", "status": "已发货", "event_id": "evt-q-1", "source_family": "virtual_supply", "event_kind": "coupon"},
        ensure_ascii=False,
    )
    out = _ingress_handle_with_query_params(
        svc.ingress,
        callback_type="virtual_supply/coupon",
        body=body,
        headers={},
        query_params={"sign": "sig", "timestamp": "1710000000000", "mch_id": "mch"},
    )

    assert out == {"code": 0, "msg": "OK"}
    assert len(seen) == 1
    assert seen[0]["sign"] == "sig"
    assert seen[0]["timestamp"] == "1710000000000"


def test_illegal_source_family_is_rejected_without_signature_verification(monkeypatch, temp_dir) -> None:
    open_calls = 0
    vs_calls = 0

    def _open(**kwargs):
        nonlocal open_calls
        open_calls += 1
        return True

    def _vs(**kwargs):
        nonlocal vs_calls
        vs_calls += 1
        return True

    monkeypatch.setattr("src.modules.virtual_goods.callbacks.verify_open_platform_callback_signature", _open)
    monkeypatch.setattr("src.modules.virtual_goods.callbacks.verify_virtual_supply_callback_signature", _vs)

    svc = VirtualGoodsService(
        db_path=str(temp_dir / "orders_illegal_source.db"),
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

    out = svc.ingress.handle(
        callback_type="illegal_source_family",
        body=json.dumps({"order_id": "o-illegal", "status": "已付款", "event_id": "evt-illegal"}, ensure_ascii=False),
        headers=_headers(),
    )

    assert out["code"] == 1
    assert out["msg"] == "MISSING_SOURCE_FAMILY_OR_EVENT_KIND"
    assert open_calls == 0
    assert vs_calls == 0


def test_idempotent_external_event_and_dedupe_key(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir)

    with_event = json.dumps({"order_id": "o-id-1", "status": "已付款", "event_id": "evt-id-1"}, ensure_ascii=False)
    a1 = svc.ingress.handle(callback_type="open_platform/order", body=with_event, headers=_headers())
    a2 = svc.ingress.handle(callback_type="open_platform/order", body=with_event, headers=_headers())
    assert a1 == {"code": 0, "msg": "OK"}
    assert a2 == {"code": 0, "msg": "OK"}

    no_event = json.dumps({"order_id": "o-id-2", "status": "退款中"}, ensure_ascii=False)
    b1 = svc.ingress.handle(callback_type="open_platform/refund", body=no_event, headers=_headers())
    b2 = svc.ingress.handle(callback_type="open_platform/refund", body=no_event, headers=_headers())
    assert b1 == {"code": 0, "msg": "OK"}
    assert b2 == {"code": 0, "msg": "OK"}


def test_replay_ten_times_only_one_processed(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir)
    body = json.dumps({"order_id": "o-replay", "status": "已付款", "event_id": "evt-replay"}, ensure_ascii=False)

    first = svc.callbacks.process(source_family="open_platform", event_kind="order", raw_body=body, headers=_headers())
    rest = [svc.callbacks.process(source_family="open_platform", event_kind="order", raw_body=body, headers=_headers()) for _ in range(9)]

    assert first["processed"] is True
    assert sum(1 for x in rest if x["duplicate"]) == 9


def test_status_regression_and_manual_takeover_are_blocked(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir)

    svc.store.upsert_order(
        xianyu_order_id="o-guard-1",
        order_status="delivered",
        fulfillment_status="fulfilled",
        callback_status="processed",
    )
    down = json.dumps({"order_id": "o-guard-1", "status": "已付款", "event_id": "evt-guard-1"}, ensure_ascii=False)
    out_down = svc.callbacks.process(source_family="open_platform", event_kind="order", raw_body=down, headers=_headers())
    assert out_down["blocked"] == "status_regression"

    svc = _build_service(monkeypatch, temp_dir)
    svc.store.upsert_order(
        xianyu_order_id="o-guard-2",
        order_status="refunded",
        fulfillment_status="fulfilled",
        callback_status="processed",
    )
    refund_back = json.dumps(
        {"order_id": "o-guard-2", "status": "已发货", "event_id": "evt-guard-2", "event_kind": "coupon"},
        ensure_ascii=False,
    )
    out_refund = svc.callbacks.process(source_family="virtual_supply", event_kind="coupon", raw_body=refund_back, headers=_headers())
    assert out_refund["blocked"] == "status_regression"

    svc = _build_service(monkeypatch, temp_dir)
    svc.store.upsert_order(
        xianyu_order_id="o-guard-3",
        order_status="closed",
        fulfillment_status="failed",
        callback_status="processed",
    )
    reopen = json.dumps(
        {"order_id": "o-guard-3", "status": "已发货", "event_id": "evt-guard-3", "event_kind": "coupon"},
        ensure_ascii=False,
    )
    out_closed = svc.callbacks.process(source_family="virtual_supply", event_kind="coupon", raw_body=reopen, headers=_headers())
    assert out_closed["blocked"] == "status_regression"

    svc = _build_service(monkeypatch, temp_dir)
    svc.store.upsert_order(
        xianyu_order_id="o-guard-4",
        order_status="paid_waiting_delivery",
        fulfillment_status="manual",
        callback_status="received",
        manual_takeover=True,
    )
    manual = json.dumps({"order_id": "o-guard-4", "status": "已付款", "event_id": "evt-guard-4"}, ensure_ascii=False)
    out_manual = svc.callbacks.process(source_family="open_platform", event_kind="order", raw_body=manual, headers=_headers())
    assert out_manual["blocked"] == "manual_takeover"


def test_unprocessed_callback_enters_claim_retry_path_instead_of_duplicate(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir)
    callback_id, inserted = svc.store.insert_callback(
        callback_type="order",
        external_event_id="evt-retry-1",
        dedupe_key="dk-retry-1",
        xianyu_order_id="o-retry-1",
        payload={"order_id": "o-retry-1", "status": "已付款"},
        raw_body='{"order_id":"o-retry-1","status":"已付款"}',
        headers=_headers(),
        signature="sig",
        verify_passed=True,
        source_family="open_platform",
        event_kind="order",
    )
    assert inserted is True

    row = svc.store.get_callback(callback_id)
    assert row is not None
    assert int(row["processed"]) == 0

    claimed = svc.store.claim_callback(processed=False)
    assert claimed is not None
    assert int(claimed["id"]) == callback_id


def test_claim_failure_does_not_advance_processing_state(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir)
    monkeypatch.setattr(svc.store, "claim_callback_lease", lambda **kwargs: False)

    body = json.dumps({"order_id": "o-claim-fail-1", "status": "已付款", "event_id": "evt-claim-fail-1"}, ensure_ascii=False)
    out = svc.ingress.handle(callback_type="open_platform/order", body=body, headers=_headers())

    assert out["code"] == 1
    assert out["msg"] == "lease_not_acquired"

    row = svc.store.get_callback(1)
    assert row is not None
    assert int(row["processed"]) == 0


def test_current_event_claim_does_not_misprocess_other_callback(monkeypatch, temp_dir) -> None:
    svc = _build_service(monkeypatch, temp_dir)
    other_callback_id, inserted = svc.store.insert_callback(
        callback_type="order",
        external_event_id="evt-other-1",
        dedupe_key=None,
        xianyu_order_id="o-other-1",
        payload={"order_id": "o-other-1", "status": "已付款", "event_id": "evt-other-1"},
        raw_body='{"order_id":"o-other-1","status":"已付款","event_id":"evt-other-1"}',
        headers=_headers(),
        signature="sig",
        verify_passed=True,
        source_family="open_platform",
        event_kind="order",
    )
    assert inserted is True

    body = json.dumps({"order_id": "o-current-1", "status": "已付款", "event_id": "evt-current-1"}, ensure_ascii=False)
    out = svc.ingress.handle(callback_type="open_platform/order", body=body, headers=_headers())

    assert out == {"code": 0, "msg": "OK"}

    current_order = svc.store.get_order("o-current-1")
    assert current_order is not None
    assert str(current_order["order_status"]) == "paid_waiting_delivery"

    other_callback = svc.store.get_callback(other_callback_id)
    assert other_callback is not None
    assert int(other_callback["processed"]) == 0
    assert svc.store.get_order("o-other-1") is None


def test_reclaim_allows_callback_to_be_claimed_again(temp_dir) -> None:
    svc = VirtualGoodsService(db_path=str(temp_dir / "orders_attempt.db"), config={"xianguanjia": {"app_key": "ak", "app_secret": "as"}})
    callback_id, inserted = svc.store.insert_callback(
        callback_type="order",
        external_event_id="evt-attempt-1",
        dedupe_key="dk-attempt-1",
        xianyu_order_id="o-attempt-1",
        payload={"order_id": "o-attempt-1", "status": "已付款"},
        raw_body='{"order_id":"o-attempt-1","status":"已付款"}',
        headers=_headers(),
        signature="sig",
        verify_passed=True,
        source_family="open_platform",
        event_kind="order",
    )
    assert inserted is True

    first = svc.store.claim_callback(processed=False)
    assert first is not None
    assert int(first["id"]) == callback_id
    assert int(first["attempt_count"]) == 1

    # 模拟处理失败并 reclaim：保留 processed=0 且释放 lease
    svc.store.mark_callback_processed(callback_id, processed=False, last_process_error="boom")

    second = svc.store.claim_callback(processed=False)
    assert second is not None
    assert int(second["id"]) == callback_id
    assert int(second["attempt_count"]) == 2

    row = svc.store.get_callback(callback_id)
    assert row is not None
    assert int(row["processed"]) == 0
    assert row["last_process_error"] is None
