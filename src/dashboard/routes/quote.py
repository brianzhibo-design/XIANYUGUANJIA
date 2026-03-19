"""Quote/pricing routes: route stats, markup rules, templates, import/export."""

from __future__ import annotations

from src.dashboard.router import RouteContext, get, post

# ---------------------------------------------------------------------------
# GET routes
# ---------------------------------------------------------------------------


@get("/api/route-stats")
def handle_route_stats(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.route_stats())


@get("/api/export-routes")
def handle_export_routes(ctx: RouteContext) -> None:
    data, filename = ctx.mimic_ops.export_routes_zip()
    ctx.send_bytes(data=data, content_type="application/zip", download_name=filename)


@get("/api/get-template")
def handle_get_template(ctx: RouteContext) -> None:
    use_default = ctx.query_bool("default")
    ctx.send_json(ctx.mimic_ops.get_template(default=use_default))


@get("/api/get-markup-rules")
def handle_get_markup_rules(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.get_markup_rules())


# ---------------------------------------------------------------------------
# POST routes
# ---------------------------------------------------------------------------


@post("/api/import-routes")
def handle_import_routes(ctx: RouteContext) -> None:
    try:
        files = ctx.multipart_files()
    except Exception as exc:
        ctx.send_json(
            {
                "success": False,
                "error": "Failed to parse upload body. Please retry with xlsx/xls/csv/zip files.",
                "details": str(exc),
            },
            status=400,
        )
        return

    try:
        payload = ctx.mimic_ops.import_route_files(files)
    except Exception as exc:
        ctx.send_json(
            {
                "success": False,
                "error": "Import processing failed.",
                "details": str(exc),
            },
            status=400,
        )
        return

    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/import-markup")
def handle_import_markup(ctx: RouteContext) -> None:
    try:
        files = ctx.multipart_files()
    except Exception as exc:
        ctx.send_json(
            {
                "success": False,
                "error": "Failed to parse upload body. Please retry with markup files.",
                "details": str(exc),
            },
            status=400,
        )
        return

    try:
        payload = ctx.mimic_ops.import_markup_files(files)
    except Exception as exc:
        ctx.send_json(
            {
                "success": False,
                "error": "Import processing failed.",
                "details": str(exc),
            },
            status=400,
        )
        return

    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/save-template")
def handle_save_template(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.save_template(
        weight_template=str(body.get("weight_template") or ""),
        volume_template=str(body.get("volume_template") or ""),
    )
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/save-markup-rules")
def handle_save_markup_rules(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.save_markup_rules(body.get("markup_rules"))
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# 三层定价 API
# ---------------------------------------------------------------------------


@get("/api/get-pricing-config")
def handle_get_pricing_config(ctx: RouteContext) -> None:
    """返回三层定价完整配置（加价表 + 让利表）。"""
    ctx.send_json(ctx.mimic_ops.get_pricing_config())


@get("/api/get-cost-summary")
def handle_get_cost_summary(ctx: RouteContext) -> None:
    """返回成本表概览（只读）。"""
    ctx.send_json(ctx.mimic_ops.get_cost_summary())


@get("/api/query-route-cost")
def handle_query_route_cost(ctx: RouteContext) -> None:
    """查询指定路线的各运力成本。"""
    origin = ctx.query_str("origin")
    destination = ctx.query_str("destination")
    payload = ctx.mimic_ops.query_route_cost(origin, destination)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/save-pricing-config")
def handle_save_pricing_config(ctx: RouteContext) -> None:
    """保存加价表 + 让利表 + 抛比 + 大件运力优先级。"""
    body = ctx.json_body()
    payload = ctx.mimic_ops.save_pricing_config(
        markup_categories=body.get("markup_categories"),
        xianyu_discount=body.get("xianyu_discount"),
        volume_divisor_default=body.get("volume_divisor_default"),
        volume_divisors=body.get("volume_divisors"),
        freight_courier_priority=body.get("freight_courier_priority"),
    )
    ctx.send_json(payload, status=200 if payload.get("success") else 400)
