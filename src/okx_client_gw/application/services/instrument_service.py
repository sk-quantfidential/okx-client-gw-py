"""Instrument service for OKX API.

High-level service for fetching instrument information.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from okx_client_gw.application.commands.instrument_commands import (
    GetInstrumentCommand,
    GetInstrumentsCommand,
)
from okx_client_gw.domain.enums import InstType
from okx_client_gw.domain.models.instrument import Instrument

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class InstrumentService:
    """Service for fetching OKX instrument information.

    Example:
        async with OkxHttpClient() as client:
            service = InstrumentService(client)

            # Get all spot instruments
            instruments = await service.get_instruments(InstType.SPOT)

            # Get specific instrument
            btc = await service.get_instrument(InstType.SPOT, "BTC-USDT")
    """

    def __init__(self, client: OkxHttpClientProtocol) -> None:
        """Initialize instrument service.

        Args:
            client: OKX HTTP client
        """
        self._client = client

    async def get_instruments(
        self,
        inst_type: InstType,
        *,
        uly: str | None = None,
        inst_family: str | None = None,
    ) -> list[Instrument]:
        """Get all instruments of a given type.

        Args:
            inst_type: Instrument type (SPOT, SWAP, etc.)
            uly: Underlying filter (for derivatives)
            inst_family: Instrument family filter

        Returns:
            List of Instrument objects
        """
        cmd = GetInstrumentsCommand(
            inst_type,
            uly=uly,
            inst_family=inst_family,
        )
        return await cmd.invoke(self._client)

    async def get_instrument(
        self,
        inst_type: InstType,
        inst_id: str,
    ) -> Instrument:
        """Get a specific instrument.

        Args:
            inst_type: Instrument type
            inst_id: Instrument ID

        Returns:
            Instrument object
        """
        cmd = GetInstrumentCommand(inst_type, inst_id)
        return await cmd.invoke(self._client)

    async def get_spot_instruments(self) -> list[Instrument]:
        """Get all spot trading instruments.

        Returns:
            List of spot Instrument objects
        """
        return await self.get_instruments(InstType.SPOT)

    async def get_swap_instruments(
        self,
        uly: str | None = None,
    ) -> list[Instrument]:
        """Get all perpetual swap instruments.

        Args:
            uly: Filter by underlying (e.g., "BTC-USDT")

        Returns:
            List of swap Instrument objects
        """
        return await self.get_instruments(InstType.SWAP, uly=uly)

    async def get_futures_instruments(
        self,
        uly: str | None = None,
    ) -> list[Instrument]:
        """Get all futures instruments.

        Args:
            uly: Filter by underlying

        Returns:
            List of futures Instrument objects
        """
        return await self.get_instruments(InstType.FUTURES, uly=uly)

    async def get_option_instruments(
        self,
        uly: str | None = None,
        inst_family: str | None = None,
    ) -> list[Instrument]:
        """Get all option instruments.

        Args:
            uly: Filter by underlying
            inst_family: Filter by instrument family

        Returns:
            List of option Instrument objects
        """
        return await self.get_instruments(
            InstType.OPTION,
            uly=uly,
            inst_family=inst_family,
        )
