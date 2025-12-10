#!/usr/bin/env python3
"""
OKX Delta-Neutral Position Margin Monitor

Monitors margin health for spot BTC + short BTC-USDT perpetual positions.
Calculates real-time margin ratios, stress tests, and liquidation distances.

Usage:
    python okx_margin_monitor.py --api-key YOUR_KEY --api-secret YOUR_SECRET --passphrase YOUR_PASS

Requirements:
    pip install requests websockets python-dotenv --break-system-packages
"""

import argparse
import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "https://www.okx.com"
WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"

# Margin thresholds (OKX uses percentage format where 100% = liquidation)
MARGIN_WARNING_THRESHOLD = 300  # OKX sends warning at 300%
MARGIN_DANGER_THRESHOLD = 150   # You probably want to act here
MARGIN_LIQUIDATION_THRESHOLD = 100  # Forced liquidation triggered


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AccountBalance:
    """Account-level balance and margin data."""
    total_equity: float          # Total equity in USD
    adjusted_equity: float       # Equity after discount rates applied
    imr: float                   # Initial margin requirement
    mmr: float                   # Maintenance margin requirement
    margin_ratio: float          # adjEq / mmr (as percentage)
    available_balance: float     # Available for new positions
    notional_usd: float          # Total notional value

    @property
    def distance_to_warning(self) -> float:
        """Percentage points above warning threshold."""
        return self.margin_ratio - MARGIN_WARNING_THRESHOLD

    @property
    def distance_to_liquidation(self) -> float:
        """Percentage points above liquidation."""
        return self.margin_ratio - MARGIN_LIQUIDATION_THRESHOLD

    @property
    def health_status(self) -> str:
        if self.margin_ratio > MARGIN_WARNING_THRESHOLD:
            return "✅ HEALTHY"
        elif self.margin_ratio > MARGIN_DANGER_THRESHOLD:
            return "⚠️  WARNING"
        elif self.margin_ratio > MARGIN_LIQUIDATION_THRESHOLD:
            return "🔴 DANGER"
        else:
            return "💀 LIQUIDATION"


@dataclass
class Position:
    """Individual position data."""
    inst_id: str                 # e.g., "BTC-USDT-SWAP"
    pos_side: str                # "long", "short", or "net"
    size: float                  # Position size
    notional_usd: float          # USD notional value
    avg_price: float             # Average entry price
    mark_price: float            # Current mark price
    unrealised_pnl: float        # Unrealised P&L
    margin: float                # Margin allocated
    leverage: float              # Effective leverage
    liq_price: float | None   # Liquidation price (if applicable)
    mmr: float                   # Position MMR


@dataclass
class SpotHolding:
    """Spot asset holding."""
    currency: str
    balance: float
    equity: float                # Balance + unrealised P&L
    usd_value: float             # USD equivalent
    discount_rate: float         # Applied discount rate
    discounted_value: float      # Value after haircut


@dataclass
class DiscountRate:
    """Discount rate tier information."""
    currency: str
    tier: int
    min_amount: float
    max_amount: float
    discount_rate: float


# =============================================================================
# API Client
# =============================================================================

class OKXClient:
    """OKX REST API client with authentication."""

    def __init__(self, api_key: str, api_secret: str, passphrase: str, demo: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.demo = demo
        self.session = requests.Session()

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate API signature."""
        message = timestamp + method + path + body
        mac = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')

    def _request(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """Make authenticated API request."""
        timestamp = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        url = BASE_URL + path
        if params:
            query = '&'.join(f"{k}={v}" for k, v in params.items())
            path = f"{path}?{query}"
            url = f"{url}?{query}"

        body_str = json.dumps(body) if body else ""
        signature = self._sign(timestamp, method.upper(), path, body_str)

        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
        }

        if self.demo:
            headers['x-simulated-trading'] = '1'

        if method.upper() == 'GET':
            response = self.session.get(url, headers=headers)
        else:
            response = self.session.post(url, headers=headers, data=body_str)

        data = response.json()
        if data.get('code') != '0':
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')} (code: {data.get('code')})")

        return data.get('data', [])

    def _public_request(self, path: str, params: dict = None) -> dict:
        """Make unauthenticated public API request."""
        url = BASE_URL + path
        if params:
            query = '&'.join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"

        response = self.session.get(url)
        data = response.json()
        if data.get('code') != '0':
            raise Exception(f"API Error: {data.get('msg', 'Unknown error')}")

        return data.get('data', [])

    def get_account_balance(self) -> AccountBalance:
        """Fetch account-level balance and margin data."""
        data = self._request('GET', '/api/v5/account/balance')

        if not data:
            raise Exception("No account balance data returned")

        acct = data[0]

        return AccountBalance(
            total_equity=float(acct.get('totalEq', 0)),
            adjusted_equity=float(acct.get('adjEq', 0)),
            imr=float(acct.get('imr', 0)),
            mmr=float(acct.get('mmr', 0)),
            margin_ratio=float(acct.get('mgnRatio', 0)) * 100,  # Convert to percentage
            available_balance=float(acct.get('availBal', 0)),
            notional_usd=float(acct.get('notionalUsd', 0)),
        )

    def get_positions(self, inst_type: str = None) -> list[Position]:
        """Fetch all open positions."""
        params = {}
        if inst_type:
            params['instType'] = inst_type

        data = self._request('GET', '/api/v5/account/positions', params=params)

        positions = []
        for pos in data:
            if float(pos.get('pos', 0)) == 0:
                continue

            positions.append(Position(
                inst_id=pos.get('instId', ''),
                pos_side=pos.get('posSide', 'net'),
                size=float(pos.get('pos', 0)),
                notional_usd=float(pos.get('notionalUsd', 0)),
                avg_price=float(pos.get('avgPx', 0)),
                mark_price=float(pos.get('markPx', 0)),
                unrealised_pnl=float(pos.get('upl', 0)),
                margin=float(pos.get('margin', 0)),
                leverage=float(pos.get('lever', 1)),
                liq_price=float(pos['liqPx']) if pos.get('liqPx') else None,
                mmr=float(pos.get('mmr', 0)),
            ))

        return positions

    def get_account_config(self) -> dict:
        """Get account configuration including margin mode."""
        data = self._request('GET', '/api/v5/account/config')
        return data[0] if data else {}

    def get_discount_rates(self, currency: str = None) -> list[DiscountRate]:
        """Fetch discount rate tiers for collateral calculation."""
        params = {}
        if currency:
            params['ccy'] = currency

        data = self._public_request('/api/v5/public/discount-rate-interest-free-quota', params)

        rates = []
        for item in data:
            ccy = item.get('ccy', '')
            for i, detail in enumerate(item.get('discountInfo', [])):
                rates.append(DiscountRate(
                    currency=ccy,
                    tier=i + 1,
                    min_amount=float(detail.get('minAmt', 0)),
                    max_amount=float(detail.get('maxAmt', 0)) if detail.get('maxAmt') else float('inf'),
                    discount_rate=float(detail.get('discountRate', 1)),
                ))

        return rates

    def get_spot_balances(self) -> list[SpotHolding]:
        """Fetch spot/margin balances with discount calculations."""
        data = self._request('GET', '/api/v5/account/balance')

        if not data:
            return []

        holdings = []
        for detail in data[0].get('details', []):
            ccy = detail.get('ccy', '')
            equity = float(detail.get('eq', 0))

            if equity <= 0:
                continue

            # Get USD value and discount
            usd_value = float(detail.get('eqUsd', 0))
            disc_equity = float(detail.get('disEq', 0))

            # Calculate effective discount rate
            discount_rate = disc_equity / usd_value if usd_value > 0 else 1.0

            holdings.append(SpotHolding(
                currency=ccy,
                balance=float(detail.get('availBal', 0)),
                equity=equity,
                usd_value=usd_value,
                discount_rate=discount_rate,
                discounted_value=disc_equity,
            ))

        return holdings

    def get_mark_price(self, inst_id: str) -> float:
        """Get current mark price for an instrument."""
        data = self._public_request('/api/v5/public/mark-price', {'instId': inst_id})
        if data:
            return float(data[0].get('markPx', 0))
        return 0.0

    def get_index_price(self, inst_id: str) -> float:
        """Get current index price."""
        # Extract base currency for index lookup
        data = self._public_request('/api/v5/market/index-tickers', {'instId': inst_id})
        if data:
            return float(data[0].get('idxPx', 0))
        return 0.0


# =============================================================================
# Margin Calculator
# =============================================================================

class MarginCalculator:
    """Calculates margin metrics and stress scenarios."""

    def __init__(self, client: OKXClient):
        self.client = client

    def calculate_stress_scenario(
        self,
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
        btc_spot = next((h for h in spot_holdings if h.currency == 'BTC'), None)
        btc_spot_value = btc_spot.discounted_value if btc_spot else 0

        # Find BTC-USDT perp position
        btc_perp = next((p for p in positions if 'BTC-USDT' in p.inst_id and 'SWAP' in p.inst_id), None)

        if not btc_spot and not btc_perp:
            return {"error": "No BTC positions found"}

        # Calculate changes
        # Spot: Value changes proportionally (with discount rate)
        btc_discount = btc_spot.discount_rate if btc_spot else 0.97
        spot_value_change = btc_spot_value * price_change_pct

        # Perp: Short position profits when price drops
        # For short: PnL = -size * (new_price - entry_price) = -size * entry * price_change_pct
        perp_pnl_change = 0
        if btc_perp and btc_perp.size < 0:  # Short position
            # Notional * -price_change (short profits on drops)
            perp_pnl_change = btc_perp.notional_usd * (-price_change_pct)
        elif btc_perp and btc_perp.size > 0:  # Long position
            perp_pnl_change = btc_perp.notional_usd * price_change_pct

        # USDT PnL gets 100% credit (no discount)
        # BTC spot change already includes discount

        # Net effect on adjusted equity
        net_adj_eq_change = spot_value_change + perp_pnl_change

        # Project new margin ratio
        # Note: MMR may also change slightly, but for stress testing we keep it constant
        new_adj_eq = balance.adjusted_equity + net_adj_eq_change
        new_margin_ratio = (new_adj_eq / balance.mmr * 100) if balance.mmr > 0 else float('inf')

        return {
            "price_change_pct": price_change_pct * 100,
            "current_adj_eq": balance.adjusted_equity,
            "spot_value_change": spot_value_change,
            "perp_pnl_change": perp_pnl_change,
            "net_change": net_adj_eq_change,
            "projected_adj_eq": new_adj_eq,
            "current_margin_ratio": balance.margin_ratio,
            "projected_margin_ratio": new_margin_ratio,
            "above_liquidation": new_margin_ratio > MARGIN_LIQUIDATION_THRESHOLD,
            "above_warning": new_margin_ratio > MARGIN_WARNING_THRESHOLD,
        }

    def find_liquidation_price(
        self,
        balance: AccountBalance,
        spot_holdings: list[SpotHolding],
        positions: list[Position],
        current_btc_price: float,
    ) -> dict:
        """
        Find the BTC price at which liquidation would occur.
        Uses binary search to find the price where margin_ratio = 100%.
        """
        btc_spot = next((h for h in spot_holdings if h.currency == 'BTC'), None)
        btc_perp = next((p for p in positions if 'BTC-USDT' in p.inst_id and 'SWAP' in p.inst_id), None)

        if not btc_spot or not btc_perp:
            return {"error": "Need both spot and perp positions"}

        # Binary search for liquidation price
        low_pct, high_pct = -0.99, 2.0  # -99% to +200%

        for _ in range(50):  # 50 iterations for precision
            mid_pct = (low_pct + high_pct) / 2
            result = self.calculate_stress_scenario(balance, spot_holdings, positions, mid_pct)

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
# Monitor Display
# =============================================================================

class MarginMonitor:
    """Main monitoring class with formatted output."""

    def __init__(self, client: OKXClient):
        self.client = client
        self.calculator = MarginCalculator(client)

    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print('='*60)

    def print_section(self, text: str):
        """Print a section header."""
        print(f"\n  --- {text} ---")

    def run_full_report(self):
        """Generate comprehensive margin report."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.print_header(f"OKX MARGIN MONITOR - {timestamp}")

        # Account configuration
        config = self.client.get_account_config()
        acct_mode = config.get('acctLv', 'unknown')
        mode_names = {'1': 'Simple', '2': 'Single-currency', '3': 'Multi-currency', '4': 'Portfolio'}
        print(f"\n  Account Mode: {mode_names.get(acct_mode, acct_mode)}")

        # Fetch all data
        balance = self.client.get_account_balance()
        positions = self.client.get_positions()
        spot_holdings = self.client.get_spot_balances()

        # Account Summary
        self.print_section("ACCOUNT SUMMARY")
        print(f"  Status:              {balance.health_status}")
        print(f"  Margin Ratio:        {balance.margin_ratio:.2f}%")
        print(f"  Distance to Warning: {balance.distance_to_warning:+.2f}%")
        print(f"  Distance to Liq:     {balance.distance_to_liquidation:+.2f}%")
        print()
        print(f"  Adjusted Equity:     ${balance.adjusted_equity:,.2f}")
        print(f"  Total Equity:        ${balance.total_equity:,.2f}")
        print(f"  Initial Margin:      ${balance.imr:,.2f}")
        print(f"  Maintenance Margin:  ${balance.mmr:,.2f}")

        # Spot Holdings
        self.print_section("SPOT HOLDINGS (Collateral)")
        if spot_holdings:
            print(f"  {'Currency':<8} {'Balance':>12} {'USD Value':>14} {'Discount':>10} {'After Haircut':>14}")
            print(f"  {'-'*8} {'-'*12} {'-'*14} {'-'*10} {'-'*14}")
            for h in spot_holdings:
                print(f"  {h.currency:<8} {h.equity:>12.6f} ${h.usd_value:>13,.2f} {h.discount_rate*100:>9.2f}% ${h.discounted_value:>13,.2f}")
        else:
            print("  No spot holdings")

        # Derivative Positions
        self.print_section("DERIVATIVE POSITIONS")
        if positions:
            for p in positions:
                direction = "SHORT" if p.size < 0 else "LONG"
                print(f"\n  {p.inst_id} ({direction})")
                print(f"    Size:           {abs(p.size):.4f}")
                print(f"    Notional:       ${p.notional_usd:,.2f}")
                print(f"    Entry Price:    ${p.avg_price:,.2f}")
                print(f"    Mark Price:     ${p.mark_price:,.2f}")
                print(f"    Unrealised PnL: ${p.unrealised_pnl:+,.2f}")
                print(f"    Leverage:       {p.leverage:.1f}x")
                if p.liq_price:
                    print(f"    Liq Price:      ${p.liq_price:,.2f}")
        else:
            print("  No derivative positions")

        # Stress Testing
        self.print_section("STRESS TEST SCENARIOS")

        scenarios = [-0.10, -0.20, -0.30, -0.40, -0.50, 0.20, 0.50]

        print(f"  {'Price Δ':>10} {'Spot Δ':>12} {'Perp PnL Δ':>12} {'Net Δ':>12} {'New Margin':>12} {'Status':>10}")
        print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")

        for pct in scenarios:
            result = self.calculator.calculate_stress_scenario(balance, spot_holdings, positions, pct)
            if "error" in result:
                continue

            status = "✅" if result["above_warning"] else ("⚠️" if result["above_liquidation"] else "💀")

            print(f"  {pct*100:>+9.0f}% ${result['spot_value_change']:>+11,.0f} ${result['perp_pnl_change']:>+11,.0f} ${result['net_change']:>+11,.0f} {result['projected_margin_ratio']:>11.1f}% {status:>10}")

        # Find liquidation price
        btc_perp = next((p for p in positions if 'BTC-USDT' in p.inst_id and 'SWAP' in p.inst_id), None)
        if btc_perp:
            current_price = btc_perp.mark_price
            liq_result = self.calculator.find_liquidation_price(
                balance, spot_holdings, positions, current_price
            )

            if "error" not in liq_result:
                self.print_section("LIQUIDATION ANALYSIS")
                print(f"  Current BTC Price:    ${liq_result['current_price']:,.2f}")
                print(f"  Liquidation Price:    ${liq_result['liquidation_price']:,.2f}")
                print(f"  Required Drop:        {liq_result['price_drop_pct']:.1f}%")
                print(f"  Buffer:               ${liq_result['price_drop_usd']:,.2f}")

        # Discount Rate Info
        self.print_section("BTC DISCOUNT RATE TIERS")
        try:
            btc_rates = self.client.get_discount_rates('BTC')
            print(f"  {'Tier':>4} {'Min Amount':>14} {'Max Amount':>14} {'Discount Rate':>14}")
            print(f"  {'-'*4} {'-'*14} {'-'*14} {'-'*14}")
            for r in btc_rates[:5]:  # First 5 tiers
                max_str = f"{r.max_amount:,.2f}" if r.max_amount != float('inf') else "∞"
                print(f"  {r.tier:>4} {r.min_amount:>14,.2f} {max_str:>14} {r.discount_rate*100:>13.2f}%")
        except Exception as e:
            print(f"  Could not fetch discount rates: {e}")

        print("\n" + "="*60 + "\n")


# =============================================================================
# WebSocket Monitor (Real-time)
# =============================================================================

async def run_websocket_monitor(client: OKXClient):
    """
    Real-time WebSocket monitoring for margin updates.
    
    Note: This requires the 'websockets' package:
        pip install websockets --break-system-packages
    """
    import websockets

    timestamp = str(int(time.time()))
    sign_str = timestamp + 'GET' + '/users/self/verify'
    signature = base64.b64encode(
        hmac.new(
            client.api_secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).digest()
    ).decode()

    login_msg = {
        "op": "login",
        "args": [{
            "apiKey": client.api_key,
            "passphrase": client.passphrase,
            "timestamp": timestamp,
            "sign": signature
        }]
    }

    subscribe_msg = {
        "op": "subscribe",
        "args": [
            {"channel": "account"},
            {"channel": "positions", "instType": "SWAP"},
        ]
    }

    async with websockets.connect(WS_PRIVATE_URL) as ws:
        # Login
        await ws.send(json.dumps(login_msg))
        response = await ws.recv()
        print(f"Login response: {response}")

        # Subscribe
        await ws.send(json.dumps(subscribe_msg))
        response = await ws.recv()
        print(f"Subscribe response: {response}")

        # Monitor loop
        print("\n🔴 LIVE MONITORING - Press Ctrl+C to stop\n")

        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)

                if data.get('arg', {}).get('channel') == 'account':
                    # Account update
                    for acct in data.get('data', []):
                        adj_eq = float(acct.get('adjEq', 0))
                        mgn_ratio = float(acct.get('mgnRatio', 0)) * 100
                        mmr = float(acct.get('mmr', 0))

                        status = "✅" if mgn_ratio > 300 else ("⚠️" if mgn_ratio > 100 else "💀")
                        timestamp = datetime.now().strftime('%H:%M:%S')

                        print(f"[{timestamp}] {status} Margin: {mgn_ratio:.1f}% | AdjEq: ${adj_eq:,.0f} | MMR: ${mmr:,.0f}")

                elif data.get('arg', {}).get('channel') == 'positions':
                    # Position update
                    for pos in data.get('data', []):
                        inst_id = pos.get('instId', '')
                        upl = float(pos.get('upl', 0))
                        mark_px = float(pos.get('markPx', 0))

                        if 'BTC' in inst_id:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            print(f"[{timestamp}] 📊 {inst_id} Mark: ${mark_px:,.0f} | UPL: ${upl:+,.0f}")

            except Exception as e:
                print(f"WebSocket error: {e}")
                break


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='OKX Delta-Neutral Position Margin Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full report
  python okx_margin_monitor.py --api-key XXX --api-secret YYY --passphrase ZZZ

  # Run in demo mode
  python okx_margin_monitor.py --api-key XXX --api-secret YYY --passphrase ZZZ --demo

  # Real-time WebSocket monitoring
  python okx_margin_monitor.py --api-key XXX --api-secret YYY --passphrase ZZZ --live

Environment variables can also be used:
  OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE
        """
    )

    parser.add_argument('--api-key', help='OKX API key (or set OKX_API_KEY env var)')
    parser.add_argument('--api-secret', help='OKX API secret (or set OKX_API_SECRET env var)')
    parser.add_argument('--passphrase', help='OKX API passphrase (or set OKX_PASSPHRASE env var)')
    parser.add_argument('--demo', action='store_true', help='Use demo trading environment')
    parser.add_argument('--live', action='store_true', help='Enable real-time WebSocket monitoring')
    parser.add_argument('--loop', type=int, default=0, help='Refresh interval in seconds (0 = run once)')

    args = parser.parse_args()

    # Get credentials from args or environment
    import os
    api_key = args.api_key or os.environ.get('OKX_API_KEY')
    api_secret = args.api_secret or os.environ.get('OKX_API_SECRET')
    passphrase = args.passphrase or os.environ.get('OKX_PASSPHRASE')

    if not all([api_key, api_secret, passphrase]):
        parser.error("API credentials required. Use --api-key, --api-secret, --passphrase or set environment variables.")

    # Create client
    client = OKXClient(api_key, api_secret, passphrase, demo=args.demo)

    if args.live:
        # WebSocket monitoring
        import asyncio
        try:
            asyncio.run(run_websocket_monitor(client))
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    else:
        # REST API report
        monitor = MarginMonitor(client)

        try:
            while True:
                monitor.run_full_report()

                if args.loop <= 0:
                    break

                print(f"Refreshing in {args.loop} seconds... (Ctrl+C to stop)")
                time.sleep(args.loop)

        except KeyboardInterrupt:
            print("\nMonitoring stopped.")


if __name__ == '__main__':
    main()
