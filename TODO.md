# TODO: OKX Client Gateway

> **Note**: This project tracks work related to the OKX Exchange API client implementation.

## Project Overview

Async Python client for OKX Exchange API, built on the generic `client-gw-core` library.

**Core Principles:**

- Async-first architecture (Python 3.13+)
- Built on `client-gw-core` generic HTTP/WebSocket clients
- Clean Architecture (domain/application/ports/adapters/presentation/core)
- Production-ready for market data streaming
- Comprehensive test coverage

---

## Epic OKX-0001: OKX Public Market Data Client

**Status:** In Progress
**Target:** v0.1.0
**Depends On:** client-gw-core-py

### Overview

Implement production-ready async client for OKX Exchange public market data using
Clean Architecture patterns from deribit-client-gw-py and HTTP patterns from
coinbase-client-gw-py.

**OKX API Reference:**

- REST Base: `https://www.okx.com`
- WebSocket Public: `wss://ws.okx.com:8443/ws/v5/public`
- Response Format: `{"code": "0", "msg": "", "data": [...]}`

---

### Milestone 1: Project Scaffold & Configuration ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-milestone-1-scaffold`
**Status:** ✅ Completed

**Completed:**

- [x] Update TODO-MASTER.md with Epic OKX-0001
- [x] Create Clean Architecture directory structure
- [x] Create pyproject.toml with dependencies
- [x] Create core/config.py with OkxConfig
- [x] Create core/exceptions.py with OkxApiError, OkxConnectionError
- [x] Create component TODO.md

---

### Milestone 2: Domain Models ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-milestone-2-domain`
**Status:** ✅ Completed

**Completed:**

- [x] Create domain/enums.py (InstType, Bar, ChannelType, TradeSide, OrderBookAction)
- [x] Create domain/models/instrument.py
- [x] Create domain/models/ticker.py
- [x] Create domain/models/candle.py
- [x] Create domain/models/trade.py
- [x] Create domain/models/orderbook.py
- [x] Add unit tests for domain models (35 tests passing)

---

### Milestone 3: Port Interfaces ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create ports/http_client.py (OkxHttpClientProtocol)
- [x] Create ports/ws_client.py (OkxWsClientProtocol)
- [x] Define response types

---

### Milestone 4: HTTP Adapter ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create adapters/http/okx_http_client.py
- [x] Extend HttpClient from client-gw-core
- [x] Implement OKX response parsing (code/msg/data)
- [x] Configure rate limiting (20 req/sec public)
- [x] Configure retry logic for 5xx errors

---

### Milestone 5: HTTP Commands ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create application/commands/base.py (OkxCommand[T])
- [x] Create GetInstrumentsCommand, GetInstrumentCommand
- [x] Create GetTickerCommand, GetTickersCommand
- [x] Create GetCandlesCommand, GetHistoryCandlesCommand
- [x] Create GetOrderBookCommand
- [x] Create GetTradesCommand

---

### Milestone 6: HTTP Services ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create application/services/market_service.py
- [x] Create application/services/instrument_service.py
- [x] Implement get_candles() with automatic pagination
- [x] Implement get_ticker(), get_tickers()
- [x] Implement get_orderbook()
- [x] Implement get_trades()
- [x] Implement stream_candles() async generator
- [x] Implement stream_history_candles() for older data

---

### Milestone 7: WebSocket Adapter ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create adapters/websocket/okx_ws_client.py
- [x] Extend WsClient from client-gw-core
- [x] Implement connection management (connect/disconnect)
- [x] Implement subscription handling (subscribe/unsubscribe)
- [x] Implement convenience methods (subscribe_tickers, subscribe_trades, etc.)
- [x] Add ping/pong keep-alive support
- [x] Add async context manager support (okx_ws_session)
- [x] Add unit tests (20 tests passing)

---

### Milestone 8: WebSocket Services ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create StreamingService for single-channel streaming
- [x] Create MultiChannelStreamingService for multi-instrument streaming
- [x] Implement ticker streaming (stream_tickers)
- [x] Implement trade streaming (stream_trades)
- [x] Implement candle streaming (stream_candles)
- [x] Implement orderbook streaming (stream_orderbook)
- [x] Implement BBO streaming (stream_bbo)
- [x] Add message routing and parsing with type hints
- [x] Add unit tests (28 tests passing)

---

### Milestone 9: Presentation Layer ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Create presentation/cli/app.py with Typer
- [x] Add `okx candles` command for candlestick data
- [x] Add `okx ticker` command for single instrument
- [x] Add `okx tickers` command for all instruments of a type
- [x] Add `okx instruments` command for listing available instruments
- [x] Add `okx orderbook` command for order book display
- [x] Add `okx stream` command for WebSocket streaming
- [x] Add CLI entry point in pyproject.toml

---

### Milestone 10: Testing & Documentation ✅ COMPLETED

**Branch:** `feature/epic-OKX-0001-public-market-data-client`
**Status:** ✅ Completed

**Completed:**

- [x] Unit tests for all domain models (35 tests)
- [x] Unit tests for commands with respx mocking (22 tests)
- [x] Unit tests for WebSocket adapter (20 tests)
- [x] Unit tests for streaming services (28 tests)
- [x] Integration tests against live OKX API (16 tests)
- [x] BDD feature tests (7 tests)
- [x] Update README.md with comprehensive usage examples

---

## Quick Reference

**Test Commands:**

```bash
# Unit tests
PYTHONPATH=src pytest tests/unit/ -v

# Integration tests
PYTHONPATH=src pytest tests/integration/ -v

# All tests with coverage
PYTHONPATH=src pytest tests/ --cov=okx_client_gw --cov-report=html

# Lint check
ruff check src/ tests/
```

**Import Pattern:**

```python
from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.application.services import MarketDataService

# Usage
async with OkxHttpClient() as client:
    service = MarketDataService(client=client)
    candles = await service.get_candles(
        inst_id="BTC-USDT",
        bar="1H",
        start_date=datetime(...),
        end_date=datetime(...),
    )
```

---

*Last Updated: 2025-12-07*
*Completed: Epic OKX-0001 Milestones 1-10 (Full HTTP/WebSocket implementation + CLI + Testing)*
*Status: Epic Complete - 128 tests passing (105 unit + 16 integration + 7 BDD)*
