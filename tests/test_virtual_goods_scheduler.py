from __future__ import annotations

from src.modules.virtual_goods.scheduler import VirtualGoodsScheduler


class _FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.anomalies: list[tuple[str, dict]] = []

    def _record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))

    def scan_timeout_orders(self, *, timeout_seconds: int, limit: int):
        self._record("scan_timeout_orders", timeout_seconds=timeout_seconds, limit=limit)
        return [{"order_id": "o-1"}, {"order_id": "o-2"}]

    def handle_timeout_order(self, *, order: dict):
        self._record("handle_timeout_order", order=order)
        return {"ok": order.get("order_id") != "o-2", "error": "resolve_failed"}

    def fetch_replay_callbacks(self, *, limit: int):
        self._record("fetch_replay_callbacks", limit=limit)
        return [
            {"callback_id": 1, "event_kind": "order"},
            {"callback_id": 2, "event_kind": "SOMETHING_NEW"},
        ]

    def replay_callback(self, *, callback: dict):
        self._record("replay_callback", callback=callback)
        return {"ok": True}

    def report_scheduler_anomaly(self, *, kind: str, payload: dict):
        self._record("report_scheduler_anomaly", kind=kind, payload=payload)
        self.anomalies.append((kind, payload))

    def fetch_manual_takeover_orders(self, *, limit: int):
        self._record("fetch_manual_takeover_orders", limit=limit)
        return [{"order_id": "m-1"}, {"order_id": "m-2"}]

    def observe_manual_takeover(self, *, order: dict):
        self._record("observe_manual_takeover", order=order)
        if order.get("order_id") == "m-2":
            return {"ok": True, "escalated": True}
        return {"ok": True, "escalated": False}


def test_timeout_scan_structured_metrics_and_service_call_chain_only() -> None:
    svc = _FakeService()
    scheduler = VirtualGoodsScheduler(service=svc)

    out = scheduler.timeout_scan(timeout_seconds=300, limit=50)

    assert out["task"] == "timeout_scan"
    assert out["ok"] is False
    assert out["metrics"] == {
        "scanned": 2,
        "timed_out": 2,
        "resolved": 1,
        "failed": 1,
    }
    assert any(name == "scan_timeout_orders" for name, _ in svc.calls)
    assert sum(1 for name, _ in svc.calls if name == "handle_timeout_order") == 2


def test_callback_replay_counts_unknown_event_kind_and_exposes_anomaly() -> None:
    svc = _FakeService()
    scheduler = VirtualGoodsScheduler(service=svc)

    out = scheduler.callback_replay(limit=20)

    assert out["task"] == "callback_replay"
    assert out["ok"] is False
    assert out["metrics"]["fetched"] == 2
    assert out["metrics"]["replayed"] == 1
    assert out["metrics"]["succeeded"] == 1
    assert out["metrics"]["unknown_event_kind"] == 1
    assert out["anomalies"]["unknown_event_kind"] == 1
    assert any("unknown event_kind" in e for e in out["errors"])
    assert svc.anomalies and svc.anomalies[0][0] == "unknown_event_kind"


def test_manual_takeover_observe_structured_metrics() -> None:
    svc = _FakeService()
    scheduler = VirtualGoodsScheduler(service=svc)

    out = scheduler.manual_takeover_observe(limit=10)

    assert out["task"] == "manual_takeover_observe"
    assert out["ok"] is True
    assert out["metrics"] == {
        "manual_orders": 2,
        "observed": 2,
        "escalated": 1,
        "failed": 0,
    }
    assert any(name == "fetch_manual_takeover_orders" for name, _ in svc.calls)
    assert sum(1 for name, _ in svc.calls if name == "observe_manual_takeover") == 2
