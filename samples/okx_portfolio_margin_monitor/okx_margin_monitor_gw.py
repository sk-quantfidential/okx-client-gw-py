#!/usr/bin/env python3
"""
OKX Delta-Neutral Position Margin Monitor (Gateway Version)

Monitors margin health for spot BTC + short BTC-USDT perpetual positions.
Calculates real-time margin ratios, stress tests, and liquidation distances.

This version uses the okx-client-gw library instead of raw HTTP requests.

Usage:
    python okx_margin_monitor_gw.py --demo
    python okx_margin_monitor_gw.py --loop 30  # Refresh every 30 seconds

Requirements:
    pip install okx-client-gw
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from okx_client_gw import OkxConfig, OkxHttpClient
from okx_client_gw.application.services import AccountService, PublicDataService
from okx_client_gw.core.auth import OkxCredentials

if TYPE_CHECKING:
    from okx_client_gw.domain.models.account import AccountBalance
    from okx_client_gw.domain.models.position import Position

# =============================================================================
# Configuration
# =============================================================================

# Margin thresholds (OKX uses percentage format where 100% = liquidation)
MARGIN_WARNING_THRESHOLD = 300  # OKX sends warning at 300%
MARGIN_DANGER_THRESHOLD = 150  # You probably want to act here
MARGIN_LIQUIDATION_THRESHOLD = 100  # Forced liquidation triggered


# =============================================================================
# Helper Data Classes
# =============================================================================


@dataclass
class SpotHolding:
    """Spot asset holding extracted from account balance."""

    currency: str
    balance: float
    equity: float
    usd_value: float
    discount_rate: float
    discounted_value: float


# =============================================================================
# Margin Calculator
# =============================================================================


class MarginCalculator:
    """Calculates margin metrics and stress scenarios."""

    @staticmethod
    def calculate_stress_scenario(
        balance: AccountBalance,
        spot_holdings: list[SpotHolding],
        positions: list[Position],
        price_change_pct: float,
    ) -> dict:
        """
        Simulate margin impact of a price change.

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
        """
        Find the BTC price at which liquidation would occur.
        Uses binary search to find the price where margin_ratio = 100%.
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


# =============================================================================
# Margin Monitor (using okx-client-gw)
# =============================================================================


class MarginMonitor:
    """Main monitoring class using okx-client-gw services."""

    def __init__(self, config: OkxConfig, credentials: OkxCredentials) -> None:
        self.config = config
        self.credentials = credentials

    def print_header(self, text: str) -> None:
        """Print a formatted header."""
        print(f"\n{'=' * 60}")
        print(f"  {text}")
        print("=" * 60)

    def print_section(self, text: str) -> None:
        """Print a section header."""
        print(f"\n  --- {text} ---")

    def _extract_spot_holdings(self, balance: AccountBalance) -> list[SpotHolding]:
        """Extract spot holdings from balance details."""
        holdings = []
        for detail in balance.details:
            equity = float(detail.eq)
            if equity <= 0:
                continue

            usd_value = float(detail.eq_usd)
            disc_equity = float(detail.dis_eq) if detail.dis_eq else usd_value

            # Calculate effective discount rate
            discount_rate = disc_equity / usd_value if usd_value > 0 else 1.0

            holdings.append(
                SpotHolding(
                    currency=detail.ccy,
                    balance=float(detail.avail_bal),
                    equity=equity,
                    usd_value=usd_value,
                    discount_rate=discount_rate,
                    discounted_value=disc_equity,
                )
            )

        return holdings

    def _get_health_status(self, margin_ratio: float) -> str:
        """Get health status string based on margin ratio."""
        if margin_ratio > MARGIN_WARNING_THRESHOLD:
            return "✅ HEALTHY"
        elif margin_ratio > MARGIN_DANGER_THRESHOLD:
            return "⚠️  WARNING"
        elif margin_ratio > MARGIN_LIQUIDATION_THRESHOLD:
            return "🔴 DANGER"
        else:
            return "💀 LIQUIDATION"

    async def run_full_report(self) -> None:
        """Generate comprehensive margin report using okx-client-gw."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.print_header(f"OKX MARGIN MONITOR (GW) - {timestamp}")

        async with OkxHttpClient(
            config=self.config, credentials=self.credentials
        ) as client:
            account_service = AccountService(client)
            public_service = PublicDataService(client)

            # Fetch account configuration
            account_config = await account_service.get_config()
            print(f"\n  Account Mode: {account_config.account_mode_name}")

            # Fetch balance and positions
            balance = await account_service.get_balance()
            positions = await account_service.get_positions()

            # Extract spot holdings from balance
            spot_holdings = self._extract_spot_holdings(balance)

            # Calculate margin metrics
            margin_ratio = float(balance.mgn_ratio) * 100 if balance.mgn_ratio else 0
            distance_to_warning = margin_ratio - MARGIN_WARNING_THRESHOLD
            distance_to_liquidation = margin_ratio - MARGIN_LIQUIDATION_THRESHOLD

            # Account Summary
            self.print_section("ACCOUNT SUMMARY")
            print(f"  Status:              {self._get_health_status(margin_ratio)}")
            print(f"  Margin Ratio:        {margin_ratio:.2f}%")
            print(f"  Distance to Warning: {distance_to_warning:+.2f}%")
            print(f"  Distance to Liq:     {distance_to_liquidation:+.2f}%")
            print()
            print(f"  Adjusted Equity:     ${float(balance.adj_eq):,.2f}")
            print(f"  Total Equity:        ${float(balance.total_eq):,.2f}")
            print(f"  Initial Margin:      ${float(balance.imr):,.2f}")
            print(f"  Maintenance Margin:  ${float(balance.mmr):,.2f}")

            # Spot Holdings
            self.print_section("SPOT HOLDINGS (Collateral)")
            if spot_holdings:
                print(
                    f"  {'Currency':<8} {'Balance':>12} {'USD Value':>14} {'Discount':>10} {'After Haircut':>14}"
                )
                print(
                    f"  {'-' * 8} {'-' * 12} {'-' * 14} {'-' * 10} {'-' * 14}"
                )
                for h in spot_holdings:
                    print(
                        f"  {h.currency:<8} {h.equity:>12.6f} ${h.usd_value:>13,.2f} {h.discount_rate * 100:>9.2f}% ${h.discounted_value:>13,.2f}"
                    )
            else:
                print("  No spot holdings")

            # Derivative Positions
            self.print_section("DERIVATIVE POSITIONS")
            if positions:
                for p in positions:
                    pos_qty = float(p.pos)
                    direction = "SHORT" if pos_qty < 0 else "LONG"
                    print(f"\n  {p.inst_id} ({direction})")
                    print(f"    Size:           {abs(pos_qty):.4f}")
                    print(f"    Notional:       ${float(p.notional_usd):,.2f}")
                    print(f"    Entry Price:    ${float(p.avg_px):,.2f}")
                    print(f"    Mark Price:     ${float(p.mark_px):,.2f}")
                    print(f"    Unrealised PnL: ${float(p.upl):+,.2f}")
                    print(f"    Leverage:       {float(p.lever):.1f}x")
                    if p.liq_px:
                        print(f"    Liq Price:      ${float(p.liq_px):,.2f}")
            else:
                print("  No derivative positions")

            # Stress Testing
            self.print_section("STRESS TEST SCENARIOS")

            scenarios = [-0.10, -0.20, -0.30, -0.40, -0.50, 0.20, 0.50]

            print(
                f"  {'Price Δ':>10} {'Spot Δ':>12} {'Perp PnL Δ':>12} {'Net Δ':>12} {'New Margin':>12} {'Status':>10}"
            )
            print(
                f"  {'-' * 10} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 10}"
            )

            for pct in scenarios:
                result = MarginCalculator.calculate_stress_scenario(
                    balance, spot_holdings, positions, pct
                )
                if "error" in result:
                    continue

                status = (
                    "✅"
                    if result["above_warning"]
                    else ("⚠️" if result["above_liquidation"] else "💀")
                )

                print(
                    f"  {pct * 100:>+9.0f}% ${result['spot_value_change']:>+11,.0f} ${result['perp_pnl_change']:>+11,.0f} ${result['net_change']:>+11,.0f} {result['projected_margin_ratio']:>11.1f}% {status:>10}"
                )

            # Find liquidation price
            btc_perp = next(
                (
                    p
                    for p in positions
                    if "BTC-USDT" in p.inst_id and "SWAP" in p.inst_id
                ),
                None,
            )
            if btc_perp:
                current_price = float(btc_perp.mark_px)
                liq_result = MarginCalculator.find_liquidation_price(
                    balance, spot_holdings, positions, current_price
                )

                if "error" not in liq_result:
                    self.print_section("LIQUIDATION ANALYSIS")
                    print(f"  Current BTC Price:    ${liq_result['current_price']:,.2f}")
                    print(
                        f"  Liquidation Price:    ${liq_result['liquidation_price']:,.2f}"
                    )
                    print(f"  Required Drop:        {liq_result['price_drop_pct']:.1f}%")
                    print(f"  Buffer:               ${liq_result['price_drop_usd']:,.2f}")

            # Discount Rate Info
            self.print_section("BTC DISCOUNT RATE TIERS")
            try:
                btc_rates = await public_service.get_discount_rates(ccy="BTC")
                print(
                    f"  {'Tier':>4} {'Min Amount':>14} {'Max Amount':>14} {'Discount Rate':>14}"
                )
                print(f"  {'-' * 4} {'-' * 14} {'-' * 14} {'-' * 14}")
                if btc_rates and btc_rates[0].discount_info:
                    for i, info in enumerate(btc_rates[0].discount_info[:5]):
                        max_str = (
                            f"{float(info.amt):,.2f}"
                            if float(info.amt) > 0
                            else "∞"
                        )
                        print(
                            f"  {i + 1:>4} {'0':>14} {max_str:>14} {float(info.discount_rate) * 100:>13.2f}%"
                        )
            except Exception as e:
                print(f"  Could not fetch discount rates: {e}")

            print("\n" + "=" * 60 + "\n")


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OKX Delta-Neutral Position Margin Monitor (Gateway Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full report (credentials from environment)
  python okx_margin_monitor_gw.py

  # Run in demo mode
  python okx_margin_monitor_gw.py --demo

  # Loop with refresh interval
  python okx_margin_monitor_gw.py --loop 30

Environment variables:
  OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE
        """,
    )

    parser.add_argument(
        "--demo", action="store_true", help="Use demo trading environment"
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Refresh interval in seconds (0 = run once)",
    )

    args = parser.parse_args()

    # Load credentials from environment
    try:
        credentials = OkxCredentials.from_env()
    except ValueError as e:
        print(f"Error loading credentials: {e}")
        print("\nSet environment variables:")
        print("  OKX_API_KEY")
        print("  OKX_SECRET_KEY")
        print("  OKX_PASSPHRASE")
        return

    # Create config
    config = OkxConfig(use_demo=args.demo)

    # Create monitor
    monitor = MarginMonitor(config, credentials)

    async def run_loop() -> None:
        while True:
            await monitor.run_full_report()

            if args.loop <= 0:
                break

            print(f"Refreshing in {args.loop} seconds... (Ctrl+C to stop)")
            await asyncio.sleep(args.loop)

    try:
        asyncio.run(run_loop())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()
