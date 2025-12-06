"""Tests for domain enums."""

import pytest

from okx_client_gw.domain.enums import Bar, ChannelType, InstType


class TestInstType:
    """Tests for InstType enum."""

    def test_all_types_exist(self):
        assert InstType.SPOT == "SPOT"
        assert InstType.MARGIN == "MARGIN"
        assert InstType.SWAP == "SWAP"
        assert InstType.FUTURES == "FUTURES"
        assert InstType.OPTION == "OPTION"

    def test_string_value(self):
        assert InstType.SPOT.value == "SPOT"
        assert InstType.SWAP.value == "SWAP"


class TestBar:
    """Tests for Bar enum."""

    def test_minute_bars(self):
        assert Bar.M1.value == "1m"
        assert Bar.M5.value == "5m"
        assert Bar.M15.value == "15m"
        assert Bar.M30.value == "30m"

    def test_hour_bars(self):
        assert Bar.H1.value == "1H"
        assert Bar.H4.value == "4H"
        assert Bar.H6_UTC.value == "6Hutc"

    def test_from_seconds(self):
        assert Bar.from_seconds(60) == Bar.M1
        assert Bar.from_seconds(300) == Bar.M5
        assert Bar.from_seconds(3600) == Bar.H1
        assert Bar.from_seconds(86400) == Bar.D1_UTC

    def test_from_seconds_invalid(self):
        with pytest.raises(ValueError, match="Invalid bar seconds"):
            Bar.from_seconds(123)

    def test_seconds_property(self):
        assert Bar.M1.seconds == 60
        assert Bar.H1.seconds == 3600
        assert Bar.D1_UTC.seconds == 86400


class TestChannelType:
    """Tests for ChannelType enum."""

    def test_public_channels(self):
        assert ChannelType.TICKERS.value == "tickers"
        assert ChannelType.TRADES.value == "trades"
        assert ChannelType.BOOKS5.value == "books5"

    def test_candle_channels(self):
        assert ChannelType.CANDLE_1M.value == "candle1m"
        assert ChannelType.CANDLE_1H.value == "candle1H"

    def test_candle_channel_from_bar(self):
        assert ChannelType.candle_channel(Bar.M1) == ChannelType.CANDLE_1M
        assert ChannelType.candle_channel(Bar.H1) == ChannelType.CANDLE_1H
        assert ChannelType.candle_channel(Bar.D1_UTC) == ChannelType.CANDLE_1D_UTC
