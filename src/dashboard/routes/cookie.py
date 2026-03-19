"""Cookie lifecycle routes: get, update, parse, diagnose, validate, import, download, auto-grab, auto-refresh."""

from __future__ import annotations

import json
import threading
import time

from src.dashboard.router import RouteContext, get, post

# ---------------------------------------------------------------------------
# GET /api/get-cookie
# ---------------------------------------------------------------------------


@get("/api/get-cookie")
def handle_get_cookie(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.get_cookie())


# ---------------------------------------------------------------------------
# GET /api/download-cookie-plugin
# ---------------------------------------------------------------------------


@get("/api/download-cookie-plugin")
def handle_download_cookie_plugin(ctx: RouteContext) -> None:
    try:
        data, filename = ctx.mimic_ops.export_cookie_plugin_bundle()
        ctx.send_bytes(data=data, content_type="application/zip", download_name=filename)
    except FileNotFoundError as exc:
        from src.dashboard_server import _error_payload

        ctx.send_json(_error_payload(str(exc), code="NOT_FOUND"), status=404)


# ---------------------------------------------------------------------------
# GET /api/cookie/auto-grab/status  (SSE streaming)
# ---------------------------------------------------------------------------


@get("/api/cookie/auto-grab/status")
def handle_cookie_auto_grab_status(ctx: RouteContext) -> None:
    """SSE stream for cookie auto-grab progress."""
    ctx.send_response(200)
    ctx.send_header("Content-Type", "text/event-stream; charset=utf-8")
    ctx.send_header("Cache-Control", "no-cache")
    ctx.send_header("Connection", "keep-alive")
    ctx.end_headers()

    from src.dashboard_server import DashboardHandler

    grabber = getattr(DashboardHandler, "_cookie_grabber", None)
    try:
        for _ in range(600):
            if grabber is not None:
                p = grabber.progress
                event = json.dumps(
                    {
                        "stage": p.stage.value if hasattr(p.stage, "value") else str(p.stage),
                        "message": p.message,
                        "hint": p.hint,
                        "progress": p.progress,
                        "error": p.error,
                    },
                    ensure_ascii=False,
                )
                ctx.wfile.write(f"data: {event}\n\n".encode())
                ctx.wfile.flush()
                if p.stage.value in {"success", "failed", "cancelled"}:
                    break
            else:
                event = json.dumps(
                    {"stage": "idle", "message": "未在运行", "hint": "", "progress": 0, "error": ""},
                    ensure_ascii=False,
                )
                ctx.wfile.write(f"data: {event}\n\n".encode())
                ctx.wfile.flush()
                break
            time.sleep(0.5)
    except (BrokenPipeError, ConnectionResetError):
        return


# ---------------------------------------------------------------------------
# GET /api/cookie/auto-refresh/status
# ---------------------------------------------------------------------------


@get("/api/cookie/auto-refresh/status")
def handle_cookie_auto_refresh_status(ctx: RouteContext) -> None:
    from src.dashboard_server import DashboardHandler

    refresher = getattr(DashboardHandler, "_cookie_auto_refresher", None)
    if refresher is None:
        ctx.send_json(
            {
                "enabled": False,
                "interval_minutes": 0,
                "message": "自动刷新未启用（设置 COOKIE_AUTO_REFRESH=true 启用）",
            }
        )
    else:
        from dataclasses import asdict

        s = refresher.status()
        ctx.send_json(asdict(s))


# ---------------------------------------------------------------------------
# POST /api/update-cookie
# ---------------------------------------------------------------------------


@post("/api/update-cookie")
def handle_update_cookie(ctx: RouteContext) -> None:
    body = ctx.json_body()
    cookie = str(body.get("cookie") or "").strip()
    payload = ctx.mimic_ops.update_cookie(cookie, auto_recover=True)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/import-cookie-plugin
# ---------------------------------------------------------------------------


@post("/api/import-cookie-plugin")
def handle_import_cookie_plugin(ctx: RouteContext) -> None:
    try:
        files = ctx.multipart_files()
    except Exception as exc:
        ctx.send_json(
            {
                "success": False,
                "error": "Failed to parse upload body. Please retry with txt/json/zip exports.",
                "details": str(exc),
            },
            status=400,
        )
        return

    try:
        payload = ctx.mimic_ops.import_cookie_plugin_files(files, auto_recover=True)
    except Exception as exc:
        ctx.send_json(
            {
                "success": False,
                "error": "Cookie import processing failed.",
                "details": str(exc),
            },
            status=400,
        )
        return

    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/parse-cookie
# ---------------------------------------------------------------------------


@post("/api/parse-cookie")
def handle_parse_cookie(ctx: RouteContext) -> None:
    body = ctx.json_body()
    cookie_text = str(body.get("text") or body.get("cookie") or "").strip()
    payload = ctx.mimic_ops.parse_cookie_text(cookie_text)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/cookie-diagnose
# ---------------------------------------------------------------------------


@post("/api/cookie-diagnose")
def handle_cookie_diagnose(ctx: RouteContext) -> None:
    body = ctx.json_body()
    cookie_text = str(body.get("text") or body.get("cookie") or "").strip()
    payload = ctx.mimic_ops.diagnose_cookie(cookie_text)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/cookie/validate
# ---------------------------------------------------------------------------


@post("/api/cookie/validate")
def handle_cookie_validate(ctx: RouteContext) -> None:
    body = ctx.json_body()
    cookie_text = str(body.get("cookie") or body.get("text") or "").strip()
    if not cookie_text:
        ctx.send_json({"ok": False, "grade": "F", "message": "Cookie 不能为空"}, status=400)
        return
    diagnosis = ctx.mimic_ops.diagnose_cookie(cookie_text)
    domain_filter = ctx.mimic_ops._cookie_domain_filter_stats(cookie_text)
    grade = diagnosis.get("grade", "F")
    ctx.send_json(
        {
            "ok": grade in ("可用", "高风险"),
            "grade": grade,
            "message": diagnosis.get("message", ""),
            "actions": diagnosis.get("actions", []),
            "required_present": diagnosis.get("required_present", []),
            "required_missing": diagnosis.get("required_missing", []),
            "cookie_items": diagnosis.get("cookie_items", 0),
            "domain_filter": domain_filter,
        }
    )


# ---------------------------------------------------------------------------
# POST /api/cookie/auto-grab
# ---------------------------------------------------------------------------


@post("/api/cookie/auto-grab")
def handle_cookie_auto_grab(ctx: RouteContext) -> None:
    from src.core.cookie_grabber import CookieGrabber
    from src.dashboard_server import DashboardHandler

    if getattr(DashboardHandler, "_cookie_grab_running", False):
        ctx.send_json({"ok": False, "error": "已有获取任务在运行"}, status=409)
        return

    grabber = CookieGrabber()
    DashboardHandler._cookie_grabber = grabber
    DashboardHandler._cookie_grab_running = True

    def _run_grab() -> None:
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(grabber.auto_grab())
            DashboardHandler._cookie_grab_result = {
                "ok": result.ok,
                "source": result.source,
                "message": result.message,
                "error": result.error,
            }
        except Exception as exc:
            DashboardHandler._cookie_grab_result = {"ok": False, "error": str(exc)}
        finally:
            loop.close()
            DashboardHandler._cookie_grab_running = False

    t = threading.Thread(target=_run_grab, daemon=True)
    t.start()
    ctx.send_json({"ok": True, "message": "Cookie 获取任务已启动，请通过 SSE 接口监听进度"})


# ---------------------------------------------------------------------------
# POST /api/cookie/auto-grab/cancel
# ---------------------------------------------------------------------------


@post("/api/cookie/auto-grab/cancel")
def handle_cookie_auto_grab_cancel(ctx: RouteContext) -> None:
    from src.dashboard_server import DashboardHandler

    grabber = getattr(DashboardHandler, "_cookie_grabber", None)
    if grabber is not None:
        grabber.cancel()
        ctx.send_json({"ok": True, "message": "已取消"})
    else:
        ctx.send_json({"ok": False, "error": "没有正在运行的获取任务"})
