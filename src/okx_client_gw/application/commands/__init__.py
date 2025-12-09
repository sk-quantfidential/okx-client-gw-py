"""Commands for OKX API operations."""

from okx_client_gw.application.commands.account_commands import (
    GetAccountBalanceCommand,
    GetAccountConfigCommand,
    GetAccountPositionsCommand,
    GetMaxAvailableSizeCommand,
    SetLeverageCommand,
    SetPositionModeCommand,
)
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
from okx_client_gw.application.commands.public_commands import (
    Currency,
    DiscountInfo,
    DiscountRateResponse,
    FundingRate,
    GetCurrenciesCommand,
    GetDiscountRateCommand,
    GetFundingRateCommand,
    GetFundingRateHistoryCommand,
)
from okx_client_gw.application.commands.trade_commands import (
    AmendOrderCommand,
    CancelBatchOrdersCommand,
    CancelOrderCommand,
    GetOrderCommand,
    GetOrderHistoryCommand,
    GetPendingOrdersCommand,
    PlaceOrderCommand,
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
    # Account commands
    "GetAccountBalanceCommand",
    "GetAccountPositionsCommand",
    "GetAccountConfigCommand",
    "SetLeverageCommand",
    "SetPositionModeCommand",
    "GetMaxAvailableSizeCommand",
    # Trade commands
    "PlaceOrderCommand",
    "CancelOrderCommand",
    "GetOrderCommand",
    "GetPendingOrdersCommand",
    "GetOrderHistoryCommand",
    "AmendOrderCommand",
    "CancelBatchOrdersCommand",
    # Public data commands
    "GetCurrenciesCommand",
    "GetDiscountRateCommand",
    "GetFundingRateCommand",
    "GetFundingRateHistoryCommand",
    # Public data models
    "Currency",
    "DiscountInfo",
    "DiscountRateResponse",
    "FundingRate",
]
