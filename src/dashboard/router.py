"""Route registration table and dispatcher for the dashboard HTTP server.

Supports:
- Exact-match routes via @get/@post/@put/@delete decorators
- Prefix-match routes via @get_prefix/@post_prefix decorators
- RouteContext for structured parameter access (query, body, path params)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# RouteContext — structured request context passed to route handlers
# ---------------------------------------------------------------------------


@dataclass
class RouteContext:
    """Structured request context for route handler functions.

    Route handlers should use the public methods (send_json, query_str, etc.)
    rather than accessing ``_handler`` directly.
    """

    _handler: Any  # DashboardHandler — kept as Any to avoid circular import at runtime
    path: str
    query: dict[str, list[str]]
    path_params: dict[str, str] = field(default_factory=dict)
    _body_cache: Any = field(default=None, repr=False)

    # -- query helpers -------------------------------------------------------

    def query_str(self, key: str, default: str = "") -> str:
        """Return a single query-string value."""
        values = self.query.get(key, [])
        return values[0] if values else default

    def query_int(
        self,
        key: str,
        default: int = 0,
        min_val: int | None = None,
        max_val: int | None = None,
    ) -> int:
        """Return an integer query-string value with optional clamping."""
        try:
            n = int(self.query_str(key, str(default)))
        except (TypeError, ValueError):
            n = default
        if min_val is not None:
            n = max(n, min_val)
        if max_val is not None:
            n = min(n, max_val)
        return n

    def query_bool(self, key: str, default: bool = False) -> bool:
        """Return a boolean query-string value (accepts 1/true/yes)."""
        raw = self.query_str(key, "").strip().lower()
        if not raw:
            return default
        return raw in {"1", "true", "yes"}

    # -- body helpers --------------------------------------------------------

    def json_body(self) -> dict[str, Any]:
        """Lazily read and cache the JSON request body."""
        if self._body_cache is None:
            self._body_cache = self._handler._read_json_body()
        return self._body_cache

    def multipart_files(self) -> list[tuple[str, bytes]]:
        """Read multipart-uploaded files."""
        return self._handler._read_multipart_files()

    # -- response helpers ----------------------------------------------------

    def send_json(self, payload: Any, status: int = 200) -> None:
        """Send a JSON response."""
        self._handler._send_json(payload, status=status)

    def send_html(self, html: str, status: int = 200) -> None:
        """Send an HTML response."""
        self._handler._send_html(html, status=status)

    def send_bytes(
        self,
        data: bytes,
        content_type: str,
        status: int = 200,
        download_name: str | None = None,
    ) -> None:
        """Send a binary response."""
        self._handler._send_bytes(data, content_type, status=status, download_name=download_name)

    # -- service accessors (injected via DashboardHandler class vars) ---------

    @property
    def repo(self):
        """Access DashboardRepository."""
        return self._handler.repo

    @property
    def module_console(self):
        """Access ModuleConsole."""
        return self._handler.module_console

    @property
    def mimic_ops(self):
        """Access MimicOps (will be removed after Phase 3)."""
        return self._handler.mimic_ops

    @property
    def headers(self):
        """Access request headers."""
        return self._handler.headers

    @property
    def wfile(self):
        """Access response output stream (for SSE etc.)."""
        return self._handler.wfile

    def send_response(self, code: int) -> None:
        """Send HTTP response status line."""
        self._handler.send_response(code)

    def send_header(self, keyword: str, value: str) -> None:
        """Send a single HTTP header."""
        self._handler.send_header(keyword, value)

    def end_headers(self) -> None:
        """Finish sending HTTP headers."""
        self._handler.end_headers()


# ---------------------------------------------------------------------------
# Route handler type
# ---------------------------------------------------------------------------

RouteHandler = Callable[[RouteContext], None]

# ---------------------------------------------------------------------------
# Route registries
# ---------------------------------------------------------------------------

_GET_ROUTES: dict[str, RouteHandler] = {}
_POST_ROUTES: dict[str, RouteHandler] = {}
_PUT_ROUTES: dict[str, RouteHandler] = {}
_DELETE_ROUTES: dict[str, RouteHandler] = {}

# Prefix routes: list of (prefix, param_name, handler)
# Sorted by prefix length descending so longest prefix matches first.
_GET_PREFIX_ROUTES: list[tuple[str, str, RouteHandler]] = []
_POST_PREFIX_ROUTES: list[tuple[str, str, RouteHandler]] = []
_PUT_PREFIX_ROUTES: list[tuple[str, str, RouteHandler]] = []
_DELETE_PREFIX_ROUTES: list[tuple[str, str, RouteHandler]] = []


# ---------------------------------------------------------------------------
# Exact-match decorators
# ---------------------------------------------------------------------------


def get(path: str):
    """Register an exact-match GET route handler."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _GET_ROUTES[path] = fn
        return fn

    return decorator


def post(path: str):
    """Register an exact-match POST route handler."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _POST_ROUTES[path] = fn
        return fn

    return decorator


def put(path: str):
    """Register an exact-match PUT route handler."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _PUT_ROUTES[path] = fn
        return fn

    return decorator


def delete(path: str):
    """Register an exact-match DELETE route handler."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _DELETE_ROUTES[path] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Prefix-match decorators
# ---------------------------------------------------------------------------


def _add_prefix(
    registry: list[tuple[str, str, RouteHandler]],
    prefix: str,
    param_name: str,
    fn: RouteHandler,
) -> None:
    registry.append((prefix, param_name, fn))
    registry.sort(key=lambda x: len(x[0]), reverse=True)


def get_prefix(prefix: str, param_name: str = "sub_path"):
    """Register a prefix-match GET route. Remaining path → ctx.path_params[param_name]."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _add_prefix(_GET_PREFIX_ROUTES, prefix, param_name, fn)
        return fn

    return decorator


def post_prefix(prefix: str, param_name: str = "sub_path"):
    """Register a prefix-match POST route."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _add_prefix(_POST_PREFIX_ROUTES, prefix, param_name, fn)
        return fn

    return decorator


def put_prefix(prefix: str, param_name: str = "sub_path"):
    """Register a prefix-match PUT route."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _add_prefix(_PUT_PREFIX_ROUTES, prefix, param_name, fn)
        return fn

    return decorator


def delete_prefix(prefix: str, param_name: str = "sub_path"):
    """Register a prefix-match DELETE route."""

    def decorator(fn: RouteHandler) -> RouteHandler:
        _add_prefix(_DELETE_PREFIX_ROUTES, prefix, param_name, fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Dispatchers
# ---------------------------------------------------------------------------


def _dispatch(
    path: str,
    ctx: RouteContext,
    exact: dict[str, RouteHandler],
    prefix_list: list[tuple[str, str, RouteHandler]],
) -> bool:
    """Try exact match first, then prefix match. Returns True if handled."""
    handler = exact.get(path)
    if handler:
        handler(ctx)
        return True
    for pfx, param_name, handler in prefix_list:
        if path.startswith(pfx):
            ctx.path_params[param_name] = path[len(pfx) :]
            handler(ctx)
            return True
    return False


def dispatch_get(path: str, ctx: RouteContext) -> bool:
    """Dispatch a GET request. Returns True if a route handled it."""
    return _dispatch(path, ctx, _GET_ROUTES, _GET_PREFIX_ROUTES)


def dispatch_post(path: str, ctx: RouteContext) -> bool:
    """Dispatch a POST request. Returns True if a route handled it."""
    return _dispatch(path, ctx, _POST_ROUTES, _POST_PREFIX_ROUTES)


def dispatch_put(path: str, ctx: RouteContext) -> bool:
    """Dispatch a PUT request. Returns True if a route handled it."""
    return _dispatch(path, ctx, _PUT_ROUTES, _PUT_PREFIX_ROUTES)


def dispatch_delete(path: str, ctx: RouteContext) -> bool:
    """Dispatch a DELETE request. Returns True if a route handled it."""
    return _dispatch(path, ctx, _DELETE_ROUTES, _DELETE_PREFIX_ROUTES)


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


def all_routes() -> dict[str, list[str]]:
    """Return summary of registered routes (for debugging)."""
    return {
        "GET": sorted(_GET_ROUTES.keys()),
        "GET_PREFIX": [pfx for pfx, _, _ in _GET_PREFIX_ROUTES],
        "POST": sorted(_POST_ROUTES.keys()),
        "POST_PREFIX": [pfx for pfx, _, _ in _POST_PREFIX_ROUTES],
        "PUT": sorted(_PUT_ROUTES.keys()),
        "DELETE": sorted(_DELETE_ROUTES.keys()),
    }


def clear_routes() -> None:
    """Clear all registered routes (useful for testing)."""
    _GET_ROUTES.clear()
    _POST_ROUTES.clear()
    _PUT_ROUTES.clear()
    _DELETE_ROUTES.clear()
    _GET_PREFIX_ROUTES.clear()
    _POST_PREFIX_ROUTES.clear()
    _PUT_PREFIX_ROUTES.clear()
    _DELETE_PREFIX_ROUTES.clear()
