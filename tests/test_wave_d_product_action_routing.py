from __future__ import annotations

import pytest

from src.modules.operations.service import OperationsService


@pytest.mark.asyncio
async def test_wave_d_operations_execute_product_action_delegates_to_listing_service(monkeypatch) -> None:
    svc = OperationsService(controller=None, config={})
    captured: dict[str, object] = {}

    async def _fake_execute(self, action: str, **kwargs):
        captured["action"] = action
        captured["kwargs"] = kwargs
        return {
            "ok": True,
            "action": action,
            "code": "OK",
            "message": "ok",
            "data": {
                "xianyu_product_id": "xp-1",
                "internal_listing_id": kwargs["listing"].internal_listing_id if kwargs.get("listing") else None,
                "mapping_status": "mapped",
                "channel": "api_primary",
                "code": "OK",
                "message": "ok",
            },
            "errors": [],
            "ts": "2026-03-06T00:00:00Z",
        }

    monkeypatch.setattr("src.modules.listing.service.ListingService.execute_product_action", _fake_execute)

    out = await svc.execute_product_action(
        "create",
        payload={"product_id": "xp-1"},
        internal_listing_id="in-1",
    )

    assert out["ok"] is True
    assert captured["action"] == "create"
    forwarded = captured["kwargs"]
    assert forwarded["payload"] == {"product_id": "xp-1"}
    assert forwarded["allow_dom_fallback"] is False
    assert forwarded["listing"].internal_listing_id == "in-1"
