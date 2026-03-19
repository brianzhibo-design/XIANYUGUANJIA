"""国际航空信风格 — 红蓝斜条边框，圆形邮戳印章，PARCEL SERVICE标题。"""

from __future__ import annotations

from typing import Any

from ._common import brand_grid_html, e, wrap_page

FRAME_META = {
    "id": "airmail",
    "name": "国际航空信",
    "desc": "红蓝斜条航空信边框，圆形邮戳与经典信封风格",
    "tags": ["红蓝", "邮戳", "经典"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items,
        shape="circle",
        size=150,
        gap=30,
        max_cols=4,
    )

    body = f"""
<div style="width:1080px;height:1080px;background-color:#f8fafc;padding:40px;
    display:flex;flex-direction:column;align-items:center;">

    <!-- 红蓝条纹边框信封 -->
    <div style="width:100%;height:100%;
        border:30px solid transparent;
        border-image:repeating-linear-gradient(45deg,
            #ef4444, #ef4444 20px, transparent 20px, transparent 40px,
            #3b82f6 40px, #3b82f6 60px, transparent 60px, transparent 80px) 30;
        background-color:#fff;padding:60px;display:flex;flex-direction:column;
        position:relative;box-shadow:0 10px 30px rgba(0,0,0,0.1);">

        <!-- 邮戳 -->
        <div style="position:absolute;top:40px;right:40px;width:140px;height:140px;
            border:8px double #1e293b;border-radius:50%;display:flex;flex-direction:column;
            align-items:center;justify-content:center;transform:rotate(15deg);opacity:0.7;">
            <div style="font-size:24px;font-weight:900;color:#1e293b;">AIRMAIL</div>
            <div style="font-size:32px;font-weight:900;color:#1e293b;">速递</div>
        </div>

        <!-- PARCEL SERVICE 标题 -->
        <div style="font-size:40px;font-weight:900;color:#64748b;letter-spacing:4px;
            margin-bottom:20px;">
            PARCEL SERVICE
        </div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:130px;
            font-weight:900;color:#0f172a;margin-bottom:30px;">
            {headline}
        </div>

        <!-- 副标题 -->
        <div style="font-size:60px;font-weight:900;color:#ef4444;margin-bottom:50px;">
            {sub_headline}
        </div>

        <!-- 标签 -->
        <div style="background-color:#e2e8f0;display:inline-block;padding:16px 40px;
            border-radius:8px;font-size:40px;font-weight:900;color:#334155;
            align-self:flex-start;margin-bottom:60px;">
            {labels}
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;display:flex;align-items:center;justify-content:center;">
            {grid}
        </div>

        <!-- 底部标语 -->
        <div style="border-top:4px solid #cbd5e1;padding-top:30px;margin-top:40px;
            font-size:46px;font-weight:900;color:#0f172a;text-align:center;">
            ✈ {tagline}
        </div>
    </div>
</div>"""

    return wrap_page(body, bg="#f8fafc")
