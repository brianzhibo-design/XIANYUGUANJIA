"""全局系统通知辅助模块 — 飞书 / 企业微信 Webhook 告警。

所有需要发送告警的模块统一调用 ``send_system_notification``，
无需关心底层通知渠道和配置读取逻辑。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from src.core.logger import get_logger

logger = get_logger()

_EVENT_TOGGLE_MAP: dict[str, str] = {
    "cookie_expire": "notify_cookie_expire",
    "cookie_refresh": "notify_cookie_refresh",
    "risk_control": "notify_risk_control",
    "sla_alert": "notify_sla_alert",
    "order_fail": "notify_order_fail",
    "after_sales": "notify_after_sales",
    "ship_fail": "notify_ship_fail",
    "manual_takeover": "notify_manual_takeover",
    "heavy_quote_alert": "notify_heavy_quote",
}

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "system_config.json"


def _load_notify_config() -> dict[str, Any]:
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("notifications", {})
    except Exception:
        pass
    return {}


async def _do_send(cfg: dict[str, Any], text: str) -> None:
    if cfg.get("feishu_enabled") and cfg.get("feishu_webhook"):
        from src.modules.messages.notifications import FeishuNotifier

        ok = await FeishuNotifier(cfg["feishu_webhook"]).send_text(text)
        if ok:
            logger.info("告警通知已发送至飞书")
        else:
            logger.warning("飞书通知发送失败")

    if cfg.get("wechat_enabled") and cfg.get("wechat_webhook"):
        from src.modules.messages.notifications import WeChatNotifier

        ok = await WeChatNotifier(cfg["wechat_webhook"]).send_text(text)
        if ok:
            logger.info("告警通知已发送至企业微信")
        else:
            logger.warning("企业微信通知发送失败")


def send_system_notification(body: str, *, event: str = "") -> None:
    """发送系统告警通知（同步，可从任意线程调用）。

    Args:
        body: 通知正文。
        event: 事件类型键，用于匹配通知配置中的开关。
               如 ``cookie_expire``, ``order_fail``, ``after_sales`` 等。
    """
    cfg = _load_notify_config()
    if not cfg:
        return

    toggle_key = _EVENT_TOGGLE_MAP.get(event, "")
    if toggle_key and not cfg.get(toggle_key, True):
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_do_send(cfg, body))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_do_send(cfg, body))
        except Exception as exc:
            logger.error(f"发送告警通知失败: {exc}")
        finally:
            loop.close()
