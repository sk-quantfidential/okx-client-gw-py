"""Quote and strategy decision models.

Value objects for strategy output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from samples.okx_market_maker.domain.models.amend_request import AmendRequest


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
