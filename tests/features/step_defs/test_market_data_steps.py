"""BDD step definitions for market data feature.

Uses pytest-bdd with asyncio.run() to execute async code in step functions.

@package: tests.features.step_defs
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from okx_client_gw.application.commands.instrument_commands import (
    GetInstrumentsCommand,
)
from okx_client_gw.application.commands.market_commands import (
    GetCandlesCommand,
    GetOrderBookCommand,
    GetTickerCommand,
    GetTickersCommand,
    GetTradesCommand,
)
from okx_client_gw.core.exceptions import OkxValidationError
from okx_client_gw.domain.enums import Bar, InstType


# Scenarios
@scenario("../market_data.feature", "Fetch ticker for a spot instrument")
def test_fetch_ticker():
    pass


@scenario("../market_data.feature", "Fetch multiple tickers for SPOT instruments")
def test_fetch_tickers():
    pass


@scenario("../market_data.feature", "Fetch candlestick data")
def test_fetch_candles():
    pass


@scenario("../market_data.feature", "Fetch order book")
def test_fetch_orderbook():
    pass


@scenario("../market_data.feature", "Fetch recent trades")
def test_fetch_trades():
    pass


@scenario("../market_data.feature", "Fetch SPOT instruments")
def test_fetch_instruments():
    pass


@scenario("../market_data.feature", "Validate candle limit parameter")
def test_validate_candle_limit():
    pass


# Fixtures
@pytest.fixture
def context():
    """Shared context for step data."""
    return {
        "mock_client": None,
        "result": None,
        "error": None,
    }


# Sample response data
SAMPLE_TICKER = {
    "instType": "SPOT",
    "instId": "BTC-USDT",
    "last": "50000.5",
    "lastSz": "0.1",
    "askPx": "50001.0",
    "askSz": "1.5",
    "bidPx": "50000.0",
    "bidSz": "2.0",
    "open24h": "49000.0",
    "high24h": "51000.0",
    "low24h": "48500.0",
    "volCcy24h": "100000000.0",
    "vol24h": "2000.0",
    "ts": "1704067200000",
}

SAMPLE_CANDLE = ["1704067200000", "50000.0", "51000.0", "49500.0", "50500.0", "100.0", "5000000.0", "5025000.0", "1"]

SAMPLE_ORDERBOOK = {
    "bids": [
        ["50000.0", "1.5", "0", "3"],
        ["49999.0", "2.0", "0", "5"],
    ],
    "asks": [
        ["50001.0", "1.0", "0", "2"],
        ["50002.0", "3.0", "0", "4"],
    ],
    "ts": "1704067200000",
}

SAMPLE_TRADE = {
    "instId": "BTC-USDT",
    "tradeId": "123456",
    "px": "50000.0",
    "sz": "0.5",
    "side": "buy",
    "ts": "1704067200000",
}

SAMPLE_INSTRUMENT = {
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
}


# Given steps
@given("a mock OKX HTTP client", target_fixture="mock_client")
def given_mock_client(context):
    """Create a mock HTTP client."""
    mock = MagicMock()
    mock.get_data = AsyncMock()
    context["mock_client"] = mock
    return mock


@given(parsers.parse('the mock returns a valid ticker response for "{inst_id}"'))
def given_mock_ticker_response(mock_client, inst_id, context):
    """Configure mock to return ticker response."""
    response = dict(SAMPLE_TICKER)
    response["instId"] = inst_id
    mock_client.get_data.return_value = [response]


@given("the mock returns multiple SPOT tickers")
def given_mock_multiple_tickers(mock_client, context):
    """Configure mock to return multiple tickers."""
    tickers = [
        dict(SAMPLE_TICKER),
        {**SAMPLE_TICKER, "instId": "ETH-USDT", "last": "3000.0"},
    ]
    mock_client.get_data.return_value = tickers


@given(parsers.parse('the mock returns candlestick data for "{inst_id}"'))
def given_mock_candle_response(mock_client, inst_id, context):
    """Configure mock to return candlestick data."""
    mock_client.get_data.return_value = [SAMPLE_CANDLE, SAMPLE_CANDLE]


@given(parsers.parse('the mock returns order book data for "{inst_id}"'))
def given_mock_orderbook_response(mock_client, inst_id, context):
    """Configure mock to return order book data."""
    orderbook = dict(SAMPLE_ORDERBOOK)
    mock_client.get_data.return_value = [orderbook]


@given(parsers.parse('the mock returns recent trades for "{inst_id}"'))
def given_mock_trades_response(mock_client, inst_id, context):
    """Configure mock to return trades data."""
    trades = [
        dict(SAMPLE_TRADE),
        {**SAMPLE_TRADE, "tradeId": "123457", "side": "sell"},
    ]
    mock_client.get_data.return_value = trades


@given("the mock returns SPOT instruments")
def given_mock_instruments_response(mock_client, context):
    """Configure mock to return instruments."""
    instruments = [
        dict(SAMPLE_INSTRUMENT),
        {**SAMPLE_INSTRUMENT, "instId": "ETH-USDT", "baseCcy": "ETH"},
    ]
    mock_client.get_data.return_value = instruments


# When steps
@when(parsers.parse('I invoke GetTickerCommand for "{inst_id}"'))
def when_invoke_ticker_command(mock_client, inst_id, context):
    """Execute GetTickerCommand."""
    async def _run():
        cmd = GetTickerCommand(inst_id)
        context["result"] = await cmd.invoke(mock_client)

    asyncio.run(_run())


@when("I invoke GetTickersCommand for SPOT instruments")
def when_invoke_tickers_command(mock_client, context):
    """Execute GetTickersCommand."""
    async def _run():
        cmd = GetTickersCommand(InstType.SPOT)
        context["result"] = await cmd.invoke(mock_client)

    asyncio.run(_run())


@when(parsers.parse('I invoke GetCandlesCommand for "{inst_id}" with 1H bars'))
def when_invoke_candles_command(mock_client, inst_id, context):
    """Execute GetCandlesCommand."""
    async def _run():
        cmd = GetCandlesCommand(inst_id, Bar.H1)
        context["result"] = await cmd.invoke(mock_client)

    asyncio.run(_run())


@when(parsers.parse('I invoke GetOrderBookCommand for "{inst_id}"'))
def when_invoke_orderbook_command(mock_client, inst_id, context):
    """Execute GetOrderBookCommand."""
    async def _run():
        cmd = GetOrderBookCommand(inst_id)
        context["result"] = await cmd.invoke(mock_client)

    asyncio.run(_run())


@when(parsers.parse('I invoke GetTradesCommand for "{inst_id}"'))
def when_invoke_trades_command(mock_client, inst_id, context):
    """Execute GetTradesCommand."""
    async def _run():
        cmd = GetTradesCommand(inst_id)
        context["result"] = await cmd.invoke(mock_client)

    asyncio.run(_run())


@when("I invoke GetInstrumentsCommand for SPOT")
def when_invoke_instruments_command(mock_client, context):
    """Execute GetInstrumentsCommand."""
    async def _run():
        cmd = GetInstrumentsCommand(InstType.SPOT)
        context["result"] = await cmd.invoke(mock_client)

    asyncio.run(_run())


@when(parsers.parse("I try to create GetCandlesCommand with limit {limit:d}"))
def when_create_candles_command_invalid(limit, context):
    """Try to create GetCandlesCommand with invalid limit."""
    try:
        GetCandlesCommand("BTC-USDT", limit=limit)
    except OkxValidationError as e:
        context["error"] = e


# Then steps
@then(parsers.parse('the ticker should have instrument ID "{inst_id}"'))
def then_ticker_has_inst_id(context, inst_id):
    """Verify ticker instrument ID."""
    assert context["result"].inst_id == inst_id


@then("the ticker last price should be greater than 0")
def then_ticker_price_positive(context):
    """Verify ticker price is positive."""
    assert context["result"].last > 0


@then("I should receive a list of tickers")
def then_receive_ticker_list(context):
    """Verify tickers is a list."""
    assert isinstance(context["result"], list)
    assert len(context["result"]) > 0


@then("all tickers should have valid prices")
def then_all_tickers_valid_prices(context):
    """Verify all tickers have valid prices."""
    for ticker in context["result"]:
        assert ticker.last > 0
        assert ticker.bid_px > 0
        assert ticker.ask_px > 0


@then("I should receive a list of candles")
def then_receive_candle_list(context):
    """Verify candles is a list."""
    assert isinstance(context["result"], list)
    assert len(context["result"]) > 0


@then("each candle should have valid OHLCV data")
def then_candles_valid_ohlcv(context):
    """Verify all candles have valid OHLCV data."""
    for candle in context["result"]:
        assert candle.open > 0
        assert candle.high > 0
        assert candle.low > 0
        assert candle.close > 0
        assert candle.volume >= 0
        assert candle.high >= candle.low
        assert candle.high >= candle.open
        assert candle.high >= candle.close


@then("the order book should have bids and asks")
def then_orderbook_has_bids_asks(context):
    """Verify order book has bids and asks."""
    orderbook = context["result"]
    assert len(orderbook.bids) > 0
    assert len(orderbook.asks) > 0


@then("the best ask price should be greater than the best bid price")
def then_ask_greater_than_bid(context):
    """Verify ask > bid."""
    orderbook = context["result"]
    assert orderbook.best_ask_price > orderbook.best_bid_price


@then("I should receive a list of trades")
def then_receive_trade_list(context):
    """Verify trades is a list."""
    assert isinstance(context["result"], list)
    assert len(context["result"]) > 0


@then("each trade should have a price and size")
def then_trades_have_price_size(context):
    """Verify all trades have price and size."""
    for trade in context["result"]:
        assert trade.px > 0
        assert trade.sz > 0


@then("I should receive a list of instruments")
def then_receive_instrument_list(context):
    """Verify instruments is a list."""
    assert isinstance(context["result"], list)
    assert len(context["result"]) > 0


@then("all instruments should be of type SPOT")
def then_all_instruments_spot(context):
    """Verify all instruments are SPOT type."""
    for instrument in context["result"]:
        assert instrument.inst_type == InstType.SPOT


@then("a validation error should be raised")
def then_validation_error_raised(context):
    """Verify validation error was raised."""
    assert context["error"] is not None
    assert isinstance(context["error"], OkxValidationError)


@then("the error should mention the limit field")
def then_error_mentions_limit(context):
    """Verify error message mentions limit."""
    assert context["error"].field == "limit"
