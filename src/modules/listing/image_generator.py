"""商品图片生成器 — HTML 模板渲染 + Playwright 截图。

流程:
1. 根据品类选择 HTML 模板
2. 填充商品参数生成完整 HTML
3. 使用 Playwright 加载 HTML 并截图为 PNG
4. 返回本地文件路径列表
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from src.core.logger import get_logger
from .templates import render_template, list_templates

logger = get_logger()

DEFAULT_OUTPUT_DIR = Path("data/generated_images")
VIEWPORT = {"width": 750, "height": 1000}


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


async def _render_html_to_png(html: str, output_path: Path) -> None:
    """使用 Playwright 将 HTML 字符串渲染为 PNG 截图。"""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for image generation. "
            "Install: pip install playwright && playwright install chromium"
        ) from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport=VIEWPORT)
            await page.set_content(html, wait_until="networkidle")
            await asyncio.sleep(0.3)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(output_path), full_page=False)
        finally:
            await browser.close()


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
        brand_items.append({
            "name": entry["name"],
            "src": path.resolve().as_uri(),
        })

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


def get_available_categories() -> list[dict[str, str]]:
    """返回可用的模板品类列表。"""
    return list_templates()
