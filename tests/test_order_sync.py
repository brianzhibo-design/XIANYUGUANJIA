from __future__ import annotations

from src.modules.orders.store import OrderStore
from src.modules.orders.sync import OrderSyncService


class Resp:
    def __init__(self, ok: bool, data=None, error_message: str = ""):
        self.ok = ok
        self.data = data
        self.error_message = error_message


class FakeClient:
    def list_orders(self, payload):
        _ = payload
        return Resp(True, {"list": [{"order_no": "o-1"}]})

    def get_order_detail(self, payload):
        return Resp(True, {"order_no": payload["order_no"], "status": "已付款", "product_id": "p-1"})


def test_order_sync_upsert_idempotent(temp_dir):
    store = OrderStore(db_path=str(temp_dir / "orders.db"))
    sync = OrderSyncService(FakeClient(), store)

    out1 = sync.sync({"page": 1})
    out2 = sync.sync({"page": 1})

    assert out1["ok"] is True and out1["synced"] == 1
    assert out2["ok"] is True and out2["synced"] == 1


def test_order_sync_callback_dedup_with_external_event_id(temp_dir):
    store = OrderStore(db_path=str(temp_dir / "orders_evt.db"))

    callback_1, created_1 = store.vg_store.insert_callback(
        callback_type="open_platform",
        external_event_id="evt-b1-001",
        dedupe_key="dk-unused",
        xianyu_order_id="o-1",
        payload={"order_no": "o-1"},
        raw_body='{"order_no":"o-1"}',
        headers={"x-sign": "ok"},
        signature="sig",
        verify_passed=True,
    )
    callback_2, created_2 = store.vg_store.insert_callback(
        callback_type="open_platform",
        external_event_id="evt-b1-001",
        dedupe_key="dk-unused-2",
        xianyu_order_id="o-1",
        payload={"order_no": "o-1"},
        raw_body='{"order_no":"o-1"}',
        headers={"x-sign": "ok"},
        signature="sig",
        verify_passed=True,
    )

    assert created_1 is True
    assert created_2 is False
    assert callback_2 == callback_1


def test_order_sync_callback_dedup_fallback_to_dedupe_key(temp_dir):
    store = OrderStore(db_path=str(temp_dir / "orders_dk.db"))

    callback_1, created_1 = store.vg_store.insert_callback(
        callback_type="virtual_supply",
        external_event_id=None,
        dedupe_key="dk-b1-fallback-001",
        xianyu_order_id="o-2",
        payload={"order_no": "o-2"},
        raw_body='{"order_no":"o-2"}',
        headers={"x-sign": "ok"},
        signature="sig",
        verify_passed=True,
    )
    callback_2, created_2 = store.vg_store.insert_callback(
        callback_type="virtual_supply",
        external_event_id=None,
        dedupe_key="dk-b1-fallback-001",
        xianyu_order_id="o-2",
        payload={"order_no": "o-2"},
        raw_body='{"order_no":"o-2"}',
        headers={"x-sign": "ok"},
        signature="sig",
        verify_passed=True,
    )

    assert created_1 is True
    assert created_2 is False
    assert callback_2 == callback_1
