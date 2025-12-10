"""Private WebSocket streaming service for OKX API.

High-level service for streaming real-time private data from OKX WebSocket API.
Handles message parsing and routing for account, positions, and orders.

Requires authentication - uses OkxPrivateWsClient.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from okx_client_gw.domain.enums import InstType
from okx_client_gw.domain.models.account import AccountBalance, BalanceDetail
from okx_client_gw.domain.models.order import Order
from okx_client_gw.domain.models.position import Position

if TYPE_CHECKING:
    from okx_client_gw.ports.ws_private_client import OkxPrivateWsClientProtocol


@dataclass(frozen=True)
class BalanceAndPosition:
    """Combined balance and position update from balance_and_position channel.

    Attributes:
        balances: List of balance details that changed.
        positions: List of positions that changed.
        event_type: Type of event ("snapshot" or "delivered").
        push_time: Time when the update was pushed.
    """

    balances: list[BalanceDetail]
    positions: list[Position]
    event_type: str
    push_time: datetime | None


class PrivateStreamingService:
    """Service for streaming real-time OKX private (authenticated) data.

    Provides high-level methods for subscribing to and streaming private data:
    - Account balance updates
    - Position updates
    - Order updates
    - Combined balance and position updates

    Requires authentication - client must be logged in before streaming.

    Example:
        credentials = OkxCredentials.from_env()
        async with OkxPrivateWsClient(credentials=credentials) as ws_client:
            service = PrivateStreamingService(ws_client)

            # Stream order updates
            async for order in service.stream_orders():
                print(f"Order {order.ord_id}: {order.state}")

            # Stream account balance
            async for balance in service.stream_account():
                print(f"Total equity: {balance.total_eq}")
    """

    def __init__(self, client: OkxPrivateWsClientProtocol) -> None:
        """Initialize private streaming service.

        Args:
            client: Authenticated OKX Private WebSocket client (injected dependency)
        """
        self._client = client

    async def stream_account(self) -> AsyncIterator[AccountBalance]:
        """Stream account balance updates.

        Subscribes to account channel and yields AccountBalance objects
        when account balance changes.

        Yields:
            AccountBalance objects as they arrive

        Raises:
            OkxWebSocketError: If not authenticated
        """
        await self._client.subscribe_account()

        async for msg in self._client.messages():
            if not self._is_data_message(msg, "account"):
                continue

            for data in msg.get("data", []):
                yield AccountBalance.from_okx_dict(data)

    async def stream_positions(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
    ) -> AsyncIterator[Position]:
        """Stream position updates.

        Subscribes to positions channel and yields Position objects
        when positions change.

        Args:
            inst_type: Filter by instrument type
            inst_id: Filter by specific instrument ID

        Yields:
            Position objects as they arrive

        Raises:
            OkxWebSocketError: If not authenticated
        """
        await self._client.subscribe_positions(
            inst_type=inst_type,
            inst_id=inst_id,
        )

        async for msg in self._client.messages():
            if not self._is_data_message(msg, "positions"):
                continue

            for data in msg.get("data", []):
                yield Position.from_okx_dict(data)

    async def stream_orders(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
    ) -> AsyncIterator[Order]:
        """Stream order updates.

        Subscribes to orders channel and yields Order objects
        when order state changes.

        Args:
            inst_type: Filter by instrument type (default: ANY)
            inst_id: Filter by specific instrument ID

        Yields:
            Order objects as they arrive

        Raises:
            OkxWebSocketError: If not authenticated
        """
        await self._client.subscribe_orders(
            inst_type=inst_type,
            inst_id=inst_id,
        )

        async for msg in self._client.messages():
            if not self._is_data_message(msg, "orders"):
                continue

            for data in msg.get("data", []):
                yield Order.from_okx_dict(data)

    async def stream_balance_and_position(self) -> AsyncIterator[BalanceAndPosition]:
        """Stream combined balance and position updates.

        Subscribes to balance_and_position channel which is more efficient
        than subscribing to both account and positions separately.

        Yields:
            BalanceAndPosition objects containing both balance and position updates

        Raises:
            OkxWebSocketError: If not authenticated
        """
        await self._client.subscribe_balance_and_position()

        async for msg in self._client.messages():
            if not self._is_data_message(msg, "balance_and_position"):
                continue

            for data in msg.get("data", []):
                yield self._parse_balance_and_position(data)

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

    def _parse_balance_and_position(self, data: dict) -> BalanceAndPosition:
        """Parse balance_and_position channel data.

        Args:
            data: Raw data from balance_and_position channel

        Returns:
            BalanceAndPosition with parsed balances and positions
        """
        # Parse balances
        balances = [
            BalanceDetail.from_okx_dict(b)
            for b in data.get("balData", [])
        ]

        # Parse positions
        positions = [
            Position.from_okx_dict(p)
            for p in data.get("posData", [])
        ]

        # Parse push time
        push_time = None
        if data.get("pTime"):
            push_time = datetime.fromtimestamp(int(data["pTime"]) / 1000, tz=UTC)

        return BalanceAndPosition(
            balances=balances,
            positions=positions,
            event_type=data.get("eventType", "snapshot"),
            push_time=push_time,
        )


class MultiChannelPrivateStreamingService:
    """Service for streaming from multiple private channels simultaneously.

    Provides methods to subscribe to multiple private channels and
    route messages to appropriate handlers.

    Example:
        credentials = OkxCredentials.from_env()
        async with OkxPrivateWsClient(credentials=credentials) as ws_client:
            service = MultiChannelPrivateStreamingService(ws_client)

            # Subscribe to multiple channels
            await service.subscribe_orders()
            await service.subscribe_positions()

            # Process all messages
            async for msg_type, data in service.stream():
                if msg_type == "order":
                    print(f"Order: {data.ord_id} = {data.state}")
                elif msg_type == "position":
                    print(f"Position: {data.inst_id} = {data.pos}")
    """

    def __init__(self, client: OkxPrivateWsClientProtocol) -> None:
        """Initialize multi-channel private streaming service.

        Args:
            client: Authenticated OKX Private WebSocket client (injected dependency)
        """
        self._client = client
        self._account_subscribed = False
        self._positions_subscribed = False
        self._orders_subscribed = False
        self._balance_and_position_subscribed = False

    async def subscribe_account(self) -> None:
        """Subscribe to account balance updates."""
        if not self._account_subscribed:
            await self._client.subscribe_account()
            self._account_subscribed = True

    async def subscribe_positions(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
    ) -> None:
        """Subscribe to position updates.

        Args:
            inst_type: Filter by instrument type
            inst_id: Filter by specific instrument ID
        """
        if not self._positions_subscribed:
            await self._client.subscribe_positions(
                inst_type=inst_type,
                inst_id=inst_id,
            )
            self._positions_subscribed = True

    async def subscribe_orders(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
    ) -> None:
        """Subscribe to order updates.

        Args:
            inst_type: Filter by instrument type (default: ANY)
            inst_id: Filter by specific instrument ID
        """
        if not self._orders_subscribed:
            await self._client.subscribe_orders(
                inst_type=inst_type,
                inst_id=inst_id,
            )
            self._orders_subscribed = True

    async def subscribe_balance_and_position(self) -> None:
        """Subscribe to combined balance and position updates."""
        if not self._balance_and_position_subscribed:
            await self._client.subscribe_balance_and_position()
            self._balance_and_position_subscribed = True

    async def stream(
        self,
    ) -> AsyncIterator[tuple[str, AccountBalance | Position | Order | BalanceAndPosition]]:
        """Stream all subscribed private channels.

        Yields tuples of (message_type, data) where message_type is one of:
        - "account": AccountBalance object
        - "position": Position object
        - "order": Order object
        - "balance_and_position": BalanceAndPosition object

        Yields:
            Tuple of (message_type, parsed_data)
        """
        async for msg in self._client.messages():
            if "data" not in msg:
                continue

            arg = msg.get("arg", {})
            channel = arg.get("channel", "")

            for data in msg.get("data", []):
                if channel == "account":
                    yield "account", AccountBalance.from_okx_dict(data)
                elif channel == "positions":
                    yield "position", Position.from_okx_dict(data)
                elif channel == "orders":
                    yield "order", Order.from_okx_dict(data)
                elif channel == "balance_and_position":
                    yield "balance_and_position", self._parse_balance_and_position(data)

    def _parse_balance_and_position(self, data: dict) -> BalanceAndPosition:
        """Parse balance_and_position channel data."""
        balances = [
            BalanceDetail.from_okx_dict(b)
            for b in data.get("balData", [])
        ]
        positions = [
            Position.from_okx_dict(p)
            for p in data.get("posData", [])
        ]
        push_time = None
        if data.get("pTime"):
            push_time = datetime.fromtimestamp(int(data["pTime"]) / 1000, tz=UTC)

        return BalanceAndPosition(
            balances=balances,
            positions=positions,
            event_type=data.get("eventType", "snapshot"),
            push_time=push_time,
        )
