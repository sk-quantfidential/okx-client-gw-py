"""Margin calculation domain service.

Calculates margin metrics and stress scenarios for delta-neutral positions
in portfolio margin mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from samples.okx_portfolio_margin_monitor.core.config import (
    MARGIN_LIQUIDATION_THRESHOLD,
    MARGIN_WARNING_THRESHOLD,
)

if TYPE_CHECKING:
    from okx_client_gw.domain.models.account import AccountBalance
    from okx_client_gw.domain.models.position import Position
    from samples.okx_portfolio_margin_monitor.domain.models.holdings import SpotHolding


class MarginCalculator:
    """Calculates margin metrics and stress scenarios.

    Pure domain service with no external dependencies.
    """

    @staticmethod
    def calculate_stress_scenario(
        balance: AccountBalance,
        spot_holdings: list[SpotHolding],
        positions: list[Position],
        price_change_pct: float,
    ) -> dict:
        """Simulate margin impact of a price change.

        Args:
            balance: Current account balance
            spot_holdings: Current spot holdings
            positions: Current derivative positions
            price_change_pct: Price change as decimal (e.g., -0.20 for -20%)

        Returns:
            Dict with projected margin metrics
        """
        # Find BTC spot holding
        btc_spot = next((h for h in spot_holdings if h.currency == "BTC"), None)
        btc_spot_value = btc_spot.discounted_value if btc_spot else 0

        # Find BTC-USDT perp position
        btc_perp = next(
            (p for p in positions if "BTC-USDT" in p.inst_id and "SWAP" in p.inst_id),
            None,
        )

        if not btc_spot and not btc_perp:
            return {"error": "No BTC positions found"}

        # Calculate changes
        # Spot: Value changes proportionally (with discount rate)
        spot_value_change = btc_spot_value * price_change_pct

        # Perp: Short position profits when price drops
        perp_pnl_change = 0.0
        if btc_perp and float(btc_perp.pos) < 0:  # Short position
            perp_pnl_change = float(btc_perp.notional_usd) * (-price_change_pct)
        elif btc_perp and float(btc_perp.pos) > 0:  # Long position
            perp_pnl_change = float(btc_perp.notional_usd) * price_change_pct

        # Net effect on adjusted equity
        net_adj_eq_change = spot_value_change + perp_pnl_change

        # Project new margin ratio
        adj_eq = float(balance.adj_eq)
        mmr = float(balance.mmr)
        new_adj_eq = adj_eq + net_adj_eq_change
        new_margin_ratio = (new_adj_eq / mmr * 100) if mmr > 0 else float("inf")

        margin_ratio = float(balance.mgn_ratio) * 100 if balance.mgn_ratio else 0

        return {
            "price_change_pct": price_change_pct * 100,
            "current_adj_eq": adj_eq,
            "spot_value_change": spot_value_change,
            "perp_pnl_change": perp_pnl_change,
            "net_change": net_adj_eq_change,
            "projected_adj_eq": new_adj_eq,
            "current_margin_ratio": margin_ratio,
            "projected_margin_ratio": new_margin_ratio,
            "above_liquidation": new_margin_ratio > MARGIN_LIQUIDATION_THRESHOLD,
            "above_warning": new_margin_ratio > MARGIN_WARNING_THRESHOLD,
        }

    @staticmethod
    def find_liquidation_price(
        balance: AccountBalance,
        spot_holdings: list[SpotHolding],
        positions: list[Position],
        current_btc_price: float,
    ) -> dict:
        """Find the BTC price at which liquidation would occur.

        Uses binary search to find the price where margin_ratio = 100%.

        Args:
            balance: Current account balance
            spot_holdings: Current spot holdings
            positions: Current derivative positions
            current_btc_price: Current BTC price

        Returns:
            Dict with liquidation analysis results
        """
        btc_spot = next((h for h in spot_holdings if h.currency == "BTC"), None)
        btc_perp = next(
            (p for p in positions if "BTC-USDT" in p.inst_id and "SWAP" in p.inst_id),
            None,
        )

        if not btc_spot or not btc_perp:
            return {"error": "Need both spot and perp positions"}

        # Binary search for liquidation price
        low_pct, high_pct = -0.99, 2.0  # -99% to +200%
        mid_pct = 0.0

        for _ in range(50):  # 50 iterations for precision
            mid_pct = (low_pct + high_pct) / 2
            result = MarginCalculator.calculate_stress_scenario(
                balance, spot_holdings, positions, mid_pct
            )

            if abs(result["projected_margin_ratio"] - 100) < 0.1:
                break

            if result["projected_margin_ratio"] > 100:
                low_pct = mid_pct  # Need more drop to hit liquidation
            else:
                high_pct = mid_pct  # Overshot, need less drop

        liquidation_price = current_btc_price * (1 + mid_pct)

        return {
            "current_price": current_btc_price,
            "liquidation_price": liquidation_price,
            "price_drop_pct": mid_pct * 100,
            "price_drop_usd": current_btc_price - liquidation_price,
        }
