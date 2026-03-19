"""Product listing, publish queue, brand assets, and image generation routes."""

from __future__ import annotations

import mimetypes
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.dashboard.router import RouteContext, delete_prefix, get, get_prefix, post, post_prefix, put_prefix


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously (lazy import to avoid circular deps)."""
    from src.dashboard.mimic_ops import _run_async as _ra

    return _ra(coro)


# ---------------------------------------------------------------------------
# GET /api/listing/templates
# ---------------------------------------------------------------------------


@get("/api/listing/templates")
def handle_listing_templates(ctx: RouteContext) -> None:
    from src.modules.listing.templates import list_frames_metadata, list_templates

    ctx.send_json({"ok": True, "templates": list_templates(), "frames": list_frames_metadata()})


# ---------------------------------------------------------------------------
# GET /api/listing/frames
# ---------------------------------------------------------------------------


@get("/api/listing/frames")
def handle_listing_frames(ctx: RouteContext) -> None:
    from src.modules.listing.templates import list_frames_metadata

    ctx.send_json({"ok": True, "frames": list_frames_metadata()})


# ---------------------------------------------------------------------------
# GET /api/listing/thumbnails
# ---------------------------------------------------------------------------


@get("/api/listing/thumbnails")
def handle_listing_thumbnails(ctx: RouteContext) -> None:
    from src.modules.listing.templates import list_frames_metadata as _lf

    cat = ctx.query_str("category", "express").strip()
    thumb_map = {}
    for f in _lf():
        p = Path(f"data/thumbnails/{f['id']}_{cat}.png")
        if p.is_file():
            thumb_map[f["id"]] = f"/api/generated-image?path={p}"
    ctx.send_json({"ok": True, "thumbnails": thumb_map})


# ---------------------------------------------------------------------------
# GET /api/generated-image
# ---------------------------------------------------------------------------


@get("/api/generated-image")
def handle_generated_image(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    img_path = ctx.query_str("path", "").strip()
    if not img_path:
        ctx.send_json(_error_payload("Missing path"), status=400)
        return

    resolved = Path(img_path).resolve()
    allowed_dirs = [
        Path("data/generated_images").resolve(),
        Path("data/brand_assets").resolve(),
        Path("data/thumbnails").resolve(),
    ]
    if not any(str(resolved).startswith(str(d)) for d in allowed_dirs):
        ctx.send_json(_error_payload("Access denied"), status=403)
        return
    if not resolved.is_file():
        ctx.send_json(_error_payload("File not found"), status=404)
        return
    ext = resolved.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    content_type = mime_map.get(ext, "application/octet-stream")
    data = resolved.read_bytes()
    ctx.send_response(200)
    ctx.send_header("Content-Type", content_type)
    ctx.send_header("Content-Length", str(len(data)))
    ctx.send_header("Cache-Control", "public, max-age=3600")
    ctx.end_headers()
    ctx.wfile.write(data)


# ---------------------------------------------------------------------------
# GET /api/listing/preview-frame
# ---------------------------------------------------------------------------


@get("/api/listing/preview-frame")
def handle_listing_preview_frame(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    frame_id = ctx.query_str("frame_id", "").strip()
    category = ctx.query_str("category", "express").strip()
    brand_ids_raw = ctx.query_str("brand_asset_ids", "").strip()
    if not frame_id:
        ctx.send_json(_error_payload("Missing frame_id"), status=400)
        return

    brand_asset_ids = [x.strip() for x in brand_ids_raw.split(",") if x.strip()] if brand_ids_raw else []

    if brand_asset_ids:
        from src.modules.listing.brand_assets import BrandAssetManager, file_to_data_uri

        mgr = BrandAssetManager()
        brand_items = []
        for aid in brand_asset_ids:
            entry = next((a for a in mgr.list_assets() if a["id"] == aid), None)
            if entry is None:
                continue
            p = mgr.get_asset_path(aid)
            if p is None:
                continue
            brand_items.append({"name": entry["name"], "src": file_to_data_uri(p)})
    else:
        thumb_path = Path(f"data/thumbnails/{frame_id}_{category}.png")
        if thumb_path.is_file():
            ctx.send_json(
                {"ok": True, "image_path": str(thumb_path), "image_url": f"/api/generated-image?path={thumb_path}"}
            )
            return
        from src.modules.listing.templates.frames._common import sample_brand_items

        brand_items = sample_brand_items()

    from src.modules.listing.image_generator import generate_frame_images

    params = {"brand_items": brand_items}
    output_dir = "data/thumbnails" if not brand_asset_ids else "data/generated_images"
    paths = _run_async(
        generate_frame_images(frame_id=frame_id, category=category, params=params, output_dir=output_dir)
    )
    if not paths:
        ctx.send_json(_error_payload("Failed to generate preview"), status=500)
        return
    if not brand_asset_ids:
        import shutil

        stable_name = f"data/thumbnails/{frame_id}_{category}.png"
        try:
            shutil.copy2(paths[0], stable_name)
        except Exception:
            stable_name = paths[0]
    else:
        stable_name = paths[0]
    ctx.send_json({"ok": True, "image_path": stable_name, "image_url": f"/api/generated-image?path={stable_name}"})


# ---------------------------------------------------------------------------
# GET /api/composition/layers
# ---------------------------------------------------------------------------


@get("/api/composition/layers")
def handle_composition_layers(ctx: RouteContext) -> None:
    from src.modules.listing.templates.compositor import list_all_options

    options = list_all_options()
    ctx.send_json({"ok": True, **options})


# ---------------------------------------------------------------------------
# GET /api/listing/preview-composition
# ---------------------------------------------------------------------------


@get("/api/listing/preview-composition")
def handle_listing_preview_composition(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    category = ctx.query_str("category", "express").strip()
    layout_p = ctx.query_str("layout") or None
    cs_p = ctx.query_str("color_scheme") or None
    deco_p = ctx.query_str("decoration") or None
    ts_p = ctx.query_str("title_style") or None
    brand_ids_raw = ctx.query_str("brand_asset_ids", "").strip()

    brand_asset_ids = [x.strip() for x in brand_ids_raw.split(",") if x.strip()] if brand_ids_raw else []

    if brand_asset_ids:
        from src.modules.listing.brand_assets import BrandAssetManager, file_to_data_uri

        mgr = BrandAssetManager()
        brand_items = []
        for aid in brand_asset_ids:
            entry = next((a for a in mgr.list_assets() if a["id"] == aid), None)
            if entry is None:
                continue
            p = mgr.get_asset_path(aid)
            if p is None:
                continue
            brand_items.append({"name": entry["name"], "src": file_to_data_uri(p)})
    else:
        from src.modules.listing.templates.frames._common import sample_brand_items

        brand_items = sample_brand_items()

    layers = {}
    if layout_p:
        layers["layout"] = layout_p
    if cs_p:
        layers["color_scheme"] = cs_p
    if deco_p:
        layers["decoration"] = deco_p
    if ts_p:
        layers["title_style"] = ts_p

    from src.modules.listing.image_generator import generate_composition_images

    params = {"brand_items": brand_items}
    paths, used_layers = _run_async(
        generate_composition_images(
            category=category, params=params, layers=layers or None, output_dir="data/generated_images"
        )
    )
    if not paths:
        ctx.send_json(_error_payload("Failed to generate composition preview"), status=500)
        return
    ctx.send_json(
        {
            "ok": True,
            "image_path": paths[0],
            "image_url": f"/api/generated-image?path={paths[0]}",
            "composition": used_layers,
        }
    )


# ---------------------------------------------------------------------------
# GET /api/auto-publish/status
# ---------------------------------------------------------------------------


@get("/api/auto-publish/status")
def handle_auto_publish_status(ctx: RouteContext) -> None:
    from src.dashboard.config_service import read_system_config as _read_system_config
    from src.modules.listing.scheduler import AutoPublishScheduler

    ap_cfg = _read_system_config().get("auto_publish", {})
    user_schedule = {}
    for k in (
        "cold_start_days",
        "cold_start_daily_count",
        "steady_replace_count",
        "max_active_listings",
        "steady_replace_metric",
    ):
        if k in ap_cfg:
            user_schedule[k] = ap_cfg[k]
    sched = AutoPublishScheduler(schedule=user_schedule if user_schedule else None)
    ctx.send_json({"ok": True, **sched.get_status()})


# ---------------------------------------------------------------------------
# GET /api/brand-assets/grouped
# ---------------------------------------------------------------------------


@get("/api/brand-assets/grouped")
def handle_brand_assets_grouped(ctx: RouteContext) -> None:
    from src.modules.listing.brand_assets import BrandAssetManager

    mgr = BrandAssetManager()
    cat_filter = ctx.query_str("category") or None
    grouped = mgr.get_brands_grouped(category=cat_filter)
    ctx.send_json({"ok": True, "brands": grouped})


# ---------------------------------------------------------------------------
# GET /api/publish-queue
# ---------------------------------------------------------------------------


@get("/api/publish-queue")
def handle_publish_queue(ctx: RouteContext) -> None:
    from src.modules.listing.publish_queue import PublishQueue

    q = PublishQueue(project_root=ctx.mimic_ops.project_root)
    date_filter = ctx.query_str("date") or None
    items = q.get_queue(date=date_filter)
    ctx.send_json({"ok": True, "items": [asdict(it) for it in items]})


# ---------------------------------------------------------------------------
# GET /api/brand-assets
# ---------------------------------------------------------------------------


@get("/api/brand-assets")
def handle_brand_assets(ctx: RouteContext) -> None:
    from src.modules.listing.brand_assets import BrandAssetManager

    mgr = BrandAssetManager()
    cat_filter = ctx.query_str("category") or None
    ctx.send_json({"ok": True, "assets": mgr.list_assets(cat_filter)})


# ---------------------------------------------------------------------------
# GET /api/brand-assets/file/<filename>
# ---------------------------------------------------------------------------


@get_prefix("/api/brand-assets/file/", "filename")
def handle_brand_assets_file(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    fname = ctx.path_params.get("filename", "")
    if not fname or ".." in fname or "/" in fname:
        ctx.send_json(_error_payload("Invalid filename"), status=400)
        return
    fpath = Path("data/brand_assets") / fname
    if fpath.is_file():
        ct, _ = mimetypes.guess_type(str(fpath))
        data = fpath.read_bytes()
        ctx.send_response(200)
        ctx.send_header("Content-Type", ct or "application/octet-stream")
        ctx.send_header("Content-Length", str(len(data)))
        ctx.send_header("Cache-Control", "public, max-age=86400")
        ctx.end_headers()
        ctx.wfile.write(data)
    else:
        ctx.send_json(_error_payload("File not found", code="NOT_FOUND"), status=404)


# ---------------------------------------------------------------------------
# PUT /api/publish-queue/<item_id>
# ---------------------------------------------------------------------------


@put_prefix("/api/publish-queue/", "item_id")
def handle_publish_queue_update(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload
    from src.modules.listing.publish_queue import PublishQueue

    item_id = ctx.path_params.get("item_id", "").strip("/")
    if not item_id:
        ctx.send_json(_error_payload("Missing item id"), status=400)
        return
    body = ctx.json_body()
    q = PublishQueue(project_root=ctx.mimic_ops.project_root)
    item = q.update_item(item_id, body)
    if item is None:
        ctx.send_json(_error_payload("Queue item not found"), status=404)
        return
    ctx.send_json({"ok": True, "item": asdict(item)})


# ---------------------------------------------------------------------------
# DELETE /api/publish-queue/<item_id>
# ---------------------------------------------------------------------------


@delete_prefix("/api/publish-queue/", "item_id")
def handle_publish_queue_delete(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload
    from src.modules.listing.publish_queue import PublishQueue

    item_id = ctx.path_params.get("item_id", "").strip("/")
    if not item_id:
        ctx.send_json(_error_payload("Missing item id"), status=400)
        return
    q = PublishQueue(project_root=ctx.mimic_ops.project_root)
    if q.delete_item(item_id):
        ctx.send_json({"ok": True, "message": "Queue item deleted"})
    else:
        ctx.send_json(_error_payload("Queue item not found", code="NOT_FOUND"), status=404)


# ---------------------------------------------------------------------------
# DELETE /api/brand-assets/<asset_id>
# ---------------------------------------------------------------------------


@delete_prefix("/api/brand-assets/", "asset_id")
def handle_brand_assets_delete(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload
    from src.modules.listing.brand_assets import BrandAssetManager

    asset_id = ctx.path_params.get("asset_id", "").strip("/")
    if not asset_id:
        ctx.send_json(_error_payload("Missing asset id"), status=400)
        return
    mgr = BrandAssetManager()
    if mgr.delete_asset(asset_id):
        ctx.send_json({"ok": True, "message": "Asset deleted"})
    else:
        ctx.send_json(_error_payload("Asset not found", code="NOT_FOUND"), status=404)


# ---------------------------------------------------------------------------
# POST /api/brand-assets/upload
# ---------------------------------------------------------------------------


@post("/api/brand-assets/upload")
def handle_brand_assets_upload(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    content_type_header = ctx.headers.get("Content-Type", "")
    if "multipart/form-data" in content_type_header:
        import cgi

        form = cgi.FieldStorage(
            fp=ctx._handler.rfile,
            headers=ctx.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type_header},
        )
        file_item = form["file"] if "file" in form else None
        name = form.getvalue("name", "unnamed")
        cat = form.getvalue("category", "default")
        if file_item is None or not getattr(file_item, "file", None):
            ctx.send_json(_error_payload("Missing file field"), status=400)
            return
        file_data = file_item.file.read()
        fname = getattr(file_item, "filename", "") or "upload.png"
        ext = fname.rsplit(".", 1)[-1] if "." in fname else "png"
    else:
        import base64

        body = ctx.json_body()
        b64 = body.get("file_data", "")
        file_data = base64.b64decode(b64) if b64 else b""
        name = body.get("name", "unnamed")
        cat = body.get("category", "default")
        ext = body.get("file_ext", "png")
        if not file_data:
            ctx.send_json(_error_payload("Missing file_data"), status=400)
            return

    from src.modules.listing.brand_assets import BrandAssetManager

    mgr = BrandAssetManager()
    try:
        asset = mgr.add_asset(name, cat, file_data, ext)
        ctx.send_json({"ok": True, "asset": asset})
    except ValueError as ve:
        ctx.send_json(_error_payload(str(ve)), status=400)


# ---------------------------------------------------------------------------
# POST /api/listing/preview
# ---------------------------------------------------------------------------


@post("/api/listing/preview")
def handle_listing_preview(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx._handler._handle_listing_preview(body)
    ctx.send_json(payload, status=200 if payload.get("ok") else 400)


# ---------------------------------------------------------------------------
# POST /api/listing/publish
# ---------------------------------------------------------------------------


@post("/api/listing/publish")
def handle_listing_publish(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx._handler._handle_listing_publish(body)
    ctx.send_json(payload, status=200 if payload.get("ok") else 400)


# ---------------------------------------------------------------------------
# POST /api/publish-queue/generate
# ---------------------------------------------------------------------------


@post("/api/publish-queue/generate")
def handle_publish_queue_generate(ctx: RouteContext) -> None:
    from src.dashboard.config_service import read_system_config as _read_system_config
    from src.modules.listing.publish_queue import PublishQueue

    body = ctx.json_body()
    q = PublishQueue(project_root=ctx.mimic_ops.project_root)

    categories = body.get("categories")
    if not categories:
        cat = body.get("category")
        categories = [cat] if cat else None

    ap_cfg = _read_system_config().get("auto_publish", {})
    user_schedule = {}
    for k in (
        "cold_start_days",
        "cold_start_daily_count",
        "steady_replace_count",
        "max_active_listings",
        "steady_replace_metric",
    ):
        if k in ap_cfg:
            user_schedule[k] = ap_cfg[k]
    items = _run_async(
        q.generate_daily_queue(categories=categories, user_schedule=user_schedule if user_schedule else None)
    )
    ctx.send_json({"ok": True, "items": [asdict(it) for it in items]})


# ---------------------------------------------------------------------------
# POST /api/publish-queue/<item_id>/regenerate
# ---------------------------------------------------------------------------


@post_prefix("/api/publish-queue/", "sub_path")
def handle_publish_queue_post_actions(ctx: RouteContext) -> None:
    """Handle POST actions on publish queue items: regenerate, publish, publish-batch."""
    from src.dashboard_server import _error_payload
    from src.modules.listing.publish_queue import PublishQueue

    sub = ctx.path_params.get("sub_path", "")

    # /api/publish-queue/publish-batch
    if sub == "publish-batch":
        body = ctx.json_body()
        q = PublishQueue(project_root=ctx.mimic_ops.project_root)
        item_ids = body.get("item_ids", [])
        interval = body.get("interval_seconds", 30)
        publish_cfg = ctx._handler._build_publish_config()
        results = _run_async(q.publish_batch(item_ids, interval_seconds=interval, config=publish_cfg))
        ctx.send_json({"ok": True, "results": results})
        return

    # /api/publish-queue/<item_id>/regenerate
    if sub.endswith("/regenerate"):
        item_id = sub.replace("/regenerate", "")
        q = PublishQueue(project_root=ctx.mimic_ops.project_root)
        item = _run_async(q.regenerate_images(item_id))
        if item is None:
            ctx.send_json(_error_payload("Queue item not found"), status=404)
            return
        ctx.send_json({"ok": True, "item": asdict(item)})
        return

    # /api/publish-queue/<item_id>/publish
    if sub.endswith("/publish"):
        item_id = sub.replace("/publish", "")
        q = PublishQueue(project_root=ctx.mimic_ops.project_root)
        publish_cfg = ctx._handler._build_publish_config()
        result = _run_async(q.publish_item(item_id, config=publish_cfg))
        ctx.send_json(result, status=200 if result.get("ok") else 400)
        return

    ctx.send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
