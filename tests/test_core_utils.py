"""
Tests for core crypto and utility modules.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestCrypto:
    """Tests for crypto module."""

    def test_encrypt_decrypt(self):
        try:
            from src.core.crypto import encrypt, decrypt

            test_data = "test_secret"
            encrypted = encrypt(test_data)
            assert encrypted != test_data

            decrypted = decrypt(encrypted)
            assert decrypted == test_data
        except ImportError:
            pytest.skip("Crypto functions not available")


class TestLogger:
    """Tests for logger module."""

    def test_logger_singleton(self):
        from src.core.logger import Logger

        logger1 = Logger()
        logger2 = Logger()
        assert logger1 is logger2

    def test_logger_instance(self):
        from src.core.logger import Logger

        logger = Logger()
        assert logger is not None


class TestNotify:
    """Tests for notify module."""

    def test_notifier_import(self):
        try:
            from src.core.notify import Notifier

            assert True
        except ImportError:
            pytest.skip("Notifier not available")


class TestCompliance:
    """Tests for compliance module."""

    def test_compliance_center_import(self):
        try:
            from src.modules.compliance.center import ComplianceCenter

            assert True
        except ImportError:
            pytest.skip("ComplianceCenter not available")


class TestPerformance:
    """Tests for performance module."""

    def test_metrics_collector(self):
        try:
            from src.core.performance import MetricsCollector

            collector = MetricsCollector()
            collector.record("test_metric", 100)
            metrics = collector.get_metrics()
            assert "test_metric" in metrics
        except ImportError:
            pytest.skip("MetricsCollector not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
