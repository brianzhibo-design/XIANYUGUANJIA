"""Slider verification stats API routes."""

from __future__ import annotations

import os
from typing import Any

from src.dashboard.router import RouteContext, get, get_prefix


@get("/api/slider/stats")
def handle_slider_stats(ctx: RouteContext) -> None:
    hours = ctx.query_int("hours", default=24, min_val=1, max_val=720)
    try:
        from src.core.slider_store import SliderEventStore
        store = SliderEventStore.get_instance()
        stats = store.get_stats(hours)
        ctx.send_json({"ok": True, **stats})
    except Exception as exc:
        ctx.send_json({"ok": False, "error": str(exc)}, status=500)


@get("/api/slider/events")
def handle_slider_events(ctx: RouteContext) -> None:
    limit = ctx.query_int("limit", default=50, min_val=1, max_val=200)
    try:
        from src.core.slider_store import SliderEventStore
        store = SliderEventStore.get_instance()
        events = store.get_recent_events(limit)
        ctx.send_json({"ok": True, "events": events})
    except Exception as exc:
        ctx.send_json({"ok": False, "error": str(exc)}, status=500)


@get_prefix("/api/slider/screenshot/", param_name="filename")
def handle_slider_screenshot(ctx: RouteContext) -> None:
    """Serve a slider screenshot image by filename."""
    filename = ctx.path_params.get("filename", "")
    if not filename or ".." in filename or "/" in filename:
        ctx.send_json({"error": "invalid filename"}, status=400)
        return

    screenshot_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "slider_screenshots"
    )
    filepath = os.path.join(screenshot_dir, filename)
    if not os.path.isfile(filepath):
        ctx.send_json({"error": "not found"}, status=404)
        return

    with open(filepath, "rb") as f:
        data = f.read()
    ctx.send_bytes(data, content_type="image/png", status=200)
