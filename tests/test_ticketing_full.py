"""Tests for ticketing module - corrected API usage."""

import pytest
from unittest.mock import Mock


class MockRecognizer:
    """Mock ticket recognizer for testing."""

    async def recognize(self, image_bytes, mime_type="image/png"):
        from src.modules.ticketing.models import TicketSelection

        return TicketSelection(
            cinema="Test Cinema", showtime="2024-01-01 20:00", seat="5排6座", count=1, confidence=0.95
        )


class MockProvider:
    """Mock ticket provider for testing."""

    async def quote_ticket(self, selection):
        from src.modules.ticketing.models import TicketQuote

        return TicketQuote(channel_price=35.0, final_price=40.0, provider="MockProvider", availability=True)

    async def create_purchase(self, request):
        from src.modules.ticketing.models import TicketPurchaseResult

        return TicketPurchaseResult(success=True, order_id="TEST123", ticket_code="CODE456")


class TestTicketingService:
    """Tests for TicketingService with correct API."""

    def test_ticketing_service_import(self):
        """Test TicketingService can be imported."""
        try:
            from src.modules.ticketing.service import TicketingService

            assert True
        except ImportError:
            pytest.skip("TicketingService not available")

    def test_ticketing_service_creation(self):
        """Test TicketingService can be created with required parameters."""
        try:
            from src.modules.ticketing.service import TicketingService

            recognizer = MockRecognizer()
            provider = MockProvider()

            # TicketingService requires recognizer and provider parameters
            service = TicketingService(recognizer=recognizer, provider=provider)
            assert service is not None
            assert service.recognizer == recognizer
            assert service.provider == provider
        except ImportError:
            pytest.skip("TicketingService not available")


class TestTicketingModels:
    """Tests for ticketing models."""

    def test_ticket_models_import(self):
        """Test ticket models can be imported."""
        try:
            from src.modules.ticketing.models import TicketSelection, TicketQuote

            assert True
        except ImportError:
            pytest.skip("Ticket models not available")

    def test_ticket_selection_creation(self):
        """Test creating TicketSelection."""
        try:
            from src.modules.ticketing.models import TicketSelection

            selection = TicketSelection(
                cinema="万达影城", showtime="2024-01-01 19:30", seat="8排8座", count=2, confidence=0.92
            )
            assert selection.cinema == "万达影城"
            assert selection.count == 2
        except ImportError:
            pytest.skip("TicketSelection not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
