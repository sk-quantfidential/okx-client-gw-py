# PR: Epic OKX-0003 - Clean Architecture Refactoring

**Branch:** `refactor/epic-OKX-0003-clean-architecture`
**Target:** `main`
**Epic:** OKX-0003 (Milestone 6)
**Version:** v0.3.1

## Summary

Refactors all three samples in `samples/` to align with the clean architecture layered
structure used in `src/okx_client_gw/`. This ensures consistency, maintainability, and
proper separation of concerns across the codebase.

## What Changed

### Market Maker (`okx_market_maker/`)

Complete restructuring from flat module layout to layered clean architecture:

| Layer | Contents |
|-------|----------|
| `domain/models/` | StrategyOrder, AmendRequest, Quote, StrategyDecision |
| `domain/services/` | RiskCalculator |
| `domain/strategies/` | BaseStrategy, GridStrategy, InventorySkewStrategy, VolatilityStrategy |
| `domain/enums.py` | OrderState enum (extracted from strategy_order) |
| `ports/` | StrategyProtocol interface |
| `application/context/` | MarketContext state container |
| `application/services/` | OrderHandler, HealthChecker |
| `core/config/` | Settings (Pydantic), params.yaml |
| `core/utils/` | ID generator, instrument utilities |
| `presentation/` | CLI entry point and MarketMaker orchestrator |

**Notable changes:**
- Renamed `SampleMMStrategy` to `GridStrategy` (with backwards-compatible alias)
- Extracted `OrderState` enum to dedicated `domain/enums.py`
- Extracted `Quote` and `StrategyDecision` from protocol to `domain/models/quote.py`
- Split main.py into thin wrapper + `presentation/cli.py`

### Multicurrency Margin Monitor (`okx_multicurrency_margin_monitor/`)

Converted from standalone scripts to clean architecture package:

| Layer | Contents |
|-------|----------|
| `domain/models/` | SpotHolding dataclass |
| `domain/services/` | MarginCalculator |
| `application/services/` | MonitorService |
| `core/` | Threshold constants (config.py) |
| `presentation/` | CLI entry point |

### Portfolio Margin Monitor (`okx_portfolio_margin_monitor/`)

Same structure as multicurrency monitor - converted to clean architecture package.

### Core Library Fix

- Added missing `OkxAuthenticationError` exception class to `src/okx_client_gw/core/exceptions.py`

## Architecture Diagram

```
samples/okx_market_maker/
├── domain/                          # Pure business logic (no dependencies)
│   ├── models/                      # Value objects and entities
│   ├── services/                    # Domain services
│   ├── strategies/                  # Strategy implementations
│   └── enums.py                     # Domain enumerations
├── ports/                           # Interface definitions
│   └── strategy.py                  # StrategyProtocol
├── adapters/                        # External integrations (placeholder)
├── application/                     # Orchestration layer
│   ├── context/                     # State containers
│   └── services/                    # Application services
├── core/                            # Infrastructure
│   ├── config/                      # Settings and parameters
│   └── utils/                       # Utilities
├── presentation/                    # Entry points
│   └── cli.py                       # CLI and orchestrator
└── tests/                           # Unit tests
```

## Dependency Rules

```
presentation/ → application/ → domain/
                    ↓              ↑
               adapters/ → ports/ ←┘
                    ↓
                 core/
```

- `domain/` depends on nothing (pure Python + Pydantic)
- `ports/` depends only on `domain/`
- `adapters/` depends on `ports/`, `domain/`, `core/`
- `application/` depends on `domain/`, `ports/`, `core/`
- `presentation/` depends on `application/`, `domain/`, `core/`
- `core/` depends on nothing (self-contained)

## Files Changed

### Market Maker (75 files total)

**Deleted (old structure):**
- `config/`, `context/`, `models/`, `risk/`, `services/`, `strategy/`, `utils/`

**Created (new structure):**
- `domain/`, `ports/`, `adapters/`, `application/`, `core/`, `presentation/`

### Margin Monitors

**Created for each:**
- `__init__.py`, `main.py`
- `domain/models/holdings.py`
- `domain/services/margin_calculator.py`
- `application/services/monitor_service.py`
- `core/config.py`
- `presentation/cli.py`
- `tests/__init__.py`

### Core Library

| File | Change |
|------|--------|
| `src/okx_client_gw/core/exceptions.py` | Added OkxAuthenticationError |

## Testing

- [x] All 30 market maker tests pass
- [x] All 128 core library tests pass
- [x] ruff check passes on all clean architecture files
- [x] No circular imports
- [ ] Entry points work:
  - `python -m samples.okx_market_maker.main --help`
  - `python -m samples.okx_multicurrency_margin_monitor.main --help`
  - `python -m samples.okx_portfolio_margin_monitor.main --help`

## Breaking Changes

**Import paths changed** for market maker sample:

```python
# Before
from samples.okx_market_maker.models.strategy_order import StrategyOrder
from samples.okx_market_maker.strategy.strategy_protocol import Quote

# After
from samples.okx_market_maker.domain.models.strategy_order import StrategyOrder
from samples.okx_market_maker.domain.models.quote import Quote
```

**Backwards compatibility:**
- `SampleMMStrategy` alias provided for `GridStrategy`

## Commits

1. `refactor(samples): align all samples with clean architecture structure` - Main refactoring
2. `fix(core): add missing OkxAuthenticationError exception class` - Exception fix

## Related Issues

- Epic OKX-0003: OKX Market Maker Framework (Milestone 6)
