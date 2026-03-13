"""螺旋笔记本风格 — 浅蓝背景，白色笔记本，左侧线圈，右上回形针，横线纹理。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "spiral_notebook",
    "name": "螺旋笔记本",
    "desc": "左侧螺旋线圈，横线纸纹理，回形针装饰",
    "tags": ["记账", "文艺", "清新"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])
    primary = theme.get("primary", "#4b75c4")

    grid = brand_grid_html(
        brand_items, shape="circle", size=140, gap=20, max_cols=4,
    )

    spirals = ""
    for i in range(16):
        top = 40 + i * 60
        spirals += (
            f'<div style="position:absolute;left:-20px;top:{top}px;'
            'width:40px;height:12px;background-color:#a0aec0;border-radius:6px;'
            'box-shadow:inset 0 3px 6px rgba(0,0,0,0.3);z-index:5;">'
            '<div style="position:absolute;right:-10px;top:-4px;width:20px;height:20px;'
            'background-color:#dce5f5;border-radius:50%;'
            'border-left:1px solid #b0c4de;"></div></div>\n'
        )

    tagline_parts = tagline.split(" ")
    tagline_display = " | ".join(tagline_parts) if len(tagline_parts) > 1 else tagline

    body = f'''
<div style="width:1080px;height:1080px;background-color:#dce5f5;
    display:flex;padding:40px;position:relative;">

    <!-- 笔记本主体 -->
    <div style="flex:1;background-color:#ffffff;border-radius:16px;
        border:2px solid #b0c4de;position:relative;margin-left:30px;
        padding:60px 40px;display:flex;flex-direction:column;align-items:center;
        background-image:
            linear-gradient(rgba(176,196,222,0.4) 2px, transparent 2px),
            linear-gradient(90deg, rgba(176,196,222,0.4) 2px, transparent 2px);
        background-size:40px 40px;">

        <!-- 左侧线圈 -->
        {spirals}

        <!-- 右上回形针 -->
        <div style="position:absolute;top:20px;right:30px;width:30px;height:80px;
            border:6px solid #ccc;border-radius:15px;transform:rotate(20deg);
            border-bottom-width:0;box-shadow:4px 4px 5px rgba(0,0,0,0.1);">
            <div style="position:absolute;top:10px;left:4px;width:10px;height:50px;
                border:6px solid #ccc;border-radius:5px;border-top-width:0;"></div>
        </div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:110px;
            font-weight:900;color:{primary};letter-spacing:2px;
            -webkit-text-stroke:8px #ffffff;
            text-shadow:4px 4px 10px rgba(0,0,0,0.1);
            margin-bottom:20px;z-index:1;">
            {headline}
        </div>

        <!-- 标签 + 粉色高亮 -->
        <div style="position:relative;margin-bottom:50px;z-index:1;">
            <div style="position:absolute;top:40%;left:-5%;right:-5%;bottom:10%;
                background-color:#ffe4e6;z-index:-1;"></div>
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:50px;
                font-weight:900;color:{primary};letter-spacing:4px;">
                ✓ {labels}
            </div>
        </div>

        <!-- Logo 区域 -->
        <div style="width:95%;border:4px solid #6ea8f0;background-color:transparent;
            padding:50px 20px 30px;position:relative;display:flex;justify-content:center;
            margin-bottom:auto;margin-top:20px;">
            <div style="position:absolute;top:-35px;background-color:#fff;padding:0 30px;
                color:#6ea8f0;font-size:48px;font-weight:900;">
                {sub_headline}
            </div>
            {grid}
        </div>

        <!-- 底部标语 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:42px;
            font-weight:900;color:#2d3748;letter-spacing:4px;margin-top:40px;">
            {tagline_display}
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#dce5f5")
