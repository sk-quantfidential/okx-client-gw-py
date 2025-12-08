"""Position domain model.

Models for OKX trading positions.

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from okx_client_gw.domain.enums import InstType


class Position(BaseModel):
    """Trading position information.

    See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions

    Attributes:
        inst_type: Instrument type (MARGIN, SWAP, FUTURES, OPTION).
        inst_id: Instrument ID (e.g., "BTC-USDT-SWAP").
        pos_id: Position ID.
        pos_side: Position side (long, short, net).
        pos: Position quantity (positive for long, negative for short in net mode).
        base_bal: Base currency balance (for MARGIN positions).
        quote_bal: Quote currency balance (for MARGIN positions).
        base_borrowed: Base currency borrowed (for MARGIN).
        base_interest: Base currency interest (for MARGIN).
        quote_borrowed: Quote currency borrowed (for MARGIN).
        quote_interest: Quote currency interest (for MARGIN).
        avg_px: Average entry price.
        mark_px: Current mark price.
        upl: Unrealized profit and loss.
        upl_ratio: Unrealized P&L ratio.
        notional_usd: Position notional value in USD.
        lever: Leverage.
        liq_px: Estimated liquidation price.
        imr: Initial margin requirement.
        margin: Position margin.
        mgn_ratio: Margin ratio for the position.
        mmr: Maintenance margin requirement.
        liab: Liabilities (negative means liabilities).
        liab_ccy: Liabilities currency.
        interest: Interest accrued.
        trade_id: Last trade ID.
        opt_val: Option value (for OPTION positions).
        adl: Auto-deleveraging indicator (1-5, 5 = highest risk).
        ccy: Margin currency.
        last: Last traded price.
        idx_px: Index price.
        c_time: Position creation time.
        u_time: Position update time.
    """

    inst_type: InstType = Field(description="Instrument type")
    inst_id: str = Field(description="Instrument ID")
    pos_id: str = Field(default="", description="Position ID")
    pos_side: str = Field(description="Position side (long/short/net)")
    pos: Decimal = Field(description="Position quantity")
    base_bal: Decimal = Field(default=Decimal("0"), description="Base currency balance")
    quote_bal: Decimal = Field(default=Decimal("0"), description="Quote currency balance")
    base_borrowed: Decimal = Field(default=Decimal("0"), description="Base borrowed")
    base_interest: Decimal = Field(default=Decimal("0"), description="Base interest")
    quote_borrowed: Decimal = Field(default=Decimal("0"), description="Quote borrowed")
    quote_interest: Decimal = Field(default=Decimal("0"), description="Quote interest")
    avg_px: Decimal = Field(description="Average entry price")
    mark_px: Decimal = Field(default=Decimal("0"), description="Mark price")
    upl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    upl_ratio: Decimal = Field(default=Decimal("0"), description="Unrealized P&L ratio")
    notional_usd: Decimal = Field(default=Decimal("0"), description="Notional in USD")
    lever: Decimal = Field(default=Decimal("1"), description="Leverage")
    liq_px: Decimal | None = Field(default=None, description="Liquidation price")
    imr: Decimal = Field(default=Decimal("0"), description="Initial margin")
    margin: Decimal = Field(default=Decimal("0"), description="Position margin")
    mgn_ratio: Decimal | None = Field(default=None, description="Margin ratio")
    mmr: Decimal = Field(default=Decimal("0"), description="Maintenance margin")
    liab: Decimal = Field(default=Decimal("0"), description="Liabilities")
    liab_ccy: str = Field(default="", description="Liabilities currency")
    interest: Decimal = Field(default=Decimal("0"), description="Interest")
    trade_id: str = Field(default="", description="Last trade ID")
    opt_val: Decimal = Field(default=Decimal("0"), description="Option value")
    adl: str = Field(default="", description="Auto-deleveraging indicator")
    ccy: str = Field(default="", description="Margin currency")
    last: Decimal = Field(default=Decimal("0"), description="Last price")
    idx_px: Decimal = Field(default=Decimal("0"), description="Index price")
    c_time: datetime | None = Field(default=None, description="Creation time")
    u_time: datetime | None = Field(default=None, description="Update time")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> Position:
        """Create a Position from OKX API dict response.

        Args:
            data: Dict from OKX positions response.

        Returns:
            Position instance.
        """
        # Parse optional timestamps
        c_time = None
        if data.get("cTime"):
            c_time = datetime.fromtimestamp(int(data["cTime"]) / 1000, tz=UTC)

        u_time = None
        if data.get("uTime"):
            u_time = datetime.fromtimestamp(int(data["uTime"]) / 1000, tz=UTC)

        # Parse optional liquidation price
        liq_px = None
        if data.get("liqPx") and data["liqPx"] != "" and data["liqPx"] != "0":
            liq_px = Decimal(data["liqPx"])

        # Parse optional margin ratio
        mgn_ratio = None
        if data.get("mgnRatio") and data["mgnRatio"] != "":
            mgn_ratio = Decimal(data["mgnRatio"])

        return cls(
            inst_type=InstType(data["instType"]),
            inst_id=data["instId"],
            pos_id=data.get("posId", ""),
            pos_side=data.get("posSide", "net"),
            pos=Decimal(data.get("pos", "0") or "0"),
            base_bal=Decimal(data.get("baseBal", "0") or "0"),
            quote_bal=Decimal(data.get("quoteBal", "0") or "0"),
            base_borrowed=Decimal(data.get("baseBorrowed", "0") or "0"),
            base_interest=Decimal(data.get("baseInterest", "0") or "0"),
            quote_borrowed=Decimal(data.get("quoteBorrowed", "0") or "0"),
            quote_interest=Decimal(data.get("quoteInterest", "0") or "0"),
            avg_px=Decimal(data.get("avgPx", "0") or "0"),
            mark_px=Decimal(data.get("markPx", "0") or "0"),
            upl=Decimal(data.get("upl", "0") or "0"),
            upl_ratio=Decimal(data.get("uplRatio", "0") or "0"),
            notional_usd=Decimal(data.get("notionalUsd", "0") or "0"),
            lever=Decimal(data.get("lever", "1") or "1"),
            liq_px=liq_px,
            imr=Decimal(data.get("imr", "0") or "0"),
            margin=Decimal(data.get("margin", "0") or "0"),
            mgn_ratio=mgn_ratio,
            mmr=Decimal(data.get("mmr", "0") or "0"),
            liab=Decimal(data.get("liab", "0") or "0"),
            liab_ccy=data.get("liabCcy", ""),
            interest=Decimal(data.get("interest", "0") or "0"),
            trade_id=data.get("tradeId", ""),
            opt_val=Decimal(data.get("optVal", "0") or "0"),
            adl=data.get("adl", ""),
            ccy=data.get("ccy", ""),
            last=Decimal(data.get("last", "0") or "0"),
            idx_px=Decimal(data.get("idxPx", "0") or "0"),
            c_time=c_time,
            u_time=u_time,
        )

    @property
    def is_long(self) -> bool:
        """Check if this is a long position."""
        if self.pos_side == "long":
            return True
        if self.pos_side == "net":
            return self.pos > 0
        return False

    @property
    def is_short(self) -> bool:
        """Check if this is a short position."""
        if self.pos_side == "short":
            return True
        if self.pos_side == "net":
            return self.pos < 0
        return False

    @property
    def abs_pos(self) -> Decimal:
        """Get absolute position size."""
        return abs(self.pos)

    @property
    def pnl_percent(self) -> Decimal:
        """Calculate P&L as percentage of entry."""
        if self.avg_px == 0:
            return Decimal("0")
        return self.upl_ratio * 100

    @property
    def is_profitable(self) -> bool:
        """Check if position is currently profitable."""
        return self.upl > 0

    @property
    def distance_to_liquidation(self) -> Decimal | None:
        """Calculate price distance to liquidation as percentage.

        Returns:
            Percentage distance to liquidation, or None if no liquidation price.
        """
        if self.liq_px is None or self.mark_px == 0:
            return None

        if self.is_long:
            # Long: liquidation is below mark price
            return ((self.mark_px - self.liq_px) / self.mark_px) * 100
        else:
            # Short: liquidation is above mark price
            return ((self.liq_px - self.mark_px) / self.mark_px) * 100

    @property
    def effective_leverage(self) -> Decimal:
        """Calculate effective leverage based on notional and margin."""
        if self.margin == 0:
            return Decimal("0")
        return self.notional_usd / self.margin
