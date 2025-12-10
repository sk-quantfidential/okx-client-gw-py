"""Monitor service for portfolio margin monitoring.

Orchestrates data fetching, calculations, and report generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from okx_client_gw import OkxConfig, OkxHttpClient
from okx_client_gw.application.services import AccountService, PublicDataService
from okx_client_gw.core.auth import OkxCredentials
from samples.okx_portfolio_margin_monitor.core.config import (
    MARGIN_DANGER_THRESHOLD,
    MARGIN_LIQUIDATION_THRESHOLD,
    MARGIN_WARNING_THRESHOLD,
)
from samples.okx_portfolio_margin_monitor.domain.models.holdings import SpotHolding
from samples.okx_portfolio_margin_monitor.domain.services.margin_calculator import (
    MarginCalculator,
)

if TYPE_CHECKING:
    from okx_client_gw.domain.models.account import AccountBalance


class MonitorService:
    """Main monitoring service using okx-client-gw.

    Handles data fetching, report generation, and presentation
    for portfolio margin mode accounts.
    """

    def __init__(self, config: OkxConfig, credentials: OkxCredentials) -> None:
        """Initialize monitor service.

        Args:
            config: OKX client configuration
            credentials: API credentials
        """
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
        """Extract spot holdings from balance details.

        Args:
            balance: Account balance from OKX

        Returns:
            List of SpotHolding objects
        """
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
        """Get health status string based on margin ratio.

        Args:
            margin_ratio: Current margin ratio percentage

        Returns:
            Status string with emoji indicator
        """
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

        self.print_header(f"OKX MARGIN MONITOR (Portfolio GW) - {timestamp}")

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
