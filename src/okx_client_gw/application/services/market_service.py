"""Market data service for OKX API.

High-level service for fetching market data with automatic pagination
and convenience methods. Uses dependency injection for the HTTP client.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING

from okx_client_gw.application.commands.market_commands import (
    GetCandlesCommand,
    GetHistoryCandlesCommand,
    GetOrderBookCommand,
    GetTickerCommand,
    GetTickersCommand,
    GetTradesCommand,
)
from okx_client_gw.domain.enums import Bar, InstType
from okx_client_gw.domain.models.candle import Candle
from okx_client_gw.domain.models.orderbook import OrderBook
from okx_client_gw.domain.models.ticker import Ticker
from okx_client_gw.domain.models.trade import Trade

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class MarketDataService:
    """Service for fetching OKX market data.

    Provides high-level methods for fetching market data with:
    - Automatic pagination for large data sets
    - Streaming via async generators
    - Deduplication of overlapping results

    Example:
        async with OkxHttpClient() as client:
            service = MarketDataService(client)

            # Get single ticker
            ticker = await service.get_ticker("BTC-USDT")

            # Stream candles with pagination
            async for candle in service.stream_candles(
                "BTC-USDT",
                bar=Bar.H1,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
            ):
                print(candle)
    """

    def __init__(self, client: OkxHttpClientProtocol) -> None:
        """Initialize market data service.

        Args:
            client: OKX HTTP client (injected dependency)
        """
        self._client = client

    async def get_ticker(self, inst_id: str) -> Ticker:
        """Get ticker for an instrument.

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT")

        Returns:
            Ticker object
        """
        cmd = GetTickerCommand(inst_id)
        return await cmd.invoke(self._client)

    async def get_tickers(self, inst_type: InstType) -> list[Ticker]:
        """Get all tickers for an instrument type.

        Args:
            inst_type: Instrument type (SPOT, SWAP, etc.)

        Returns:
            List of Ticker objects
        """
        cmd = GetTickersCommand(inst_type)
        return await cmd.invoke(self._client)

    async def get_orderbook(
        self,
        inst_id: str,
        depth: int = 20,
    ) -> OrderBook:
        """Get order book for an instrument.

        Args:
            inst_id: Instrument ID
            depth: Order book depth (1, 5, 20, 50, 100, 400)

        Returns:
            OrderBook object
        """
        cmd = GetOrderBookCommand(inst_id, depth)
        return await cmd.invoke(self._client)

    async def get_trades(
        self,
        inst_id: str,
        limit: int = 100,
    ) -> list[Trade]:
        """Get recent trades for an instrument.

        Args:
            inst_id: Instrument ID
            limit: Number of trades (max 500)

        Returns:
            List of Trade objects (newest first)
        """
        cmd = GetTradesCommand(inst_id, limit)
        return await cmd.invoke(self._client)

    async def get_candles(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Get candlestick data with automatic pagination.

        Fetches all candles in the date range, handling pagination
        automatically. Returns candles sorted in chronological order.

        Args:
            inst_id: Instrument ID
            bar: Candlestick granularity
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            limit: Maximum total candles to fetch (None = unlimited)

        Returns:
            List of Candle objects sorted by timestamp (oldest first)
        """
        candles: list[Candle] = []
        count = 0

        async for candle in self.stream_candles(
            inst_id,
            bar,
            start_date=start_date,
            end_date=end_date,
        ):
            candles.append(candle)
            count += 1
            if limit and count >= limit:
                break

        # Sort chronologically (oldest first)
        return sorted(candles, key=lambda c: c.timestamp)

    async def stream_candles(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AsyncIterator[Candle]:
        """Stream candlestick data with automatic pagination.

        Yields candles as they are fetched, handling pagination
        automatically. OKX returns candles in reverse chronological
        order (newest first), so this streams newest to oldest.

        Args:
            inst_id: Instrument ID
            bar: Candlestick granularity
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Yields:
            Candle objects (newest first due to OKX API ordering)
        """
        before = end_date
        seen_timestamps: set[datetime] = set()

        while True:
            cmd = GetCandlesCommand(
                inst_id,
                bar,
                before=before,
                after=start_date,
                limit=GetCandlesCommand.MAX_LIMIT,
            )
            batch = await cmd.invoke(self._client)

            if not batch:
                break

            for candle in batch:
                # Deduplicate in case of overlapping results
                if candle.timestamp not in seen_timestamps:
                    seen_timestamps.add(candle.timestamp)
                    yield candle

            # Get oldest candle timestamp for next page
            oldest = min(c.timestamp for c in batch)

            # Stop if we've reached start_date
            if start_date and oldest <= start_date:
                break

            # Stop if no more data
            if len(batch) < GetCandlesCommand.MAX_LIMIT:
                break

            # Set before to oldest timestamp for next page
            before = oldest

    async def stream_history_candles(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AsyncIterator[Candle]:
        """Stream historical candlestick data.

        Uses the history endpoint for older data that may not be
        available from the regular candles endpoint.

        Args:
            inst_id: Instrument ID
            bar: Candlestick granularity
            start_date: Start of date range
            end_date: End of date range

        Yields:
            Candle objects (newest first)
        """
        before = end_date
        seen_timestamps: set[datetime] = set()

        while True:
            cmd = GetHistoryCandlesCommand(
                inst_id,
                bar,
                before=before,
                after=start_date,
                limit=GetHistoryCandlesCommand.MAX_LIMIT,
            )
            batch = await cmd.invoke(self._client)

            if not batch:
                break

            for candle in batch:
                if candle.timestamp not in seen_timestamps:
                    seen_timestamps.add(candle.timestamp)
                    yield candle

            oldest = min(c.timestamp for c in batch)

            if start_date and oldest <= start_date:
                break

            if len(batch) < GetHistoryCandlesCommand.MAX_LIMIT:
                break

            before = oldest
