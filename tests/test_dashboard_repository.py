"""Dashboard repository and config service tests - corrected API usage."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.dashboard.repository import DashboardRepository, LiveDashboardDataSource
from src.dashboard.config_service import (
    read_system_config,
    write_system_config,
    mask_sensitive,
    update_config,
)


class TestDashboardRepository:
    """Tests for DashboardRepository."""

    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    def test_repository_init(self, temp_db):
        repo = DashboardRepository(db_path=temp_db)
        assert repo is not None
        assert Path(temp_db).exists()

    def test_repository_tables_created(self, temp_db):
        repo = DashboardRepository(db_path=temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert len(tables) > 0


class TestLiveDashboardDataSource:
    """Tests for LiveDashboardDataSource with correct API."""

    def test_datasource_init(self):
        """Test creating LiveDashboardDataSource with get_client_fn parameter."""
        mock_get_client = Mock(return_value=None)
        ds = LiveDashboardDataSource(get_client_fn=mock_get_client)
        assert ds is not None

    def test_get_summary(self):
        """Test getting summary from data source."""
        mock_get_client = Mock(return_value=None)
        ds = LiveDashboardDataSource(get_client_fn=mock_get_client)
        result = ds._fetch_all_products()
        assert isinstance(result, list)


class TestConfigService:
    """Tests for config service functions with corrected assertions."""

    @pytest.fixture
    def temp_config_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "value"}, f)
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def mock_config_path(self, temp_config_file):
        with patch("src.dashboard.config_service._SYS_CONFIG_FILE", Path(temp_config_file)):
            yield temp_config_file

    def test_read_system_config(self, mock_config_path):
        config = read_system_config()
        assert isinstance(config, dict)

    def test_write_and_read_system_config(self, mock_config_path):
        test_data = {"ai": {"provider": "deepseek"}, "test_section": {"key": "value"}}
        write_system_config(test_data)
        config = read_system_config()
        assert config.get("ai", {}).get("provider") == "deepseek"

    def test_mask_sensitive(self):
        """Test that sensitive values are masked correctly."""
        config = {"xianguanjia": {"api_key": "secret123", "app_secret": "super_secret"}}
        masked = mask_sensitive(config)
        # mask_sensitive masks values with **** after first 4 chars
        assert "****" in masked["xianguanjia"]["app_secret"]

    def test_update_config(self, mock_config_path):
        write_system_config({"existing": "value"})
        result = update_config({"new_section": {"key": "new_value"}})
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
