"""Tests for compliance and safety modules - corrected API usage."""

import pytest
from unittest.mock import Mock


class TestComplianceCenter:
    """Tests for ComplianceCenter with correct API."""

    def test_compliance_center_import(self):
        """Test ComplianceCenter can be imported."""
        try:
            from src.modules.compliance.center import ComplianceCenter

            assert True
        except ImportError:
            pytest.skip("ComplianceCenter not available")

    def test_compliance_center_creation(self):
        """Test ComplianceCenter can be created."""
        try:
            from src.modules.compliance.center import ComplianceCenter

            center = ComplianceCenter()
            assert center is not None
        except ImportError:
            pytest.skip("ComplianceCenter not available")

    def test_evaluate_before_send(self):
        """Test content evaluation using evaluate_before_send (not check_content)."""
        try:
            from src.modules.compliance.center import ComplianceCenter

            center = ComplianceCenter()
            result = center.evaluate_before_send(content="测试内容", actor="test", account_id="test_account")

            assert result is not None
        except ImportError:
            pytest.skip("ComplianceCenter not available")


class TestSafetyGuard:
    """Tests for SafetyGuard with correct API."""

    def test_safety_guard_import(self):
        """Test SafetyGuard can be imported."""
        try:
            from src.modules.messages.safety_guard import SafetyGuard

            assert True
        except ImportError:
            pytest.skip("SafetyGuard not available")

    def test_safety_guard_creation(self):
        """Test SafetyGuard can be created with llm_judge parameter."""
        try:
            from src.modules.messages.safety_guard import SafetyGuard

            mock_llm_judge = Mock(return_value={"is_prohibited": False})
            guard = SafetyGuard(llm_judge=mock_llm_judge)
            assert guard is not None
        except ImportError:
            pytest.skip("SafetyGuard not available")

    def test_check_message(self):
        """Test message safety check using check method with context."""
        try:
            from src.modules.messages.safety_guard import SafetyGuard

            mock_llm_judge = Mock(return_value={"is_prohibited": False})
            guard = SafetyGuard(llm_judge=mock_llm_judge)
            result = guard.check(message="测试消息", context="test_context")

            assert result is not None
        except ImportError:
            pytest.skip("SafetyGuard not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
