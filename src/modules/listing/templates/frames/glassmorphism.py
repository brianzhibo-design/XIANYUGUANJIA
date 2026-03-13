"""现代毛玻璃风格 — 紫粉渐变背景，模糊光斑，半透明圆角卡片。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "glassmorphism",
    "name": "现代毛玻璃",
    "desc": "紫粉渐变背景配模糊光斑，半透明毛玻璃卡片",
    "tags": ["高级", "极简", "现代"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="rounded_square", size=110, gap=14, max_cols=4,
    )

    body = f'''
<div style="width:1080px;height:1080px;
    background:linear-gradient(45deg, #a855f7, #ec4899, #f43f5e);
    padding:60px;display:flex;align-items:center;justify-content:center;
    position:relative;overflow:hidden;">

    <!-- 模糊光斑 -->
    <div style="position:absolute;top:10%;left:10%;width:400px;height:400px;
        background-color:#fbbf24;border-radius:50%;filter:blur(80px);"></div>
    <div style="position:absolute;bottom:10%;right:10%;width:500px;height:500px;
        background-color:#3b82f6;border-radius:50%;filter:blur(100px);"></div>

    <!-- 毛玻璃卡片 -->
    <div style="width:100%;height:100%;
        background:rgba(255,255,255,0.25);
        -webkit-backdrop-filter:blur(20px);
        backdrop-filter:blur(20px);
        border-radius:40px;border:2px solid rgba(255,255,255,0.5);
        padding:60px 60px;display:flex;flex-direction:column;align-items:center;
        box-shadow:0 20px 40px rgba(0,0,0,0.1);">

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:100px;
            font-weight:900;color:#fff;text-shadow:0 4px 10px rgba(0,0,0,0.1);
            margin-bottom:16px;text-align:center;">
            {headline}
        </div>

        <!-- 副标题 -->
        <div style="font-size:50px;font-weight:900;color:#fff;opacity:0.9;
            margin-bottom:24px;">
            {sub_headline}
        </div>

        <!-- 标签胶囊 -->
        <div style="background:rgba(255,255,255,0.3);padding:16px 60px;
            border-radius:999px;font-size:40px;font-weight:700;color:#fff;
            margin-bottom:30px;border:1px solid rgba(255,255,255,0.4);">
            {labels}
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;width:100%;background:rgba(255,255,255,0.4);
            border-radius:30px;padding:20px;display:flex;align-items:center;
            justify-content:center;min-height:0;overflow:hidden;">
            {grid}
        </div>

        <!-- 底部标语 -->
        <div style="margin-top:24px;font-size:44px;font-weight:700;color:#fff;
            opacity:0.9;letter-spacing:4px;">
            {tagline}
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#a855f7")
