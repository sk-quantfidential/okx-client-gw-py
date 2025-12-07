"""WebSocket client protocol interface for OKX API.

Defines the interface for OKX WebSocket client implementations using Protocol
for structural subtyping. Supports OKX public and private WebSocket channels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@runtime_checkable
class OkxWsClientProtocol(Protocol):
    """Protocol defining the interface for OKX WebSocket clients.

    Supports subscription to OKX WebSocket channels:
    - Public channels (tickers, trades, candles, orderbook)
    - Private channels (orders, positions, account) - requires authentication

    OKX WebSocket message format:
    - Subscribe: {"op": "subscribe", "args": [{"channel": "...", "instId": "..."}]}
    - Unsubscribe: {"op": "unsubscribe", "args": [...]}
    - Push data: {"arg": {...}, "data": [...]}

    Any class implementing these methods can be used as an OKX WebSocket client.
    """

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected, False otherwise
        """
        ...

    async def connect(self) -> None:
        """Connect to OKX WebSocket server.

        Raises:
            OkxConnectionError: If connection fails
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from OKX WebSocket server."""
        ...

    async def subscribe(
        self,
        channel: str,
        inst_id: str | None = None,
        inst_type: str | None = None,
    ) -> None:
        """Subscribe to a WebSocket channel.

        Args:
            channel: Channel name (e.g., "tickers", "candle1H", "books5")
            inst_id: Instrument ID (e.g., "BTC-USDT") - required for most channels
            inst_type: Instrument type filter (e.g., "SPOT") - for some channels

        Raises:
            OkxWebSocketError: If subscription fails
        """
        ...

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
        ...

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message to the WebSocket server.

        Args:
            message: Message to send (will be JSON-encoded)

        Raises:
            OkxWebSocketError: If send fails
        """
        ...

    async def receive(self) -> dict[str, Any]:
        """Receive a single message from the WebSocket server.

        Returns:
            Parsed JSON message

        Raises:
            OkxWebSocketError: If receive fails or connection closed
        """
        ...

    def messages(self) -> AsyncIterator[dict[str, Any]]:
        """Iterate over incoming WebSocket messages.

        Yields:
            Parsed JSON messages as they arrive

        Example:
            async for msg in client.messages():
                if "data" in msg:
                    process_data(msg["data"])
        """
        ...

    async def ping(self) -> None:
        """Send a ping to keep the connection alive.

        OKX requires ping every 30 seconds to maintain connection.

        Raises:
            OkxWebSocketError: If ping fails
        """
        ...

    async def __aenter__(self) -> OkxWsClientProtocol:
        """Enter async context manager - connects to WebSocket.

        Returns:
            Self for use in async with statement
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager - disconnects from WebSocket.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        ...
