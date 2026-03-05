from __future__ import annotations

import httpx

from src.integrations.xianguanjia.models import XianGuanJiaResponse
from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient


def test_open_platform_success_response_and_method_surface(monkeypatch) -> None:
    called = []

    def fake_post(url: str, json: dict, timeout: float):
        called.append((url, json, timeout))
        return httpx.Response(200, json={"code": 0, "data": {"ok": True}, "request_id": "rid-1"})

    monkeypatch.setattr("src.integrations.xianguanjia.open_platform_client.httpx.post", fake_post)
    client = OpenPlatformClient(base_url="https://xg.test")

    methods = [
        client.create_product,
        client.publish_product,
        client.unpublish_product,
        client.edit_product,
        client.edit_stock,
        client.modify_order_price,
        client.delivery_order,
        client.list_orders,
        client.get_order_detail,
    ]
    for method in methods:
        res = method({"a": 1})
        assert isinstance(res, XianGuanJiaResponse)
        assert res.ok is True

    assert len(called) == 9


def test_open_platform_error_uses_map_error(monkeypatch) -> None:
    def fake_post(url: str, json: dict, timeout: float):
        _ = (url, json, timeout)
        return httpx.Response(200, json={"code": "E429", "msg": "too many", "request_id": "rid-2"})

    monkeypatch.setattr("src.integrations.xianguanjia.open_platform_client.httpx.post", fake_post)
    client = OpenPlatformClient(base_url="https://xg.test")
    res = client.list_orders({"page": 1})

    assert isinstance(res, XianGuanJiaResponse)
    assert res.ok is False
    assert res.retryable is True
    assert res.error_code == "E429"


def test_open_platform_transport_error_no_network(monkeypatch) -> None:
    def fake_post(url: str, json: dict, timeout: float):
        _ = (url, json, timeout)
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("src.integrations.xianguanjia.open_platform_client.httpx.post", fake_post)
    client = OpenPlatformClient(base_url="https://xg.test")
    res = client.get_order_detail({"order_no": "1"})

    assert isinstance(res, XianGuanJiaResponse)
    assert res.ok is False
    assert res.retryable is True
