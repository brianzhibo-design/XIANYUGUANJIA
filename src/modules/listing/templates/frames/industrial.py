"""工业硬核风格 — 黄黑斜纹警示带，钢板灰背景，铆钉四角，CAUTION标语。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "industrial",
    "name": "工业硬核风",
    "desc": "黄黑斜纹警示带背景，钢板灰内框与铆钉四角",
    "tags": ["大件", "物流", "硬核"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels_raw = str(params.get("labels") or theme.get("labels", "") or "")
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="rounded_square", size=140, gap=24, max_cols=4,
    )

    labels_display = " // ".join(p.strip() for p in labels_raw.split("/") if p.strip())

    rivet = (
        '<div style="width:24px;height:24px;border-radius:50%;'
        'background-color:#9ca3af;border:4px solid #4b5563;"></div>'
    )

    body = f'''
<div style="width:1080px;height:1080px;background-color:#1f2937;padding:40px;
    display:flex;flex-direction:column;
    background-image:repeating-linear-gradient(-45deg,
        #facc15, #facc15 30px, #111 30px, #111 60px);">

    <!-- 钢板灰内框 -->
    <div style="width:100%;height:100%;background-color:#e5e7eb;border:12px solid #111;
        padding:60px;display:flex;flex-direction:column;position:relative;">

        <!-- 四角铆钉 -->
        <div style="position:absolute;top:20px;left:20px;">{rivet}</div>
        <div style="position:absolute;top:20px;right:20px;">{rivet}</div>
        <div style="position:absolute;bottom:20px;left:20px;">{rivet}</div>
        <div style="position:absolute;bottom:20px;right:20px;">{rivet}</div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:140px;
            font-weight:900;color:#111;text-transform:uppercase;margin-bottom:20px;
            line-height:1;">
            {headline}
        </div>

        <!-- 副标题黑底黄字 -->
        <div style="background-color:#111;color:#facc15;display:inline-block;
            padding:10px 40px;font-size:60px;font-weight:900;align-self:flex-start;
            margin-bottom:50px;">
            {sub_headline}
        </div>

        <!-- 标签 + 黄色左边线 -->
        <div style="font-size:40px;font-weight:900;color:#374151;
            border-left:12px solid #facc15;padding-left:30px;margin-bottom:60px;">
            {labels_display}
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;background-color:#fff;border:6px solid #111;padding:40px;
            display:flex;align-items:center;justify-content:center;">
            {grid}
        </div>

        <!-- CAUTION 标语 -->
        <div style="margin-top:50px;font-size:46px;font-weight:900;color:#111;
            letter-spacing:4px;">
            CAUTION: {tagline}
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#1f2937")
