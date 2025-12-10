"""Volatility-adjusted market making strategy.

Adjusts spread based on recent price volatility:
- Higher volatility -> wider spreads (more protection)
- Lower volatility -> tighter spreads (more competitive)
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from samples.okx_market_maker.domain.models.quote import Quote
from samples.okx_market_maker.domain.strategies.base_strategy import BaseStrategy

if TYPE_CHECKING:
    from samples.okx_market_maker.application.context.market_context import MarketContext


class VolatilityStrategy(BaseStrategy):
    """Volatility-adjusted spread market making strategy.

    Dynamically adjusts spread based on recent price volatility.
    Combines volatility-based spreads with inventory skewing.

    Spread calculation:
        base_spread = volatility * volatility_multiplier
        spread = clamp(base_spread, min_spread_pct, max_spread_pct)

    Benefits:
        - Wider spreads in volatile markets reduce adverse selection
        - Tighter spreads in calm markets increase fill probability
        - Inventory skew helps manage position risk

    Configuration:
        - volatility_lookback: Number of price observations for vol calc
        - volatility_multiplier: Multiplier for volatility to spread
        - min_spread_pct: Minimum spread percentage
        - max_spread_pct: Maximum spread percentage
        - (plus inventory skew settings)
    """

    def compute_quotes(self, context: MarketContext) -> list[Quote]:
        """Compute volatility-adjusted quotes.

        Args:
            context: Current market context

        Returns:
            List of quotes with volatility-adjusted spreads
        """
        mid = context.mid_price
        if mid is None:
            return []

        quotes: list[Quote] = []
        tick_size = context.tick_size
        lot_size = context.lot_size

        # Get settings
        num_orders = self.settings.num_orders_per_side
        order_size = self.settings.effective_order_size
        vol_lookback = self.settings.volatility_lookback
        vol_multiplier = self.settings.volatility_multiplier
        min_spread = self.settings.min_spread_pct
        max_spread = self.settings.max_spread_pct
        skew_factor = self.settings.skew_factor
        max_skew_pct = self.settings.max_skew_pct

        # Calculate volatility-based spread
        volatility = context.calculate_volatility(vol_lookback)

        if volatility is not None:
            # Spread = volatility * multiplier, clamped to min/max
            spread_pct = volatility * vol_multiplier
            spread_pct = max(min_spread, min(max_spread, spread_pct))
        else:
            # Fall back to minimum spread if not enough data
            spread_pct = min_spread

        # Calculate inventory skew
        net_pos = context.net_position
        max_pos = max(self.settings.max_net_buy, self.settings.max_net_sell)

        if max_pos > 0:
            position_ratio = net_pos / max_pos
            skew_pct = skew_factor * position_ratio * max_skew_pct
        else:
            skew_pct = Decimal("0")

        skew_pct = max(-max_skew_pct, min(max_skew_pct, skew_pct))

        # Calculate skewed mid
        skewed_mid = mid * (Decimal("1") - skew_pct)

        # Position-aware order count
        max_buy = self.settings.max_net_buy
        max_sell = self.settings.max_net_sell

        buy_orders = num_orders
        sell_orders = num_orders

        if net_pos > 0:
            position_ratio = net_pos / max_buy
            buy_orders = max(1, int(num_orders * (1 - position_ratio)))
        elif net_pos < 0:
            position_ratio = abs(net_pos) / max_sell
            sell_orders = max(1, int(num_orders * (1 - position_ratio)))

        # Calculate half spread for each side
        half_spread = skewed_mid * spread_pct / 2

        # Generate buy quotes
        for i in range(1, buy_orders + 1):
            # Each level is half_spread * i below mid
            price = skewed_mid - half_spread * i
            price = self.round_price(price, tick_size)
            size = self.round_size(order_size, lot_size)

            if size >= context.min_size and price > 0:
                quotes.append(Quote(price=price, size=size, side="buy"))

        # Generate sell quotes
        for i in range(1, sell_orders + 1):
            price = skewed_mid + half_spread * i
            price = self.round_price(price, tick_size)
            size = self.round_size(order_size, lot_size)

            if size >= context.min_size:
                quotes.append(Quote(price=price, size=size, side="sell"))

        return quotes

    def should_halt(self, context: MarketContext) -> tuple[bool, str | None]:
        """Extended halt check including volatility circuit breaker.

        Args:
            context: Current market context

        Returns:
            Tuple of (should_halt, reason)
        """
        # Base checks
        should_halt, reason = super().should_halt(context)
        if should_halt:
            return should_halt, reason

        # Volatility circuit breaker
        volatility = context.calculate_volatility(self.settings.volatility_lookback)
        if volatility is not None:
            # Halt if volatility exceeds 3x max spread (extreme conditions)
            max_vol = self.settings.max_spread_pct * 3
            if volatility > max_vol:
                return True, f"Extreme volatility: {volatility:.4f} > {max_vol:.4f}"

        return False, None
