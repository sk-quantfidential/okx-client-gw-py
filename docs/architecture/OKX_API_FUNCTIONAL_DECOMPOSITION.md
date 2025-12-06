# OKX API Functional Decomposition

Reference: https://www.okx.com/docs-v5/en/#overview (use for behavior and payload shapes; do not vendor code). Mirrors the Deribit decomposition to keep gateway scope aligned.

## Auth, Environments, URLs
- REST: API key + secret + passphrase + timestamp/signature; `flag` distinguishes live (`0`) vs demo (`1`). Domain defaults to `https://www.okx.com`; allow override for regional/demo hosts.
- WebSocket: login payload with key/passphrase/secret/timestamp/signature; public streams are anonymous. Separate URLs for public vs private, and demo vs live.
- Time sync: prefer server time endpoint for signatures; back off on system-status degradation.

## Service Segments

### 1) Public Market Data (no auth)
- REST/WS: instruments, tickers, order book (`books`, `books-lite`), trades, candles, mark/index prices, funding rates/history, open interest, insurance fund, delivery/exercise history, option chains/Greeks.
- WS channels: tickers, books, trades, candles, mark-price, index, funding-rate.
- Notes: keep bursty subscriptions within rate limits; expose lightweight book (books-lite) and full book variants.

### 2) Account & Wallet (private)
- Balances (cash/margin/portfolio), positions, account mode/config (isolated/cross/PM), risk/collateral, Greeks, borrowing/interest, VIP loans, transfers (master/sub), subaccount views.
- WS private: account/balance/position/greeks updates.
- Scopes: treat wallet vs account separation; segregate keys for least privilege.

### 3) Trading / OMS-EMS (private)
- Place/amend/cancel orders (spot/swap/futures/options), batch ops, OCO/OTO variants, algo/trigger/iceberg/twap/conditional, set leverage/margin mode, risk limits.
- Query open orders, fills, history. Close/exit positions.
- WS private: orders/trades/fills/positions/algo events.
- Notes: standardize on idempotent client order ids; map error codes into core error categories.

### 4) Funding, Convert, Finance (private)
- Deposits/withdrawals, internal transfers, convert, savings/staking/earn products, interest history.
- Typically wallet-scoped; gate behind feature flags if not needed for initial release.

### 5) Block/RFQ (private, optional)
- RFQ creation/quotes, block trades lifecycle. Lower priority unless a requirement emerges.

### 6) System & Health
- System status/maintenance windows, server time, ping. Use for health endpoints and backoff control.

### 7) Grid/Strategy Bots (out of MVP)
- Grid/strategy bot endpoints; exclude from initial gateway unless explicitly requested.

## Implementation Notes for okx-client-gw-py
- Build on `client-gw-core-py` for HTTP/WS, rate limiting, backoff, circuit breaker, logging/metrics/tracing.
- Structure services to mirror this decomposition (public MD, account/wallet, trading OMS, optional finance/block) and keep parity with the Deribit gateway layout.
- Use `okx-api-code` only for examples of signing/logins/channel lists; do not import or vendor its code.
