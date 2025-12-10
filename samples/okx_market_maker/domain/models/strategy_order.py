"""Strategy order model with state machine.

Tracks order lifecycle from creation through fill/cancel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from samples.okx_market_maker.domain.enums import OrderState


@dataclass
class StrategyOrder:
    """Strategy order tracking with state machine.

    Tracks the full lifecycle of an order from strategy decision
    through execution and fill.

    Attributes:
        cl_ord_id: Client-assigned order ID (unique)
        inst_id: Instrument ID
        side: Order side ("buy" or "sell")
        price: Order price
        size: Order size
        state: Current order state
        ord_id: Exchange-assigned order ID (after ACK)
        filled_size: Accumulated fill size
        avg_fill_price: Average fill price
        created_at: Order creation timestamp
        updated_at: Last update timestamp
        amend_price: Pending amendment price
        amend_size: Pending amendment size

    Example:
        # Create order
        order = StrategyOrder(
            cl_ord_id="mm_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
        )

        # Track lifecycle
        order.mark_sent()
        order.mark_ack(ord_id="exchange_123")
        order.mark_live()
        order.record_fill(Decimal("0.0005"), Decimal("50001"))
        order.record_fill(Decimal("0.0005"), Decimal("50002"))
        assert order.is_filled
    """

    cl_ord_id: str
    inst_id: str
    side: Literal["buy", "sell"]
    price: Decimal
    size: Decimal
    state: OrderState = OrderState.PENDING
    ord_id: str | None = None
    filled_size: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    amend_price: Decimal | None = None
    amend_size: Decimal | None = None
    error_message: str | None = None

    # --- State Properties ---

    @property
    def is_pending(self) -> bool:
        """Check if order is pending (not yet sent)."""
        return self.state == OrderState.PENDING

    @property
    def is_sent(self) -> bool:
        """Check if order has been sent."""
        return self.state == OrderState.SENT

    @property
    def is_live(self) -> bool:
        """Check if order is live on exchange."""
        return self.state in (OrderState.LIVE, OrderState.PARTIALLY_FILLED)

    @property
    def is_active(self) -> bool:
        """Check if order is still active (not terminal)."""
        return self.state not in (
            OrderState.FILLED,
            OrderState.CANCELED,
            OrderState.REJECTED,
        )

    @property
    def is_terminal(self) -> bool:
        """Check if order is in terminal state."""
        return not self.is_active

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.state == OrderState.FILLED

    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.state == OrderState.PARTIALLY_FILLED

    @property
    def is_canceled(self) -> bool:
        """Check if order was canceled."""
        return self.state == OrderState.CANCELED

    @property
    def is_rejected(self) -> bool:
        """Check if order was rejected."""
        return self.state == OrderState.REJECTED

    @property
    def is_amending(self) -> bool:
        """Check if order has pending amendment."""
        return self.state == OrderState.AMENDING

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.side == "buy"

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.side == "sell"

    # --- Calculated Properties ---

    @property
    def remaining_size(self) -> Decimal:
        """Calculate remaining unfilled size."""
        return self.size - self.filled_size

    @property
    def fill_ratio(self) -> Decimal:
        """Calculate fill ratio (0-1)."""
        if self.size == 0:
            return Decimal("0")
        return self.filled_size / self.size

    @property
    def fill_percent(self) -> Decimal:
        """Calculate fill percentage (0-100)."""
        return self.fill_ratio * 100

    @property
    def effective_price(self) -> Decimal:
        """Get effective price (amended price if amending, else current)."""
        if self.amend_price is not None and self.is_amending:
            return self.amend_price
        return self.price

    @property
    def effective_size(self) -> Decimal:
        """Get effective size (amended size if amending, else current)."""
        if self.amend_size is not None and self.is_amending:
            return self.amend_size
        return self.size

    # --- State Transitions ---

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    def mark_sent(self) -> None:
        """Mark order as sent to exchange."""
        if self.state != OrderState.PENDING:
            raise ValueError(f"Cannot mark as sent from state {self.state}")
        self.state = OrderState.SENT
        self._touch()

    def mark_ack(self, ord_id: str) -> None:
        """Mark order as acknowledged by exchange.

        Args:
            ord_id: Exchange-assigned order ID
        """
        if self.state != OrderState.SENT:
            raise ValueError(f"Cannot mark as ack from state {self.state}")
        self.ord_id = ord_id
        self.state = OrderState.ACK
        self._touch()

    def mark_live(self) -> None:
        """Mark order as live on exchange."""
        if self.state not in (OrderState.ACK, OrderState.AMENDING):
            raise ValueError(f"Cannot mark as live from state {self.state}")
        self.state = OrderState.LIVE
        self.amend_price = None
        self.amend_size = None
        self._touch()

    def mark_rejected(self, error: str | None = None) -> None:
        """Mark order as rejected.

        Args:
            error: Error message from exchange
        """
        self.state = OrderState.REJECTED
        self.error_message = error
        self._touch()

    def mark_canceled(self) -> None:
        """Mark order as canceled."""
        if self.state not in (OrderState.LIVE, OrderState.PARTIALLY_FILLED, OrderState.AMENDING):
            raise ValueError(f"Cannot cancel from state {self.state}")
        self.state = OrderState.CANCELED
        self._touch()

    def mark_amending(self, new_price: Decimal | None = None, new_size: Decimal | None = None) -> None:
        """Mark order as being amended.

        Args:
            new_price: New price (optional)
            new_size: New size (optional)
        """
        if self.state not in (OrderState.LIVE, OrderState.PARTIALLY_FILLED):
            raise ValueError(f"Cannot amend from state {self.state}")
        self.state = OrderState.AMENDING
        self.amend_price = new_price
        self.amend_size = new_size
        self._touch()

    def record_fill(self, fill_size: Decimal, fill_price: Decimal) -> None:
        """Record a fill for this order.

        Updates filled_size, avg_fill_price, and state.

        Args:
            fill_size: Size of this fill
            fill_price: Price of this fill
        """
        if not self.is_active:
            raise ValueError(f"Cannot fill order in state {self.state}")

        # Update average fill price
        if self.filled_size == 0:
            self.avg_fill_price = fill_price
        else:
            total_value = (self.avg_fill_price or Decimal("0")) * self.filled_size
            total_value += fill_price * fill_size
            self.avg_fill_price = total_value / (self.filled_size + fill_size)

        self.filled_size += fill_size

        # Update state
        if self.filled_size >= self.size:
            self.state = OrderState.FILLED
        else:
            self.state = OrderState.PARTIALLY_FILLED

        self._touch()

    def confirm_amend(self, new_price: Decimal | None = None, new_size: Decimal | None = None) -> None:
        """Confirm amendment was applied.

        Args:
            new_price: Confirmed new price
            new_size: Confirmed new size
        """
        if self.state != OrderState.AMENDING:
            raise ValueError(f"Cannot confirm amend from state {self.state}")

        if new_price is not None:
            self.price = new_price
        elif self.amend_price is not None:
            self.price = self.amend_price

        if new_size is not None:
            self.size = new_size
        elif self.amend_size is not None:
            self.size = self.amend_size

        self.amend_price = None
        self.amend_size = None
        self.state = OrderState.LIVE
        self._touch()

    # --- Utilities ---

    def update_from_exchange(
        self,
        state: str,
        filled_size: Decimal | None = None,
        avg_price: Decimal | None = None,
        ord_id: str | None = None,
    ) -> None:
        """Update order from exchange data.

        Maps exchange state strings to OrderState.

        Args:
            state: Exchange state string (live, filled, canceled, etc.)
            filled_size: Current filled size
            avg_price: Average fill price
            ord_id: Exchange order ID
        """
        state_map = {
            "live": OrderState.LIVE,
            "partially_filled": OrderState.PARTIALLY_FILLED,
            "filled": OrderState.FILLED,
            "canceled": OrderState.CANCELED,
            "mmp_canceled": OrderState.CANCELED,
        }

        if ord_id:
            self.ord_id = ord_id

        if filled_size is not None:
            self.filled_size = filled_size

        if avg_price is not None:
            self.avg_fill_price = avg_price

        if state in state_map:
            self.state = state_map[state]

        self._touch()

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/debugging.

        Returns:
            Dict representation of the order
        """
        return {
            "cl_ord_id": self.cl_ord_id,
            "ord_id": self.ord_id,
            "inst_id": self.inst_id,
            "side": self.side,
            "price": str(self.price),
            "size": str(self.size),
            "state": self.state.value,
            "filled_size": str(self.filled_size),
            "avg_fill_price": str(self.avg_fill_price) if self.avg_fill_price else None,
            "remaining_size": str(self.remaining_size),
        }
