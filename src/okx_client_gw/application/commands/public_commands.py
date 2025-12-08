"""Public data commands for OKX API.

Commands for fetching additional public data including currencies,
discount rates, and funding rates. These are public endpoints that
do not require authentication.

See: https://www.okx.com/docs-v5/en/#public-data-rest-api
See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-discount-rate-and-interest-free-quota
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from okx_client_gw.application.commands.base import OkxQueryCommand

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class Currency(BaseModel):
    """Currency information.

    See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-currencies
    """

    ccy: str = Field(description="Currency name (e.g., BTC)")
    name: str = Field(description="Currency full name")
    chain: str = Field(default="", description="Chain name")
    can_dep: bool = Field(default=True, description="Can deposit")
    can_wd: bool = Field(default=True, description="Can withdraw")
    can_internal: bool = Field(default=True, description="Can internal transfer")
    min_dep: Decimal = Field(default=Decimal("0"), description="Minimum deposit")
    min_wd: Decimal = Field(default=Decimal("0"), description="Minimum withdrawal")
    max_wd: Decimal = Field(default=Decimal("0"), description="Maximum withdrawal")
    wd_tick_sz: str = Field(default="", description="Withdrawal precision")
    wd_quota: Decimal = Field(default=Decimal("0"), description="Withdrawal quota")
    used_wd_quota: Decimal = Field(default=Decimal("0"), description="Used quota")
    min_fee: Decimal = Field(default=Decimal("0"), description="Minimum fee")
    max_fee: Decimal = Field(default=Decimal("0"), description="Maximum fee")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> Currency:
        """Create Currency from OKX API response."""
        return cls(
            ccy=data.get("ccy", ""),
            name=data.get("name", ""),
            chain=data.get("chain", ""),
            can_dep=data.get("canDep", "true").lower() == "true",
            can_wd=data.get("canWd", "true").lower() == "true",
            can_internal=data.get("canInternal", "true").lower() == "true",
            min_dep=Decimal(data.get("minDep", "0") or "0"),
            min_wd=Decimal(data.get("minWd", "0") or "0"),
            max_wd=Decimal(data.get("maxWd", "0") or "0"),
            wd_tick_sz=data.get("wdTickSz", ""),
            wd_quota=Decimal(data.get("wdQuota", "0") or "0"),
            used_wd_quota=Decimal(data.get("usedWdQuota", "0") or "0"),
            min_fee=Decimal(data.get("minFee", "0") or "0"),
            max_fee=Decimal(data.get("maxFee", "0") or "0"),
        )


class DiscountInfo(BaseModel):
    """Discount rate information for a currency.

    Used in portfolio/multi-currency margin mode to determine
    collateral haircuts.
    """

    ccy: str = Field(description="Currency")
    amt: Decimal = Field(description="Amount")
    discount_lv: int = Field(default=1, description="Discount level")
    discount_rate: Decimal = Field(description="Discount rate (0-1)")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> DiscountInfo:
        """Create DiscountInfo from OKX API response."""
        return cls(
            ccy=data.get("ccy", ""),
            amt=Decimal(data.get("amt", "0") or "0"),
            discount_lv=int(data.get("discountLv", "1") or "1"),
            discount_rate=Decimal(data.get("discountRate", "1") or "1"),
        )


class DiscountRateResponse(BaseModel):
    """Complete discount rate response.

    Includes discount info for multiple currencies.
    """

    ccy: str = Field(description="Primary currency queried")
    discount_info: list[DiscountInfo] = Field(
        default_factory=list,
        description="Discount info by amount tier",
    )

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> DiscountRateResponse:
        """Create DiscountRateResponse from OKX API response."""
        discount_info = [
            DiscountInfo.from_okx_dict(item)
            for item in data.get("discountInfo", [])
        ]
        return cls(
            ccy=data.get("ccy", ""),
            discount_info=discount_info,
        )


class FundingRate(BaseModel):
    """Funding rate information for perpetual swaps.

    See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate
    """

    inst_id: str = Field(description="Instrument ID")
    inst_type: str = Field(description="Instrument type")
    funding_rate: Decimal = Field(description="Current funding rate")
    next_funding_rate: Decimal | None = Field(default=None, description="Predicted next rate")
    funding_time: datetime = Field(description="Current funding settlement time")
    next_funding_time: datetime | None = Field(default=None, description="Next funding time")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict) -> FundingRate:
        """Create FundingRate from OKX API response."""
        funding_time = datetime.fromtimestamp(
            int(data["fundingTime"]) / 1000, tz=UTC
        )

        next_funding_time = None
        if data.get("nextFundingTime"):
            next_funding_time = datetime.fromtimestamp(
                int(data["nextFundingTime"]) / 1000, tz=UTC
            )

        next_funding_rate = None
        if data.get("nextFundingRate") and data["nextFundingRate"] != "":
            next_funding_rate = Decimal(data["nextFundingRate"])

        return cls(
            inst_id=data["instId"],
            inst_type=data.get("instType", "SWAP"),
            funding_rate=Decimal(data["fundingRate"]),
            next_funding_rate=next_funding_rate,
            funding_time=funding_time,
            next_funding_time=next_funding_time,
        )


class GetCurrenciesCommand(OkxQueryCommand[list[Currency]]):
    """Get available currencies.

    API: GET /api/v5/asset/currencies (AUTH REQUIRED for full data)

    Note: This endpoint returns different data depending on authentication.
    Without auth, returns basic currency list. With auth, returns
    deposit/withdrawal details.

    Example:
        cmd = GetCurrenciesCommand()
        currencies = await cmd.invoke(client)
    """

    def __init__(self, ccy: str | None = None) -> None:
        """Initialize command.

        Args:
            ccy: Filter by currency (e.g., "BTC" or "BTC,ETH")
        """
        self._ccy = ccy

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Currency]:
        """Get currencies.

        Uses authenticated endpoint if credentials available,
        otherwise uses public endpoint with limited data.

        Args:
            client: OKX HTTP client

        Returns:
            List of Currency objects
        """
        params = {}
        if self._ccy:
            params["ccy"] = self._ccy

        # Try authenticated endpoint first, fall back to public
        if client.has_credentials:
            data = await client.get_data_auth(
                "/api/v5/asset/currencies",
                params=params if params else None,
            )
        else:
            data = await client.get_data(
                "/api/v5/asset/currencies",
                params=params if params else None,
            )

        return [Currency.from_okx_dict(item) for item in data]


class GetDiscountRateCommand(OkxQueryCommand[list[DiscountRateResponse]]):
    """Get discount rate and interest-free quota.

    API: GET /api/v5/public/discount-rate-interest-free-quota

    Returns discount rates (haircuts) for currencies when used as
    collateral in portfolio/multi-currency margin mode.

    Example:
        cmd = GetDiscountRateCommand(ccy="BTC")
        rates = await cmd.invoke(client)
        for rate in rates:
            print(f"{rate.ccy}: {rate.discount_info}")
    """

    def __init__(
        self,
        ccy: str | None = None,
        *,
        discount_lv: int | None = None,
    ) -> None:
        """Initialize command.

        Args:
            ccy: Filter by currency
            discount_lv: Filter by discount level (1-5)
        """
        self._ccy = ccy
        self._discount_lv = discount_lv

    async def invoke(
        self, client: OkxHttpClientProtocol
    ) -> list[DiscountRateResponse]:
        """Get discount rates.

        Args:
            client: OKX HTTP client

        Returns:
            List of DiscountRateResponse objects
        """
        params: dict[str, str] = {}
        if self._ccy:
            params["ccy"] = self._ccy
        if self._discount_lv:
            params["discountLv"] = str(self._discount_lv)

        data = await client.get_data(
            "/api/v5/public/discount-rate-interest-free-quota",
            params=params if params else None,
        )
        return [DiscountRateResponse.from_okx_dict(item) for item in data]


class GetFundingRateCommand(OkxQueryCommand[FundingRate]):
    """Get current funding rate for a perpetual swap.

    API: GET /api/v5/public/funding-rate

    Returns the current and predicted next funding rate.

    Example:
        cmd = GetFundingRateCommand(inst_id="BTC-USDT-SWAP")
        rate = await cmd.invoke(client)
        print(f"Funding rate: {rate.funding_rate}")
    """

    def __init__(self, inst_id: str) -> None:
        """Initialize command.

        Args:
            inst_id: Perpetual swap instrument ID (e.g., "BTC-USDT-SWAP")
        """
        self._inst_id = inst_id

    async def invoke(self, client: OkxHttpClientProtocol) -> FundingRate:
        """Get funding rate.

        Args:
            client: OKX HTTP client

        Returns:
            FundingRate object
        """
        data = await client.get_data(
            "/api/v5/public/funding-rate",
            params={"instId": self._inst_id},
        )
        return FundingRate.from_okx_dict(data[0])


class GetFundingRateHistoryCommand(OkxQueryCommand[list[FundingRate]]):
    """Get historical funding rates.

    API: GET /api/v5/public/funding-rate-history

    Returns historical funding rates for a perpetual swap.

    Example:
        cmd = GetFundingRateHistoryCommand(inst_id="BTC-USDT-SWAP", limit=100)
        rates = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_id: str,
        *,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int = 100,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Perpetual swap instrument ID
            before: Return rates before this time
            after: Return rates after this time
            limit: Maximum rates to return (max 100)
        """
        self._inst_id = inst_id
        self._before = before
        self._after = after
        self._limit = min(limit, 100)

    async def invoke(self, client: OkxHttpClientProtocol) -> list[FundingRate]:
        """Get funding rate history.

        Args:
            client: OKX HTTP client

        Returns:
            List of FundingRate objects
        """
        params: dict[str, str] = {
            "instId": self._inst_id,
            "limit": str(self._limit),
        }
        if self._before:
            params["before"] = str(int(self._before.timestamp() * 1000))
        if self._after:
            params["after"] = str(int(self._after.timestamp() * 1000))

        data = await client.get_data(
            "/api/v5/public/funding-rate-history",
            params=params,
        )
        return [FundingRate.from_okx_dict(item) for item in data]
