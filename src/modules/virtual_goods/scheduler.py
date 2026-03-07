from __future__ import annotations

from collections.abc import Callable
from typing import Any

KNOWN_EVENT_KINDS = {"order", "refund", "voucher", "coupon", "code"}


class VirtualGoodsScheduler:
    """Wave C scheduler for virtual goods domain.

    Design goals:
    - Scheduler never executes SQL directly.
    - Interacts with upper-layer service interfaces only.
    - Returns structured metrics reusable by CLI / Dashboard.
    """

    def __init__(self, service: Any) -> None:
        self.service = service

    def _invoke(self, names: list[str], **kwargs: Any) -> Any:
        for name in names:
            fn = getattr(self.service, name, None)
            if callable(fn):
                return fn(**kwargs)
        raise AttributeError(f"service method not found, expected one of: {', '.join(names)}")

    @staticmethod
    def _base_result(task: str) -> dict[str, Any]:
        return {
            "task": task,
            "ok": True,
            "metrics": {},
            "errors": [],
            "anomalies": {"unknown_event_kind": 0},
        }

    def timeout_scan(self, *, timeout_seconds: int = 900, limit: int = 100) -> dict[str, Any]:
        result = self._base_result("timeout_scan")
        metrics = {
            "scanned": 0,
            "timed_out": 0,
            "resolved": 0,
            "failed": 0,
        }
        result["metrics"] = metrics

        try:
            orders = self._invoke(
                ["list_timeout_candidates", "scan_timeout_orders"],
                timeout_seconds=timeout_seconds,
                limit=limit,
            )
        except AttributeError as exc:
            result["ok"] = False
            result["errors"].append(str(exc))
            return result

        for order in list(orders or []):
            metrics["scanned"] += 1
            metrics["timed_out"] += 1
            try:
                out = self._invoke(
                    ["resolve_timeout_order", "handle_timeout_order"],
                    order=order,
                )
                if isinstance(out, dict) and out.get("ok") is False:
                    metrics["failed"] += 1
                    result["errors"].append(str(out.get("error") or "timeout_resolve_failed"))
                else:
                    metrics["resolved"] += 1
            except Exception as exc:
                metrics["failed"] += 1
                result["errors"].append(str(exc))

        if metrics["failed"] > 0:
            result["ok"] = False
        return result

    def callback_replay(self, *, limit: int = 100) -> dict[str, Any]:
        result = self._base_result("callback_replay")
        metrics = {
            "fetched": 0,
            "replayed": 0,
            "succeeded": 0,
            "failed": 0,
            "unknown_event_kind": 0,
        }
        result["metrics"] = metrics

        try:
            callbacks = self._invoke(["list_replay_callbacks", "fetch_replay_callbacks"], limit=limit)
        except AttributeError as exc:
            result["ok"] = False
            result["errors"].append(str(exc))
            return result

        for callback in list(callbacks or []):
            metrics["fetched"] += 1
            event_kind = str((callback or {}).get("event_kind") or "").strip().lower() or "unknown"

            if event_kind not in KNOWN_EVENT_KINDS:
                metrics["unknown_event_kind"] += 1
                result["anomalies"]["unknown_event_kind"] += 1
                metrics["failed"] += 1
                result["errors"].append(f"unknown event_kind: {event_kind}")
                reporter: Callable[..., Any] | None = getattr(self.service, "report_scheduler_anomaly", None)
                if callable(reporter):
                    reporter(kind="unknown_event_kind", payload=callback)
                continue

            metrics["replayed"] += 1
            try:
                out = self._invoke(["replay_callback", "process_callback_replay"], callback=callback)
                if isinstance(out, dict) and out.get("ok") is False:
                    metrics["failed"] += 1
                    result["errors"].append(str(out.get("error") or "callback_replay_failed"))
                else:
                    metrics["succeeded"] += 1
            except Exception as exc:
                metrics["failed"] += 1
                result["errors"].append(str(exc))

        if metrics["failed"] > 0:
            result["ok"] = False
        return result

    def manual_takeover_observe(self, *, limit: int = 100) -> dict[str, Any]:
        result = self._base_result("manual_takeover_observe")
        metrics = {
            "manual_orders": 0,
            "observed": 0,
            "escalated": 0,
            "failed": 0,
        }
        result["metrics"] = metrics

        try:
            orders = self._invoke(["list_manual_takeover_orders", "fetch_manual_takeover_orders"], limit=limit)
        except AttributeError as exc:
            result["ok"] = False
            result["errors"].append(str(exc))
            return result

        for order in list(orders or []):
            metrics["manual_orders"] += 1
            try:
                out = self._invoke(["observe_manual_takeover_order", "observe_manual_takeover"], order=order)
                if isinstance(out, dict) and out.get("escalated") is True:
                    metrics["escalated"] += 1
                if isinstance(out, dict) and out.get("ok") is False:
                    metrics["failed"] += 1
                    result["errors"].append(str(out.get("error") or "manual_observe_failed"))
                else:
                    metrics["observed"] += 1
            except Exception as exc:
                metrics["failed"] += 1
                result["errors"].append(str(exc))

        if metrics["failed"] > 0:
            result["ok"] = False
        return result
