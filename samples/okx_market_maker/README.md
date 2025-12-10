# OKX Market Maker Sample

A production-quality market maker sample using Clean Architecture with dependency injection.

## Features

- **Pluggable Strategies**: Three built-in strategies with easy extensibility
  - `grid`: Basic symmetric grid around bid/ask
  - `inventory_skew`: Price skewing based on inventory position
  - `volatility`: Dynamic spreads based on market volatility

- **Real-time WebSocket**: Private WebSocket for orders/positions/account
- **Risk Management**: Position limits, P&L tracking, health monitoring
- **Graceful Shutdown**: Signal handling with automatic order cancellation
- **Clean Architecture**: Dependency injection, no global state

## Quick Start

```bash
# Set credentials
export OKX_API_KEY="your-api-key"
export OKX_SECRET_KEY="your-secret-key"
export OKX_PASSPHRASE="your-passphrase"

# Run in demo mode (recommended for testing)
python -m samples.okx_market_maker.main --inst-id BTC-USDT --demo

# Run with specific strategy
python -m samples.okx_market_maker.main --inst-id ETH-USDT --strategy inventory_skew --demo

# Run with custom config
python -m samples.okx_market_maker.main --config my_params.yaml
```

## Configuration

### Environment Variables

All settings can be overridden via environment variables with `MM_` prefix:

```bash
export MM_INST_ID="ETH-USDT"
export MM_STEP_PCT="0.002"
export MM_NUM_ORDERS_PER_SIDE="3"
export MM_USE_DEMO="true"
```

### YAML Configuration

Edit `core/config/params.yaml` or provide a custom config file:

```yaml
# Instrument settings
inst_id: "BTC-USDT"
trading_mode: "cash"
use_demo: true

# Strategy
strategy_type: "grid"  # grid, inventory_skew, or volatility
step_pct: "0.001"      # 0.1% between orders
num_orders_per_side: 5
single_order_size: "0.001"

# Risk limits
max_net_buy: "100.0"
max_net_sell: "100.0"
max_position_value_usd: "10000.0"

# Health check thresholds
orderbook_max_delay_sec: 5.0
account_max_delay_sec: 10.0

# Strategy-specific (inventory_skew)
skew_factor: "0.5"
max_skew_pct: "0.005"

# Strategy-specific (volatility)
volatility_lookback: 20
volatility_multiplier: "2.0"
min_spread_pct: "0.001"
max_spread_pct: "0.01"
```

## Architecture

Clean Architecture with layered structure:

```
samples/okx_market_maker/
├── main.py                          # Thin entry point
├── domain/                          # Pure business logic (no external deps)
│   ├── enums.py                     # OrderState enum
│   ├── models/
│   │   ├── strategy_order.py        # Order state machine
│   │   ├── amend_request.py         # Amendment request POD
│   │   └── quote.py                 # Quote and StrategyDecision
│   ├── services/
│   │   └── risk_calculator.py       # P&L and risk metrics
│   └── strategies/
│       ├── base_strategy.py         # Abstract base
│       ├── grid_strategy.py         # Grid strategy (formerly sample_mm_strategy)
│       ├── inventory_skew_strategy.py
│       └── volatility_strategy.py
├── ports/                           # Interface definitions
│   └── strategy.py                  # StrategyProtocol
├── adapters/                        # External integrations (placeholder)
├── application/                     # Use cases and orchestration
│   ├── context/
│   │   └── market_context.py        # Centralized state container
│   └── services/
│       ├── order_handler.py         # Order lifecycle management
│       └── health_checker.py        # Data freshness monitoring
├── core/                            # Infrastructure
│   ├── config/
│   │   ├── settings.py              # Pydantic Settings (YAML + env)
│   │   └── params.yaml              # Default parameters
│   └── utils/
│       ├── instrument_util.py       # Price/size rounding
│       └── id_generator.py          # Client order IDs
├── presentation/                    # CLI entry points
│   └── cli.py                       # MarketMaker orchestrator
└── tests/
    ├── test_context.py
    └── test_strategy.py
```

**Dependency rules**:
- `domain/` → depends on nothing (pure Python + Pydantic)
- `ports/` → depends only on domain/
- `adapters/` → implements ports/, uses domain/, core/
- `application/` → depends on domain/, ports/, core/
- `presentation/` → depends on application/, domain/, core/
- `core/` → depends on nothing (self-contained)

## Strategies

### Grid Strategy (`grid`)

Places symmetric orders at fixed percentage intervals from best bid/ask.

```
Best Ask: 50010
  Sell 3: 50040 (+0.3%)
  Sell 2: 50030 (+0.2%)
  Sell 1: 50020 (+0.1%)
  ─────────────────────
  Buy 1:  49990 (-0.1%)
  Buy 2:  49980 (-0.2%)
  Buy 3:  49970 (-0.3%)
Best Bid: 50000
```

Position-aware: Reduces orders on the side that would increase position.

### Inventory Skew Strategy (`inventory_skew`)

Shifts the mid price based on current position to encourage mean reversion.

- Long position → Lower prices (encourage sells)
- Short position → Higher prices (encourage buys)

### Volatility Strategy (`volatility`)

Dynamically adjusts spread based on recent price volatility.

- High volatility → Wider spreads (more protection)
- Low volatility → Tighter spreads (more competitive)

Includes volatility circuit breaker that halts trading in extreme conditions.

## Extending

### Custom Strategy

```python
from samples.okx_market_maker.domain.strategies.base_strategy import BaseStrategy
from samples.okx_market_maker.domain.models.quote import Quote
from samples.okx_market_maker.application.context.market_context import MarketContext

class MyStrategy(BaseStrategy):
    def compute_quotes(self, context: MarketContext) -> list[Quote]:
        mid = context.mid_price
        if mid is None:
            return []

        # Your logic here
        return [
            Quote(price=mid * Decimal("0.999"), size=Decimal("0.001"), side="buy"),
            Quote(price=mid * Decimal("1.001"), size=Decimal("0.001"), side="sell"),
        ]
```

## Safety Features

- **Demo Mode**: Always test with `--demo` flag first
- **Position Limits**: Configurable max net buy/sell
- **Stale Data Detection**: Halts on stale orderbook/account data
- **Graceful Shutdown**: Ctrl+C cancels all orders before exit
- **Emergency Stop**: Automatic halt after consecutive health check failures

## Requirements

- Python 3.11+
- `okx-client-gw` library (parent package)
- `pydantic-settings` for configuration
- `pyyaml` for YAML config support
