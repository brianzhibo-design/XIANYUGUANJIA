"""
Test suite for core error handler module.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.core.error_handler import ErrorHandler, ErrorSeverity, handle_error


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_error_severity_values(self):
        """Test that ErrorSeverity has expected values."""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    def test_error_handler_creation(self):
        """Test ErrorHandler can be created."""
        handler = ErrorHandler()
        assert handler is not None

    def test_handle_error_with_exception(self):
        """Test handling an exception."""
        handler = ErrorHandler()

        try:
            raise ValueError("Test error")
        except Exception as e:
            result = handler.handle(e, severity=ErrorSeverity.ERROR)
            assert result is not None

    def test_handle_error_with_context(self):
        """Test handling error with context."""
        handler = ErrorHandler()

        context = {"user_id": "123", "action": "test"}
        result = handler.handle(Exception("Test"), severity=ErrorSeverity.WARNING, context=context)
        assert result is not None


class TestHandleErrorFunction:
    """Tests for standalone handle_error function."""

    def test_handle_error_basic(self):
        """Test basic error handling."""
        try:
            raise RuntimeError("Test runtime error")
        except Exception as e:
            result = handle_error(e)
            assert result is not None

    def test_handle_error_with_severity(self):
        """Test error handling with severity."""
        try:
            raise ValueError("Test value error")
        except Exception as e:
            result = handle_error(e, severity="critical")
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
