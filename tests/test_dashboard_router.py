"""
Tests for dashboard router.
"""

import pytest
from unittest.mock import MagicMock

from src.dashboard.router import (
    RouteContext,
    all_routes,
    dispatch_get,
    dispatch_post,
    dispatch_put,
    dispatch_delete,
)


class TestRouteContext:
    """Tests for RouteContext."""

    def test_context_creation(self):
        ctx = RouteContext(path="/api/test", method="GET", headers={"Content-Type": "application/json"}, body=None)
        assert ctx.path == "/api/test"
        assert ctx.method == "GET"


class TestRouterDispatch:
    """Tests for router dispatch functions."""

    def test_all_routes_returns_dict(self):
        routes = all_routes()
        assert isinstance(routes, dict)

    def test_dispatch_get_handles_unknown_path(self):
        ctx = MagicMock()
        result = dispatch_get("/unknown/path", ctx)
        assert result is False

    def test_dispatch_post_handles_unknown_path(self):
        ctx = MagicMock()
        result = dispatch_post("/unknown/path", ctx)
        assert result is False

    def test_dispatch_put_handles_unknown_path(self):
        ctx = MagicMock()
        result = dispatch_put("/unknown/path", ctx)
        assert result is False

    def test_dispatch_delete_handles_unknown_path(self):
        ctx = MagicMock()
        result = dispatch_delete("/unknown/path", ctx)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
