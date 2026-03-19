"""撕纸拼接风格 — 深蓝色背景，倾斜白纸，黄色胶带装饰，圆角标签。"""

from __future__ import annotations

from typing import Any

from ._common import brand_grid_html, e, wrap_page

FRAME_META = {
    "id": "torn_paper",
    "name": "撕纸拼接",
    "desc": "深蓝背景配倾斜白纸拼贴，黄色胶带装饰",
    "tags": ["折扣", "潮流", "个性"],
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
        size=130,
        gap=24,
        max_cols=4,
    )

    body = f"""
<div style="width:1080px;height:1080px;background-color:#3b5bdb;position:relative;
    display:flex;align-items:center;justify-content:center;overflow:hidden;">

    <!-- 倾斜白纸 -->
    <div style="width:120%;height:70%;background-color:#fff;transform:rotate(-3deg);
        display:flex;flex-direction:column;align-items:center;padding:60px 100px;
        box-shadow:0 20px 40px rgba(0,0,0,0.2);">

        <!-- 右上胶带 -->
        <div style="position:absolute;top:-20px;right:150px;width:120px;height:40px;
            background-color:#fcc419;transform:rotate(15deg);opacity:0.9;
            box-shadow:1px 1px 4px rgba(0,0,0,0.2);"></div>

        <!-- 左下胶带 -->
        <div style="position:absolute;bottom:-20px;left:150px;width:120px;height:40px;
            background-color:#fcc419;transform:rotate(5deg);opacity:0.9;
            box-shadow:1px 1px 4px rgba(0,0,0,0.2);"></div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:130px;
            font-weight:900;color:#111;-webkit-text-stroke:3px #111;
            text-shadow:6px 6px 0 #ffd43b;margin-bottom:20px;
            transform:rotate(3deg);">
            {headline}
        </div>

        <!-- 标签胶囊 -->
        <div style="background-color:#f8f9fa;padding:10px 40px;border-radius:50px;
            border:4px solid #111;margin-bottom:40px;transform:rotate(3deg);">
            <span style="font-size:40px;font-weight:900;color:#3b5bdb;">
                {labels}
            </span>
        </div>

        <!-- Logo 网格 -->
        <div style="transform:rotate(3deg);width:100%;display:flex;
            justify-content:center;">
            {grid}
        </div>

        <!-- 底部标语 -->
        <div style="transform:rotate(3deg);margin-top:40px;font-size:40px;
            font-weight:900;color:#111;letter-spacing:4px;">
            ··· {tagline} ···
        </div>
    </div>

    <!-- 左上水印副标题 -->
    <div style="position:absolute;top:40px;left:40px;font-size:70px;font-weight:900;
        color:#fff;opacity:0.2;">
        {sub_headline}
    </div>

    <!-- 右下水印副标题 -->
    <div style="position:absolute;bottom:40px;right:40px;font-size:70px;font-weight:900;
        color:#fff;opacity:0.2;">
        {sub_headline}
    </div>
</div>"""

    return wrap_page(body, bg="#3b5bdb")
