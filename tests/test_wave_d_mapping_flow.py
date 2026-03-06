from __future__ import annotations

from src.modules.virtual_goods.service import VirtualGoodsService


def test_wave_d_mapping_crud_and_status_persistence(temp_dir) -> None:
    svc = VirtualGoodsService(db_path=str(temp_dir / "wave_d_mapping_flow.db"), config={"xianguanjia": {"app_key": "ak", "app_secret": "as"}})

    created = svc.upsert_listing_product_mapping(
        xianyu_product_id="xp-1",
        internal_listing_id="in-1",
        supply_goods_no="goods-1",
        mapping_status="unmapped",
        last_sync_at="2026-03-06T00:00:00Z",
    )
    assert created["ok"] is True
    assert created["data"]["mapping"]["mapping_status"] == "unmapped"

    got_by_product = svc.get_listing_product_mapping_by_product_id(xianyu_product_id="xp-1")
    assert got_by_product["ok"] is True
    assert got_by_product["data"]["mapping"]["internal_listing_id"] == "in-1"
    assert got_by_product["data"]["mapping"]["mapping_status"] == "unmapped"

    got_by_internal = svc.get_listing_product_mapping_by_internal_id(internal_listing_id="in-1")
    assert got_by_internal["ok"] is True
    assert got_by_internal["data"]["mapping"]["xianyu_product_id"] == "xp-1"
    assert got_by_internal["data"]["mapping"]["mapping_status"] == "unmapped"

    for status in ("mapped", "syncing", "failed", "disabled"):
        status_updated = svc.update_listing_mapping_status(
            xianyu_product_id="xp-1",
            mapping_status=status,
            last_sync_at="2026-03-06T00:10:00Z",
        )
        assert status_updated["ok"] is True
        assert status_updated["data"]["mapping"]["mapping_status"] == status

        got_after = svc.get_listing_product_mapping_by_product_id(xianyu_product_id="xp-1")
        assert got_after["ok"] is True
        assert got_after["data"]["mapping"]["mapping_status"] == status

        still_present = svc.get_listing_product_mapping_by_internal_id(internal_listing_id="in-1")
        assert still_present["ok"] is True
        assert still_present["data"]["mapping"]["mapping_status"] == status

    deleted = svc.delete_listing_product_mapping(xianyu_product_id="xp-1")
    assert deleted["ok"] is True
    assert deleted["metrics"]["deleted"] == 1

    missing = svc.get_listing_product_mapping_by_product_id(xianyu_product_id="xp-1")
    assert missing["ok"] is False
    assert missing["code"] == "NOT_FOUND"
