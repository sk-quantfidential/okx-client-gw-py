"""Tests for market context and models."""

from decimal import Decimal

import pytest

from samples.okx_market_maker.context.market_context import MarketContext
from samples.okx_market_maker.models.strategy_order import OrderState, StrategyOrder


class TestMarketContext:
    """Tests for MarketContext."""

    def test_mid_price_calculation(self) -> None:
        """Test mid price calculation from orderbook."""
        from unittest.mock import MagicMock

        context = MarketContext(inst_id="BTC-USDT")

        orderbook = MagicMock()
        orderbook.bids = [MagicMock(price=Decimal("50000"))]
        orderbook.asks = [MagicMock(price=Decimal("50010"))]

        context.update_orderbook(orderbook)

        assert context.mid_price == Decimal("50005")

    def test_spread_calculation(self) -> None:
        """Test spread calculation."""
        from unittest.mock import MagicMock

        context = MarketContext(inst_id="BTC-USDT")

        orderbook = MagicMock()
        orderbook.bids = [MagicMock(price=Decimal("50000"))]
        orderbook.asks = [MagicMock(price=Decimal("50010"))]

        context.update_orderbook(orderbook)

        assert context.spread == Decimal("10")
        assert context.spread_pct == Decimal("10") / Decimal("50005")

    def test_net_position_tracking(self) -> None:
        """Test net position calculation."""
        context = MarketContext(inst_id="BTC-USDT")

        context.record_fill("buy", Decimal("1"))
        context.record_fill("buy", Decimal("0.5"))
        context.record_fill("sell", Decimal("0.3"))

        assert context.net_position == Decimal("1.2")

    def test_order_management(self) -> None:
        """Test order add/get/remove."""
        context = MarketContext(inst_id="BTC-USDT")

        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
        )

        context.add_order(order)
        assert context.get_order("test_001") == order

        removed = context.remove_order("test_001")
        assert removed == order
        assert context.get_order("test_001") is None

    def test_active_orders_filtering(self) -> None:
        """Test active order filtering by side."""
        context = MarketContext(inst_id="BTC-USDT")

        buy_order = StrategyOrder(
            cl_ord_id="buy_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
            state=OrderState.LIVE,
        )

        sell_order = StrategyOrder(
            cl_ord_id="sell_001",
            inst_id="BTC-USDT",
            side="sell",
            price=Decimal("50010"),
            size=Decimal("0.001"),
            state=OrderState.LIVE,
        )

        filled_order = StrategyOrder(
            cl_ord_id="filled_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("49990"),
            size=Decimal("0.001"),
            state=OrderState.FILLED,
        )

        context.add_order(buy_order)
        context.add_order(sell_order)
        context.add_order(filled_order)

        assert len(context.active_buy_orders) == 1
        assert len(context.active_sell_orders) == 1

    def test_clear_terminal_orders(self) -> None:
        """Test clearing filled/canceled orders."""
        context = MarketContext(inst_id="BTC-USDT")

        live_order = StrategyOrder(
            cl_ord_id="live_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
            state=OrderState.LIVE,
        )

        filled_order = StrategyOrder(
            cl_ord_id="filled_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("49990"),
            size=Decimal("0.001"),
            state=OrderState.FILLED,
        )

        context.add_order(live_order)
        context.add_order(filled_order)

        removed = context.clear_terminal_orders()

        assert removed == 1
        assert context.get_order("live_001") is not None
        assert context.get_order("filled_001") is None


class TestStrategyOrder:
    """Tests for StrategyOrder state machine."""

    def test_initial_state_is_pending(self) -> None:
        """Test that new orders start in PENDING state."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
        )

        assert order.state == OrderState.PENDING
        assert order.is_pending
        assert order.is_active

    def test_state_transitions(self) -> None:
        """Test valid state transitions."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
        )

        # PENDING -> SENT
        order.mark_sent()
        assert order.state == OrderState.SENT

        # SENT -> ACK
        order.mark_ack("exchange_123")
        assert order.state == OrderState.ACK
        assert order.ord_id == "exchange_123"

        # ACK -> LIVE
        order.mark_live()
        assert order.state == OrderState.LIVE
        assert order.is_live

    def test_fill_tracking(self) -> None:
        """Test fill recording and calculations."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.002"),
            state=OrderState.LIVE,
        )

        # Partial fill
        order.record_fill(Decimal("0.001"), Decimal("50001"))
        assert order.state == OrderState.PARTIALLY_FILLED
        assert order.filled_size == Decimal("0.001")
        assert order.avg_fill_price == Decimal("50001")
        assert order.fill_percent == Decimal("50")

        # Complete fill
        order.record_fill(Decimal("0.001"), Decimal("50003"))
        assert order.state == OrderState.FILLED
        assert order.is_filled
        assert order.filled_size == Decimal("0.002")
        # Avg price = (50001 * 0.001 + 50003 * 0.001) / 0.002 = 50002
        assert order.avg_fill_price == Decimal("50002")

    def test_remaining_size(self) -> None:
        """Test remaining size calculation."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.003"),
            state=OrderState.LIVE,
        )

        order.record_fill(Decimal("0.001"), Decimal("50000"))
        assert order.remaining_size == Decimal("0.002")

    def test_cancel_from_live(self) -> None:
        """Test canceling a live order."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
            state=OrderState.LIVE,
        )

        order.mark_canceled()
        assert order.state == OrderState.CANCELED
        assert order.is_canceled
        assert order.is_terminal

    def test_invalid_state_transition_raises(self) -> None:
        """Test that invalid transitions raise ValueError."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
        )

        # Can't go from PENDING to LIVE directly
        with pytest.raises(ValueError):
            order.mark_live()

        # Can't cancel a PENDING order
        with pytest.raises(ValueError):
            order.mark_canceled()

    def test_to_dict(self) -> None:
        """Test dictionary serialization."""
        order = StrategyOrder(
            cl_ord_id="test_001",
            inst_id="BTC-USDT",
            side="buy",
            price=Decimal("50000"),
            size=Decimal("0.001"),
        )

        d = order.to_dict()

        assert d["cl_ord_id"] == "test_001"
        assert d["inst_id"] == "BTC-USDT"
        assert d["side"] == "buy"
        assert d["price"] == "50000"
        assert d["state"] == "pending"
