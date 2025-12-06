"""Domain enums for OKX market data types."""

from enum import Enum


class InstType(str, Enum):
    """OKX instrument types.

    See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments
    """

    SPOT = "SPOT"
    MARGIN = "MARGIN"
    SWAP = "SWAP"
    FUTURES = "FUTURES"
    OPTION = "OPTION"


class Bar(str, Enum):
    """OKX candlestick granularities.

    See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks

    Note: UTC-based bars (e.g., 6Hutc) align to UTC midnight.
    Non-UTC bars align to Hong Kong time (UTC+8).
    """

    # Minute bars
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"

    # Hour bars (Hong Kong time aligned)
    H1 = "1H"
    H2 = "2H"
    H4 = "4H"

    # Hour bars (UTC aligned)
    H6_UTC = "6Hutc"
    H12_UTC = "12Hutc"

    # Day/Week/Month bars (UTC aligned)
    D1_UTC = "1Dutc"
    W1_UTC = "1Wutc"
    M1_UTC = "1Mutc"

    # Day/Week/Month bars (Hong Kong time aligned)
    D1 = "1D"
    W1 = "1W"
    M1_MONTH = "1M"

    @classmethod
    def from_seconds(cls, seconds: int) -> "Bar":
        """Get Bar enum from seconds.

        Args:
            seconds: Number of seconds in the bar period.

        Returns:
            Corresponding Bar enum value.

        Raises:
            ValueError: If seconds doesn't match a valid bar period.
        """
        mapping = {
            60: cls.M1,
            180: cls.M3,
            300: cls.M5,
            900: cls.M15,
            1800: cls.M30,
            3600: cls.H1,
            7200: cls.H2,
            14400: cls.H4,
            21600: cls.H6_UTC,
            43200: cls.H12_UTC,
            86400: cls.D1_UTC,
            604800: cls.W1_UTC,
        }
        if seconds not in mapping:
            valid = sorted(mapping.keys())
            raise ValueError(f"Invalid bar seconds: {seconds}. Valid values: {valid}")
        return mapping[seconds]

    @property
    def seconds(self) -> int:
        """Get the number of seconds in this bar period."""
        mapping = {
            self.M1: 60,
            self.M3: 180,
            self.M5: 300,
            self.M15: 900,
            self.M30: 1800,
            self.H1: 3600,
            self.H2: 7200,
            self.H4: 14400,
            self.H6_UTC: 21600,
            self.H12_UTC: 43200,
            self.D1_UTC: 86400,
            self.D1: 86400,
            self.W1_UTC: 604800,
            self.W1: 604800,
            self.M1_UTC: 2592000,  # Approximate (30 days)
            self.M1_MONTH: 2592000,
        }
        return mapping[self]


class ChannelType(str, Enum):
    """OKX WebSocket channel types.

    See: https://www.okx.com/docs-v5/en/#websocket-api-public-channel
    """

    # Public channels
    TICKERS = "tickers"
    TRADES = "trades"
    BOOKS = "books"  # Order book snapshot
    BOOKS5 = "books5"  # 5-level order book
    BOOKS50_TBT = "books50-l2-tbt"  # 50-level order book, tick-by-tick
    BOOKS_L2_TBT = "books-l2-tbt"  # 400-level order book, tick-by-tick
    BBO_TBT = "bbo-tbt"  # Best bid/offer, tick-by-tick

    # Candlestick channels (prefixed with "candle")
    CANDLE_1M = "candle1m"
    CANDLE_3M = "candle3m"
    CANDLE_5M = "candle5m"
    CANDLE_15M = "candle15m"
    CANDLE_30M = "candle30m"
    CANDLE_1H = "candle1H"
    CANDLE_2H = "candle2H"
    CANDLE_4H = "candle4H"
    CANDLE_6H_UTC = "candle6Hutc"
    CANDLE_12H_UTC = "candle12Hutc"
    CANDLE_1D_UTC = "candle1Dutc"
    CANDLE_1W_UTC = "candle1Wutc"
    CANDLE_1M_UTC = "candle1Mutc"

    @classmethod
    def candle_channel(cls, bar: Bar) -> "ChannelType":
        """Get the candle channel for a given bar granularity."""
        mapping = {
            Bar.M1: cls.CANDLE_1M,
            Bar.M3: cls.CANDLE_3M,
            Bar.M5: cls.CANDLE_5M,
            Bar.M15: cls.CANDLE_15M,
            Bar.M30: cls.CANDLE_30M,
            Bar.H1: cls.CANDLE_1H,
            Bar.H2: cls.CANDLE_2H,
            Bar.H4: cls.CANDLE_4H,
            Bar.H6_UTC: cls.CANDLE_6H_UTC,
            Bar.H12_UTC: cls.CANDLE_12H_UTC,
            Bar.D1_UTC: cls.CANDLE_1D_UTC,
            Bar.W1_UTC: cls.CANDLE_1W_UTC,
            Bar.M1_UTC: cls.CANDLE_1M_UTC,
        }
        if bar not in mapping:
            raise ValueError(f"No candle channel for bar: {bar}")
        return mapping[bar]


class TradeSide(str, Enum):
    """Trade side (buy or sell)."""

    BUY = "buy"
    SELL = "sell"


class OrderBookAction(str, Enum):
    """Order book update action type."""

    SNAPSHOT = "snapshot"
    UPDATE = "update"
