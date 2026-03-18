"""Tests for xianguanjia integration - corrected API usage."""

import pytest


class TestXianguanjiaOpenPlatform:
    """Tests for Xianguanjia OpenPlatformClient with correct API."""

    def test_open_platform_client_import(self):
        """Test OpenPlatformClient can be imported."""
        try:
            from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

            assert True
        except ImportError:
            pytest.skip("OpenPlatformClient not available")

    def test_open_platform_client_creation(self):
        """Test OpenPlatformClient can be created with base_url parameter."""
        try:
            from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

            # OpenPlatformClient requires base_url parameter
            client = OpenPlatformClient(base_url="https://api.xianguanjia.com", app_key="test", app_secret="test")
            assert client is not None
            assert client.base_url == "https://api.xianguanjia.com"
        except ImportError:
            pytest.skip("OpenPlatformClient not available")


class TestXianguanjiaSigning:
    """Tests for Xianguanjia signing with correct API."""

    def test_sign_functions_import(self):
        """Test signing functions can be imported."""
        try:
            from src.integrations.xianguanjia.signing import sign_open_platform_request, sign_business_request

            assert True
        except ImportError:
            pytest.skip("Signing functions not available")

    def test_sign_open_platform_request(self):
        try:
            from src.integrations.xianguanjia.signing import sign_open_platform_request

            signature = sign_open_platform_request(
                app_key="test_key", app_secret="test_secret", timestamp="1234567890", body='{"test":"data"}'
            )

            assert isinstance(signature, str)
            assert len(signature) > 0
        except ImportError:
            pytest.skip("sign_open_platform_request not available")

    def test_sign_business_request(self):
        """Test business mode signing."""
        try:
            from src.integrations.xianguanjia.signing import sign_business_request

            signature = sign_business_request(
                app_key="test_key",
                app_secret="test_secret",
                seller_id="seller123",
                timestamp="1234567890",
                body='{"test":"data"}',
            )

            assert isinstance(signature, str)
            assert len(signature) > 0
        except ImportError:
            pytest.skip("sign_business_request not available")


class TestXianguanjiaModels:
    """Tests for Xianguanjia models."""

    def test_models_import(self):
        """Test models can be imported."""
        try:
            from src.integrations.xianguanjia.models import XianGuanJiaResponse

            assert True
        except ImportError:
            pytest.skip("Models not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
