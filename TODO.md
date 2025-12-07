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

### Milestone 7: WebSocket Adapter 📋 PLANNED

**Branch:** `feature/epic-OKX-0001-milestone-7-websocket`
**Status:** Planned

**Tasks:**

- [ ] Create adapters/websocket/okx_ws_client.py
- [ ] Extend WsClient from client-gw-core
- [ ] Implement connection management
- [ ] Implement subscription handling
- [ ] Implement message parsing
- [ ] Add reconnection logic
- [ ] Add unit tests

---

### Milestone 8: WebSocket Services 📋 PLANNED

**Branch:** `feature/epic-OKX-0001-milestone-8-ws-services`
**Status:** Planned

**Tasks:**

- [ ] Create WebSocket stream services
- [ ] Implement ticker streaming
- [ ] Implement candle streaming
- [ ] Implement orderbook streaming
- [ ] Add message routing and parsing

---

### Milestone 9: Presentation Layer 📋 PLANNED

**Branch:** `feature/epic-OKX-0001-milestone-9-cli`
**Status:** Planned

**Tasks:**

- [ ] Create presentation/cli/app.py with Typer
- [ ] Add candle download command
- [ ] Add ticker display command
- [ ] Add WebSocket streaming command

---

### Milestone 10: Testing & Documentation 📋 PLANNED

**Branch:** `feature/epic-OKX-0001-milestone-10-docs`
**Status:** Planned

**Tasks:**

- [ ] Unit tests for all domain models
- [ ] Unit tests for commands with respx mocking
- [ ] Integration tests with VCR cassettes
- [ ] BDD feature tests
- [ ] Update README.md with usage examples

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

*Last Updated: 2025-12-06*
*Completed: Epic OKX-0001 Milestones 1-6 (HTTP client complete)*
*Next: Epic OKX-0001 Milestone 7 (WebSocket Adapter)*
