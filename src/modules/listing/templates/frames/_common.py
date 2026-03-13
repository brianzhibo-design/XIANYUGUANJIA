"""共用 HTML/CSS 工具函数。"""

from __future__ import annotations

from html import escape
from pathlib import Path

SQUARE_VIEWPORT = {"width": 1080, "height": 1080}

_FONT_DIR = Path(__file__).resolve().parents[4] / "data" / "fonts"
_FONT_PATH = _FONT_DIR / "AlibabaPuHuiTi-Heavy.ttf"


def e(text: str | None) -> str:
    return escape(str(text or ""))


def _font_face_css() -> str:
    """生成 @font-face 声明，使用阿里巴巴普惠体 Heavy。"""
    if _FONT_PATH.exists():
        from src.modules.listing.brand_assets import file_to_data_uri
        uri = file_to_data_uri(_FONT_PATH)
    else:
        uri = ""
    return f"""@font-face {{
    font-family: 'DisplayBold';
    src: url('{uri}') format('truetype');
    font-weight: 900;
    font-style: normal;
}}"""


def brand_grid_html(
    brand_items: list[dict[str, str]],
    *,
    shape: str = "circle",
    size: int = 150,
    gap: int = 20,
    max_cols: int = 5,
    show_name: bool = False,
    name_color: str = "#444",
    border_color: str = "transparent",
    bg_color: str = "transparent",
) -> str:
    """生成品牌 Logo 网格 HTML。

    默认 150px 大图、圆形裁切、无边框，对标真实闲鱼快递代发主图风格。
    """
    if not brand_items:
        return ""

    n = len(brand_items)
    if n <= 2:
        cols = n
    elif n <= 4:
        cols = 2
    elif n <= 6:
        cols = 3
    elif n <= 8:
        cols = 4
    else:
        cols = min(max_cols, 5)

    radius = "50%" if shape == "circle" else ("16px" if shape == "rounded_square" else "4px")

    items_html = ""
    for item in brand_items[:8]:
        src = e(item.get("src", ""))
        name = e(item.get("name", ""))
        name_font = max(14, size // 8)
        name_el = (
            f'<span style="font-size:{name_font}px;font-weight:700;color:{name_color};'
            f'margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'
            f'max-width:{size + 20}px;letter-spacing:0.5px;">{name}</span>'
        ) if show_name and name else ""

        border_css = f"border:2px solid {border_color};" if border_color != "transparent" else ""
        bg_css = f"background:{bg_color};" if bg_color != "transparent" else ""

        items_html += (
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px;">'
            f'<img src="{src}" alt="{name}" style="width:{size}px;height:{size}px;'
            f'object-fit:cover;border-radius:{radius};{border_css}{bg_css}'
            f'overflow:hidden;">'
            f'{name_el}</div>\n'
        )

    return (
        f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
        f'gap:{gap}px;justify-items:center;align-items:start;">\n{items_html}</div>'
    )


def brand_price_list_html(
    brand_items: list[dict[str, str]],
    *,
    price_text: str = "首重3元起",
    row_height: int = 60,
    font_size: int = 22,
    text_color: str = "#333",
    accent_color: str = "#dc2626",
    border_color: str = "#eee",
) -> str:
    """生成品牌名+价格的列表 HTML，适用于 price_table 等模版。"""
    if not brand_items:
        return ""
    rows = ""
    for item in brand_items[:8]:
        src = e(item.get("src", ""))
        name = e(item.get("name", ""))
        price = e(item.get("price", price_text))
        rows += (
            f'<div style="display:flex;align-items:center;height:{row_height}px;'
            f'border-bottom:1px solid {border_color};padding:0 20px;">'
            f'<img src="{src}" style="width:40px;height:40px;border-radius:8px;'
            f'object-fit:cover;margin-right:16px;">'
            f'<span style="flex:1;font-size:{font_size}px;font-weight:700;'
            f'color:{text_color};">{name}</span>'
            f'<span style="font-size:{font_size}px;font-weight:900;'
            f'color:{accent_color};">{price}</span></div>\n'
        )
    return f'<div style="display:flex;flex-direction:column;">{rows}</div>'


def wrap_page(body: str, *, width: int = 1080, height: int = 1080, bg: str = "#ffffff") -> str:
    """将 body 内容包裹成完整 HTML 页面，内置粗体字体声明。"""
    font_face = _font_face_css()
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
{font_face}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px; overflow: hidden;
    font-family: 'DisplayBold', -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif;
    background: {bg};
}}
</style>
</head>
<body>
{body}
</body>
</html>'''


def sample_brand_items() -> list[dict[str, str]]:
    """返回示例品牌数据（用于缩略图预渲染）。"""
    brands = [
        ("顺丰速运", "SF"),
        ("中通快递", "ZTO"),
        ("圆通速递", "YTO"),
        ("韵达快递", "YD"),
        ("申通快递", "STO"),
        ("极兔速递", "J&T"),
        ("京东物流", "JDL"),
        ("德邦快递", "DBL"),
        ("中国邮政", "EMS"),
        ("百世快递", "BEST"),
    ]
    items = []
    for name, code in brands:
        svg = _placeholder_logo_svg(code, name)
        items.append({"name": name, "src": f"data:image/svg+xml,{svg}"})
    return items


def _placeholder_logo_svg(code: str, name: str) -> str:
    """生成占位 Logo SVG（无需外部图片文件）。"""
    import hashlib
    h = int(hashlib.md5(code.encode()).hexdigest()[:6], 16) % 360
    color = f"hsl({h}, 65%, 40%)"
    bg = f"hsl({h}, 50%, 88%)"
    from urllib.parse import quote
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="150" height="150" viewBox="0 0 150 150">'
        f'<circle cx="75" cy="75" r="75" fill="{bg}"/>'
        f'<text x="75" y="55" text-anchor="middle" font-size="32" font-weight="900" '
        f'fill="{color}" font-family="Arial">{code}</text>'
        f'<text x="75" y="95" text-anchor="middle" font-size="16" font-weight="700" '
        f'fill="{color}" font-family="PingFang SC,sans-serif">{name}</text></svg>'
    )
    return quote(svg, safe='')
