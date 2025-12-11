"""OKX Market Maker - Main Entry Point.

Thin wrapper that delegates to the presentation layer CLI.

Usage:
    python -m samples.okx_market_maker.main --inst-id BTC-USDT --demo
    python -m samples.okx_market_maker.main --config custom_params.yaml

Environment variables:
    OKX_API_KEY: API key
    OKX_SECRET_KEY: Secret key
    OKX_PASSPHRASE: Passphrase
    MM_*: Configuration overrides (e.g., MM_INST_ID, MM_STEP_PCT)
"""

from samples.okx_market_maker.presentation.cli import MarketMaker, run_cli

# Re-export for backwards compatibility
__all__ = ["MarketMaker", "main", "run_cli"]


def main() -> None:
    """Main entry point - delegates to presentation layer."""
    run_cli()


if __name__ == "__main__":
    main()
