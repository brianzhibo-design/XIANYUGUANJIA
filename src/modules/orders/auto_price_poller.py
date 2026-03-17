"""定时轮询待付款订单并自动匹配报价改价。

不依赖公网回调地址，通过定时调用闲管家 API 查询
order_status=11 的订单，匹配 QuoteLedger 中的报价记录后自动改价。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_POLL_INTERVAL_DEFAULT = 45
_MAX_QUOTE_AGE_DEFAULT = 7200
_PROCESSED_CACHE_TTL = 3600


_instance: AutoPricePoller | None = None


def get_price_poller() -> AutoPricePoller | None:
    """Return the running poller singleton, if any."""
    return _instance


def set_price_poller(poller: AutoPricePoller | None) -> None:
    global _instance
    _instance = poller


class AutoPricePoller:
    """Background poller: queries pending-payment orders and auto-modifies price."""

    def __init__(self, *, get_config_fn, interval: int = _POLL_INTERVAL_DEFAULT) -> None:
        self._get_config = get_config_fn
        self._interval = max(interval, 10)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._processed: dict[str, float] = {}
        self._reminded: dict[str, float] = {}
        self._trigger_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="auto-price-poller")
        self._thread.start()
        logger.info("AutoPricePoller started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        self._trigger_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("AutoPricePoller stopped")

    def trigger_now(self) -> None:
        """Wake up the poller for an immediate poll cycle (e.g. from chat trigger)."""
        self._trigger_event.set()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                sys_cfg = self._get_config()
                apm_cfg = sys_cfg.get("auto_price_modify", {})
                remind_cfg = sys_cfg.get("order_reminder", {})
                orders = []

                if apm_cfg.get("enabled") or remind_cfg.get("auto_remind_enabled"):
                    orders = self._fetch_pending_orders()

                if apm_cfg.get("enabled") and orders:
                    self._run_auto_price(orders, apm_cfg)

                if remind_cfg.get("auto_remind_enabled") and orders:
                    self._run_auto_remind(orders, remind_cfg)

                self._evict_stale_cache()
            except Exception:
                logger.error("AutoPricePoller: unexpected error in poll cycle", exc_info=True)

            self._trigger_event.clear()
            self._trigger_event.wait(timeout=self._interval)

    def _build_client(self):
        from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

        sys_cfg = self._get_config()
        xgj = sys_cfg.get("xianguanjia", {})
        app_key = str(xgj.get("app_key", "")).strip()
        app_secret = str(xgj.get("app_secret", "")).strip()
        if not app_key or not app_secret:
            return None
        return OpenPlatformClient(
            base_url=str(xgj.get("base_url", "https://open.goofish.pro")).strip(),
            app_key=app_key,
            app_secret=app_secret,
            timeout=float(xgj.get("timeout", 30.0)),
            mode=str(xgj.get("mode", "self_developed")).strip() or "self_developed",
            seller_id=str(xgj.get("seller_id", "")).strip(),
        )

    def _fetch_pending_orders(self) -> list[dict]:
        client = self._build_client()
        if not client:
            return []
        try:
            resp = client.list_orders({"order_status": 11, "page_no": 1, "page_size": 50})
        except Exception:
            logger.error("AutoPricePoller: failed to list orders", exc_info=True)
            return []
        if not resp.ok:
            logger.warning("AutoPricePoller: list_orders failed: %s", resp.error_message)
            return []
        data = resp.data
        orders = []
        if isinstance(data, dict):
            orders = data.get("list") or data.get("data", {}).get("list") or []
        elif isinstance(data, list):
            orders = data
        return [o for o in orders if isinstance(o, dict)]

    def _run_auto_price(self, orders: list[dict], apm_cfg: dict[str, Any]) -> None:
        client = self._build_client()
        if not client:
            return
        logger.debug("AutoPricePoller: found %d pending-payment orders", len(orders))
        for order in orders:
            order_no = str(order.get("order_no", "")).strip()
            if not order_no or order_no in self._processed:
                continue
            self._process_order(client, order_no, order, apm_cfg)

    def _process_order(self, client, order_no: str, order_summary: dict, apm_cfg: dict) -> None:
        from src.modules.quote.ledger import get_quote_ledger

        buyer_nick = str(order_summary.get("buyer_nick", "")).strip()
        buyer_eid = str(order_summary.get("buyer_eid", "")).strip()
        goods = order_summary.get("goods") or {}
        item_id = str(goods.get("item_id", "")).strip()
        total_amount = 0
        try:
            total_amount = int(order_summary.get("total_amount", 0))
        except (ValueError, TypeError):
            pass

        if not buyer_nick:
            try:
                detail_resp = client.get_order_detail({"order_no": order_no})
                if detail_resp.ok and isinstance(detail_resp.data, dict):
                    detail = detail_resp.data
                    buyer_nick = str(detail.get("buyer_nick", "")).strip()
                    if not buyer_eid:
                        buyer_eid = str(detail.get("buyer_eid", "")).strip()
                    if not goods:
                        goods = detail.get("goods") or {}
                        item_id = str(goods.get("item_id", "")).strip()
                    if not total_amount:
                        total_amount = int(detail.get("total_amount", 0))
            except Exception:
                logger.debug("AutoPricePoller: failed to get detail for %s", order_no)

        if not buyer_nick and not buyer_eid:
            logger.debug("AutoPricePoller: no buyer_nick/buyer_eid for order %s, skipping", order_no)
            return

        max_age = int(apm_cfg.get("max_quote_age_seconds", _MAX_QUOTE_AGE_DEFAULT))
        ledger = get_quote_ledger()
        quote = ledger.find_by_buyer(
            buyer_nick, item_id=item_id, max_age_seconds=max_age,
            sender_user_id=buyer_eid,
        )

        if not quote:
            fallback = apm_cfg.get("fallback_action", "skip")
            if fallback == "use_listing_price":
                logger.info(
                    "AutoPricePoller: no quote for buyer=%s order=%s, "
                    "fallback=use_listing_price — accepting at current price",
                    buyer_nick, order_no,
                )
                self._processed[order_no] = time.time()
                return
            logger.debug("AutoPricePoller: no quote for buyer=%s order=%s, fallback=%s", buyer_nick, order_no, fallback)
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
            logger.debug("AutoPricePoller: no valid fee in quote for order=%s", order_no)
            return

        target_price_cents = int(round(float(target_fee) * 100))
        express_fee_cents = int(float(apm_cfg.get("default_express_fee", 0)) * 100)

        if target_price_cents == total_amount and total_amount > 0:
            logger.info("AutoPricePoller: price already correct for order=%s", order_no)
            self._processed[order_no] = time.time()
            return

        try:
            modify_resp = client.modify_order_price({
                "order_no": order_no,
                "order_price": target_price_cents,
                "express_fee": express_fee_cents,
            })
            if modify_resp.ok:
                logger.info(
                    "AutoPricePoller: SUCCESS order=%s from=%d to=%d (express=%d)",
                    order_no, total_amount, target_price_cents, express_fee_cents,
                )
                self._processed[order_no] = time.time()
            else:
                logger.warning(
                    "AutoPricePoller: FAILED order=%s error=%s",
                    order_no, modify_resp.error_message,
                )
        except Exception:
            logger.error("AutoPricePoller: modify_order_price error for order=%s", order_no, exc_info=True)

    def _evict_stale_cache(self) -> None:
        cutoff = time.time() - _PROCESSED_CACHE_TTL
        stale = [k for k, t in self._processed.items() if t < cutoff]
        for k in stale:
            del self._processed[k]
        stale_r = [k for k, t in self._reminded.items() if t < cutoff]
        for k in stale_r:
            del self._reminded[k]

    def _run_auto_remind(self, orders: list[dict], remind_cfg: dict[str, Any]) -> None:
        delay_minutes = int(remind_cfg.get("auto_remind_delay_minutes", 5))
        now = time.time()

        for order in orders:
            order_no = str(order.get("order_no", "")).strip()
            if not order_no or order_no in self._reminded:
                continue

            order_time = 0
            try:
                order_time = int(order.get("order_time", 0))
            except (ValueError, TypeError):
                pass
            if order_time and (now - order_time) < delay_minutes * 60:
                continue

            buyer_nick = str(order.get("buyer_nick", "")).strip()
            session_id = self._resolve_session_for_remind(order_no, buyer_nick)
            if not session_id:
                logger.debug("AutoRemind: no session_id for order=%s buyer=%s", order_no, buyer_nick)
                continue

            try:
                from src.modules.followup.service import FollowUpEngine

                engine = FollowUpEngine.from_system_config()
                if not getattr(engine, "_reminder_enabled", True):
                    continue

                result = engine.process_unpaid_order(
                    session_id=session_id,
                    order_id=order_no,
                )
                if not result.get("eligible"):
                    self._reminded[order_no] = now
                    continue

                template_text = result.get("template_text", "")
                if not template_text:
                    continue

                import asyncio
                from src.modules.messages.service import MessagesService
                from src.core.config import get_config

                msgs_cfg = {}
                try:
                    msgs_cfg = get_config().messages
                except Exception:
                    pass
                svc = MessagesService(msgs_cfg)
                loop = asyncio.new_event_loop()
                try:
                    sent = loop.run_until_complete(svc.reply_to_session(session_id, template_text))
                finally:
                    loop.close()

                if sent:
                    logger.info("AutoRemind: sent reminder for order=%s buyer=%s", order_no, buyer_nick)
                    self._reminded[order_no] = now
                else:
                    logger.warning("AutoRemind: send failed for order=%s", order_no)
            except Exception:
                logger.error("AutoRemind: error for order=%s", order_no, exc_info=True)

    def _resolve_session_for_remind(self, order_no: str, buyer_nick: str) -> str:
        """Find session_id for a given order, using QuoteLedger and ws_live."""
        if buyer_nick:
            try:
                from src.modules.quote.ledger import get_quote_ledger

                quote = get_quote_ledger().find_by_buyer(buyer_nick)
                if quote and str(quote.get("session_id", "")).strip():
                    return str(quote["session_id"]).strip()
            except Exception:
                pass

            try:
                from src.modules.messages.ws_live import get_session_by_buyer_nick

                sid = get_session_by_buyer_nick(buyer_nick)
                if sid:
                    return sid
            except Exception:
                pass

        return ""
