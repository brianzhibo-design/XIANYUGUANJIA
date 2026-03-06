from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLiteWsClient:
    """Cover uncovered lines in ws_client.py."""

    def _make_client(self):
        from src.lite.ws_client import LiteWsClient
        return LiteWsClient(
            ws_url="wss://test.ws",
            cookie="test_cookie",
            device_id="dev1",
            my_user_id="user1",
            token_provider=AsyncMock(return_value="token1"),
        )

    def test_update_cookie(self):
        client = self._make_client()
        client.update_cookie("new_cookie")
        assert client.cookie == "new_cookie"

    def test_update_auth_context(self):
        client = self._make_client()
        client.update_auth_context(cookie="c2", device_id="d2", my_user_id="u2")
        assert client.cookie == "c2"
        assert client.device_id == "d2"
        assert client.my_user_id == "u2"

    def test_update_auth_context_empty(self):
        client = self._make_client()
        client.update_auth_context(cookie="", device_id="", my_user_id="")
        assert client.cookie == ""
        assert client.device_id == ""
        assert client.my_user_id == ""

    async def test_force_reconnect_no_ws(self):
        client = self._make_client()
        client._ws = None
        await client.force_reconnect("test")
        assert client._reconnect_requested.is_set()

    async def test_force_reconnect_with_ws(self):
        client = self._make_client()
        mock_ws = AsyncMock()
        client._ws = mock_ws
        await client.force_reconnect("test")
        assert client._reconnect_requested.is_set()
        mock_ws.close.assert_called_once()

    async def test_force_reconnect_close_fails(self):
        client = self._make_client()
        mock_ws = AsyncMock()
        mock_ws.close.side_effect = RuntimeError("close failed")
        client._ws = mock_ws
        await client.force_reconnect("test")
        assert client._reconnect_requested.is_set()


class TestLiteMain:
    """Cover uncovered lines in __main__.py."""

    def test_try_parse_quote_request_valid(self):
        from src.lite.__main__ import _try_parse_quote_request
        req = _try_parse_quote_request("北京到上海 2kg")
        assert req is not None
        assert req.origin == "北京"
        assert req.destination == "上海"
        assert req.weight == 2.0

    def test_try_parse_quote_request_jin(self):
        from src.lite.__main__ import _try_parse_quote_request
        req = _try_parse_quote_request("广州到深圳 4斤")
        assert req is not None
        assert req.weight == 2.0

    def test_try_parse_quote_request_invalid(self):
        from src.lite.__main__ import _try_parse_quote_request
        assert _try_parse_quote_request("hello world") is None
        assert _try_parse_quote_request("北京到上海") is None
        assert _try_parse_quote_request("2kg") is None

    async def test_token_provider_success(self):
        from src.lite.__main__ import _token_provider
        api_client = AsyncMock()
        api_client.get_token = AsyncMock(return_value="token_ok")
        cookie_renewal = AsyncMock()
        result = await _token_provider(api_client, cookie_renewal)
        assert result == "token_ok"

    async def test_token_provider_retry_after_renewal(self):
        from src.lite.__main__ import _token_provider
        api_client = AsyncMock()
        api_client.get_token = AsyncMock(side_effect=[Exception("fail"), "token_renewed"])
        cookie_renewal = AsyncMock()
        cookie_renewal.handle_auth_failure = AsyncMock(return_value=True)
        result = await _token_provider(api_client, cookie_renewal)
        assert result == "token_renewed"

    async def test_token_provider_renewal_fails(self):
        from src.lite.__main__ import _token_provider
        api_client = AsyncMock()
        api_client.get_token = AsyncMock(side_effect=Exception("fail"))
        cookie_renewal = AsyncMock()
        cookie_renewal.handle_auth_failure = AsyncMock(return_value=False)
        with pytest.raises(Exception, match="fail"):
            await _token_provider(api_client, cookie_renewal)

    def test_main_function(self):
        from src.lite.__main__ import main
        with patch("src.lite.__main__.asyncio") as mock_asyncio:
            main()
            mock_asyncio.run.assert_called_once()


class TestXianyuApi:
    """Cover uncovered lines in xianyu_api.py."""

    async def test_get_token_no_success_in_ret(self):
        from src.lite.xianyu_api import XianyuApiClient
        client = XianyuApiClient.__new__(XianyuApiClient)
        client._token = None
        client._token_ts = 0.0
        client.cookie_text = "test_cookie"
        client.cookies = {"_m_h5_tk": "tokenseed_12345"}
        client.user_id = "u1"
        client.device_id = "d1"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ret": ["ERROR::some error"], "data": {}}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Token API failed"):
                await client.get_token(force_refresh=True)

    async def test_get_token_missing_access_token(self):
        from src.lite.xianyu_api import XianyuApiClient
        client = XianyuApiClient.__new__(XianyuApiClient)
        client._token = None
        client._token_ts = 0.0
        client.cookie_text = "test_cookie"
        client.cookies = {"_m_h5_tk": "tokenseed_12345"}
        client.user_id = "u1"
        client.device_id = "d1"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ret": ["SUCCESS::调用成功"], "data": {}}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="accessToken missing"):
                await client.get_token(force_refresh=True)
