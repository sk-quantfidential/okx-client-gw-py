"""Trade domain model."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from okx_client_gw.domain.enums import TradeSide


class Trade(BaseModel):
    """Individual trade data.

    See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-trades

    Attributes:
        inst_id: Instrument ID (e.g., "BTC-USDT").
        trade_id: Trade ID.
        px: Trade price.
        sz: Trade size.
        side: Trade side (buy/sell) - taker side.
        ts: Trade timestamp.
    """

    inst_id: str = Field(description="Instrument ID")
    trade_id: str = Field(description="Trade ID")
    px: Decimal = Field(description="Trade price")
    sz: Decimal = Field(description="Trade size")
    side: TradeSide = Field(description="Trade side (taker side)")
    ts: datetime = Field(description="Trade timestamp")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> "Trade":
        """Create a Trade from OKX API dict response.

        Args:
            data: Dict from OKX API trade response.

        Returns:
            Trade instance.
        """
        return cls(
            inst_id=data["instId"],
            trade_id=data["tradeId"],
            px=Decimal(data["px"]),
            sz=Decimal(data["sz"]),
            side=TradeSide(data["side"]),
            ts=datetime.fromtimestamp(int(data["ts"]) / 1000),
        )

    @property
    def notional(self) -> Decimal:
        """Calculate trade notional value (price * size)."""
        return self.px * self.sz

    @property
    def is_buy(self) -> bool:
        """Check if trade is a buy (taker bought)."""
        return self.side == TradeSide.BUY

    @property
    def is_sell(self) -> bool:
        """Check if trade is a sell (taker sold)."""
        return self.side == TradeSide.SELL
