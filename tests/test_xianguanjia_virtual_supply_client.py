from __future__ import annotations

from pathlib import Path

import httpx

from src.integrations.xianguanjia.models import XianGuanJiaResponse
from src.integrations.xianguanjia.virtual_supply_client import VirtualSupplyClient


ROOT = Path(__file__).resolve().parents[1]


def test_virtual_supply_method_surface_and_uniform_response(monkeypatch) -> None:
    calls = []

    def fake_post(url: str, json: dict, timeout: float):
        calls.append((url, json, timeout))
        return httpx.Response(200, json={"code": 0, "data": {"order_no": "o1"}})

    monkeypatch.setattr("src.integrations.xianguanjia.virtual_supply_client.httpx.post", fake_post)
    client = VirtualSupplyClient(base_url="https://xg.test")

    for method in (client.create_card_order, client.create_coupon_order, client.create_recharge_order):
        res = method({"x": 1})
        assert isinstance(res, XianGuanJiaResponse)
        assert res.ok is True

    assert len(calls) == 3


def test_virtual_supply_error_uses_map_error(monkeypatch) -> None:
    def fake_post(url: str, json: dict, timeout: float):
        _ = (url, json, timeout)
        return httpx.Response(200, json={"code": "E401", "msg": "bad auth"})

    monkeypatch.setattr("src.integrations.xianguanjia.virtual_supply_client.httpx.post", fake_post)
    client = VirtualSupplyClient(base_url="https://xg.test")
    res = client.create_card_order({"x": 1})

    assert isinstance(res, XianGuanJiaResponse)
    assert res.ok is False
    assert res.retryable is False
    assert res.error_code == "E401"


def test_virtual_supply_not_wired_in_default_execution_chain() -> None:
    forbidden = "integrations.xianguanjia.virtual_supply_client"
    targets = [ROOT / "src" / "modules", ROOT / "src" / "core"]
    for target in targets:
        for py_file in target.rglob("*.py"):
            assert forbidden not in py_file.read_text(encoding="utf-8")
