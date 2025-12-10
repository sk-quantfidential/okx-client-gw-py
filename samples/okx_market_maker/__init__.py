"""OKX Market Maker Sample.

A production-quality market maker sample using Clean Architecture patterns
with dependency injection instead of global state.

Features:
- Pluggable strategy framework (grid, inventory skew, volatility)
- Real-time private WebSocket for orders/positions
- Graceful shutdown with order cancellation
- Structured JSON logging

Example:
    python -m samples.okx_market_maker.main --inst-id BTC-USDT --demo
"""

__version__ = "0.3.0"
