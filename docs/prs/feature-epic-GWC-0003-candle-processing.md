# PR: Epic GWC-0003 - Candle Processing (OKX)

**Branch:** `feature/epic-GWC-0003-candle-processing`
**Target:** `main`
**Epic:** GWC-0003
**Component:** okx-client-gw-py

## Summary

Updates OKX candle model to conform to `CandleProtocol` from client-gw-core-py
by adding the required `time_delta` field and creating `OkxCandleFactory` for
interpolated candle creation.

## What Changed

### New Files

| File | Purpose |
|------|---------|
| `src/okx_client_gw/adapters/candle_factory.py` | OkxCandleFactory (float to Decimal conversion) |

### Modified Files

| File | Change |
|------|--------|
| `src/okx_client_gw/domain/models/candle.py` | Added `time_delta` field, float accessors |
| `src/okx_client_gw/adapters/__init__.py` | Export OkxCandleFactory |

## CandleProtocol Compliance

The OKX `Candle` model now conforms to `CandleProtocol`:

```python
class Candle(BaseModel):
    timestamp: datetime
    time_delta: timedelta  # NEW: Required for protocol
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    volume_ccy: Decimal
    volume_ccy_quote: Decimal
    confirm: bool

    model_config = {"frozen": True}

    # Float accessor properties for CandleProtocol compliance
    @property
    def open_float(self) -> float:
        return float(self.open)
    # ... etc for high, low, close, volume
```

## Factory Implementation

OKX uses `Decimal` for prices. The factory converts float inputs (from interpolation)
to Decimal:

```python
class OkxCandleFactory:
    def create(self, timestamp, time_delta, open, high, low, close, volume) -> Candle:
        return Candle(
            timestamp=timestamp,
            time_delta=time_delta,
            open=Decimal(str(open)),
            high=Decimal(str(high)),
            # ...
        )
```

## Migration

Update candle creation to include `time_delta`:

```python
# Before
candle = Candle.from_okx_array(data)

# After
candle = Candle.from_okx_array(data, time_delta=timedelta(hours=1))
```

## Testing

- [x] Ruff check passes
- [x] Existing unit tests pass
- [x] CandleProtocol compliance verified via shared library tests in client-gw-core-py

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `b2684e2` | feat(domain) | Add time_delta to Candle model and OkxCandleFactory |

## Related PRs

- client-gw-core-py: CandleProtocol and processing utilities
- coinbase-client-gw-py: CoinbaseCandleFactory implementation
- project-plan: Epic tracking documentation
