"""Ticker domain model."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from okx_client_gw.domain.enums import InstType


class Ticker(BaseModel):
    """Market ticker data.

    See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-ticker

    Attributes:
        inst_type: Instrument type.
        inst_id: Instrument ID (e.g., "BTC-USDT").
        last: Last traded price.
        last_sz: Last traded size.
        ask_px: Best ask price.
        ask_sz: Best ask size.
        bid_px: Best bid price.
        bid_sz: Best bid size.
        open_24h: Open price in the past 24 hours.
        high_24h: Highest price in the past 24 hours.
        low_24h: Lowest price in the past 24 hours.
        vol_ccy_24h: 24h trading volume in quote currency.
        vol_24h: 24h trading volume in base currency.
        ts: Ticker timestamp.
        sod_utc0: Open price at UTC 00:00.
        sod_utc8: Open price at UTC+8 00:00.
    """

    inst_type: InstType = Field(description="Instrument type")
    inst_id: str = Field(description="Instrument ID")
    last: Decimal = Field(description="Last traded price")
    last_sz: Decimal = Field(description="Last traded size")
    ask_px: Decimal = Field(description="Best ask price")
    ask_sz: Decimal = Field(description="Best ask size")
    bid_px: Decimal = Field(description="Best bid price")
    bid_sz: Decimal = Field(description="Best bid size")
    open_24h: Decimal = Field(description="Open price in past 24h")
    high_24h: Decimal = Field(description="Highest price in past 24h")
    low_24h: Decimal = Field(description="Lowest price in past 24h")
    vol_ccy_24h: Decimal = Field(description="24h volume in quote currency")
    vol_24h: Decimal = Field(description="24h volume in base currency")
    ts: datetime = Field(description="Ticker timestamp")
    sod_utc0: Decimal | None = Field(default=None, description="Open price at UTC 00:00")
    sod_utc8: Decimal | None = Field(default=None, description="Open price at UTC+8 00:00")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> "Ticker":
        """Create a Ticker from OKX API dict response.

        Args:
            data: Dict from OKX API ticker response.

        Returns:
            Ticker instance.
        """
        return cls(
            inst_type=InstType(data["instType"]),
            inst_id=data["instId"],
            last=Decimal(data["last"]),
            last_sz=Decimal(data["lastSz"]),
            ask_px=Decimal(data["askPx"]),
            ask_sz=Decimal(data["askSz"]),
            bid_px=Decimal(data["bidPx"]),
            bid_sz=Decimal(data["bidSz"]),
            open_24h=Decimal(data["open24h"]),
            high_24h=Decimal(data["high24h"]),
            low_24h=Decimal(data["low24h"]),
            vol_ccy_24h=Decimal(data["volCcy24h"]),
            vol_24h=Decimal(data["vol24h"]),
            ts=datetime.fromtimestamp(int(data["ts"]) / 1000),
            sod_utc0=Decimal(data["sodUtc0"]) if data.get("sodUtc0") else None,
            sod_utc8=Decimal(data["sodUtc8"]) if data.get("sodUtc8") else None,
        )

    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        return self.ask_px - self.bid_px

    @property
    def spread_percent(self) -> Decimal:
        """Calculate bid-ask spread as percentage of mid price."""
        mid = (self.ask_px + self.bid_px) / 2
        if mid == 0:
            return Decimal("0")
        return (self.spread / mid) * 100

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.ask_px + self.bid_px) / 2

    @property
    def change_24h(self) -> Decimal:
        """Calculate 24h price change."""
        return self.last - self.open_24h

    @property
    def change_24h_percent(self) -> Decimal:
        """Calculate 24h price change percentage."""
        if self.open_24h == 0:
            return Decimal("0")
        return (self.change_24h / self.open_24h) * 100

    @property
    def range_24h(self) -> Decimal:
        """Calculate 24h price range."""
        return self.high_24h - self.low_24h
