"""Tests for core error handler module - corrected API usage."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from src.core.error_handler import (
    XianyuError,
    ConfigError,
    BrowserError,
    AIError,
    MediaError,
    AccountError,
    DatabaseError,
    handle_controller_errors,
    handle_operation_errors,
    safe_execute,
    handle_errors,
)


class TestXianyuError:
    """Tests for XianyuError exceptions."""

    def test_xianyu_error_creation(self):
        """Test XianyuError can be created."""
        error = XianyuError("Test error message")
        assert str(error) == "Test error message"

    def test_config_error_creation(self):
        """Test ConfigError can be created."""
        error = ConfigError("Config error")
        assert isinstance(error, XianyuError)

    def test_browser_error_creation(self):
        """Test BrowserError can be created."""
        error = BrowserError("Browser error")
        assert isinstance(error, XianyuError)

    def test_ai_error_creation(self):
        """Test AIError can be created."""
        error = AIError("AI error")
        assert isinstance(error, XianyuError)

    def test_media_error_creation(self):
        """Test MediaError can be created."""
        error = MediaError("Media error")
        assert isinstance(error, XianyuError)

    def test_account_error_creation(self):
        """Test AccountError can be created."""
        error = AccountError("Account error")
        assert isinstance(error, XianyuError)

    def test_database_error_creation(self):
        """Test DatabaseError can be created."""
        error = DatabaseError("Database error")
        assert isinstance(error, XianyuError)


class TestErrorDecorators:
    """Tests for error handling decorators - using class methods."""

    def test_handle_controller_errors_decorator(self):
        """Test handle_controller_errors decorator exists."""
        assert callable(handle_controller_errors)

    def test_handle_operation_errors_decorator(self):
        """Test handle_operation_errors decorator exists."""
        assert callable(handle_operation_errors)

    def test_safe_execute_decorator(self):
        """Test safe_execute decorator exists."""
        assert callable(safe_execute)

    @pytest.mark.asyncio
    async def test_controller_error_handler_with_async_method(self):
        """Test handle_controller_errors with an async class method."""

        class TestController:
            def __init__(self):
                self.logger = MagicMock()

            @handle_controller_errors(default_return="fallback")
            async def test_method(self):
                raise ValueError("Test error")

        controller = TestController()
        result = await controller.test_method()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_operation_error_handler_with_async_method(self):
        """Test handle_operation_errors with an async class method."""

        class TestService:
            def __init__(self):
                self.logger = MagicMock()

            @handle_operation_errors(default_return=False)
            async def test_method(self):
                raise ValueError("Test error")

        service = TestService()
        result = await service.test_method()
        assert result is False

    def test_safe_execute_with_function(self):
        """Test safe_execute with a function."""

        @safe_execute(default_return="safe")
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == "safe"


class TestHandleErrorsFunction:
    """Tests for standalone handle_errors function."""

    def test_handle_errors_exists(self):
        """Test handle_errors function exists."""
        assert callable(handle_errors)

    def test_handle_errors_basic(self):
        """Test basic error handling with handle_errors."""
        try:
            raise RuntimeError("Test runtime error")
        except Exception as e:
            result = handle_errors(e)
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
