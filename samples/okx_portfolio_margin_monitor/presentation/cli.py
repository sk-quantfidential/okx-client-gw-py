"""CLI entry point for portfolio margin monitor.

Usage:
    python -m samples.okx_portfolio_margin_monitor.main --demo
    python -m samples.okx_portfolio_margin_monitor.main --loop 30
"""

from __future__ import annotations

import argparse
import asyncio

from okx_client_gw import OkxConfig
from okx_client_gw.core.auth import OkxCredentials
from samples.okx_portfolio_margin_monitor.application.services.monitor_service import (
    MonitorService,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OKX Delta-Neutral Position Margin Monitor (Portfolio Gateway Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full report (credentials from environment)
  python -m samples.okx_portfolio_margin_monitor.main

  # Run in demo mode
  python -m samples.okx_portfolio_margin_monitor.main --demo

  # Loop with refresh interval
  python -m samples.okx_portfolio_margin_monitor.main --loop 30

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

    return parser.parse_args()


def run_cli() -> None:
    """CLI entry point for portfolio margin monitor."""
    args = parse_args()

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

    # Create monitor service
    monitor = MonitorService(config, credentials)

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


def main() -> None:
    """Main entry point - delegates to CLI."""
    run_cli()


if __name__ == "__main__":
    main()
