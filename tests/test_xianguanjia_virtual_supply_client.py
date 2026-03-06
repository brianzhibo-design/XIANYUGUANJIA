from __future__ import annotations

from pathlib import Path

import httpx

from src.integrations.xianguanjia.models import XianGuanJiaResponse
from src.integrations.xianguanjia.virtual_supply_client import VirtualSupplyClient


ROOT = Path(__file__).resolve().parents[1]


def test_virtual_supply_method_surface_and_signed_request(monkeypatch) -> None:
    calls = []
    sign_calls = []

    def fake_sign_virtual_supply_request(**kwargs):
        sign_calls.append(kwargs)
        return "sig-vs"

    def fake_post(url: str, params: dict, content: bytes, headers: dict, timeout: float):
        calls.append((url, params, content, headers, timeout))
        return httpx.Response(200, json={"code": 0, "data": {"order_no": "o1"}})

    monkeypatch.setattr(
        "src.integrations.xianguanjia.virtual_supply_client.sign_virtual_supply_request",
        fake_sign_virtual_supply_request,
    )
    monkeypatch.setattr("src.integrations.xianguanjia.virtual_supply_client.httpx.post", fake_post)
    client = VirtualSupplyClient(
        base_url="https://xg.test",
        app_id="app-1",
        app_secret="app-secret-1",
        mch_id="mch-1",
        mch_secret="mch-secret-1",
    )

    methods_with_path = [
        (client.create_card_order, "/goofish/order/purchase/create"),
        (client.create_coupon_order, "/goofish/order/ticket/create"),
        (client.create_recharge_order, "/goofish/order/recharge/create"),
    ]
    for method, expected_path in methods_with_path:
        res = method({"x": 1})
        assert isinstance(res, XianGuanJiaResponse)
        assert res.ok is True
        assert calls[-1][0] == f"https://xg.test{expected_path}"

    assert len(calls) == 3
    assert len(sign_calls) == 3
    assert sign_calls[0]["app_id"] == "app-1"
    assert sign_calls[0]["mch_id"] == "mch-1"

    _, params, content, headers, _ = calls[0]
    assert params["mch_id"] == "mch-1"
    assert params["sign"] == "sig-vs"
    assert "timestamp" in params
    assert headers["Content-Type"] == "application/json"
    assert content == b'{"x":1}'


def test_virtual_supply_error_uses_map_error(monkeypatch) -> None:
    def fake_sign_virtual_supply_request(**kwargs):
        _ = kwargs
        return "sig-vs"

    def fake_post(url: str, params: dict, content: bytes, headers: dict, timeout: float):
        _ = (url, params, content, headers, timeout)
        return httpx.Response(200, json={"code": "E401", "msg": "bad auth"})

    monkeypatch.setattr(
        "src.integrations.xianguanjia.virtual_supply_client.sign_virtual_supply_request",
        fake_sign_virtual_supply_request,
    )
    monkeypatch.setattr("src.integrations.xianguanjia.virtual_supply_client.httpx.post", fake_post)
    client = VirtualSupplyClient(
        base_url="https://xg.test",
        app_id="app-1",
        app_secret="app-secret-1",
        mch_id="mch-1",
        mch_secret="mch-secret-1",
    )
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
