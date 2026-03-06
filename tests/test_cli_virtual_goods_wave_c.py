from __future__ import annotations

import argparse

import pytest

from src import cli


class _VGServiceStub:
    def __init__(self, db_path: str = "data/orders.db") -> None:
        self.db_path = db_path

    def scheduler_run(self, *, max_events: int) -> dict:
        return {"max_events": max_events, "handled": 2}

    def scheduler_dry_run(self, *, max_events: int) -> dict:
        return {"max_events": max_events, "preview": 3}

    def replay(self, *, event_id=None, dedupe_key=None) -> dict:
        return {"event_id": event_id, "dedupe_key": dedupe_key, "replayed": True}

    def manual_list(self, *, order_ids: list[str]) -> dict:
        return {"order_ids": order_ids, "total": len(order_ids)}

    def manual_set(self, *, order_id: str, enabled: bool) -> dict:
        return {"order_id": order_id, "enabled": enabled}

    def inspect(self, *, event_id=None, order_id=None) -> dict:
        return {"event_id": event_id, "order_id": order_id, "exists": True}


@pytest.mark.asyncio
async def test_virtual_goods_scheduler_run(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr("src.modules.virtual_goods.service.VirtualGoodsService", _VGServiceStub)
    monkeypatch.setattr("src.cli._json_out", lambda data: out.append(data))

    await cli.cmd_virtual_goods(
        argparse.Namespace(action="scheduler", db_path="/tmp/vg.db", dry_run=False, max_events=5)
    )

    assert out
    payload = out[-1]
    assert payload["ok"] is True
    assert payload["action"] == "virtual_goods_scheduler_run"
    assert payload["max_events"] == 5


@pytest.mark.asyncio
async def test_virtual_goods_scheduler_dry_run(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr("src.modules.virtual_goods.service.VirtualGoodsService", _VGServiceStub)
    monkeypatch.setattr("src.cli._json_out", lambda data: out.append(data))

    await cli.cmd_virtual_goods(
        argparse.Namespace(action="scheduler", db_path="/tmp/vg.db", dry_run=True, max_events=7)
    )

    payload = out[-1]
    assert payload["ok"] is True
    assert payload["action"] == "virtual_goods_scheduler_dry_run"
    assert payload["preview"] == 3


@pytest.mark.asyncio
async def test_virtual_goods_replay_with_event_id(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr("src.modules.virtual_goods.service.VirtualGoodsService", _VGServiceStub)
    monkeypatch.setattr("src.cli._json_out", lambda data: out.append(data))

    await cli.cmd_virtual_goods(
        argparse.Namespace(action="replay", db_path="/tmp/vg.db", event_id="1001", dedupe_key=None)
    )

    payload = out[-1]
    assert payload["ok"] is True
    assert payload["action"] == "virtual_goods_replay"
    assert payload["event_id"] == "1001"


@pytest.mark.asyncio
async def test_virtual_goods_replay_with_dedupe_key(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr("src.modules.virtual_goods.service.VirtualGoodsService", _VGServiceStub)
    monkeypatch.setattr("src.cli._json_out", lambda data: out.append(data))

    await cli.cmd_virtual_goods(
        argparse.Namespace(action="replay", db_path="/tmp/vg.db", event_id=None, dedupe_key="dedupe-1")
    )

    payload = out[-1]
    assert payload["ok"] is True
    assert payload["dedupe_key"] == "dedupe-1"


@pytest.mark.asyncio
async def test_virtual_goods_manual_list_and_set(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr("src.modules.virtual_goods.service.VirtualGoodsService", _VGServiceStub)
    monkeypatch.setattr("src.cli._json_out", lambda data: out.append(data))

    await cli.cmd_virtual_goods(
        argparse.Namespace(
            action="manual",
            db_path="/tmp/vg.db",
            manual_action="list",
            order_ids=["o1", "o2"],
            order_id=None,
            enabled=False,
        )
    )
    await cli.cmd_virtual_goods(
        argparse.Namespace(
            action="manual",
            db_path="/tmp/vg.db",
            manual_action="set",
            order_ids=[],
            order_id="o1",
            enabled=True,
        )
    )

    assert out[-2]["action"] == "virtual_goods_manual_list"
    assert out[-2]["ok"] is True
    assert out[-1]["action"] == "virtual_goods_manual_set"
    assert out[-1]["enabled"] is True


@pytest.mark.asyncio
async def test_virtual_goods_inspect(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr("src.modules.virtual_goods.service.VirtualGoodsService", _VGServiceStub)
    monkeypatch.setattr("src.cli._json_out", lambda data: out.append(data))

    await cli.cmd_virtual_goods(
        argparse.Namespace(action="inspect", db_path="/tmp/vg.db", event_id="9", order_id="o9")
    )

    payload = out[-1]
    assert payload["ok"] is True
    assert payload["action"] == "virtual_goods_inspect"
    assert payload["event_id"] == "9"
    assert payload["order_id"] == "o9"


def test_virtual_goods_parser_actions():
    parser = cli.build_parser()
    args = parser.parse_args(["virtual-goods", "--action", "scheduler", "--dry-run"])
    assert args.command == "virtual-goods"
    assert args.action == "scheduler"
    assert args.dry_run is True
