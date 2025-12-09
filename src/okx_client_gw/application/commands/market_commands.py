"""Market data commands for OKX API.

Commands for fetching public market data including tickers, candles,
order books, and trades. These endpoints do not require authentication.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from okx_client_gw.application.commands.base import OkxQueryCommand
from okx_client_gw.core.exceptions import OkxValidationError
from okx_client_gw.domain.enums import Bar, InstType
from okx_client_gw.domain.models.candle import Candle
from okx_client_gw.domain.models.orderbook import OrderBook
from okx_client_gw.domain.models.ticker import Ticker
from okx_client_gw.domain.models.trade import Trade

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class GetTickersCommand(OkxQueryCommand[list[Ticker]]):
    """Get tickers for all instruments of a given type.

    API: GET /api/v5/market/tickers

    Example:
        cmd = GetTickersCommand(inst_type=InstType.SPOT)
        tickers = await cmd.invoke(client)
    """

    def __init__(self, inst_type: InstType) -> None:
        """Initialize command.

        Args:
            inst_type: Instrument type (SPOT, SWAP, FUTURES, OPTION)
        """
        self._inst_type = inst_type

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Ticker]:
        """Fetch tickers for all instruments of the given type.

        Args:
            client: OKX HTTP client

        Returns:
            List of Ticker objects
        """
        data = await client.get_data(
            "/api/v5/market/tickers",
            params={"instType": self._inst_type.value},
        )
        return [Ticker.from_okx_dict(item) for item in data]


class GetTickerCommand(OkxQueryCommand[Ticker]):
    """Get ticker for a single instrument.

    API: GET /api/v5/market/ticker

    Example:
        cmd = GetTickerCommand(inst_id="BTC-USDT")
        ticker = await cmd.invoke(client)
    """

    def __init__(self, inst_id: str) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT", "BTC-USDT-SWAP")
        """
        self._inst_id = inst_id

    async def invoke(self, client: OkxHttpClientProtocol) -> Ticker:
        """Fetch ticker for the instrument.

        Args:
            client: OKX HTTP client

        Returns:
            Ticker object

        Raises:
            OkxApiError: If instrument not found
        """
        data = await client.get_data(
            "/api/v5/market/ticker",
            params={"instId": self._inst_id},
        )
        return Ticker.from_okx_dict(data[0])


class GetCandlesCommand(OkxQueryCommand[list[Candle]]):
    """Get candlestick data for an instrument.

    API: GET /api/v5/market/candles

    Returns up to 300 candles per request. For historical data,
    use the `before` parameter to paginate backwards in time.

    OKX returns candles in reverse chronological order (newest first).

    Example:
        cmd = GetCandlesCommand(
            inst_id="BTC-USDT",
            bar=Bar.H1,
            limit=100,
        )
        candles = await cmd.invoke(client)
    """

    MAX_LIMIT = 300

    def __init__(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
        *,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int = 100,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT")
            bar: Candlestick granularity (default: 1H)
            before: Return candles before this time (pagination)
            after: Return candles after this time (filter)
            limit: Number of candles to return (max 300)

        Raises:
            OkxValidationError: If limit is out of range
        """
        if limit < 1 or limit > self.MAX_LIMIT:
            raise OkxValidationError(
                field="limit",
                value=str(limit),
                reason=f"Must be between 1 and {self.MAX_LIMIT}",
            )

        self._inst_id = inst_id
        self._bar = bar
        self._before = before
        self._after = after
        self._limit = limit

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Candle]:
        """Fetch candlestick data.

        Args:
            client: OKX HTTP client

        Returns:
            List of Candle objects (newest first)
        """
        params: dict[str, str] = {
            "instId": self._inst_id,
            "bar": self._bar.value if hasattr(self._bar, "value") else str(self._bar),
            "limit": str(self._limit),
        }

        if self._before:
            # OKX expects millisecond timestamps
            params["before"] = str(int(self._before.timestamp() * 1000))

        if self._after:
            params["after"] = str(int(self._after.timestamp() * 1000))

        data = await client.get_data("/api/v5/market/candles", params=params)
        return [Candle.from_okx_array(row) for row in data]


class GetHistoryCandlesCommand(OkxQueryCommand[list[Candle]]):
    """Get historical candlestick data (older than recent).

    API: GET /api/v5/market/history-candles

    For data older than what /market/candles provides.
    Same parameters and response format as GetCandlesCommand.
    """

    MAX_LIMIT = 100

    def __init__(
        self,
        inst_id: str,
        bar: Bar = Bar.H1,
        *,
        before: datetime | None = None,
        after: datetime | None = None,
        limit: int = 100,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            bar: Candlestick granularity
            before: Return candles before this time
            after: Return candles after this time
            limit: Number of candles (max 100 for history endpoint)
        """
        if limit < 1 or limit > self.MAX_LIMIT:
            raise OkxValidationError(
                field="limit",
                value=str(limit),
                reason=f"Must be between 1 and {self.MAX_LIMIT}",
            )

        self._inst_id = inst_id
        self._bar = bar
        self._before = before
        self._after = after
        self._limit = limit

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Candle]:
        """Fetch historical candlestick data.

        Args:
            client: OKX HTTP client

        Returns:
            List of Candle objects (newest first)
        """
        params: dict[str, str] = {
            "instId": self._inst_id,
            "bar": self._bar.value if hasattr(self._bar, "value") else str(self._bar),
            "limit": str(self._limit),
        }

        if self._before:
            params["before"] = str(int(self._before.timestamp() * 1000))

        if self._after:
            params["after"] = str(int(self._after.timestamp() * 1000))

        data = await client.get_data("/api/v5/market/history-candles", params=params)
        return [Candle.from_okx_array(row) for row in data]


class GetOrderBookCommand(OkxQueryCommand[OrderBook]):
    """Get order book for an instrument.

    API: GET /api/v5/market/books

    Example:
        cmd = GetOrderBookCommand(inst_id="BTC-USDT", depth=20)
        book = await cmd.invoke(client)
    """

    VALID_DEPTHS = {1, 5, 10, 20, 50, 100, 400}

    def __init__(
        self,
        inst_id: str,
        depth: int = 20,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            depth: Order book depth (1, 5, 20, 50, 100, or 400)

        Raises:
            OkxValidationError: If depth is not a valid value
        """
        if depth not in self.VALID_DEPTHS:
            raise OkxValidationError(
                field="depth",
                value=str(depth),
                reason=f"Must be one of {sorted(self.VALID_DEPTHS)}",
            )

        self._inst_id = inst_id
        self._depth = depth

    async def invoke(self, client: OkxHttpClientProtocol) -> OrderBook:
        """Fetch order book.

        Args:
            client: OKX HTTP client

        Returns:
            OrderBook object
        """
        data = await client.get_data(
            "/api/v5/market/books",
            params={
                "instId": self._inst_id,
                "sz": str(self._depth),
            },
        )
        return OrderBook.from_okx_dict(data[0], inst_id=self._inst_id)


class GetTradesCommand(OkxQueryCommand[list[Trade]]):
    """Get recent trades for an instrument.

    API: GET /api/v5/market/trades

    Example:
        cmd = GetTradesCommand(inst_id="BTC-USDT", limit=100)
        trades = await cmd.invoke(client)
    """

    MAX_LIMIT = 500

    def __init__(
        self,
        inst_id: str,
        limit: int = 100,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            limit: Number of trades to return (max 500)
        """
        if limit < 1 or limit > self.MAX_LIMIT:
            raise OkxValidationError(
                field="limit",
                value=str(limit),
                reason=f"Must be between 1 and {self.MAX_LIMIT}",
            )

        self._inst_id = inst_id
        self._limit = limit

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Trade]:
        """Fetch recent trades.

        Args:
            client: OKX HTTP client

        Returns:
            List of Trade objects (newest first)
        """
        data = await client.get_data(
            "/api/v5/market/trades",
            params={
                "instId": self._inst_id,
                "limit": str(self._limit),
            },
        )
        return [Trade.from_okx_dict(item) for item in data]
