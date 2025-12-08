"""Unit tests for WebSocket streaming services."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from okx_client_gw.application.services.streaming_service import (
    MultiChannelStreamingService,
    StreamingService,
)
from okx_client_gw.domain.enums import Bar, ChannelType, InstType, OrderBookAction


class MockWsClient:
    """Mock WebSocket client for testing."""

    def __init__(self, messages: list[dict] | None = None) -> None:
        self.messages_list = messages or []
        self.subscribe = AsyncMock()
        self._message_index = 0

    async def messages(self):
        """Yield mock messages."""
        for msg in self.messages_list:
            yield msg


class TestStreamingServiceInit:
    """Test StreamingService initialization."""

    def test_init(self) -> None:
        """Test service initialization."""
        mock_client = MockWsClient()
        service = StreamingService(mock_client)
        assert service._client is mock_client


class TestStreamingServiceTickerStreaming:
    """Test ticker streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_tickers_subscribes_to_channel(self) -> None:
        """Test that stream_tickers subscribes to correct channel."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        # Start iteration (won't yield anything due to empty messages)
        async for _ in service.stream_tickers(inst_id="BTC-USDT"):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.TICKERS.value,
            inst_id="BTC-USDT",
            inst_type=None,
        )

    @pytest.mark.asyncio
    async def test_stream_tickers_with_inst_type(self) -> None:
        """Test subscribing to all tickers of an instrument type."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_tickers(inst_type=InstType.SPOT):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.TICKERS.value,
            inst_id=None,
            inst_type="SPOT",
        )

    @pytest.mark.asyncio
    async def test_stream_tickers_parses_messages(self) -> None:
        """Test that ticker messages are parsed correctly."""
        ticker_msg = {
            "arg": {"channel": "tickers", "instId": "BTC-USDT"},
            "data": [
                {
                    "instType": "SPOT",
                    "instId": "BTC-USDT",
                    "last": "50000.0",
                    "lastSz": "0.1",
                    "askPx": "50001.0",
                    "askSz": "1.0",
                    "bidPx": "49999.0",
                    "bidSz": "1.5",
                    "open24h": "48000.0",
                    "high24h": "51000.0",
                    "low24h": "47500.0",
                    "volCcy24h": "1000000.0",
                    "vol24h": "20.0",
                    "ts": "1704067200000",
                }
            ],
        }
        mock_client = MockWsClient([ticker_msg])
        service = StreamingService(mock_client)

        tickers = []
        async for ticker in service.stream_tickers(inst_id="BTC-USDT"):
            tickers.append(ticker)

        assert len(tickers) == 1
        assert tickers[0].inst_id == "BTC-USDT"
        assert tickers[0].last == Decimal("50000.0")

    @pytest.mark.asyncio
    async def test_stream_tickers_ignores_non_ticker_messages(self) -> None:
        """Test that non-ticker messages are ignored."""
        messages = [
            {"event": "subscribe"},  # Subscribe confirmation
            {"arg": {"channel": "trades"}, "data": []},  # Wrong channel
            {"arg": {"channel": "tickers"}, "data": []},  # Empty data
        ]
        mock_client = MockWsClient(messages)
        service = StreamingService(mock_client)

        tickers = []
        async for ticker in service.stream_tickers(inst_id="BTC-USDT"):
            tickers.append(ticker)

        assert len(tickers) == 0


class TestStreamingServiceTradeStreaming:
    """Test trade streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_trades_subscribes_to_channel(self) -> None:
        """Test that stream_trades subscribes to correct channel."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_trades("ETH-USDT"):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.TRADES.value, inst_id="ETH-USDT"
        )

    @pytest.mark.asyncio
    async def test_stream_trades_parses_messages(self) -> None:
        """Test that trade messages are parsed correctly."""
        trade_msg = {
            "arg": {"channel": "trades", "instId": "ETH-USDT"},
            "data": [
                {
                    "instId": "ETH-USDT",
                    "tradeId": "12345",
                    "px": "3000.0",
                    "sz": "1.5",
                    "side": "buy",
                    "ts": "1704067200000",
                }
            ],
        }
        mock_client = MockWsClient([trade_msg])
        service = StreamingService(mock_client)

        trades = []
        async for trade in service.stream_trades("ETH-USDT"):
            trades.append(trade)

        assert len(trades) == 1
        assert trades[0].inst_id == "ETH-USDT"
        assert trades[0].px == Decimal("3000.0")


class TestStreamingServiceCandleStreaming:
    """Test candle streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_candles_subscribes_to_correct_channel(self) -> None:
        """Test that stream_candles subscribes to correct bar channel."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_candles("BTC-USDT", Bar.H1):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.CANDLE_1H.value, inst_id="BTC-USDT"
        )

    @pytest.mark.asyncio
    async def test_stream_candles_different_bars(self) -> None:
        """Test subscribing to different bar sizes."""
        test_cases = [
            (Bar.M1, ChannelType.CANDLE_1M.value),
            (Bar.M5, ChannelType.CANDLE_5M.value),
            (Bar.H4, ChannelType.CANDLE_4H.value),
        ]

        for bar, expected_channel in test_cases:
            mock_client = MockWsClient([])
            service = StreamingService(mock_client)

            async for _ in service.stream_candles("BTC-USDT", bar):
                pass

            mock_client.subscribe.assert_called_once_with(
                expected_channel, inst_id="BTC-USDT"
            )

    @pytest.mark.asyncio
    async def test_stream_candles_parses_messages(self) -> None:
        """Test that candle messages are parsed correctly."""
        candle_msg = {
            "arg": {"channel": "candle1H", "instId": "BTC-USDT"},
            "data": [
                ["1704067200000", "50000.0", "51000.0", "49500.0", "50500.0", "100.0", "5000000.0", "5025000.0", "1"]
            ],
        }
        mock_client = MockWsClient([candle_msg])
        service = StreamingService(mock_client)

        candles = []
        async for candle in service.stream_candles("BTC-USDT", Bar.H1):
            candles.append(candle)

        assert len(candles) == 1
        assert candles[0].open == Decimal("50000.0")
        assert candles[0].high == Decimal("51000.0")
        assert candles[0].confirm is True


class TestStreamingServiceOrderBookStreaming:
    """Test order book streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_orderbook_depth5(self) -> None:
        """Test subscribing to 5-level order book."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_orderbook("BTC-USDT", depth=5):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.BOOKS5.value, inst_id="BTC-USDT"
        )

    @pytest.mark.asyncio
    async def test_stream_orderbook_depth50(self) -> None:
        """Test subscribing to 50-level order book."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_orderbook("BTC-USDT", depth=50):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.BOOKS50_TBT.value, inst_id="BTC-USDT"
        )

    @pytest.mark.asyncio
    async def test_stream_orderbook_depth400(self) -> None:
        """Test subscribing to 400-level order book."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_orderbook("BTC-USDT", depth=400):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.BOOKS_L2_TBT.value, inst_id="BTC-USDT"
        )

    @pytest.mark.asyncio
    async def test_stream_orderbook_parses_snapshot(self) -> None:
        """Test that order book snapshot messages are parsed correctly."""
        orderbook_msg = {
            "arg": {"channel": "books5", "instId": "BTC-USDT"},
            "action": "snapshot",
            "data": [
                {
                    "instId": "BTC-USDT",
                    "bids": [["50000.0", "1.0", "0", "1"], ["49999.0", "2.0", "0", "2"]],
                    "asks": [["50001.0", "0.5", "0", "1"], ["50002.0", "1.0", "0", "1"]],
                    "ts": "1704067200000",
                }
            ],
        }
        mock_client = MockWsClient([orderbook_msg])
        service = StreamingService(mock_client)

        results = []
        async for orderbook, action in service.stream_orderbook("BTC-USDT", depth=5):
            results.append((orderbook, action))

        assert len(results) == 1
        orderbook, action = results[0]
        assert orderbook.inst_id == "BTC-USDT"
        assert len(orderbook.bids) == 2
        assert action == OrderBookAction.SNAPSHOT

    @pytest.mark.asyncio
    async def test_stream_orderbook_parses_update(self) -> None:
        """Test that order book update messages are parsed correctly."""
        orderbook_msg = {
            "arg": {"channel": "books5", "instId": "BTC-USDT"},
            "action": "update",
            "data": [
                {
                    "instId": "BTC-USDT",
                    "bids": [["50000.0", "1.5", "0", "1"]],
                    "asks": [],
                    "ts": "1704067200000",
                }
            ],
        }
        mock_client = MockWsClient([orderbook_msg])
        service = StreamingService(mock_client)

        results = []
        async for orderbook, action in service.stream_orderbook("BTC-USDT", depth=5):
            results.append((orderbook, action))

        assert len(results) == 1
        _, action = results[0]
        assert action == OrderBookAction.UPDATE


class TestStreamingServiceBBOStreaming:
    """Test BBO streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_bbo_subscribes_to_channel(self) -> None:
        """Test that stream_bbo subscribes to correct channel."""
        mock_client = MockWsClient([])
        service = StreamingService(mock_client)

        async for _ in service.stream_bbo("BTC-USDT"):
            pass

        mock_client.subscribe.assert_called_once_with(
            ChannelType.BBO_TBT.value, inst_id="BTC-USDT"
        )


class TestMultiChannelStreamingService:
    """Test MultiChannelStreamingService."""

    @pytest.mark.asyncio
    async def test_subscribe_tickers_multiple(self) -> None:
        """Test subscribing to multiple tickers."""
        mock_client = MockWsClient([])
        service = MultiChannelStreamingService(mock_client)

        await service.subscribe_tickers(["BTC-USDT", "ETH-USDT"])

        assert mock_client.subscribe.call_count == 2
        assert "BTC-USDT" in service._ticker_subs
        assert "ETH-USDT" in service._ticker_subs

    @pytest.mark.asyncio
    async def test_subscribe_tickers_deduplicates(self) -> None:
        """Test that duplicate subscriptions are ignored."""
        mock_client = MockWsClient([])
        service = MultiChannelStreamingService(mock_client)

        await service.subscribe_tickers(["BTC-USDT"])
        await service.subscribe_tickers(["BTC-USDT"])

        assert mock_client.subscribe.call_count == 1

    @pytest.mark.asyncio
    async def test_subscribe_trades_multiple(self) -> None:
        """Test subscribing to multiple trade channels."""
        mock_client = MockWsClient([])
        service = MultiChannelStreamingService(mock_client)

        await service.subscribe_trades(["BTC-USDT", "ETH-USDT"])

        assert mock_client.subscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_subscribe_candles_multiple(self) -> None:
        """Test subscribing to multiple candle channels."""
        mock_client = MockWsClient([])
        service = MultiChannelStreamingService(mock_client)

        await service.subscribe_candles(["BTC-USDT", "ETH-USDT"], Bar.H1)

        assert mock_client.subscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_subscribe_orderbooks_multiple(self) -> None:
        """Test subscribing to multiple order book channels."""
        mock_client = MockWsClient([])
        service = MultiChannelStreamingService(mock_client)

        await service.subscribe_orderbooks(["BTC-USDT", "ETH-USDT"], depth=5)

        assert mock_client.subscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_stream_routes_messages(self) -> None:
        """Test that stream routes messages to correct types."""
        messages = [
            {
                "arg": {"channel": "tickers"},
                "data": [
                    {
                        "instType": "SPOT",
                        "instId": "BTC-USDT",
                        "last": "50000.0",
                        "lastSz": "0.1",
                        "askPx": "50001.0",
                        "askSz": "1.0",
                        "bidPx": "49999.0",
                        "bidSz": "1.5",
                        "open24h": "48000.0",
                        "high24h": "51000.0",
                        "low24h": "47500.0",
                        "volCcy24h": "1000000.0",
                        "vol24h": "20.0",
                        "ts": "1704067200000",
                    }
                ],
            },
            {
                "arg": {"channel": "trades"},
                "data": [
                    {
                        "instId": "BTC-USDT",
                        "tradeId": "123",
                        "px": "50000.0",
                        "sz": "0.1",
                        "side": "buy",
                        "ts": "1704067200000",
                    }
                ],
            },
        ]
        mock_client = MockWsClient(messages)
        service = MultiChannelStreamingService(mock_client)

        results = []
        async for msg_type, data in service.stream():
            results.append((msg_type, data))

        assert len(results) == 2
        assert results[0][0] == "ticker"
        assert results[1][0] == "trade"


class TestStreamingServiceHelperMethods:
    """Test helper methods."""

    def test_is_data_message_with_matching_channel(self) -> None:
        """Test _is_data_message with matching channel."""
        service = StreamingService(MockWsClient())

        msg = {"arg": {"channel": "tickers"}, "data": [{"price": 100}]}
        assert service._is_data_message(msg, "tickers") is True

    def test_is_data_message_with_non_matching_channel(self) -> None:
        """Test _is_data_message with non-matching channel."""
        service = StreamingService(MockWsClient())

        msg = {"arg": {"channel": "trades"}, "data": [{"price": 100}]}
        assert service._is_data_message(msg, "tickers") is False

    def test_is_data_message_without_data(self) -> None:
        """Test _is_data_message without data field."""
        service = StreamingService(MockWsClient())

        msg = {"event": "subscribe"}
        assert service._is_data_message(msg, "tickers") is False

    def test_parse_orderbook_action_snapshot(self) -> None:
        """Test _parse_orderbook_action for snapshot."""
        service = StreamingService(MockWsClient())

        msg = {"action": "snapshot"}
        assert service._parse_orderbook_action(msg) == OrderBookAction.SNAPSHOT

    def test_parse_orderbook_action_update(self) -> None:
        """Test _parse_orderbook_action for update."""
        service = StreamingService(MockWsClient())

        msg = {"action": "update"}
        assert service._parse_orderbook_action(msg) == OrderBookAction.UPDATE

    def test_parse_orderbook_action_default(self) -> None:
        """Test _parse_orderbook_action default is snapshot."""
        service = StreamingService(MockWsClient())

        msg = {}
        assert service._parse_orderbook_action(msg) == OrderBookAction.SNAPSHOT
