"""活页板夹风格 — 浅绿格子底纹，白色圆角夹板，金属夹子+粉色标签胶囊，粗体分区框。"""

from __future__ import annotations
from typing import Any
from ._common import e, brand_grid_html, wrap_page

FRAME_META = {
    "id": "clipboard",
    "name": "活页板夹",
    "desc": "浅绿格子背景，金属夹子，粉色标签胶囊与粗体分区",
    "tags": ["信任", "手工", "温暖"],
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
<div style="width:1080px;height:1080px;background-color:#e9f5ed;padding:80px 60px;
    position:relative;
    background-image:
        linear-gradient(rgba(255,255,255,0.6) 4px, transparent 4px),
        linear-gradient(90deg, rgba(255,255,255,0.6) 4px, transparent 4px);
    background-size:40px 40px;">

    <!-- 白色夹板主体 -->
    <div style="width:100%;height:100%;background-color:#fff;border-radius:32px;
        border:16px solid #8ab6a6;position:relative;display:flex;flex-direction:column;
        align-items:center;padding:100px 40px 40px;
        box-shadow:0 20px 40px rgba(0,0,0,0.1);">

        <!-- 顶部金属夹子 -->
        <div style="position:absolute;top:-40px;left:50%;transform:translateX(-50%);
            width:260px;height:90px;background-color:#fbe599;border-radius:20px;
            border:8px solid #6b5a3e;z-index:10;display:flex;justify-content:center;">
            <div style="width:60px;height:40px;border:8px solid #6b5a3e;border-radius:50%;
                margin-top:-30px;background-color:#e9f5ed;"></div>
        </div>

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:120px;
            font-weight:900;color:#4a3f35;letter-spacing:4px;
            text-shadow:4px 4px 0 #fff, 8px 8px 0 rgba(74,63,53,0.1);
            margin-bottom:30px;text-align:center;">
            {headline}
        </div>

        <!-- 粉色标签胶囊 -->
        <div style="background-color:#f2a999;border-radius:999px;padding:16px 48px;
            margin-bottom:60px;border:6px solid #fff;
            box-shadow:0 8px 0 rgba(0,0,0,0.05);">
            <span style="font-family:'DisplayBold',system-ui,sans-serif;font-size:44px;
                font-weight:900;color:#fff;letter-spacing:4px;">
                {labels}
            </span>
        </div>

        <!-- Logo 分区框 -->
        <div style="flex:1;width:90%;border:8px solid #4a3f35;border-radius:32px;
            position:relative;display:flex;flex-direction:column;align-items:center;
            justify-content:center;margin-top:20px;">
            <div style="position:absolute;top:-36px;background-color:#fff;padding:0 24px;
                border:6px solid #4a3f35;border-radius:999px;color:#4a3f35;
                font-size:32px;font-weight:900;">
                · {sub_headline} ·
            </div>
            <div style="padding:20px;">
                {grid}
            </div>
        </div>

        <!-- 底部标语 -->
        <div style="margin-top:50px;font-size:40px;font-weight:900;color:#4a3f35;
            letter-spacing:6px;">
            ▪▪▪ {tagline} ▪▪▪
        </div>
    </div>
</div>'''

    return wrap_page(body, bg="#e9f5ed")
