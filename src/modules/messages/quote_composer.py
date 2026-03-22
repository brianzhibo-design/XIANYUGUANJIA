"""报价回复组装器 — 多快递报价查询与回复文本生成。

从 MessagesService 中抽取，负责并发查询多家快递报价、
组装用户友好的多快递比价回复、以及持久化报价记录到 QuoteLedger。
"""

from __future__ import annotations

import asyncio
import random
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
        self._express_fallback_no_freight = False
        self._freight_only_large_weight = False
        self._low_weight_freight_fallback = False
        self.freight_courier_priority: list[str] = list(quote_config.get("freight_courier_priority") or [])
        self.volume_divisor_default: float = float(quote_config.get("volume_divisor_default") or 8000)

    @staticmethod
    def _is_freight_result(result: QuoteResult) -> bool:
        return (result.explain or {}).get("service_type") == "freight"

    def _is_freight_pair(self, pair: tuple[str, QuoteResult]) -> bool:
        return self._is_freight_result(pair[1])

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
        self._express_fallback_no_freight = False
        self._freight_only_large_weight = False
        self._low_weight_freight_fallback = False

        if not ok_pairs:
            return []

        full_pairs = list(ok_pairs)
        first_exp = ok_pairs[0][1].explain if isinstance(ok_pairs[0][1].explain, dict) else {}
        billing_w = float(first_exp.get("billing_weight_kg") or request.weight or 0)

        freight_below = float(self.quote_config.get("freight_hide_below_kg", 20))
        express_above = float(self.quote_config.get("express_hide_above_kg", 30))
        if freight_below >= express_above:
            self.logger.warning(
                "quote: freight_hide_below_kg (%.1f) >= express_hide_above_kg (%.1f); using 20/30",
                freight_below,
                express_above,
            )
            freight_below, express_above = 20.0, 30.0

        if billing_w < freight_below:
            ok_pairs = [p for p in ok_pairs if not self._is_freight_pair(p)]
        else:
            geo = GeoResolver()
            if geo.is_province_level(request.origin) or geo.is_province_level(request.destination):
                ok_pairs = [p for p in ok_pairs if not self._is_freight_pair(p)]
                self._freight_needs_city = True

        if not ok_pairs:
            ok_pairs = list(full_pairs)
            self._low_weight_freight_fallback = True

        before_high = list(ok_pairs)

        if billing_w > express_above:
            freight_only = [p for p in ok_pairs if self._is_freight_pair(p)]
            if freight_only:
                ok_pairs = freight_only
                self._freight_only_large_weight = True
            else:
                self._express_fallback_no_freight = True

        if not ok_pairs:
            ok_pairs = list(before_high) if before_high else list(full_pairs)
            self._express_fallback_no_freight = True
            self._freight_only_large_weight = False

        ok_pairs.sort(key=lambda item: (float(item[1].total_fee), str(item[0])))
        return ok_pairs

    _HEADER_VARIANTS = [
        "{origin}->{dest} {weight}kg 报价~",
        "亲，{origin}寄{dest} {weight}kg 帮您查好了~",
        "{origin}到{dest} {weight}kg 价格如下~",
    ]
    _PICK_COURIER_VARIANTS = [
        "回复\u201c选XX快递\u201d锁定价格~ 大部分人选1~",
        "看中哪个回复我就行~ 选1性价比最高~",
        "选好快递告诉我一声~ 推荐选1最划算~",
    ]
    _ORDER_GUIDE_VARIANTS = [
        "下单流程：拍下不付款→我改价→付款自动发码→到小程序下单即可~\n首单有优惠，正常价也比自寄便宜5折起~",
        "先拍下别付款，我改完价您再付，自动发兑换码到小程序用~\n首单优惠价，正常价也比自寄便宜5折起~",
        "流程：拍下→我改价→付款出码→小程序下单，很简单~\n首单有优惠哦，正常价也比自寄便宜5折起~",
    ]

    def compose_multi_courier_reply_segments(self, quote_rows: list[tuple[str, QuoteResult]]) -> list[str]:
        """组装多快递报价，返回分段消息列表（每个元素是一条独立消息）。"""
        if not quote_rows:
            return []

        first_explain = quote_rows[0][1].explain if isinstance(quote_rows[0][1].explain, dict) else {}
        origin = str(first_explain.get("matched_origin") or first_explain.get("normalized_origin") or "寄件地")
        destination = str(
            first_explain.get("matched_destination") or first_explain.get("normalized_destination") or "收件地"
        )

        actual_w = first_explain.get("actual_weight_kg")
        volume_w = first_explain.get("volume_weight_kg")
        billing_w = first_explain.get("billing_weight_kg")

        # --- Segment 1: header + price list + pick courier ---
        seg1_lines: list[str] = []
        weight_str = f"{float(billing_w or actual_w or 0):.1f}"
        header = random.choice(self._HEADER_VARIANTS).format(
            origin=origin,
            dest=destination,
            weight=weight_str,
        )
        seg1_lines.append(header)

        if actual_w is not None and billing_w is not None:
            weight_parts: list[str] = [f"实际重量 {float(actual_w):.1f}kg"]
            vol_w_val = float(volume_w or 0)
            if vol_w_val > 0:
                weight_parts.append(f"体积重 {vol_w_val:.1f}kg")
            weight_parts.append(f"按 {float(billing_w):.1f}kg 计费")
            seg1_lines.append(" | ".join(weight_parts))
            # 体积重计费时展示真实抛比公式（配置中 5000/6000/8000 等）
            if vol_w_val > 0 and float(billing_w or 0) >= vol_w_val:
                divisor = first_explain.get("volume_divisor")
                if divisor is not None and float(divisor) > 0:
                    div_int = int(float(divisor))
                    seg1_lines.append(f"体积重公式：长×宽×高(cm)/{div_int}，本次按体积重计费~")

        def _format_courier_line(
            index: int, courier_name: str, result: QuoteResult, *, is_cheapest: bool = False
        ) -> str:
            price_str = f"{float(result.total_fee):.2f}元"
            prefix = "【推荐】" if is_cheapest else ""
            return f"{prefix}{index}. {courier_name}：{price_str}"

        express_rows = [(n, r) for n, r in quote_rows if (r.explain or {}).get("service_type") != "freight"]
        freight_rows = [(n, r) for n, r in quote_rows if (r.explain or {}).get("service_type") == "freight"]

        if freight_rows and self.freight_courier_priority:
            prio = self.freight_courier_priority
            freight_rows.sort(
                key=lambda item: (
                    prio.index(item[0]) if item[0] in prio else len(prio),
                    float(item[1].total_fee),
                ),
            )

        if express_rows and freight_rows:
            seg1_lines.append("快递方案：")
            for i, (name, result) in enumerate(express_rows, 1):
                seg1_lines.append(_format_courier_line(i, name, result, is_cheapest=(i == 1)))

            bw_val = float(billing_w or 0)
            cheapest_freight = freight_rows[0][1]
            unit_price = float(cheapest_freight.total_fee) / bw_val if bw_val > 0 else 0
            freight_header = (
                f"大件快运方案（首重30kg起，低至{unit_price:.1f}元/kg）："
                if unit_price > 0
                else "大件快运方案（首重30kg起）："
            )
            seg1_lines.append(freight_header)
            for i, (name, result) in enumerate(freight_rows, 1):
                seg1_lines.append(_format_courier_line(i, name, result, is_cheapest=(i == 1)))

            cheapest_express_fee = float(express_rows[0][1].total_fee) if express_rows else 0
            cheapest_freight_fee = float(cheapest_freight.total_fee)
            if cheapest_freight_fee < cheapest_express_fee:
                saving = cheapest_express_fee - cheapest_freight_fee
                seg1_lines.append(f"推荐：大件快运比快递便宜{saving:.0f}元，越重越划算~")
        else:
            for i, (name, result) in enumerate(quote_rows, 1):
                seg1_lines.append(_format_courier_line(i, name, result, is_cheapest=(i == 1)))

        seg1_lines.append(random.choice(self._PICK_COURIER_VARIANTS))

        if len(quote_rows) == 1:
            single_courier = quote_rows[0][0]
            _svc = "快运" if self._is_freight_result(quote_rows[0][1]) else "快递"
            seg1_lines.append(f"您这个路线目前 {single_courier} {_svc}最优惠，其他线路暂无报价或价格偏高~")

        segments: list[str] = ["\n".join(seg1_lines)]

        # --- Segment 2: order guide + first-order discount ---
        segments.append(random.choice(self._ORDER_GUIDE_VARIANTS))

        # --- Segment 3 (conditional): tips ---
        tips_lines: list[str] = []
        vol_w_val = float(volume_w or 0)
        actual_w_val = float(actual_w or 0)
        if vol_w_val > 0 and vol_w_val > actual_w_val:
            divisor = first_explain.get("volume_divisor")
            if divisor is not None and float(divisor) > 0:
                div_int = int(float(divisor))
                tips_lines.append(
                    f"温馨提示：本次按体积重计费（长×宽×高/{div_int}={vol_w_val:.1f}kg > 实重{actual_w_val:.1f}kg），"
                    "实际体积有出入可能需补差价~"
                )
            else:
                tips_lines.append("温馨提示：本次按体积重计费，实际体积有出入可能需补差价~")

        for _, r in quote_rows:
            exp = r.explain if isinstance(r.explain, dict) else {}
            if exp.get("oversize_warning"):
                max_dim = exp.get("max_dimension_cm", 0)
                threshold = exp.get("oversize_threshold_cm", 120)
                svc_label = "快运" if exp.get("service_type") == "freight" else "快递"
                tips_lines.append(
                    f"超长提醒：最长边约{max_dim:.0f}cm，超出{svc_label}标准（{threshold:.0f}cm），可能收取超长费~"
                )
                break

        if self._freight_needs_city:
            tips_lines.append("大件快运报价需精确到市-市，麻烦提供具体城市帮您查快运价~")

        cfg = self.quote_config
        if self._express_fallback_no_freight:
            tip_fb = (cfg.get("heavy_freight_express_fallback_tip") or "").strip()
            if not tip_fb:
                tip_fb = "本路线暂无快运参考价，以下为快递估算仅供参考；大件请发长宽高，便于核对体积重与渠道/后台价~"
            tips_lines.append(tip_fb)

        if self._freight_only_large_weight:
            tip_lo = (cfg.get("heavy_freight_only_tip") or "").strip()
            if not tip_lo:
                kg_line = int(float(cfg.get("express_hide_above_kg", 30)))
                tip_lo = (
                    f"超过约{kg_line}kg 按大件快运报价，快递标快不适用；请发长宽高核对体积重，最终以网点/后台核实为准~"
                )
            tips_lines.append(tip_lo)

        if self._low_weight_freight_fallback:
            tips_lines.append("小件以快递为主；若下列含快运参考，请以快递方案优先~")

        if tips_lines:
            segments.append("\n".join(tips_lines))

        return segments

    def compose_multi_courier_reply(self, quote_rows: list[tuple[str, QuoteResult]]) -> str:
        """兼容旧调用：返回所有分段拼接的完整文本。"""
        segments = self.compose_multi_courier_reply_segments(quote_rows)
        return "\n".join(segments)

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
                self.logger.warning(
                    "persist_to_ledger: quote_rows empty, skipping persist (session=%s, peer=%s, meta_keys=%s)",
                    session_id,
                    peer_name,
                    list(quote_meta.keys()),
                )
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
