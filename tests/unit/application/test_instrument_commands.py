"""Unit tests for instrument commands with respx mocking."""

from __future__ import annotations

from decimal import Decimal

import pytest
import respx
from httpx import Response

from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.application.commands.instrument_commands import (
    GetInstrumentCommand,
    GetInstrumentsCommand,
)
from okx_client_gw.domain.enums import InstType


class TestGetInstrumentsCommand:
    """Tests for GetInstrumentsCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_instruments_spot(self) -> None:
        """Test fetching spot instruments."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SPOT",
                    "instId": "BTC-USDT",
                    "uly": "",
                    "instFamily": "",
                    "baseCcy": "BTC",
                    "quoteCcy": "USDT",
                    "settleCcy": "",
                    "ctVal": "",
                    "ctMult": "",
                    "ctValCcy": "",
                    "optType": "",
                    "stk": "",
                    "listTime": "1548133200000",
                    "expTime": "",
                    "lever": "",
                    "tickSz": "0.1",
                    "lotSz": "0.00001",
                    "minSz": "0.00001",
                    "ctType": "",
                    "alias": "",
                    "state": "live",
                    "maxLmtSz": "10000",
                    "maxMktSz": "1000",
                    "maxTwapSz": "",
                    "maxIcebergSz": "",
                    "maxTriggerSz": "",
                    "maxStopSz": "",
                },
                {
                    "instType": "SPOT",
                    "instId": "ETH-USDT",
                    "uly": "",
                    "instFamily": "",
                    "baseCcy": "ETH",
                    "quoteCcy": "USDT",
                    "settleCcy": "",
                    "ctVal": "",
                    "ctMult": "",
                    "ctValCcy": "",
                    "optType": "",
                    "stk": "",
                    "listTime": "1548133200000",
                    "expTime": "",
                    "lever": "",
                    "tickSz": "0.01",
                    "lotSz": "0.0001",
                    "minSz": "0.0001",
                    "ctType": "",
                    "alias": "",
                    "state": "live",
                    "maxLmtSz": "50000",
                    "maxMktSz": "5000",
                    "maxTwapSz": "",
                    "maxIcebergSz": "",
                    "maxTriggerSz": "",
                    "maxStopSz": "",
                },
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentsCommand(InstType.SPOT)
            instruments = await cmd.invoke(client)

        assert len(instruments) == 2
        assert instruments[0].inst_id == "BTC-USDT"
        assert instruments[0].base_ccy == "BTC"
        assert instruments[0].quote_ccy == "USDT"
        assert instruments[0].tick_sz == Decimal("0.1")
        assert instruments[0].state == "live"
        assert route.calls[0].request.url.params["instType"] == "SPOT"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_instruments_swap(self) -> None:
        """Test fetching perpetual swap instruments."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SWAP",
                    "instId": "BTC-USDT-SWAP",
                    "uly": "BTC-USDT",
                    "instFamily": "BTC-USDT",
                    "baseCcy": "",
                    "quoteCcy": "",
                    "settleCcy": "USDT",
                    "ctVal": "0.01",
                    "ctMult": "1",
                    "ctValCcy": "BTC",
                    "optType": "",
                    "stk": "",
                    "listTime": "1548133200000",
                    "expTime": "",
                    "lever": "125",
                    "tickSz": "0.1",
                    "lotSz": "1",
                    "minSz": "1",
                    "ctType": "linear",
                    "alias": "",
                    "state": "live",
                    "maxLmtSz": "100000",
                    "maxMktSz": "10000",
                    "maxTwapSz": "50000",
                    "maxIcebergSz": "50000",
                    "maxTriggerSz": "50000",
                    "maxStopSz": "50000",
                },
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentsCommand(InstType.SWAP)
            instruments = await cmd.invoke(client)

        assert len(instruments) == 1
        assert instruments[0].inst_id == "BTC-USDT-SWAP"
        assert instruments[0].inst_type == InstType.SWAP
        assert instruments[0].ct_val == Decimal("0.01")
        assert instruments[0].settle_ccy == "USDT"
        assert route.calls[0].request.url.params["instType"] == "SWAP"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_instruments_with_uly_filter(self) -> None:
        """Test fetching instruments with underlying filter."""
        mock_response = {"code": "0", "msg": "", "data": []}

        route = respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentsCommand(InstType.FUTURES, uly="BTC-USDT")
            await cmd.invoke(client)

        params = route.calls[0].request.url.params
        assert params["instType"] == "FUTURES"
        assert params["uly"] == "BTC-USDT"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_instruments_with_inst_family(self) -> None:
        """Test fetching instruments with instrument family filter."""
        mock_response = {"code": "0", "msg": "", "data": []}

        route = respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentsCommand(InstType.OPTION, inst_family="BTC-USD")
            await cmd.invoke(client)

        params = route.calls[0].request.url.params
        assert params["instType"] == "OPTION"
        assert params["instFamily"] == "BTC-USD"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_instruments_with_inst_id_filter(self) -> None:
        """Test fetching instruments with specific instrument ID filter."""
        mock_response = {"code": "0", "msg": "", "data": []}

        route = respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentsCommand(InstType.SPOT, inst_id="BTC-USDT")
            await cmd.invoke(client)

        params = route.calls[0].request.url.params
        assert params["instType"] == "SPOT"
        assert params["instId"] == "BTC-USDT"


class TestGetInstrumentCommand:
    """Tests for GetInstrumentCommand."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_single_instrument(self) -> None:
        """Test fetching a single instrument by ID."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SPOT",
                    "instId": "BTC-USDT",
                    "uly": "",
                    "instFamily": "",
                    "baseCcy": "BTC",
                    "quoteCcy": "USDT",
                    "settleCcy": "",
                    "ctVal": "",
                    "ctMult": "",
                    "ctValCcy": "",
                    "optType": "",
                    "stk": "",
                    "listTime": "1548133200000",
                    "expTime": "",
                    "lever": "",
                    "tickSz": "0.1",
                    "lotSz": "0.00001",
                    "minSz": "0.00001",
                    "ctType": "",
                    "alias": "",
                    "state": "live",
                    "maxLmtSz": "10000",
                    "maxMktSz": "1000",
                    "maxTwapSz": "",
                    "maxIcebergSz": "",
                    "maxTriggerSz": "",
                    "maxStopSz": "",
                },
            ],
        }

        route = respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentCommand(InstType.SPOT, "BTC-USDT")
            instrument = await cmd.invoke(client)

        assert instrument.inst_id == "BTC-USDT"
        assert instrument.inst_type == InstType.SPOT
        assert instrument.base_ccy == "BTC"

        params = route.calls[0].request.url.params
        assert params["instType"] == "SPOT"
        assert params["instId"] == "BTC-USDT"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_swap_instrument(self) -> None:
        """Test fetching a swap instrument."""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SWAP",
                    "instId": "ETH-USDT-SWAP",
                    "uly": "ETH-USDT",
                    "instFamily": "ETH-USDT",
                    "baseCcy": "",
                    "quoteCcy": "",
                    "settleCcy": "USDT",
                    "ctVal": "0.1",
                    "ctMult": "1",
                    "ctValCcy": "ETH",
                    "optType": "",
                    "stk": "",
                    "listTime": "1548133200000",
                    "expTime": "",
                    "lever": "100",
                    "tickSz": "0.01",
                    "lotSz": "1",
                    "minSz": "1",
                    "ctType": "linear",
                    "alias": "",
                    "state": "live",
                    "maxLmtSz": "100000",
                    "maxMktSz": "10000",
                    "maxTwapSz": "50000",
                    "maxIcebergSz": "50000",
                    "maxTriggerSz": "50000",
                    "maxStopSz": "50000",
                },
            ],
        }

        respx.get("https://www.okx.com/api/v5/public/instruments").mock(
            return_value=Response(200, json=mock_response)
        )

        async with OkxHttpClient() as client:
            cmd = GetInstrumentCommand(InstType.SWAP, "ETH-USDT-SWAP")
            instrument = await cmd.invoke(client)

        assert instrument.inst_id == "ETH-USDT-SWAP"
        assert instrument.inst_type == InstType.SWAP
        assert instrument.uly == "ETH-USDT"
        assert instrument.ct_val == Decimal("0.1")
