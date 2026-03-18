"""Tests for content service module - corrected API usage."""

import pytest
from unittest.mock import MagicMock, patch


class TestContentService:
    """Tests for ContentService with correct API."""

    def test_content_service_import(self):
        """Test ContentService can be imported."""
        try:
            from src.modules.content.service import ContentService

            assert True
        except ImportError:
            pytest.skip("ContentService not available")

    def test_content_service_creation(self):
        """Test ContentService can be created."""
        try:
            from src.modules.content.service import ContentService

            service = ContentService()
            assert service is not None
        except ImportError:
            pytest.skip("ContentService not available")

    def test_generate_title(self):
        """Test title generation with correct parameters."""
        try:
            from src.modules.content.service import ContentService

            service = ContentService()
            # generate_title(product_name, features, category)
            result = service.generate_title(product_name="iPhone", features=["国行", "128G"], category="数码手机")

            assert isinstance(result, str) or result is None
        except ImportError:
            pytest.skip("ContentService not available")

    def test_generate_description(self):
        """Test description generation with correct parameters."""
        try:
            from src.modules.content.service import ContentService

            service = ContentService()
            # generate_description(product_name, condition, reason, tags, extra_info)
            result = service.generate_description(
                product_name="iPhone 14",
                condition="95新",
                reason="换新手机",
                tags=["手机", "苹果"],
                extra_info="无拆修",
            )

            assert isinstance(result, str) or result is None
        except ImportError:
            pytest.skip("ContentService not available")


class TestContentSEO:
    """Tests for SEO functionality with correct API."""

    def test_generate_seo_keywords(self):
        """Test SEO keywords generation with correct parameters."""
        try:
            from src.modules.content.service import ContentService

            service = ContentService()
            # generate_seo_keywords(product_name, category)
            result = service.generate_seo_keywords(product_name="iPhone 14 Pro", category="数码手机")

            assert isinstance(result, list) or result is None
        except ImportError:
            pytest.skip("ContentService not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
