# Market Maker Adaptation Specification

## Overview

This document specifies how the `okx-sample-market-maker` can be adapted to use
`okx-client-gw-py` as its underlying infrastructure, replacing direct `python-okx`
SDK calls with our clean architecture client gateway.

## Current Architecture (okx-sample-market-maker)

The existing market maker has the following components:

### Service Layer

| Service | Description | Dependencies |
|---------|-------------|--------------|
| `WssMarketDataService` | WebSocket orderbook streaming | `python-okx` WebSocket |
| `RESTMarketDataService` | REST API for instruments, tickers | `python-okx` REST |
| `WssOrderManagementService` | WebSocket order updates | `python-okx` WebSocket |
| `WssPositionManagementService` | WebSocket account/position updates | `python-okx` WebSocket |

### Data Models

| Model | Location | Description |
|-------|----------|-------------|
| `Instrument` | `market_data_service/model/` | Trading pair specifications |
| `OrderBook` | `market_data_service/model/` | Order book with checksum validation |
| `Tickers` | `market_data_service/model/` | Market ticker data |
| `MarkPx` | `market_data_service/model/` | Mark price data |
| `Order` | `order_management_service/model/` | Order state and details |
| `OrderRequest` | `order_management_service/model/` | Place/Amend/Cancel requests |
| `Account` | `position_management_service/model/` | Account balance info |
| `Positions` | `position_management_service/model/` | Open positions |
| `BalanceAndPosition` | `position_management_service/model/` | Combined balance/position snapshot |

### Strategy Layer

| Component | Description |
|-----------|-------------|
| `BaseStrategy` | Abstract base class with order management, health checks |
| `SampleMM` | Concrete market making strategy implementation |
| `StrategyOrder` | Internal order tracking with lifecycle states |
| `StrategyMeasurement` | Performance metrics and risk tracking |
| `RiskCalculator` | Risk snapshot generation |
| `ParamsLoader` | Dynamic parameter loading from YAML |

### Global State Containers

The current implementation uses module-level global containers:
- `order_books` - Order book cache
- `orders_container` - Live orders cache
- `account_container` - Account balance cache
- `positions_container` - Positions cache
- `tickers_container` - Ticker cache
- `mark_px_container` - Mark price cache

---

## Proposed Adaptation Architecture

### Design Principles

1. **Replace global containers** with dependency-injected services
2. **Use domain models** from `okx-client-gw-py` instead of duplicating
3. **Leverage existing services** for REST operations
4. **Extend WebSocket support** for private channels (account, orders, positions)
5. **Maintain strategy abstraction** for flexibility

### Component Mapping

| Original | Adapted | Notes |
|----------|---------|-------|
| `WssMarketDataService` | `StreamingService` | Already implemented in okx-client-gw-py |
| `RESTMarketDataService` | `MarketDataService`, `InstrumentService` | Already implemented |
| `WssOrderManagementService` | `PrivateStreamingService` (NEW) | Needs implementation |
| `WssPositionManagementService` | `PrivateStreamingService` (NEW) | Needs implementation |
| `TradeAPI` | `TradeService` | Already implemented |
| `AccountAPI` | `AccountService` | Already implemented |

### New Components Required

#### 1. Private WebSocket Client

```python
# ports/ws_private_client.py
class OkxPrivateWsClientProtocol(Protocol):
    """Protocol for authenticated WebSocket operations."""

    async def connect(self) -> None: ...
    async def login(self) -> bool: ...
    async def subscribe_account(self) -> None: ...
    async def subscribe_positions(self, inst_type: InstType | None = None) -> None: ...
    async def subscribe_orders(self, inst_type: InstType | None = None) -> None: ...

    def on_account_update(self, callback: Callable[[AccountBalance], None]) -> None: ...
    def on_position_update(self, callback: Callable[[list[Position]], None]) -> None: ...
    def on_order_update(self, callback: Callable[[Order], None]) -> None: ...
```

#### 2. Private Streaming Service

```python
# application/services/private_streaming_service.py
class PrivateStreamingService:
    """Service for private WebSocket channel subscriptions."""

    def __init__(
        self,
        ws_client: OkxPrivateWsClientProtocol,
        credentials: OkxCredentials,
    ) -> None: ...

    async def stream_account(self) -> AsyncIterator[AccountBalance]: ...
    async def stream_positions(self, inst_type: InstType | None = None) -> AsyncIterator[list[Position]]: ...
    async def stream_orders(self, inst_type: InstType | None = None) -> AsyncIterator[Order]: ...
```

#### 3. Market Maker Context

Replace global containers with a context object:

```python
# samples/market_maker/context.py
@dataclass
class MarketMakerContext:
    """Holds all market data and account state for market making."""

    # Market data (public)
    orderbook: OrderBook | None = None
    ticker: Ticker | None = None
    instrument: Instrument | None = None

    # Account data (private)
    balance: AccountBalance | None = None
    positions: list[Position] = field(default_factory=list)

    # Order tracking
    live_orders: dict[str, Order] = field(default_factory=dict)
    strategy_orders: dict[str, StrategyOrder] = field(default_factory=dict)

    # Timestamps for staleness detection
    orderbook_ts: datetime | None = None
    balance_ts: datetime | None = None

    def is_data_fresh(self, max_delay_sec: float = 5.0) -> bool:
        """Check if all data is sufficiently fresh."""
        now = datetime.now(UTC)
        if not self.orderbook_ts or (now - self.orderbook_ts).total_seconds() > max_delay_sec:
            return False
        if not self.balance_ts or (now - self.balance_ts).total_seconds() > max_delay_sec:
            return False
        return True
```

### Adapted Strategy Base Class

```python
# samples/market_maker/base_strategy.py
class BaseStrategy(ABC):
    """Abstract base strategy using okx-client-gw services."""

    def __init__(
        self,
        credentials: OkxCredentials,
        config: OkxConfig,
        inst_id: str,
    ) -> None:
        self.credentials = credentials
        self.config = config
        self.inst_id = inst_id
        self.context = MarketMakerContext()
        self._strategy_orders: dict[str, StrategyOrder] = {}

    @abstractmethod
    def order_operation_decision(
        self,
    ) -> tuple[list[OrderRequest], list[AmendRequest], list[CancelRequest]]:
        """Strategy must implement order decision logic."""
        pass

    async def run(self) -> None:
        """Main event loop."""
        async with OkxHttpClient(config=self.config, credentials=self.credentials) as http_client:
            # Initialize services
            account_service = AccountService(http_client)
            trade_service = TradeService(http_client)
            instrument_service = InstrumentService(http_client)

            # Get instrument info
            inst_type = self._infer_inst_type(self.inst_id)
            self.context.instrument = await instrument_service.get_instrument(
                inst_type, self.inst_id
            )

            # Start WebSocket streams
            async with self._create_ws_clients() as (public_ws, private_ws):
                streaming_service = StreamingService(public_ws)
                private_streaming = PrivateStreamingService(private_ws, self.credentials)

                # Run concurrent tasks
                await asyncio.gather(
                    self._process_orderbook(streaming_service),
                    self._process_account(private_streaming),
                    self._process_orders(private_streaming),
                    self._strategy_loop(trade_service),
                )

    async def _strategy_loop(self, trade_service: TradeService) -> None:
        """Main strategy execution loop."""
        while True:
            try:
                if not self.context.is_data_fresh():
                    await asyncio.sleep(1)
                    continue

                # Get order decisions from strategy
                place_orders, amend_orders, cancel_orders = self.order_operation_decision()

                # Execute orders
                await self._execute_orders(trade_service, place_orders, amend_orders, cancel_orders)

                await asyncio.sleep(1)  # Main loop delay

            except Exception as e:
                logging.exception(f"Strategy error: {e}")
                await self._cancel_all(trade_service)
                await asyncio.sleep(20)
```

---

## Implementation Phases

### Phase 1: Private WebSocket Support

**Goal**: Add authenticated WebSocket streaming for account/orders/positions

**Files to create**:
- `src/okx_client_gw/adapters/websocket/okx_private_ws_client.py`
- `src/okx_client_gw/application/services/private_streaming_service.py`

**Key features**:
- WebSocket login with HMAC signature
- Account channel subscription
- Positions channel subscription
- Orders channel subscription
- Automatic reconnection handling

### Phase 2: Market Maker Infrastructure

**Goal**: Create market maker framework using okx-client-gw

**Files to create**:
- `samples/market_maker/__init__.py`
- `samples/market_maker/context.py`
- `samples/market_maker/base_strategy.py`
- `samples/market_maker/strategy_order.py`
- `samples/market_maker/risk_calculator.py`

**Key features**:
- Context object replacing global containers
- Base strategy class with order management
- Strategy order lifecycle tracking
- Risk calculation utilities

### Phase 3: Sample Strategy Port

**Goal**: Port SampleMM strategy to new framework

**Files to create**:
- `samples/market_maker/sample_mm.py`
- `samples/market_maker/params_loader.py`

**Key features**:
- Quote generation logic
- Order sizing and pricing
- Dynamic parameter loading
- Risk limits enforcement

---

## API Mapping Reference

### REST API Endpoints

| Endpoint | okx-client-gw Command/Service | Status |
|----------|------------------------------|--------|
| `GET /api/v5/account/balance` | `AccountService.get_balance()` | ✅ Implemented |
| `GET /api/v5/account/positions` | `AccountService.get_positions()` | ✅ Implemented |
| `GET /api/v5/account/config` | `AccountService.get_config()` | ✅ Implemented |
| `GET /api/v5/public/instruments` | `InstrumentService.get_instruments()` | ✅ Implemented |
| `GET /api/v5/market/books` | `MarketDataService.get_orderbook()` | ✅ Implemented |
| `GET /api/v5/market/ticker` | `MarketDataService.get_ticker()` | ✅ Implemented |
| `POST /api/v5/trade/order` | `TradeService.place_order()` | ✅ Implemented |
| `POST /api/v5/trade/cancel-order` | `TradeService.cancel_order()` | ✅ Implemented |
| `POST /api/v5/trade/amend-order` | `TradeService.amend_order()` | ✅ Implemented |
| `POST /api/v5/trade/batch-orders` | `PlaceBatchOrdersCommand` | ❌ Not implemented |
| `POST /api/v5/trade/cancel-batch-orders` | `TradeService.cancel_batch_orders()` | ✅ Implemented |
| `POST /api/v5/trade/amend-batch-orders` | `AmendBatchOrdersCommand` | ❌ Not implemented |

### WebSocket Channels

| Channel | okx-client-gw Service | Status |
|---------|----------------------|--------|
| `books` (public) | `StreamingService.stream_orderbook()` | ✅ Implemented |
| `tickers` (public) | `StreamingService.stream_ticker()` | ✅ Implemented |
| `trades` (public) | `StreamingService.stream_trades()` | ✅ Implemented |
| `account` (private) | `PrivateStreamingService.stream_account()` | ❌ Not implemented |
| `positions` (private) | `PrivateStreamingService.stream_positions()` | ❌ Not implemented |
| `orders` (private) | `PrivateStreamingService.stream_orders()` | ❌ Not implemented |

---

## Risk Considerations

1. **Order Tracking**: The original market maker tracks orders via `StrategyOrder`
   with detailed lifecycle states. This should be preserved.

2. **Health Checks**: Order book checksum validation and staleness detection are critical for market making.

3. **Error Recovery**: Automatic cancel-all on errors prevents runaway positions.

4. **Rate Limits**: Batch operations should be used where possible to stay within rate limits.

5. **Concurrency**: Multiple async tasks need proper coordination to prevent race conditions.

---

## Dependencies

**Required additions to okx-client-gw-py**:
- Private WebSocket authentication
- Private channel subscriptions (account, positions, orders)
- Batch amend orders command

**Required for market maker sample**:
- PyYAML (for params loading)
- Rich (for terminal UI, optional)

---

## Success Criteria

1. ✅ Market maker runs using only okx-client-gw-py (no direct python-okx imports)
2. ✅ All WebSocket channels stream real-time updates
3. ✅ Order lifecycle tracking works correctly
4. ✅ Health checks detect stale data
5. ✅ Risk calculations match original implementation
6. ✅ Strategy can be paused/resumed gracefully
7. ✅ Comprehensive logging for debugging

---

## Timeline Estimate

| Phase | Scope | Complexity |
|-------|-------|------------|
| Phase 1 | Private WebSocket | Medium |
| Phase 2 | MM Infrastructure | Medium |
| Phase 3 | Strategy Port | Low |
| Testing | Integration tests | Medium |

**Note**: This is a complexity estimate, not a time estimate. Actual implementation
depends on available resources and priorities.
