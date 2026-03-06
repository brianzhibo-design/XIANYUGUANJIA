from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.modules.messages.workflow import WorkflowStore
from src.modules.virtual_goods.models import normalize_order_status
from src.modules.virtual_goods.store import VirtualGoodsStore


def test_insert_callback_external_event_id_is_idempotent(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_store_event.db"))

    first_id, first_inserted = store.insert_callback(
        callback_type="order",
        external_event_id="evt-001",
        dedupe_key="dup-a",
        xianyu_order_id="xy-1",
        payload={"k": 1},
        raw_body='{"k":1}',
        headers={"x-sign": "s"},
        signature="s",
        verify_passed=True,
    )
    second_id, second_inserted = store.insert_callback(
        callback_type="order",
        external_event_id="evt-001",
        dedupe_key="dup-b",
        xianyu_order_id="xy-1",
        payload={"k": 2},
        raw_body='{"k":2}',
        headers={"x-sign": "s"},
        signature="s",
        verify_passed=True,
    )

    assert first_inserted is True
    assert second_inserted is False
    assert second_id == first_id


def test_insert_callback_uses_dedupe_key_when_external_event_id_missing(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_store_dedupe.db"))

    first_id, first_inserted = store.insert_callback(
        callback_type="order",
        external_event_id=None,
        dedupe_key="order-xy-2:paid",
        xianyu_order_id="xy-2",
        payload={"status": "paid"},
        raw_body='{"status":"paid"}',
        headers={},
        signature="sig",
        verify_passed=True,
    )
    second_id, second_inserted = store.insert_callback(
        callback_type="order",
        external_event_id=None,
        dedupe_key="order-xy-2:paid",
        xianyu_order_id="xy-2",
        payload={"status": "paid"},
        raw_body='{"status":"paid"}',
        headers={},
        signature="sig",
        verify_passed=True,
    )

    assert first_inserted is True
    assert second_inserted is False
    assert second_id == first_id


def test_callback_raw_body_and_verify_error_are_persisted(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_store_raw.db"))
    raw = '{"order_id":"xy-3","status":"paid"}'

    callback_id, inserted = store.insert_callback(
        callback_type="order",
        external_event_id="evt-raw-1",
        dedupe_key="xy-3:paid",
        xianyu_order_id="xy-3",
        payload={"order_id": "xy-3", "status": "paid"},
        raw_body=raw,
        headers={"x-ts": "1"},
        signature="bad-sig",
        verify_passed=False,
        verify_error="signature_mismatch",
    )

    row = store.get_callback(callback_id)
    assert inserted is True
    assert row is not None
    assert row["raw_body"] == raw
    assert row["verify_passed"] == 0
    assert row["verify_error"] == "signature_mismatch"
    assert json.loads(row["payload_json"])["order_id"] == "xy-3"


def test_upsert_order_uses_virtual_goods_status_mapping(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_store_status.db"))

    row = store.upsert_order(
        xianyu_order_id="xy-map-1",
        order_status="paid",  # 旧 orders 状态词
        fulfillment_status="delivering",
        callback_status="received",
    )

    assert row["order_status"] == "paid_waiting_delivery"
    assert row["fulfillment_status"] == "delivering"
    assert row["callback_status"] == "received"
    assert normalize_order_status("completed") == "delivered"


def test_upsert_order_rejects_invalid_virtual_goods_status(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_store_bad_status.db"))

    with pytest.raises(ValueError, match="Unsupported fulfillment status"):
        store.upsert_order(
            xianyu_order_id="xy-bad-1",
            order_status="paid_waiting_delivery",
            fulfillment_status="unknown",
        )


def test_normalize_order_status_rejects_unknown_and_none() -> None:
    with pytest.raises(ValueError):
        normalize_order_status(999)
    with pytest.raises(ValueError):
        normalize_order_status("unknown_status")
    with pytest.raises(ValueError):
        normalize_order_status(None)


def test_insert_callback_requires_external_event_id_or_dedupe_key(temp_dir) -> None:
    db_path = temp_dir / "vg_store_missing_keys.db"
    store = VirtualGoodsStore(db_path=str(db_path))

    with pytest.raises(ValueError, match="requires external_event_id or dedupe_key"):
        store.insert_callback(
            callback_type="order",
            external_event_id=None,
            dedupe_key=None,
            xianyu_order_id="xy-missing",
            payload={"k": 1},
            raw_body='{"k":1}',
            headers={},
            signature="sig",
            verify_passed=True,
        )

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(1) FROM virtual_goods_callbacks").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_migration_creates_tables_and_indexes(temp_dir) -> None:
    migration_path = Path("database/migrations/20260306_wave_b1_virtual_goods_tables.sql")
    sql = migration_path.read_text(encoding="utf-8")
    db_path = temp_dir / "migration_b1.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'virtual_goods_%'"
            ).fetchall()
        }
        assert tables == {
            "virtual_goods_products",
            "virtual_goods_orders",
            "virtual_goods_callbacks",
        }

        idx = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='virtual_goods_orders'"
            ).fetchall()
        }
        assert "idx_vg_orders_status_updated" in idx
        assert "idx_vg_orders_callback_status_updated" in idx

        # 校验 CHECK 约束生效（非法状态应失败）
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO virtual_goods_orders(
                    xianyu_order_id, order_status, fulfillment_status, callback_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("xy-illegal", "paid", "pending", "none", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
    finally:
        conn.close()


def test_workflow_claim_lease_and_reclaim_behaviors(temp_dir) -> None:
    store = WorkflowStore(db_path=str(temp_dir / "workflow_claim.db"))
    session = {"session_id": "s-lease-1", "last_message": "hello"}
    assert store.enqueue_job(session, stage="reply") is True

    first_claim = store.claim_jobs(limit=1, lease_seconds=1)
    assert len(first_claim) == 1
    job = first_claim[0]
    assert job.lease_until is not None

    # active lease 下不可重复 claim
    second_claim = store.claim_jobs(limit=1, lease_seconds=1)
    assert second_claim == []

    # 过期后可 reclaim
    conn = sqlite3.connect(temp_dir / "workflow_claim.db")
    try:
        conn.execute("UPDATE workflow_jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (job.id,))
        conn.commit()
    finally:
        conn.close()

    recovered = store.recover_expired_jobs()
    assert recovered == 1
    reclaimed = store.claim_jobs(limit=1, lease_seconds=1)
    assert len(reclaimed) == 1
    assert reclaimed[0].id == job.id


def test_workflow_fail_job_updates_attempt_count_and_last_error(temp_dir) -> None:
    store = WorkflowStore(db_path=str(temp_dir / "workflow_fail.db"))
    session = {"session_id": "s-fail-1", "last_message": "need retry"}
    assert store.enqueue_job(session, stage="reply") is True

    jobs = store.claim_jobs(limit=1, lease_seconds=30)
    assert len(jobs) == 1
    job = jobs[0]

    assert store.fail_job(
        job_id=job.id,
        error="upstream timeout",
        max_attempts=3,
        base_backoff_seconds=1,
        expected_lease_until=job.lease_until,
    ) is True

    conn = sqlite3.connect(temp_dir / "workflow_fail.db")
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT status, attempts, last_error, lease_until FROM workflow_jobs WHERE id=?", (job.id,)).fetchone()
        assert row is not None
        assert row["status"] == "pending"
        assert int(row["attempts"]) == 1
        assert row["last_error"] == "upstream timeout"
        assert row["lease_until"] is None
    finally:
        conn.close()


def test_claim_callback_lease_claims_exact_callback_id(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_claim_precise.db"))

    callback_a, _ = store.insert_callback(
        callback_type="order",
        external_event_id="evt-precise-a",
        dedupe_key="dk-precise-a",
        xianyu_order_id="o-precise-a",
        payload={"order_id": "o-precise-a", "status": "paid"},
        raw_body='{"order_id":"o-precise-a","status":"paid"}',
        headers={},
        signature="sig",
        verify_passed=True,
    )
    callback_b, _ = store.insert_callback(
        callback_type="order",
        external_event_id="evt-precise-b",
        dedupe_key="dk-precise-b",
        xianyu_order_id="o-precise-b",
        payload={"order_id": "o-precise-b", "status": "paid"},
        raw_body='{"order_id":"o-precise-b","status":"paid"}',
        headers={},
        signature="sig",
        verify_passed=True,
    )

    assert store.claim_callback_lease(callback_b) is True

    row_a = store.get_callback(callback_a)
    row_b = store.get_callback(callback_b)
    assert row_a is not None and row_b is not None
    assert int(row_a["attempt_count"]) == 0
    assert int(row_b["attempt_count"]) == 1
    assert row_a["claim_expires_at"] is None
    assert row_b["claim_expires_at"] is not None


def test_claim_failure_does_not_advance_and_reclaim_allows_reprocess(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_claim_reclaim.db"))

    callback_id, inserted = store.insert_callback(
        callback_type="order",
        external_event_id="evt-reclaim-1",
        dedupe_key="dk-reclaim-1",
        xianyu_order_id="o-reclaim-1",
        payload={"order_id": "o-reclaim-1", "status": "paid"},
        raw_body='{"order_id":"o-reclaim-1","status":"paid"}',
        headers={},
        signature="sig",
        verify_passed=True,
    )
    assert inserted is True

    assert store.claim_callback_lease(callback_id, processed=True) is False
    row = store.get_callback(callback_id)
    assert row is not None
    assert int(row["attempt_count"]) == 0

    assert store.claim_callback_lease(callback_id, processed=False) is True
    first_claim = store.get_callback(callback_id)
    assert first_claim is not None
    assert int(first_claim["attempt_count"]) == 1

    assert store.claim_callback_lease(callback_id, processed=False) is False
    still_claimed = store.get_callback(callback_id)
    assert still_claimed is not None
    assert int(still_claimed["attempt_count"]) == 1

    assert store.reclaim_callback_lease(callback_id) is True
    assert store.claim_callback_lease(callback_id, processed=False) is True
    second_claim = store.get_callback(callback_id)
    assert second_claim is not None
    assert int(second_claim["attempt_count"]) == 2


def test_processed_false_retry_path_can_be_claimed_and_error_cleared(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_retry_path.db"))

    callback_id, inserted = store.insert_callback(
        callback_type="order",
        external_event_id="evt-retry-1",
        dedupe_key="dk-retry-1",
        xianyu_order_id="o-retry-1",
        payload={"order_id": "o-retry-1", "status": "paid"},
        raw_body='{"order_id":"o-retry-1","status":"paid"}',
        headers={},
        signature="sig",
        verify_passed=True,
    )
    assert inserted is True

    store.mark_callback_processed(callback_id, processed=False, last_process_error="boom")
    failed_row = store.get_callback(callback_id)
    assert failed_row is not None
    assert int(failed_row["processed"]) == 0
    assert failed_row["last_process_error"] == "boom"

    claimed = store.claim_callback(processed=False)
    assert claimed is not None
    assert int(claimed["id"]) == callback_id
    assert int(claimed["attempt_count"]) == 1
    assert claimed["last_process_error"] is None


def test_unknown_event_kind_is_recorded_as_exception_metric(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_unknown_kind.db"))

    callback_id, inserted = store.insert_callback(
        callback_type="something-new",
        external_event_id="evt-unknown-1",
        dedupe_key="dk-unknown-1",
        xianyu_order_id="o-unknown-1",
        payload={"order_id": "o-unknown-1"},
        raw_body='{"order_id":"o-unknown-1"}',
        headers={},
        signature="sig",
        verify_passed=True,
        event_kind="brand_new_kind",
    )

    assert inserted is True
    events = store.list_order_events(is_exception=True)
    assert any(
        int(e.get("callback_id") or 0) == callback_id
        and e["event_type"] == "callback_event_kind_unknown"
        and e["error_code"] == "unknown_event_kind"
        for e in events
    )


def test_manual_takeover_and_order_event_support_transaction_boundary(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "vg_txn_boundary.db"))
    store.upsert_order(xianyu_order_id="o-tx-1", order_status="paid_waiting_delivery")

    with store.transaction() as conn:
        assert store.set_manual_takeover("o-tx-1", True, reason="ops", conn=conn) is True
        store.record_order_event(
            xianyu_order_id="o-tx-1",
            event_type="scheduler_result",
            event_kind="order",
            result="ok",
            conn=conn,
        )

    row = store.get_order("o-tx-1")
    assert row is not None
    assert int(row["manual_takeover"]) == 1
    assert len(store.list_order_events(xianyu_order_id="o-tx-1")) == 1
