"""商品图片 HTML 模板集合 — 统一入口。

架构概览
========
三套渲染引擎共用此入口，生产环境使用前两套，第三套仅预览：

1. **品类模板** (base.py / TEMPLATES)
   - 按品类 key 渲染 750×1000 简洁卡片 (legacy)
   - 对外: get_template / list_templates / render_template

2. **框架模板** (registry.py + frames/*.py)
   - frame_id × theme 组合渲染 1080×1080 视觉图
   - 15 个 frame 注册于 frames/ 目录，通过 @register_frame 装饰器自动注册
   - 对外: render_by_frame / list_frames_metadata / list_all_templates
   - publish_queue 实际使用此引擎生成商品主图

3. **组合模板** (compositor.py + layers/)
   - layout + modifiers 自由拼装 1080×1080（仅前端预览，尚未接入发布流程）
   - 对外: render_by_composition

外部统一从此包导入即可，无需关心底层分布。
"""

from .base import TEMPLATES, get_template, list_templates, render_template
from .registry import (
    list_all_templates,
    list_frames_metadata,
    render_by_composition,
    render_by_frame,
)

__all__ = [
    "TEMPLATES",
    "get_template",
    "list_templates",
    "render_template",
    "list_all_templates",
    "list_frames_metadata",
    "render_by_frame",
    "render_by_composition",
]
