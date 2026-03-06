from __future__ import annotations

import sqlite3

from src.modules.virtual_goods.store import VirtualGoodsStore


def test_wave_d_unknown_event_kind_must_land_in_exception_pool(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "wave_d_exception_pool.db"))
    store.upsert_order(xianyu_order_id="o-ex-1", order_status="paid_waiting_delivery")

    callback_id, inserted = store.insert_callback(
        callback_type="new-event-kind",
        external_event_id="evt-ex-1",
        dedupe_key="dk-ex-1",
        xianyu_order_id="o-ex-1",
        payload={"k": 1},
        raw_body='{"k":1}',
        headers={},
        signature="sig",
        verify_passed=True,
        event_kind="brand_new_kind",
    )

    assert inserted is True
    assert callback_id > 0

    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute(
            """
            SELECT event_kind, exception_code, severity, status, occurrence_count
            FROM ops_exception_pool
            WHERE xianyu_order_id=? AND exception_code='unknown_event_kind'
            ORDER BY id DESC
            LIMIT 1
            """,
            ("o-ex-1",),
        ).fetchone()
        assert row is not None
        assert row[0] == "brand_new_kind"
        assert row[1] == "unknown_event_kind"
        assert row[2] == "P1"
        assert row[3] == "open"
        assert int(row[4]) >= 1


def test_wave_d_exception_pool_reoccurrence_updates_occurrence_and_transition(temp_dir) -> None:
    store = VirtualGoodsStore(db_path=str(temp_dir / "wave_d_exception_pool_reoccur.db"))
    now = store._now()

    with store.transaction() as conn:
        exception_id = store.record_ops_exception(
            xianyu_order_id="o-ex-2",
            event_kind="unknown_kind",
            exception_code="unknown_event_kind",
            severity="P1",
            detail={"first": True},
            conn=conn,
        )
        conn.execute(
            "UPDATE ops_exception_pool SET status='investigating', updated_at=? WHERE id=?",
            (now, exception_id),
        )

    with store.transaction() as conn:
        same_id = store.record_ops_exception(
            xianyu_order_id="o-ex-2",
            event_kind="unknown_kind",
            exception_code="unknown_event_kind",
            severity="P1",
            detail={"second": True},
            conn=conn,
        )

    assert same_id == exception_id

    with sqlite3.connect(store.db_path) as conn:
        pool = conn.execute(
            "SELECT status, occurrence_count FROM ops_exception_pool WHERE id=?",
            (exception_id,),
        ).fetchone()
        assert pool is not None
        assert pool[0] == "open"
        assert int(pool[1]) == 2

        transitions = conn.execute(
            "SELECT from_status, to_status, reason FROM ops_exception_transition_log WHERE exception_id=? ORDER BY id ASC",
            (exception_id,),
        ).fetchall()

    assert len(transitions) == 2
    assert transitions[0][0] is None and transitions[0][1] == "open" and transitions[0][2] == "exception_created"
    assert transitions[1][0] == "investigating" and transitions[1][1] == "open" and transitions[1][2] == "exception_reoccurred"
