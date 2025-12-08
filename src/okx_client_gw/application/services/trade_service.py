"""Trade service for OKX API.

High-level service for order management including placement,
cancellation, and order queries. All operations require authentication.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from okx_client_gw.application.commands.trade_commands import (
    AmendOrderCommand,
    CancelBatchOrdersCommand,
    CancelOrderCommand,
    GetOrderCommand,
    GetOrderHistoryCommand,
    GetPendingOrdersCommand,
    PlaceOrderCommand,
)
from okx_client_gw.domain.enums import (
    InstType,
    OrderType,
    PositionSide,
    TradeMode,
    TradeSide,
)
from okx_client_gw.domain.models.order import Order, OrderRequest

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class TradeService:
    """Service for OKX order management operations.

    Provides high-level methods for placing and managing orders.
    All methods require authentication (credentials must be set on client).

    Example:
        credentials = OkxCredentials.from_env()
        async with OkxHttpClient(credentials=credentials) as client:
            service = TradeService(client)

            # Place a limit order
            result = await service.place_limit_order(
                inst_id="BTC-USDT",
                side=TradeSide.BUY,
                sz=Decimal("0.001"),
                px=Decimal("50000"),
            )
            print(f"Order ID: {result['ordId']}")

            # Cancel the order
            await service.cancel_order("BTC-USDT", ord_id=result["ordId"])
    """

    def __init__(self, client: OkxHttpClientProtocol) -> None:
        """Initialize trade service.

        Args:
            client: OKX HTTP client with credentials (injected dependency)
        """
        self._client = client

    async def place_order(self, request: OrderRequest) -> dict:
        """Place an order using an OrderRequest object.

        Args:
            request: Order request with all parameters

        Returns:
            Dict with ordId, clOrdId, sCode, sMsg
        """
        cmd = PlaceOrderCommand(request)
        return await cmd.invoke(self._client)

    async def place_limit_order(
        self,
        inst_id: str,
        side: TradeSide,
        sz: Decimal,
        px: Decimal,
        *,
        td_mode: TradeMode = TradeMode.CASH,
        pos_side: PositionSide | None = None,
        cl_ord_id: str | None = None,
        reduce_only: bool = False,
        ccy: str | None = None,
    ) -> dict:
        """Place a limit order (convenience method).

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT")
            side: Buy or sell
            sz: Order size
            px: Limit price
            td_mode: Trade mode (cash for spot, cross/isolated for margin)
            pos_side: Position side for hedge mode
            cl_ord_id: Client order ID
            reduce_only: Only reduce position
            ccy: Margin currency

        Returns:
            Dict with ordId, clOrdId, sCode, sMsg
        """
        request = OrderRequest(
            inst_id=inst_id,
            td_mode=td_mode,
            side=side,
            ord_type=OrderType.LIMIT,
            sz=sz,
            px=px,
            pos_side=pos_side,
            cl_ord_id=cl_ord_id,
            reduce_only=reduce_only,
            ccy=ccy,
        )
        return await self.place_order(request)

    async def place_market_order(
        self,
        inst_id: str,
        side: TradeSide,
        sz: Decimal,
        *,
        td_mode: TradeMode = TradeMode.CASH,
        pos_side: PositionSide | None = None,
        cl_ord_id: str | None = None,
        reduce_only: bool = False,
        ccy: str | None = None,
        tgt_ccy: str | None = None,
    ) -> dict:
        """Place a market order (convenience method).

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT")
            side: Buy or sell
            sz: Order size
            td_mode: Trade mode
            pos_side: Position side for hedge mode
            cl_ord_id: Client order ID
            reduce_only: Only reduce position
            ccy: Margin currency
            tgt_ccy: Target currency for SPOT market orders

        Returns:
            Dict with ordId, clOrdId, sCode, sMsg
        """
        request = OrderRequest(
            inst_id=inst_id,
            td_mode=td_mode,
            side=side,
            ord_type=OrderType.MARKET,
            sz=sz,
            pos_side=pos_side,
            cl_ord_id=cl_ord_id,
            reduce_only=reduce_only,
            ccy=ccy,
            tgt_ccy=tgt_ccy,
        )
        return await self.place_order(request)

    async def cancel_order(
        self,
        inst_id: str,
        *,
        ord_id: str | None = None,
        cl_ord_id: str | None = None,
    ) -> dict:
        """Cancel an order.

        Args:
            inst_id: Instrument ID
            ord_id: Order ID (either ord_id or cl_ord_id required)
            cl_ord_id: Client order ID

        Returns:
            Dict with ordId, clOrdId, sCode, sMsg
        """
        cmd = CancelOrderCommand(inst_id, ord_id=ord_id, cl_ord_id=cl_ord_id)
        return await cmd.invoke(self._client)

    async def cancel_batch_orders(self, orders: list[dict]) -> list[dict]:
        """Cancel multiple orders at once.

        Args:
            orders: List of dicts with instId and ordId/clOrdId

        Returns:
            List of result dicts for each order
        """
        cmd = CancelBatchOrdersCommand(orders)
        return await cmd.invoke(self._client)

    async def amend_order(
        self,
        inst_id: str,
        *,
        ord_id: str | None = None,
        cl_ord_id: str | None = None,
        new_sz: str | None = None,
        new_px: str | None = None,
    ) -> dict:
        """Amend an existing order.

        Args:
            inst_id: Instrument ID
            ord_id: Order ID (either ord_id or cl_ord_id required)
            cl_ord_id: Client order ID
            new_sz: New order size
            new_px: New order price

        Returns:
            Dict with ordId, clOrdId, sCode, sMsg
        """
        cmd = AmendOrderCommand(
            inst_id,
            ord_id=ord_id,
            cl_ord_id=cl_ord_id,
            new_sz=new_sz,
            new_px=new_px,
        )
        return await cmd.invoke(self._client)

    async def get_order(
        self,
        inst_id: str,
        *,
        ord_id: str | None = None,
        cl_ord_id: str | None = None,
    ) -> Order:
        """Get order details.

        Args:
            inst_id: Instrument ID
            ord_id: Order ID (either ord_id or cl_ord_id required)
            cl_ord_id: Client order ID

        Returns:
            Order object
        """
        cmd = GetOrderCommand(inst_id, ord_id=ord_id, cl_ord_id=cl_ord_id)
        return await cmd.invoke(self._client)

    async def get_pending_orders(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
        *,
        limit: int = 100,
    ) -> list[Order]:
        """Get pending (live) orders.

        Args:
            inst_type: Filter by instrument type
            inst_id: Filter by instrument ID
            limit: Maximum orders to return (max 100)

        Returns:
            List of Order objects
        """
        cmd = GetPendingOrdersCommand(inst_type, inst_id, limit=limit)
        return await cmd.invoke(self._client)

    async def get_order_history(
        self,
        inst_type: InstType,
        inst_id: str | None = None,
        *,
        state: str | None = None,
        limit: int = 100,
    ) -> list[Order]:
        """Get order history (last 7 days).

        Args:
            inst_type: Instrument type (required)
            inst_id: Filter by instrument ID
            state: Filter by state (filled, canceled)
            limit: Maximum orders to return (max 100)

        Returns:
            List of Order objects
        """
        cmd = GetOrderHistoryCommand(
            inst_type,
            inst_id,
            state=state,
            limit=limit,
        )
        return await cmd.invoke(self._client)

    async def cancel_all_orders(self, inst_id: str) -> list[dict]:
        """Cancel all pending orders for an instrument.

        Args:
            inst_id: Instrument ID

        Returns:
            List of cancellation results
        """
        pending = await self.get_pending_orders(inst_id=inst_id)
        if not pending:
            return []

        orders = [{"instId": inst_id, "ordId": order.ord_id} for order in pending]
        return await self.cancel_batch_orders(orders)
