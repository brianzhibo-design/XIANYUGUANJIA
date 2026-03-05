"""闲管家签名与验签工具（开放平台/虚拟货源双口径）。"""

from __future__ import annotations

import hashlib
import hmac

__all__ = [
    "sign_open_platform_request",
    "sign_virtual_supply_request",
    "verify_open_platform_callback_signature",
    "verify_virtual_supply_callback_signature",
]


def _md5_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.md5(data).hexdigest()


def _body_md5(body: str | bytes | None) -> str:
    if body is None:
        payload = ""
    else:
        payload = body
    return _md5_hex(payload)


def sign_open_platform_request(
    *,
    app_key: str,
    app_secret: str,
    timestamp: str | int,
    body: str | bytes | None,
    seller_id: str | None = None,
) -> str:
    """开放平台请求签名（沿用现有实现口径，无分隔符拼接）。"""
    parts = [str(app_key), _body_md5(body), str(timestamp)]
    if seller_id:
        parts.append(str(seller_id))
    parts.append(str(app_secret))
    return _md5_hex("".join(parts))


def sign_virtual_supply_request(
    *,
    app_id: str | int,
    app_secret: str,
    mch_id: str | int,
    mch_secret: str,
    timestamp: str | int,
    body: str | bytes | None,
) -> str:
    """虚拟货源请求签名（按接入说明逗号拼接规则）。"""
    plain = ",".join(
        [
            str(app_id),
            str(app_secret),
            _body_md5(body),
            str(timestamp),
            str(mch_id),
            str(mch_secret),
        ]
    )
    return _md5_hex(plain)


def verify_open_platform_callback_signature(
    *,
    app_key: str,
    app_secret: str,
    timestamp: str | int,
    sign: str,
    body: str | bytes | None,
    seller_id: str | None = None,
) -> bool:
    """校验开放平台回调签名。"""
    expected = sign_open_platform_request(
        app_key=app_key,
        app_secret=app_secret,
        timestamp=timestamp,
        body=body,
        seller_id=seller_id,
    )
    return hmac.compare_digest(expected, str(sign).strip().lower())


def verify_virtual_supply_callback_signature(
    *,
    app_id: str | int,
    app_secret: str,
    mch_id: str | int,
    mch_secret: str,
    timestamp: str | int,
    sign: str,
    body: str | bytes | None,
) -> bool:
    """校验虚拟货源回调签名。"""
    expected = sign_virtual_supply_request(
        app_id=app_id,
        app_secret=app_secret,
        mch_id=mch_id,
        mch_secret=mch_secret,
        timestamp=timestamp,
        body=body,
    )
    return hmac.compare_digest(expected, str(sign).strip().lower())
