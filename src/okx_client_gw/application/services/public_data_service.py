"""Public data service for OKX API.

High-level service for fetching additional public data including
currencies, discount rates, and funding rates.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from okx_client_gw.application.commands.public_commands import (
    Currency,
    DiscountRateResponse,
    FundingRate,
    GetCurrenciesCommand,
    GetDiscountRateCommand,
    GetFundingRateCommand,
    GetFundingRateHistoryCommand,
)

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class PublicDataService:
    """Service for OKX public data operations.

    Provides high-level methods for fetching currencies, discount rates,
    and funding rates. Most methods do not require authentication.

    Example:
        async with OkxHttpClient() as client:
            service = PublicDataService(client)

            # Get currencies
            currencies = await service.get_currencies()

            # Get funding rate
            rate = await service.get_funding_rate("BTC-USDT-SWAP")
            print(f"Funding rate: {rate.funding_rate}")
    """

    def __init__(self, client: OkxHttpClientProtocol) -> None:
        """Initialize public data service.

        Args:
            client: OKX HTTP client (injected dependency)
        """
        self._client = client

    async def get_currencies(self, ccy: str | None = None) -> list[Currency]:
        """Get available currencies.

        Note: Returns more data if credentials are configured.

        Args:
            ccy: Filter by currency (e.g., "BTC" or "BTC,ETH")

        Returns:
            List of Currency objects
        """
        cmd = GetCurrenciesCommand(ccy)
        return await cmd.invoke(self._client)

    async def get_currency(self, ccy: str) -> Currency | None:
        """Get info for a specific currency.

        Args:
            ccy: Currency name (e.g., "BTC")

        Returns:
            Currency object or None if not found
        """
        currencies = await self.get_currencies(ccy)
        return currencies[0] if currencies else None

    async def get_discount_rates(
        self,
        ccy: str | None = None,
        discount_lv: int | None = None,
    ) -> list[DiscountRateResponse]:
        """Get discount rates (collateral haircuts).

        Used in portfolio/multi-currency margin mode to determine
        how much equity each currency provides as collateral.

        Args:
            ccy: Filter by currency
            discount_lv: Filter by discount level (1-5)

        Returns:
            List of DiscountRateResponse objects
        """
        cmd = GetDiscountRateCommand(ccy, discount_lv=discount_lv)
        return await cmd.invoke(self._client)

    async def get_discount_rate(self, ccy: str) -> DiscountRateResponse | None:
        """Get discount rate for a specific currency.

        Args:
            ccy: Currency name (e.g., "BTC")

        Returns:
            DiscountRateResponse or None if not found
        """
        rates = await self.get_discount_rates(ccy)
        return rates[0] if rates else None

    async def get_funding_rate(self, inst_id: str) -> FundingRate:
        """Get current funding rate for a perpetual swap.

        Args:
            inst_id: Perpetual swap instrument ID (e.g., "BTC-USDT-SWAP")

        Returns:
            FundingRate object with current and predicted next rate
        """
        cmd = GetFundingRateCommand(inst_id)
        return await cmd.invoke(self._client)

    async def get_funding_rate_history(
        self,
        inst_id: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        """Get historical funding rates.

        Args:
            inst_id: Perpetual swap instrument ID
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum rates to return (max 100)

        Returns:
            List of FundingRate objects (newest first)
        """
        cmd = GetFundingRateHistoryCommand(
            inst_id,
            before=end_date,
            after=start_date,
            limit=limit,
        )
        return await cmd.invoke(self._client)

    async def get_funding_rate_annualized(self, inst_id: str) -> float:
        """Get annualized funding rate.

        OKX funding occurs every 8 hours (3x daily).
        Annualized = rate * 3 * 365

        Args:
            inst_id: Perpetual swap instrument ID

        Returns:
            Annualized funding rate as float (e.g., 0.1 = 10%)
        """
        rate = await self.get_funding_rate(inst_id)
        return float(rate.funding_rate) * 3 * 365

    async def get_all_discount_rates(self) -> dict[str, float]:
        """Get discount rates for all currencies.

        Returns:
            Dict mapping currency to its primary discount rate
        """
        all_rates = await self.get_discount_rates()
        result = {}
        for response in all_rates:
            if response.discount_info:
                # Use the first tier discount rate
                result[response.ccy] = float(response.discount_info[0].discount_rate)
        return result
