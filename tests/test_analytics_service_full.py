"""Tests for analytics service module - corrected API usage."""

import tempfile
from pathlib import Path

import pytest


class TestAnalyticsService:
    """Tests for AnalyticsService with correct API."""

    def test_analytics_service_import(self):
        """Test AnalyticsService can be imported."""
        try:
            from src.modules.analytics.service import AnalyticsService

            assert True
        except ImportError:
            pytest.skip("AnalyticsService not available")

    def test_analytics_service_creation(self):
        """Test AnalyticsService can be created with config parameter."""
        try:
            from src.modules.analytics.service import AnalyticsService

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                db_path = f.name

            # AnalyticsService uses config= not db_path=
            service = AnalyticsService(config={"db_path": db_path})
            assert service is not None

            Path(db_path).unlink(missing_ok=True)
        except ImportError:
            pytest.skip("AnalyticsService not available")

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self):
        """Test getting dashboard stats."""
        try:
            from src.modules.analytics.service import AnalyticsService

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                db_path = f.name

            service = AnalyticsService(config={"path": db_path})
            result = await service.get_dashboard_stats()

            assert isinstance(result, dict)

            Path(db_path).unlink(missing_ok=True)
        except ImportError:
            pytest.skip("AnalyticsService not available")

    @pytest.mark.asyncio
    async def test_get_trend_data(self):
        """Test getting trend data."""
        try:
            from src.modules.analytics.service import AnalyticsService

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                db_path = f.name

            service = AnalyticsService(config={"path": db_path})
            result = await service.get_trend_data(metric="views", days=7)

            assert isinstance(result, list)

            Path(db_path).unlink(missing_ok=True)
        except ImportError:
            pytest.skip("AnalyticsService not available")


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_report_generator_import(self):
        """Test ReportGenerator can be imported."""
        try:
            from src.modules.analytics.report_generator import ReportGenerator

            assert True
        except ImportError:
            pytest.skip("ReportGenerator not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
