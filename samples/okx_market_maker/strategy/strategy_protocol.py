"""Strategy protocol for dependency injection.

Defines the interface that all market making strategies must implement.
Uses Protocol for structural subtyping (duck typing with type hints).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from samples.okx_market_maker.context.market_context import MarketContext
    from samples.okx_market_maker.models.amend_request import AmendRequest
    from samples.okx_market_maker.models.strategy_order import StrategyOrder


@dataclass
class Quote:
    """A single quote (bid or ask) to place.

    Attributes:
        price: Quote price
        size: Quote size
        side: "buy" or "sell"
    """

    price: Decimal
    size: Decimal
    side: str  # "buy" or "sell"


@dataclass
class StrategyDecision:
    """Decision output from strategy.

    Contains the orders to place, amend, and cancel.

    Attributes:
        orders_to_place: New orders to place
        orders_to_amend: Existing orders to amend (typed AmendRequest objects)
        orders_to_cancel: Orders to cancel by cl_ord_id
        should_halt: Whether trading should be halted
        halt_reason: Reason for halting if should_halt is True
    """

    orders_to_place: list[Quote] = field(default_factory=list)
    orders_to_amend: list[AmendRequest] = field(default_factory=list)
    orders_to_cancel: list[str] = field(default_factory=list)
    should_halt: bool = False
    halt_reason: str | None = None

    @property
    def has_actions(self) -> bool:
        """Check if decision has any actions to take."""
        return bool(
            self.orders_to_place
            or self.orders_to_amend
            or self.orders_to_cancel
        )

    @property
    def num_buys_to_place(self) -> int:
        """Count buy orders to place."""
        return sum(1 for q in self.orders_to_place if q.side == "buy")

    @property
    def num_sells_to_place(self) -> int:
        """Count sell orders to place."""
        return sum(1 for q in self.orders_to_place if q.side == "sell")


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
