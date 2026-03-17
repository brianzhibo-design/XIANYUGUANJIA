"""报价回复组装器 — 多快递报价查询与回复文本生成。

从 MessagesService 中抽取，负责并发查询多家快递报价、
组装用户友好的多快递比价回复、以及持久化报价记录到 QuoteLedger。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.logger import get_logger
from src.modules.quote.geo_resolver import GeoResolver
from src.modules.quote.models import QuoteRequest, QuoteResult

_logger = get_logger()


class QuoteReplyComposer:
    """并发查询多快递报价并组装回复。"""

    def __init__(
        self,
        *,
        quote_engine: Any,
        quote_config: dict[str, Any],
        quote_reply_max_couriers: int = 10,
    ):
        self.quote_engine = quote_engine
        self.quote_config = quote_config
        self.quote_reply_max_couriers = quote_reply_max_couriers
        self.logger = _logger
        self._freight_needs_city = False

    @staticmethod
    def format_eta_days(minutes: int | float | None) -> str:
        try:
            raw = float(minutes or 0)
        except (TypeError, ValueError):
            raw = 0.0
        if raw <= 0:
            return "1天"
        days = max(1.0, raw / 1440.0)
        rounded = round(days, 1)
        if abs(rounded - round(rounded)) < 1e-9:
            return f"{round(rounded)}天"
        return f"{rounded:.1f}天"

    def resolve_candidate_couriers(self, request: QuoteRequest) -> list[str]:
        couriers: list[str] = []
        seen: set[str] = set()

        preferred = self.quote_config.get("preferred_couriers", [])
        if isinstance(preferred, list):
            for item in preferred:
                name = str(item or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                couriers.append(name)

        provider = getattr(self.quote_engine, "cost_table_provider", None)
        repo = getattr(provider, "repo", None)
        if repo is not None:
            try:
                rows = repo.find_candidates(
                    origin=request.origin,
                    destination=request.destination,
                    courier=None,
                    limit=max(24, self.quote_reply_max_couriers * 8),
                    weight=request.weight,
                )
                for row in rows:
                    name = str(getattr(row, "courier", "") or "").strip()
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    couriers.append(name)
            except Exception as exc:
                self.logger.warning("Resolve candidate couriers failed: %s", exc)

        return couriers[: self.quote_reply_max_couriers]

    async def quote_all_couriers(self, request: QuoteRequest) -> list[tuple[str, QuoteResult]]:
        couriers = self.resolve_candidate_couriers(request)
        if not couriers:
            return []

        async def _one(courier_name: str) -> tuple[str, QuoteResult | None]:
            sub_request = QuoteRequest(
                origin=request.origin,
                destination=request.destination,
                weight=request.weight,
                volume=request.volume,
                volume_weight=request.volume_weight,
                service_level=request.service_level,
                courier=courier_name,
                item_type=request.item_type,
                time_window=request.time_window,
                max_dimension_cm=request.max_dimension_cm,
            )
            try:
                result = await self.quote_engine.get_quote(sub_request)
                return courier_name, result
            except Exception:
                return courier_name, None

        pairs = await asyncio.gather(*[_one(name) for name in couriers])
        ok_pairs: list[tuple[str, QuoteResult]] = []
        for courier_name, result in pairs:
            if result is None:
                continue
            ok_pairs.append((courier_name, result))

        self._freight_needs_city = False
        if ok_pairs:
            first_exp = ok_pairs[0][1].explain if isinstance(ok_pairs[0][1].explain, dict) else {}
            billing_w = float(first_exp.get("billing_weight_kg") or request.weight or 0)
            if billing_w < 20:
                ok_pairs = [
                    p for p in ok_pairs
                    if (p[1].explain or {}).get("service_type") != "freight"
                ]
            else:
                geo = GeoResolver()
                if geo.is_province_level(request.origin) or geo.is_province_level(request.destination):
                    ok_pairs = [
                        p for p in ok_pairs
                        if (p[1].explain or {}).get("service_type") != "freight"
                    ]
                    self._freight_needs_city = True

        ok_pairs.sort(key=lambda item: (float(item[1].total_fee), str(item[0])))
        return ok_pairs

    def compose_multi_courier_reply(self, quote_rows: list[tuple[str, QuoteResult]]) -> str:
        if not quote_rows:
            return ""

        first_explain = quote_rows[0][1].explain if isinstance(quote_rows[0][1].explain, dict) else {}
        origin = str(first_explain.get("matched_origin") or first_explain.get("normalized_origin") or "寄件地")
        destination = str(
            first_explain.get("matched_destination") or first_explain.get("normalized_destination") or "收件地"
        )

        actual_w = first_explain.get("actual_weight_kg")
        volume_w = first_explain.get("volume_weight_kg")
        billing_w = first_explain.get("billing_weight_kg")

        lines = [f"亲，{origin} -> {destination} 的报价已为您查好~"]

        if actual_w is not None and billing_w is not None:
            weight_parts: list[str] = [f"实际重量 {float(actual_w):.1f}kg"]
            if volume_w and float(volume_w) > 0:
                weight_parts.append(f"体积重 {float(volume_w):.1f}kg")
            weight_parts.append(f"按 {float(billing_w):.1f}kg 计费")
            lines.append(" | ".join(weight_parts))

        def _format_courier_line(index: int, courier_name: str, result: QuoteResult) -> str:
            exp = result.explain if isinstance(result.explain, dict) else {}
            bw = float(exp.get("billing_weight_kg") or billing_w or 0)
            base_w = float(exp.get("base_weight", 1.0))
            extra_w = max(0.0, bw - base_w)
            xianyu_extra = exp.get("xianyu_extra")
            price_str = f"{float(result.total_fee):.2f}元"
            if xianyu_extra is not None and extra_w > 0:
                if base_w > 1:
                    price_str += f"（首重{base_w:.0f}kg {float(result.base_fee):.2f} + 续重{extra_w:.1f}kg×{float(xianyu_extra):.2f}）"
                else:
                    price_str += f"（首重{float(result.base_fee):.2f} + 续重{extra_w:.1f}kg×{float(xianyu_extra):.2f}）"
            elif extra_w > 0:
                first_cost = exp.get("cost_first")
                extra_cost = exp.get("cost_extra")
                if first_cost is not None and extra_cost is not None:
                    price_str += f"（首重{float(first_cost):.2f} + 续重{extra_w:.1f}kg×{float(extra_cost):.2f}）"
            return f"{index}. {courier_name}：{price_str}"

        express_rows = [(n, r) for n, r in quote_rows if (r.explain or {}).get("service_type") != "freight"]
        freight_rows = [(n, r) for n, r in quote_rows if (r.explain or {}).get("service_type") == "freight"]

        if express_rows and freight_rows:
            lines.append("快递方案：")
            for i, (name, result) in enumerate(express_rows, 1):
                lines.append(_format_courier_line(i, name, result))

            bw_val = float(billing_w or 0)
            cheapest_freight = freight_rows[0][1]
            unit_price = float(cheapest_freight.total_fee) / bw_val if bw_val > 0 else 0
            freight_header = f"大件快运方案（首重30kg起，低至{unit_price:.1f}元/kg）：" if unit_price > 0 else "大件快运方案（首重30kg起）："
            lines.append(freight_header)
            for i, (name, result) in enumerate(freight_rows, 1):
                lines.append(_format_courier_line(i, name, result))

            cheapest_express_fee = float(express_rows[0][1].total_fee) if express_rows else 0
            cheapest_freight_fee = float(cheapest_freight.total_fee)
            if cheapest_freight_fee < cheapest_express_fee:
                saving = cheapest_express_fee - cheapest_freight_fee
                lines.append(f"推荐：大件快运比快递便宜{saving:.0f}元，越重越划算~")
        else:
            for i, (name, result) in enumerate(quote_rows, 1):
                lines.append(_format_courier_line(i, name, result))

        lines.append("回复\u201c选XX快递\u201d帮您锁定价格哦~")
        lines.append("下单流程：先拍下链接不付款 → 我改价 → 付款后自动发兑换码，到小橙序下单即可~")
        if volume_w and float(volume_w) > 0:
            lines.append("温馨提示：本次已按体积重与实际重量中较大值计费，如实际体积有出入可能需补差价哦~")
        else:
            lines.append("温馨提示：以上按实际重量计算，如包裹体积较大（体积重=长×宽×高/8000），快递按较大值计费，届时可能需补差价哦~")

        for _, r in quote_rows:
            exp = r.explain if isinstance(r.explain, dict) else {}
            if exp.get("oversize_warning"):
                max_dim = exp.get("max_dimension_cm", 0)
                threshold = exp.get("oversize_threshold_cm", 120)
                svc_label = "快运" if exp.get("service_type") == "freight" else "快递"
                lines.append(
                    f"超长提醒：您的包裹最长边约{max_dim:.0f}cm，超出{svc_label}标准（{threshold:.0f}cm），"
                    "物流方可能根据实际情况收取超长费，届时小橙序会自动通知补差价~"
                )
                break

        if self._freight_needs_city:
            lines.append(
                "大件快运报价需精确到市-市才准确，麻烦提供具体城市（如：广州到杭州），帮您查快运价格哦~"
            )

        lines.append("新用户福利：以上为首单优惠价（每个手机号限一次）~ 若已使用过小橙序，则按正常价计费，后续可直接在小橙序下单，无需再走闲鱼，正常价也比自寄便宜5折起~")
        return "\n".join(lines)

    def persist_to_ledger(
        self,
        *,
        session_id: str,
        peer_name: str,
        sender_user_id: str,
        item_id: str,
        quote_meta: dict[str, Any],
        get_context: Any = None,
    ) -> None:
        """Write successful quote to persistent QuoteLedger for cross-process lookup."""
        try:
            context = get_context(session_id) if get_context else {}
            quote_rows = context.get("last_quote_rows") or []
            if not quote_rows:
                all_couriers = quote_meta.get("quote_all_couriers")
                if isinstance(all_couriers, list):
                    quote_rows = [
                        {"courier": c.get("courier", ""), "total_fee": c.get("total_fee", 0)} for c in all_couriers
                    ]
                else:
                    qr = quote_meta.get("quote_result", {})
                    if qr:
                        quote_rows = [{"courier": qr.get("selected_courier", ""), "total_fee": qr.get("total_fee", 0)}]

            if not quote_rows:
                return

            from src.modules.quote.ledger import get_quote_ledger

            ledger = get_quote_ledger()
            ledger.record_quote(
                session_id=session_id,
                peer_name=peer_name,
                sender_user_id=sender_user_id,
                item_id=item_id,
                origin=context.get("origin", ""),
                destination=context.get("destination", ""),
                weight=context.get("weight"),
                courier_choice=context.get("courier_choice", ""),
                quote_rows=quote_rows,
            )
        except Exception:
            self.logger.debug("Failed to persist quote to ledger", exc_info=True)
