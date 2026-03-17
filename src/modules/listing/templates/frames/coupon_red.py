"""大红喜庆促销风格 — 红色渐变背景，放射线纹理，金色边框，限时特惠徽章。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "coupon_red",
    "name": "大红喜庆促销",
    "desc": "红色渐变背景配放射线，金色边框与限时特惠",
    "tags": ["促销", "双11", "急迫"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="circle", size=140, gap=24, max_cols=4,
    )

    body = f'''
<div style="width:1080px;height:1080px;
    background:linear-gradient(135deg, #ef4444, #991b1b);
    padding:40px;display:flex;flex-direction:column;align-items:center;
    position:relative;overflow:hidden;">

    <!-- 放射线纹理 -->
    <div style="position:absolute;top:-50%;left:-50%;width:200%;height:200%;
        background:repeating-conic-gradient(from 0deg,
            transparent 0deg 15deg,
            rgba(255,255,255,0.1) 15deg 30deg);"></div>

    <!-- 金色边框内容区 -->
    <div style="position:relative;z-index:1;border:8px solid #fef08a;
        width:100%;height:100%;padding:60px 40px;
        display:flex;flex-direction:column;align-items:center;">

        <!-- 限时特惠徽章 -->
        <div style="background-color:#fef08a;color:#b91c1c;padding:10px 40px;
            border-radius:50px;font-size:40px;font-weight:900;margin-bottom:40px;
            letter-spacing:4px;">
            ★ 限时特惠 ★
        </div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:140px;
            font-weight:900;color:#fef08a;letter-spacing:2px;
            text-shadow:0 10px 20px rgba(0,0,0,0.5);text-align:center;
            line-height:1.1;margin-bottom:30px;">
            {headline}
        </div>

        <!-- 副标题 -->
        <div style="font-size:70px;font-weight:900;color:#fff;
            text-shadow:0 4px 8px rgba(0,0,0,0.4);margin-bottom:50px;">
            {sub_headline}
        </div>

        <!-- 标签 -->
        <div style="background-color:#dc2626;border:4px solid #fef08a;
            padding:20px 60px;border-radius:20px;color:#fef08a;font-size:40px;
            font-weight:900;margin-bottom:60px;box-shadow:0 8px 0 #991b1b;">
            {labels}
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;background:rgba(255,255,255,0.9);width:100%;
            border-radius:30px;padding:30px;display:flex;flex-direction:column;
            align-items:center;justify-content:center;">
            {grid}
        </div>

        <!-- 底部标语 -->
        <div style="margin-top:40px;font-size:46px;font-weight:900;color:#fef08a;
            letter-spacing:8px;">
            {tagline}
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#ef4444")
