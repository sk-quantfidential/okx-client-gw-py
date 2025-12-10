"""Private WebSocket client protocol interface for OKX API.

Defines the interface for authenticated OKX WebSocket client implementations.
Extends the base WebSocket protocol with login authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from okx_client_gw.ports.ws_client import OkxWsClientProtocol

if TYPE_CHECKING:
    from okx_client_gw.domain.enums import InstType


@runtime_checkable
class OkxPrivateWsClientProtocol(OkxWsClientProtocol, Protocol):
    """Protocol for authenticated OKX Private WebSocket clients.

    Extends OkxWsClientProtocol with:
    - Login authentication using HMAC-SHA256
    - Private channel subscriptions (account, positions, orders)

    OKX Private WebSocket requires login before subscribing to channels.
    Login message format:
        {"op": "login", "args": [{
            "apiKey": "...",
            "passphrase": "...",
            "timestamp": "...",
            "sign": "..."
        }]}

    Login signature:
        sign = Base64(HMAC-SHA256(timestamp + "GET" + "/users/self/verify", secretKey))
    """

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated.

        Returns:
            True if login was successful, False otherwise
        """
        ...

    async def login(self) -> bool:
        """Authenticate with OKX Private WebSocket.

        Login uses HMAC-SHA256 signature:
            sign = Base64(HMAC-SHA256(timestamp + "GET" + "/users/self/verify", secretKey))

        Returns:
            True if login successful.

        Raises:
            OkxAuthenticationError: If login fails or times out.
        """
        ...

    async def subscribe_account(self) -> None:
        """Subscribe to account balance updates.

        Channel: account
        Requires authentication.

        Data pushed when account balance changes.

        Raises:
            OkxWebSocketError: If not authenticated
        """
        ...

    async def subscribe_positions(
        self,
        inst_type: InstType | None = None,
        inst_family: str | None = None,
        inst_id: str | None = None,
    ) -> None:
        """Subscribe to position updates.

        Channel: positions
        Requires authentication.

        Args:
            inst_type: Instrument type filter.
            inst_family: Instrument family filter.
            inst_id: Specific instrument ID filter.

        Raises:
            OkxWebSocketError: If not authenticated
        """
        ...

    async def subscribe_orders(
        self,
        inst_type: InstType | None = None,
        inst_family: str | None = None,
        inst_id: str | None = None,
    ) -> None:
        """Subscribe to order updates.

        Channel: orders
        Requires authentication.

        Args:
            inst_type: Instrument type filter (default: ANY).
            inst_family: Instrument family filter.
            inst_id: Specific instrument ID filter.

        Raises:
            OkxWebSocketError: If not authenticated
        """
        ...

    async def subscribe_balance_and_position(self) -> None:
        """Subscribe to combined balance and position updates.

        Channel: balance_and_position
        Requires authentication.

        More efficient than subscribing to both account and positions separately.

        Raises:
            OkxWebSocketError: If not authenticated
        """
        ...
