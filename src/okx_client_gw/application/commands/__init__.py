"""Commands for OKX API operations."""

from okx_client_gw.application.commands.base import (
    OkxCommand,
    OkxMutationCommand,
    OkxQueryCommand,
)
from okx_client_gw.application.commands.instrument_commands import (
    GetInstrumentCommand,
    GetInstrumentsCommand,
)
from okx_client_gw.application.commands.market_commands import (
    GetCandlesCommand,
    GetHistoryCandlesCommand,
    GetOrderBookCommand,
    GetTickerCommand,
    GetTickersCommand,
    GetTradesCommand,
)

__all__ = [
    # Base classes
    "OkxCommand",
    "OkxQueryCommand",
    "OkxMutationCommand",
    # Instrument commands
    "GetInstrumentsCommand",
    "GetInstrumentCommand",
    # Market commands
    "GetTickersCommand",
    "GetTickerCommand",
    "GetCandlesCommand",
    "GetHistoryCandlesCommand",
    "GetOrderBookCommand",
    "GetTradesCommand",
]
