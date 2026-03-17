"""System routes: health checks, module management, service control, database reset."""

from __future__ import annotations

import json
import os
import threading
import time as _time_mod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from src.dashboard.router import RouteContext, get, post

from src.dashboard.config_service import read_system_config as _read_system_config
from src.dashboard.config_service import write_system_config as _write_system_config


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Health check response cache (TTL 30s)
# ---------------------------------------------------------------------------

_health_cache: dict[str, Any] | None = None
_health_cache_ts: float = 0.0
_health_cache_lock = threading.Lock()
_HEALTH_CACHE_TTL = 30.0


# ---------------------------------------------------------------------------
# GET /healthz
# ---------------------------------------------------------------------------


@get("/healthz")
def handle_healthz(ctx: RouteContext) -> None:
    db_ok = False
    try:
        with ctx.repo._connect() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    modules_summary: dict[str, str] = {}
    try:
        status_payload = ctx.mimic_ops.service_status()
        if isinstance(status_payload, dict):
            modules_summary = {
                "system_running": "alive" if status_payload.get("system_running") else "dead",
                "alive_count": str(status_payload.get("alive_count", 0)),
                "total_modules": str(status_payload.get("total_modules", 0)),
            }
    except Exception:
        modules_summary = {"error": "status_check_failed"}

    started = getattr(ctx.mimic_ops, "_service_started_at", "")
    uptime_seconds = 0
    if started:
        try:
            start_dt = datetime.strptime(started, "%Y-%m-%dT%H:%M:%S")
            uptime_seconds = int((datetime.now() - start_dt).total_seconds())
        except Exception:
            pass

    ctx.send_json(
        {
            "status": "ok" if db_ok else "degraded",
            "timestamp": _now_iso(),
            "database": "writable" if db_ok else "error",
            "modules": modules_summary,
            "uptime_seconds": uptime_seconds,
        }
    )


# ---------------------------------------------------------------------------
# GET /api/health/check
# ---------------------------------------------------------------------------


def _check_cookie_health(cookie_text: str) -> dict[str, Any]:
    try:
        from src.core.cookie_health import CookieHealthChecker

        checker = CookieHealthChecker(cookie_text, timeout_seconds=8.0)
        ck_result = checker.check_sync(force=True)
        return {"ok": bool(ck_result.get("healthy")), "message": ck_result.get("message", "")}
    except Exception as exc:
        return {"ok": False, "message": f"检查异常: {exc}"}


def _check_ai_health() -> dict[str, Any]:
    try:
        ai_key = os.environ.get("AI_API_KEY", "")
        ai_base = os.environ.get("AI_BASE_URL", "")
        ai_model = os.environ.get("AI_MODEL", "")
        if not ai_key or not ai_base:
            try:
                _sys_cfg_path = Path(__file__).resolve().parents[3] / "data" / "system_config.json"
                if _sys_cfg_path.exists():
                    _sys_cfg = json.loads(_sys_cfg_path.read_text(encoding="utf-8"))
                    ai_cfg = _sys_cfg.get("ai", {})
                    ai_key = ai_key or str(ai_cfg.get("api_key", "") or "")
                    ai_base = ai_base or str(ai_cfg.get("base_url", "") or "")
                    ai_model = ai_model or str(ai_cfg.get("model", "") or "")
            except Exception:
                pass
        ai_model = ai_model or "qwen-plus"
        if ai_key and ai_base:
            t0 = _time_mod.time()
            import httpx

            chat_url = ai_base.rstrip("/") + "/chat/completions"
            with httpx.Client(timeout=8.0) as hc:
                resp = hc.post(
                    chat_url,
                    headers={"Authorization": f"Bearer {ai_key}", "Content-Type": "application/json"},
                    json={
                        "model": ai_model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
            latency = int((_time_mod.time() - t0) * 1000)
            if resp.status_code == 200:
                return {"ok": True, "message": "连通", "latency_ms": latency}
            _status_msgs = {401: "API Key 无效", 403: "无权访问", 429: "请求过频"}
            _msg = _status_msgs.get(resp.status_code, f"HTTP {resp.status_code}")
            return {"ok": False, "message": _msg, "latency_ms": latency}
        return {"ok": False, "message": "API Key 或 Base URL 未配置"}
    except Exception as exc:
        return {"ok": False, "message": f"检查异常: {type(exc).__name__}"}


def _check_xgj_health() -> dict[str, Any]:
    try:
        sys_cfg = _read_system_config()
        xgj_cfg = sys_cfg.get("xianguanjia", {})
        xgj_app_key = str(xgj_cfg.get("app_key", "") or os.environ.get("XGJ_APP_KEY", ""))
        xgj_app_secret = str(xgj_cfg.get("app_secret", "") or os.environ.get("XGJ_APP_SECRET", ""))
        xgj_base = str(
            xgj_cfg.get("base_url", "") or os.environ.get("XGJ_BASE_URL", "https://open.goofish.pro")
        )
        if not xgj_app_key or not xgj_app_secret:
            return {"ok": False, "message": "AppKey 或 AppSecret 未配置"}
        from src.dashboard_server import _test_xgj_connection

        return _test_xgj_connection(
            app_key=xgj_app_key,
            app_secret=xgj_app_secret,
            base_url=xgj_base,
            mode=str(xgj_cfg.get("mode", "self_developed")),
            seller_id=str(xgj_cfg.get("seller_id", "")),
        )
    except Exception as exc:
        return {"ok": False, "message": f"检查异常: {type(exc).__name__}"}


@get("/api/health/check")
def handle_health_check(ctx: RouteContext) -> None:
    global _health_cache, _health_cache_ts

    with _health_cache_lock:
        if _health_cache is not None and (_time_mod.time() - _health_cache_ts) < _HEALTH_CACHE_TTL:
            ctx.send_json(_health_cache)
            return

    cookie_text = os.environ.get("XIANYU_COOKIE_1", "")
    if not cookie_text:
        try:
            ck = ctx.mimic_ops.get_cookie()
            cookie_text = str(ck.get("cookie", "") or "")
        except Exception:
            pass

    result: dict[str, Any] = {"timestamp": _now_iso()}
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_cookie = pool.submit(_check_cookie_health, cookie_text)
        fut_ai = pool.submit(_check_ai_health)
        fut_xgj = pool.submit(_check_xgj_health)

        result["cookie"] = fut_cookie.result(timeout=12)
        result["ai"] = fut_ai.result(timeout=12)
        result["xgj"] = fut_xgj.result(timeout=12)

    result["services"] = {"python": {"ok": True, "message": "运行中"}}

    with _health_cache_lock:
        _health_cache = result
        _health_cache_ts = _time_mod.time()

    ctx.send_json(result)


# ---------------------------------------------------------------------------
# GET /api/module/*
# ---------------------------------------------------------------------------


@get("/api/module/status")
def handle_module_status(ctx: RouteContext) -> None:
    window = ctx.query_int("window", default=60, min_val=1, max_val=10080)
    limit = ctx.query_int("limit", default=20, min_val=1, max_val=200)
    payload = ctx.module_console.status(window_minutes=window, limit=limit)
    status = 200 if not payload.get("error") else 500
    ctx.send_json(payload, status=status)


@get("/api/module/check")
def handle_module_check(ctx: RouteContext) -> None:
    skip_gateway = ctx.query_bool("skip_gateway")
    payload = ctx.module_console.check(skip_gateway=skip_gateway)
    status = 200 if not payload.get("error") else 500
    ctx.send_json(payload, status=status)


@get("/api/module/logs")
def handle_module_logs(ctx: RouteContext) -> None:
    target = ctx.query_str("target", "all").strip().lower()
    tail = ctx.query_int("tail", default=120, min_val=10, max_val=500)
    payload = ctx.module_console.logs(target=target, tail_lines=tail)
    status = 200 if not payload.get("error") else 500
    ctx.send_json(payload, status=status)


# ---------------------------------------------------------------------------
# GET /api/status, /api/service-status
# ---------------------------------------------------------------------------


@get("/api/status")
def handle_status(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.service_status())


@get("/api/service-status")
def handle_service_status(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.service_status())


# ---------------------------------------------------------------------------
# POST /api/module/control
# ---------------------------------------------------------------------------


@post("/api/module/control")
def handle_module_control(ctx: RouteContext) -> None:
    body = ctx.json_body()
    action = str(body.get("action") or "").strip().lower()
    target = str(body.get("target") or "all").strip().lower()
    payload = ctx.module_console.control(action=action, target=target)
    status = 200 if not payload.get("error") else 400
    ctx.send_json(payload, status=status)


# ---------------------------------------------------------------------------
# POST /api/service/control, /api/service/recover, /api/service/auto-fix
# ---------------------------------------------------------------------------


@post("/api/service/control")
def handle_service_control(ctx: RouteContext) -> None:
    body = ctx.json_body()
    action = str(body.get("action") or "").strip().lower()
    payload = ctx.mimic_ops.service_control(action=action)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/service/recover")
def handle_service_recover(ctx: RouteContext) -> None:
    body = ctx.json_body()
    target = str(body.get("target") or "presales").strip().lower()
    payload = ctx.mimic_ops.service_recover(target=target)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/service/auto-fix")
def handle_service_auto_fix(ctx: RouteContext) -> None:
    payload = ctx.mimic_ops.service_auto_fix()
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/reset-database
# ---------------------------------------------------------------------------


@post("/api/reset-database")
def handle_reset_database(ctx: RouteContext) -> None:
    body = ctx.json_body()
    db_type = str(body.get("type") or "all")
    payload = ctx.mimic_ops.reset_database(db_type=db_type)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# GET /api/accounts
# ---------------------------------------------------------------------------


@get("/api/accounts")
def handle_accounts(ctx: RouteContext) -> None:
    """返回账户列表 — 前端 AccountList 页面使用。"""
    cfg = _read_system_config()
    xgj = cfg.get("xianguanjia", {})
    configured = bool(
        xgj.get("app_key")
        and xgj.get("app_secret")
        and "****" not in str(xgj.get("app_key", ""))
    )
    accounts = [
        {
            "id": "default",
            "name": "默认店铺",
            "enabled": True,
            "configured": configured,
        }
    ]
    ctx.send_json({"ok": True, "accounts": accounts})


# ---------------------------------------------------------------------------
# GET /api/version
# ---------------------------------------------------------------------------


@get("/api/version")
def handle_version(ctx: RouteContext) -> None:
    try:
        from src import __version__
    except Exception:
        __version__ = "unknown"
    ctx.send_json({
        "version": __version__,
        "releases_url": "https://github.com/openclawlab/xianyu-openclaw/releases",
    })


_latest_version_cache: dict[str, Any] = {}
_latest_version_ts: float = 0.0
_LATEST_VERSION_TTL = 3600.0


@get("/api/version/latest")
def handle_version_latest(ctx: RouteContext) -> None:
    """Proxy GitHub releases API with 1-hour cache to avoid rate limits and China access issues."""
    global _latest_version_cache, _latest_version_ts

    if _latest_version_cache and (_time_mod.time() - _latest_version_ts) < _LATEST_VERSION_TTL:
        ctx.send_json(_latest_version_cache)
        return

    try:
        import httpx
        with httpx.Client(timeout=10.0) as hc:
            resp = hc.get(
                "https://api.github.com/repos/openclawlab/xianyu-openclaw/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
        if resp.status_code == 200:
            tag = resp.json().get("tag_name", "")
            latest = tag.lstrip("v") if tag else None
            result: dict[str, Any] = {"latest": latest, "tag": tag}
            _latest_version_cache = result
            _latest_version_ts = _time_mod.time()
            ctx.send_json(result)
        else:
            ctx.send_json({"latest": None, "error": f"GitHub API returned {resp.status_code}"})
    except Exception as exc:
        ctx.send_json({"latest": None, "error": str(exc)})


# ---------------------------------------------------------------------------
# GET /api/wizard/status, POST /api/wizard/complete
# ---------------------------------------------------------------------------


@get("/api/wizard/status")
def handle_wizard_status(ctx: RouteContext) -> None:
    cfg = _read_system_config()
    ctx.send_json({
        "completed": bool(cfg.get("wizard_completed")),
        "completed_at": cfg.get("wizard_completed_at", ""),
    })


@post("/api/wizard/complete")
def handle_wizard_complete(ctx: RouteContext) -> None:
    cfg = _read_system_config()
    cfg["wizard_completed"] = True
    cfg["wizard_completed_at"] = _now_iso()
    _write_system_config(cfg)
    ctx.send_json({"ok": True})
