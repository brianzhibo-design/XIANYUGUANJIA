"""Tests for core service container module - corrected API usage."""

import pytest
from unittest.mock import MagicMock, patch

from src.core.service_container import ServiceContainer


class ITestService:
    """Test service interface."""

    pass


class TestServiceImpl(ITestService):
    """Test service implementation."""

    pass


class AnotherService:
    """Another test service."""

    pass


class TestServiceContainer:
    """Tests for ServiceContainer class with correct type-based API."""

    def test_container_creation(self):
        """Test ServiceContainer can be created."""
        container = ServiceContainer()
        assert container is not None

    def test_container_singleton(self):
        """Test that ServiceContainer behaves as singleton."""
        container1 = ServiceContainer()
        container2 = ServiceContainer()

        assert container1 is container2

    def test_register_and_get_service(self):
        """Test registering and retrieving a service by type."""
        container = ServiceContainer()

        mock_service = MagicMock()

        # ServiceContainer uses type parameters, not strings
        container.register(TestServiceImpl, instance=mock_service)
        retrieved = container.get(TestServiceImpl)

        assert retrieved is mock_service

    def test_get_nonexistent_service(self):
        """Test getting a non-existent service."""
        container = ServiceContainer()

        result = container.get(AnotherService)
        assert result is None

    def test_has_service(self):
        """Test checking if service exists by type."""
        container = ServiceContainer()

        mock_service = MagicMock()
        container.register(TestServiceImpl, instance=mock_service)

        assert container.has(TestServiceImpl) is True
        assert container.has(AnotherService) is False

    def test_clear_services(self):
        """Test clearing all services."""
        container = ServiceContainer()

        mock_service = MagicMock()
        container.register(TestServiceImpl, instance=mock_service)
        assert container.has(TestServiceImpl) is True

        container.clear()
        assert container.has(TestServiceImpl) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
