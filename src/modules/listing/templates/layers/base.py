"""图层基础类型和注册表。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayoutOutput:
    """Layout 主模版输出 — 包含完整 HTML body。"""

    body_html: str
    required_css: str = ""


@dataclass
class ModifierOutput:
    """修饰器输出 — CSS 变量、额外 CSS 规则、浮动装饰 HTML。"""

    css_vars: dict[str, str] = field(default_factory=dict)
    css_rules: str = ""
    overlay_html: str = ""


LayoutFn = Callable[[dict[str, Any], dict[str, Any]], LayoutOutput]
ModifierFn = Callable[[dict[str, Any], dict[str, Any]], ModifierOutput]

LAYOUT_REGISTRY: dict[str, dict[str, Any]] = {}

MODIFIER_REGISTRY: dict[str, dict[str, dict[str, Any]]] = {
    "color_scheme": {},
    "decoration": {},
    "title_style": {},
}


def register_layout(layout_id: str, *, name: str, desc: str = ""):
    """装饰器：注册一个 Layout 主模版。"""

    def decorator(fn: LayoutFn) -> LayoutFn:
        LAYOUT_REGISTRY[layout_id] = {
            "id": layout_id,
            "name": name,
            "desc": desc,
            "render": fn,
        }
        return fn

    return decorator


def register_modifier(kind: str, modifier_id: str, *, name: str, desc: str = ""):
    """装饰器：注册一个修饰器（color_scheme / decoration / title_style）。"""

    def decorator(fn: ModifierFn) -> ModifierFn:
        if kind not in MODIFIER_REGISTRY:
            raise ValueError(f"Unknown modifier kind: {kind}")
        MODIFIER_REGISTRY[kind][modifier_id] = {
            "id": modifier_id,
            "name": name,
            "desc": desc,
            "render": fn,
        }
        return fn

    return decorator


def list_layouts() -> list[dict[str, str]]:
    return [{"id": v["id"], "name": v["name"], "desc": v["desc"]} for v in LAYOUT_REGISTRY.values()]


def list_modifiers(kind: str | None = None) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for k, entries in MODIFIER_REGISTRY.items():
        if kind and k != kind:
            continue
        result[k] = [{"id": v["id"], "name": v["name"], "desc": v["desc"]} for v in entries.values()]
    return result


def get_layout(layout_id: str) -> dict[str, Any] | None:
    return LAYOUT_REGISTRY.get(layout_id)


def get_modifier(kind: str, modifier_id: str) -> dict[str, Any] | None:
    return MODIFIER_REGISTRY.get(kind, {}).get(modifier_id)
