# okx-client-gw-py

Async HTTP/WebSocket client gateway for OKX Exchange, built on `client-gw-core` for resilient HTTP/WebSocket patterns.

## Features

- **OkxHttpClient**: Extends generic `HttpClient` with OKX response parsing
- **OkxWsClient**: Extends generic `WsClient` for OKX WebSocket streaming
- **Rate Limiting**: Fixed delay rate limiting (20 req/sec for public endpoints)
- **Retry Logic**: Automatic retry with exponential backoff for 5xx errors
- **Clean Architecture**: Domain models, ports, adapters, following SOLID principles
- **Comprehensive Tests**: 112 unit tests, 16 integration tests, 7 BDD tests

## Status

**Epic OKX-0001: OKX Public Market Data Client** - Complete

| Milestone | Status | Description |
|-----------|--------|-------------|
| 1. Project Scaffold | ✅ Complete | Directory structure, config, exceptions |
| 2. Domain Models | ✅ Complete | Candle, Ticker, OrderBook, Trade, Instrument |
| 3. Port Interfaces | ✅ Complete | Protocol classes for dependency inversion |
| 4. HTTP Adapter | ✅ Complete | OkxHttpClient implementation |
| 5. HTTP Commands | ✅ Complete | GetCandlesCommand, GetTickerCommand, etc. |
| 6. HTTP Services | ✅ Complete | MarketDataService with pagination |
| 7. WebSocket Adapter | ✅ Complete | OkxWsClient implementation |
| 8. WebSocket Services | ✅ Complete | StreamingService, MultiChannelStreamingService |
| 9. Presentation Layer | ✅ Complete | CLI application with Typer + Rich |
| 10. Testing & Docs | ✅ Complete | Full test coverage, API documentation |

## Installation

```bash
# Install with dependencies
pip install -e .

# Install with dev dependencies (pytest, respx)
pip install -e ".[dev]"

# Install with CLI dependencies (typer, rich)
pip install -e ".[cli]"

# Install client-gw-core (required, from monorepo)
pip install -e ../client-gw-core-py
```

## Quick Start

### HTTP API

```python
import asyncio
from datetime import datetime
from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.application.services import MarketDataService, InstrumentService
from okx_client_gw.domain.enums import Bar, InstType

async def main():
    async with OkxHttpClient() as client:
        # Market Data Service
        market = MarketDataService(client)

        # Get ticker
        ticker = await market.get_ticker("BTC-USDT")
        print(f"BTC-USDT: {ticker.last} (bid: {ticker.bid_px}, ask: {ticker.ask_px})")

        # Get candles with pagination
        candles = await market.get_candles(
            inst_id="BTC-USDT",
            bar=Bar.H1,
            limit=100,
        )
        for candle in candles[:5]:
            print(f"{candle.timestamp}: O={candle.open} H={candle.high} L={candle.low} C={candle.close}")

        # Get order book
        orderbook = await market.get_orderbook("BTC-USDT", depth=20)
        print(f"Spread: {orderbook.spread} ({orderbook.spread_percent:.4f}%)")

        # Instrument Service
        instruments = InstrumentService(client)

        # Get all SPOT instruments
        spot_instruments = await instruments.get_instruments(InstType.SPOT)
        print(f"Found {len(spot_instruments)} SPOT instruments")

asyncio.run(main())
```

### WebSocket Streaming

```python
import asyncio
from okx_client_gw.adapters.websocket import okx_ws_session
from okx_client_gw.application.services import StreamingService

async def main():
    async with okx_ws_session() as client:
        service = StreamingService(client)

        # Stream ticker updates
        print("Streaming BTC-USDT tickers...")
        async for ticker in service.stream_tickers("BTC-USDT"):
            print(f"Last: {ticker.last} Bid: {ticker.bid_px} Ask: {ticker.ask_px}")
            break  # Just one update for demo

asyncio.run(main())
```

### CLI

```bash
# Get current ticker
okx ticker BTC-USDT

# Get candlestick data
okx candles BTC-USDT --bar 1H --limit 50

# List instruments
okx instruments SPOT --filter BTC

# Get order book
okx orderbook ETH-USDT --depth 20

# Stream real-time data
okx stream BTC-USDT --channel ticker
okx stream BTC-USDT --channel trades
```

## Project Structure

```
okx-client-gw-py/
├── src/okx_client_gw/
│   ├── domain/              # Business entities (no external deps)
│   │   ├── enums.py         # InstType, Bar, ChannelType
│   │   └── models/          # Candle, Ticker, OrderBook, Trade, Instrument
│   ├── application/         # Use cases and commands
│   │   ├── commands/        # GetCandlesCommand, GetTickerCommand, etc.
│   │   └── services/        # MarketDataService, StreamingService
│   ├── ports/               # Protocol interfaces
│   ├── adapters/            # External implementations
│   │   ├── http/            # OkxHttpClient
│   │   └── websocket/       # OkxWsClient
│   ├── presentation/        # CLI application
│   └── core/                # Config, exceptions
├── tests/
│   ├── unit/                # 105 unit tests
│   ├── integration/         # 16 integration tests (live API)
│   └── features/            # 7 BDD tests
└── docs/
    └── architecture/        # OKX API functional decomposition
```

## Available Commands

### Market Data Commands

| Command | Description |
|---------|-------------|
| `GetTickerCommand` | Get ticker for single instrument |
| `GetTickersCommand` | Get tickers for all instruments of a type |
| `GetCandlesCommand` | Get candlestick data (up to 300 bars) |
| `GetHistoryCandlesCommand` | Get historical candlestick data |
| `GetOrderBookCommand` | Get order book (depth: 1, 5, 20, 50, 100, 400) |
| `GetTradesCommand` | Get recent trades |

### Instrument Commands

| Command | Description |
|---------|-------------|
| `GetInstrumentsCommand` | Get all instruments of a type |
| `GetInstrumentCommand` | Get single instrument details |

## Domain Models

### Enums

```python
from okx_client_gw.domain import InstType, Bar, ChannelType

# Instrument types
InstType.SPOT, InstType.SWAP, InstType.FUTURES, InstType.OPTION

# Candlestick granularities
Bar.M1, Bar.M5, Bar.M15, Bar.M30       # Minutes
Bar.H1, Bar.H2, Bar.H4                  # Hours
Bar.H6_UTC, Bar.H12_UTC, Bar.D1_UTC    # UTC-aligned
Bar.W1_UTC, Bar.MONTH1_UTC             # Weekly, Monthly

# WebSocket channels
ChannelType.TICKERS, ChannelType.TRADES
ChannelType.BOOKS5, ChannelType.BOOKS50, ChannelType.BOOKS
ChannelType.BBO_TBT  # Best bid/offer tick-by-tick
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

# Trade with side helpers
trade = Trade.from_okx_dict(data)
print(trade.is_buy, trade.is_sell, trade.px, trade.sz)
```

## Development

### Running Tests

```bash
# Unit tests only (fast, no network)
PYTHONPATH=src pytest tests/unit/ -v

# Integration tests (requires network, hits live OKX API)
PYTHONPATH=src pytest tests/integration/ -v

# BDD tests
PYTHONPATH=src pytest tests/features/ -v

# All tests with coverage
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
- [Public Data REST API](https://www.okx.com/docs-v5/en/#public-data-rest-api)
- [WebSocket Public Channel](https://www.okx.com/docs-v5/en/#websocket-api-public-channel)

See `docs/architecture/OKX_API_FUNCTIONAL_DECOMPOSITION.md` for detailed API mapping.

## Related Projects

- **client-gw-core-py**: Core HTTP/WebSocket client infrastructure
- **deribit-client-gw-py**: Reference Clean Architecture implementation
- **coinbase-client-gw-py**: HTTP client patterns

## License

MIT
