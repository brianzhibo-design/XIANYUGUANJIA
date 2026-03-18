"""Tests for create_browser_client factory."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.error_handler import BrowserError


@pytest.mark.asyncio
async def test_create_browser_client_success():
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_class = MagicMock(return_value=mock_client)

    with patch("src.core.drissionpage_client.DrissionPageBrowserClient", mock_class):
        from src.core.browser_client import create_browser_client
        client = await create_browser_client()
        assert client is mock_client


@pytest.mark.asyncio
async def test_create_browser_client_connect_fails():
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(return_value=False)
    mock_class = MagicMock(return_value=mock_client)

    with patch("src.core.drissionpage_client.DrissionPageBrowserClient", mock_class):
        from src.core.browser_client import create_browser_client
        with pytest.raises(BrowserError):
            await create_browser_client()


@pytest.mark.asyncio
async def test_create_browser_client_import_error():
    import sys
    import src.core.browser_client as bc_mod

    with patch.dict(sys.modules, {"src.core.drissionpage_client": None}):
        with pytest.raises(BrowserError):
            await bc_mod.create_browser_client()
