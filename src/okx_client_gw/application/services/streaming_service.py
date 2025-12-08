"""WebSocket streaming service for OKX API.

High-level service for streaming real-time market data from OKX WebSocket API.
Handles message parsing and routing for tickers, trades, candles, and order books.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from okx_client_gw.domain.enums import Bar, ChannelType, InstType, OrderBookAction
from okx_client_gw.domain.models.candle import Candle
from okx_client_gw.domain.models.orderbook import OrderBook
from okx_client_gw.domain.models.ticker import Ticker
from okx_client_gw.domain.models.trade import Trade

if TYPE_CHECKING:
    from okx_client_gw.ports.ws_client import OkxWsClientProtocol


class StreamingService:
    """Service for streaming real-time OKX market data.

    Provides high-level methods for subscribing to and streaming market data:
    - Ticker updates
    - Trade updates
    - Candlestick updates
    - Order book updates

    Handles message parsing and converts raw OKX WebSocket messages to domain objects.

    Example:
        async with okx_ws_session() as ws_client:
            service = StreamingService(ws_client)

            # Stream ticker updates
            async for ticker in service.stream_tickers("BTC-USDT"):
                print(f"Price: {ticker.last}")

            # Stream multiple channels
            async for candle in service.stream_candles("ETH-USDT", Bar.M1):
                print(f"Close: {candle.close}")
    """

    def __init__(self, client: OkxWsClientProtocol) -> None:
        """Initialize streaming service.

        Args:
            client: OKX WebSocket client (injected dependency)
        """
        self._client = client

    async def stream_tickers(
        self,
        inst_id: str | None = None,
        inst_type: InstType | None = None,
    ) -> AsyncIterator[Ticker]:
        """Stream ticker updates.

        Subscribes to ticker channel and yields Ticker objects.

        Args:
            inst_id: Specific instrument ID (e.g., "BTC-USDT")
            inst_type: Instrument type for all instruments of that type

        Yields:
            Ticker objects as they arrive
        """
        await self._client.subscribe(
            ChannelType.TICKERS.value,
            inst_id=inst_id,
            inst_type=inst_type.value if inst_type else None,
        )

        async for msg in self._client.messages():
            if not self._is_data_message(msg, ChannelType.TICKERS.value):
                continue

            for data in msg.get("data", []):
                yield Ticker.from_okx_dict(data)

    async def stream_trades(
        self,
        inst_id: str,
    ) -> AsyncIterator[Trade]:
        """Stream trade updates.

        Subscribes to trades channel and yields Trade objects.

        Args:
            inst_id: Instrument ID (required)

        Yields:
            Trade objects as they arrive
        """
        await self._client.subscribe(ChannelType.TRADES.value, inst_id=inst_id)

        async for msg in self._client.messages():
            if not self._is_data_message(msg, ChannelType.TRADES.value):
                continue

            for data in msg.get("data", []):
                yield Trade.from_okx_dict(data)

    async def stream_candles(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
    ) -> AsyncIterator[Candle]:
        """Stream candlestick updates.

        Subscribes to candle channel and yields Candle objects.
        Note: Only yields when candle is updated, not historical data.

        Args:
            inst_id: Instrument ID
            bar: Candlestick granularity

        Yields:
            Candle objects as they are updated
        """
        channel = ChannelType.candle_channel(bar)
        await self._client.subscribe(channel.value, inst_id=inst_id)

        async for msg in self._client.messages():
            if not self._is_data_message(msg, channel.value):
                continue

            for data in msg.get("data", []):
                # OKX candle data is an array of arrays
                if isinstance(data, list):
                    yield Candle.from_okx_array(data)

    async def stream_orderbook(
        self,
        inst_id: str,
        depth: int = 5,
    ) -> AsyncIterator[tuple[OrderBook, OrderBookAction]]:
        """Stream order book updates.

        Subscribes to order book channel and yields OrderBook objects
        with the action type (snapshot or update).

        Args:
            inst_id: Instrument ID
            depth: Order book depth (5, 50, or 400)

        Yields:
            Tuple of (OrderBook, OrderBookAction) - the order book and whether
            it's a snapshot or incremental update
        """
        if depth == 5:
            channel = ChannelType.BOOKS5.value
        elif depth == 50:
            channel = ChannelType.BOOKS50_TBT.value
        elif depth == 400:
            channel = ChannelType.BOOKS_L2_TBT.value
        else:
            channel = ChannelType.BOOKS.value

        await self._client.subscribe(channel, inst_id=inst_id)

        async for msg in self._client.messages():
            if not self._is_data_message(msg, channel):
                continue

            action = self._parse_orderbook_action(msg)

            for data in msg.get("data", []):
                yield OrderBook.from_okx_dict(data), action

    async def stream_bbo(
        self,
        inst_id: str,
    ) -> AsyncIterator[OrderBook]:
        """Stream best bid/offer updates.

        Subscribes to BBO channel and yields simplified OrderBook objects
        with only the best bid and ask.

        Args:
            inst_id: Instrument ID

        Yields:
            OrderBook objects with single best bid/ask levels
        """
        await self._client.subscribe(ChannelType.BBO_TBT.value, inst_id=inst_id)

        async for msg in self._client.messages():
            if not self._is_data_message(msg, ChannelType.BBO_TBT.value):
                continue

            for data in msg.get("data", []):
                yield OrderBook.from_okx_dict(data)

    def _is_data_message(self, msg: dict[str, Any], channel: str) -> bool:
        """Check if message is a data push for the specified channel.

        OKX push messages have format: {"arg": {"channel": "...", ...}, "data": [...]}

        Args:
            msg: The WebSocket message
            channel: Expected channel name

        Returns:
            True if this is a data message for the channel
        """
        if "data" not in msg:
            return False

        arg = msg.get("arg", {})
        return arg.get("channel") == channel

    def _parse_orderbook_action(self, msg: dict[str, Any]) -> OrderBookAction:
        """Parse order book action from message.

        Args:
            msg: The WebSocket message

        Returns:
            OrderBookAction.SNAPSHOT or OrderBookAction.UPDATE
        """
        action = msg.get("action", "snapshot")
        if action == "update":
            return OrderBookAction.UPDATE
        return OrderBookAction.SNAPSHOT


class MultiChannelStreamingService:
    """Service for streaming from multiple channels simultaneously.

    Provides methods to subscribe to multiple instruments/channels and
    route messages to appropriate handlers.

    Example:
        async with okx_ws_session() as ws_client:
            service = MultiChannelStreamingService(ws_client)

            # Subscribe to multiple tickers
            await service.subscribe_tickers(["BTC-USDT", "ETH-USDT"])

            # Process all messages
            async for msg_type, data in service.stream():
                if msg_type == "ticker":
                    print(f"Ticker: {data.inst_id} = {data.last}")
                elif msg_type == "trade":
                    print(f"Trade: {data.price}")
    """

    def __init__(self, client: OkxWsClientProtocol) -> None:
        """Initialize multi-channel streaming service.

        Args:
            client: OKX WebSocket client (injected dependency)
        """
        self._client = client
        self._ticker_subs: set[str] = set()
        self._trade_subs: set[str] = set()
        self._candle_subs: dict[str, Bar] = {}
        self._orderbook_subs: dict[str, int] = {}

    async def subscribe_tickers(self, inst_ids: list[str]) -> None:
        """Subscribe to tickers for multiple instruments.

        Args:
            inst_ids: List of instrument IDs
        """
        for inst_id in inst_ids:
            if inst_id not in self._ticker_subs:
                await self._client.subscribe(ChannelType.TICKERS.value, inst_id=inst_id)
                self._ticker_subs.add(inst_id)

    async def subscribe_trades(self, inst_ids: list[str]) -> None:
        """Subscribe to trades for multiple instruments.

        Args:
            inst_ids: List of instrument IDs
        """
        for inst_id in inst_ids:
            if inst_id not in self._trade_subs:
                await self._client.subscribe(ChannelType.TRADES.value, inst_id=inst_id)
                self._trade_subs.add(inst_id)

    async def subscribe_candles(
        self,
        inst_ids: list[str],
        bar: Bar = Bar.H1,
    ) -> None:
        """Subscribe to candles for multiple instruments.

        Args:
            inst_ids: List of instrument IDs
            bar: Candlestick granularity
        """
        channel = ChannelType.candle_channel(bar)
        for inst_id in inst_ids:
            key = f"{inst_id}:{bar.value}"
            if key not in self._candle_subs:
                await self._client.subscribe(channel.value, inst_id=inst_id)
                self._candle_subs[key] = bar

    async def subscribe_orderbooks(
        self,
        inst_ids: list[str],
        depth: int = 5,
    ) -> None:
        """Subscribe to order books for multiple instruments.

        Args:
            inst_ids: List of instrument IDs
            depth: Order book depth
        """
        if depth == 5:
            channel = ChannelType.BOOKS5.value
        elif depth == 50:
            channel = ChannelType.BOOKS50_TBT.value
        elif depth == 400:
            channel = ChannelType.BOOKS_L2_TBT.value
        else:
            channel = ChannelType.BOOKS.value

        for inst_id in inst_ids:
            key = f"{inst_id}:{depth}"
            if key not in self._orderbook_subs:
                await self._client.subscribe(channel, inst_id=inst_id)
                self._orderbook_subs[key] = depth

    async def stream(
        self,
    ) -> AsyncIterator[tuple[str, Ticker | Trade | Candle | OrderBook]]:
        """Stream all subscribed channels.

        Yields tuples of (message_type, data) where message_type is one of:
        - "ticker": Ticker object
        - "trade": Trade object
        - "candle": Candle object
        - "orderbook": OrderBook object

        Yields:
            Tuple of (message_type, parsed_data)
        """
        async for msg in self._client.messages():
            if "data" not in msg:
                continue

            arg = msg.get("arg", {})
            channel = arg.get("channel", "")

            for data in msg.get("data", []):
                if channel == ChannelType.TICKERS.value:
                    yield "ticker", Ticker.from_okx_dict(data)
                elif channel == ChannelType.TRADES.value:
                    yield "trade", Trade.from_okx_dict(data)
                elif channel.startswith("candle"):
                    if isinstance(data, list):
                        yield "candle", Candle.from_okx_array(data)
                elif channel.startswith("books") or channel == ChannelType.BBO_TBT.value:
                    yield "orderbook", OrderBook.from_okx_dict(data)
