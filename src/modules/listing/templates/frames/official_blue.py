"""官方正规蓝风格 — 浅蓝背景，白色圆角卡片，蓝色信息栏，虚线框Logo区。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "official_blue",
    "name": "官方正规蓝",
    "desc": "浅蓝背景白卡片，蓝色信息栏与虚线框Logo区",
    "tags": ["严肃", "正规", "信任"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="circle", size=120, gap=16, max_cols=4,
    )

    body = f'''
<div style="width:1080px;height:1080px;background-color:#93c5fd;padding:40px;
    display:flex;flex-direction:column;align-items:center;position:relative;">

    <!-- 白色圆角卡片 -->
    <div style="width:100%;height:100%;background-color:#f8fafc;border-radius:30px;
        padding:60px 40px;display:flex;flex-direction:column;align-items:center;
        box-shadow:0 10px 30px rgba(0,0,0,0.1);position:relative;">

        <!-- 顶部装饰条 -->
        <div style="position:absolute;top:20px;width:120px;height:20px;
            background-color:#e2e8f0;border-radius:10px;"></div>

        <!-- 蓝色信息栏 -->
        <div style="background-color:#60a5fa;width:100%;border-radius:20px;
            padding:40px 20px;text-align:center;margin-bottom:30px;
            box-shadow:0 8px 0 #3b82f6;">
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:110px;
                font-weight:900;color:#fff;-webkit-text-stroke:4px #1e3a8a;
                text-shadow:4px 4px 0 #1e3a8a;line-height:1;">
                {headline}
            </div>
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:80px;
                font-weight:900;color:#fef08a;-webkit-text-stroke:3px #1e3a8a;
                text-shadow:4px 4px 0 #1e3a8a;margin-top:20px;">
                {sub_headline}
            </div>
        </div>

        <!-- 标签胶囊 -->
        <div style="background-color:#bfdbfe;padding:12px 40px;border-radius:999px;
            margin-bottom:40px;">
            <span style="font-size:36px;font-weight:900;color:#1e3a8a;">
                ✨ {labels}
            </span>
        </div>

        <!-- Logo 虚线框区域 -->
        <div style="width:100%;flex:1;border:4px dashed #93c5fd;border-radius:20px;
            display:flex;flex-direction:column;align-items:center;padding:30px;
            position:relative;">
            <div style="position:absolute;top:-25px;background-color:#f8fafc;padding:0 20px;
                font-size:40px;font-weight:900;color:#60a5fa;">
                {sub_headline}
            </div>
            <div style="flex:1;display:flex;align-items:center;">
                {grid}
            </div>
        </div>

        <!-- 底部标语 -->
        <div style="margin-top:30px;font-size:44px;font-weight:900;color:#60a5fa;
            letter-spacing:6px;">
            {tagline} &gt;&gt;&gt;
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#93c5fd")
