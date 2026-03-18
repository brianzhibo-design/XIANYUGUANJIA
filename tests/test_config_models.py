"""
Tests for core config models.
"""

import pytest
from pydantic import ValidationError

from src.core.config_models import (
    AIConfig,
    AccountConfig,
    BrowserRuntimeConfig,
    DatabaseConfig,
    MediaConfig,
    SchedulerConfig,
    Provider,
)


class TestAIConfig:
    """Tests for AIConfig model."""

    def test_default_values(self):
        config = AIConfig()
        assert config.provider == Provider.DEEPSEEK
        assert config.model == "deepseek-chat"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000

    def test_custom_values(self):
        config = AIConfig(provider=Provider.OPENAI, api_key="test_key", model="gpt-4", temperature=0.5)
        assert config.provider == Provider.OPENAI
        assert config.api_key == "test_key"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5

    def test_temperature_validation(self):
        with pytest.raises(ValidationError):
            AIConfig(temperature=3.0)


class TestBrowserRuntimeConfig:
    """Tests for BrowserRuntimeConfig model."""

    def test_default_values(self):
        config = BrowserRuntimeConfig()
        assert config.host == "localhost"
        assert config.port == 9222
        assert config.timeout == 30

    def test_port_validation(self):
        with pytest.raises(ValidationError):
            BrowserRuntimeConfig(port=70000)


class TestDatabaseConfig:
    """Tests for DatabaseConfig model."""

    def test_default_values(self):
        config = DatabaseConfig()
        assert config.type == "sqlite"
        assert config.path == "data/agent.db"

    def test_connection_limits(self):
        with pytest.raises(ValidationError):
            DatabaseConfig(max_connections=0)


class TestAccountConfig:
    """Tests for AccountConfig model."""

    def test_account_creation(self):
        config = AccountConfig(id="test_id", name="Test Account", cookie="test_cookie")
        assert config.id == "test_id"
        assert config.name == "Test Account"
        assert config.priority == 1
        assert config.enabled is True


class TestMediaConfig:
    """Tests for MediaConfig model."""

    def test_default_formats(self):
        config = MediaConfig()
        assert "jpg" in config.supported_formats
        assert "png" in config.supported_formats

    def test_max_size_validation(self):
        with pytest.raises(ValidationError):
            MediaConfig(max_image_size=100)


class TestSchedulerConfig:
    """Tests for SchedulerConfig model."""

    def test_default_timezone(self):
        config = SchedulerConfig()
        assert config.timezone == "Asia/Shanghai"
        assert config.enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
