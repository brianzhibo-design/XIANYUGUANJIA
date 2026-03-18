"""
Test suite for core service container module.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.core.service_container import ServiceContainer


class TestServiceContainer:
    """Tests for ServiceContainer class."""

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
        """Test registering and retrieving a service."""
        container = ServiceContainer()

        mock_service = MagicMock()
        mock_service.name = "TestService"

        container.register("test_service", mock_service)
        retrieved = container.get("test_service")

        assert retrieved is mock_service

    def test_get_nonexistent_service(self):
        """Test getting a non-existent service."""
        container = ServiceContainer()

        result = container.get("nonexistent")
        assert result is None

    def test_has_service(self):
        """Test checking if service exists."""
        container = ServiceContainer()

        mock_service = MagicMock()
        container.register("existing", mock_service)

        assert container.has("existing") is True
        assert container.has("not_existing") is False

    def test_unregister_service(self):
        """Test unregistering a service."""
        container = ServiceContainer()

        mock_service = MagicMock()
        container.register("to_remove", mock_service)
        assert container.has("to_remove") is True

        container.unregister("to_remove")
        assert container.has("to_remove") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
