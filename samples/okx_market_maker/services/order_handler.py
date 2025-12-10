"""Order handler service for market maker.

Manages order lifecycle including placement, cancellation, and state updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from client_gw_core import get_logger

from samples.okx_market_maker.models.strategy_order import OrderState, StrategyOrder
from samples.okx_market_maker.strategy.strategy_protocol import Quote, StrategyDecision
from samples.okx_market_maker.utils.id_generator import OrderIdGenerator

if TYPE_CHECKING:
    from okx_client_gw.application.services.trade_service import TradeService
    from okx_client_gw.domain.models.order import Order, OrderRequest
    from samples.okx_market_maker.config.settings import MarketMakerSettings
    from samples.okx_market_maker.context.market_context import MarketContext


logger = get_logger(__name__)


class OrderHandler:
    """Handles order placement, cancellation, and state management.

    Responsibilities:
    - Convert strategy decisions to API calls
    - Batch order operations (max 20 per request)
    - Track order state in context
    - Handle order updates from WebSocket

    Example:
        handler = OrderHandler(trade_service, settings, context)

        # Execute strategy decision
        await handler.execute_decision(decision)

        # Handle order update from WebSocket
        handler.on_order_update(order_data)

        # Cancel all orders
        await handler.cancel_all()
    """

    MAX_BATCH_SIZE = 20

    def __init__(
        self,
        trade_service: TradeService,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Initialize order handler.

        Args:
            trade_service: OKX trade service for API calls
            settings: Market maker configuration
            context: Market context for state tracking
        """
        self._trade_service = trade_service
        self._settings = settings
        self._context = context
        self._id_generator = OrderIdGenerator(prefix="mm")

    async def execute_decision(self, decision: StrategyDecision) -> None:
        """Execute a strategy decision.

        Places new orders, cancels unwanted orders.

        Args:
            decision: Strategy decision to execute
        """
        # First cancel orders
        if decision.orders_to_cancel:
            await self._cancel_orders(decision.orders_to_cancel)

        # Then place new orders
        if decision.orders_to_place:
            await self._place_orders(decision.orders_to_place)

    async def _place_orders(self, quotes: list[Quote]) -> None:
        """Place orders from quotes.

        Batches orders up to MAX_BATCH_SIZE per request.

        Args:
            quotes: Quotes to place as orders
        """
        from okx_client_gw.domain.enums import OrderType, TradeMode, TradeSide
        from okx_client_gw.domain.models.order import OrderRequest

        if not quotes:
            return

        # Convert quotes to order requests
        order_requests: list[OrderRequest] = []
        strategy_orders: list[StrategyOrder] = []

        trade_mode = TradeMode(self._settings.trading_mode)

        for quote in quotes:
            cl_ord_id = self._id_generator.next()

            # Create strategy order for tracking
            strategy_order = StrategyOrder(
                cl_ord_id=cl_ord_id,
                inst_id=self._settings.inst_id,
                side=quote.side,
                price=quote.price,
                size=quote.size,
            )
            strategy_orders.append(strategy_order)

            # Create API order request
            order_request = OrderRequest(
                inst_id=self._settings.inst_id,
                td_mode=trade_mode,
                side=TradeSide(quote.side.upper()),
                ord_type=OrderType.LIMIT,
                sz=quote.size,
                px=quote.price,
                cl_ord_id=cl_ord_id,
            )
            order_requests.append(order_request)

        # Add to context before sending
        for strategy_order in strategy_orders:
            self._context.add_order(strategy_order)

        # Place in batches
        for i in range(0, len(order_requests), self.MAX_BATCH_SIZE):
            batch = order_requests[i : i + self.MAX_BATCH_SIZE]
            batch_strategy = strategy_orders[i : i + self.MAX_BATCH_SIZE]

            try:
                # Mark as sent
                for so in batch_strategy:
                    so.mark_sent()

                # Place batch
                results = await self._trade_service.place_batch_orders(batch)

                # Process results
                for j, result in enumerate(results):
                    so = batch_strategy[j]
                    if result.get("sCode") == "0":
                        ord_id = result.get("ordId", "")
                        so.mark_ack(ord_id)
                        logger.info(
                            f"Order placed: {so.cl_ord_id} -> {ord_id} "
                            f"{so.side} {so.size}@{so.price}"
                        )
                    else:
                        error_msg = result.get("sMsg", "Unknown error")
                        so.mark_rejected(error_msg)
                        logger.warning(
                            f"Order rejected: {so.cl_ord_id} - {error_msg}"
                        )

            except Exception as e:
                logger.error(f"Failed to place batch: {e}")
                for so in batch_strategy:
                    if so.state == OrderState.SENT:
                        so.mark_rejected(str(e))

    async def _cancel_orders(self, cl_ord_ids: list[str]) -> None:
        """Cancel orders by client order ID.

        Args:
            cl_ord_ids: Client order IDs to cancel
        """
        if not cl_ord_ids:
            return

        # Build cancel requests
        cancel_requests = []
        for cl_ord_id in cl_ord_ids:
            order = self._context.get_order(cl_ord_id)
            if order and order.is_active:
                cancel_requests.append({
                    "instId": self._settings.inst_id,
                    "clOrdId": cl_ord_id,
                })

        if not cancel_requests:
            return

        # Cancel in batches
        for i in range(0, len(cancel_requests), self.MAX_BATCH_SIZE):
            batch = cancel_requests[i : i + self.MAX_BATCH_SIZE]

            try:
                results = await self._trade_service.cancel_batch_orders(batch)

                for j, result in enumerate(results):
                    cl_ord_id = batch[j]["clOrdId"]
                    order = self._context.get_order(cl_ord_id)

                    if result.get("sCode") == "0":
                        if order:
                            order.mark_canceled()
                        logger.info(f"Order canceled: {cl_ord_id}")
                    else:
                        error_msg = result.get("sMsg", "Unknown error")
                        logger.warning(
                            f"Cancel failed for {cl_ord_id}: {error_msg}"
                        )

            except Exception as e:
                logger.error(f"Failed to cancel batch: {e}")

    async def cancel_all(self) -> int:
        """Cancel all active orders.

        Returns:
            Number of orders canceled
        """
        active_orders = [
            order.cl_ord_id
            for order in self._context.live_orders.values()
            if order.is_active
        ]

        if not active_orders:
            return 0

        await self._cancel_orders(active_orders)
        return len(active_orders)

    def on_order_update(self, order_data: Order) -> None:
        """Handle order update from WebSocket.

        Updates strategy order state based on exchange order data.

        Args:
            order_data: Order data from exchange
        """
        cl_ord_id = order_data.cl_ord_id
        if not cl_ord_id:
            return

        strategy_order = self._context.get_order(cl_ord_id)
        if not strategy_order:
            logger.debug(f"Unknown order update: {cl_ord_id}")
            return

        # Update from exchange
        strategy_order.update_from_exchange(
            state=order_data.state.value,
            filled_size=order_data.acc_fill_sz,
            avg_price=order_data.avg_px,
            ord_id=order_data.ord_id,
        )

        # Handle fill
        if order_data.fill_sz > 0:
            self._context.record_fill(
                side=strategy_order.side,
                size=order_data.fill_sz,
            )
            logger.info(
                f"Fill: {cl_ord_id} {strategy_order.side} "
                f"{order_data.fill_sz}@{order_data.fill_px}"
            )

        # Log state changes
        if strategy_order.is_filled:
            logger.info(f"Order filled: {cl_ord_id}")
        elif strategy_order.is_canceled:
            logger.info(f"Order canceled: {cl_ord_id}")

    def cleanup_terminal_orders(self) -> int:
        """Remove terminal orders from tracking.

        Returns:
            Number of orders removed
        """
        return self._context.clear_terminal_orders()
