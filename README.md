# okx-client-gw-py

Async HTTP/WebSocket client gateway for OKX Exchange, built on `client-gw-core` for resilient HTTP/WebSocket patterns.

## Features

- **OkxHttpClient**: Extends generic `HttpClient` with OKX response parsing
- **OkxWsClient**: Extends generic `WsClient` for OKX WebSocket streaming (planned)
- **Rate Limiting**: Fixed delay rate limiting (20 req/sec for public endpoints)
- **Retry Logic**: Automatic retry with exponential backoff for 5xx errors
- **Clean Architecture**: Domain models, ports, adapters, following SOLID principles
- **Comprehensive Tests**: Unit tests with pytest, BDD tests planned

## Status

**Epic OKX-0001: OKX Public Market Data Client**

| Milestone | Status | Description |
|-----------|--------|-------------|
| 1. Project Scaffold | ✅ Complete | Directory structure, config, exceptions |
| 2. Domain Models | ✅ Complete | Candle, Ticker, OrderBook, Trade, Instrument |
| 3. Port Interfaces | 📋 Planned | Protocol classes for dependency inversion |
| 4. HTTP Adapter | 📋 Planned | OkxHttpClient implementation |
| 5. HTTP Commands | 📋 Planned | GetCandlesCommand, GetTickerCommand, etc. |
| 6. HTTP Services | 📋 Planned | MarketDataService with pagination |
| 7. WebSocket Adapter | 📋 Planned | OkxWsClient implementation |
| 8. WebSocket Services | 📋 Planned | Streaming services |
| 9. Presentation Layer | 📋 Planned | CLI application |
| 10. Testing & Docs | 📋 Planned | Full test coverage |

## Installation

```bash
# Install with dependencies
pip install -e .

# Install with dev dependencies (pytest, respx)
pip install -e ".[dev]"

# Install client-gw-core (required, from monorepo)
pip install -e ../client-gw-core-py
```

## Quick Start (Planned)

```python
import asyncio
from datetime import datetime
from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.application.services import MarketDataService

async def main():
    # Create client (no auth needed for public data)
    async with OkxHttpClient() as client:
        # Create market data service
        service = MarketDataService(client=client)

        # Get candle data
        candles = await service.get_candles(
            inst_id="BTC-USDT",
            bar="1H",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
        )

        for candle in candles:
            print(f"{candle.timestamp}: O={candle.open} H={candle.high} L={candle.low} C={candle.close}")

asyncio.run(main())
```

## Project Structure

```
okx-client-gw-py/
├── src/okx_client_gw/
│   ├── domain/              # Business entities (no external deps)
│   │   ├── enums.py         # InstType, Bar, ChannelType
│   │   └── models/          # Candle, Ticker, OrderBook, Trade, Instrument
│   ├── application/         # Use cases and commands
│   │   ├── commands/        # OkxCommand[T] implementations
│   │   └── services/        # MarketDataService, etc.
│   ├── ports/               # Protocol interfaces
│   ├── adapters/            # External implementations
│   │   ├── http/            # OkxHttpClient
│   │   └── websocket/       # OkxWsClient
│   ├── presentation/        # CLI and API endpoints
│   └── core/                # Config, exceptions
├── tests/
│   ├── unit/
│   │   ├── domain/          # 35 tests passing
│   │   ├── application/
│   │   └── adapters/
│   ├── integration/
│   └── features/            # BDD tests
└── docs/
    └── architecture/        # OKX API decomposition
```

## Domain Models

### Enums

```python
from okx_client_gw.domain import InstType, Bar, ChannelType

# Instrument types
InstType.SPOT, InstType.SWAP, InstType.FUTURES, InstType.OPTION

# Candlestick granularities
Bar.M1, Bar.M5, Bar.H1, Bar.D1_UTC

# WebSocket channels
ChannelType.TICKERS, ChannelType.TRADES, ChannelType.BOOKS5
```

### Models

```python
from okx_client_gw.domain import Candle, Ticker, OrderBook, Trade, Instrument

# Candle with computed properties
candle = Candle.from_okx_array(data)
print(candle.mid_price, candle.is_bullish, candle.range)

# Order book with spread calculation
book = OrderBook.from_okx_dict(data, inst_id="BTC-USDT")
print(book.spread, book.mid_price, book.imbalance)
```

## Development

### Running Tests

```bash
# Unit tests
PYTHONPATH=src pytest tests/unit/ -v

# Specific test file
PYTHONPATH=src pytest tests/unit/domain/test_candle.py -v

# With coverage
PYTHONPATH=src pytest tests/ --cov=okx_client_gw --cov-report=html
```

### Code Quality

```bash
# Lint check
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

## API Documentation

- [OKX v5 API Overview](https://www.okx.com/docs-v5/en/#overview)
- [Market Data REST API](https://www.okx.com/docs-v5/en/#order-book-trading-market-data)
- [WebSocket Public Channel](https://www.okx.com/docs-v5/en/#websocket-api-public-channel)

## Related Projects

- **client-gw-core-py**: Core HTTP/WebSocket client infrastructure
- **deribit-client-gw-py**: Reference Clean Architecture implementation
- **coinbase-client-gw-py**: HTTP client patterns

## License

MIT
