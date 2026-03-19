"""新模板注册表 — 管理 Frame + Theme 组合，及组合式模版引擎。

对外提供与旧系统兼容的接口，同时支持新的 frame_id 选择方式和 composition 组合模式。
"""

from __future__ import annotations

from typing import Any

from .frames import list_frames, render_frame
from .themes import THEMES, get_theme


def list_all_templates() -> list[dict[str, Any]]:
    """返回所有可用模板（frame x theme 组合）。"""
    frames = list_frames()
    result = []
    for frame in frames:
        for cat_key in THEMES:
            result.append(
                {
                    "key": f"{frame['id']}:{cat_key}",
                    "frame_id": frame["id"],
                    "frame_name": frame["name"],
                    "category": cat_key,
                    "name": f"{frame['name']} · {THEMES[cat_key]['badge']}",
                    "desc": frame.get("desc", ""),
                    "tags": frame.get("tags", []),
                }
            )
    return result


def list_frames_metadata() -> list[dict[str, Any]]:
    """返回框架列表（不含品类展开）。"""
    return list_frames()


def render_by_frame(
    frame_id: str,
    category: str = "express",
    params: dict[str, Any] | None = None,
) -> str | None:
    """用指定框架 + 品类渲染 HTML（向后兼容）。"""
    theme = get_theme(category)
    return render_frame(frame_id, params or {}, theme)


def render_by_composition(
    category: str = "express",
    params: dict[str, Any] | None = None,
    layers: dict[str, str] | None = None,
) -> tuple[str | None, dict[str, str]]:
    """组合式渲染，返回 (html, used_layers)。

    layers 字典可包含 layout / color_scheme / decoration / title_style，
    缺省项随机选择。
    """
    from .compositor import compose

    theme = get_theme(category)
    layers = layers or {}

    def _val(k: str) -> str | None:
        v = layers.get(k)
        return v if v else None

    try:
        html, used = compose(
            layout=_val("layout"),
            color_scheme=_val("color_scheme"),
            decoration=_val("decoration"),
            title_style=_val("title_style"),
            params=params or {},
            theme=theme,
        )
        return html, used
    except Exception:
        return None, {}
