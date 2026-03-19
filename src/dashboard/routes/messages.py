"""Message-related routes: reply logs, sandbox, notification test, AI test."""

from __future__ import annotations

import asyncio
import time as _time_mod

from src.dashboard.router import RouteContext, get, post

# ---------------------------------------------------------------------------
# GET /api/replies
# ---------------------------------------------------------------------------


@get("/api/replies")
def handle_replies(ctx: RouteContext) -> None:
    ctx.send_json(ctx.mimic_ops.get_replies())


# ---------------------------------------------------------------------------
# POST /api/test-reply
# ---------------------------------------------------------------------------


@post("/api/test-reply")
def handle_test_reply(ctx: RouteContext) -> None:
    body = ctx.json_body()
    payload = ctx.mimic_ops.test_reply(body)
    ctx.send_json(payload, status=200 if payload.get("success") else 400)


# ---------------------------------------------------------------------------
# POST /api/notifications/test
# ---------------------------------------------------------------------------


@post("/api/notifications/test")
def handle_notifications_test(ctx: RouteContext) -> None:
    body = ctx.json_body()
    channel = str(body.get("channel", "")).strip()
    webhook_url = str(body.get("webhook_url", "")).strip()
    if not channel or not webhook_url:
        ctx.send_json({"ok": False, "error": "缺少 channel 或 webhook_url"}, status=400)
        return

    test_msg = "【闲鱼自动化】通知测试\n如果你看到这条消息，说明通知配置成功！"

    async def _send() -> bool:
        if channel == "feishu":
            from src.modules.messages.notifications import FeishuNotifier

            return await FeishuNotifier(webhook_url).send_text(test_msg)
        elif channel == "wechat":
            from src.modules.messages.notifications import WeChatNotifier

            return await WeChatNotifier(webhook_url).send_text(test_msg)
        return False

    loop = asyncio.new_event_loop()
    try:
        ok = loop.run_until_complete(_send())
    finally:
        loop.close()

    if ok:
        ctx.send_json({"ok": True, "message": "测试消息发送成功"})
    else:
        ctx.send_json({"ok": False, "error": "发送失败，请检查 Webhook URL 是否正确"}, status=400)


# ---------------------------------------------------------------------------
# POST /api/ai/test
# ---------------------------------------------------------------------------


@post("/api/ai/test")
def handle_ai_test(ctx: RouteContext) -> None:
    body = ctx.json_body()
    ai_key = str(body.get("api_key") or "").strip()
    ai_base = str(body.get("base_url") or "").strip()
    ai_model = str(body.get("model") or "").strip() or "qwen-plus"
    if not ai_key or not ai_base:
        ctx.send_json({"ok": False, "message": "请填写 API Key 和 API 地址"})
        return
    try:
        t0 = _time_mod.time()
        import httpx

        chat_url = ai_base.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=10.0) as hc:
            resp = hc.post(
                chat_url,
                headers={"Authorization": f"Bearer {ai_key}", "Content-Type": "application/json"},
                json={"model": ai_model, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
            )
        latency = int((_time_mod.time() - t0) * 1000)
        if resp.status_code == 200:
            ctx.send_json({"ok": True, "message": f"连接成功（延迟 {latency}ms）", "latency_ms": latency})
        else:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                pass
            status_msgs = {
                401: "API Key 无效或已过期，请检查后重试",
                403: "API Key 无权访问该模型",
                404: f"模型 {ai_model} 不存在，请检查模型名称",
                429: "请求过于频繁，请稍后再试",
            }
            msg = status_msgs.get(resp.status_code, f"HTTP {resp.status_code}")
            if detail:
                msg += f"（{detail}）"
            ctx.send_json({"ok": False, "message": msg, "latency_ms": latency})
    except Exception as exc:
        ctx.send_json({"ok": False, "message": f"连接异常: {type(exc).__name__}: {exc}"})
