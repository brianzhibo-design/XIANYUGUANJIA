"""日系便利店风格 — 三色条幅，粗圆角边框，EXPRESS SERVICE徽章。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "convenience",
    "name": "日系便利店",
    "desc": "三色条幅开场，粗圆角边框与EXPRESS SERVICE徽章",
    "tags": ["清新", "日常", "简洁"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="circle", size=150, gap=30, max_cols=4,
    )

    body = f'''
<div style="width:1080px;height:1080px;background-color:#ffffff;
    display:flex;flex-direction:column;">

    <!-- 三色条幅 -->
    <div style="height:40px;background-color:#10b981;"></div>
    <div style="height:40px;background-color:#fff;"></div>
    <div style="height:40px;background-color:#3b82f6;"></div>

    <!-- 主内容区 -->
    <div style="padding:60px;flex:1;display:flex;flex-direction:column;
        align-items:center;background-color:#f8fafc;">

        <!-- 粗圆角边框卡片 -->
        <div style="border:8px solid #1e293b;border-radius:40px;padding:60px 40px;
            width:100%;height:100%;background-color:#fff;display:flex;
            flex-direction:column;align-items:center;position:relative;
            box-shadow:0 10px 20px rgba(0,0,0,0.05);">

            <!-- EXPRESS SERVICE 徽章 -->
            <div style="background-color:#1e293b;color:#fff;padding:10px 60px;
                border-radius:999px;font-size:36px;font-weight:900;
                position:absolute;top:-30px;letter-spacing:2px;">
                EXPRESS SERVICE
            </div>

            <!-- 主标题 -->
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:100px;
                font-weight:900;color:#1e293b;margin-top:20px;margin-bottom:10px;">
                {headline}
            </div>

            <!-- 副标题 -->
            <div style="font-size:50px;font-weight:900;color:#ef4444;
                margin-bottom:20px;">
                {sub_headline}
            </div>

            <!-- 标签条 -->
            <div style="width:100%;background-color:#f1f5f9;padding:14px;
                border-radius:20px;text-align:center;font-size:40px;font-weight:900;
                color:#334155;margin-bottom:24px;">
                {labels}
            </div>

            <!-- Logo 区域 -->
            <div style="flex:1;display:flex;align-items:center;justify-content:center;
                width:100%;min-height:0;overflow:hidden;">
                {grid}
            </div>

            <!-- 底部虚线分隔 + 标语 -->
            <div style="border-top:6px dashed #cbd5e1;padding-top:16px;margin-top:16px;
                width:100%;text-align:center;font-size:46px;font-weight:900;
                color:#1e293b;">
                {tagline}
            </div>
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#ffffff")
