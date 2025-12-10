"""Trade commands for OKX API.

Commands for order placement, cancellation, and order queries.
These endpoints require authentication.

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from okx_client_gw.application.commands.base import OkxMutationCommand, OkxQueryCommand
from okx_client_gw.domain.enums import InstType
from okx_client_gw.domain.models.order import Order, OrderRequest

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class PlaceOrderCommand(OkxMutationCommand[dict]):
    """Place a new order.

    API: POST /api/v5/trade/order (AUTH REQUIRED)

    Places a single order. For batch orders, use PlaceBatchOrdersCommand.

    Example:
        request = OrderRequest(
            inst_id="BTC-USDT",
            td_mode=TradeMode.CASH,
            side=TradeSide.BUY,
            ord_type=OrderType.LIMIT,
            sz=Decimal("0.001"),
            px=Decimal("50000"),
        )
        cmd = PlaceOrderCommand(request)
        result = await cmd.invoke(client)
        print(f"Order ID: {result['ordId']}")
    """

    def __init__(self, request: OrderRequest) -> None:
        """Initialize command.

        Args:
            request: Order request with all parameters
        """
        self._request = request

    async def invoke(self, client: OkxHttpClientProtocol) -> dict:
        """Place order.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Dict with "ordId", "clOrdId", "sCode", "sMsg"
        """
        data = await client.post_data_auth(
            "/api/v5/trade/order",
            json_data=self._request.to_okx_dict(),
        )
        return data[0] if data else {}


class CancelOrderCommand(OkxMutationCommand[dict]):
    """Cancel an existing order.

    API: POST /api/v5/trade/cancel-order (AUTH REQUIRED)

    Cancels a single order by order ID or client order ID.

    Example:
        cmd = CancelOrderCommand(inst_id="BTC-USDT", ord_id="123456789")
        result = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_id: str,
        *,
        ord_id: str | None = None,
        cl_ord_id: str | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            ord_id: Order ID (either ord_id or cl_ord_id required)
            cl_ord_id: Client order ID

        Raises:
            ValueError: If neither ord_id nor cl_ord_id provided
        """
        if not ord_id and not cl_ord_id:
            raise ValueError("Either ord_id or cl_ord_id is required")
        self._inst_id = inst_id
        self._ord_id = ord_id
        self._cl_ord_id = cl_ord_id

    async def invoke(self, client: OkxHttpClientProtocol) -> dict:
        """Cancel order.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Dict with "ordId", "clOrdId", "sCode", "sMsg"
        """
        body: dict[str, str] = {"instId": self._inst_id}
        if self._ord_id:
            body["ordId"] = self._ord_id
        if self._cl_ord_id:
            body["clOrdId"] = self._cl_ord_id

        data = await client.post_data_auth(
            "/api/v5/trade/cancel-order",
            json_data=body,
        )
        return data[0] if data else {}


class GetOrderCommand(OkxQueryCommand[Order]):
    """Get details of a single order.

    API: GET /api/v5/trade/order (AUTH REQUIRED)

    Example:
        cmd = GetOrderCommand(inst_id="BTC-USDT", ord_id="123456789")
        order = await cmd.invoke(client)
        print(f"Order state: {order.state}")
    """

    def __init__(
        self,
        inst_id: str,
        *,
        ord_id: str | None = None,
        cl_ord_id: str | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            ord_id: Order ID (either ord_id or cl_ord_id required)
            cl_ord_id: Client order ID

        Raises:
            ValueError: If neither ord_id nor cl_ord_id provided
        """
        if not ord_id and not cl_ord_id:
            raise ValueError("Either ord_id or cl_ord_id is required")
        self._inst_id = inst_id
        self._ord_id = ord_id
        self._cl_ord_id = cl_ord_id

    async def invoke(self, client: OkxHttpClientProtocol) -> Order:
        """Get order details.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Order object
        """
        params: dict[str, str] = {"instId": self._inst_id}
        if self._ord_id:
            params["ordId"] = self._ord_id
        if self._cl_ord_id:
            params["clOrdId"] = self._cl_ord_id

        data = await client.get_data_auth("/api/v5/trade/order", params=params)
        return Order.from_okx_dict(data[0])


class GetPendingOrdersCommand(OkxQueryCommand[list[Order]]):
    """Get pending (live) orders.

    API: GET /api/v5/trade/orders-pending (AUTH REQUIRED)

    Returns orders in live or partially filled state.

    Example:
        cmd = GetPendingOrdersCommand(inst_type=InstType.SPOT)
        orders = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
        *,
        ord_type: str | None = None,
        limit: int = 100,
    ) -> None:
        """Initialize command.

        Args:
            inst_type: Filter by instrument type
            inst_id: Filter by instrument ID
            ord_type: Filter by order type
            limit: Maximum orders to return (max 100)
        """
        self._inst_type = inst_type
        self._inst_id = inst_id
        self._ord_type = ord_type
        self._limit = min(limit, 100)

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Order]:
        """Get pending orders.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            List of Order objects
        """
        params: dict[str, str] = {"limit": str(self._limit)}
        if self._inst_type:
            params["instType"] = self._inst_type.value
        if self._inst_id:
            params["instId"] = self._inst_id
        if self._ord_type:
            params["ordType"] = self._ord_type

        data = await client.get_data_auth("/api/v5/trade/orders-pending", params=params)
        return [Order.from_okx_dict(item) for item in data]


class GetOrderHistoryCommand(OkxQueryCommand[list[Order]]):
    """Get order history.

    API: GET /api/v5/trade/orders-history (AUTH REQUIRED)

    Returns completed orders (filled, canceled) from the last 7 days.
    For older history, use GetOrderHistoryArchiveCommand.

    Example:
        cmd = GetOrderHistoryCommand(inst_type=InstType.SPOT, limit=50)
        orders = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_type: InstType,
        inst_id: str | None = None,
        *,
        ord_type: str | None = None,
        state: str | None = None,
        limit: int = 100,
    ) -> None:
        """Initialize command.

        Args:
            inst_type: Instrument type (required)
            inst_id: Filter by instrument ID
            ord_type: Filter by order type
            state: Filter by state (filled, canceled)
            limit: Maximum orders to return (max 100)
        """
        self._inst_type = inst_type
        self._inst_id = inst_id
        self._ord_type = ord_type
        self._state = state
        self._limit = min(limit, 100)

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Order]:
        """Get order history.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            List of Order objects
        """
        params: dict[str, str] = {
            "instType": self._inst_type.value,
            "limit": str(self._limit),
        }
        if self._inst_id:
            params["instId"] = self._inst_id
        if self._ord_type:
            params["ordType"] = self._ord_type
        if self._state:
            params["state"] = self._state

        data = await client.get_data_auth(
            "/api/v5/trade/orders-history",
            params=params,
        )
        return [Order.from_okx_dict(item) for item in data]


class AmendOrderCommand(OkxMutationCommand[dict]):
    """Amend an existing order.

    API: POST /api/v5/trade/amend-order (AUTH REQUIRED)

    Modifies price and/or size of an existing order.
    Note: Not all order types support amendment.

    Example:
        cmd = AmendOrderCommand(
            inst_id="BTC-USDT",
            ord_id="123456789",
            new_px="51000",
        )
        result = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_id: str,
        *,
        ord_id: str | None = None,
        cl_ord_id: str | None = None,
        req_id: str | None = None,
        new_sz: str | None = None,
        new_px: str | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            ord_id: Order ID (either ord_id or cl_ord_id required)
            cl_ord_id: Client order ID
            req_id: Request ID for idempotency
            new_sz: New order size
            new_px: New order price

        Raises:
            ValueError: If neither ord_id nor cl_ord_id provided
            ValueError: If neither new_sz nor new_px provided
        """
        if not ord_id and not cl_ord_id:
            raise ValueError("Either ord_id or cl_ord_id is required")
        if not new_sz and not new_px:
            raise ValueError("Either new_sz or new_px is required")

        self._inst_id = inst_id
        self._ord_id = ord_id
        self._cl_ord_id = cl_ord_id
        self._req_id = req_id
        self._new_sz = new_sz
        self._new_px = new_px

    async def invoke(self, client: OkxHttpClientProtocol) -> dict:
        """Amend order.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Dict with "ordId", "clOrdId", "reqId", "sCode", "sMsg"
        """
        body: dict[str, str] = {"instId": self._inst_id}
        if self._ord_id:
            body["ordId"] = self._ord_id
        if self._cl_ord_id:
            body["clOrdId"] = self._cl_ord_id
        if self._req_id:
            body["reqId"] = self._req_id
        if self._new_sz:
            body["newSz"] = self._new_sz
        if self._new_px:
            body["newPx"] = self._new_px

        data = await client.post_data_auth(
            "/api/v5/trade/amend-order",
            json_data=body,
        )
        return data[0] if data else {}


class PlaceBatchOrdersCommand(OkxMutationCommand[list[dict]]):
    """Place multiple orders at once.

    API: POST /api/v5/trade/batch-orders (AUTH REQUIRED)

    Places up to 20 orders in a single request.

    Example:
        orders = [
            OrderRequest(inst_id="BTC-USDT", td_mode=TradeMode.CASH, ...),
            OrderRequest(inst_id="ETH-USDT", td_mode=TradeMode.CASH, ...),
        ]
        cmd = PlaceBatchOrdersCommand(orders)
        results = await cmd.invoke(client)
    """

    MAX_BATCH_SIZE = 20

    def __init__(self, orders: list[OrderRequest]) -> None:
        """Initialize command.

        Args:
            orders: List of OrderRequest objects

        Raises:
            ValueError: If batch size exceeds limit
        """
        if len(orders) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} orders per batch")
        self._orders = orders

    async def invoke(self, client: OkxHttpClientProtocol) -> list[dict]:
        """Place batch orders.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            List of dicts with ordId, clOrdId, sCode, sMsg for each order
        """
        order_data = [order.to_okx_dict() for order in self._orders]
        return await client.post_data_auth(
            "/api/v5/trade/batch-orders",
            json_data=order_data,
        )


class AmendBatchOrdersCommand(OkxMutationCommand[list[dict]]):
    """Amend multiple orders at once.

    API: POST /api/v5/trade/amend-batch-orders (AUTH REQUIRED)

    Amends up to 20 orders in a single request.

    Example:
        amendments = [
            {"instId": "BTC-USDT", "ordId": "123", "newPx": "51000"},
            {"instId": "ETH-USDT", "clOrdId": "client_456", "newSz": "2"},
        ]
        cmd = AmendBatchOrdersCommand(amendments)
        results = await cmd.invoke(client)
    """

    MAX_BATCH_SIZE = 20

    def __init__(self, amendments: list[dict]) -> None:
        """Initialize command.

        Args:
            amendments: List of dicts with instId, ordId/clOrdId, and newPx/newSz

        Raises:
            ValueError: If batch size exceeds limit
        """
        if len(amendments) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} amendments per batch")
        self._amendments = amendments

    async def invoke(self, client: OkxHttpClientProtocol) -> list[dict]:
        """Amend batch orders.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            List of dicts with ordId, clOrdId, reqId, sCode, sMsg for each order
        """
        return await client.post_data_auth(
            "/api/v5/trade/amend-batch-orders",
            json_data=self._amendments,
        )


class CancelBatchOrdersCommand(OkxMutationCommand[list[dict]]):
    """Cancel multiple orders at once.

    API: POST /api/v5/trade/cancel-batch-orders (AUTH REQUIRED)

    Cancels up to 20 orders in a single request.

    Example:
        orders = [
            {"instId": "BTC-USDT", "ordId": "123"},
            {"instId": "ETH-USDT", "ordId": "456"},
        ]
        cmd = CancelBatchOrdersCommand(orders)
        results = await cmd.invoke(client)
    """

    MAX_BATCH_SIZE = 20

    def __init__(self, orders: list[dict]) -> None:
        """Initialize command.

        Args:
            orders: List of dicts with "instId" and "ordId" or "clOrdId"

        Raises:
            ValueError: If batch size exceeds limit
        """
        if len(orders) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {self.MAX_BATCH_SIZE} orders per batch")
        self._orders = orders

    async def invoke(self, client: OkxHttpClientProtocol) -> list[dict]:
        """Cancel batch orders.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            List of dicts with results for each order
        """
        return await client.post_data_auth(
            "/api/v5/trade/cancel-batch-orders",
            json_data=self._orders,
        )
