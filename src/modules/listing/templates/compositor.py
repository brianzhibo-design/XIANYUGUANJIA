"""组合式模版引擎。

将 1 个 Layout 主模版 + 3 个修饰器（ColorScheme / Decoration / TitleStyle）合并为完整 HTML。
"""

from __future__ import annotations

import random
from typing import Any

from .frames._common import _font_face_css
from .layers.base import (
    LAYOUT_REGISTRY,
    MODIFIER_REGISTRY,
    LayoutOutput,
    ModifierOutput,
    get_layout,
    get_modifier,
)


def compose(
    *,
    layout: str | None = None,
    color_scheme: str | None = None,
    decoration: str | None = None,
    title_style: str | None = None,
    params: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    """组合渲染，返回 (html, used_layers)。

    各参数为 None 时随机选择。
    """
    from .layers import (  # noqa: ensure registration
        LAYOUT_REGISTRY as _lr,
        MODIFIER_REGISTRY as _mr,
    )

    params = params or {}
    theme = theme or {}

    color_scheme_keys = list(MODIFIER_REGISTRY["color_scheme"].keys())
    decoration_keys = list(MODIFIER_REGISTRY["decoration"].keys())
    title_style_keys = list(MODIFIER_REGISTRY["title_style"].keys())

    chosen = {
        "layout": layout or random.choice(list(LAYOUT_REGISTRY.keys())),
        "color_scheme": color_scheme or random.choice(color_scheme_keys),
        "decoration": decoration or random.choice(decoration_keys),
        "title_style": title_style or random.choice(title_style_keys),
    }

    layout_entry = get_layout(chosen["layout"])
    if layout_entry is None:
        layout_entry = get_layout("hero_center")
        chosen["layout"] = "hero_center"

    layout_out: LayoutOutput = layout_entry["render"](params, theme)

    modifiers: list[ModifierOutput] = []
    for kind in ("color_scheme", "decoration", "title_style"):
        mod_id = chosen[kind]
        mod_entry = get_modifier(kind, mod_id)
        if mod_entry is None and mod_id:
            mod_id = random.choice(
                color_scheme_keys if kind == "color_scheme"
                else decoration_keys if kind == "decoration"
                else title_style_keys
            )
            chosen[kind] = mod_id
            mod_entry = get_modifier(kind, mod_id)
        if mod_entry is None:
            continue
        modifiers.append(mod_entry["render"](params, theme))

    merged_vars: dict[str, str] = {}
    merged_css_parts: list[str] = []
    merged_overlay: list[str] = []

    for mod in modifiers:
        merged_vars.update(mod.css_vars)
        if mod.css_rules:
            merged_css_parts.append(mod.css_rules)
        if mod.overlay_html:
            merged_overlay.append(mod.overlay_html)

    if layout_out.required_css:
        merged_css_parts.append(layout_out.required_css)

    if not merged_vars or "--bg-primary" not in merged_vars:
        mod_entry = get_modifier("color_scheme", "red_gold")
        if mod_entry:
            merged_vars.update(mod_entry["render"](params, theme).css_vars)

    vars_css = ""
    if merged_vars:
        pairs = "\n".join(f"    {k}: {v};" for k, v in merged_vars.items())
        vars_css = f":root {{\n{pairs}\n}}"

    font_face = _font_face_css()
    extra_css = "\n".join(merged_css_parts)
    overlay_html = "\n".join(merged_overlay)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
{font_face}
{vars_css}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: 1080px; height: 1080px; overflow: hidden;
    font-family: 'DisplayBold', -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif;
    background: var(--bg-primary, #ffffff);
}}
.title-text {{
    font-size: 96px;
    font-weight: 900;
    line-height: 1.2;
    color: var(--text-accent, #dc2626);
}}
{extra_css}
</style>
</head>
<body>
{layout_out.body_html}
{overlay_html}
</body>
</html>'''

    return html, chosen


def list_all_options() -> dict[str, list[dict[str, str]]]:
    """返回所有可用的图层选项，供前端下拉列表使用。"""
    from .layers.base import list_layouts, list_modifiers

    result = {"layout": list_layouts()}
    result.update(list_modifiers())
    return result
