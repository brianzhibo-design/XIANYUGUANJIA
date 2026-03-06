from __future__ import annotations

from typing import Any

from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

from .store import OrderStore


class OrderSyncService:
    def __init__(self, open_platform_client: OpenPlatformClient, order_store: OrderStore) -> None:
        self.client = open_platform_client
        self.store = order_store

    @staticmethod
    def _extract_orders(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            rows = data.get("list") or data.get("rows") or data.get("orders")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        return []

    def sync(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        req = dict(payload or {})
        listed = self.client.list_orders(req)
        if not listed.ok:
            return {"ok": False, "synced": 0, "error": listed.error_message}

        synced = 0
        for row in self._extract_orders(listed.data):
            order_no = str(row.get("order_no") or row.get("order_id") or "").strip()
            if not order_no:
                continue
            detail_resp = self.client.get_order_detail({"order_no": order_no})
            if not detail_resp.ok:
                continue
            detail = detail_resp.data if isinstance(detail_resp.data, dict) else {}
            if not detail:
                detail = {"order_no": order_no, **row}
            self.store.upsert_from_open_platform_detail(detail)
            synced += 1
        return {"ok": True, "synced": synced}
