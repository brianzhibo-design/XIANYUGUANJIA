"""小票收据风格 — 窄纸居中，锯齿边缘，等宽字体，条形码装饰。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "receipt",
    "name": "极简黑白票据",
    "desc": "热敏纸小票风格，锯齿边，等宽文字，条形码装饰",
    "tags": ["极简", "低价", "趣味"],
}


def _barcode_html(width: int = 400, height: int = 100) -> str:
    bars = ""
    pattern = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 3, 1, 2, 1, 1, 3, 2, 1, 1, 2, 3, 1, 1, 2, 1, 3, 1]
    x = 0
    for i, w in enumerate(pattern):
        if i % 2 == 0:
            bars += (
                f'<div style="position:absolute;left:{x}px;top:0;width:{w * 3}px;height:100%;'
                f'background:#111;"></div>'
            )
        x += w * 3
    return (
        f'<div style="position:relative;width:{width}px;height:{height}px;'
        f'margin:0 auto;overflow:hidden;">{bars}</div>'
    )


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = e(params.get("labels") or theme.get("labels", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items, shape="rounded_square", size=130, gap=20, max_cols=4,
    )

    barcode = _barcode_html(500, 100)

    body = f'''
<div style="width:1080px;height:1080px;background-color:#e2e8f0;
    display:flex;align-items:center;justify-content:center;padding:40px;">

    <!-- 小票主体 -->
    <div style="width:80%;height:100%;background-color:#fff;display:flex;
        flex-direction:column;align-items:center;padding:60px 40px;
        position:relative;
        background-image:radial-gradient(circle at 15px 0, transparent 16px, #fff 17px);
        background-size:30px 20px;background-position:top left;
        background-repeat:repeat-x;">

        <!-- 底部锯齿 -->
        <div style="position:absolute;bottom:0;left:0;right:0;height:20px;
            background-image:radial-gradient(circle at 15px 20px, transparent 16px, #fff 17px);
            background-size:30px 20px;background-repeat:repeat-x;
            transform:rotate(180deg);"></div>

        <!-- 店铺标题 -->
        <div style="font-family:monospace;font-size:40px;font-weight:900;color:#111;
            margin-bottom:40px;">
            *** 物流收据 ***
        </div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:110px;
            font-weight:900;color:#111;text-align:center;line-height:1.1;
            margin-bottom:20px;">
            {headline}
        </div>

        <!-- 副标题 + 虚线分隔 -->
        <div style="font-size:50px;font-weight:900;color:#555;
            border-bottom:4px dashed #ccc;padding-bottom:30px;margin-bottom:30px;
            width:100%;text-align:center;">
            {sub_headline}
        </div>

        <!-- 信息行 -->
        <div style="width:100%;text-align:left;font-size:36px;font-weight:700;
            color:#333;margin-bottom:40px;font-family:monospace;">
            <div>&gt; 类型: {labels}</div>
            <div>&gt; 状态: {tagline}</div>
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;display:flex;align-items:center;justify-content:center;
            width:100%;">
            {grid}
        </div>

        <!-- 条形码 -->
        <div style="margin-top:40px;">
            {barcode}
            <div style="margin-top:10px;font-size:24px;color:#aaa;text-align:center;
                font-family:monospace;letter-spacing:3px;">
                192837465019283
            </div>
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#e2e8f0")
