"""OKX Multi-Currency Margin Monitor - Main Entry Point.

Thin wrapper that delegates to the presentation layer CLI.

Usage:
    python -m samples.okx_multicurrency_margin_monitor.main --demo
    python -m samples.okx_multicurrency_margin_monitor.main --loop 30
"""

from samples.okx_multicurrency_margin_monitor.presentation.cli import main, run_cli

__all__ = ["main", "run_cli"]

if __name__ == "__main__":
    main()
