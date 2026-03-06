from __future__ import annotations

import json

import httpx
import pytest

from src.modules.orders.xianguanjia import XianGuanJiaClient


def test_modify_order_price_uses_order_api_path_and_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_post(url: str, **kwargs):
        calls["url"] = url
        calls["params"] = kwargs["params"]
        calls["content"] = kwargs["content"]
        return httpx.Response(200, json={"code": 0, "data": {"ok": True}})

    monkeypatch.setattr("src.modules.orders.xianguanjia.httpx.post", fake_post)
    client = XianGuanJiaClient(
        app_key="A1",
        app_secret="B2",
        base_url="https://example.test",
        merchant_id="M-1",
    )

    result = client.modify_order_price(order_no="O-100", order_price=1299, express_fee=200)

    assert result["data"]["ok"] is True
    assert calls["url"] == "https://example.test/api/open/order/modify/price"
    payload = json.loads(calls["content"].decode("utf-8"))
    assert payload == {"order_no": "O-100", "order_price": 1299, "express_fee": 200}
    assert calls["params"]["merchantId"] == "M-1"
    assert isinstance(calls["params"]["sign"], str) and len(calls["params"]["sign"]) == 32


def test_modify_order_price_omits_express_fee_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, object]] = []

    def fake_post(url: str, **kwargs):
        _ = url
        sent.append(json.loads(kwargs["content"].decode("utf-8")))
        return httpx.Response(200, json={"code": 0, "data": {"ok": True}})

    monkeypatch.setattr("src.modules.orders.xianguanjia.httpx.post", fake_post)
    client = XianGuanJiaClient(app_key="A1", app_secret="B2", base_url="https://example.test")

    _ = client.modify_order_price(order_no="O-200", order_price=888)

    assert sent[0] == {"order_no": "O-200", "order_price": 888}
