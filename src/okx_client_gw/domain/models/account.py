"""Account domain models.

Models for OKX account-related data including balance, configuration, and details.

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance
See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BalanceDetail(BaseModel):
    """Balance details for a single currency.

    Part of the account balance response, showing detailed holdings
    for each currency in the account.

    Attributes:
        ccy: Currency name (e.g., "BTC", "USDT").
        eq: Equity of the currency.
        cash_bal: Cash balance.
        upl: Unrealized P&L.
        iso_eq: Isolated margin equity (for cross/isolated positions).
        avail_eq: Available equity.
        dis_eq: Discount equity of the currency.
        avail_bal: Available balance.
        frozen_bal: Frozen balance for orders.
        ord_frozen: Frozen for open orders.
        iso_liab: Isolated margin liabilities.
        spot_in_use_amt: Spot in use.
        interest: Accrued interest.
        notional_lever: Leverage for this currency.
        stgy_eq: Strategy equity.
        update_time: Update timestamp.
    """

    ccy: str = Field(description="Currency name")
    eq: Decimal = Field(description="Equity of the currency")
    cash_bal: Decimal = Field(description="Cash balance")
    upl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    iso_eq: Decimal = Field(default=Decimal("0"), description="Isolated margin equity")
    avail_eq: Decimal = Field(description="Available equity")
    dis_eq: Decimal = Field(default=Decimal("0"), description="Discount equity")
    avail_bal: Decimal = Field(description="Available balance")
    frozen_bal: Decimal = Field(default=Decimal("0"), description="Frozen balance")
    ord_frozen: Decimal = Field(default=Decimal("0"), description="Frozen for orders")
    iso_liab: Decimal = Field(default=Decimal("0"), description="Isolated liabilities")
    spot_in_use_amt: Decimal = Field(default=Decimal("0"), description="Spot in use")
    interest: Decimal = Field(default=Decimal("0"), description="Accrued interest")
    notional_lever: Decimal = Field(default=Decimal("0"), description="Leverage")
    stgy_eq: Decimal = Field(default=Decimal("0"), description="Strategy equity")
    update_time: datetime | None = Field(default=None, description="Update time")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> BalanceDetail:
        """Create a BalanceDetail from OKX API dict response.

        Args:
            data: Dict from OKX account balance details.

        Returns:
            BalanceDetail instance.
        """
        update_time = None
        if data.get("uTime"):
            update_time = datetime.fromtimestamp(int(data["uTime"]) / 1000, tz=UTC)

        return cls(
            ccy=data["ccy"],
            eq=Decimal(data.get("eq", "0") or "0"),
            cash_bal=Decimal(data.get("cashBal", "0") or "0"),
            upl=Decimal(data.get("upl", "0") or "0"),
            iso_eq=Decimal(data.get("isoEq", "0") or "0"),
            avail_eq=Decimal(data.get("availEq", "0") or "0"),
            dis_eq=Decimal(data.get("disEq", "0") or "0"),
            avail_bal=Decimal(data.get("availBal", "0") or "0"),
            frozen_bal=Decimal(data.get("frozenBal", "0") or "0"),
            ord_frozen=Decimal(data.get("ordFrozen", "0") or "0"),
            iso_liab=Decimal(data.get("isoLiab", "0") or "0"),
            spot_in_use_amt=Decimal(data.get("spotInUseAmt", "0") or "0"),
            interest=Decimal(data.get("interest", "0") or "0"),
            notional_lever=Decimal(data.get("notionalLever", "0") or "0"),
            stgy_eq=Decimal(data.get("stgyEq", "0") or "0"),
            update_time=update_time,
        )


class AccountBalance(BaseModel):
    """Account balance information.

    See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance

    OKX has 4 account modes:
    - 1: Simple mode (Spot only)
    - 2: Single-currency margin mode
    - 3: Multi-currency margin mode
    - 4: Portfolio margin mode

    Attributes:
        total_eq: Total equity in USD.
        adj_eq: Adjusted equity (for margin calculation).
        iso_eq: Isolated margin equity.
        ord_froz: Margin frozen for open orders.
        imr: Initial margin requirement.
        mmr: Maintenance margin requirement.
        mgn_ratio: Margin ratio (account health indicator).
        notional_usd: Total notional value in USD.
        upl: Total unrealized P&L.
        details: Per-currency balance breakdown.
        update_time: Balance update timestamp.
    """

    total_eq: Decimal = Field(description="Total equity in USD")
    adj_eq: Decimal = Field(default=Decimal("0"), description="Adjusted equity")
    iso_eq: Decimal = Field(default=Decimal("0"), description="Isolated margin equity")
    ord_froz: Decimal = Field(default=Decimal("0"), description="Order margin frozen")
    imr: Decimal = Field(default=Decimal("0"), description="Initial margin requirement")
    mmr: Decimal = Field(default=Decimal("0"), description="Maintenance margin requirement")
    mgn_ratio: Decimal | None = Field(default=None, description="Margin ratio")
    notional_usd: Decimal = Field(default=Decimal("0"), description="Total notional in USD")
    upl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    details: list[BalanceDetail] = Field(default_factory=list, description="Currency details")
    update_time: datetime | None = Field(default=None, description="Update timestamp")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> AccountBalance:
        """Create an AccountBalance from OKX API dict response.

        Args:
            data: Dict from OKX account balance response.

        Returns:
            AccountBalance instance.
        """
        update_time = None
        if data.get("uTime"):
            update_time = datetime.fromtimestamp(int(data["uTime"]) / 1000, tz=UTC)

        # Parse margin ratio - can be empty string or missing
        mgn_ratio = None
        if data.get("mgnRatio") and data["mgnRatio"] != "":
            mgn_ratio = Decimal(data["mgnRatio"])

        # Parse currency details
        details = [
            BalanceDetail.from_okx_dict(d)
            for d in data.get("details", [])
        ]

        return cls(
            total_eq=Decimal(data.get("totalEq", "0") or "0"),
            adj_eq=Decimal(data.get("adjEq", "0") or "0"),
            iso_eq=Decimal(data.get("isoEq", "0") or "0"),
            ord_froz=Decimal(data.get("ordFroz", "0") or "0"),
            imr=Decimal(data.get("imr", "0") or "0"),
            mmr=Decimal(data.get("mmr", "0") or "0"),
            mgn_ratio=mgn_ratio,
            notional_usd=Decimal(data.get("notionalUsd", "0") or "0"),
            upl=Decimal(data.get("upl", "0") or "0"),
            details=details,
            update_time=update_time,
        )

    @property
    def available_equity(self) -> Decimal:
        """Calculate total available equity across all currencies."""
        return sum((d.avail_eq for d in self.details), Decimal("0"))

    @property
    def is_healthy(self) -> bool:
        """Check if margin ratio indicates healthy account (>150%)."""
        if self.mgn_ratio is None:
            return True  # Simple mode, no margin
        return self.mgn_ratio > Decimal("1.5")

    def get_currency_balance(self, ccy: str) -> BalanceDetail | None:
        """Get balance details for a specific currency.

        Args:
            ccy: Currency name (e.g., "BTC", "USDT").

        Returns:
            BalanceDetail for the currency, or None if not found.
        """
        for detail in self.details:
            if detail.ccy == ccy:
                return detail
        return None


class AccountConfig(BaseModel):
    """Account configuration settings.

    See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration

    Account levels:
    - 1: Simple mode (Spot trading only)
    - 2: Single-currency margin mode
    - 3: Multi-currency margin mode
    - 4: Portfolio margin mode

    Attributes:
        uid: Account unique identifier.
        acct_lv: Account level (1-4).
        pos_mode: Position mode (long_short_mode, net_mode).
        auto_loan: Whether auto-borrow is enabled.
        greeks_type: Greeks calculation type (PA for physical, BS for Black-Scholes).
        level: User level (deprecated, use acct_lv).
        level_tmp: Temporary user level.
        ct_iso_mode: Isolated margin mode for contracts.
        mgn_iso_mode: Isolated margin mode for margin trades.
        spot_offset_type: Spot offset type.
        role_type: User role (0=normal, 1=leading trader, 2=copy trader).
        trader_inst_id: Copy trading instrument ID.
        spot_role_type: Spot copy trading role.
        spot_trader_inst_id: Spot copy trading instrument ID.
        ip: IP restriction settings.
        perm: API key permissions.
        label: API key label.
        enable_spot_borrow: Whether spot borrowing is enabled.
    """

    uid: str = Field(description="Account unique ID")
    acct_lv: str = Field(description="Account level (1-4)")
    pos_mode: str = Field(description="Position mode")
    auto_loan: bool = Field(default=False, description="Auto-borrow enabled")
    greeks_type: str = Field(default="PA", description="Greeks calculation type")
    level: str = Field(default="", description="User level (deprecated)")
    level_tmp: str = Field(default="", description="Temporary user level")
    ct_iso_mode: str = Field(default="", description="Contract isolated mode")
    mgn_iso_mode: str = Field(default="", description="Margin isolated mode")
    spot_offset_type: str = Field(default="", description="Spot offset type")
    role_type: str = Field(default="0", description="User role type")
    trader_inst_id: str = Field(default="", description="Copy trading inst ID")
    spot_role_type: str = Field(default="0", description="Spot copy role")
    spot_trader_inst_id: str = Field(default="", description="Spot copy inst ID")
    ip: str = Field(default="", description="IP restrictions")
    perm: str = Field(default="", description="API permissions")
    label: str = Field(default="", description="API key label")
    enable_spot_borrow: bool = Field(default=False, description="Spot borrow enabled")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> AccountConfig:
        """Create an AccountConfig from OKX API dict response.

        Args:
            data: Dict from OKX account config response.

        Returns:
            AccountConfig instance.
        """
        return cls(
            uid=data.get("uid", ""),
            acct_lv=data.get("acctLv", "1"),
            pos_mode=data.get("posMode", "net_mode"),
            auto_loan=data.get("autoLoan", "false").lower() == "true",
            greeks_type=data.get("greeksType", "PA"),
            level=data.get("level", ""),
            level_tmp=data.get("levelTmp", ""),
            ct_iso_mode=data.get("ctIsoMode", ""),
            mgn_iso_mode=data.get("mgnIsoMode", ""),
            spot_offset_type=data.get("spotOffsetType", ""),
            role_type=data.get("roleType", "0"),
            trader_inst_id=data.get("traderInstId", ""),
            spot_role_type=data.get("spotRoleType", "0"),
            spot_trader_inst_id=data.get("spotTraderInstId", ""),
            ip=data.get("ip", ""),
            perm=data.get("perm", ""),
            label=data.get("label", ""),
            enable_spot_borrow=data.get("enableSpotBorrow", "false").lower() == "true",
        )

    @property
    def is_simple_mode(self) -> bool:
        """Check if account is in simple (spot-only) mode."""
        return self.acct_lv == "1"

    @property
    def is_single_currency_margin(self) -> bool:
        """Check if account is in single-currency margin mode."""
        return self.acct_lv == "2"

    @property
    def is_multi_currency_margin(self) -> bool:
        """Check if account is in multi-currency margin mode."""
        return self.acct_lv == "3"

    @property
    def is_portfolio_margin(self) -> bool:
        """Check if account is in portfolio margin mode."""
        return self.acct_lv == "4"

    @property
    def is_net_mode(self) -> bool:
        """Check if using net position mode."""
        return self.pos_mode == "net_mode"

    @property
    def is_long_short_mode(self) -> bool:
        """Check if using long/short position mode."""
        return self.pos_mode == "long_short_mode"

    @property
    def account_mode_name(self) -> str:
        """Get human-readable account mode name."""
        modes = {
            "1": "Simple",
            "2": "Single-currency Margin",
            "3": "Multi-currency Margin",
            "4": "Portfolio Margin",
        }
        return modes.get(self.acct_lv, f"Unknown ({self.acct_lv})")
