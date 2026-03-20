"""System routes: health checks, module management, service control, database reset."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time as _time_mod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from src.dashboard.config_service import read_system_config as _read_system_config
from src.dashboard.config_service import write_system_config as _write_system_config
from src.dashboard.router import RouteContext, get, post


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Health check response cache (TTL 30s)
# ---------------------------------------------------------------------------

_health_cache: dict[str, Any] | None = None
_health_cache_ts: float = 0.0
_health_cache_lock = threading.Lock()
_HEALTH_CACHE_TTL = 30.0


def invalidate_health_cache() -> None:
    """Clear cached health check result so the next request fetches fresh data."""
    global _health_cache
    with _health_cache_lock:
        _health_cache = None


# ---------------------------------------------------------------------------
# GET /healthz, GET /api/health
# ---------------------------------------------------------------------------


@get("/api/health")
def handle_health_simple(ctx: RouteContext) -> None:
    ctx.send_json({"status": "ok"})


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
            ai_cfg = _read_system_config().get("ai", {})
            ai_key = ai_key or str(ai_cfg.get("api_key", "") or "")
            ai_base = ai_base or str(ai_cfg.get("base_url", "") or "")
            ai_model = ai_model or str(ai_cfg.get("model", "") or "")
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
        xgj_base = str(xgj_cfg.get("base_url", "") or os.environ.get("XGJ_BASE_URL", "https://open.goofish.pro"))
        if not xgj_app_key or not xgj_app_secret:
            return {"ok": False, "message": "AppKey 或 AppSecret 未配置"}
        from src.dashboard.mimic_ops import _test_xgj_connection

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
    payload = ctx.module_console.check()
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
    configured = bool(xgj.get("app_key") and xgj.get("app_secret") and "****" not in str(xgj.get("app_key", "")))
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
    from src.core.update_config import GITHUB_OWNER, GITHUB_REPO

    ctx.send_json(
        {
            "version": __version__,
            "releases_url": f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases",
        }
    )


_latest_version_cache: dict[str, Any] = {}
_latest_version_ts: float = 0.0
_LATEST_VERSION_TTL = 3600.0


def _gh_api_headers() -> dict[str, str]:
    from src.core.update_config import GITHUB_TOKEN

    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _gh_releases_url() -> str:
    from src.core.update_config import GITHUB_OWNER, GITHUB_REPO

    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


@get("/api/version/latest")
def handle_version_latest(ctx: RouteContext) -> None:
    """Proxy GitHub releases API with 1-hour cache. Uses gh CLI as fallback."""
    global _latest_version_cache, _latest_version_ts

    if _latest_version_cache and (_time_mod.time() - _latest_version_ts) < _LATEST_VERSION_TTL:
        ctx.send_json(_latest_version_cache)
        return

    # Try gh CLI first (authenticated, reliable)
    try:
        result = _fetch_latest_via_gh()
        if result:
            _latest_version_cache = result
            _latest_version_ts = _time_mod.time()
            ctx.send_json(result)
            return
    except Exception:
        pass

    # Fallback to HTTP API
    try:
        import httpx

        with httpx.Client(timeout=15.0) as hc:
            resp = hc.get(_gh_releases_url(), headers=_gh_api_headers())
        if resp.status_code == 200:
            release_data = resp.json()
            tag = release_data.get("tag_name", "")
            latest = tag.lstrip("v") if tag else None
            assets = release_data.get("assets", [])
            from src.core.update_config import UPDATE_ASSET_SUFFIX

            update_asset_url = ""
            update_asset_size = 0
            for asset in assets:
                if asset.get("name", "").endswith(UPDATE_ASSET_SUFFIX):
                    update_asset_url = asset.get("url", "")
                    update_asset_size = asset.get("size", 0)
                    break
            result = {
                "latest": latest,
                "tag": tag,
                "update_asset_url": update_asset_url,
                "update_asset_size": update_asset_size,
                "body": release_data.get("body", ""),
            }
            _latest_version_cache = result
            _latest_version_ts = _time_mod.time()
            ctx.send_json(result)
        else:
            ctx.send_json({"latest": None, "error": f"GitHub API returned {resp.status_code}"})
    except Exception as exc:
        ctx.send_json({"latest": None, "error": str(exc)})


def _fetch_latest_via_gh() -> dict[str, Any] | None:
    """Use gh CLI to fetch latest release (authenticated, bypasses IP rate limits)."""
    from src.core.update_config import GITHUB_OWNER, GITHUB_REPO

    try:
        proc = __import__("subprocess").run(
            ["gh", "api", f"repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest", "--jq", ".tag_name"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            tag = proc.stdout.strip()
            latest = tag.lstrip("v")
            return {"latest": latest, "tag": tag, "update_asset_url": "", "update_asset_size": 0, "body": ""}
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# POST /api/update/apply, GET /api/update/status
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_UPDATE_STATUS_FILE = _PROJECT_ROOT / "data" / "update-status.json"


def _cmp_ver(a: str, b: str) -> int:
    """Compare semver strings. Returns <0 if a<b, 0 if a==b, >0 if a>b."""
    pa = [int(x) for x in a.replace("v", "").split(".") if x.isdigit()]
    pb = [int(x) for x in b.replace("v", "").split(".") if x.isdigit()]
    for i in range(max(len(pa), len(pb))):
        na = pa[i] if i < len(pa) else 0
        nb = pb[i] if i < len(pb) else 0
        if na != nb:
            return na - nb
    return 0


def _read_update_status() -> dict[str, Any]:
    try:
        if _UPDATE_STATUS_FILE.exists():
            return json.loads(_UPDATE_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"status": "idle"}


def _write_update_status(status: str, **extra: Any) -> None:
    _UPDATE_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"status": status, "timestamp": _now_iso(), **extra}
    _UPDATE_STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _is_update_in_progress() -> bool:
    s = _read_update_status().get("status", "idle")
    return s not in ("idle", "error", "done")


def _do_update_in_background(latest: str, asset_url: str, checksum_url: str = "") -> None:
    """Download update package, verify SHA256, and spawn the install script."""
    try:
        import hashlib

        _write_update_status("downloading", version=latest)
        dl_headers = _gh_api_headers()
        dl_headers["Accept"] = "application/octet-stream"
        tmp_path = Path(tempfile.gettempdir()) / f"xianyu-update-{latest}.tar.gz"

        import httpx

        with httpx.Client(timeout=180.0, follow_redirects=True) as hc:
            with hc.stream("GET", asset_url, headers=dl_headers) as stream:
                stream.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=65536):
                        f.write(chunk)

            if checksum_url:
                _write_update_status("verifying", version=latest)
                cs_headers = _gh_api_headers()
                cs_headers["Accept"] = "application/octet-stream"
                cs_resp = hc.get(checksum_url, headers=cs_headers, follow_redirects=True)
                if cs_resp.status_code == 200:
                    expected_hash = cs_resp.text.strip().split()[0].lower()
                    actual_hash = hashlib.sha256(tmp_path.read_bytes()).hexdigest().lower()
                    if expected_hash != actual_hash:
                        tmp_path.unlink(missing_ok=True)
                        _write_update_status(
                            "error",
                            message=f"SHA256 校验失败: 期望 {expected_hash[:16]}…, 实际 {actual_hash[:16]}…",
                        )
                        return

        _write_update_status("installing", version=latest, package=str(tmp_path))

        project_root = str(_PROJECT_ROOT)
        (_PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            script = str(_PROJECT_ROOT / "scripts" / "update.bat")
            subprocess.Popen(
                ["cmd", "/c", script, str(tmp_path), project_root],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                close_fds=True,
            )
        else:
            script = str(_PROJECT_ROOT / "scripts" / "update.sh")
            log_path = _PROJECT_ROOT / "logs" / "update.log"
            log_fd = open(log_path, "a")
            try:
                subprocess.Popen(
                    ["bash", script, str(tmp_path), project_root],
                    cwd=project_root,
                    start_new_session=True,
                    close_fds=True,
                    stdout=log_fd,
                    stderr=subprocess.STDOUT,
                )
            finally:
                log_fd.close()
    except Exception as exc:
        _write_update_status("error", message=str(exc))


@get("/api/update/status")
def handle_update_status(ctx: RouteContext) -> None:
    ctx.send_json(_read_update_status())


@post("/api/update/apply")
def handle_update_apply(ctx: RouteContext) -> None:
    if _is_update_in_progress():
        ctx.send_json({"success": False, "error": "更新正在进行中"}, status=409)
        return

    try:
        from src import __version__ as current_version
        from src.core.update_config import CHECKSUM_ASSET_SUFFIX, UPDATE_ASSET_SUFFIX

        _write_update_status("checking")

        import httpx

        with httpx.Client(timeout=15.0) as hc:
            resp = hc.get(_gh_releases_url(), headers=_gh_api_headers())
        if resp.status_code != 200:
            _write_update_status("error", message=f"GitHub API {resp.status_code}")
            ctx.send_json({"success": False, "error": f"无法获取最新版本: HTTP {resp.status_code}"})
            return

        release = resp.json()
        tag = release.get("tag_name", "")
        latest = tag.lstrip("v") if tag else ""
        if not latest:
            _write_update_status("error", message="无法解析版本号")
            ctx.send_json({"success": False, "error": "无法解析最新版本号"})
            return

        if _cmp_ver(current_version, latest) >= 0:
            _write_update_status("idle")
            ctx.send_json({"success": False, "error": f"当前版本 {current_version} 已是最新"})
            return

        asset_url = ""
        checksum_url = ""
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(UPDATE_ASSET_SUFFIX):
                asset_url = asset.get("url", "")
            elif name.endswith(CHECKSUM_ASSET_SUFFIX):
                checksum_url = asset.get("url", "")
        if not asset_url:
            _write_update_status("error", message="Release 中未找到更新包")
            ctx.send_json({"success": False, "error": "Release 中未找到更新包 (*-update.tar.gz)"})
            return

        threading.Thread(
            target=_do_update_in_background,
            args=(latest, asset_url, checksum_url),
            daemon=True,
        ).start()

        ctx.send_json({"success": True, "status": "checking", "version": latest})
    except Exception as exc:
        _write_update_status("error", message=str(exc))
        ctx.send_json({"success": False, "error": str(exc)}, status=500)


# ---------------------------------------------------------------------------
# GET /api/wizard/status, POST /api/wizard/complete
# ---------------------------------------------------------------------------


@get("/api/wizard/status")
def handle_wizard_status(ctx: RouteContext) -> None:
    cfg = _read_system_config()
    ctx.send_json(
        {
            "completed": bool(cfg.get("wizard_completed")),
            "completed_at": cfg.get("wizard_completed_at", ""),
        }
    )


@post("/api/wizard/complete")
def handle_wizard_complete(ctx: RouteContext) -> None:
    cfg = _read_system_config()
    cfg["wizard_completed"] = True
    cfg["wizard_completed_at"] = _now_iso()
    _write_system_config(cfg)
    ctx.send_json({"ok": True})
