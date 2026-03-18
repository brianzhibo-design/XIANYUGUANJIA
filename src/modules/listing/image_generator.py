"""商品图片生成器 — HTML 模板渲染 + DrissionPage 截图。

流程:
1. 根据品类/框架选择 HTML 模板
2. 填充商品参数生成完整 HTML
3. 使用 DrissionPage headless Chrome 加载 HTML 并截图为 PNG
4. 返回本地文件路径列表
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from src.core.logger import get_logger

from .templates import (
    render_template,
    list_templates,
    render_by_frame,
    render_by_composition,
    list_frames_metadata,
)

logger = get_logger()

DEFAULT_OUTPUT_DIR = Path("data/generated_images")
VIEWPORT = {"width": 750, "height": 1000}
VIEWPORT_SQUARE = {"width": 1080, "height": 1080}


async def generate_product_images(
    *,
    category: str,
    params_list: list[dict[str, Any]] | None = None,
    output_dir: str | Path | None = None,
) -> list[str]:
    """为一个商品生成多张图片。

    Args:
        category: 模板品类 key (express/recharge/exchange/account/movie_ticket/game)
        params_list: 每张图片的参数字典列表。None 则生成 1 张默认图。
        output_dir: 输出目录，默认 data/generated_images/

    Returns:
        本地 PNG 文件路径列表
    """
    if not params_list:
        params_list = [{}]

    allowed = {t["key"] for t in list_templates()}
    if category not in allowed:
        logger.error(f"Invalid category: {category}, allowed: {allowed}")
        return []

    out = Path(output_dir or DEFAULT_OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for i, params in enumerate(params_list):
        html = render_template(category, params)
        if html is None:
            logger.warning(f"Template not found for category: {category}")
            continue

        safe_cat = category.replace("/", "_").replace("\\", "_").replace("..", "")
        filename = f"{safe_cat}_{uuid.uuid4().hex[:8]}_{i}.png"
        filepath = out / filename

        try:
            await _render_html_to_png(html, filepath)
            paths.append(str(filepath))
            logger.info(f"Generated image: {filepath}")
        except Exception as e:
            logger.error(f"Failed to render image {i} for {category}: {e}")

    return paths


async def _render_html_to_png(
    html: str,
    output_path: Path,
    viewport: dict[str, int] | None = None,
) -> None:
    """使用 DrissionPage headless Chrome 将 HTML 字符串渲染为 PNG 截图。"""
    import tempfile

    try:
        from DrissionPage import Chromium, ChromiumOptions
    except ImportError as exc:
        raise RuntimeError(
            "DrissionPage is required for image generation. "
            "Install: pip install DrissionPage"
        ) from exc

    vp = viewport or VIEWPORT

    def _render() -> None:
        co = ChromiumOptions()
        co.auto_port()
        co.headless()
        co.set_argument("--window-size", f'{vp["width"]},{vp["height"]}')
        co.set_argument("--hide-scrollbars")
        browser = Chromium(co)
        try:
            tab = browser.latest_tab
            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8"
            ) as f:
                f.write(html)
                tmp_path = f.name
            try:
                tab.get(f"file://{tmp_path}")
                import time

                time.sleep(0.3)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                tab.get_screenshot(path=str(output_path), full_page=False)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        finally:
            browser.quit()

    await asyncio.to_thread(_render)


async def generate_brand_images(
    category: str,
    brand_asset_ids: list[str],
    layout: str = "auto",
    title: str = "",
    params: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
) -> list[str]:
    """Generate product images with brand icon grid layout.

    Loads brand assets from BrandAssetManager, arranges them
    into the brand_grid template, and renders PNG screenshots.

    Args:
        category: Store category (express, exchange, etc.)
        brand_asset_ids: List of brand asset UUIDs to include.
        layout: "auto", "grid_2x2", "grid_2x3", "single_hero".
        title: Product title to display.
        params: Extra template parameters (price, tagline, badge, etc.)
        output_dir: Output directory; defaults to data/generated_images/.

    Returns:
        List of local PNG file paths.
    """
    from itertools import combinations
    from .brand_assets import BrandAssetManager

    mgr = BrandAssetManager()
    extra = params or {}

    brand_items = []
    for aid in brand_asset_ids:
        entry = None
        for a in mgr.list_assets():
            if a["id"] == aid:
                entry = a
                break
        if entry is None:
            continue
        path = mgr.get_asset_path(aid)
        if path is None:
            continue
        brand_items.append(
            {
                "name": entry["name"],
                "src": path.resolve().as_uri(),
            }
        )

    if not brand_items:
        logger.warning("No valid brand assets found for IDs: %s", brand_asset_ids)
        return []

    out = Path(output_dir or DEFAULT_OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    combos: list[list[dict[str, str]]] = []
    n = len(brand_items)

    if layout == "single_hero" or n == 1:
        for item in brand_items:
            combos.append([item])
    elif layout == "grid_2x2":
        if n >= 4:
            combos.append(brand_items[:4])
        else:
            combos.append(brand_items)
    elif layout == "grid_2x3":
        if n >= 6:
            combos.append(brand_items[:6])
        else:
            combos.append(brand_items)
    else:
        combos.append(brand_items)
        if n >= 3:
            for combo in combinations(brand_items, min(n, 3)):
                combos.append(list(combo))
                if len(combos) >= 5:
                    break

    paths: list[str] = []
    for i, combo in enumerate(combos):
        tpl_params = {
            "category": category,
            "brand_items": combo,
            "title": title or f"品牌组合 #{i + 1}",
            **extra,
        }
        html = render_template("brand_grid", tpl_params)
        if html is None:
            continue
        filename = f"brand_{category}_{uuid.uuid4().hex[:8]}_{i}.png"
        filepath = out / filename
        try:
            await _render_html_to_png(html, filepath)
            paths.append(str(filepath))
            logger.info("Generated brand image: %s", filepath)
        except Exception as e:
            logger.error("Failed to render brand image %d: %s", i, e)

    return paths


async def generate_frame_images(
    *,
    frame_id: str,
    category: str = "express",
    params: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
) -> list[str]:
    """使用新的框架模板系统生成商品图片（1080x1080 正方形）。

    Args:
        frame_id: 框架模板 ID（如 "grid_paper", "id_badge" 等）
        category: 品类 key，决定配色主题
        params: 模板参数（headline, sub_headline, brand_items 等）
        output_dir: 输出目录

    Returns:
        本地 PNG 文件路径列表
    """
    html = render_by_frame(frame_id, category, params)
    if html is None:
        logger.error("Frame template not found: %s", frame_id)
        return []

    out = Path(output_dir or DEFAULT_OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    safe_id = frame_id.replace("/", "_").replace("\\", "_").replace("..", "")
    filename = f"frame_{safe_id}_{category}_{uuid.uuid4().hex[:8]}.png"
    filepath = out / filename

    try:
        await _render_html_to_png(html, filepath, viewport=VIEWPORT_SQUARE)
        logger.info(f"Generated frame image: {filepath}")
        return [str(filepath)]
    except Exception as exc:
        logger.error(f"Failed to render frame image {frame_id}: {exc}")
        return []


async def generate_composition_images(
    *,
    category: str = "express",
    params: dict[str, Any] | None = None,
    layers: dict[str, str] | None = None,
    output_dir: str | Path | None = None,
) -> tuple[list[str], dict[str, str]]:
    """使用组合式模版引擎生成商品图片。

    Returns:
        (本地 PNG 文件路径列表, 实际使用的图层组合)
    """
    html, used_layers = render_by_composition(category, params, layers)
    if html is None:
        logger.error("Composition rendering failed")
        return [], {}

    out = Path(output_dir or DEFAULT_OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    layer_tag = "_".join(used_layers.get(k, "?")[:6] for k in ("layout", "color_scheme", "decoration", "title_style"))
    filename = f"comp_{layer_tag}_{uuid.uuid4().hex[:8]}.png"
    filepath = out / filename

    try:
        await _render_html_to_png(html, filepath, viewport=VIEWPORT_SQUARE)
        logger.info(f"Generated composition image: {filepath}")
        return [str(filepath)], used_layers
    except Exception as exc:
        logger.error(f"Failed to render composition image: {exc}")
        return [], used_layers


def get_available_categories() -> list[dict[str, str]]:
    """返回可用的模板品类列表。"""
    return list_templates()


def get_available_frames() -> list[dict[str, Any]]:
    """返回可用的框架模板列表。"""
    return list_frames_metadata()
