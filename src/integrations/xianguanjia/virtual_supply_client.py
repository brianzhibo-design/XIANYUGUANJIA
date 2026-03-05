"""闲管家虚拟货源 Client 骨架。

注意：该文件当前仅包含骨架 + 测试 + 文档映射，
不接入 P0 默认执行链。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .errors import is_retryable_error, map_error
from .models import XianGuanJiaResponse


@dataclass(slots=True)
class VirtualSupplyClient:
    base_url: str
    timeout: float = 10.0

    def _post(self, path: str, payload: dict[str, Any]) -> XianGuanJiaResponse:
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
            raw = resp.json()
            code = raw.get("code")
            if code == 0:
                return XianGuanJiaResponse.success(
                    data=raw.get("data"),
                    request_id=raw.get("request_id"),
                    http_status=resp.status_code,
                    raw_payload=raw,
                )
            normalized = map_error(
                http_status=resp.status_code,
                error_code=code,
                request_id=raw.get("request_id"),
                raw_payload=raw,
                message=raw.get("msg") or "virtual supply business error",
            )
            return XianGuanJiaResponse.failure(
                error_code=str(code) if code is not None else None,
                error_message=str(normalized),
                retryable=is_retryable_error(normalized),
                request_id=raw.get("request_id"),
                http_status=resp.status_code,
                raw_payload=raw,
            )
        except Exception as exc:
            normalized = map_error(exc=exc, message=str(exc))
            return XianGuanJiaResponse.failure(
                error_code=getattr(normalized, "error_code", None),
                error_message=str(normalized),
                retryable=is_retryable_error(normalized),
                request_id=getattr(normalized, "request_id", None),
                http_status=getattr(normalized, "http_status", None),
                raw_payload=getattr(normalized, "raw_payload", None),
            )

    def create_card_order(self, payload: dict[str, Any]) -> XianGuanJiaResponse:
        return self._post("/goofish/order/kam/create", payload)

    def create_coupon_order(self, payload: dict[str, Any]) -> XianGuanJiaResponse:
        return self._post("/goofish/order/coupon/create", payload)

    def create_recharge_order(self, payload: dict[str, Any]) -> XianGuanJiaResponse:
        return self._post("/goofish/order/purchase/create", payload)
