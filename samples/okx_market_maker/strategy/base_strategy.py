"""Base strategy with common functionality.

Abstract base class that provides:
- Order matching logic (decide which orders to keep/cancel)
- Risk limit checking
- Fill tracking
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from samples.okx_market_maker.strategy.strategy_protocol import Quote, StrategyDecision

if TYPE_CHECKING:
    from samples.okx_market_maker.config.settings import MarketMakerSettings
    from samples.okx_market_maker.context.market_context import MarketContext
    from samples.okx_market_maker.models.strategy_order import StrategyOrder


class BaseStrategy(ABC):
    """Abstract base class for market making strategies.

    Provides common functionality:
    - Order matching to decide which existing orders to keep
    - Risk limit checking (max position, staleness)
    - Fill and cancel event handling

    Subclasses must implement compute_quotes() to define quote generation logic.

    Example:
        class MyStrategy(BaseStrategy):
            def compute_quotes(self, context: MarketContext) -> list[Quote]:
                # Generate quotes based on market state
                mid = context.mid_price
                return [
                    Quote(mid * Decimal("0.999"), Decimal("0.001"), "buy"),
                    Quote(mid * Decimal("1.001"), Decimal("0.001"), "sell"),
                ]
    """

    def __init__(self, settings: MarketMakerSettings) -> None:
        """Initialize base strategy.

        Args:
            settings: Market maker configuration
        """
        self.settings = settings
        self._total_pnl = Decimal("0")

    @abstractmethod
    def compute_quotes(self, context: MarketContext) -> list[Quote]:
        """Compute desired quotes based on market state.

        Must be implemented by subclasses.

        Args:
            context: Current market context

        Returns:
            List of Quote objects representing desired orders
        """
        ...

    def decide(self, context: MarketContext) -> StrategyDecision:
        """Compute strategy decision based on current market state.

        1. Check if trading should be halted
        2. Compute desired quotes
        3. Match against existing orders
        4. Return orders to place/cancel

        Args:
            context: Current market context

        Returns:
            StrategyDecision with actions to take
        """
        # Check halt conditions
        should_halt, halt_reason = self.should_halt(context)
        if should_halt:
            # Cancel all orders when halting
            orders_to_cancel = [
                order.cl_ord_id
                for order in context.live_orders.values()
                if order.is_active
            ]
            return StrategyDecision(
                orders_to_cancel=orders_to_cancel,
                should_halt=True,
                halt_reason=halt_reason,
            )

        # Compute desired quotes
        desired_quotes = self.compute_quotes(context)

        # Match against existing orders
        return self._match_orders(context, desired_quotes)

    def _match_orders(
        self,
        context: MarketContext,
        desired_quotes: list[Quote],
    ) -> StrategyDecision:
        """Match desired quotes against existing orders.

        Determines which orders to:
        - Keep (existing order matches desired quote)
        - Cancel (existing order doesn't match any quote)
        - Place (new quote doesn't match any order)

        Uses price tolerance for matching (within tick size).

        Args:
            context: Current market context
            desired_quotes: Quotes we want to have on the book

        Returns:
            StrategyDecision with orders to place/cancel
        """
        tick_size = context.tick_size
        orders_to_place: list[Quote] = []
        orders_to_cancel: list[str] = []

        # Get active orders by side
        active_buys = list(context.active_buy_orders)
        active_sells = list(context.active_sell_orders)

        # Split desired quotes by side
        desired_buys = [q for q in desired_quotes if q.side == "buy"]
        desired_sells = [q for q in desired_quotes if q.side == "sell"]

        # Match buys
        matched_buy_orders: set[str] = set()
        for quote in desired_buys:
            matched = False
            for order in active_buys:
                if order.cl_ord_id in matched_buy_orders:
                    continue
                # Match if price is within tick
                if abs(order.price - quote.price) <= tick_size:
                    matched_buy_orders.add(order.cl_ord_id)
                    matched = True
                    break
            if not matched:
                orders_to_place.append(quote)

        # Cancel unmatched buy orders
        for order in active_buys:
            if order.cl_ord_id not in matched_buy_orders:
                orders_to_cancel.append(order.cl_ord_id)

        # Match sells
        matched_sell_orders: set[str] = set()
        for quote in desired_sells:
            matched = False
            for order in active_sells:
                if order.cl_ord_id in matched_sell_orders:
                    continue
                if abs(order.price - quote.price) <= tick_size:
                    matched_sell_orders.add(order.cl_ord_id)
                    matched = True
                    break
            if not matched:
                orders_to_place.append(quote)

        # Cancel unmatched sell orders
        for order in active_sells:
            if order.cl_ord_id not in matched_sell_orders:
                orders_to_cancel.append(order.cl_ord_id)

        return StrategyDecision(
            orders_to_place=orders_to_place,
            orders_to_cancel=orders_to_cancel,
        )

    def should_halt(self, context: MarketContext) -> tuple[bool, str | None]:
        """Check if trading should be halted.

        Checks:
        - Data freshness (orderbook, account, position)
        - Position limits (max net buy/sell)

        Args:
            context: Current market context

        Returns:
            Tuple of (should_halt, reason)
        """
        # Check data freshness
        if not context.is_orderbook_fresh(self.settings.orderbook_max_delay_sec):
            return True, "Orderbook data is stale"

        if not context.is_account_fresh(self.settings.account_max_delay_sec):
            return True, "Account data is stale"

        if not context.is_position_fresh(self.settings.position_max_delay_sec):
            return True, "Position data is stale"

        # Check position limits
        net_pos = context.net_position
        if net_pos > self.settings.max_net_buy:
            return True, f"Max net buy exceeded: {net_pos} > {self.settings.max_net_buy}"

        if net_pos < -self.settings.max_net_sell:
            return True, f"Max net sell exceeded: {abs(net_pos)} > {self.settings.max_net_sell}"

        # Check mid price exists
        if context.mid_price is None:
            return True, "No mid price available"

        return False, None

    def on_fill(
        self,
        order: StrategyOrder,
        fill_size: Decimal,
        fill_price: Decimal,
    ) -> None:
        """Handle order fill event.

        Updates P&L tracking.

        Args:
            order: The order that was filled
            fill_size: Size of this fill
            fill_price: Price of this fill
        """
        # P&L tracking is done in MarketContext
        pass

    def on_cancel(self, order: StrategyOrder) -> None:
        """Handle order cancellation event.

        Default implementation does nothing.

        Args:
            order: The order that was canceled
        """
        pass

    @property
    def total_pnl(self) -> Decimal:
        """Get total realized P&L."""
        return self._total_pnl

    def round_price(self, price: Decimal, tick_size: Decimal) -> Decimal:
        """Round price to nearest tick.

        Args:
            price: Price to round
            tick_size: Tick size

        Returns:
            Price rounded to nearest tick
        """
        return (price / tick_size).quantize(Decimal("1")) * tick_size

    def round_size(self, size: Decimal, lot_size: Decimal) -> Decimal:
        """Round size to nearest lot.

        Args:
            size: Size to round
            lot_size: Lot size

        Returns:
            Size rounded to nearest lot
        """
        return (size / lot_size).quantize(Decimal("1")) * lot_size
