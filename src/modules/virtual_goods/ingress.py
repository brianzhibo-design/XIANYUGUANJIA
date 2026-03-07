from __future__ import annotations

from typing import Any

from .callbacks import VirtualGoodsCallbackService


class VirtualGoodsIngress:
    _SUCCESS_ACK: dict[str, Any] = {"code": 0, "msg": "OK"}

    def __init__(self, callback_service: VirtualGoodsCallbackService) -> None:
        self.callback_service = callback_service

    @staticmethod
    def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, Any]:
        return {k.lower(): v for k, v in dict(headers or {}).items()}

    @staticmethod
    def _normalize_query_params(query_params: dict[str, Any] | None) -> dict[str, Any]:
        return {k.lower(): v for k, v in dict(query_params or {}).items()}

    @staticmethod
    def _parse_entry(callback_type: str) -> tuple[str, str]:
        raw = str(callback_type or "").strip().lower()
        if "/" in raw:
            source_family, event_kind = raw.split("/", 1)
        elif ":" in raw:
            source_family, event_kind = raw.split(":", 1)
        else:
            return "", ""

        source_family = (source_family or "").strip().lower()
        event_kind = (event_kind or "").strip().lower()
        return source_family, event_kind

    def _call_processor(
        self,
        *,
        source_family: str,
        event_kind: str,
        raw_body: str,
        headers: dict[str, Any],
        query_params: dict[str, Any],
    ) -> dict[str, Any]:
        return self.callback_service.process(
            source_family=source_family,
            event_kind=event_kind,
            raw_body=raw_body,
            headers=headers,
            query_params=query_params,
        )

    @classmethod
    def _map_external_ack(cls, internal_result: dict[str, Any]) -> dict[str, Any]:
        processed = bool(internal_result.get("processed"))
        replay_already_processed = (
            bool(internal_result.get("duplicate")) and str(internal_result.get("processed_state") or "") == "processed"
        )

        if processed or replay_already_processed:
            return dict(cls._SUCCESS_ACK)

        return {
            "code": 1,
            "msg": str(internal_result.get("error") or "FAIL"),
        }

    def handle(
        self,
        *,
        callback_type: str,
        body: bytes | str,
        headers: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_body = body.decode("utf-8") if isinstance(body, bytes) else str(body or "")
        normalized_headers = self._normalize_headers(headers)
        normalized_query_params = self._normalize_query_params(query_params)
        source_family, event_kind = self._parse_entry(callback_type)
        if not source_family or not event_kind:
            return {
                "code": 1,
                "msg": "MISSING_SOURCE_FAMILY_OR_EVENT_KIND",
            }

        internal_result = self._call_processor(
            source_family=source_family,
            event_kind=event_kind,
            raw_body=raw_body,
            headers=normalized_headers,
            query_params=normalized_query_params,
        )
        return self._map_external_ack(internal_result)
