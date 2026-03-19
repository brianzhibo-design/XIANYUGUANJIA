"""L2 智能学习：从 unmatched_messages.jsonl 中聚类分析，生成规则建议。"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from src.core.config import get_config

logger = logging.getLogger(__name__)

UNMATCHED_PATH = Path("data/unmatched_messages.jsonl")
SYSTEM_CONFIG_PATH = Path("data/system_config.json")
SUGGESTIONS_KEY = "rule_suggestions"


class RuleSuggester:
    def __init__(self) -> None:
        self.config = get_config()

    def load_unmatched_messages(self, limit: int = 200) -> list[dict]:
        if not UNMATCHED_PATH.exists():
            return []
        messages: list[dict] = []
        try:
            with open(UNMATCHED_PATH, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                    if len(messages) >= limit:
                        break
        except Exception as exc:
            logger.warning("Failed to load unmatched messages: %s", exc)
        return messages

    def _simple_cluster(self, messages: list[dict]) -> list[list[dict]]:
        """按关键词粗聚类，每类限制 5 条。"""
        clusters: dict[str, list[dict]] = {}
        for msg in messages:
            text = str(msg.get("message_text", "") or msg.get("text", ""))[:60]
            key = text.split()[0] if text.split() else text[:3]
            clusters.setdefault(key, []).append(msg)
        return [v[:5] for v in clusters.values() if v]

    def _generate_rules_for_cluster(self, cluster: list[dict]) -> list[dict]:
        """对同类消息调用 LLM 生成规则。"""
        from src.modules.content.service import ContentService

        texts = [str(m.get("message_text", "") or m.get("text", ""))[:100] for m in cluster]
        prompt = (
            "你是一个快递客服规则引擎专家。以下是用户发送的几条未被识别的消息：\n"
            + "\n".join(f"- {t}" for t in texts)
            + "\n\n请分析这些消息的共同意图，生成 1-2 条意图识别规则。每条规则包含："
            "name（英文标识）、keywords（中文关键词列表，2-5个）、reply（客服回复文本，30字以内）、"
            "priority（优先级，数字越小越高，取 15-25）、categories（空数组）、phase（填空字符串）。"
            "只输出 JSON 数组，不要解释。"
        )
        svc = ContentService()
        if not svc or not svc.client:
            return []
        try:
            response = svc._call_ai(prompt, task="rule_suggest")
            import re

            match = re.search(r"\[[\s\S]*\]", response)
            if match:
                rules = json.loads(match.group())
                return rules if isinstance(rules, list) else []
        except Exception as exc:
            logger.debug("Rule generation failed: %s", exc)
        return []

    def analyze_and_suggest(self, min_messages: int = 5) -> list[dict]:
        messages = self.load_unmatched_messages()
        if len(messages) < min_messages:
            logger.info("Not enough unmatched messages: %d < %d", len(messages), min_messages)
            return []
        clusters = self._simple_cluster(messages)
        all_suggestions: list[dict] = []
        for cluster in clusters:
            rules = self._generate_rules_for_cluster(cluster)
            for rule in rules:
                rule["_source_cluster_size"] = len(cluster)
                rule["_created_at"] = time.time()
                all_suggestions.append(rule)
        self.save_suggestions(all_suggestions)
        logger.info("Generated %d rule suggestions from %d clusters", len(all_suggestions), len(clusters))
        return all_suggestions

    def get_suggestions(self) -> list[dict]:
        try:
            if not SYSTEM_CONFIG_PATH.exists():
                return []
            with open(SYSTEM_CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            suggestions = data.get(SUGGESTIONS_KEY, [])
            return suggestions if isinstance(suggestions, list) else []
        except Exception as exc:
            logger.warning("Failed to load suggestions: %s", exc)
            return []

    def save_suggestions(self, suggestions: list[dict]) -> None:
        try:
            SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            data: dict = {}
            if SYSTEM_CONFIG_PATH.exists():
                with open(SYSTEM_CONFIG_PATH, encoding="utf-8") as f:
                    data = json.load(f)
            data[SUGGESTIONS_KEY] = suggestions
            with open(SYSTEM_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Failed to save suggestions: %s", exc)

    def _load_system_config(self) -> dict:
        try:
            if SYSTEM_CONFIG_PATH.exists():
                with open(SYSTEM_CONFIG_PATH, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _write_system_config(self, data: dict) -> None:
        try:
            SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SYSTEM_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Failed to write system config: %s", exc)

    def adopt_suggestion(self, name: str) -> bool:
        suggestions = self.get_suggestions()
        target = None
        for s in suggestions:
            if str(s.get("name", "")) == name:
                target = s
                break
        if not target:
            return False
        from src.dashboard.config_service import read_system_config, write_system_config

        cfg = read_system_config()
        ar = cfg.setdefault("auto_reply", {})
        rules = ar.setdefault("custom_intent_rules", [])
        if not isinstance(rules, list):
            rules = []
        clean_rule = {k: v for k, v in target.items() if not k.startswith("_")}
        rules = [r for r in rules if r.get("name") != name]
        rules.append(clean_rule)
        ar["custom_intent_rules"] = rules
        write_system_config(cfg)
        get_config().reload()
        self.save_suggestions([s for s in suggestions if s.get("name") != name])
        try:
            from src.modules.messages.service import _active_service

            if _active_service is not None:
                _active_service.reload_rules()
        except Exception as exc:
            logger.warning("Failed to hot-reload rules: %s", exc)
        return True

    def reject_suggestion(self, name: str) -> bool:
        suggestions = self.get_suggestions()
        self.save_suggestions([s for s in suggestions if s.get("name") != name])
        return True
