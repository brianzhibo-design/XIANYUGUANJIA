from __future__ import annotations

import httpx

from src.integrations.xianguanjia.errors import (
    XianGuanJiaErrorType,
    XianGuanJiaNonRetryableError,
    XianGuanJiaRetryableError,
    is_retryable_error,
    map_error,
)


def test_map_error_returns_exception_with_metadata_fields() -> None:
    payload = {"code": "E401", "msg": "auth failed"}

    err = map_error(
        error_type=XianGuanJiaErrorType.AUTH_INVALID,
        http_status=401,
        error_code="E401",
        request_id="rid-001",
        raw_payload=payload,
        message="auth failed",
    )

    assert isinstance(err, XianGuanJiaNonRetryableError)
    assert err.error_type == XianGuanJiaErrorType.AUTH_INVALID
    assert err.http_status == 401
    assert err.error_code == "E401"
    assert err.request_id == "rid-001"
    assert err.raw_payload == payload


def test_map_error_unknown_falls_back_to_non_retryable_unknown() -> None:
    err = map_error(error_type="TOTALLY_UNKNOWN_ERROR")

    assert isinstance(err, XianGuanJiaNonRetryableError)
    assert err.error_type == XianGuanJiaErrorType.UNKNOWN


def test_map_error_prefers_exc_normalization_when_exc_and_http_status_both_present() -> None:
    exc = httpx.ConnectError("connect failed")

    err = map_error(exc=exc, http_status=401, error_type=XianGuanJiaErrorType.AUTH_INVALID)

    # exc 优先：应归一化为 NETWORK_ERROR（可重试），而不是按 401/AUTH_INVALID 走不可重试
    assert isinstance(err, XianGuanJiaRetryableError)
    assert err.error_type == XianGuanJiaErrorType.NETWORK_ERROR
    assert err.http_status == 401


def test_is_retryable_error_recognizes_transport_exception() -> None:
    assert is_retryable_error(httpx.ConnectError("boom")) is True


def test_is_retryable_error_recognizes_timeout_exception() -> None:
    assert is_retryable_error(httpx.ReadTimeout("slow")) is True


def test_map_error_http_status_5xx_maps_retryable_server_error() -> None:
    err = map_error(http_status=503, message="server down")

    assert isinstance(err, XianGuanJiaRetryableError)
    assert err.error_type == XianGuanJiaErrorType.HTTP_SERVER_ERROR


def test_map_error_uses_retryable_business_error_code_when_no_exc() -> None:
    err = map_error(error_code="E429", message="too frequent")

    assert isinstance(err, XianGuanJiaRetryableError)
    assert err.error_type == XianGuanJiaErrorType.RATE_LIMITED


def test_map_error_uses_non_retryable_business_error_code_when_no_exc() -> None:
    err = map_error(error_code="E401", message="token invalid")

    assert isinstance(err, XianGuanJiaNonRetryableError)
    assert err.error_type == XianGuanJiaErrorType.AUTH_INVALID


def test_map_error_uses_error_code_when_exc_is_not_classifiable() -> None:
    err = map_error(exc=ValueError("bad value"), error_code="E429")

    assert isinstance(err, XianGuanJiaRetryableError)
    assert err.error_type == XianGuanJiaErrorType.RATE_LIMITED


def test_is_retryable_error_does_not_treat_generic_oserror_as_transport_error() -> None:
    assert is_retryable_error(OSError("not a network error")) is False
