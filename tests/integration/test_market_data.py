"""Integration tests for OKX market data endpoints.

These tests hit the live OKX API. Run with:
    PYTHONPATH=src pytest tests/integration/ -v

@package: tests.integration
"""

from __future__ import annotations

import pytest

from okx_client_gw.application.commands.instrument_commands import (
    GetInstrumentCommand,
    GetInstrumentsCommand,
)
from okx_client_gw.application.commands.market_commands import (
    GetCandlesCommand,
    GetHistoryCandlesCommand,
    GetOrderBookCommand,
    GetTickerCommand,
    GetTickersCommand,
    GetTradesCommand,
)
from okx_client_gw.application.services import InstrumentService, MarketDataService
from okx_client_gw.domain.enums import Bar, InstType
from okx_client_gw.domain.models import Candle, Instrument, OrderBook, Ticker, Trade


class TestGetInstrumentsIntegration:
    """Integration tests for instrument endpoints."""

    @pytest.mark.asyncio
    async def test_get_spot_instruments(self, okx_http_client) -> None:
        """Test fetching all SPOT instruments from live API."""
        cmd = GetInstrumentsCommand(InstType.SPOT)
        instruments = await cmd.invoke(okx_http_client)

        assert len(instruments) > 0
        assert all(isinstance(inst, Instrument) for inst in instruments)
        assert all(inst.inst_type == InstType.SPOT for inst in instruments)

        # BTC-USDT should exist
        btc_usdt = next((i for i in instruments if i.inst_id == "BTC-USDT"), None)
        assert btc_usdt is not None
        assert btc_usdt.base_ccy == "BTC"
        assert btc_usdt.quote_ccy == "USDT"

    @pytest.mark.asyncio
    async def test_get_swap_instruments(self, okx_http_client) -> None:
        """Test fetching all SWAP instruments from live API."""
        cmd = GetInstrumentsCommand(InstType.SWAP)
        instruments = await cmd.invoke(okx_http_client)

        assert len(instruments) > 0
        assert all(inst.inst_type == InstType.SWAP for inst in instruments)

        # BTC-USDT-SWAP should exist
        btc_swap = next((i for i in instruments if i.inst_id == "BTC-USDT-SWAP"), None)
        assert btc_swap is not None
        assert btc_swap.settle_ccy == "USDT"

    @pytest.mark.asyncio
    async def test_get_single_instrument(self, okx_http_client) -> None:
        """Test fetching a single instrument by ID."""
        cmd = GetInstrumentCommand(InstType.SPOT, "BTC-USDT")
        instrument = await cmd.invoke(okx_http_client)

        assert instrument.inst_id == "BTC-USDT"
        assert instrument.inst_type == InstType.SPOT
        assert instrument.base_ccy == "BTC"
        assert instrument.quote_ccy == "USDT"
        assert instrument.tick_sz > 0
        assert instrument.lot_sz > 0


class TestGetTickerIntegration:
    """Integration tests for ticker endpoints."""

    @pytest.mark.asyncio
    async def test_get_ticker(self, okx_http_client) -> None:
        """Test fetching ticker for BTC-USDT."""
        cmd = GetTickerCommand("BTC-USDT")
        ticker = await cmd.invoke(okx_http_client)

        assert isinstance(ticker, Ticker)
        assert ticker.inst_id == "BTC-USDT"
        assert ticker.last > 0
        assert ticker.bid_px > 0
        assert ticker.ask_px > 0
        assert ticker.ask_px >= ticker.bid_px  # Ask should be >= Bid

    @pytest.mark.asyncio
    async def test_get_tickers(self, okx_http_client) -> None:
        """Test fetching all SPOT tickers."""
        cmd = GetTickersCommand(InstType.SPOT)
        tickers = await cmd.invoke(okx_http_client)

        assert len(tickers) > 0
        assert all(isinstance(t, Ticker) for t in tickers)

        # BTC-USDT should be in there
        btc_ticker = next((t for t in tickers if t.inst_id == "BTC-USDT"), None)
        assert btc_ticker is not None


class TestGetCandlesIntegration:
    """Integration tests for candle/OHLCV endpoints."""

    @pytest.mark.asyncio
    async def test_get_candles_1h(self, okx_http_client) -> None:
        """Test fetching 1-hour candles for BTC-USDT."""
        cmd = GetCandlesCommand("BTC-USDT", Bar.H1, limit=10)
        candles = await cmd.invoke(okx_http_client)

        assert len(candles) > 0
        assert len(candles) <= 10
        assert all(isinstance(c, Candle) for c in candles)

        for candle in candles:
            assert candle.high >= candle.low
            assert candle.high >= candle.open
            assert candle.high >= candle.close
            assert candle.low <= candle.open
            assert candle.low <= candle.close
            assert candle.volume >= 0

    @pytest.mark.asyncio
    async def test_get_candles_different_bars(self, okx_http_client) -> None:
        """Test fetching candles with different bar sizes."""
        for bar in [Bar.M1, Bar.M5, Bar.M15, Bar.H1, Bar.D1_UTC]:
            cmd = GetCandlesCommand("BTC-USDT", bar, limit=5)
            candles = await cmd.invoke(okx_http_client)

            assert len(candles) > 0, f"No candles returned for {bar}"
            assert all(isinstance(c, Candle) for c in candles)

    @pytest.mark.asyncio
    async def test_get_history_candles(self, okx_http_client) -> None:
        """Test fetching historical candles."""
        cmd = GetHistoryCandlesCommand("BTC-USDT", Bar.D1_UTC, limit=50)
        candles = await cmd.invoke(okx_http_client)

        assert len(candles) > 0
        assert len(candles) <= 50
        assert all(isinstance(c, Candle) for c in candles)


class TestGetOrderBookIntegration:
    """Integration tests for order book endpoint."""

    @pytest.mark.asyncio
    async def test_get_orderbook(self, okx_http_client) -> None:
        """Test fetching order book for BTC-USDT."""
        cmd = GetOrderBookCommand("BTC-USDT", depth=20)
        orderbook = await cmd.invoke(okx_http_client)

        assert isinstance(orderbook, OrderBook)
        assert orderbook.inst_id == "BTC-USDT"
        assert len(orderbook.bids) > 0
        assert len(orderbook.asks) > 0

        # Verify bid/ask ordering
        if len(orderbook.bids) > 1:
            assert orderbook.bids[0].price >= orderbook.bids[1].price
        if len(orderbook.asks) > 1:
            assert orderbook.asks[0].price <= orderbook.asks[1].price

        # Best ask should be > best bid
        assert orderbook.best_ask_price > orderbook.best_bid_price

    @pytest.mark.asyncio
    async def test_get_orderbook_different_depths(self, okx_http_client) -> None:
        """Test order book with different depth values."""
        for depth in [1, 5, 20]:
            cmd = GetOrderBookCommand("BTC-USDT", depth=depth)
            orderbook = await cmd.invoke(okx_http_client)

            assert len(orderbook.bids) <= depth
            assert len(orderbook.asks) <= depth


class TestGetTradesIntegration:
    """Integration tests for trades endpoint."""

    @pytest.mark.asyncio
    async def test_get_trades(self, okx_http_client) -> None:
        """Test fetching recent trades for BTC-USDT."""
        cmd = GetTradesCommand("BTC-USDT", limit=50)
        trades = await cmd.invoke(okx_http_client)

        assert len(trades) > 0
        assert len(trades) <= 50
        assert all(isinstance(t, Trade) for t in trades)

        for trade in trades:
            assert trade.inst_id == "BTC-USDT"
            assert trade.px > 0
            assert trade.sz > 0
            assert trade.trade_id


class TestMarketDataServiceIntegration:
    """Integration tests for MarketDataService."""

    @pytest.mark.asyncio
    async def test_service_get_candles(self, market_data_service: MarketDataService) -> None:
        """Test MarketDataService.get_candles()."""
        candles = await market_data_service.get_candles(
            inst_id="ETH-USDT",
            bar=Bar.H1,
            limit=20,
        )

        assert len(candles) > 0
        assert all(isinstance(c, Candle) for c in candles)

    @pytest.mark.asyncio
    async def test_service_get_ticker(self, market_data_service: MarketDataService) -> None:
        """Test MarketDataService.get_ticker()."""
        ticker = await market_data_service.get_ticker("ETH-USDT")

        assert isinstance(ticker, Ticker)
        assert ticker.inst_id == "ETH-USDT"
        assert ticker.last > 0

    @pytest.mark.asyncio
    async def test_service_get_orderbook(self, market_data_service: MarketDataService) -> None:
        """Test MarketDataService.get_orderbook()."""
        orderbook = await market_data_service.get_orderbook("ETH-USDT", depth=20)

        assert isinstance(orderbook, OrderBook)
        assert len(orderbook.bids) > 0
        assert len(orderbook.asks) > 0


class TestInstrumentServiceIntegration:
    """Integration tests for InstrumentService."""

    @pytest.mark.asyncio
    async def test_service_get_instruments(
        self, instrument_service: InstrumentService
    ) -> None:
        """Test InstrumentService.get_instruments()."""
        instruments = await instrument_service.get_instruments(InstType.SPOT)

        assert len(instruments) > 0
        assert all(isinstance(i, Instrument) for i in instruments)

    @pytest.mark.asyncio
    async def test_service_get_instrument(
        self, instrument_service: InstrumentService
    ) -> None:
        """Test InstrumentService.get_instrument()."""
        instrument = await instrument_service.get_instrument(InstType.SPOT, "BTC-USDT")

        assert isinstance(instrument, Instrument)
        assert instrument.inst_id == "BTC-USDT"
