"""Dashboard legacy data endpoints + log viewer routes."""

from __future__ import annotations

import json
import time
from datetime import datetime

from src.dashboard.router import RouteContext, get


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _safe_int(value: str | None, default: int, min_value: int, max_value: int) -> int:
    try:
        if value is None:
            return default
        n = int(value)
        if n < min_value:
            return min_value
        if n > max_value:
            return max_value
        return n
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# GET /api/summary, /api/trend, /api/recent-operations, /api/top-products
# These 4 routes are handled by _legacy_dashboard_payload on DashboardHandler.
# ---------------------------------------------------------------------------


@get("/api/summary")
def handle_summary(ctx: RouteContext) -> None:
    ctx.send_json(ctx._handler._legacy_dashboard_payload(ctx.path, ctx.query))


@get("/api/trend")
def handle_trend(ctx: RouteContext) -> None:
    ctx.send_json(ctx._handler._legacy_dashboard_payload(ctx.path, ctx.query))


@get("/api/recent-operations")
def handle_recent_operations(ctx: RouteContext) -> None:
    ctx.send_json(ctx._handler._legacy_dashboard_payload(ctx.path, ctx.query))


@get("/api/top-products")
def handle_top_products(ctx: RouteContext) -> None:
    ctx.send_json(ctx._handler._legacy_dashboard_payload(ctx.path, ctx.query))


# ---------------------------------------------------------------------------
# GET /api/dashboard
# ---------------------------------------------------------------------------


@get("/api/dashboard")
def handle_dashboard(ctx: RouteContext) -> None:
    aggregate = ctx.mimic_ops.get_dashboard_readonly_aggregate()
    ctx.send_json(aggregate, status=200 if aggregate.get("success") else 400)


# ---------------------------------------------------------------------------
# GET /api/logs/files
# ---------------------------------------------------------------------------


@get("/api/unmatched-stats")
def handle_unmatched_stats(ctx: RouteContext) -> None:
    """未匹配消息统计：高频词 Top10 + 每日趋势。"""
    result = ctx.mimic_ops.get_unmatched_message_stats(max_lines=3000, top_n=10)
    ctx.send_json(result, status=200 if result.get("ok") else 400)


@get("/api/logs/files")
def handle_logs_files(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.list_log_files())


# ---------------------------------------------------------------------------
# GET /api/logs/content
# ---------------------------------------------------------------------------


@get("/api/logs/content")
def handle_logs_content(ctx: RouteContext) -> None:
    file_name = ctx.query_str("file", "").strip()
    tail = _safe_int((ctx.query.get("tail") or ["200"])[0], default=200, min_value=1, max_value=5000)
    page_raw = (ctx.query.get("page") or [None])[0]
    size_raw = (ctx.query.get("size") or [None])[0]
    search = ctx.query_str("search", "").strip()

    if page_raw is not None or size_raw is not None or search:
        page = _safe_int(
            str(page_raw) if page_raw is not None else None,
            default=1,
            min_value=1,
            max_value=100000,
        )
        size = _safe_int(
            str(size_raw) if size_raw is not None else None,
            default=100,
            min_value=10,
            max_value=2000,
        )
        payload = ctx.mimic_ops.read_log_content(
            file_name=file_name,
            page=page,
            size=size,
            search=search,
        )
    else:
        payload = ctx.mimic_ops.read_log_content(file_name=file_name, tail=tail)

    ctx.send_json(payload, status=200 if payload.get("success") else 404)


# ---------------------------------------------------------------------------
# GET /api/logs/realtime/stream  (SSE — streaming response exception)
# ---------------------------------------------------------------------------


@get("/api/logs/realtime/stream")
def handle_logs_realtime_stream(ctx: RouteContext) -> None:
    """Server-Sent Events stream for real-time log tailing.

    This route uses ctx._handler directly for streaming response headers
    and wfile access — this is an intentional exception to the RouteContext
    abstraction for SSE support.
    """
    file_name = ctx.query_str("file", "presales").strip()
    tail = _safe_int((ctx.query.get("tail") or ["200"])[0], default=200, min_value=1, max_value=1000)

    ctx.send_response(200)
    ctx.send_header("Content-Type", "text/event-stream; charset=utf-8")
    ctx.send_header("Cache-Control", "no-cache")
    ctx.send_header("Connection", "keep-alive")
    ctx.end_headers()

    last = ""
    try:
        for _ in range(180):
            payload = ctx.mimic_ops.read_log_content(file_name=file_name, tail=tail)
            lines = payload.get("lines", []) if payload.get("success") else [payload.get("error", "log not found")]
            text = "\n".join(lines)
            if text != last:
                event = json.dumps(
                    {"success": True, "lines": lines, "updated_at": _now_iso()},
                    ensure_ascii=False,
                )
                ctx.wfile.write(f"data: {event}\n\n".encode())
                ctx.wfile.flush()
                last = text
            time.sleep(1)
    except (BrokenPipeError, ConnectionResetError):
        return
