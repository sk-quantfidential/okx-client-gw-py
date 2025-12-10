"""Market context - centralized state container for market maker.

Replaces global state with dependency-injected context.
Thread-safe updates with proper synchronization.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from okx_client_gw.domain.models.account import AccountBalance
    from okx_client_gw.domain.models.instrument import Instrument
    from okx_client_gw.domain.models.orderbook import OrderBook
    from okx_client_gw.domain.models.position import Position
    from okx_client_gw.domain.models.ticker import Ticker

    from samples.okx_market_maker.models.strategy_order import StrategyOrder


@dataclass
class MarketContext:
    """Centralized state container for market maker.

    Holds all market data and account state needed for strategy decisions.
    Designed to replace global state with explicit dependency injection.

    Thread-safe: Uses asyncio.Lock for concurrent updates.

    Attributes:
        inst_id: Instrument being traded
        instrument: Instrument specification (tick size, lot size, etc.)
        orderbook: Current order book snapshot
        ticker: Current ticker data
        account: Current account balance
        positions: Current positions by instrument
        live_orders: Active strategy orders by client order ID
        net_filled_buy: Net filled buy quantity
        net_filled_sell: Net filled sell quantity

    Example:
        context = MarketContext(inst_id="BTC-USDT")

        # Update market data
        async with context.lock:
            context.update_orderbook(orderbook)
            context.update_ticker(ticker)

        # Check data freshness
        if context.is_data_fresh():
            decision = strategy.decide(context)
    """

    inst_id: str
    instrument: Instrument | None = None
    orderbook: OrderBook | None = None
    ticker: Ticker | None = None
    account: AccountBalance | None = None
    positions: dict[str, Position] = field(default_factory=dict)
    live_orders: dict[str, StrategyOrder] = field(default_factory=dict)

    # Fill tracking
    net_filled_buy: Decimal = Decimal("0")
    net_filled_sell: Decimal = Decimal("0")

    # Timestamps for staleness checking
    orderbook_time: datetime | None = None
    ticker_time: datetime | None = None
    account_time: datetime | None = None
    position_time: datetime | None = None

    # Volatility tracking for volatility strategy
    recent_prices: list[Decimal] = field(default_factory=list)
    max_price_history: int = 100

    # Synchronization
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def lock(self) -> asyncio.Lock:
        """Get the context lock for thread-safe updates."""
        return self._lock

    # --- Market Data Properties ---

    @property
    def best_bid(self) -> Decimal | None:
        """Get best bid price from orderbook."""
        if self.orderbook is None or not self.orderbook.bids:
            return None
        return self.orderbook.bids[0].price

    @property
    def best_ask(self) -> Decimal | None:
        """Get best ask price from orderbook."""
        if self.orderbook is None or not self.orderbook.asks:
            return None
        return self.orderbook.asks[0].price

    @property
    def mid_price(self) -> Decimal | None:
        """Calculate mid price from best bid/ask."""
        bid = self.best_bid
        ask = self.best_ask
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2

    @property
    def spread(self) -> Decimal | None:
        """Calculate current spread."""
        bid = self.best_bid
        ask = self.best_ask
        if bid is None or ask is None:
            return None
        return ask - bid

    @property
    def spread_pct(self) -> Decimal | None:
        """Calculate spread as percentage of mid price."""
        spread = self.spread
        mid = self.mid_price
        if spread is None or mid is None or mid == 0:
            return None
        return spread / mid

    @property
    def last_price(self) -> Decimal | None:
        """Get last traded price from ticker."""
        if self.ticker is None:
            return None
        return self.ticker.last

    # --- Position Properties ---

    @property
    def net_position(self) -> Decimal:
        """Calculate net position (buys - sells)."""
        return self.net_filled_buy - self.net_filled_sell

    @property
    def position_for_inst(self) -> Position | None:
        """Get position for the traded instrument."""
        return self.positions.get(self.inst_id)

    @property
    def current_position_size(self) -> Decimal:
        """Get current position size from positions or fill tracking."""
        pos = self.position_for_inst
        if pos is not None:
            return pos.pos
        return self.net_position

    # --- Order Properties ---

    @property
    def active_buy_orders(self) -> list[StrategyOrder]:
        """Get all active buy orders."""
        from samples.okx_market_maker.models.strategy_order import OrderState

        return [
            order for order in self.live_orders.values()
            if order.side == "buy" and order.state not in (
                OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED
            )
        ]

    @property
    def active_sell_orders(self) -> list[StrategyOrder]:
        """Get all active sell orders."""
        from samples.okx_market_maker.models.strategy_order import OrderState

        return [
            order for order in self.live_orders.values()
            if order.side == "sell" and order.state not in (
                OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED
            )
        ]

    @property
    def num_active_buy_orders(self) -> int:
        """Count active buy orders."""
        return len(self.active_buy_orders)

    @property
    def num_active_sell_orders(self) -> int:
        """Count active sell orders."""
        return len(self.active_sell_orders)

    # --- Instrument Properties ---

    @property
    def tick_size(self) -> Decimal:
        """Get tick size from instrument, default to 0.01."""
        if self.instrument is None:
            return Decimal("0.01")
        return self.instrument.tick_sz

    @property
    def lot_size(self) -> Decimal:
        """Get lot size from instrument, default to 0.0001."""
        if self.instrument is None:
            return Decimal("0.0001")
        return self.instrument.lot_sz

    @property
    def min_size(self) -> Decimal:
        """Get minimum order size from instrument."""
        if self.instrument is None:
            return Decimal("0.0001")
        return self.instrument.min_sz

    # --- Data Freshness ---

    def is_orderbook_fresh(self, max_age_sec: float = 5.0) -> bool:
        """Check if orderbook data is fresh.

        Args:
            max_age_sec: Maximum age in seconds

        Returns:
            True if orderbook was updated within max_age_sec
        """
        if self.orderbook_time is None:
            return False
        age = (datetime.now(UTC) - self.orderbook_time).total_seconds()
        return age <= max_age_sec

    def is_account_fresh(self, max_age_sec: float = 10.0) -> bool:
        """Check if account data is fresh.

        Args:
            max_age_sec: Maximum age in seconds

        Returns:
            True if account was updated within max_age_sec
        """
        if self.account_time is None:
            return False
        age = (datetime.now(UTC) - self.account_time).total_seconds()
        return age <= max_age_sec

    def is_position_fresh(self, max_age_sec: float = 10.0) -> bool:
        """Check if position data is fresh.

        Args:
            max_age_sec: Maximum age in seconds

        Returns:
            True if position was updated within max_age_sec
        """
        if self.position_time is None:
            # No position data yet is ok if we have no position
            return True
        age = (datetime.now(UTC) - self.position_time).total_seconds()
        return age <= max_age_sec

    def is_data_fresh(
        self,
        orderbook_max_age: float = 5.0,
        account_max_age: float = 10.0,
        position_max_age: float = 10.0,
    ) -> bool:
        """Check if all required data is fresh.

        Args:
            orderbook_max_age: Max orderbook age in seconds
            account_max_age: Max account age in seconds
            position_max_age: Max position age in seconds

        Returns:
            True if all data is fresh enough for trading
        """
        return (
            self.is_orderbook_fresh(orderbook_max_age)
            and self.is_account_fresh(account_max_age)
            and self.is_position_fresh(position_max_age)
        )

    # --- Update Methods ---

    def update_orderbook(self, orderbook: OrderBook) -> None:
        """Update orderbook and timestamp.

        Args:
            orderbook: New orderbook snapshot
        """
        self.orderbook = orderbook
        self.orderbook_time = datetime.now(UTC)

        # Track price for volatility
        if self.mid_price is not None:
            self.recent_prices.append(self.mid_price)
            if len(self.recent_prices) > self.max_price_history:
                self.recent_prices.pop(0)

    def update_ticker(self, ticker: Ticker) -> None:
        """Update ticker and timestamp.

        Args:
            ticker: New ticker data
        """
        self.ticker = ticker
        self.ticker_time = datetime.now(UTC)

    def update_account(self, account: AccountBalance) -> None:
        """Update account balance and timestamp.

        Args:
            account: New account balance
        """
        self.account = account
        self.account_time = datetime.now(UTC)

    def update_position(self, position: Position) -> None:
        """Update position for an instrument.

        Args:
            position: New position data
        """
        self.positions[position.inst_id] = position
        self.position_time = datetime.now(UTC)

    def update_instrument(self, instrument: Instrument) -> None:
        """Update instrument specification.

        Args:
            instrument: Instrument specification
        """
        self.instrument = instrument

    # --- Order Management ---

    def add_order(self, order: StrategyOrder) -> None:
        """Add a strategy order to tracking.

        Args:
            order: Strategy order to track
        """
        self.live_orders[order.cl_ord_id] = order

    def get_order(self, cl_ord_id: str) -> StrategyOrder | None:
        """Get a tracked order by client order ID.

        Args:
            cl_ord_id: Client order ID

        Returns:
            Strategy order or None if not found
        """
        return self.live_orders.get(cl_ord_id)

    def remove_order(self, cl_ord_id: str) -> StrategyOrder | None:
        """Remove an order from tracking.

        Args:
            cl_ord_id: Client order ID

        Returns:
            Removed order or None if not found
        """
        return self.live_orders.pop(cl_ord_id, None)

    def record_fill(self, side: str, size: Decimal) -> None:
        """Record a fill for position tracking.

        Args:
            side: "buy" or "sell"
            size: Fill size
        """
        if side == "buy":
            self.net_filled_buy += size
        else:
            self.net_filled_sell += size

    def clear_terminal_orders(self) -> int:
        """Remove all filled/canceled orders from tracking.

        Returns:
            Number of orders removed
        """
        from samples.okx_market_maker.models.strategy_order import OrderState

        terminal_states = {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED}
        to_remove = [
            cl_ord_id for cl_ord_id, order in self.live_orders.items()
            if order.state in terminal_states
        ]
        for cl_ord_id in to_remove:
            del self.live_orders[cl_ord_id]
        return len(to_remove)

    # --- Volatility Calculation ---

    def calculate_volatility(self, lookback: int = 20) -> Decimal | None:
        """Calculate recent price volatility.

        Uses standard deviation of price returns.

        Args:
            lookback: Number of prices to consider

        Returns:
            Volatility as decimal, or None if insufficient data
        """
        if len(self.recent_prices) < lookback + 1:
            return None

        prices = self.recent_prices[-lookback - 1:]
        returns = [
            (prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, len(prices))
        ]

        if not returns:
            return None

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)

        # Return standard deviation
        return Decimal(str(variance)).sqrt()
