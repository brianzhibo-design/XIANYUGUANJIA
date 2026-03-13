"""牛皮纸包裹风格 — 牛皮纸底色，虚线裁切框，红色橡皮章，寄件单标题。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "package_box",
    "name": "牛皮纸包裹",
    "desc": "牛皮纸底色配虚线框，红色橡皮章与寄件单标题",
    "tags": ["包裹", "复古", "快递"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="rounded_square", size=120, gap=16, max_cols=4,
    )

    body = f'''
<div style="width:1080px;height:1080px;background-color:#d4b895;padding:50px;
    position:relative;
    background-image:repeating-linear-gradient(45deg,
        rgba(0,0,0,0.02) 0px, rgba(0,0,0,0.02) 2px,
        transparent 2px, transparent 8px);">

    <!-- 白色内容区 -->
    <div style="width:100%;height:100%;background-color:#fff;padding:60px;
        display:flex;flex-direction:column;border:2px solid #a68a64;
        position:relative;box-shadow:0 10px 20px rgba(0,0,0,0.1);">

        <!-- 虚线内框 -->
        <div style="position:absolute;top:15px;left:15px;right:15px;bottom:15px;
            border:4px dashed #d4b895;pointer-events:none;"></div>

        <!-- 红色橡皮章 -->
        <div style="position:absolute;top:50px;right:50px;width:120px;height:120px;
            border:6px solid #dc2626;border-radius:50%;display:flex;align-items:center;
            justify-content:center;transform:rotate(-15deg);color:#dc2626;
            font-size:32px;font-weight:900;letter-spacing:2px;opacity:0.8;">
            特快
        </div>

        <!-- 寄件单标题 -->
        <div style="font-size:30px;font-weight:900;color:#785b37;margin-bottom:20px;
            border-bottom:4px solid #785b37;padding-bottom:10px;width:50%;">
            寄件单 SHIPPING BILL
        </div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:120px;
            font-weight:900;color:#27272a;letter-spacing:2px;margin-top:20px;">
            {headline}
        </div>

        <!-- 副标题 -->
        <div style="font-size:50px;font-weight:900;color:#dc2626;margin-bottom:40px;
            letter-spacing:2px;">
            [ {sub_headline} ]
        </div>

        <!-- 黑色标签 -->
        <div style="background-color:#27272a;color:#fff;padding:16px 30px;
            display:inline-block;font-size:36px;font-weight:900;margin-bottom:60px;
            align-self:flex-start;">
            {labels}
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;display:flex;align-items:center;justify-content:center;">
            {grid}
        </div>

        <!-- 底部备注 -->
        <div style="border-top:4px solid #785b37;padding-top:20px;margin-top:40px;
            display:flex;justify-content:space-between;font-size:36px;font-weight:900;
            color:#785b37;">
            <span>备注: {tagline}</span>
            <span style="font-family:monospace;"># 001</span>
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#d4b895")
