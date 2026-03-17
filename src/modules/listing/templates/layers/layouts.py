"""4 种布局主模版。

每个 Layout 输出完整 HTML body，通过 CSS 变量引用配色。
标题元素统一使用 class="title-text"，由 TitleStyle 修饰器控制样式。
"""

from __future__ import annotations

from typing import Any

from ..frames._common import brand_grid_html, brand_price_list_html, e, sample_brand_items
from .base import LayoutOutput, register_layout


def _ensure_brand_items(params: dict[str, Any]) -> list[dict[str, str]]:
    items = params.get("brand_items", [])
    if not items:
        items = sample_brand_items()
    return items


@register_layout("hero_center", name="居中大标题", desc="大标题居中，品牌网格居下")
def hero_center(params: dict[str, Any], theme: dict[str, Any]) -> LayoutOutput:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = params.get("labels") or theme.get("labels", "")
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = _ensure_brand_items(params)
    badge = e(theme.get("badge", ""))

    label_tags = ""
    for lb in (labels.split("/") if isinstance(labels, str) else labels):
        lb = lb.strip()
        if lb:
            label_tags += (
                f'<span style="display:inline-block;padding:6px 18px;'
                f'border-radius:20px;font-size:20px;font-weight:700;'
                f'background:var(--bg-secondary, #f3f4f6);color:var(--text-primary, #1f2937);'
                f'border:2px solid var(--border-color,transparent);">{e(lb)}</span>\n'
            )

    grid = brand_grid_html(brand_items, size=130, show_name=True,
                           name_color="var(--text-primary)", gap=24)

    body = f'''
<div style="position:relative;width:1080px;height:1080px;
    background:var(--bg-primary);display:flex;flex-direction:column;
    align-items:center;justify-content:center;padding:60px;overflow:hidden;">

  <div style="position:absolute;top:30px;right:40px;padding:8px 24px;
      border-radius:20px;background:var(--badge-bg,var(--text-accent));
      color:var(--badge-text,#fff);font-size:18px;font-weight:700;">{badge}</div>

  <div class="title-text" style="text-align:center;margin-bottom:16px;">{headline}</div>

  <div style="font-size:32px;font-weight:700;color:var(--text-light,#fff);
      text-align:center;margin-bottom:24px;opacity:0.9;">{sub_headline}</div>

  <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;
      margin-bottom:36px;">{label_tags}</div>

  <div style="flex:1;display:flex;align-items:center;justify-content:center;
      width:100%;">{grid}</div>

  <div style="font-size:20px;color:var(--text-light,#fff);opacity:0.7;
      letter-spacing:4px;margin-top:20px;">{tagline}</div>
</div>'''

    css = ""
    return LayoutOutput(body_html=body, required_css=css)


@register_layout("split_panel", name="左右分栏", desc="左侧文案，右侧品牌网格")
def split_panel(params: dict[str, Any], theme: dict[str, Any]) -> LayoutOutput:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    labels = params.get("labels") or theme.get("labels", "")
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = _ensure_brand_items(params)
    badge = e(theme.get("badge", ""))

    label_items = ""
    for lb in (labels.split("/") if isinstance(labels, str) else labels):
        lb = lb.strip()
        if lb:
            label_items += (
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'font-size:22px;font-weight:600;color:var(--text-primary);">'
                f'<span style="width:8px;height:8px;border-radius:50%;'
                f'background:var(--text-accent);"></span>{e(lb)}</div>\n'
            )

    grid = brand_grid_html(brand_items, size=140, show_name=True,
                           name_color="var(--text-primary)", max_cols=3, gap=20,
                           bg_color="var(--bg-secondary,rgba(255,255,255,0.15))",
                           shape="rounded_square")

    body = f'''
<div style="position:relative;width:1080px;height:1080px;
    background:var(--bg-primary);display:grid;grid-template-columns:1fr 1fr;
    overflow:hidden;">

  <!-- Left: Text -->
  <div style="display:flex;flex-direction:column;justify-content:center;
      padding:60px 50px;gap:24px;">

    <div style="padding:6px 20px;border-radius:20px;width:fit-content;
        background:var(--badge-bg,var(--text-accent));
        color:var(--badge-text,#fff);font-size:16px;font-weight:700;">{badge}</div>

    <div class="title-text">{headline}</div>

    <div style="font-size:28px;font-weight:600;color:var(--text-light,#fff);
        opacity:0.9;line-height:1.4;">{sub_headline}</div>

    <div style="display:flex;flex-direction:column;gap:12px;margin-top:8px;">
      {label_items}
    </div>

    <div style="font-size:18px;color:var(--text-light,#fff);opacity:0.6;
        letter-spacing:3px;margin-top:auto;">{tagline}</div>
  </div>

  <!-- Right: Brands -->
  <div style="display:flex;align-items:center;justify-content:center;
      padding:40px;background:var(--bg-secondary,rgba(0,0,0,0.1));
      border-left:3px solid var(--border-color,rgba(255,255,255,0.1));">
    {grid}
  </div>
</div>'''

    return LayoutOutput(body_html=body)


@register_layout("price_rows", name="价格列表", desc="表格式品牌+价格行")
def price_rows(params: dict[str, Any], theme: dict[str, Any]) -> LayoutOutput:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = _ensure_brand_items(params)
    badge = e(theme.get("badge", ""))

    price_list = brand_price_list_html(
        brand_items,
        price_text="首重3元起",
        row_height=72,
        font_size=26,
        text_color="var(--text-primary)",
        accent_color="var(--text-accent)",
        border_color="var(--border-color,rgba(0,0,0,0.08))",
    )

    body = f'''
<div style="position:relative;width:1080px;height:1080px;
    background:var(--bg-primary);display:flex;flex-direction:column;
    overflow:hidden;">

  <!-- Header -->
  <div style="padding:50px 60px 30px;text-align:center;">
    <div style="display:inline-block;padding:6px 24px;border-radius:20px;
        background:var(--badge-bg,var(--text-accent));
        color:var(--badge-text,#fff);font-size:16px;font-weight:700;
        margin-bottom:16px;">{badge}</div>
    <div class="title-text">{headline}</div>
    <div style="font-size:26px;font-weight:600;color:var(--text-primary);
        opacity:0.8;margin-top:10px;">{sub_headline}</div>
  </div>

  <!-- Price List -->
  <div style="flex:1;padding:10px 60px;overflow:hidden;">
    {price_list}
  </div>

  <!-- Footer -->
  <div style="padding:20px;text-align:center;font-size:18px;
      color:var(--text-primary);opacity:0.5;letter-spacing:4px;">{tagline}</div>
</div>'''

    return LayoutOutput(body_html=body)


@register_layout("brand_hero", name="品牌大图", desc="品牌 Logo 大面积展示，文案辅助")
def brand_hero(params: dict[str, Any], theme: dict[str, Any]) -> LayoutOutput:
    headline = e(params.get("headline") or theme.get("headline", ""))
    sub_headline = e(params.get("sub_headline") or theme.get("sub_headline", ""))
    tagline = e(params.get("tagline") or theme.get("tagline", ""))
    brand_items = _ensure_brand_items(params)
    badge = e(theme.get("badge", ""))

    grid = brand_grid_html(brand_items, size=180, show_name=True,
                           name_color="var(--text-primary)", gap=30, max_cols=4,
                           shape="rounded_square",
                           bg_color="var(--bg-secondary,rgba(255,255,255,0.2))")

    body = f'''
<div style="position:relative;width:1080px;height:1080px;
    background:var(--bg-primary);display:flex;flex-direction:column;
    align-items:center;overflow:hidden;">

  <!-- Top bar -->
  <div style="width:100%;padding:40px 60px 20px;display:flex;
      align-items:center;justify-content:space-between;">
    <div class="title-text title-text--compact">{headline}</div>
    <div style="padding:8px 24px;border-radius:20px;
        background:var(--badge-bg,var(--text-accent));
        color:var(--badge-text,#fff);font-size:16px;font-weight:700;">{badge}</div>
  </div>

  <div style="font-size:26px;font-weight:600;color:var(--text-light,#fff);
      opacity:0.8;margin-bottom:20px;">{sub_headline}</div>

  <!-- Brand Grid (hero) -->
  <div style="flex:1;display:flex;align-items:center;justify-content:center;
      padding:20px 60px;width:100%;">
    {grid}
  </div>

  <!-- Footer -->
  <div style="padding:30px;font-size:20px;color:var(--text-light,#fff);
      opacity:0.6;letter-spacing:4px;">{tagline}</div>
</div>'''

    css = ".title-text--compact { font-size: 56px !important; }"
    return LayoutOutput(body_html=body, required_css=css)
