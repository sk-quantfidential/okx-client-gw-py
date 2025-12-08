"""Unit tests for market data commands with respx mocking."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import respx
from httpx import Response

from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.application.commands.market_commands import (
    GetCandlesCommand,
    GetHistoryCandlesCommand,
    GetOrderBookCommand,
    GetTickerCommand,
    GetTickersCommand,
    GetTradesCommand,
)
from okx_client_gw.core.exceptions import OkxValidationError
from okx_client_gw.domain.enums import Bar, InstType


class TestGetTickerCommand:
    """Tests for GetTickerCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_ticker_success(self) -> None:
        """Test fetching a single ticker."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SPOT",
                    "instId": "BTC-USDT",
                    "last": "50000.5",
                    "lastSz": "0.1",
                    "askPx": "50001.0",
                    "askSz": "1.5",
                    "bidPx": "50000.0",
                    "bidSz": "2.0",
                    "open24h": "49000.0",
                    "high24h": "51000.0",
                    "low24h": "48500.0",
                    "volCcy24h": "100000000.0",
                    "vol24h": "2000.0",
                    "ts": "1704067200000",
                }
            ],
        }

        respx.get("https://www.okx.com/api/v5/market/ticker").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetTickerCommand("BTC-USDT")
            ticker = await cmd.invoke(client)

        assert ticker.inst_id == "BTC-USDT"
        assert ticker.last == Decimal("50000.5")
        assert ticker.bid_px == Decimal("50000.0")
        assert ticker.ask_px == Decimal("50001.0")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_ticker_params(self) -> None:
        """Test that correct parameters are sent."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SPOT",
                    "instId": "ETH-USDT",
                    "last": "3000.0",
                    "lastSz": "1.0",
                    "askPx": "3001.0",
                    "askSz": "10.0",
                    "bidPx": "2999.0",
                    "bidSz": "10.0",
                    "open24h": "2900.0",
                    "high24h": "3100.0",
                    "low24h": "2850.0",
                    "volCcy24h": "50000000.0",
                    "vol24h": "16000.0",
                    "ts": "1704067200000",
                }
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/market/ticker").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetTickerCommand("ETH-USDT")
            await cmd.invoke(client)

        assert route.called
        assert route.calls[0].request.url.params["instId"] == "ETH-USDT"


class TestGetTickersCommand:
    """Tests for GetTickersCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_tickers_success(self) -> None:
        """Test fetching multiple tickers."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SPOT",
                    "instId": "BTC-USDT",
                    "last": "50000.0",
                    "lastSz": "0.1",
                    "askPx": "50001.0",
                    "askSz": "1.0",
                    "bidPx": "49999.0",
                    "bidSz": "1.0",
                    "open24h": "49000.0",
                    "high24h": "51000.0",
                    "low24h": "48500.0",
                    "volCcy24h": "100000000.0",
                    "vol24h": "2000.0",
                    "ts": "1704067200000",
                },
                {
                    "instType": "SPOT",
                    "instId": "ETH-USDT",
                    "last": "3000.0",
                    "lastSz": "1.0",
                    "askPx": "3001.0",
                    "askSz": "10.0",
                    "bidPx": "2999.0",
                    "bidSz": "10.0",
                    "open24h": "2900.0",
                    "high24h": "3100.0",
                    "low24h": "2850.0",
                    "volCcy24h": "50000000.0",
                    "vol24h": "16000.0",
                    "ts": "1704067200000",
                },
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/market/tickers").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetTickersCommand(InstType.SPOT)
            tickers = await cmd.invoke(client)

        assert len(tickers) == 2
        assert tickers[0].inst_id == "BTC-USDT"
        assert tickers[1].inst_id == "ETH-USDT"
        assert route.calls[0].request.url.params["instType"] == "SPOT"


class TestGetCandlesCommand:
    """Tests for GetCandlesCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_candles_success(self) -> None:
        """Test fetching candlestick data."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                ["1704067200000", "50000.0", "51000.0", "49500.0", "50500.0", "100.0", "5000000.0", "5025000.0", "1"],
                ["1704063600000", "49500.0", "50200.0", "49000.0", "50000.0", "150.0", "7500000.0", "7425000.0", "1"],
            ],
        }

        respx.get("https://www.okx.com/api/v5/market/candles").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetCandlesCommand("BTC-USDT", Bar.H1, limit=100)
            candles = await cmd.invoke(client)

        assert len(candles) == 2
        assert candles[0].open == Decimal("50000.0")
        assert candles[0].high == Decimal("51000.0")
        assert candles[0].low == Decimal("49500.0")
        assert candles[0].close == Decimal("50500.0")
        assert candles[0].confirm is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_candles_with_pagination(self) -> None:
        """Test candles command with before/after parameters."""
        mock_response = {"code": "0", "msg": "", "data": []}

        route = respx.get("https://www.okx.com/api/v5/market/candles").mock(
            return_value=Response(200, json=mock_response)
        )

        before_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        after_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        async with OkxHttpClient() as client:
            cmd = GetCandlesCommand(
                "BTC-USDT",
                Bar.H1,
                before=before_time,
                after=after_time,
                limit=50,
            )
            await cmd.invoke(client)

        params = route.calls[0].request.url.params
        assert params["instId"] == "BTC-USDT"
        assert params["bar"] == "1H"
        assert params["limit"] == "50"
        assert "before" in params
        assert "after" in params

    def test_get_candles_validation_limit_too_high(self) -> None:
        """Test validation error for limit > 300."""
        with pytest.raises(OkxValidationError) as exc_info:
            GetCandlesCommand("BTC-USDT", limit=301)

        assert exc_info.value.field == "limit"
        assert "300" in exc_info.value.reason

    def test_get_candles_validation_limit_too_low(self) -> None:
        """Test validation error for limit < 1."""
        with pytest.raises(OkxValidationError) as exc_info:
            GetCandlesCommand("BTC-USDT", limit=0)

        assert exc_info.value.field == "limit"


class TestGetHistoryCandlesCommand:
    """Tests for GetHistoryCandlesCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_history_candles_success(self) -> None:
        """Test fetching historical candlestick data."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                ["1703980800000", "48000.0", "49000.0", "47500.0", "48500.0", "200.0", "9600000.0", "9700000.0", "1"],
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/market/history-candles").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetHistoryCandlesCommand("BTC-USDT", Bar.D1_UTC, limit=50)
            candles = await cmd.invoke(client)

        assert len(candles) == 1
        assert candles[0].open == Decimal("48000.0")
        assert route.calls[0].request.url.params["bar"] == "1Dutc"

    def test_history_candles_validation_limit(self) -> None:
        """Test validation error for limit > 100."""
        with pytest.raises(OkxValidationError) as exc_info:
            GetHistoryCandlesCommand("BTC-USDT", limit=101)

        assert exc_info.value.field == "limit"
        assert "100" in exc_info.value.reason


class TestGetOrderBookCommand:
    """Tests for GetOrderBookCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_orderbook_success(self) -> None:
        """Test fetching order book."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "bids": [
                        ["50000.0", "1.5", "0", "3"],
                        ["49999.0", "2.0", "0", "5"],
                    ],
                    "asks": [
                        ["50001.0", "1.0", "0", "2"],
                        ["50002.0", "3.0", "0", "4"],
                    ],
                    "ts": "1704067200000",
                }
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/market/books").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetOrderBookCommand("BTC-USDT", depth=20)
            orderbook = await cmd.invoke(client)

        assert orderbook.inst_id == "BTC-USDT"
        assert len(orderbook.bids) == 2
        assert len(orderbook.asks) == 2
        assert orderbook.best_bid_price == Decimal("50000.0")
        assert orderbook.best_ask_price == Decimal("50001.0")
        assert route.calls[0].request.url.params["sz"] == "20"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_orderbook_different_depths(self) -> None:
        """Test order book with different depth values."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [{"bids": [], "asks": [], "ts": "1704067200000"}],
        }

        for depth in [1, 5, 20, 50, 100, 400]:
            route = respx.get("https://www.okx.com/api/v5/market/books").mock(
                return_value=Response(200, json=mock_response)
            )

            async with OkxHttpClient() as client:
                cmd = GetOrderBookCommand("BTC-USDT", depth=depth)
                await cmd.invoke(client)

            assert route.calls[-1].request.url.params["sz"] == str(depth)

    def test_orderbook_validation_invalid_depth(self) -> None:
        """Test validation error for invalid depth."""
        with pytest.raises(OkxValidationError) as exc_info:
            GetOrderBookCommand("BTC-USDT", depth=25)

        assert exc_info.value.field == "depth"
        assert "1" in exc_info.value.reason  # Should list valid values


class TestGetTradesCommand:
    """Tests for GetTradesCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_trades_success(self) -> None:
        """Test fetching recent trades."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT",
                    "tradeId": "123456",
                    "px": "50000.0",
                    "sz": "0.5",
                    "side": "buy",
                    "ts": "1704067200000",
                },
                {
                    "instId": "BTC-USDT",
                    "tradeId": "123457",
                    "px": "50001.0",
                    "sz": "0.3",
                    "side": "sell",
                    "ts": "1704067201000",
                },
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/market/trades").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetTradesCommand("BTC-USDT", limit=100)
            trades = await cmd.invoke(client)

        assert len(trades) == 2
        assert trades[0].px == Decimal("50000.0")
        assert trades[0].is_buy is True
        assert trades[1].is_sell is True
        assert route.calls[0].request.url.params["limit"] == "100"

    def test_trades_validation_limit_too_high(self) -> None:
        """Test validation error for limit > 500."""
        with pytest.raises(OkxValidationError) as exc_info:
            GetTradesCommand("BTC-USDT", limit=501)

        assert exc_info.value.field == "limit"
        assert "500" in exc_info.value.reason

    def test_trades_validation_limit_too_low(self) -> None:
        """Test validation error for limit < 1."""
        with pytest.raises(OkxValidationError) as exc_info:
            GetTradesCommand("BTC-USDT", limit=0)

        assert exc_info.value.field == "limit"
