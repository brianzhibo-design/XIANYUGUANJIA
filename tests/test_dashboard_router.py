"""Tests for dashboard router - corrected API usage."""

import pytest
from unittest.mock import MagicMock

from src.dashboard.router import (
    RouteContext,
    _GET_ROUTES,
    _POST_ROUTES,
)


class TestRouteContext:
    """Tests for RouteContext with correct API."""

    def test_context_creation(self):
        """Test RouteContext creation with correct parameters."""
        mock_handler = MagicMock()
        ctx = RouteContext(_handler=mock_handler, path="/api/test", query={"page": ["1"]})
        assert ctx.path == "/api/test"

    def test_query_str(self):
        """Test query_str helper method."""
        mock_handler = MagicMock()
        ctx = RouteContext(_handler=mock_handler, path="/api/test", query={"search": ["keyword"]})
        assert ctx.query_str("search") == "keyword"
        assert ctx.query_str("missing") == ""

    def test_query_int(self):
        """Test query_int helper method."""
        mock_handler = MagicMock()
        ctx = RouteContext(_handler=mock_handler, path="/api/test", query={"page": ["5"]})
        assert ctx.query_int("page") == 5
        assert ctx.query_int("missing") == 0


class TestRouterRoutes:
    """Tests for router route registration."""

    def test_get_routes_exist(self):
        """Test that GET routes dictionary exists."""
        assert isinstance(_GET_ROUTES, dict)

    def test_post_routes_exist(self):
        """Test that POST routes dictionary exists."""
        assert isinstance(_POST_ROUTES, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
