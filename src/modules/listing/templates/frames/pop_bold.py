"""3D立体漫画风格 — 白色背景，超大描边阴影文字，气泡标签，箭头分隔线。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "pop_bold",
    "name": "3D立体漫画",
    "desc": "超大描边文字配3D阴影偏移，气泡标签与箭头装饰",
    "tags": ["冲击", "年轻", "大胆"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels_raw = str(params.get("labels") or theme.get("labels", "") or "")
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="circle", size=160, gap=36, max_cols=4,
    )

    short_label = e(sub_headline[:6]) if sub_headline else ""
    labels_display = " ".join(p.strip() for p in labels_raw.split("/") if p.strip())

    body = f'''
<div style="width:1080px;height:1080px;background-color:#ffffff;
    display:flex;flex-direction:column;align-items:center;padding:80px 40px;
    position:relative;overflow:hidden;">

    <!-- 中心光晕 -->
    <div style="position:absolute;top:40%;left:50%;
        transform:translate(-50%,-50%);width:800px;height:800px;
        background:radial-gradient(circle, #fff9cc 0%, transparent 70%);
        z-index:0;"></div>

    <!-- 主标题 + 气泡标签 -->
    <div style="position:relative;z-index:1;display:flex;align-items:center;
        justify-content:center;width:100%;margin-bottom:20px;">
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:130px;
            font-weight:900;color:#ffffff;letter-spacing:4px;font-style:italic;
            -webkit-text-stroke:6px #111;
            text-shadow:10px 10px 0 #ffd166, 10px 10px 0 #111;">
            {headline}
        </div>
        <div style="position:absolute;right:40px;top:10px;background-color:#fff;
            border:5px solid #111;border-radius:16px;padding:12px 24px;
            transform:rotate(5deg);box-shadow:6px 6px 0 #ffd166;">
            <span style="font-size:36px;font-weight:900;color:#111;">
                {short_label}
            </span>
            <div style="position:absolute;bottom:-20px;left:20px;width:0;height:0;
                border-left:15px solid transparent;border-right:15px solid transparent;
                border-top:20px solid #111;"></div>
        </div>
    </div>

    <!-- 副标题 -->
    <div style="position:relative;z-index:1;margin-bottom:60px;">
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:110px;
            font-weight:900;color:#ffffff;letter-spacing:8px;font-style:italic;
            -webkit-text-stroke:6px #111;
            text-shadow:8px 8px 0 #e9edc9, 8px 8px 0 #111;">
            {sub_headline}
        </div>
    </div>

    <!-- Logo 网格 -->
    <div style="position:relative;z-index:1;width:100%;flex:1;
        display:flex;align-items:center;justify-content:center;">
        {grid}
    </div>

    <!-- 箭头分隔线 + 底部标语 -->
    <div style="position:relative;z-index:1;margin-top:40px;width:90%;">
        <div style="border-top:3px solid #111;position:relative;margin-bottom:40px;">
            <div style="position:absolute;right:-10px;top:-11px;width:0;height:0;
                border-top:10px solid transparent;border-bottom:10px solid transparent;
                border-left:20px solid #111;"></div>
        </div>
        <div style="text-align:center;font-family:'DisplayBold',system-ui,sans-serif;
            font-size:48px;font-weight:900;color:#111;letter-spacing:6px;">
            ...{labels_display} {tagline}...
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#ffffff")
