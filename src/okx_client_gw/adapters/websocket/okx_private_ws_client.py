"""OKX Private WebSocket client implementation.

Extends OkxWsClient with authentication for private channels
(account, positions, orders, balance_and_position).

See: https://www.okx.com/docs-v5/en/#overview-websocket-login
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from client_gw_core import BackoffConfig, get_logger

from okx_client_gw.adapters.websocket.okx_ws_client import OkxWsClient
from okx_client_gw.core.auth import OkxCredentials
from okx_client_gw.core.config import DEFAULT_CONFIG, OkxConfig
from okx_client_gw.core.exceptions import OkxAuthenticationError, OkxWebSocketError
from okx_client_gw.domain.enums import InstType

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class OkxPrivateWsClient(OkxWsClient):
    """OKX WebSocket client for private (authenticated) channels.

    Extends OkxWsClient with:
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

    Example:
        credentials = OkxCredentials.from_env()
        async with okx_private_ws_session(credentials=credentials) as client:
            await client.subscribe_orders()
            async for msg in client.messages():
                if msg.get("arg", {}).get("channel") == "orders":
                    process_order(msg["data"])
    """

    # Login timeout in seconds
    LOGIN_TIMEOUT = 10.0

    def __init__(
        self,
        credentials: OkxCredentials,
        config: OkxConfig | None = None,
        *,
        backoff_config: BackoffConfig | None = None,
        throttle_delay: float | None = None,
    ) -> None:
        """Initialize the OKX Private WebSocket client.

        Args:
            credentials: OKX API credentials for authentication.
            config: OKX configuration. Uses DEFAULT_CONFIG if not provided.
            backoff_config: Configuration for exponential backoff on reconnection.
            throttle_delay: Delay in seconds between sends to avoid flooding.
        """
        self._credentials = credentials
        self._config = config or DEFAULT_CONFIG
        self._is_authenticated = False
        self._login_event = asyncio.Event()

        # Initialize parent with private WebSocket URL
        super(OkxWsClient, self).__init__(
            url=self._config.effective_ws_private_url,
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
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._ping_task: asyncio.Task | None = None
        self._receive_task: asyncio.Task | None = None
        self._running = False

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._is_authenticated

    async def connect(self) -> None:
        """Connect to OKX Private WebSocket and authenticate.

        Raises:
            OkxConnectionError: If connection fails.
            OkxAuthenticationError: If login fails.
        """
        # Connect using parent's method
        await super().connect()

        # Now login
        await self.login()

    async def login(self) -> bool:
        """Authenticate with OKX Private WebSocket.

        Login uses HMAC-SHA256 signature:
            sign = Base64(HMAC-SHA256(timestamp + "GET" + "/users/self/verify", secretKey))

        Returns:
            True if login successful.

        Raises:
            OkxAuthenticationError: If login fails or times out.
        """
        # Generate timestamp (seconds since epoch as string)
        timestamp = str(int(time.time()))

        # Generate signature: timestamp + "GET" + "/users/self/verify"
        sign = self._credentials.sign(
            timestamp=timestamp,
            method="GET",
            request_path="/users/self/verify",
            body="",
        )

        login_message = {
            "op": "login",
            "args": [
                {
                    "apiKey": self._credentials.api_key,
                    "passphrase": self._credentials.passphrase,
                    "timestamp": timestamp,
                    "sign": sign,
                }
            ],
        }

        logger.info("Sending login request to private WebSocket")

        try:
            await self._send_json(login_message)

            # Wait for login response
            self._login_event.clear()
            login_success = await self._wait_for_login_response()

            if login_success:
                self._is_authenticated = True
                logger.info("Successfully authenticated with OKX Private WebSocket")
                return True
            else:
                raise OkxAuthenticationError("Login failed - received error response")

        except TimeoutError as e:
            raise OkxAuthenticationError(
                f"Login timed out after {self.LOGIN_TIMEOUT}s"
            ) from e
        except Exception as e:
            raise OkxAuthenticationError(f"Login failed: {e}") from e

    async def _wait_for_login_response(self) -> bool:
        """Wait for login response from server.

        Returns:
            True if login successful, False otherwise.
        """
        start_time = time.time()

        while time.time() - start_time < self.LOGIN_TIMEOUT:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )

                # Check for login response
                if msg.get("event") == "login":
                    if msg.get("code") == "0":
                        return True
                    else:
                        error_msg = msg.get("msg", "Unknown error")
                        logger.error(f"Login failed: {error_msg}")
                        return False

                # Check for error
                if msg.get("event") == "error":
                    error_msg = msg.get("msg", "Unknown error")
                    logger.error(f"Login error: {error_msg}")
                    return False

                # Put non-login messages back for processing
                # (shouldn't happen before login, but just in case)
                await self._message_queue.put(msg)

            except TimeoutError:
                continue

        return False

    async def subscribe_account(self) -> None:
        """Subscribe to account balance updates.

        Channel: account
        Requires authentication.

        Data pushed when account balance changes.
        """
        if not self._is_authenticated:
            raise OkxWebSocketError("Must be authenticated to subscribe to account")

        await self.subscribe("account")
        logger.info("Subscribed to account channel")

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

        Data pushed when positions change.
        """
        if not self._is_authenticated:
            raise OkxWebSocketError("Must be authenticated to subscribe to positions")

        arg: dict[str, str] = {"channel": "positions"}
        if inst_type:
            arg["instType"] = inst_type.value
        if inst_family:
            arg["instFamily"] = inst_family
        if inst_id:
            arg["instId"] = inst_id

        message = {"op": "subscribe", "args": [arg]}
        await self._send_json(message)
        self._subscriptions.add(("positions", inst_id, inst_type.value if inst_type else None))
        logger.info(f"Subscribed to positions channel (inst_type={inst_type}, inst_id={inst_id})")

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

        Data pushed when order state changes.
        """
        if not self._is_authenticated:
            raise OkxWebSocketError("Must be authenticated to subscribe to orders")

        arg: dict[str, str] = {"channel": "orders"}
        # OKX requires instType for orders channel
        arg["instType"] = inst_type.value if inst_type else "ANY"
        if inst_family:
            arg["instFamily"] = inst_family
        if inst_id:
            arg["instId"] = inst_id

        message = {"op": "subscribe", "args": [arg]}
        await self._send_json(message)
        self._subscriptions.add(("orders", inst_id, inst_type.value if inst_type else "ANY"))
        logger.info(f"Subscribed to orders channel (inst_type={inst_type or 'ANY'}, inst_id={inst_id})")

    async def subscribe_balance_and_position(self) -> None:
        """Subscribe to combined balance and position updates.

        Channel: balance_and_position
        Requires authentication.

        More efficient than subscribing to both account and positions separately.
        Pushed when either balance or position changes.
        """
        if not self._is_authenticated:
            raise OkxWebSocketError(
                "Must be authenticated to subscribe to balance_and_position"
            )

        await self.subscribe("balance_and_position")
        logger.info("Subscribed to balance_and_position channel")

    async def subscribe_order_algo(
        self,
        inst_type: InstType | None = None,
        inst_family: str | None = None,
        inst_id: str | None = None,
    ) -> None:
        """Subscribe to algo order updates.

        Channel: orders-algo
        Requires authentication.

        Args:
            inst_type: Instrument type filter.
            inst_family: Instrument family filter.
            inst_id: Specific instrument ID filter.
        """
        if not self._is_authenticated:
            raise OkxWebSocketError("Must be authenticated to subscribe to orders-algo")

        arg: dict[str, str] = {"channel": "orders-algo"}
        arg["instType"] = inst_type.value if inst_type else "ANY"
        if inst_family:
            arg["instFamily"] = inst_family
        if inst_id:
            arg["instId"] = inst_id

        message = {"op": "subscribe", "args": [arg]}
        await self._send_json(message)
        logger.info("Subscribed to orders-algo channel")

    async def disconnect(self) -> None:
        """Disconnect from OKX Private WebSocket."""
        self._is_authenticated = False
        await super().disconnect()

    async def __aenter__(self) -> OkxPrivateWsClient:
        """Enter async context manager - connects and authenticates."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager - disconnects."""
        await self.disconnect()
