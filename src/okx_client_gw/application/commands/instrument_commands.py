"""Instrument commands for OKX API.

Commands for fetching instrument information. These endpoints
do not require authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from okx_client_gw.application.commands.base import OkxQueryCommand
from okx_client_gw.domain.enums import InstType
from okx_client_gw.domain.models.instrument import Instrument

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class GetInstrumentsCommand(OkxQueryCommand[list[Instrument]]):
    """Get all instruments of a given type.

    API: GET /api/v5/public/instruments

    Example:
        cmd = GetInstrumentsCommand(inst_type=InstType.SPOT)
        instruments = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_type: InstType,
        *,
        uly: str | None = None,
        inst_family: str | None = None,
        inst_id: str | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_type: Instrument type (SPOT, SWAP, FUTURES, OPTION, MARGIN)
            uly: Underlying (e.g., "BTC-USDT") - for derivatives
            inst_family: Instrument family (e.g., "BTC-USDT")
            inst_id: Specific instrument ID to filter
        """
        self._inst_type = inst_type
        self._uly = uly
        self._inst_family = inst_family
        self._inst_id = inst_id

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Instrument]:
        """Fetch instruments.

        Args:
            client: OKX HTTP client

        Returns:
            List of Instrument objects
        """
        params: dict[str, str] = {"instType": self._inst_type.value}

        if self._uly:
            params["uly"] = self._uly

        if self._inst_family:
            params["instFamily"] = self._inst_family

        if self._inst_id:
            params["instId"] = self._inst_id

        data = await client.get_data("/api/v5/public/instruments", params=params)
        return [Instrument.from_okx_dict(item) for item in data]


class GetInstrumentCommand(OkxQueryCommand[Instrument]):
    """Get a single instrument by ID.

    API: GET /api/v5/public/instruments

    Example:
        cmd = GetInstrumentCommand(inst_type=InstType.SPOT, inst_id="BTC-USDT")
        instrument = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_type: InstType,
        inst_id: str,
    ) -> None:
        """Initialize command.

        Args:
            inst_type: Instrument type
            inst_id: Instrument ID
        """
        self._inst_type = inst_type
        self._inst_id = inst_id

    async def invoke(self, client: OkxHttpClientProtocol) -> Instrument:
        """Fetch instrument.

        Args:
            client: OKX HTTP client

        Returns:
            Instrument object

        Raises:
            OkxApiError: If instrument not found
        """
        data = await client.get_data(
            "/api/v5/public/instruments",
            params={
                "instType": self._inst_type.value,
                "instId": self._inst_id,
            },
        )
        return Instrument.from_okx_dict(data[0])
