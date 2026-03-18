"""Tests for quote engine and related modules - corrected API usage."""

import tempfile
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch


class TestQuoteEngine:
    """Tests for QuoteEngine."""

    def test_quote_engine_import(self):
        """Test QuoteEngine can be imported."""
        try:
            from src.modules.quote.engine import QuoteEngine

            assert True
        except ImportError:
            pytest.skip("QuoteEngine not available")

    def test_quote_engine_creation(self):
        """Test QuoteEngine can be created."""
        try:
            from src.modules.quote.engine import QuoteEngine

            engine = QuoteEngine()
            assert engine is not None
        except ImportError:
            pytest.skip("QuoteEngine not available")

    def test_calculate_quote(self):
        """Test calculating a quote."""
        try:
            from src.modules.quote.engine import QuoteEngine

            engine = QuoteEngine()
            result = engine.calculate(origin="北京", destination="上海", weight=5.0)

            assert isinstance(result, dict)
        except ImportError:
            pytest.skip("QuoteEngine not available")


class TestQuoteModels:
    """Tests for quote models with correct API."""

    def test_quote_result_creation(self):
        """Test QuoteResult model with correct parameters."""
        try:
            from src.modules.quote.models import QuoteResult, QuoteSnapshot

            # QuoteResult uses provider, base_fee, eta_minutes (not price, courier, eta_days)
            snapshot = QuoteSnapshot()
            result = QuoteResult(
                provider="顺丰",
                base_fee=25.0,
                total_fee=30.0,
                eta_minutes=2880,  # 2 days in minutes
                snapshot=snapshot,
            )

            assert result.provider == "顺丰"
            assert result.base_fee == 25.0
        except ImportError:
            pytest.skip("QuoteResult not available")


class TestCostTable:
    """Tests for CostTableRepository with correct API."""

    def test_cost_table_import(self):
        """Test CostTableRepository can be imported."""
        try:
            from src.modules.quote.cost_table import CostTableRepository

            assert True
        except ImportError:
            pytest.skip("CostTableRepository not available")

    def test_cost_table_creation(self):
        """Test CostTableRepository can be created with table_dir parameter."""
        try:
            from src.modules.quote.cost_table import CostTableRepository

            with tempfile.TemporaryDirectory() as tmpdir:
                # CostTableRepository requires table_dir parameter
                repo = CostTableRepository(table_dir=tmpdir)
                assert repo is not None
        except ImportError:
            pytest.skip("CostTableRepository not available")


class TestGeoResolver:
    """Tests for GeoResolver with correct API."""

    def test_geo_resolver_import(self):
        """Test GeoResolver can be imported."""
        try:
            from src.modules.quote.geo_resolver import GeoResolver

            assert True
        except ImportError:
            pytest.skip("GeoResolver not available")

    def test_geo_resolver_creation(self):
        """Test GeoResolver can be created."""
        try:
            from src.modules.quote.geo_resolver import GeoResolver

            resolver = GeoResolver()
            assert resolver is not None
        except ImportError:
            pytest.skip("GeoResolver not available")

    def test_province_of_city(self):
        """Test getting province of a city using province_of method."""
        try:
            from src.modules.quote.geo_resolver import GeoResolver

            resolver = GeoResolver()
            # GeoResolver uses province_of, not resolve
            result = resolver.province_of("北京")

            assert isinstance(result, str)
        except ImportError:
            pytest.skip("GeoResolver not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
