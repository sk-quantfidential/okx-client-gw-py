"""Order domain model.

Models for OKX trading orders.

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-details
See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from okx_client_gw.domain.enums import (
    InstType,
    OrderState,
    OrderType,
    PositionSide,
    TradeMode,
    TradeSide,
)


class Order(BaseModel):
    """Trading order information.

    See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-details

    Attributes:
        inst_type: Instrument type.
        inst_id: Instrument ID (e.g., "BTC-USDT").
        ord_id: Order ID assigned by OKX.
        cl_ord_id: Client-assigned order ID.
        ccy: Margin currency (for margin trades).
        tag: Order tag for analytics.
        px: Order price (None for market orders).
        sz: Order size.
        ord_type: Order type (market, limit, etc.).
        side: Buy or sell.
        pos_side: Position side (for hedge mode).
        td_mode: Trade mode (cross, isolated, cash).
        acc_fill_sz: Accumulated fill size.
        fill_px: Last fill price.
        trade_id: Last trade ID.
        fill_sz: Last fill size.
        fill_time: Last fill time.
        avg_px: Average fill price.
        state: Order state (live, filled, canceled).
        lever: Leverage.
        tp_trigger_px: Take profit trigger price.
        tp_ord_px: Take profit order price.
        sl_trigger_px: Stop loss trigger price.
        sl_ord_px: Stop loss order price.
        fee_ccy: Fee currency.
        fee: Accumulated fees (negative).
        rebate_ccy: Rebate currency.
        rebate: Rebate amount (positive).
        pnl: P&L for this order.
        category: Order category.
        reduce_only: Whether reduce-only order.
        cancel_source: Cancellation source.
        cancel_source_reason: Cancellation reason.
        c_time: Order creation time.
        u_time: Order update time.
    """

    inst_type: InstType = Field(description="Instrument type")
    inst_id: str = Field(description="Instrument ID")
    ord_id: str = Field(description="Order ID")
    cl_ord_id: str = Field(default="", description="Client order ID")
    ccy: str = Field(default="", description="Margin currency")
    tag: str = Field(default="", description="Order tag")
    px: Decimal | None = Field(default=None, description="Order price")
    sz: Decimal = Field(description="Order size")
    ord_type: OrderType = Field(description="Order type")
    side: TradeSide = Field(description="Order side")
    pos_side: PositionSide = Field(default=PositionSide.NET, description="Position side")
    td_mode: TradeMode = Field(description="Trade mode")
    acc_fill_sz: Decimal = Field(default=Decimal("0"), description="Accumulated fill size")
    fill_px: Decimal | None = Field(default=None, description="Last fill price")
    trade_id: str = Field(default="", description="Last trade ID")
    fill_sz: Decimal = Field(default=Decimal("0"), description="Last fill size")
    fill_time: datetime | None = Field(default=None, description="Last fill time")
    avg_px: Decimal | None = Field(default=None, description="Average fill price")
    state: OrderState = Field(description="Order state")
    lever: Decimal = Field(default=Decimal("1"), description="Leverage")
    tp_trigger_px: Decimal | None = Field(default=None, description="TP trigger price")
    tp_ord_px: Decimal | None = Field(default=None, description="TP order price")
    sl_trigger_px: Decimal | None = Field(default=None, description="SL trigger price")
    sl_ord_px: Decimal | None = Field(default=None, description="SL order price")
    fee_ccy: str = Field(default="", description="Fee currency")
    fee: Decimal = Field(default=Decimal("0"), description="Fees (negative)")
    rebate_ccy: str = Field(default="", description="Rebate currency")
    rebate: Decimal = Field(default=Decimal("0"), description="Rebate (positive)")
    pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    category: str = Field(default="normal", description="Order category")
    reduce_only: bool = Field(default=False, description="Reduce-only order")
    cancel_source: str = Field(default="", description="Cancel source")
    cancel_source_reason: str = Field(default="", description="Cancel reason")
    c_time: datetime | None = Field(default=None, description="Creation time")
    u_time: datetime | None = Field(default=None, description="Update time")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> Order:
        """Create an Order from OKX API dict response.

        Args:
            data: Dict from OKX order response.

        Returns:
            Order instance.
        """
        # Parse timestamps
        c_time = None
        if data.get("cTime"):
            c_time = datetime.fromtimestamp(int(data["cTime"]) / 1000, tz=UTC)

        u_time = None
        if data.get("uTime"):
            u_time = datetime.fromtimestamp(int(data["uTime"]) / 1000, tz=UTC)

        fill_time = None
        if data.get("fillTime"):
            fill_time = datetime.fromtimestamp(int(data["fillTime"]) / 1000, tz=UTC)

        # Parse optional decimal fields
        px = None
        if data.get("px") and data["px"] != "":
            px = Decimal(data["px"])

        avg_px = None
        if data.get("avgPx") and data["avgPx"] != "":
            avg_px = Decimal(data["avgPx"])

        fill_px = None
        if data.get("fillPx") and data["fillPx"] != "":
            fill_px = Decimal(data["fillPx"])

        tp_trigger_px = None
        if data.get("tpTriggerPx") and data["tpTriggerPx"] != "":
            tp_trigger_px = Decimal(data["tpTriggerPx"])

        tp_ord_px = None
        if data.get("tpOrdPx") and data["tpOrdPx"] != "":
            tp_ord_px = Decimal(data["tpOrdPx"])

        sl_trigger_px = None
        if data.get("slTriggerPx") and data["slTriggerPx"] != "":
            sl_trigger_px = Decimal(data["slTriggerPx"])

        sl_ord_px = None
        if data.get("slOrdPx") and data["slOrdPx"] != "":
            sl_ord_px = Decimal(data["slOrdPx"])

        # Parse position side with default
        pos_side_str = data.get("posSide", "net") or "net"
        if pos_side_str == "":
            pos_side_str = "net"
        pos_side = PositionSide(pos_side_str)

        return cls(
            inst_type=InstType(data["instType"]),
            inst_id=data["instId"],
            ord_id=data.get("ordId", ""),
            cl_ord_id=data.get("clOrdId", ""),
            ccy=data.get("ccy", ""),
            tag=data.get("tag", ""),
            px=px,
            sz=Decimal(data.get("sz", "0") or "0"),
            ord_type=OrderType(data.get("ordType", "limit")),
            side=TradeSide(data.get("side", "buy")),
            pos_side=pos_side,
            td_mode=TradeMode(data.get("tdMode", "cash")),
            acc_fill_sz=Decimal(data.get("accFillSz", "0") or "0"),
            fill_px=fill_px,
            trade_id=data.get("tradeId", ""),
            fill_sz=Decimal(data.get("fillSz", "0") or "0"),
            fill_time=fill_time,
            avg_px=avg_px,
            state=OrderState(data.get("state", "live")),
            lever=Decimal(data.get("lever", "1") or "1"),
            tp_trigger_px=tp_trigger_px,
            tp_ord_px=tp_ord_px,
            sl_trigger_px=sl_trigger_px,
            sl_ord_px=sl_ord_px,
            fee_ccy=data.get("feeCcy", ""),
            fee=Decimal(data.get("fee", "0") or "0"),
            rebate_ccy=data.get("rebateCcy", ""),
            rebate=Decimal(data.get("rebate", "0") or "0"),
            pnl=Decimal(data.get("pnl", "0") or "0"),
            category=data.get("category", "normal"),
            reduce_only=data.get("reduceOnly", "false").lower() == "true",
            cancel_source=data.get("cancelSource", ""),
            cancel_source_reason=data.get("cancelSourceReason", ""),
            c_time=c_time,
            u_time=u_time,
        )

    @property
    def is_live(self) -> bool:
        """Check if order is still active."""
        return self.state == OrderState.LIVE

    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.state == OrderState.FILLED

    @property
    def is_canceled(self) -> bool:
        """Check if order was canceled."""
        return self.state in (OrderState.CANCELED, OrderState.MMP_CANCELED)

    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.state == OrderState.PARTIALLY_FILLED

    @property
    def fill_ratio(self) -> Decimal:
        """Calculate fill ratio (0-1)."""
        if self.sz == 0:
            return Decimal("0")
        return self.acc_fill_sz / self.sz

    @property
    def fill_percent(self) -> Decimal:
        """Calculate fill percentage (0-100)."""
        return self.fill_ratio * 100

    @property
    def remaining_sz(self) -> Decimal:
        """Calculate remaining unfilled size."""
        return self.sz - self.acc_fill_sz

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.side == TradeSide.BUY

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.side == TradeSide.SELL

    @property
    def is_market_order(self) -> bool:
        """Check if this is a market order."""
        return self.ord_type == OrderType.MARKET

    @property
    def is_limit_order(self) -> bool:
        """Check if this is a limit order."""
        return self.ord_type in (OrderType.LIMIT, OrderType.POST_ONLY)

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost/value of filled portion."""
        if self.avg_px is None:
            return Decimal("0")
        return self.acc_fill_sz * self.avg_px

    @property
    def net_fee(self) -> Decimal:
        """Calculate net fees (fee + rebate)."""
        return self.fee + self.rebate


class OrderRequest(BaseModel):
    """Request to place a new order.

    See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order
    """

    inst_id: str = Field(description="Instrument ID")
    td_mode: TradeMode = Field(description="Trade mode")
    side: TradeSide = Field(description="Order side")
    ord_type: OrderType = Field(description="Order type")
    sz: Decimal = Field(description="Order size")
    px: Decimal | None = Field(default=None, description="Price (for limit orders)")
    ccy: str | None = Field(default=None, description="Margin currency")
    cl_ord_id: str | None = Field(default=None, description="Client order ID")
    tag: str | None = Field(default=None, description="Order tag")
    pos_side: PositionSide | None = Field(default=None, description="Position side")
    reduce_only: bool = Field(default=False, description="Reduce-only order")
    tgt_ccy: str | None = Field(default=None, description="Target currency (for SPOT)")

    def to_okx_dict(self) -> dict:
        """Convert to OKX API request format.

        Returns:
            Dict suitable for OKX order placement API.
        """
        request = {
            "instId": self.inst_id,
            "tdMode": self.td_mode.value,
            "side": self.side.value,
            "ordType": self.ord_type.value,
            "sz": str(self.sz),
        }

        if self.px is not None:
            request["px"] = str(self.px)

        if self.ccy:
            request["ccy"] = self.ccy

        if self.cl_ord_id:
            request["clOrdId"] = self.cl_ord_id

        if self.tag:
            request["tag"] = self.tag

        if self.pos_side:
            request["posSide"] = self.pos_side.value

        if self.reduce_only:
            request["reduceOnly"] = "true"

        if self.tgt_ccy:
            request["tgtCcy"] = self.tgt_ccy

        return request
