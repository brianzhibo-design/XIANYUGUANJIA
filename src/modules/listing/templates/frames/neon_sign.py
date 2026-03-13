"""荧光极客风格 — 深色背景，终端命令行风格，绿色荧光文字，网格细线。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "neon_sign",
    "name": "荧光极客风",
    "desc": "深色背景配终端风格绿色荧光文字与网格线",
    "tags": ["赛博", "秒出", "酷炫"],
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
<div style="width:1080px;height:1080px;background-color:#0f172a;padding:60px;
    display:flex;flex-direction:column;position:relative;
    background-image:
        linear-gradient(rgba(52,211,153,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(52,211,153,0.05) 1px, transparent 1px);
    background-size:30px 30px;">

    <!-- 终端命令行 -->
    <div style="font-family:monospace;font-size:30px;color:#34d399;
        margin-bottom:40px;">
        &gt; root@system:~/shipping_proxy_$ ./start.sh
    </div>

    <!-- 主标题 -->
    <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:130px;
        font-weight:900;color:#fff;
        text-shadow:0 0 20px #34d399, 0 0 40px #34d399;
        margin-bottom:20px;">
        {headline}
    </div>

    <!-- 副标题 -->
    <div style="font-size:70px;font-weight:900;color:#a7f3d0;
        text-shadow:0 0 10px #10b981;margin-bottom:60px;">
        [ {sub_headline} ]
    </div>

    <!-- 状态标签 -->
    <div style="border-left:8px solid #34d399;padding-left:30px;margin-bottom:60px;">
        <div style="font-size:40px;color:#fff;font-weight:700;letter-spacing:2px;">
            STATUS: <span style="color:#34d399;">{labels}</span>
        </div>
    </div>

    <!-- Logo 区域 -->
    <div style="flex:1;border:2px solid #34d399;
        background-color:rgba(15,23,42,0.8);padding:40px;border-radius:16px;
        box-shadow:inset 0 0 20px rgba(52,211,153,0.2);
        display:flex;align-items:center;justify-content:center;">
        {grid}
    </div>

    <!-- 底部标语 -->
    <div style="margin-top:50px;font-size:36px;color:#34d399;font-family:monospace;
        text-align:center;">
        &gt;&gt; {tagline} &lt;&lt; _
    </div>
</div>'''

    return wrap_page(body, bg="#0f172a")
