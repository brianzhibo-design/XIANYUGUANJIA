"""Configuration CRUD, intent rules, and manual mode routes."""

from __future__ import annotations

import logging
import os
from typing import Any

from src.core.config import get_config
from src.dashboard.config_service import (
    _ALLOWED_CONFIG_SECTIONS,
    _SENSITIVE_CONFIG_KEYS,
)
from src.dashboard.config_service import (
    CONFIG_SECTIONS as _CONFIG_SECTIONS,
)
from src.dashboard.config_service import (
    read_system_config as _read_system_config,
)
from src.dashboard.config_service import (
    write_system_config as _write_system_config,
)
from src.dashboard.router import RouteContext, get, post, put

# Lazy imports to avoid circular dependency with dashboard_server

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------


@get("/api/config")
def handle_config_get(ctx: RouteContext) -> None:
    cfg = _read_system_config()
    if "slider_auto_solve" not in cfg:
        yaml_slider = get_config().get_section("messages", {}).get("ws", {}).get("slider_auto_solve", {})
        if isinstance(yaml_slider, dict) and yaml_slider:
            cfg["slider_auto_solve"] = yaml_slider
    ar = cfg.get("auto_reply")
    if isinstance(ar, dict) and "custom_intent_rules" not in ar:
        yaml_rules = get_config().get_section("messages", {}).get("intent_rules", [])
        if isinstance(yaml_rules, list) and yaml_rules:
            ar["custom_intent_rules"] = yaml_rules
    ctx.send_json({"ok": True, "config": cfg})


# ---------------------------------------------------------------------------
# GET /api/config/sections
# ---------------------------------------------------------------------------


@get("/api/config/sections")
def handle_config_sections(ctx: RouteContext) -> None:
    ctx.send_json({"ok": True, "sections": _CONFIG_SECTIONS})


# ---------------------------------------------------------------------------
# GET /api/config/setup-progress
# ---------------------------------------------------------------------------


@get("/api/config/setup-progress")
def handle_setup_progress(ctx: RouteContext) -> None:
    cfg = _read_system_config()
    xgj = cfg.get("xianguanjia", {})
    ai_cfg = cfg.get("ai", {})
    oss_cfg = cfg.get("oss", {})
    store = cfg.get("store", {})
    ar = cfg.get("auto_reply", {})
    notif = cfg.get("notifications", {})

    def _has_real(d: dict, key: str) -> bool:
        v = d.get(key, "")
        return bool(v) and "****" not in str(v)

    checks = {
        "store_category": bool(store.get("category")),
        "xianguanjia": _has_real(xgj, "app_key"),
        "ai": _has_real(ai_cfg, "api_key"),
        "oss": _has_real(oss_cfg, "access_key_id"),
        "auto_reply": bool(ar.get("default_reply")),
        "notifications": bool(notif.get("feishu_enabled") or notif.get("wechat_enabled")),
    }
    done = sum(1 for v in checks.values() if v)
    total = len(checks)
    ctx.send_json(
        {
            "ok": True,
            **checks,
            "overall_percent": int(done / total * 100) if total else 0,
        }
    )


# ---------------------------------------------------------------------------
# GET /api/intent-rules
# ---------------------------------------------------------------------------


@get("/api/intent-rules")
def handle_intent_rules(ctx: RouteContext) -> None:
    from src.modules.messages.reply_engine import DEFAULT_INTENT_RULES

    sys_cfg = _read_system_config()
    ar = sys_cfg.get("auto_reply", {})
    custom_rules = ar.get("custom_intent_rules", [])
    if not isinstance(custom_rules, list):
        custom_rules = []
    yaml_rules = get_config().get_section("messages", {}).get("intent_rules", [])
    if isinstance(yaml_rules, list) and yaml_rules and not custom_rules:
        custom_rules = yaml_rules
    custom_names = {r.get("name") for r in custom_rules if isinstance(r, dict)}

    kw_text = ar.get("keyword_replies_text", "")
    kw_replies: dict[str, str] = {}
    if isinstance(kw_text, str) and kw_text.strip():
        for line in kw_text.strip().splitlines():
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and v:
                    kw_replies[k] = v

    result: list[dict[str, Any]] = []
    for r in DEFAULT_INTENT_RULES:
        entry = dict(r)
        if entry.get("name") in custom_names:
            entry["source"] = "overridden"
        else:
            entry["source"] = "builtin"
        result.append(entry)
    for r in custom_rules:
        if not isinstance(r, dict) or not r.get("name"):
            continue
        entry = dict(r)
        if entry["name"] not in {d.get("name") for d in DEFAULT_INTENT_RULES}:
            entry["source"] = "custom"
        else:
            entry["source"] = "custom"
        result.append(entry)
    for keyword, reply in kw_replies.items():
        result.append(
            {
                "name": f"legacy_{keyword}",
                "keywords": [keyword],
                "reply": reply,
                "priority": 30,
                "categories": [],
                "phase": "",
                "source": "keyword",
            }
        )
    ctx.send_json({"ok": True, "rules": result})


# ---------------------------------------------------------------------------
# GET /api/manual-mode
# ---------------------------------------------------------------------------


@get("/api/manual-mode")
def handle_manual_mode_get(ctx: RouteContext) -> None:
    from src.modules.messages.manual_mode import ManualModeStore

    timeout = int(get_config().get_section("messages", {}).get("manual_mode_timeout", 600))
    store = ManualModeStore(os.path.join("data", "manual_mode.db"), timeout_seconds=timeout)
    sessions = store.list_active()
    ctx.send_json(
        {
            "ok": True,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "enabled": s.enabled,
                    "updated_at": s.updated_at,
                    "expires_at": s.expires_at,
                }
                for s in sessions
            ],
            "timeout_seconds": timeout,
        }
    )


# ---------------------------------------------------------------------------
# POST /api/config  (also handles PUT /api/config — same logic)
# ---------------------------------------------------------------------------


def _save_config(ctx: RouteContext) -> None:
    """Shared config save logic for POST and PUT."""
    body = ctx.json_body()
    current = _read_system_config()
    for section, values in body.items():
        if section not in _ALLOWED_CONFIG_SECTIONS:
            continue
        if not isinstance(values, dict):
            continue
        clean: dict[str, Any] = {}
        for k, v in values.items():
            if not isinstance(k, str) or k.startswith("__"):
                continue
            if any(s in k.lower() for s in _SENSITIVE_CONFIG_KEYS) and isinstance(v, str) and "****" in v:
                continue
            clean[k] = v
        current[section] = {**(current.get(section) or {}), **clean}
    _write_system_config(current)
    get_config().reload()
    try:
        from src.dashboard.routes.system import invalidate_health_cache

        invalidate_health_cache()
    except Exception:
        pass
    try:
        from src.modules.messages.service import _active_service

        if _active_service is not None:
            _active_service.reload_rules()
            logger.info("Hot-reloaded reply rules after config save")
    except Exception as exc:
        logger.warning("Failed to hot-reload rules: %s", exc)
    ctx.send_json({"ok": True, "message": "Configuration updated", "config": current})


@post("/api/config")
def handle_config_post(ctx: RouteContext) -> None:
    _save_config(ctx)


@put("/api/config")
def handle_config_put(ctx: RouteContext) -> None:
    _save_config(ctx)


# ---------------------------------------------------------------------------
# POST /api/manual-mode
# ---------------------------------------------------------------------------


@post("/api/manual-mode")
def handle_manual_mode_post(ctx: RouteContext) -> None:
    body = ctx.json_body()
    sid = str(body.get("session_id", "")).strip()
    if not sid:
        from src.dashboard_server import _error_payload

        ctx.send_json(_error_payload("session_id required"), status=400)
        return
    enabled = body.get("enabled", True)
    from src.modules.messages.manual_mode import ManualModeStore

    timeout = int(get_config().get_section("messages", {}).get("manual_mode_timeout", 600))
    store = ManualModeStore(os.path.join("data", "manual_mode.db"), timeout_seconds=timeout)
    state = store.set_state(sid, bool(enabled))
    ctx.send_json(
        {
            "ok": True,
            "session_id": state.session_id,
            "enabled": state.enabled,
            "updated_at": state.updated_at,
            "expires_at": state.expires_at,
        }
    )


# ---------------------------------------------------------------------------
# L2 智能学习路由
# ---------------------------------------------------------------------------


@get("/api/intent-rules/suggestions")
def handle_intent_rules_suggestions(ctx: RouteContext) -> None:
    from src.modules.messages.rule_suggester import RuleSuggester

    suggester = RuleSuggester()
    suggestions = suggester.get_suggestions()
    ctx.send_json({"ok": True, "suggestions": suggestions})


@post("/api/intent-rules/analyze")
def handle_intent_rules_analyze(ctx: RouteContext) -> None:
    from src.modules.messages.rule_suggester import RuleSuggester

    suggester = RuleSuggester()
    suggestions = suggester.analyze_and_suggest()
    ctx.send_json({"ok": True, "suggestions": suggestions})


@post("/api/intent-rules/suggestions/{name}/adopt")
def handle_intent_rules_adopt(ctx: RouteContext, name: str) -> None:
    from src.modules.messages.rule_suggester import RuleSuggester

    suggester = RuleSuggester()
    ok = suggester.adopt_suggestion(name)
    if ok:
        ctx.send_json({"ok": True, "message": f"Rule '{name}' adopted"})
    else:
        ctx.send_json({"ok": False, "error": f"Suggestion '{name}' not found"}, status=404)


@post("/api/intent-rules/suggestions/{name}/reject")
def handle_intent_rules_reject(ctx: RouteContext, name: str) -> None:
    from src.modules.messages.rule_suggester import RuleSuggester

    suggester = RuleSuggester()
    suggester.reject_suggestion(name)
    ctx.send_json({"ok": True, "message": f"Rule '{name}' rejected"})
