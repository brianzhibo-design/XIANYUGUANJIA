"""Test suite for dashboard routes - corrected API usage."""

import pytest
from unittest.mock import MagicMock

from src.dashboard.router import _GET_ROUTES, _POST_ROUTES

# Import routes to trigger registration
from src.dashboard.routes import system, config, cookie, messages, orders, products, quote


class TestRouteConfig:
    """Tests for config routes."""

    def test_config_get_route_exists(self):
        """Test config get route exists."""
        assert "/api/config" in _GET_ROUTES

    def test_config_sections_route_exists(self):
        """Test config sections route exists."""
        assert "/api/config/sections" in _GET_ROUTES


class TestRouteCookie:
    """Tests for cookie routes."""

    def test_cookie_get_route_exists(self):
        """Test cookie get route exists."""
        assert "/api/get-cookie" in _GET_ROUTES

    def test_cookie_diagnose_route_exists(self):
        """Test cookie diagnose route exists."""
        assert "/api/cookie-diagnose" in _POST_ROUTES


class TestRouteSystem:
    """Tests for system routes."""

    def test_healthz_route_exists(self):
        """Test healthz route exists."""
        assert "/healthz" in _GET_ROUTES

    def test_version_route_exists(self):
        """Test version route exists."""
        assert "/api/version" in _GET_ROUTES

    def test_status_route_exists(self):
        """Test status route exists."""
        assert "/api/status" in _GET_ROUTES


class TestRouteMessages:
    """Tests for message routes."""

    def test_messages_replies_route_exists(self):
        """Test messages replies route exists."""
        assert "/api/replies" in _GET_ROUTES


class TestRouteOrders:
    """Tests for order routes."""

    def test_orders_route_exists(self):
        """Test orders route exists."""
        assert "/api/virtual-goods/metrics" in _GET_ROUTES


class TestRouteProducts:
    """Tests for product routes."""

    def test_products_listing_route_exists(self):
        """Test products listing route exists."""
        assert "/api/listing/templates" in _GET_ROUTES


class TestRouteQuote:
    """Tests for quote routes."""

    def test_quote_route_stats_exists(self):
        """Test quote route stats exists."""
        assert "/api/route-stats" in _GET_ROUTES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
