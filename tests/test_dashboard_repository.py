"""
Dashboard repository and config service tests.
"""

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
    """Tests for LiveDashboardDataSource."""

    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    def test_datasource_init(self, temp_db):
        ds = LiveDashboardDataSource(db_path=temp_db)
        assert ds is not None

    def test_get_summary(self, temp_db):
        ds = LiveDashboardDataSource(db_path=temp_db)
        summary = ds.get_summary()
        assert isinstance(summary, dict)


class TestConfigService:
    """Tests for config service functions."""

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
        config = {"api_key": "secret123", "app_secret": "super_secret"}
        masked = mask_sensitive(config)
        assert "***" in str(masked.get("api_key", "")) or masked.get("api_key") != "secret123"

    def test_update_config(self, mock_config_path):
        write_system_config({"existing": "value"})
        result = update_config({"new_section": {"key": "new_value"}})
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
