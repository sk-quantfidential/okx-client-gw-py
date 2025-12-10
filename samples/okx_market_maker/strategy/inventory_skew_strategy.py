"""Inventory skew market making strategy.

Extends the basic grid strategy with inventory-based price skewing.
Shifts the mid price based on current position to encourage mean reversion.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from samples.okx_market_maker.strategy.base_strategy import BaseStrategy
from samples.okx_market_maker.strategy.strategy_protocol import Quote

if TYPE_CHECKING:
    from samples.okx_market_maker.context.market_context import MarketContext


class InventorySkewStrategy(BaseStrategy):
    """Inventory-based price skewing strategy.

    Like SampleMMStrategy but shifts prices based on current inventory:
    - Long position: Lower prices to encourage sells (reduce inventory)
    - Short position: Raise prices to encourage buys (reduce inventory)

    The skew is proportional to position size relative to limits.

    Skew calculation:
        skew_pct = skew_factor * (position / max_position) * max_skew_pct

    Order placement:
        - Buy: (mid - skew) * (1 - step_pct * i)
        - Sell: (mid + skew) * (1 + step_pct * i)

    Example:
        With position=50, max_position=100, skew_factor=0.5, max_skew=0.5%:
        - skew = 0.5 * (50/100) * 0.005 = 0.00125 (0.125%)
        - Prices shifted down by 0.125% to encourage selling

    Configuration:
        - skew_factor: Aggressiveness of inventory skew (0-1)
        - max_skew_pct: Maximum price skew percentage
        - (plus all SampleMMStrategy settings)
    """

    def compute_quotes(self, context: MarketContext) -> list[Quote]:
        """Compute inventory-skewed quotes.

        Args:
            context: Current market context

        Returns:
            List of quotes with inventory-based price skew
        """
        mid = context.mid_price
        if mid is None:
            return []

        quotes: list[Quote] = []
        tick_size = context.tick_size
        lot_size = context.lot_size

        # Get settings
        step_pct = self.settings.step_pct
        num_orders = self.settings.num_orders_per_side
        order_size = self.settings.effective_order_size
        skew_factor = self.settings.skew_factor
        max_skew_pct = self.settings.max_skew_pct

        # Calculate inventory skew
        net_pos = context.net_position
        max_pos = max(self.settings.max_net_buy, self.settings.max_net_sell)

        if max_pos > 0:
            # Normalize position to [-1, 1]
            position_ratio = net_pos / max_pos
            # Calculate skew (negative skew shifts prices down)
            skew_pct = skew_factor * position_ratio * max_skew_pct
        else:
            skew_pct = Decimal("0")

        # Clamp skew to max
        skew_pct = max(-max_skew_pct, min(max_skew_pct, skew_pct))

        # Calculate skewed mid price
        # Positive position -> negative skew -> lower mid -> cheaper buys, more attractive sells
        skewed_mid = mid * (Decimal("1") - skew_pct)

        # Position-aware order count adjustment
        max_buy = self.settings.max_net_buy
        max_sell = self.settings.max_net_sell

        buy_orders = num_orders
        sell_orders = num_orders

        if net_pos > 0:
            # Long - reduce buys more aggressively
            position_ratio = net_pos / max_buy
            buy_orders = max(1, int(num_orders * (1 - position_ratio * Decimal("1.5"))))
        elif net_pos < 0:
            # Short - reduce sells more aggressively
            position_ratio = abs(net_pos) / max_sell
            sell_orders = max(1, int(num_orders * (1 - position_ratio * Decimal("1.5"))))

        # Calculate base spread from step
        half_spread = skewed_mid * step_pct

        # Generate buy quotes (below skewed mid)
        for i in range(1, buy_orders + 1):
            price = skewed_mid - half_spread * i
            price = self.round_price(price, tick_size)
            size = self.round_size(order_size, lot_size)

            if size >= context.min_size and price > 0:
                quotes.append(Quote(price=price, size=size, side="buy"))

        # Generate sell quotes (above skewed mid)
        for i in range(1, sell_orders + 1):
            price = skewed_mid + half_spread * i
            price = self.round_price(price, tick_size)
            size = self.round_size(order_size, lot_size)

            if size >= context.min_size:
                quotes.append(Quote(price=price, size=size, side="sell"))

        return quotes
