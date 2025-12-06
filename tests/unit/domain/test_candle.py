"""Tests for Candle domain model."""

from datetime import datetime
from decimal import Decimal

import pytest

from okx_client_gw.domain.models.candle import Candle


class TestCandleCreation:
    """Tests for Candle creation."""

    def test_create_candle(self):
        candle = Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("95.00"),
            close=Decimal("102.00"),
            volume=Decimal("1000.0"),
            volume_ccy=Decimal("100000.0"),
            volume_ccy_quote=Decimal("100000.0"),
            confirm=True,
        )

        assert candle.open == Decimal("100.00")
        assert candle.high == Decimal("105.00")
        assert candle.low == Decimal("95.00")
        assert candle.close == Decimal("102.00")
        assert candle.volume == Decimal("1000.0")
        assert candle.confirm is True

    def test_from_okx_array(self):
        # OKX returns [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        data = [
            "1704067200000",  # 2024-01-01 00:00:00 UTC
            "100.00",
            "105.00",
            "95.00",
            "102.00",
            "1000.0",
            "100000.0",
            "100000.0",
            "1",  # confirmed
        ]

        candle = Candle.from_okx_array(data)

        assert candle.open == Decimal("100.00")
        assert candle.high == Decimal("105.00")
        assert candle.close == Decimal("102.00")
        assert candle.confirm is True

    def test_from_okx_array_unconfirmed(self):
        data = [
            "1704067200000",
            "100.00",
            "105.00",
            "95.00",
            "102.00",
            "1000.0",
            "100000.0",
            "100000.0",
            "0",  # not confirmed
        ]

        candle = Candle.from_okx_array(data)
        assert candle.confirm is False


class TestCandleProperties:
    """Tests for Candle computed properties."""

    @pytest.fixture
    def bullish_candle(self):
        return Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=Decimal("100.00"),
            high=Decimal("110.00"),
            low=Decimal("95.00"),
            close=Decimal("105.00"),
            volume=Decimal("1000.0"),
            volume_ccy=Decimal("100000.0"),
            volume_ccy_quote=Decimal("100000.0"),
            confirm=True,
        )

    @pytest.fixture
    def bearish_candle(self):
        return Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=Decimal("105.00"),
            high=Decimal("110.00"),
            low=Decimal("95.00"),
            close=Decimal("100.00"),
            volume=Decimal("1000.0"),
            volume_ccy=Decimal("100000.0"),
            volume_ccy_quote=Decimal("100000.0"),
            confirm=True,
        )

    def test_mid_price(self, bullish_candle):
        # (110 + 95) / 2 = 102.50
        assert bullish_candle.mid_price == Decimal("102.50")

    def test_typical_price(self, bullish_candle):
        # (110 + 95 + 105) / 3 = 103.333...
        expected = (Decimal("110") + Decimal("95") + Decimal("105")) / 3
        assert bullish_candle.typical_price == expected

    def test_range(self, bullish_candle):
        # 110 - 95 = 15
        assert bullish_candle.range == Decimal("15.00")

    def test_body(self, bullish_candle):
        # abs(105 - 100) = 5
        assert bullish_candle.body == Decimal("5.00")

    def test_is_bullish(self, bullish_candle, bearish_candle):
        assert bullish_candle.is_bullish is True
        assert bullish_candle.is_bearish is False
        assert bearish_candle.is_bullish is False
        assert bearish_candle.is_bearish is True

    def test_timestamp_ms(self, bullish_candle):
        expected_ms = int(bullish_candle.timestamp.timestamp() * 1000)
        assert bullish_candle.timestamp_ms == expected_ms


class TestCandleImmutability:
    """Tests for Candle immutability."""

    def test_candle_is_frozen(self):
        candle = Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("95.00"),
            close=Decimal("102.00"),
            volume=Decimal("1000.0"),
            volume_ccy=Decimal("100000.0"),
            volume_ccy_quote=Decimal("100000.0"),
            confirm=True,
        )

        with pytest.raises(ValueError):  # Pydantic frozen model raises ValueError
            candle.open = Decimal("200.00")
