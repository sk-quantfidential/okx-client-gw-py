# OKX API Functional Decomposition

## Summary of Service Segmentation and API Scopes

The OKX API is organized into distinct functional areas with clear authentication boundaries.
Unlike Deribit's OAuth-style scopes, OKX uses API key permissions (`read`, `trade`, `withdraw`)
combined with IP whitelisting for access control.

### Service Component Overview

1. **Market Data Service**: Uses Public REST endpoints and Public WebSocket channels.
   No authentication required. Rate limited by IP address.

2. **Account Management Service**: Uses Private REST endpoints requiring `read` permission.
   Monitors balances, positions, fees, and account configuration.

3. **Trade/OMS Gateway**: Uses Private REST endpoints and Private WebSocket channels
   requiring `trade` permission. Handles order placement, modification, and execution.

4. **Funding Service**: Uses Private REST endpoints requiring `withdraw` permission
   for deposits, withdrawals, and inter-account transfers.

5. **Sub-Account Management**: Uses Private REST endpoints with master account credentials.
   Manages sub-account creation, API keys, and fund transfers.

### OKX Authentication Model

**API Key Components:**
- `OK-ACCESS-KEY`: API key identifier
- `OK-ACCESS-SIGN`: Base64-encoded HMAC-SHA256 signature
- `OK-ACCESS-TIMESTAMP`: UTC timestamp in ISO format
- `OK-ACCESS-PASSPHRASE`: User-defined passphrase from API key creation

**Signature Generation:**
```
signature = Base64(HMAC-SHA256(timestamp + method + requestPath + body, secretKey))
```

**Permission Levels:**
- `read`: Read-only access to account information
- `trade`: Order placement and modification (includes `read`)
- `withdraw`: Deposit/withdrawal operations (includes `read` and `trade`)

---

## API Base URLs

| Environment | Type | URL |
|-------------|------|-----|
| Production | REST | `https://www.okx.com` |
| Production | WebSocket Public | `wss://ws.okx.com:8443/ws/v5/public` |
| Production | WebSocket Private | `wss://ws.okx.com:8443/ws/v5/private` |
| Demo | WebSocket Public | `wss://wspap.okx.com:8443/ws/v5/public` |
| Demo | WebSocket Private | `wss://wspap.okx.com:8443/ws/v5/private` |

**Demo Trading Header:** `x-simulated-trading: 1`

---

## Response Format

**Success Response:**
```json
{
  "code": "0",
  "msg": "",
  "data": [...]
}
```

**Error Response:**
```json
{
  "code": "50011",
  "msg": "Rate limit exceeded",
  "data": []
}
```

---

## 1. Market Data Service (Public API)

This component focuses on fetching public, real-time market data through non-authenticated
endpoints. Suitable for market monitoring, charting, and price feed applications.

### REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/market/tickers` | GET | All tickers for instrument type | 20/2s |
| `/api/v5/market/ticker` | GET | Single instrument ticker | 20/2s |
| `/api/v5/market/books` | GET | Order book (configurable depth) | 40/2s |
| `/api/v5/market/books-full` | GET | Full order book (400 levels) | 40/2s |
| `/api/v5/market/candles` | GET | Candlestick data (recent) | 40/2s |
| `/api/v5/market/history-candles` | GET | Historical candlestick data | 20/2s |
| `/api/v5/market/trades` | GET | Recent trades | 100/2s |
| `/api/v5/market/history-trades` | GET | Historical trades | 20/2s |
| `/api/v5/market/24-volume` | GET | 24h total trading volume | 2/2s |
| `/api/v5/market/option-trades` | GET | Options trades | 20/2s |

### Public Data Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/public/instruments` | GET | Available instruments | 20/2s |
| `/api/v5/public/funding-rate` | GET | Current funding rate | 20/2s |
| `/api/v5/public/funding-rate-history` | GET | Historical funding rates | 20/2s |
| `/api/v5/public/open-interest` | GET | Open interest data | 20/2s |
| `/api/v5/public/price-limit` | GET | Price limits | 20/2s |
| `/api/v5/public/mark-price` | GET | Mark price | 10/2s |
| `/api/v5/public/mark-price-kline` | GET | Mark price candles | 20/2s |
| `/api/v5/public/index-tickers` | GET | Index tickers | 20/2s |
| `/api/v5/public/index-kline` | GET | Index candles | 20/2s |
| `/api/v5/public/index-components` | GET | Index composition | 20/2s |
| `/api/v5/public/opt-summary` | GET | Options summary | 20/2s |
| `/api/v5/public/estimated-price` | GET | Estimated delivery price | 10/2s |
| `/api/v5/public/position-tiers` | GET | Position tiers | 10/2s |
| `/api/v5/public/interest-rate-loan-quota` | GET | Interest rates | 2/2s |
| `/api/v5/public/economic-calendar` | GET | Economic calendar | 5/2s |
| `/api/v5/public/system-time` | GET | Server time | 10/2s |

### Public WebSocket Channels

| Channel | Description | Subscription Format |
|---------|-------------|---------------------|
| `tickers` | Real-time ticker updates | `{"channel":"tickers","instId":"BTC-USDT"}` |
| `candle{bar}` | Candlestick updates | `{"channel":"candle1H","instId":"BTC-USDT"}` |
| `trades` | Trade executions | `{"channel":"trades","instId":"BTC-USDT"}` |
| `trades-all` | All trades (aggregate) | `{"channel":"trades-all","instId":"BTC-USDT"}` |
| `books` | Order book (400 levels) | `{"channel":"books","instId":"BTC-USDT"}` |
| `books5` | Order book (5 levels) | `{"channel":"books5","instId":"BTC-USDT"}` |
| `books50-l2-tbt` | Order book (50 levels, tick-by-tick) | `{"channel":"books50-l2-tbt","instId":"BTC-USDT"}` |
| `books-l2-tbt` | Order book (400 levels, tick-by-tick) | `{"channel":"books-l2-tbt","instId":"BTC-USDT"}` |
| `bbo-tbt` | Best bid/offer (tick-by-tick) | `{"channel":"bbo-tbt","instId":"BTC-USDT"}` |
| `instruments` | Instrument updates | `{"channel":"instruments","instType":"SPOT"}` |
| `open-interest` | Open interest updates | `{"channel":"open-interest","instId":"BTC-USDT-SWAP"}` |
| `funding-rate` | Funding rate updates | `{"channel":"funding-rate","instId":"BTC-USDT-SWAP"}` |
| `price-limit` | Price limit updates | `{"channel":"price-limit","instId":"BTC-USDT-SWAP"}` |
| `mark-price` | Mark price updates | `{"channel":"mark-price","instId":"BTC-USDT-SWAP"}` |
| `index-tickers` | Index ticker updates | `{"channel":"index-tickers","instId":"BTC-USD"}` |
| `opt-summary` | Options summary updates | `{"channel":"opt-summary","instFamily":"BTC-USD"}` |

---

## 2. Account Management Service (Private API - Read)

Requires authentication with `read` permission. Monitors account state, positions,
balances, and configuration settings.

### Account REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/account/balance` | GET | Trading account balance | 10/2s |
| `/api/v5/account/positions` | GET | Current positions | 10/2s |
| `/api/v5/account/positions-history` | GET | Historical positions | 10/sec |
| `/api/v5/account/account-risk` | GET | Account risk assessment | 10/2s |
| `/api/v5/account/config` | GET | Account configuration | 5/2s |
| `/api/v5/account/leverage-info` | GET | Leverage settings | 20/2s |
| `/api/v5/account/max-order-quantity` | GET | Max order quantity | 20/2s |
| `/api/v5/account/max-available-sz` | GET | Max available size | 20/2s |
| `/api/v5/account/max-loan` | GET | Max loan amount | 20/2s |
| `/api/v5/account/trade-fee` | GET | Trading fee rates | 5/2s |
| `/api/v5/account/interest-accrued` | GET | Accrued interest | 5/2s |
| `/api/v5/account/interest-rate` | GET | Interest rates | 5/2s |
| `/api/v5/account/greeks` | GET | Options Greeks | 10/2s |
| `/api/v5/account/bills/7d` | GET | 7-day billing | 6/sec |
| `/api/v5/account/bills/3m` | GET | 3-month billing | 6/sec |

### Account Configuration Endpoints (Requires `trade` permission)

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/account/position-mode` | POST | Set position mode | 5/2s |
| `/api/v5/account/set-leverage` | POST | Set leverage | 20/2s |
| `/api/v5/account/margin-balance` | POST | Adjust margin | 20/2s |
| `/api/v5/account/set-greeks` | POST | Set Greeks display | 5/2s |

### Private WebSocket Channels (Account)

| Channel | Description | Subscription Format |
|---------|-------------|---------------------|
| `account` | Balance and equity updates | `{"channel":"account"}` |
| `positions` | Position updates | `{"channel":"positions","instType":"SWAP"}` |
| `balance_and_position` | Combined updates | `{"channel":"balance_and_position"}` |
| `account-greeks` | Options Greeks updates | `{"channel":"account-greeks"}` |
| `liquidation-warning` | Liquidation risk alerts | `{"channel":"liquidation-warning","instType":"SWAP"}` |

---

## 3. Trade/OMS Gateway (Private API - Trade)

Requires authentication with `trade` permission. Handles order lifecycle management
including placement, modification, cancellation, and execution tracking.

### Order Management REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/trade/order` | POST | Place single order | 60/2s (per inst) |
| `/api/v5/trade/order-batch` | POST | Place multiple orders | 300/2s |
| `/api/v5/trade/cancel-order` | POST | Cancel single order | 60/2s (per inst) |
| `/api/v5/trade/cancel-batch-orders` | POST | Cancel multiple orders | 300/2s |
| `/api/v5/trade/amend-order` | POST | Modify single order | 60/2s (per inst) |
| `/api/v5/trade/amend-batch-orders` | POST | Modify multiple orders | 300/2s |
| `/api/v5/trade/close-position` | POST | Close position | 20/2s (per inst) |

### Order Query REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/trade/order` | GET | Get order details | 60/2s |
| `/api/v5/trade/orders-pending` | GET | Active/pending orders | 60/2s |
| `/api/v5/trade/orders-history` | GET | Order history (7 days) | 40/2s |
| `/api/v5/trade/orders-history-archive` | GET | Order history (3 months) | 20/2s |
| `/api/v5/trade/fills` | GET | Execution details (3 days) | 60/2s |
| `/api/v5/trade/fills-history` | GET | Execution history (3 months) | 10/2s |

### Algo Trading REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/trade/order-algo` | POST | Place algo order | 20/2s |
| `/api/v5/trade/cancel-algos` | POST | Cancel algo orders | 20/2s |
| `/api/v5/trade/amend-algos` | POST | Modify algo orders | 20/2s |
| `/api/v5/trade/orders-algo-pending` | GET | Active algo orders | 20/2s |
| `/api/v5/trade/orders-algo-history` | GET | Algo order history | 20/2s |
| `/api/v5/trade/orders-algo-details` | GET | Algo order details | 20/2s |

**Supported Algo Order Types:**
- Stop Loss / Take Profit (TP/SL): 100 per instrument max
- Trigger Orders: 500 pending max
- Trailing Stop: 50 max
- Iceberg Orders: 100 per instrument max
- TWAP: 20 max

### Private WebSocket Channels (Orders)

| Channel | Description | Subscription Format |
|---------|-------------|---------------------|
| `orders` | Order status updates | `{"channel":"orders","instType":"SPOT"}` |
| `fills` | Fill/execution updates | `{"channel":"fills"}` |
| `orders-algo` | Algo order updates | `{"channel":"orders-algo","instType":"SWAP"}` |

---

## 4. Funding Service (Private API - Withdraw)

Requires authentication with `withdraw` permission. Manages deposits, withdrawals,
and fund transfers between accounts.

### Funding REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/asset/currencies` | GET | Supported currencies | 6/sec |
| `/api/v5/asset/balance` | GET | Funding account balance | 6/sec |
| `/api/v5/asset/deposit-address` | GET | Deposit addresses | 6/sec |
| `/api/v5/asset/deposit-history` | GET | Deposit history | 6/sec |
| `/api/v5/asset/withdraw` | POST | Initiate withdrawal | 6/sec |
| `/api/v5/asset/cancel-withdrawal` | POST | Cancel withdrawal | 6/sec |
| `/api/v5/asset/withdrawal-history` | GET | Withdrawal history | 6/sec |
| `/api/v5/asset/transfer` | POST | Internal transfer | 2/sec |
| `/api/v5/asset/transfer-state` | GET | Transfer status | 10/2s |
| `/api/v5/asset/bills` | GET | Asset bills | 6/sec |
| `/api/v5/asset/deposit-withdraw-status` | GET | D/W system status | 6/sec |
| `/api/v5/account/asset-valuation` | GET | Total asset valuation | 5/2s |

### Currency Conversion Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/asset/convert/currencies` | GET | Convertible currencies | 6/sec |
| `/api/v5/asset/convert/currency-pair` | GET | Conversion pair info | 6/sec |
| `/api/v5/asset/convert/estimate-quote` | POST | Get conversion quote | 10/sec |
| `/api/v5/asset/convert/trade` | POST | Execute conversion | 10/sec |
| `/api/v5/asset/convert/history` | GET | Conversion history | 6/sec |

---

## 5. Sub-Account Management (Private API - Master Account)

Requires master account credentials. Manages sub-account creation, API keys,
and fund distribution.

### Sub-Account REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/account/sub-accounts` | GET | List sub-accounts | 2/2s |
| `/api/v5/account/sub-account/create` | POST | Create sub-account | 2/2s |
| `/api/v5/account/sub-account/create-apikey` | POST | Create API key | 2/2s |
| `/api/v5/account/sub-account/apikey` | GET | Query API keys | 2/2s |
| `/api/v5/account/sub-account/modify-apikey` | POST | Modify API key | 2/2s |
| `/api/v5/account/sub-account/delete-apikey` | POST | Delete API key | 2/2s |
| `/api/v5/account/sub-account/get-trading-balance` | GET | Sub trading balance | 6/sec |
| `/api/v5/account/sub-account/get-funding-balance` | GET | Sub funding balance | 6/sec |
| `/api/v5/account/sub-account/get-max-withdrawals` | GET | Sub max withdrawals | 2/2s |
| `/api/v5/account/sub-account/transfer` | POST | Transfer to/from sub | 2/sec |
| `/api/v5/account/sub-account/get-transfer-history` | GET | Transfer history | 6/sec |
| `/api/v5/account/sub-account/set-transfer-out` | POST | Set transfer permission | 2/2s |

---

## 6. Block Trading Service (Private API)

For institutional block trading with RFQ (Request for Quote) workflow.

### RFQ REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/blocktrading/rfq/counterparties` | GET | Available counterparties | 5/2s |
| `/api/v5/blocktrading/rfq/create` | POST | Create RFQ | 5/2s |
| `/api/v5/blocktrading/rfq/cancel` | POST | Cancel RFQ | 5/2s |
| `/api/v5/blocktrading/rfq/cancel-multiple` | POST | Cancel multiple RFQs | 2/2s |
| `/api/v5/blocktrading/rfq/cancel-all` | POST | Cancel all RFQs | 2/2s |
| `/api/v5/blocktrading/rfq/rfqs` | GET | Query RFQs | 5/2s |

### Quote REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/blocktrading/quote/create` | POST | Create quote | 50/2s |
| `/api/v5/blocktrading/quote/cancel` | POST | Cancel quote | 50/2s |
| `/api/v5/blocktrading/quote/cancel-multiple` | POST | Cancel multiple quotes | 2/2s |
| `/api/v5/blocktrading/quote/cancel-all` | POST | Cancel all quotes | 2/2s |
| `/api/v5/blocktrading/quote/execute` | POST | Execute quote | 20/2s |
| `/api/v5/blocktrading/quote/quotes` | GET | Query quotes | 5/2s |

### Block Trade REST Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v5/blocktrading/trades` | GET | User block trades | 5/2s |
| `/api/v5/blocktrading/tickers` | GET | Block tickers | 20/2s |
| `/api/v5/blocktrading/ticker` | GET | Single block ticker | 20/2s |
| `/api/v5/blocktrading/public-trades-multi-leg` | GET | Public multi-leg trades | 5/2s |
| `/api/v5/blocktrading/public-trades-single-leg` | GET | Public single-leg trades | 5/2s |

### Block Trading WebSocket Channels

| Channel | Description | Subscription Format |
|---------|-------------|---------------------|
| `rfqs` | RFQ updates | `{"channel":"rfqs"}` |
| `quotes` | Quote updates | `{"channel":"quotes"}` |
| `struc-block-trades` | Block trade updates | `{"channel":"struc-block-trades"}` |

---

## Rate Limiting Summary

### General Limits

| API Type | Default Limit | Notes |
|----------|--------------|-------|
| Public REST | 20 req/2s | Per IP address |
| Private REST | Varies | Per User ID |
| Order Operations | 60 req/2s | Per User ID + Instrument ID |
| Batch Operations | 300 req/2s | Per User ID |
| WebSocket Subscribe | 480/hour | Per connection |

### VIP Rate Limit Tiers

Higher rate limits available for VIP accounts based on:
- 30-day trading volume
- 30-day fill ratio (fills / orders)

---

## Instrument Types

| Type | Code | Description |
|------|------|-------------|
| SPOT | `SPOT` | Spot trading pairs |
| MARGIN | `MARGIN` | Margin trading pairs |
| SWAP | `SWAP` | Perpetual swaps |
| FUTURES | `FUTURES` | Delivery futures |
| OPTION | `OPTION` | Options contracts |

---

## Implementation Status for okx-client-gw-py

### Epic OKX-0001: Public Market Data (Complete)
- ✅ Public Market Data REST API
- ✅ Public WebSocket Streaming
- ✅ Instruments Service
- ✅ Candles, Tickers, Trades, Order Book

### Epic OKX-0002: Private APIs (Complete)
- ✅ HMAC-SHA256 Authentication
- ✅ Account Balance and Position Reading
- ✅ Account Configuration
- ✅ Position Management
- ✅ Order Placement (single)
- ✅ Order Cancellation (single and batch)
- ✅ Order Amendment
- ✅ Order History and Pending Orders
- ✅ Public Data Extensions (currencies, discount rates, funding rates)

### Future Phases
- ⏳ Private WebSocket Channels (account, positions, orders)
- ⏳ Batch Order Placement
- ⏳ Batch Order Amendment
- ⏳ Algo Order Support
- ⏳ Funding Operations
- ⏳ Sub-Account Management

---

## okx-client-gw-py Service Architecture

### Domain Layer

| Model | Location | Description |
|-------|----------|-------------|
| `Instrument` | `domain/models/instrument.py` | Trading instrument specifications |
| `Candle` | `domain/models/candle.py` | OHLCV candlestick data |
| `Ticker` | `domain/models/ticker.py` | Real-time market ticker |
| `Trade` | `domain/models/trade.py` | Individual trade execution |
| `OrderBook` | `domain/models/orderbook.py` | Order book with levels |
| `AccountBalance` | `domain/models/account.py` | Account balance with details |
| `AccountConfig` | `domain/models/account.py` | Account configuration |
| `Position` | `domain/models/position.py` | Open position data |
| `Order` | `domain/models/order.py` | Order state and details |
| `OrderRequest` | `domain/models/order.py` | Order placement request |

### Application Layer - Commands

| Command | Endpoint | Auth Required |
|---------|----------|---------------|
| `GetInstrumentsCommand` | `GET /api/v5/public/instruments` | No |
| `GetInstrumentCommand` | `GET /api/v5/public/instruments` | No |
| `GetTickerCommand` | `GET /api/v5/market/ticker` | No |
| `GetTickersCommand` | `GET /api/v5/market/tickers` | No |
| `GetCandlesCommand` | `GET /api/v5/market/candles` | No |
| `GetHistoryCandlesCommand` | `GET /api/v5/market/history-candles` | No |
| `GetOrderBookCommand` | `GET /api/v5/market/books` | No |
| `GetTradesCommand` | `GET /api/v5/market/trades` | No |
| `GetAccountBalanceCommand` | `GET /api/v5/account/balance` | Yes |
| `GetAccountPositionsCommand` | `GET /api/v5/account/positions` | Yes |
| `GetAccountConfigCommand` | `GET /api/v5/account/config` | Yes |
| `SetLeverageCommand` | `POST /api/v5/account/set-leverage` | Yes |
| `SetPositionModeCommand` | `POST /api/v5/account/position-mode` | Yes |
| `GetMaxAvailableSizeCommand` | `GET /api/v5/account/max-avail-size` | Yes |
| `PlaceOrderCommand` | `POST /api/v5/trade/order` | Yes |
| `CancelOrderCommand` | `POST /api/v5/trade/cancel-order` | Yes |
| `AmendOrderCommand` | `POST /api/v5/trade/amend-order` | Yes |
| `GetOrderCommand` | `GET /api/v5/trade/order` | Yes |
| `GetPendingOrdersCommand` | `GET /api/v5/trade/orders-pending` | Yes |
| `GetOrderHistoryCommand` | `GET /api/v5/trade/orders-history` | Yes |
| `CancelBatchOrdersCommand` | `POST /api/v5/trade/cancel-batch-orders` | Yes |
| `GetCurrenciesCommand` | `GET /api/v5/asset/currencies` | Partial |
| `GetDiscountRateCommand` | `GET /api/v5/public/discount-rate-interest-free-quota` | No |
| `GetFundingRateCommand` | `GET /api/v5/public/funding-rate` | No |
| `GetFundingRateHistoryCommand` | `GET /api/v5/public/funding-rate-history` | No |

### Application Layer - Services

| Service | Description | Auth Required |
|---------|-------------|---------------|
| `MarketDataService` | Tickers, order books, trades, candles | No |
| `InstrumentService` | Trading instruments lookup | No |
| `StreamingService` | WebSocket streaming (public) | No |
| `MultiChannelStreamingService` | Multi-instrument streaming | No |
| `AccountService` | Balance, positions, configuration | Yes |
| `TradeService` | Order placement and management | Yes |
| `PublicDataService` | Currencies, discount rates, funding | Partial |

### Adapters Layer

| Adapter | Description |
|---------|-------------|
| `OkxHttpClient` | HTTP client with optional auth |
| `OkxWebSocketClient` | WebSocket client (public) |
| `OkxConfig` | REST API configuration |
| `OkxWsConfig` | WebSocket configuration |
| `OkxCredentials` | Authentication credentials |

---

*Last Updated: 2025-12-08*
*Reference: https://www.okx.com/docs-v5/en/*
