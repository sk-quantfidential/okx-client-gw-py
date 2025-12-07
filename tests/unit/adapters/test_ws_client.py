"""Unit tests for OKX WebSocket client."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from okx_client_gw.adapters.websocket import OkxWsClient
from okx_client_gw.core.config import OkxConfig
from okx_client_gw.domain.enums import Bar, ChannelType, InstType


class TestOkxWsClientInit:
    """Test OkxWsClient initialization."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        client = OkxWsClient()
        assert client.url == "wss://ws.okx.com:8443/ws/v5/public"
        assert client._subscriptions == set()

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = OkxConfig(use_demo=True)
        client = OkxWsClient(config=config)
        assert "wspap.okx.com" in client.url

    def test_init_subscriptions_empty(self) -> None:
        """Test that subscriptions start empty."""
        client = OkxWsClient()
        assert len(client.subscriptions) == 0


class TestOkxWsClientSubscriptions:
    """Test subscription methods."""

    @pytest.fixture
    def mock_client(self) -> OkxWsClient:
        """Create a client with mocked send."""
        client = OkxWsClient()
        client._send_json = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_subscribe(self, mock_client: OkxWsClient) -> None:
        """Test basic subscribe."""
        await mock_client.subscribe("tickers", inst_id="BTC-USDT")

        mock_client._send_json.assert_called_once()
        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["op"] == "subscribe"
        assert call_args["args"][0]["channel"] == "tickers"
        assert call_args["args"][0]["instId"] == "BTC-USDT"
        assert ("tickers", "BTC-USDT", None) in mock_client.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_with_inst_type(self, mock_client: OkxWsClient) -> None:
        """Test subscribe with instrument type."""
        await mock_client.subscribe("tickers", inst_type="SPOT")

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["instType"] == "SPOT"
        assert ("tickers", None, "SPOT") in mock_client.subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe(self, mock_client: OkxWsClient) -> None:
        """Test unsubscribe."""
        # First subscribe
        mock_client._subscriptions.add(("tickers", "BTC-USDT", None))

        await mock_client.unsubscribe("tickers", inst_id="BTC-USDT")

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["op"] == "unsubscribe"
        assert ("tickers", "BTC-USDT", None) not in mock_client.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_tickers(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_tickers convenience method."""
        await mock_client.subscribe_tickers(inst_id="ETH-USDT")

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "tickers"
        assert call_args["args"][0]["instId"] == "ETH-USDT"

    @pytest.mark.asyncio
    async def test_subscribe_tickers_by_type(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_tickers with instrument type."""
        await mock_client.subscribe_tickers(inst_type=InstType.SPOT)

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "tickers"
        assert call_args["args"][0]["instType"] == "SPOT"

    @pytest.mark.asyncio
    async def test_subscribe_trades(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_trades convenience method."""
        await mock_client.subscribe_trades("BTC-USDT")

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "trades"
        assert call_args["args"][0]["instId"] == "BTC-USDT"

    @pytest.mark.asyncio
    async def test_subscribe_candles(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_candles convenience method."""
        await mock_client.subscribe_candles("BTC-USDT", Bar.H1)

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == ChannelType.CANDLE_1H.value

    @pytest.mark.asyncio
    async def test_subscribe_candles_different_bars(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_candles with different bar sizes."""
        test_cases = [
            (Bar.M1, ChannelType.CANDLE_1M.value),
            (Bar.M5, ChannelType.CANDLE_5M.value),
            (Bar.H4, ChannelType.CANDLE_4H.value),
            (Bar.D1_UTC, ChannelType.CANDLE_1D_UTC.value),
        ]
        for bar, expected_channel in test_cases:
            mock_client._send_json.reset_mock()
            await mock_client.subscribe_candles("BTC-USDT", bar)

            call_args = mock_client._send_json.call_args[0][0]
            assert call_args["args"][0]["channel"] == expected_channel, f"Failed for bar {bar}"

    @pytest.mark.asyncio
    async def test_subscribe_orderbook_depth5(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_orderbook with depth 5."""
        await mock_client.subscribe_orderbook("BTC-USDT", depth=5)

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "books5"

    @pytest.mark.asyncio
    async def test_subscribe_orderbook_depth50(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_orderbook with depth 50."""
        await mock_client.subscribe_orderbook("BTC-USDT", depth=50)

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "books50-l2-tbt"

    @pytest.mark.asyncio
    async def test_subscribe_orderbook_depth400(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_orderbook with depth 400."""
        await mock_client.subscribe_orderbook("BTC-USDT", depth=400)

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "books-l2-tbt"

    @pytest.mark.asyncio
    async def test_subscribe_orderbook_default_depth(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_orderbook with default/other depth."""
        await mock_client.subscribe_orderbook("BTC-USDT", depth=20)

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "books"

    @pytest.mark.asyncio
    async def test_subscribe_bbo(self, mock_client: OkxWsClient) -> None:
        """Test subscribe_bbo convenience method."""
        await mock_client.subscribe_bbo("BTC-USDT")

        call_args = mock_client._send_json.call_args[0][0]
        assert call_args["args"][0]["channel"] == "bbo-tbt"


class TestOkxWsClientMessageExtraction:
    """Test message ID extraction."""

    def test_extract_message_id_returns_zero(self) -> None:
        """Test that _extract_message_id always returns 0.

        OKX uses subscription model, not request/response,
        so we don't need message ID correlation.
        """
        client = OkxWsClient()
        # Any message should return 0
        assert client._extract_message_id('{"event": "subscribe"}') == 0
        assert client._extract_message_id('{"data": []}') == 0
        assert client._extract_message_id("pong") == 0


class TestOkxWsClientPing:
    """Test ping functionality."""

    def test_ping_interval(self) -> None:
        """Test that ping interval is set correctly."""
        assert OkxWsClient.PING_INTERVAL == 25.0


class TestOkxWsClientConnectionProperties:
    """Test connection-related properties."""

    def test_is_connected_when_disconnected(self) -> None:
        """Test is_connected returns False when not connected."""
        client = OkxWsClient()
        # New client should not be connected
        assert client.is_connected is False

    def test_subscriptions_returns_copy(self) -> None:
        """Test that subscriptions property returns a copy."""
        client = OkxWsClient()
        client._subscriptions.add(("tickers", "BTC-USDT", None))

        subs = client.subscriptions
        subs.add(("trades", "ETH-USDT", None))

        # Original should not be modified
        assert len(client._subscriptions) == 1
        assert ("trades", "ETH-USDT", None) not in client._subscriptions
