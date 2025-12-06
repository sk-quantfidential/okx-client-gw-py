"""Instrument domain model."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from okx_client_gw.domain.enums import InstType


class Instrument(BaseModel):
    """Trading instrument information.

    See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments

    Attributes:
        inst_type: Instrument type (SPOT, SWAP, FUTURES, OPTION).
        inst_id: Instrument ID (e.g., "BTC-USDT", "BTC-USDT-SWAP").
        uly: Underlying (e.g., "BTC-USDT" for derivatives).
        inst_family: Instrument family (e.g., "BTC-USDT").
        base_ccy: Base currency (e.g., "BTC").
        quote_ccy: Quote currency (e.g., "USDT").
        settle_ccy: Settlement currency.
        ct_val: Contract value (for derivatives).
        ct_mult: Contract multiplier.
        ct_val_ccy: Contract value currency.
        opt_type: Option type (C=Call, P=Put).
        stk: Strike price (for options).
        list_time: Listing time.
        exp_time: Expiry time (for derivatives).
        lever: Max leverage (for derivatives).
        tick_sz: Tick size (minimum price increment).
        lot_sz: Lot size (minimum quantity increment).
        min_sz: Minimum order size.
        ct_type: Contract type (linear, inverse).
        state: Instrument state (live, suspend, preopen, settlement).
    """

    inst_type: InstType = Field(description="Instrument type")
    inst_id: str = Field(description="Instrument ID")
    uly: str | None = Field(default=None, description="Underlying")
    inst_family: str | None = Field(default=None, description="Instrument family")
    base_ccy: str | None = Field(default=None, description="Base currency")
    quote_ccy: str | None = Field(default=None, description="Quote currency")
    settle_ccy: str | None = Field(default=None, description="Settlement currency")
    ct_val: Decimal | None = Field(default=None, description="Contract value")
    ct_mult: Decimal | None = Field(default=None, description="Contract multiplier")
    ct_val_ccy: str | None = Field(default=None, description="Contract value currency")
    opt_type: str | None = Field(default=None, description="Option type (C/P)")
    stk: Decimal | None = Field(default=None, description="Strike price")
    list_time: datetime | None = Field(default=None, description="Listing time")
    exp_time: datetime | None = Field(default=None, description="Expiry time")
    lever: Decimal | None = Field(default=None, description="Max leverage")
    tick_sz: Decimal = Field(description="Tick size")
    lot_sz: Decimal = Field(description="Lot size")
    min_sz: Decimal = Field(description="Minimum order size")
    ct_type: str | None = Field(default=None, description="Contract type")
    state: str = Field(default="live", description="Instrument state")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> "Instrument":
        """Create an Instrument from OKX API dict response.

        Args:
            data: Dict from OKX API instruments response.

        Returns:
            Instrument instance.
        """

        def parse_decimal(value: str | None) -> Decimal | None:
            return Decimal(value) if value else None

        def parse_timestamp(value: str | None) -> datetime | None:
            return datetime.fromtimestamp(int(value) / 1000) if value else None

        return cls(
            inst_type=InstType(data["instType"]),
            inst_id=data["instId"],
            uly=data.get("uly") or None,
            inst_family=data.get("instFamily") or None,
            base_ccy=data.get("baseCcy") or None,
            quote_ccy=data.get("quoteCcy") or None,
            settle_ccy=data.get("settleCcy") or None,
            ct_val=parse_decimal(data.get("ctVal")),
            ct_mult=parse_decimal(data.get("ctMult")),
            ct_val_ccy=data.get("ctValCcy") or None,
            opt_type=data.get("optType") or None,
            stk=parse_decimal(data.get("stk")),
            list_time=parse_timestamp(data.get("listTime")),
            exp_time=parse_timestamp(data.get("expTime")),
            lever=parse_decimal(data.get("lever")),
            tick_sz=Decimal(data["tickSz"]),
            lot_sz=Decimal(data["lotSz"]),
            min_sz=Decimal(data["minSz"]),
            ct_type=data.get("ctType") or None,
            state=data.get("state", "live"),
        )

    @property
    def is_spot(self) -> bool:
        """Check if instrument is spot."""
        return self.inst_type == InstType.SPOT

    @property
    def is_derivative(self) -> bool:
        """Check if instrument is a derivative."""
        return self.inst_type in (InstType.SWAP, InstType.FUTURES, InstType.OPTION)

    @property
    def is_perpetual(self) -> bool:
        """Check if instrument is a perpetual swap."""
        return self.inst_type == InstType.SWAP

    @property
    def is_futures(self) -> bool:
        """Check if instrument is futures."""
        return self.inst_type == InstType.FUTURES

    @property
    def is_option(self) -> bool:
        """Check if instrument is an option."""
        return self.inst_type == InstType.OPTION

    @property
    def is_call(self) -> bool:
        """Check if instrument is a call option."""
        return self.opt_type == "C"

    @property
    def is_put(self) -> bool:
        """Check if instrument is a put option."""
        return self.opt_type == "P"

    @property
    def is_linear(self) -> bool:
        """Check if derivative is linear (USDT margined)."""
        return self.ct_type == "linear"

    @property
    def is_inverse(self) -> bool:
        """Check if derivative is inverse (coin margined)."""
        return self.ct_type == "inverse"

    @property
    def is_live(self) -> bool:
        """Check if instrument is actively trading."""
        return self.state == "live"
