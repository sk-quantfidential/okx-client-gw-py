"""Tests for OrderBook domain models."""

from datetime import datetime
from decimal import Decimal

import pytest

from okx_client_gw.domain.models.orderbook import OrderBook, OrderBookLevel


class TestOrderBookLevel:
    """Tests for OrderBookLevel."""

    def test_create_level(self):
        level = OrderBookLevel(
            price=Decimal("50000.00"),
            size=Decimal("1.5"),
            liquidated_orders=0,
            num_orders=10,
        )

        assert level.price == Decimal("50000.00")
        assert level.size == Decimal("1.5")
        assert level.num_orders == 10

    def test_from_okx_array(self):
        # OKX returns [price, size, liquidatedOrders, numOrders]
        data = ["50000.00", "1.5", "0", "10"]
        level = OrderBookLevel.from_okx_array(data)

        assert level.price == Decimal("50000.00")
        assert level.size == Decimal("1.5")
        assert level.liquidated_orders == 0
        assert level.num_orders == 10

    def test_from_okx_array_minimal(self):
        # Some responses may have fewer fields
        data = ["50000.00", "1.5"]
        level = OrderBookLevel.from_okx_array(data)

        assert level.price == Decimal("50000.00")
        assert level.size == Decimal("1.5")
        assert level.liquidated_orders == 0
        assert level.num_orders == 1  # default


class TestOrderBook:
    """Tests for OrderBook."""

    @pytest.fixture
    def order_book(self):
        return OrderBook(
            inst_id="BTC-USDT",
            bids=[
                OrderBookLevel(
                    price=Decimal("49900"), size=Decimal("1.0"), liquidated_orders=0, num_orders=5
                ),
                OrderBookLevel(
                    price=Decimal("49800"), size=Decimal("2.0"), liquidated_orders=0, num_orders=8
                ),
            ],
            asks=[
                OrderBookLevel(
                    price=Decimal("50100"), size=Decimal("0.5"), liquidated_orders=0, num_orders=3
                ),
                OrderBookLevel(
                    price=Decimal("50200"), size=Decimal("1.5"), liquidated_orders=0, num_orders=6
                ),
            ],
            ts=datetime(2024, 1, 1, 12, 0, 0),
        )

    def test_best_bid(self, order_book):
        assert order_book.best_bid is not None
        assert order_book.best_bid.price == Decimal("49900")

    def test_best_ask(self, order_book):
        assert order_book.best_ask is not None
        assert order_book.best_ask.price == Decimal("50100")

    def test_best_bid_price(self, order_book):
        assert order_book.best_bid_price == Decimal("49900")

    def test_best_ask_price(self, order_book):
        assert order_book.best_ask_price == Decimal("50100")

    def test_spread(self, order_book):
        # 50100 - 49900 = 200
        assert order_book.spread == Decimal("200")

    def test_mid_price(self, order_book):
        # (50100 + 49900) / 2 = 50000
        assert order_book.mid_price == Decimal("50000")

    def test_spread_percent(self, order_book):
        # 200 / 50000 * 100 = 0.4%
        assert order_book.spread_percent == Decimal("0.4")

    def test_total_bid_size(self, order_book):
        # 1.0 + 2.0 = 3.0
        assert order_book.total_bid_size == Decimal("3.0")

    def test_total_ask_size(self, order_book):
        # 0.5 + 1.5 = 2.0
        assert order_book.total_ask_size == Decimal("2.0")

    def test_imbalance(self, order_book):
        # (3.0 - 2.0) / (3.0 + 2.0) = 0.2
        assert order_book.imbalance == Decimal("0.2")

    def test_empty_order_book(self):
        book = OrderBook(
            inst_id="BTC-USDT",
            bids=[],
            asks=[],
            ts=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert book.best_bid is None
        assert book.best_ask is None
        assert book.spread is None
        assert book.mid_price is None
        assert book.imbalance is None

    def test_from_okx_dict(self):
        data = {
            "bids": [["49900", "1.0", "0", "5"], ["49800", "2.0", "0", "8"]],
            "asks": [["50100", "0.5", "0", "3"], ["50200", "1.5", "0", "6"]],
            "ts": "1704110400000",  # 2024-01-01 12:00:00 UTC
            "checksum": "123456789",
            "seqId": "100",
        }

        book = OrderBook.from_okx_dict(data, inst_id="BTC-USDT")

        assert book.inst_id == "BTC-USDT"
        assert len(book.bids) == 2
        assert len(book.asks) == 2
        assert book.checksum == 123456789
        assert book.seq_id == 100
