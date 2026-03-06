from __future__ import annotations

from typing import Any

# 目标状态词（virtual_goods 模块内统一语义）
VG_ORDER_STATUS_PENDING_PAYMENT = "pending_payment"
VG_ORDER_STATUS_PAID_WAITING_DELIVERY = "paid_waiting_delivery"
VG_ORDER_STATUS_DELIVERED = "delivered"
VG_ORDER_STATUS_DELIVERY_FAILED = "delivery_failed"
VG_ORDER_STATUS_REFUND_PENDING = "refund_pending"
VG_ORDER_STATUS_REFUNDED = "refunded"
VG_ORDER_STATUS_CLOSED = "closed"

ORDER_STATUS_VALUES = {
    VG_ORDER_STATUS_PENDING_PAYMENT,
    VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
    VG_ORDER_STATUS_DELIVERED,
    VG_ORDER_STATUS_DELIVERY_FAILED,
    VG_ORDER_STATUS_REFUND_PENDING,
    VG_ORDER_STATUS_REFUNDED,
    VG_ORDER_STATUS_CLOSED,
}

# 与旧 orders 模块状态解耦：显式映射层（禁止直接沿用旧词）
LEGACY_ORDER_STATUS_MAP = {
    "pending": VG_ORDER_STATUS_PENDING_PAYMENT,
    "paid": VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
    "processing": VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
    "shipping": VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
    "completed": VG_ORDER_STATUS_DELIVERED,
    "after_sales": VG_ORDER_STATUS_REFUND_PENDING,
    "closed": VG_ORDER_STATUS_CLOSED,
}

# 闲鱼开放平台常见状态编码映射到 virtual_goods 目标状态
OPEN_PLATFORM_ORDER_STATUS_MAP = {
    11: VG_ORDER_STATUS_PENDING_PAYMENT,
    12: VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
    21: VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
    22: VG_ORDER_STATUS_DELIVERED,
    23: VG_ORDER_STATUS_REFUND_PENDING,
    24: VG_ORDER_STATUS_CLOSED,
}


def normalize_order_status(raw: Any) -> str:
    """将外部/旧模块状态归一到 virtual_goods 目标状态词。"""
    if raw is None:
        raise ValueError("Unsupported virtual_goods order status: None")

    if isinstance(raw, int):
        mapped = OPEN_PLATFORM_ORDER_STATUS_MAP.get(raw)
        if mapped is None:
            raise ValueError(f"Unsupported virtual_goods order status code: {raw}")
        return mapped

    text = str(raw).strip()
    if not text:
        raise ValueError("Unsupported virtual_goods order status: empty")

    lower = text.lower()
    if lower in ORDER_STATUS_VALUES:
        return lower

    if lower in LEGACY_ORDER_STATUS_MAP:
        return LEGACY_ORDER_STATUS_MAP[lower]

    explicit_text_map = {
        "待付款": VG_ORDER_STATUS_PENDING_PAYMENT,
        "已付款": VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
        "待发货": VG_ORDER_STATUS_PAID_WAITING_DELIVERY,
        "已发货": VG_ORDER_STATUS_DELIVERED,
        "已完成": VG_ORDER_STATUS_DELIVERED,
        "发货失败": VG_ORDER_STATUS_DELIVERY_FAILED,
        "退款中": VG_ORDER_STATUS_REFUND_PENDING,
        "售后中": VG_ORDER_STATUS_REFUND_PENDING,
        "已退款": VG_ORDER_STATUS_REFUNDED,
        "已关闭": VG_ORDER_STATUS_CLOSED,
        "已取消": VG_ORDER_STATUS_CLOSED,
    }
    mapped = explicit_text_map.get(text)
    if mapped is not None:
        return mapped

    raise ValueError(f"Unsupported virtual_goods order status: {raw}")
