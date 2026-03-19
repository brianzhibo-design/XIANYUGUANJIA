"""宝丽来相纸风格 — 灰色背景，白边宽下边距，微旋转，标签框。"""

from __future__ import annotations

from typing import Any

from ._common import brand_grid_html, e, wrap_page

FRAME_META = {
    "id": "polaroid",
    "name": "宝丽来相纸",
    "desc": "白色相纸宽下边距，微旋转效果与手写感标语",
    "tags": ["生活", "手作", "文艺"],
}


def render(params: dict[str, Any], theme: dict[str, str]) -> str:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels_raw = str(params.get("labels") or theme.get("labels", "") or "")
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = params.get("brand_items", [])

    grid = brand_grid_html(
        brand_items,
        shape="circle",
        size=130,
        gap=24,
        max_cols=4,
    )

    label_boxes = ""
    for lbl in labels_raw.split("/"):
        lbl = lbl.strip()
        if lbl:
            label_boxes += (
                f'<span style="border:3px solid #cbd5e1;padding:10px 30px;'
                f"border-radius:8px;font-size:32px;font-weight:700;"
                f'color:#475569;">{e(lbl)}</span>\n'
            )

    body = f"""
<div style="width:1080px;height:1080px;background-color:#cbd5e1;padding:60px;
    display:flex;align-items:center;justify-content:center;">

    <!-- 相纸主体 -->
    <div style="width:90%;height:95%;background-color:#fff;
        padding:40px 40px 140px 40px;transform:rotate(2deg);
        box-shadow:0 25px 50px rgba(0,0,0,0.15);display:flex;flex-direction:column;
        position:relative;">

        <!-- 照片内容区 -->
        <div style="background-color:#f1f5f9;flex:1;border:2px inset rgba(0,0,0,0.1);
            display:flex;flex-direction:column;align-items:center;
            justify-content:center;padding:60px 40px;">

            <!-- 主标题 -->
            <div style="font-family:'DisplayBold',system-ui,sans-serif;font-size:120px;
                font-weight:900;color:#334155;margin-bottom:30px;text-align:center;
                line-height:1.1;">
                {headline}
            </div>

            <!-- 副标题 -->
            <div style="font-size:60px;font-weight:700;color:#ef4444;
                margin-bottom:50px;">
                {sub_headline}
            </div>

            <!-- 标签框 -->
            <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:16px;
                margin-bottom:60px;">
                {label_boxes}
            </div>

            <!-- Logo 网格 -->
            {grid}
        </div>

        <!-- 底部手写标语 -->
        <div style="position:absolute;bottom:50px;left:0;width:100%;text-align:center;
            font-size:50px;font-weight:700;color:#334155;font-style:italic;">
            ~ {tagline} ~
        </div>
    </div>
</div>"""

    return wrap_page(body, bg="#cbd5e1")
