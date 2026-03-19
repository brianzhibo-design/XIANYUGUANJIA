"""客服气泡风格 — 灰色背景，聊天气泡白卡，客服头像，标签pills。"""

from __future__ import annotations

from typing import Any

from ._common import brand_grid_html, e, wrap_page

FRAME_META = {
    "id": "chat_bubble",
    "name": "客服气泡风",
    "desc": "聊天窗口样式，客服头像与气泡白卡，高亲和力",
    "tags": ["亲和", "对话", "信任"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels_raw = str(params.get("labels") or theme.get("labels", "") or "")
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items,
        shape="rounded_square",
        size=140,
        gap=24,
        max_cols=4,
    )

    label_pills = ""
    for lbl in labels_raw.split("/"):
        lbl = lbl.strip()
        if lbl:
            label_pills += (
                f'<span style="background-color:#f1f5f9;padding:12px 30px;'
                f"border-radius:999px;font-size:32px;font-weight:700;"
                f'color:#475569;">{e(lbl)}</span>\n'
            )

    body = f"""
<div style="width:1080px;height:1080px;background-color:#e2e8f0;padding:60px;
    display:flex;flex-direction:column;justify-content:center;">

    <!-- 客服头像行 -->
    <div style="display:flex;align-items:center;margin-bottom:20px;">
        <div style="width:100px;height:100px;background-color:#3b82f6;border-radius:50%;
            display:flex;align-items:center;justify-content:center;font-size:50px;">
            &#x1F469;&#x200D;&#x1F4BB;
        </div>
        <div style="margin-left:20px;font-size:36px;font-weight:700;color:#64748b;">
            官方代发客服
        </div>
    </div>

    <!-- 气泡白卡 -->
    <div style="background-color:#ffffff;border-radius:40px;
        border-top-left-radius:0;padding:80px 60px;position:relative;
        box-shadow:0 20px 40px rgba(0,0,0,0.05);flex:1;display:flex;
        flex-direction:column;">

        <!-- 主标题 -->
        <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:120px;
            font-weight:900;color:#0f172a;margin-bottom:30px;">
            {headline}
        </div>

        <!-- 副标题 -->
        <div style="font-size:60px;font-weight:900;color:#3b82f6;margin-bottom:50px;">
            {sub_headline}
        </div>

        <!-- 标签 pills -->
        <div style="display:flex;gap:20px;margin-bottom:60px;flex-wrap:wrap;">
            {label_pills}
        </div>

        <!-- Logo 区域 -->
        <div style="flex:1;border-top:2px solid #e2e8f0;border-bottom:2px solid #e2e8f0;
            padding:40px 0;display:flex;align-items:center;justify-content:center;">
            {grid}
        </div>

        <!-- 底部确认标语 -->
        <div style="margin-top:40px;font-size:42px;font-weight:900;color:#10b981;">
            ✓ {tagline}
        </div>
    </div>
</div>"""

    return wrap_page(body, bg="#e2e8f0")
