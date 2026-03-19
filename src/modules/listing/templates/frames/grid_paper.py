"""记号笔网格风格 — 网格纸背景，高亮标记标题，四角装饰方框容器。"""

from __future__ import annotations

from typing import Any

from ._common import brand_grid_html, e, wrap_page

FRAME_META = {
    "id": "grid_paper",
    "name": "记号笔网格",
    "desc": "网格纸背景，高亮标记标题，方框容器与四角装饰",
    "tags": ["爆款", "醒目", "简约"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items,
        shape="rounded_square",
        size=160,
        gap=24,
        max_cols=4,
    )

    body = f"""
<div style="width:1080px;height:1080px;background-color:#f9f9f9;padding:40px;
    position:relative;
    background-image:
        linear-gradient(#e5e7eb 2px, transparent 2px),
        linear-gradient(90deg, #e5e7eb 2px, transparent 2px);
    background-size:40px 40px;">

    <!-- 外框 -->
    <div style="position:absolute;top:40px;left:40px;right:40px;bottom:40px;
        border:3px solid #333;z-index:1;"></div>

    <div style="position:relative;z-index:2;display:flex;flex-direction:column;
        align-items:center;height:100%;padding-top:60px;">

        <!-- 顶部虚线 -->
        <div style="border-top:12px dashed #333;width:60%;margin-bottom:40px;"></div>

        <!-- 主标题 + 蓝色高亮背景 -->
        <div style="position:relative;margin-bottom:40px;">
            <div style="position:absolute;top:15%;left:-5%;right:-5%;bottom:10%;
                background-color:#b3e0ff;z-index:-1;"></div>
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:110px;
                font-weight:900;color:#111;letter-spacing:4px;">
                {headline}
            </div>
        </div>

        <!-- 副标题 + 绿色高亮背景 -->
        <div style="position:relative;margin-bottom:60px;">
            <div style="position:absolute;top:15%;left:-5%;right:-5%;bottom:10%;
                background-color:#cce6cc;z-index:-1;"></div>
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:80px;
                font-weight:900;color:#111;letter-spacing:4px;">
                {sub_headline}
            </div>
        </div>

        <!-- Logo 网格容器 + 四角装饰 -->
        <div style="width:90%;border:4px solid #333;background-color:#fff;
            padding:40px 30px;position:relative;display:flex;flex-direction:column;
            align-items:center;margin-bottom:auto;">
            <div style="position:absolute;top:-8px;left:-8px;width:16px;height:16px;
                border:3px solid #333;background:#fff;"></div>
            <div style="position:absolute;top:-8px;right:-8px;width:16px;height:16px;
                border:3px solid #333;background:#fff;"></div>
            <div style="position:absolute;bottom:-8px;left:-8px;width:16px;height:16px;
                border:3px solid #333;background:#fff;"></div>
            <div style="position:absolute;bottom:-8px;right:-8px;width:16px;height:16px;
                border:3px solid #333;background:#fff;"></div>
            {grid}
        </div>

        <!-- 底部标语 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:48px;
            font-weight:900;color:#111;margin-bottom:60px;letter-spacing:4px;">
            —— {tagline} ——
        </div>
    </div>
</div>"""

    return wrap_page(body, bg="#f9f9f9")
