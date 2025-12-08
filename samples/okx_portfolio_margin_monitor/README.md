# OKX Delta-Neutral Margin Monitor

Real-time margin monitoring for delta-neutral BTC carry trade positions on OKX.

## Position Structure

This monitor is designed for the classic funding rate arbitrage:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DELTA-NEUTRAL CARRY TRADE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SPOT LEG                        PERP LEG                       │
│   ────────                        ────────                       │
│   Hold BTC                        Short BTC-USDT-SWAP            │
│   (Collateral)                    (Earn funding)                 │
│                                                                  │
│   ┌─────────────┐                 ┌─────────────┐               │
│   │   1 BTC     │ ◄───HEDGE───► │  -1 BTC     │               │
│   │   SPOT      │                 │  PERP       │               │
│   └─────────────┘                 └─────────────┘               │
│         │                               │                        │
│         ▼                               ▼                        │
│   Contributes to                  Consumes margin                │
│   adjEq @ 97%                     but earns funding              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## The Key Insight

In OKX multi-currency margin mode:

| Component | Margin Treatment |
|-----------|------------------|
| Spot BTC | Contributes to `adjEq` with ~97% discount (haircut) |
| Short perp unrealised PnL (USDT) | Contributes to `adjEq` at 100% |

**When BTC crashes:**
- Your spot BTC loses value → reduces `adjEq` by `loss × 0.97`
- Your short perp gains value → increases `adjEq` by `gain × 1.00`
- Net effect: **You're slightly better off** because USDT has no haircut

This asymmetry works in your favour during crashes, but against you during rallies.

## Installation

```bash
# Clone or copy the files
pip install requests websockets python-dotenv --break-system-packages

# Set up credentials
cp .env.example .env
# Edit .env with your API credentials
```

## Usage

### One-time Report

```bash
python okx_margin_monitor.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --passphrase YOUR_PASS
```

### Continuous Monitoring (refresh every 60s)

```bash
python okx_margin_monitor.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --passphrase YOUR_PASS \
  --loop 60
```

### Real-time WebSocket Monitoring

```bash
python okx_margin_monitor.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --passphrase YOUR_PASS \
  --live
```

### Demo Trading Mode

```bash
python okx_margin_monitor.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --passphrase YOUR_PASS \
  --demo
```

## Output Example

```
============================================================
  OKX MARGIN MONITOR - 2024-12-03 14:30:00
============================================================

  Account Mode: Multi-currency

  --- ACCOUNT SUMMARY ---
  Status:              ✅ HEALTHY
  Margin Ratio:        845.32%
  Distance to Warning: +545.32%
  Distance to Liq:     +745.32%

  Adjusted Equity:     $142,500.00
  Total Equity:        $145,000.00
  Initial Margin:      $14,250.00
  Maintenance Margin:  $16,875.00

  --- SPOT HOLDINGS (Collateral) ---
  Currency      Balance      USD Value   Discount   After Haircut
  -------- ------------ -------------- ---------- --------------
  BTC          1.500000   $142,500.00     97.00%   $138,225.00
  USDT        10,000.00    $10,000.00    100.00%    $10,000.00

  --- DERIVATIVE POSITIONS ---

  BTC-USDT-SWAP (SHORT)
    Size:           1.5000
    Notional:       $142,500.00
    Entry Price:    $94,500.00
    Mark Price:     $95,000.00
    Unrealised PnL: -$750.00
    Leverage:       5.0x

  --- STRESS TEST SCENARIOS ---
    Price Δ       Spot Δ   Perp PnL Δ        Net Δ   New Margin     Status
  ---------- ------------ ------------ ------------ ------------ ----------
       -50%     -$69,113     +$71,250      +$2,138       912.3%         ✅
       -40%     -$55,290     +$57,000      +$1,710       890.1%         ✅
       -30%     -$41,468     +$42,750      +$1,283       867.9%         ✅
       -20%     -$27,645     +$28,500        +$855       845.7%         ✅
       -10%     -$13,823     +$14,250        +$428       823.5%         ✅
       +20%     +$27,645     -$28,500        -$855       801.3%         ✅
       +50%     +$69,113     -$71,250      -$2,138       756.9%         ✅

  --- LIQUIDATION ANALYSIS ---
  Current BTC Price:    $95,000.00
  Liquidation Price:    $12,350.00
  Required Drop:        -87.0%
  Buffer:               $82,650.00
```

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v5/account/balance` | Account equity, margin, adjEq |
| `GET /api/v5/account/positions` | Open derivative positions |
| `GET /api/v5/account/config` | Account mode (multi-currency, etc.) |
| `GET /api/v5/public/discount-rate-interest-free-quota` | BTC discount rate tiers |
| `GET /api/v5/public/funding-rate` | Current funding rate |
| WebSocket `account` channel | Real-time margin updates |
| WebSocket `positions` channel | Real-time position updates |

## Margin Thresholds

| Margin Ratio | Status | Action |
|--------------|--------|--------|
| > 300% | ✅ Healthy | No action needed |
| 150-300% | ⚠️ Warning | Consider adding margin |
| 100-150% | 🔴 Danger | Add margin immediately |
| ≤ 100% | 💀 Liquidation | Position being closed |

## Risk Factors to Monitor

1. **Negative Funding Rate** - When funding flips negative, shorts pay longs
2. **Basis Blowout** - Perp trades at significant discount to spot
3. **Discount Rate Changes** - OKX can adjust BTC haircuts
4. **Delta Imbalance** - Position not perfectly hedged
5. **Tier Changes** - Large positions get worse discount rates

## Files

- `okx_margin_monitor.py` - Main monitoring script
- `delta_neutral_analyser.py` - Carry trade specific analysis
- `.env.example` - Configuration template

## Dependencies

- `requests` - REST API calls
- `websockets` - Real-time monitoring (optional)
- `python-dotenv` - Environment configuration (optional)

## License

MIT
