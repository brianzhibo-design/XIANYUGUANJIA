"""L2 智能学习 — LLM 规则建议的生成与应用。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.dashboard.config_service import (
    read_system_config as _read_system_config,
    write_system_config as _write_system_config,
)
from src.dashboard.router import RouteContext, post

logger = logging.getLogger(__name__)

_MAX_UNMATCHED_FOR_LLM = 100
_DEDUP_SIMILARITY_THRESHOLD = 0.85


def _read_recent_unmatched(project_root: Path, max_lines: int = 500) -> list[str]:
    """读取最近 N 条未匹配消息并去重。"""
    path = project_root / "data" / "unmatched_messages.jsonl"
    if not path.exists():
        return []
    lines: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                lines.append(line)
                if len(lines) > max_lines:
                    lines.pop(0)
    except Exception:
        return []
    msgs: list[str] = []
    seen: set[str] = set()
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            msg = (obj.get("msg") or "").strip()
            if msg and msg not in seen and len(msg) >= 2:
                seen.add(msg)
                msgs.append(msg)
                if len(msgs) >= _MAX_UNMATCHED_FOR_LLM:
                    break
        except Exception:
            continue
    return msgs


def _get_existing_rule_names() -> list[str]:
    from src.modules.messages.reply_engine import DEFAULT_INTENT_RULES

    cfg = _read_system_config()
    custom = cfg.get("auto_reply", {}).get("custom_intent_rules", [])
    names = [r.get("name", "") for r in DEFAULT_INTENT_RULES if isinstance(r, dict)]
    if isinstance(custom, list):
        names.extend(r.get("name", "") for r in custom if isinstance(r, dict))
    return [n for n in names if n]


def _build_suggestion_prompt(messages: list[str], existing_names: list[str]) -> str:
    msg_block = "\n".join(f"- {m}" for m in messages[:_MAX_UNMATCHED_FOR_LLM])
    names_block = "、".join(existing_names[:50]) if existing_names else "（无）"
    return f"""你是一个快递代发客服系统的规则配置专家。

以下是近期未被任何规则匹配的买家消息（已去重）：
{msg_block}

已有的规则名称列表（避免重复）：
{names_block}

请分析这些消息，找出可以归纳为新规则的模式。对每个建议的规则，输出以下 JSON 格式：

```json
[
  {{
    "name": "规则英文标识（snake_case）",
    "keywords": ["关键词1", "关键词2"],
    "reply": "自动回复内容（口语化、友好、简洁）",
    "priority": 100,
    "reason": "一句话说明为什么建议这条规则"
  }}
]
```

要求：
1. 只建议确实有重复出现模式的规则，不要为单条消息创建规则
2. 关键词要精准，避免误匹配
3. 回复语气要像快递客服，亲切自然
4. 优先级建议 80-120 之间
5. 最多建议 5 条规则
6. 只输出 JSON 数组，不要其他内容"""


def _parse_llm_suggestions(raw: str) -> list[dict[str, Any]]:
    """从 LLM 返回文本中提取 JSON 数组。"""
    json_match = re.search(r"\[[\s\S]*\]", raw)
    if not json_match:
        return []
    try:
        items = json.loads(json_match.group())
    except json.JSONDecodeError:
        return []
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        keywords = item.get("keywords", [])
        reply = str(item.get("reply", "")).strip()
        if not name or not keywords or not reply:
            continue
        result.append({
            "name": name,
            "keywords": keywords if isinstance(keywords, list) else [str(keywords)],
            "reply": reply,
            "priority": int(item.get("priority", 100)),
            "reason": str(item.get("reason", "")),
        })
    return result


@post("/api/rule-suggestions/generate")
def handle_generate_suggestions(ctx: RouteContext) -> None:
    """读取未匹配消息，调用 LLM 生成规则建议。"""
    from src.dashboard_server import _error_payload

    msgs = _read_recent_unmatched(ctx.mimic_ops.project_root)
    if not msgs:
        ctx.send_json({"ok": True, "suggestions": [], "message": "暂无未匹配消息"})
        return

    existing_names = _get_existing_rule_names()
    prompt = _build_suggestion_prompt(msgs, existing_names)

    try:
        from src.modules.content.service import ContentService
        svc = ContentService()
        raw = svc._call_ai(prompt, max_tokens=2000, task="rule_suggestion")
    except Exception as exc:
        logger.warning("LLM call failed for rule suggestions: %s", exc)
        ctx.send_json(_error_payload(f"AI 调用失败: {exc}"), status=500)
        return

    if not raw:
        ctx.send_json(_error_payload("AI 未返回有效内容，请检查 AI 配置是否可用"), status=500)
        return

    suggestions = _parse_llm_suggestions(raw)
    ctx.send_json({
        "ok": True,
        "suggestions": suggestions,
        "analyzed_count": len(msgs),
    })


@post("/api/rule-suggestions/apply")
def handle_apply_suggestion(ctx: RouteContext) -> None:
    """将审核通过的规则写入 custom_intent_rules 并热重载。"""
    from src.dashboard_server import _error_payload

    body = ctx.json_body()
    rule = body.get("rule")
    if not isinstance(rule, dict) or not rule.get("name") or not rule.get("keywords") or not rule.get("reply"):
        ctx.send_json(_error_payload("rule 必须包含 name, keywords, reply"), status=400)
        return

    new_rule: dict[str, Any] = {
        "name": str(rule["name"]),
        "keywords": rule["keywords"] if isinstance(rule["keywords"], list) else [str(rule["keywords"])],
        "reply": str(rule["reply"]),
        "priority": int(rule.get("priority", 100)),
    }

    cfg = _read_system_config()
    ar = cfg.setdefault("auto_reply", {})
    custom_rules: list[dict] = ar.get("custom_intent_rules", [])
    if not isinstance(custom_rules, list):
        custom_rules = []

    if any(r.get("name") == new_rule["name"] for r in custom_rules if isinstance(r, dict)):
        ctx.send_json(_error_payload(f"规则 '{new_rule['name']}' 已存在"), status=409)
        return

    custom_rules.append(new_rule)
    ar["custom_intent_rules"] = custom_rules
    _write_system_config(cfg)

    try:
        from src.core.config import get_config
        get_config().reload()
    except Exception:
        pass

    try:
        from src.modules.messages.service import _active_service
        if _active_service is not None:
            _active_service.reload_rules()
            logger.info("Hot-reloaded reply rules after applying suggestion: %s", new_rule["name"])
    except Exception as exc:
        logger.warning("Failed to hot-reload rules: %s", exc)

    ctx.send_json({
        "ok": True,
        "message": f"规则 '{new_rule['name']}' 已添加并生效",
        "rule": new_rule,
    })
