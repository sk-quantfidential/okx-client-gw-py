"""OKX WebSocket client implementation.

Extends the generic WsClient from client-gw-core with OKX-specific
subscription handling and message parsing for public market data channels.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from client_gw_core import BackoffConfig, WsClient, get_logger

from okx_client_gw.core.config import DEFAULT_CONFIG, OkxConfig
from okx_client_gw.core.exceptions import OkxConnectionError, OkxWebSocketError
from okx_client_gw.domain.enums import Bar, ChannelType, InstType

logger = get_logger(__name__)


class OkxWsClient(WsClient):
    """OKX WebSocket client for public market data streaming.

    Extends the generic WsClient with OKX-specific:
    - Subscription handling (subscribe/unsubscribe operations)
    - Message routing for push data
    - Ping/pong keep-alive (OKX requires ping every 30 seconds)
    - Channel management

    OKX WebSocket message formats:
    - Subscribe: {"op": "subscribe", "args": [{"channel": "...", "instId": "..."}]}
    - Unsubscribe: {"op": "unsubscribe", "args": [...]}
    - Push data: {"arg": {...}, "data": [...]}
    - Error: {"event": "error", "code": "...", "msg": "..."}

    Example:
        async with okx_ws_session() as client:
            await client.subscribe_tickers("BTC-USDT")
            async for msg in client.messages():
                if msg.get("arg", {}).get("channel") == "tickers":
                    print(msg["data"])
    """

    # OKX requires ping every 30 seconds
    PING_INTERVAL = 25.0

    def __init__(
        self,
        config: OkxConfig | None = None,
        *,
        backoff_config: BackoffConfig | None = None,
        throttle_delay: float | None = None,
    ) -> None:
        """Initialize the OKX WebSocket client.

        Args:
            config: OKX configuration. Uses DEFAULT_CONFIG if not provided.
            backoff_config: Configuration for exponential backoff on reconnection.
            throttle_delay: Delay in seconds between sends to avoid flooding.
        """
        self._config = config or DEFAULT_CONFIG
        super().__init__(
            url=self._config.effective_ws_public_url,
            backoff_config=backoff_config
            or BackoffConfig(
                initial_delay=1.0,
                max_delay=60.0,
                multiplier=2.0,
                jitter=0.1,
            ),
            throttle_delay=throttle_delay,
        )
        self._subscriptions: set[tuple[str, str | None, str | None]] = set()
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._ping_task: asyncio.Task[None] | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        from client_gw_core import ConnectionState

        return self.state == ConnectionState.CONNECTED

    @property
    def subscriptions(self) -> set[tuple[str, str | None, str | None]]:
        """Get current subscriptions as (channel, inst_id, inst_type) tuples."""
        return self._subscriptions.copy()

    async def connect(self) -> None:
        """Connect to OKX WebSocket server and start background tasks.

        Raises:
            OkxConnectionError: If connection fails
        """
        try:
            # Start the connection loop in background
            self._running = True
            await self.start()
            # Give connection time to establish
            await asyncio.sleep(0.5)

            # Start ping task
            self._ping_task = asyncio.create_task(self._ping_loop())

        except Exception as e:
            self._running = False
            raise OkxConnectionError(f"Failed to connect to OKX WebSocket: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from OKX WebSocket server."""
        self._running = False

        # Cancel ping task
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Stop WebSocket connection
        await self.stop()
        self._subscriptions.clear()

    async def subscribe(
        self,
        channel: str,
        inst_id: str | None = None,
        inst_type: str | None = None,
    ) -> None:
        """Subscribe to a WebSocket channel.

        Args:
            channel: Channel name (e.g., "tickers", "candle1H", "books5")
            inst_id: Instrument ID (e.g., "BTC-USDT")
            inst_type: Instrument type filter (e.g., "SPOT")

        Raises:
            OkxWebSocketError: If subscription fails
        """
        arg: dict[str, str] = {"channel": channel}
        if inst_id:
            arg["instId"] = inst_id
        if inst_type:
            arg["instType"] = inst_type

        message = {"op": "subscribe", "args": [arg]}

        try:
            await self._send_json(message)
            self._subscriptions.add((channel, inst_id, inst_type))
            logger.info(f"Subscribed to channel={channel}, inst_id={inst_id}, inst_type={inst_type}")
        except Exception as e:
            raise OkxWebSocketError(f"Failed to subscribe to {channel}: {e}") from e

    async def unsubscribe(
        self,
        channel: str,
        inst_id: str | None = None,
        inst_type: str | None = None,
    ) -> None:
        """Unsubscribe from a WebSocket channel.

        Args:
            channel: Channel name
            inst_id: Instrument ID
            inst_type: Instrument type filter

        Raises:
            OkxWebSocketError: If unsubscription fails
        """
        arg: dict[str, str] = {"channel": channel}
        if inst_id:
            arg["instId"] = inst_id
        if inst_type:
            arg["instType"] = inst_type

        message = {"op": "unsubscribe", "args": [arg]}

        try:
            await self._send_json(message)
            self._subscriptions.discard((channel, inst_id, inst_type))
            logger.info(f"Unsubscribed from channel={channel}, inst_id={inst_id}, inst_type={inst_type}")
        except Exception as e:
            raise OkxWebSocketError(f"Failed to unsubscribe from {channel}: {e}") from e

    async def subscribe_tickers(
        self,
        inst_id: str | None = None,
        inst_type: InstType | None = None,
    ) -> None:
        """Subscribe to ticker updates.

        Args:
            inst_id: Specific instrument ID (e.g., "BTC-USDT")
            inst_type: Instrument type for all instruments of that type
        """
        await self.subscribe(
            ChannelType.TICKERS.value,
            inst_id=inst_id,
            inst_type=inst_type.value if inst_type else None,
        )

    async def subscribe_trades(
        self,
        inst_id: str,
    ) -> None:
        """Subscribe to trade updates for an instrument.

        Args:
            inst_id: Instrument ID (required)
        """
        await self.subscribe(ChannelType.TRADES.value, inst_id=inst_id)

    async def subscribe_candles(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
    ) -> None:
        """Subscribe to candlestick updates.

        Args:
            inst_id: Instrument ID
            bar: Candlestick granularity
        """
        channel = ChannelType.candle_channel(bar)
        await self.subscribe(channel.value, inst_id=inst_id)

    async def subscribe_orderbook(
        self,
        inst_id: str,
        depth: int = 5,
    ) -> None:
        """Subscribe to order book updates.

        Args:
            inst_id: Instrument ID
            depth: Order book depth (5 for books5, 50 for books50-l2-tbt, 400 for books-l2-tbt)
        """
        if depth == 5:
            channel = ChannelType.BOOKS5.value
        elif depth == 50:
            channel = ChannelType.BOOKS50_TBT.value
        elif depth == 400:
            channel = ChannelType.BOOKS_L2_TBT.value
        else:
            channel = ChannelType.BOOKS.value

        await self.subscribe(channel, inst_id=inst_id)

    async def subscribe_bbo(
        self,
        inst_id: str,
    ) -> None:
        """Subscribe to best bid/offer updates.

        Args:
            inst_id: Instrument ID
        """
        await self.subscribe(ChannelType.BBO_TBT.value, inst_id=inst_id)

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message to the WebSocket server.

        Args:
            message: Message to send (will be JSON-encoded)

        Raises:
            OkxWebSocketError: If send fails
        """
        await self._send_json(message)

    async def receive(self) -> dict[str, Any]:
        """Receive a single message from the WebSocket server.

        Returns:
            Parsed JSON message

        Raises:
            OkxWebSocketError: If receive fails or connection closed
        """
        try:
            return await self._message_queue.get()
        except Exception as e:
            raise OkxWebSocketError(f"Failed to receive message: {e}") from e

    async def messages(self) -> AsyncIterator[dict[str, Any]]:
        """Iterate over incoming WebSocket messages.

        Yields:
            Parsed JSON messages as they arrive

        Example:
            async for msg in client.messages():
                if "data" in msg:
                    process_data(msg["data"])
        """
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                yield msg
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def ping(self) -> None:
        """Send a ping to keep the connection alive.

        OKX requires ping every 30 seconds. This sends the string "ping"
        which OKX responds to with "pong".

        Raises:
            OkxWebSocketError: If ping fails
        """
        try:
            # OKX uses literal string "ping" not WebSocket ping frame
            await self._send_raw("ping")
            logger.debug("Sent ping")
        except Exception as e:
            raise OkxWebSocketError(f"Failed to send ping: {e}") from e

    async def _send_json(self, message: dict[str, Any]) -> None:
        """Send a JSON message."""
        await self._send_raw(json.dumps(message))

    async def _send_raw(self, message: str) -> None:
        """Send a raw string message."""
        # Use send_raw from base class with a dummy message ID
        # since OKX uses subscription model, not request/response
        await self.send_raw(message=message, msg_id=0)

    async def _ping_loop(self) -> None:
        """Background task to send periodic pings."""
        while self._running:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if self.is_connected:
                    await self.ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Ping failed: {e}")

    def _extract_message_id(self, data: str) -> int | None:
        """Extract message ID from OKX response.

        OKX push messages don't have IDs - they use subscription model.
        We return 0 for all messages since we don't use request/response correlation.
        """
        # OKX subscription responses don't have message IDs
        # Return 0 to match our dummy msg_id in _send_raw
        return 0

    async def __aenter__(self) -> OkxWsClient:
        """Enter async context manager - connects to WebSocket."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager - disconnects from WebSocket."""
        await self.disconnect()


@asynccontextmanager
async def okx_ws_session(
    config: OkxConfig | None = None,
    *,
    backoff_config: BackoffConfig | None = None,
) -> AsyncIterator[OkxWsClient]:
    """Async context manager for OKX WebSocket client lifecycle.

    Automatically connects and disconnects the WebSocket connection.

    Usage:
        async with okx_ws_session() as client:
            await client.subscribe_tickers("BTC-USDT")
            async for msg in client.messages():
                print(msg)

    Args:
        config: OKX configuration
        backoff_config: Reconnection backoff configuration

    Yields:
        OkxWsClient: The connected client instance
    """
    client = OkxWsClient(config=config, backoff_config=backoff_config)

    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()
