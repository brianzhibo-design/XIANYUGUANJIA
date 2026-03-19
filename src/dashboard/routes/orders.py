"""Order, XGJ integration, and virtual goods routes."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.dashboard.router import RouteContext, get, post


# ---------------------------------------------------------------------------
# GET /api/virtual-goods/metrics
# ---------------------------------------------------------------------------


@get("/api/virtual-goods/metrics")
def handle_virtual_goods_metrics(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    payload: dict[str, Any]
    metrics_query = getattr(ctx.mimic_ops, "get_virtual_goods_metrics", None)
    if callable(metrics_query):
        result = metrics_query()
        payload = result if isinstance(result, dict) else _error_payload("virtual_goods metrics payload invalid")
    else:
        aggregate_query = getattr(ctx.mimic_ops, "get_dashboard_readonly_aggregate", None)
        aggregate = aggregate_query() if callable(aggregate_query) else None
        if isinstance(aggregate, dict):
            payload = {
                "success": bool(aggregate.get("success")),
                "module": "virtual_goods",
                "readonly": True,
                "service_response": aggregate.get("service_response", {}),
                "dashboard_panels": aggregate.get("sections", {}),
                "generated_at": aggregate.get("generated_at", ""),
            }
            if not payload["success"]:
                payload = aggregate
        else:
            payload = _error_payload("virtual_goods metrics endpoint unavailable", code="VG_QUERY_NOT_AVAILABLE")
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# GET /api/virtual-goods/inspect-order
# ---------------------------------------------------------------------------


@get("/api/virtual-goods/inspect-order")
def handle_virtual_goods_inspect_order_get(ctx: RouteContext) -> None:
    order_id = ctx.query_str("order_id") or ctx.query_str("xianyu_order_id")
    payload = ctx.mimic_ops.inspect_virtual_goods_order(order_id)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/orders/remind
# ---------------------------------------------------------------------------


@post("/api/orders/remind")
def handle_orders_remind(ctx: RouteContext) -> None:
    from src.dashboard_server import _error_payload

    body = ctx.json_body()
    order_id = str(body.get("order_no") or body.get("order_id") or "").strip()
    session_id = str(body.get("session_id", "")).strip()
    if not order_id:
        ctx.send_json(_error_payload("Missing order_no"), status=400)
        return

    try:
        from src.modules.followup.service import FollowUpEngine

        engine = FollowUpEngine.from_system_config()
    except Exception as init_err:
        ctx.send_json({"ok": False, "error": f"催单引擎初始化失败: {init_err}", "reason": "engine_init_error"})
        return

    if not getattr(engine, "_reminder_enabled", True):
        ctx.send_json({"ok": False, "error": "催单功能未启用", "reason": "disabled"})
        return

    if not session_id:
        session_id = ctx.mimic_ops._resolve_session_id_for_order(order_id)

    use_session = session_id or order_id
    try:
        result = engine.process_unpaid_order(
            session_id=use_session,
            order_id=order_id,
            force=True,
        )
    except Exception as proc_err:
        ctx.send_json({"ok": False, "error": f"催单处理失败: {proc_err}", "reason": "process_error"})
        return

    if result.get("eligible") and session_id:
        template_text = result.get("template_text", "")
        if template_text:
            try:
                import asyncio
                from src.modules.messages.service import MessagesService

                msgs_cfg = {}
                try:
                    from src.core.config import get_config as _get_config

                    msgs_cfg = _get_config().messages
                except Exception:
                    pass
                svc = MessagesService(msgs_cfg)
                loop = asyncio.new_event_loop()
                sent = loop.run_until_complete(svc.reply_to_session(session_id, template_text))
                loop.close()
                result["message_sent"] = sent
            except Exception as send_err:
                result["message_sent"] = False
                result["send_error"] = str(send_err)
    elif result.get("eligible") and not session_id:
        result["message_sent"] = False
        result["send_note"] = "no_session_id_resolved"

    ctx.send_json({"ok": True, **result})


# ---------------------------------------------------------------------------
# POST /api/xgj/settings
# ---------------------------------------------------------------------------


@post("/api/xgj/settings")
def handle_xgj_settings(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.save_xianguanjia_settings(body)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/xgj/retry-price
# ---------------------------------------------------------------------------


@post("/api/xgj/retry-price")
def handle_xgj_retry_price(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.retry_xianguanjia_price(body)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/xgj/retry-ship  &  POST /api/orders/retry (alias)
# ---------------------------------------------------------------------------


@post("/api/xgj/retry-ship")
def handle_xgj_retry_ship(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.retry_xianguanjia_delivery(body)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


@post("/api/orders/retry")
def handle_orders_retry(ctx: RouteContext) -> None:
    """前端兼容别名 — 委托到 /api/xgj/retry-ship 处理。"""
    handle_xgj_retry_ship(ctx)


# ---------------------------------------------------------------------------
# POST /api/orders/callback
# ---------------------------------------------------------------------------


@post("/api/orders/callback")
def handle_orders_callback(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.handle_order_callback(body)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/virtual-goods/inspect-order
# ---------------------------------------------------------------------------


@post("/api/virtual-goods/inspect-order")
def handle_virtual_goods_inspect_order_post(ctx: RouteContext) -> None:
    body = ctx.json_body()
    order_id = str(body.get("order_id") or body.get("xianyu_order_id") or "").strip()
    payload = ctx.mimic_ops.inspect_virtual_goods_order(order_id)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/xgj/test-connection
# ---------------------------------------------------------------------------


@post("/api/xgj/test-connection")
def handle_xgj_test_connection(ctx: RouteContext) -> None:
    from src.dashboard.mimic_ops import _test_xgj_connection

    body = ctx.json_body()
    app_key = str(body.get("app_key", ""))
    app_secret = str(body.get("app_secret", ""))
    base_url = str(body.get("base_url", "") or "https://open.goofish.pro")
    mode = str(body.get("mode", "self_developed"))
    seller_id = str(body.get("seller_id", ""))
    if not app_key or not app_secret:
        ctx.send_json({"ok": False, "message": "AppKey 或 AppSecret 未填写"})
        return
    try:
        info = _test_xgj_connection(
            app_key=app_key,
            app_secret=app_secret,
            base_url=base_url,
            mode=mode,
            seller_id=seller_id,
        )
        ctx.send_json(info)
    except Exception as exc:
        ctx.send_json({"ok": False, "message": f"检查异常: {type(exc).__name__}: {exc}"})


# ---------------------------------------------------------------------------
# POST /api/xgj/proxy
# ---------------------------------------------------------------------------


@post("/api/xgj/proxy")
def handle_xgj_proxy(ctx: RouteContext) -> None:
    import logging
    from src.dashboard.config_service import read_system_config as _read_system_config

    logger = logging.getLogger(__name__)
    body = ctx.json_body()
    api_path = str(body.get("apiPath") or body.get("path") or "")
    req_body = body.get("body") or body.get("payload") or {}
    if not api_path or not api_path.startswith("/api/open/"):
        ctx.send_json({"error": "Invalid apiPath"}, status=400)
        return
    cfg = _read_system_config()
    xgj = cfg.get("xianguanjia", {})
    app_key = str(xgj.get("app_key", ""))
    app_secret = str(xgj.get("app_secret", ""))
    base_url = str(xgj.get("base_url", "") or "https://open.goofish.pro")
    mode = str(xgj.get("mode", "self_developed"))
    seller_id = str(xgj.get("seller_id", ""))
    if not app_key or not app_secret:
        ctx.send_json({"ok": False, "error": "闲管家 API 未配置，请在设置中配置 AppKey 和 AppSecret"}, status=400)
        return
    payload_str = json.dumps(req_body, ensure_ascii=False)
    ts = str(int(time.time()))
    from src.integrations.xianguanjia.signing import sign_open_platform_request, sign_business_request

    if mode == "business" and seller_id:
        sign = sign_business_request(
            app_key=app_key, app_secret=app_secret, seller_id=seller_id, timestamp=ts, body=payload_str
        )
    else:
        sign = sign_open_platform_request(app_key=app_key, app_secret=app_secret, timestamp=ts, body=payload_str)
    try:
        import httpx

        url = f"{base_url}{api_path}"
        with httpx.Client(timeout=15.0) as hc:
            resp = hc.post(
                url,
                params={"appid": app_key, "timestamp": ts, "sign": sign},
                content=payload_str,
                headers={"Content-Type": "application/json"},
            )
        resp_data = resp.json()

        if api_path == "/api/open/product/list":
            from src.dashboard_server import DashboardHandler

            DashboardHandler._enrich_product_images(resp_data, base_url, app_key, app_secret, mode, seller_id)

        ctx.send_json({"ok": True, "data": resp_data})
    except Exception as exc:
        logger.error("XGJ proxy error: %s", exc)
        ctx.send_json({"ok": False, "error": str(exc)}, status=500)


# ---------------------------------------------------------------------------
# POST /api/auto-price/diagnose
# ---------------------------------------------------------------------------


@post("/api/auto-price/diagnose")
def handle_auto_price_diagnose(ctx: RouteContext) -> None:
    """Full diagnostic of the auto-pricing pipeline without executing modifications."""
    import logging
    from src.dashboard.config_service import read_system_config as _read_system_config
    from src.modules.orders.auto_price_poller import get_price_poller

    logger = logging.getLogger(__name__)
    cfg = _read_system_config()
    apm_cfg = cfg.get("auto_price_modify", {})
    xgj = cfg.get("xianguanjia", {})

    poller = get_price_poller()
    result: dict = {
        "config_enabled": bool(apm_cfg.get("enabled")),
        "poller_running": poller is not None and poller._thread is not None and poller._thread.is_alive()
        if poller
        else False,
        "poller_interval": int(apm_cfg.get("poll_interval_seconds", 15)),
        "max_quote_age_seconds": int(apm_cfg.get("max_quote_age_seconds", 7200)),
        "fallback_action": apm_cfg.get("fallback_action", "skip"),
        "xgj_configured": bool(xgj.get("app_key") and xgj.get("app_secret")),
        "pending_orders": [],
        "api_connection_ok": False,
        "api_error": None,
    }

    if not result["xgj_configured"]:
        result["api_error"] = "闲管家 AppKey/AppSecret 未配置"
        ctx.send_json(result)
        return

    try:
        from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

        client = OpenPlatformClient(
            base_url=str(xgj.get("base_url", "") or "https://open.goofish.pro"),
            app_key=str(xgj.get("app_key", "")),
            app_secret=str(xgj.get("app_secret", "")),
            timeout=float(xgj.get("timeout", 30.0)),
            mode=str(xgj.get("mode", "self_developed")).strip() or "self_developed",
            seller_id=str(xgj.get("seller_id", "")).strip(),
        )
        resp = client.list_orders({"order_status": 11, "page_no": 1, "page_size": 50})
        if not resp.ok:
            result["api_error"] = f"list_orders 失败: {resp.error_message}"
            ctx.send_json(result)
            return
        result["api_connection_ok"] = True

        data = resp.data
        orders = []
        if isinstance(data, dict):
            orders = data.get("list") or data.get("data", {}).get("list") or []
        elif isinstance(data, list):
            orders = data

        from src.modules.quote.ledger import get_quote_ledger

        ledger = get_quote_ledger()
        max_age = int(apm_cfg.get("max_quote_age_seconds", 7200))
        processed_set = set(poller._processed.keys()) if poller else set()

        for order in orders:
            if not isinstance(order, dict):
                continue
            order_no = str(order.get("order_no", "")).strip()
            buyer_nick = str(order.get("buyer_nick", "")).strip()
            buyer_eid = str(order.get("buyer_eid", "")).strip()
            goods = order.get("goods") or {}
            item_id = str(goods.get("item_id", "")).strip()
            total_amount = 0
            try:
                total_amount = int(order.get("total_amount", 0))
            except (ValueError, TypeError):
                pass

            diag: dict = {
                "order_no": order_no,
                "buyer_nick": buyer_nick,
                "buyer_eid": buyer_eid,
                "item_id": item_id,
                "total_amount_cents": total_amount,
                "already_processed": order_no in processed_set,
                "quote_found": False,
                "quote_id": None,
                "courier_choice": None,
                "target_fee": None,
                "target_price_cents": None,
                "would_modify": False,
                "reason": "",
            }

            if order_no in processed_set:
                diag["reason"] = "already_processed_in_cache"
                result["pending_orders"].append(diag)
                continue

            quote = ledger.find_by_buyer(buyer_nick, item_id=item_id, max_age_seconds=max_age, sender_user_id=buyer_eid)
            if not quote:
                diag["reason"] = "no_quote_in_ledger"
                result["pending_orders"].append(diag)
                continue

            diag["quote_found"] = True
            diag["quote_id"] = quote.get("id")
            diag["courier_choice"] = quote.get("courier_choice", "")
            quote_rows = quote.get("quote_rows", [])

            target_fee = None
            cc = diag["courier_choice"]
            if cc:
                for row in quote_rows:
                    if str(row.get("courier", "")).strip() == cc.strip():
                        target_fee = row.get("total_fee")
                        break
            if target_fee is None and quote_rows:
                fees = [r.get("total_fee", 0) for r in quote_rows if r.get("total_fee")]
                if fees:
                    target_fee = min(fees)

            if target_fee is None:
                diag["reason"] = "no_valid_fee_in_quote_rows"
                result["pending_orders"].append(diag)
                continue

            diag["target_fee"] = target_fee
            target_cents = round(float(target_fee) * 100)
            diag["target_price_cents"] = target_cents

            if target_cents == total_amount and total_amount > 0:
                diag["reason"] = "price_already_correct"
            else:
                diag["would_modify"] = True
                diag["reason"] = f"would_change_from_{total_amount}_to_{target_cents}"
            result["pending_orders"].append(diag)

    except Exception as exc:
        logger.error("auto-price diagnose error: %s", exc, exc_info=True)
        result["api_error"] = str(exc)

    ctx.send_json(result)


# ---------------------------------------------------------------------------
# POST /api/auto-price/test-modify
# ---------------------------------------------------------------------------


@post("/api/auto-price/test-modify")
def handle_auto_price_test_modify(ctx: RouteContext) -> None:
    """Execute auto-price modification for a specific order."""
    import logging
    from src.dashboard.config_service import read_system_config as _read_system_config

    logger = logging.getLogger(__name__)
    body = ctx.json_body()
    order_no = str(body.get("order_no", "")).strip()
    if not order_no:
        ctx.send_json({"ok": False, "error": "Missing order_no"}, status=400)
        return

    cfg = _read_system_config()
    xgj = cfg.get("xianguanjia", {})
    apm_cfg = cfg.get("auto_price_modify", {})

    if not xgj.get("app_key") or not xgj.get("app_secret"):
        ctx.send_json({"ok": False, "error": "闲管家 API 未配置"}, status=400)
        return

    try:
        from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient
        from src.modules.quote.ledger import get_quote_ledger

        client = OpenPlatformClient(
            base_url=str(xgj.get("base_url", "") or "https://open.goofish.pro"),
            app_key=str(xgj.get("app_key", "")),
            app_secret=str(xgj.get("app_secret", "")),
            timeout=float(xgj.get("timeout", 30.0)),
            mode=str(xgj.get("mode", "self_developed")).strip() or "self_developed",
            seller_id=str(xgj.get("seller_id", "")).strip(),
        )

        detail_resp = client.get_order_detail({"order_no": order_no})
        if not detail_resp.ok:
            ctx.send_json({"ok": False, "error": f"获取订单详情失败: {detail_resp.error_message}"})
            return

        detail = detail_resp.data or {}
        buyer_nick = str(detail.get("buyer_nick", ""))
        buyer_eid = str(detail.get("buyer_eid", "")).strip()
        goods = detail.get("goods") or {}
        item_id = str(goods.get("item_id", ""))
        total_amount = int(detail.get("total_amount", 0))

        max_age = int(apm_cfg.get("max_quote_age_seconds", 7200))
        ledger = get_quote_ledger()
        quote = ledger.find_by_buyer(buyer_nick, item_id=item_id, max_age_seconds=max_age, sender_user_id=buyer_eid)

        if not quote:
            ctx.send_json(
                {
                    "ok": False,
                    "error": f"未找到报价记录 (buyer={buyer_nick}, eid={buyer_eid}, item={item_id})",
                    "order_detail": {
                        "buyer_nick": buyer_nick,
                        "buyer_eid": buyer_eid,
                        "item_id": item_id,
                        "total_amount": total_amount,
                    },
                }
            )
            return

        quote_rows = quote.get("quote_rows", [])
        courier_choice = quote.get("courier_choice", "")
        target_fee = None
        if courier_choice:
            for row in quote_rows:
                if str(row.get("courier", "")).strip() == courier_choice.strip():
                    target_fee = row.get("total_fee")
                    break
        if target_fee is None and quote_rows:
            fees = [r.get("total_fee", 0) for r in quote_rows if r.get("total_fee")]
            if fees:
                target_fee = min(fees)

        if target_fee is None:
            ctx.send_json({"ok": False, "error": "报价记录中无有效价格", "quote": quote})
            return

        target_cents = round(float(target_fee) * 100)
        express_fee_cents = int(float(apm_cfg.get("default_express_fee", 0)) * 100)

        if target_cents == total_amount and total_amount > 0:
            ctx.send_json(
                {
                    "ok": True,
                    "modified": False,
                    "reason": "price_already_correct",
                    "total_amount": total_amount,
                    "target_cents": target_cents,
                }
            )
            return

        modify_resp = client.modify_order_price(
            {
                "order_no": order_no,
                "order_price": target_cents,
                "express_fee": express_fee_cents,
            }
        )

        ctx.send_json(
            {
                "ok": modify_resp.ok,
                "modified": modify_resp.ok,
                "order_no": order_no,
                "from_cents": total_amount,
                "to_cents": target_cents,
                "express_fee_cents": express_fee_cents,
                "courier_choice": courier_choice or "(auto-min)",
                "api_response": {
                    "ok": modify_resp.ok,
                    "error_message": modify_resp.error_message if not modify_resp.ok else None,
                    "error_code": modify_resp.error_code if not modify_resp.ok else None,
                },
            }
        )

    except Exception as exc:
        logger.error("auto-price test-modify error: %s", exc, exc_info=True)
        ctx.send_json({"ok": False, "error": str(exc)}, status=500)


# ---------------------------------------------------------------------------
# POST /api/xgj/order/receive, /api/xgj/product/receive  (webhook callbacks)
# ---------------------------------------------------------------------------


@post("/api/xgj/order/receive")
def handle_xgj_order_receive(ctx: RouteContext) -> None:
    _handle_xgj_webhook(ctx)


@post("/api/xgj/product/receive")
def handle_xgj_product_receive(ctx: RouteContext) -> None:
    _handle_xgj_webhook(ctx)


def _handle_xgj_webhook(ctx: RouteContext) -> None:
    """Shared webhook handler for order and product callbacks with signature verification."""
    from src.dashboard.config_service import read_system_config as _read_system_config

    content_len = int(ctx.headers.get("Content-Length", "0"))
    raw_body = ctx._handler.rfile.read(content_len) if content_len > 0 else b""
    body_str = raw_body.decode("utf-8") if raw_body else ""
    cfg = _read_system_config()
    xgj = cfg.get("xianguanjia", {})
    app_key = str(xgj.get("app_key", ""))
    app_secret = str(xgj.get("app_secret", ""))
    if not app_key or not app_secret:
        ctx.send_json({"result": "fail", "msg": "Not configured"}, status=400)
        return

    parsed_url = urlparse(ctx._handler.path)
    qs = parse_qs(parsed_url.query)
    sign_val = qs.get("sign", [""])[0]
    try:
        body_data = json.loads(body_str) if body_str else {}
    except Exception:
        body_data = {}
    ts_val = str(body_data.get("timestamp") or (qs.get("timestamp", [""])[0]))
    now = int(time.time())
    try:
        if abs(now - int(ts_val)) > 300:
            ctx.send_json({"result": "fail", "msg": "Timestamp expired"}, status=400)
            return
    except (ValueError, TypeError):
        ctx.send_json({"result": "fail", "msg": "Invalid timestamp"}, status=400)
        return

    from src.integrations.xianguanjia.signing import verify_open_platform_callback_signature

    if not verify_open_platform_callback_signature(
        app_key=app_key, app_secret=app_secret, timestamp=ts_val, sign=sign_val, body=body_str
    ):
        ctx.send_json({"result": "fail", "msg": "Invalid signature"}, status=401)
        return

    if ctx.path == "/api/xgj/product/receive":
        ctx.mimic_ops.handle_product_callback(body_data)
    else:
        ctx.mimic_ops.handle_order_push(body_data)
    ctx.send_json({"result": "success", "msg": "接收成功"})
