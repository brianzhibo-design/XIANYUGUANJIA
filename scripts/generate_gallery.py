#!/usr/bin/env python3
"""生成组合式模版引擎的视觉画廊。

遍历所有 Layout x ColorScheme x Decoration x TitleStyle 组合（4x4x5x3=240），
生成缩略图并拼成一张网格大图，用于人工视觉审查。

用法:
    python scripts/generate_gallery.py [--sample N] [--thumb-size 360]

参数:
    --sample N       只随机生成 N 个组合（默认全部 240 个）
    --thumb-size S   缩略图尺寸，默认 360px
    --output PATH    输出拼图路径，默认 data/gallery.png
"""

import argparse
import asyncio
import itertools
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    parser = argparse.ArgumentParser(description="生成组合模版画廊")
    parser.add_argument("--sample", type=int, default=0, help="随机抽样数量，0=全部")
    parser.add_argument("--thumb-size", type=int, default=360)
    parser.add_argument("--output", type=str, default="data/gallery.png")
    args = parser.parse_args()

    from src.modules.listing.templates.layers.base import LAYOUT_REGISTRY, MODIFIER_REGISTRY

    # trigger registration
    from src.modules.listing.templates import layers as _  # noqa: F401

    layouts = list(LAYOUT_REGISTRY.keys())
    color_schemes = list(MODIFIER_REGISTRY["color_scheme"].keys())
    decorations = list(MODIFIER_REGISTRY["decoration"].keys())
    title_styles = list(MODIFIER_REGISTRY["title_style"].keys())

    all_combos = list(itertools.product(layouts, color_schemes, decorations, title_styles))
    total = len(all_combos)
    print(f"Total combinations: {total}")

    if args.sample and args.sample < total:
        combos = random.sample(all_combos, args.sample)
        print(f"Sampled {args.sample} combinations")
    else:
        combos = all_combos

    from src.modules.listing.templates.frames._common import sample_brand_items
    from src.modules.listing.templates.themes import get_random_variant
    from src.modules.listing.templates.compositor import compose

    brand_items = sample_brand_items()
    variant = get_random_variant("express")
    params = {
        "brand_items": brand_items,
        "headline": variant.get("headline", "首重3元起"),
        "sub_headline": variant.get("sub_headline", "全国免费上门取件"),
        "labels": variant.get("labels", "个人/商家/退换货/可用"),
        "tagline": variant.get("tagline", "秒出单号 · 操作简单"),
    }

    output_dir = Path("data/gallery_thumbs")
    output_dir.mkdir(parents=True, exist_ok=True)

    thumb_paths: list[tuple[str, Path]] = []
    for i, (lay, cs, deco, ts) in enumerate(combos):
        label = f"{lay}_{cs}_{deco}_{ts}"
        html, _ = compose(
            layout=lay, color_scheme=cs, decoration=deco, title_style=ts,
            params=params, theme=variant,
        )

        thumb_file = output_dir / f"{label}.png"
        from src.modules.listing.image_generator import _render_html_to_png
        try:
            await _render_html_to_png(html, thumb_file, viewport={"width": 1080, "height": 1080})
            thumb_paths.append((label, thumb_file))
            print(f"  [{i+1}/{len(combos)}] {label}")
        except Exception as exc:
            print(f"  [{i+1}/{len(combos)}] FAILED {label}: {exc}")

    if not thumb_paths:
        print("No thumbnails generated.")
        return

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed. Skipping grid assembly. Thumbnails saved in data/gallery_thumbs/")
        return

    thumb_size = args.thumb_size
    cols = min(12, len(thumb_paths))
    rows = (len(thumb_paths) + cols - 1) // cols
    padding = 4
    label_height = 20
    cell = thumb_size + padding * 2 + label_height

    canvas = Image.new("RGB", (cols * cell, rows * cell), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    for idx, (label, path) in enumerate(thumb_paths):
        r, c = divmod(idx, cols)
        x = c * cell + padding
        y = r * cell + padding

        try:
            img = Image.open(path).resize((thumb_size, thumb_size), Image.LANCZOS)
            canvas.paste(img, (x, y))
        except Exception:
            draw.rectangle([x, y, x + thumb_size, y + thumb_size], fill=(200, 200, 200))

        short_label = label.replace("_", " ")[:40]
        draw.text((x + 2, y + thumb_size + 2), short_label, fill=(60, 60, 60))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "PNG")
    print(f"\nGallery saved: {output_path} ({cols}x{rows}, {len(thumb_paths)} combos)")


if __name__ == "__main__":
    asyncio.run(main())
