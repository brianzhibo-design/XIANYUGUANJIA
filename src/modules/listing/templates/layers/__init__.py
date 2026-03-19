"""组合式模版图层系统。

提供 1 主模版（Layout） + 3 修饰器（ColorScheme / Decoration / TitleStyle）的注册与查询。
"""

from __future__ import annotations

from .base import (
    LAYOUT_REGISTRY,
    MODIFIER_REGISTRY,
    LayoutOutput,
    ModifierOutput,
    get_layout,
    get_modifier,
    list_layouts,
    list_modifiers,
)

__all__ = [
    "LAYOUT_REGISTRY",
    "MODIFIER_REGISTRY",
    "LayoutOutput",
    "ModifierOutput",
    "get_layout",
    "get_modifier",
    "list_layouts",
    "list_modifiers",
]

from . import color_schemes as _cs  # noqa: F401
from . import decorations as _deco  # noqa: F401
from . import layouts as _layouts  # noqa: F401  trigger registration
from . import title_styles as _ts  # noqa: F401
