"""Candle (OHLCV) domain model."""

from datetime import datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field


class Candle(BaseModel):
    """OHLCV candlestick data.

    OKX returns candle data as an array:
    [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]

    See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks

    Attributes:
        timestamp: Opening time of the candlestick (Unix timestamp in ms).
        time_delta: Candle duration/granularity (e.g., 1H = 1 hour).
        open: Opening price.
        high: Highest price.
        low: Lowest price.
        close: Closing price.
        volume: Trading volume in base currency.
        volume_ccy: Trading volume in quote currency.
        volume_ccy_quote: Trading volume in quote currency (same as volume_ccy for spot).
        confirm: Whether the candle is confirmed (closed). False for in-progress candles.
    """

    timestamp: datetime = Field(description="Opening time of the candlestick")
    time_delta: timedelta = Field(description="Candle duration/granularity")
    open: Decimal = Field(description="Opening price")
    high: Decimal = Field(description="Highest price")
    low: Decimal = Field(description="Lowest price")
    close: Decimal = Field(description="Closing price")
    volume: Decimal = Field(description="Trading volume in base currency")
    volume_ccy: Decimal = Field(description="Trading volume in quote currency")
    volume_ccy_quote: Decimal = Field(description="Trading volume in quote currency")
    confirm: bool = Field(default=True, description="Whether the candle is confirmed")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_array(cls, data: list[str], time_delta: timedelta) -> "Candle":
        """Create a Candle from OKX API array response.

        Args:
            data: Array from OKX API [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            time_delta: Candle duration/granularity (e.g., timedelta(hours=1) for 1H bar)

        Returns:
            Candle instance.
        """
        return cls(
            timestamp=datetime.fromtimestamp(int(data[0]) / 1000),
            time_delta=time_delta,
            open=Decimal(data[1]),
            high=Decimal(data[2]),
            low=Decimal(data[3]),
            close=Decimal(data[4]),
            volume=Decimal(data[5]),
            volume_ccy=Decimal(data[6]),
            volume_ccy_quote=Decimal(data[7]),
            confirm=data[8] == "1",
        )

    @property
    def timestamp_ms(self) -> int:
        """Get timestamp as Unix milliseconds."""
        return int(self.timestamp.timestamp() * 1000)

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price (average of high and low)."""
        return (self.high + self.low) / 2

    @property
    def typical_price(self) -> Decimal:
        """Calculate typical price (average of high, low, close)."""
        return (self.high + self.low + self.close) / 3

    @property
    def range(self) -> Decimal:
        """Calculate price range (high - low)."""
        return self.high - self.low

    @property
    def body(self) -> Decimal:
        """Calculate candle body size (absolute difference between open and close)."""
        return abs(self.close - self.open)

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)."""
        return self.close < self.open

    # Float accessor properties for CandleProtocol compliance
    # (Protocol expects float, OKX uses Decimal internally)

    @property
    def open_float(self) -> float:
        """Get opening price as float for CandleProtocol compliance."""
        return float(self.open)

    @property
    def high_float(self) -> float:
        """Get highest price as float for CandleProtocol compliance."""
        return float(self.high)

    @property
    def low_float(self) -> float:
        """Get lowest price as float for CandleProtocol compliance."""
        return float(self.low)

    @property
    def close_float(self) -> float:
        """Get closing price as float for CandleProtocol compliance."""
        return float(self.close)

    @property
    def volume_float(self) -> float:
        """Get volume as float for CandleProtocol compliance."""
        return float(self.volume)
