"""Grid market maker strategy - symmetric grid.

Basic market making strategy that places symmetric orders around the mid price.
Orders are placed at fixed percentage steps from the best bid/ask.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from samples.okx_market_maker.domain.models.quote import Quote
from samples.okx_market_maker.domain.strategies.base_strategy import BaseStrategy

if TYPE_CHECKING:
    from samples.okx_market_maker.application.context.market_context import MarketContext


class GridStrategy(BaseStrategy):
    """Symmetric grid market making strategy.

    Places buy orders below best bid and sell orders above best ask
    at fixed percentage intervals.

    Order placement:
        - Buy orders: best_bid * (1 - step_pct * i) for i in [1, num_orders]
        - Sell orders: best_ask * (1 + step_pct * i) for i in [1, num_orders]

    Position-aware adjustment:
        - Reduces buy orders when long position
        - Reduces sell orders when short position

    Example:
        With step_pct=0.001 (0.1%) and num_orders=5:
        - Buy orders at -0.1%, -0.2%, -0.3%, -0.4%, -0.5% from best bid
        - Sell orders at +0.1%, +0.2%, +0.3%, +0.4%, +0.5% from best ask

    Configuration:
        - step_pct: Price step between orders (default: 0.001 = 0.1%)
        - num_orders_per_side: Orders per side (default: 5)
        - single_order_size: Size per order
        - max_net_buy/sell: Position limits
    """

    def compute_quotes(self, context: MarketContext) -> list[Quote]:
        """Compute symmetric grid quotes around best bid/ask.

        Args:
            context: Current market context

        Returns:
            List of quotes to place
        """
        best_bid = context.best_bid
        best_ask = context.best_ask

        if best_bid is None or best_ask is None:
            return []

        quotes: list[Quote] = []
        tick_size = context.tick_size
        lot_size = context.lot_size

        # Get settings
        step_pct = self.settings.step_pct
        num_orders = self.settings.num_orders_per_side
        order_size = self.settings.effective_order_size

        # Position-aware order count adjustment
        net_pos = context.net_position
        max_buy = self.settings.max_net_buy
        max_sell = self.settings.max_net_sell

        # Reduce orders on the side that would increase position
        buy_orders = num_orders
        sell_orders = num_orders

        if net_pos > 0:
            # Long position - reduce buys, keep sells
            position_ratio = net_pos / max_buy
            buy_orders = max(1, int(num_orders * (1 - position_ratio)))
        elif net_pos < 0:
            # Short position - reduce sells, keep buys
            position_ratio = abs(net_pos) / max_sell
            sell_orders = max(1, int(num_orders * (1 - position_ratio)))

        # Generate buy quotes (below best bid)
        for i in range(1, buy_orders + 1):
            price = best_bid * (Decimal("1") - step_pct * i)
            price = self.round_price(price, tick_size)
            size = self.round_size(order_size, lot_size)

            if size >= context.min_size:
                quotes.append(Quote(price=price, size=size, side="buy"))

        # Generate sell quotes (above best ask)
        for i in range(1, sell_orders + 1):
            price = best_ask * (Decimal("1") + step_pct * i)
            price = self.round_price(price, tick_size)
            size = self.round_size(order_size, lot_size)

            if size >= context.min_size:
                quotes.append(Quote(price=price, size=size, side="sell"))

        return quotes


# Alias for backwards compatibility
SampleMMStrategy = GridStrategy
