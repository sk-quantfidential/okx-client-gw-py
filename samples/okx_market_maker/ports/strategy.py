"""Strategy protocol for dependency injection.

Defines the interface that all market making strategies must implement.
Uses Protocol for structural subtyping (duck typing with type hints).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from samples.okx_market_maker.application.context.market_context import MarketContext
    from samples.okx_market_maker.domain.models.quote import StrategyDecision
    from samples.okx_market_maker.domain.models.strategy_order import StrategyOrder


@runtime_checkable
class StrategyProtocol(Protocol):
    """Protocol defining the interface for market making strategies.

    Any class implementing these methods can be used as a strategy.
    Enables dependency injection and easy strategy swapping.

    Example:
        class MyStrategy:
            def decide(self, context: MarketContext) -> StrategyDecision:
                # Compute quotes based on market state
                ...

            def on_fill(self, order: StrategyOrder, fill_size: Decimal, fill_price: Decimal) -> None:
                # Handle fill events
                ...

        # Use with type hints
        strategy: StrategyProtocol = MyStrategy()
    """

    def decide(self, context: MarketContext) -> StrategyDecision:
        """Compute strategy decision based on current market state.

        Called on each iteration of the main loop.
        Should return orders to place, amend, and cancel.

        Args:
            context: Current market context with orderbook, positions, etc.

        Returns:
            StrategyDecision with orders to place/amend/cancel
        """
        ...

    def on_fill(
        self,
        order: StrategyOrder,
        fill_size: Decimal,
        fill_price: Decimal,
    ) -> None:
        """Handle order fill event.

        Called when an order is filled (partially or completely).
        Use to update internal state, track P&L, etc.

        Args:
            order: The order that was filled
            fill_size: Size of this fill
            fill_price: Price of this fill
        """
        ...

    def on_cancel(self, order: StrategyOrder) -> None:
        """Handle order cancellation event.

        Called when an order is canceled.

        Args:
            order: The order that was canceled
        """
        ...

    def should_halt(self, context: MarketContext) -> tuple[bool, str | None]:
        """Check if trading should be halted.

        Called before each decision to check for risk conditions.

        Args:
            context: Current market context

        Returns:
            Tuple of (should_halt, reason)
        """
        ...
