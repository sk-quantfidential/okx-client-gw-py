"""Risk calculator for market maker.

Calculates risk metrics including P&L, exposure, and position limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from samples.okx_market_maker.context.market_context import MarketContext
    from samples.okx_market_maker.config.settings import MarketMakerSettings


@dataclass(frozen=True)
class RiskMetrics:
    """Risk metrics snapshot.

    Attributes:
        net_position: Current net position
        position_value_usd: Position value in USD
        unrealized_pnl: Unrealized P&L
        realized_pnl: Realized P&L
        total_pnl: Total P&L (realized + unrealized)
        buy_exposure: Total buy order exposure
        sell_exposure: Total sell order exposure
        max_position_used_pct: Percentage of max position used
        is_within_limits: Whether within all risk limits
    """

    net_position: Decimal
    position_value_usd: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    buy_exposure: Decimal
    sell_exposure: Decimal
    max_position_used_pct: Decimal
    is_within_limits: bool


class RiskCalculator:
    """Calculator for risk metrics and limit checking.

    Provides real-time risk metrics based on current market state
    and active orders.

    Example:
        calculator = RiskCalculator(settings)
        metrics = calculator.calculate(context)

        if not metrics.is_within_limits:
            # Halt trading
            pass
    """

    def __init__(self, settings: MarketMakerSettings) -> None:
        """Initialize risk calculator.

        Args:
            settings: Market maker configuration
        """
        self.settings = settings
        self._realized_pnl = Decimal("0")

    def calculate(self, context: MarketContext) -> RiskMetrics:
        """Calculate current risk metrics.

        Args:
            context: Current market context

        Returns:
            RiskMetrics with current risk state
        """
        net_pos = context.net_position
        mid_price = context.mid_price or Decimal("0")

        # Calculate position value
        position_value_usd = abs(net_pos) * mid_price

        # Calculate unrealized P&L
        # This is simplified - real implementation would use entry prices
        unrealized_pnl = self._calculate_unrealized_pnl(context)

        # Calculate order exposure
        buy_exposure = sum(
            order.size * order.price
            for order in context.active_buy_orders
        )
        sell_exposure = sum(
            order.size * order.price
            for order in context.active_sell_orders
        )

        # Calculate position limit usage
        max_pos = max(self.settings.max_net_buy, self.settings.max_net_sell)
        if max_pos > 0:
            max_position_used_pct = abs(net_pos) / max_pos * 100
        else:
            max_position_used_pct = Decimal("0")

        # Check if within limits
        is_within_limits = self._check_limits(
            net_pos,
            position_value_usd,
            buy_exposure,
            sell_exposure,
        )

        return RiskMetrics(
            net_position=net_pos,
            position_value_usd=position_value_usd,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self._realized_pnl,
            total_pnl=self._realized_pnl + unrealized_pnl,
            buy_exposure=buy_exposure,
            sell_exposure=sell_exposure,
            max_position_used_pct=max_position_used_pct,
            is_within_limits=is_within_limits,
        )

    def _calculate_unrealized_pnl(self, context: MarketContext) -> Decimal:
        """Calculate unrealized P&L from current position.

        Simplified calculation - uses mid price vs average fill.

        Args:
            context: Market context

        Returns:
            Unrealized P&L
        """
        pos = context.position_for_inst
        if pos is None or pos.pos == 0:
            return Decimal("0")

        return pos.upl

    def _check_limits(
        self,
        net_pos: Decimal,
        position_value_usd: Decimal,
        buy_exposure: Decimal,
        sell_exposure: Decimal,
    ) -> bool:
        """Check if all risk limits are satisfied.

        Args:
            net_pos: Net position
            position_value_usd: Position value in USD
            buy_exposure: Buy order exposure
            sell_exposure: Sell order exposure

        Returns:
            True if within all limits
        """
        # Check position limits
        if net_pos > self.settings.max_net_buy:
            return False
        if net_pos < -self.settings.max_net_sell:
            return False

        # Check position value limit
        if position_value_usd > self.settings.max_position_value_usd:
            return False

        return True

    def record_fill(
        self,
        side: str,
        size: Decimal,
        price: Decimal,
        avg_position_price: Decimal | None,
    ) -> Decimal:
        """Record a fill and calculate realized P&L.

        Args:
            side: "buy" or "sell"
            size: Fill size
            price: Fill price
            avg_position_price: Average position price before fill

        Returns:
            Realized P&L from this fill
        """
        # This is a simplified P&L calculation
        # Real implementation would track entry prices properly
        if avg_position_price is None:
            return Decimal("0")

        if side == "sell":
            # Selling - realize profit/loss vs avg position price
            pnl = (price - avg_position_price) * size
        else:
            # Buying to close short
            pnl = (avg_position_price - price) * size

        self._realized_pnl += pnl
        return pnl

    @property
    def realized_pnl(self) -> Decimal:
        """Get total realized P&L."""
        return self._realized_pnl

    def reset_pnl(self) -> None:
        """Reset realized P&L tracking."""
        self._realized_pnl = Decimal("0")
