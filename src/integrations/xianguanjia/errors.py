"""闲管家集成层错误定义与可重试映射。"""

from __future__ import annotations

import socket
from enum import Enum
from typing import Any

try:
    import httpx
except Exception:  # pragma: no cover - httpx is optional in some runtimes
    httpx = None  # type: ignore[assignment]


class XianGuanJiaErrorType(str, Enum):
    """闲管家错误类型。"""

    AUTH_INVALID = "AUTH_INVALID"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    HTTP_BAD_REQUEST = "HTTP_BAD_REQUEST"
    HTTP_UNAUTHORIZED = "HTTP_UNAUTHORIZED"
    HTTP_FORBIDDEN = "HTTP_FORBIDDEN"
    HTTP_NOT_FOUND = "HTTP_NOT_FOUND"
    HTTP_CONFLICT = "HTTP_CONFLICT"
    HTTP_UNPROCESSABLE = "HTTP_UNPROCESSABLE"
    HTTP_TOO_MANY_REQUESTS = "HTTP_TOO_MANY_REQUESTS"
    HTTP_SERVER_ERROR = "HTTP_SERVER_ERROR"
    API_BUSINESS_REJECTED = "API_BUSINESS_REJECTED"
    RESPONSE_INVALID = "RESPONSE_INVALID"
    UNKNOWN = "UNKNOWN"


class XianGuanJiaError(Exception):
    """闲管家集成层基础异常。"""

    def __init__(
        self,
        message: str,
        *,
        error_type: XianGuanJiaErrorType,
        http_status: int | None = None,
        error_code: str | int | None = None,
        request_id: str | None = None,
        raw_payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.http_status = http_status
        self.error_code = error_code
        self.request_id = request_id
        self.raw_payload = raw_payload


class XianGuanJiaRetryableError(XianGuanJiaError):
    """可重试异常。"""


class XianGuanJiaNonRetryableError(XianGuanJiaError):
    """不可重试异常。"""


_RETRYABLE_ERROR_TYPES: frozenset[XianGuanJiaErrorType] = frozenset(
    {
        XianGuanJiaErrorType.RATE_LIMITED,
        XianGuanJiaErrorType.NETWORK_ERROR,
        XianGuanJiaErrorType.TIMEOUT,
        XianGuanJiaErrorType.HTTP_TOO_MANY_REQUESTS,
        XianGuanJiaErrorType.HTTP_SERVER_ERROR,
    }
)

_RETRYABLE_HTTP_STATUS: frozenset[int] = frozenset({408, 409, 425, 429, 500, 502, 503, 504})

# 业务错误码归一化映射：code -> (error_type, retryable)
_ERROR_CODE_MAPPING: dict[str, tuple[XianGuanJiaErrorType, bool]] = {
    # 可重试业务码
    "E429": (XianGuanJiaErrorType.RATE_LIMITED, True),
    "BIZ_RATE_LIMIT": (XianGuanJiaErrorType.RATE_LIMITED, True),
    "E503": (XianGuanJiaErrorType.HTTP_SERVER_ERROR, True),
    # 不可重试业务码
    "E401": (XianGuanJiaErrorType.AUTH_INVALID, False),
    "AUTH_INVALID": (XianGuanJiaErrorType.AUTH_INVALID, False),
    "SIGN_INVALID": (XianGuanJiaErrorType.SIGNATURE_INVALID, False),
    "BIZ_REJECTED": (XianGuanJiaErrorType.API_BUSINESS_REJECTED, False),
}

_NETWORK_ERRNO_SET: frozenset[int] = frozenset(
    {
        32,   # EPIPE
        54,   # ECONNRESET (macOS)
        60,   # ETIMEDOUT (macOS)
        61,   # ECONNREFUSED (macOS)
        64,   # EHOSTDOWN
        65,   # EHOSTUNREACH
        101,  # ENETUNREACH
        104,  # ECONNRESET (linux)
        110,  # ETIMEDOUT (linux)
        111,  # ECONNREFUSED (linux)
        113,  # EHOSTUNREACH (linux)
    }
)


def _normalize_error_type(error_type: XianGuanJiaErrorType | str | None) -> XianGuanJiaErrorType | None:
    if error_type is None:
        return None
    if isinstance(error_type, XianGuanJiaErrorType):
        return error_type
    text = str(error_type).strip()
    if not text:
        return None
    try:
        return XianGuanJiaErrorType(text)
    except ValueError:
        return XianGuanJiaErrorType.UNKNOWN


def _is_timeout_error(exc: BaseException) -> bool:
    timeout_types: tuple[type[BaseException], ...] = (TimeoutError, socket.timeout)
    if httpx is not None:
        timeout_types = timeout_types + (httpx.TimeoutException,)
    return isinstance(exc, timeout_types)


def _normalize_error_code(
    error_code: str | int | None,
) -> tuple[XianGuanJiaErrorType, bool] | None:
    if error_code is None:
        return None
    key = str(error_code).strip()
    if not key:
        return None
    return _ERROR_CODE_MAPPING.get(key)


def _is_transport_error(exc: BaseException) -> bool:
    transport_types: tuple[type[BaseException], ...] = (
        ConnectionError,
        socket.gaierror,
        ConnectionResetError,
        ConnectionRefusedError,
        ConnectionAbortedError,
        BrokenPipeError,
    )
    if httpx is not None:
        transport_types = transport_types + (httpx.TransportError,)

    if isinstance(exc, transport_types):
        return True

    if isinstance(exc, OSError):
        err_no = getattr(exc, "errno", None)
        if isinstance(err_no, int) and err_no in _NETWORK_ERRNO_SET:
            return True
        lowered = str(exc).lower()
        network_keywords = (
            "connection reset",
            "connection refused",
            "host unreachable",
            "network is unreachable",
            "name or service not known",
            "temporary failure in name resolution",
        )
        return any(keyword in lowered for keyword in network_keywords)

    return False


def _map_http_status_to_type(http_status: int | None) -> XianGuanJiaErrorType | None:
    if http_status is None:
        return None
    status = int(http_status)
    if status == 400:
        return XianGuanJiaErrorType.HTTP_BAD_REQUEST
    if status == 401:
        return XianGuanJiaErrorType.HTTP_UNAUTHORIZED
    if status == 403:
        return XianGuanJiaErrorType.HTTP_FORBIDDEN
    if status == 404:
        return XianGuanJiaErrorType.HTTP_NOT_FOUND
    if status == 409:
        return XianGuanJiaErrorType.HTTP_CONFLICT
    if status == 422:
        return XianGuanJiaErrorType.HTTP_UNPROCESSABLE
    if status == 429:
        return XianGuanJiaErrorType.HTTP_TOO_MANY_REQUESTS
    if 500 <= status <= 599:
        return XianGuanJiaErrorType.HTTP_SERVER_ERROR
    return None


def map_error(
    *,
    error_type: XianGuanJiaErrorType | str | None = None,
    http_status: int | None = None,
    error_code: str | int | None = None,
    request_id: str | None = None,
    raw_payload: Any = None,
    exc: BaseException | None = None,
    message: str | None = None,
) -> XianGuanJiaError:
    """统一错误归一化入口，返回可读元信息的异常实例。"""

    normalized: XianGuanJiaErrorType | None = None
    retryable_from_code: bool | None = None

    # 最高优先级：真实异常对象（transport/timeout）
    if exc is not None:
        if _is_timeout_error(exc):
            normalized = XianGuanJiaErrorType.TIMEOUT
        elif _is_transport_error(exc):
            normalized = XianGuanJiaErrorType.NETWORK_ERROR

    if normalized is None:
        normalized = _normalize_error_type(error_type)

    if normalized is None:
        mapped_by_code = _normalize_error_code(error_code)
        if mapped_by_code is not None:
            normalized, retryable_from_code = mapped_by_code

    if normalized is None:
        normalized = _map_http_status_to_type(http_status)
    if normalized is None:
        normalized = XianGuanJiaErrorType.UNKNOWN

    text = message or (str(exc) if exc is not None else "XianGuanJia error")
    if not text:
        text = "XianGuanJia error"

    exc_cls: type[XianGuanJiaError]
    if normalized in _RETRYABLE_ERROR_TYPES or (
        http_status is not None and int(http_status) in _RETRYABLE_HTTP_STATUS
    ) or retryable_from_code is True:
        exc_cls = XianGuanJiaRetryableError
    elif retryable_from_code is False:
        exc_cls = XianGuanJiaNonRetryableError
    else:
        exc_cls = XianGuanJiaNonRetryableError

    return exc_cls(
        text,
        error_type=normalized,
        http_status=http_status,
        error_code=error_code,
        request_id=request_id,
        raw_payload=raw_payload,
    )


def is_retryable_error(
    error: XianGuanJiaErrorType | str | BaseException | None,
    *,
    http_status: int | None = None,
) -> bool:
    """判断错误是否可重试。"""

    if isinstance(error, XianGuanJiaRetryableError):
        return True
    if isinstance(error, XianGuanJiaNonRetryableError):
        return False

    if isinstance(error, BaseException):
        if _is_timeout_error(error) or _is_transport_error(error):
            return True

    normalized = _normalize_error_type(error if not isinstance(error, BaseException) else None)
    if normalized in _RETRYABLE_ERROR_TYPES:
        return True

    if http_status is not None and int(http_status) in _RETRYABLE_HTTP_STATUS:
        return True

    return False
