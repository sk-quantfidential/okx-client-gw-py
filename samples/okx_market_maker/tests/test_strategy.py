"""Tests for market maker strategies."""

from decimal import Decimal

import pytest

from samples.okx_market_maker.config.settings import MarketMakerSettings
from samples.okx_market_maker.context.market_context import MarketContext
from samples.okx_market_maker.strategy.inventory_skew_strategy import InventorySkewStrategy
from samples.okx_market_maker.strategy.sample_mm_strategy import SampleMMStrategy
from samples.okx_market_maker.strategy.volatility_strategy import VolatilityStrategy


@pytest.fixture
def settings() -> MarketMakerSettings:
    """Create test settings."""
    return MarketMakerSettings(
        inst_id="BTC-USDT",
        step_pct=Decimal("0.001"),
        num_orders_per_side=3,
        single_order_size=Decimal("0.001"),
        max_net_buy=Decimal("10"),
        max_net_sell=Decimal("10"),
        orderbook_max_delay_sec=5.0,
        account_max_delay_sec=10.0,
        skew_factor=Decimal("0.5"),
        max_skew_pct=Decimal("0.005"),
    )


@pytest.fixture
def context() -> MarketContext:
    """Create test context with mock orderbook."""
    ctx = MarketContext(inst_id="BTC-USDT")

    # Create mock orderbook
    from unittest.mock import MagicMock

    orderbook = MagicMock()
    orderbook.bids = [
        MagicMock(price=Decimal("50000"), size=Decimal("1")),
        MagicMock(price=Decimal("49990"), size=Decimal("2")),
    ]
    orderbook.asks = [
        MagicMock(price=Decimal("50010"), size=Decimal("1")),
        MagicMock(price=Decimal("50020"), size=Decimal("2")),
    ]

    ctx.update_orderbook(orderbook)

    # Create mock account
    account = MagicMock()
    account.total_eq = Decimal("10000")
    ctx.update_account(account)

    return ctx


class TestSampleMMStrategy:
    """Tests for basic grid strategy."""

    def test_compute_quotes_generates_symmetric_grid(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that strategy generates symmetric buy/sell quotes."""
        strategy = SampleMMStrategy(settings)
        quotes = strategy.compute_quotes(context)

        # Should have 3 buys and 3 sells
        buys = [q for q in quotes if q.side == "buy"]
        sells = [q for q in quotes if q.side == "sell"]

        assert len(buys) == 3
        assert len(sells) == 3

        # Buys should be below best bid
        for quote in buys:
            assert quote.price < context.best_bid

        # Sells should be above best ask
        for quote in sells:
            assert quote.price > context.best_ask

    def test_position_aware_order_reduction(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that long position reduces buy orders."""
        strategy = SampleMMStrategy(settings)

        # Add a long position
        context.net_filled_buy = Decimal("5")

        quotes = strategy.compute_quotes(context)
        buys = [q for q in quotes if q.side == "buy"]
        sells = [q for q in quotes if q.side == "sell"]

        # Should have fewer buy orders due to position
        assert len(buys) < len(sells)

    def test_decide_returns_decision(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that decide() returns proper decision."""
        strategy = SampleMMStrategy(settings)
        decision = strategy.decide(context)

        assert not decision.should_halt
        assert len(decision.orders_to_place) > 0


class TestInventorySkewStrategy:
    """Tests for inventory skew strategy."""

    def test_skew_shifts_prices_when_long(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that long position shifts prices down."""
        strategy = InventorySkewStrategy(settings)

        # Get quotes with no position
        context.net_filled_buy = Decimal("0")
        quotes_neutral = strategy.compute_quotes(context)

        # Get quotes with long position
        context.net_filled_buy = Decimal("5")
        quotes_long = strategy.compute_quotes(context)

        # Compare average buy prices - should be lower when long
        avg_buy_neutral = sum(q.price for q in quotes_neutral if q.side == "buy") / 3
        avg_buy_long = sum(q.price for q in quotes_long if q.side == "buy") / max(
            1, len([q for q in quotes_long if q.side == "buy"])
        )

        # Prices should be lower (skewed down) when long
        assert avg_buy_long <= avg_buy_neutral

    def test_skew_shifts_prices_when_short(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that short position shifts prices up."""
        strategy = InventorySkewStrategy(settings)

        # Get quotes with no position
        context.net_filled_sell = Decimal("0")
        quotes_neutral = strategy.compute_quotes(context)

        # Get quotes with short position
        context.net_filled_sell = Decimal("5")
        quotes_short = strategy.compute_quotes(context)

        # Compare average sell prices
        avg_sell_neutral = sum(q.price for q in quotes_neutral if q.side == "sell") / 3
        avg_sell_short = sum(q.price for q in quotes_short if q.side == "sell") / max(
            1, len([q for q in quotes_short if q.side == "sell"])
        )

        # Prices should be higher (skewed up) when short
        assert avg_sell_short >= avg_sell_neutral


class TestVolatilityStrategy:
    """Tests for volatility strategy."""

    def test_uses_min_spread_without_volatility_data(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that strategy uses min spread when no volatility data."""
        strategy = VolatilityStrategy(settings)
        quotes = strategy.compute_quotes(context)

        # Should still generate quotes
        assert len(quotes) > 0

    def test_wider_spread_with_high_volatility(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that high volatility results in wider spreads."""
        strategy = VolatilityStrategy(settings)

        # Add price history with low volatility
        context.recent_prices = [Decimal("50000")] * 25

        quotes_low_vol = strategy.compute_quotes(context)
        buy_low = min(q.price for q in quotes_low_vol if q.side == "buy")
        sell_low = max(q.price for q in quotes_low_vol if q.side == "sell")
        spread_low = sell_low - buy_low

        # Add price history with high volatility
        context.recent_prices = [
            Decimal("50000") + (Decimal(i % 10) * 100)
            for i in range(25)
        ]

        quotes_high_vol = strategy.compute_quotes(context)
        buy_high = min(q.price for q in quotes_high_vol if q.side == "buy")
        sell_high = max(q.price for q in quotes_high_vol if q.side == "sell")
        spread_high = sell_high - buy_high

        # High volatility should result in wider spread
        assert spread_high >= spread_low


class TestStrategyHaltConditions:
    """Tests for strategy halt conditions."""

    def test_halt_on_stale_orderbook(
        self,
        settings: MarketMakerSettings,
    ) -> None:
        """Test that strategy halts on stale orderbook."""
        context = MarketContext(inst_id="BTC-USDT")
        # No orderbook data = stale

        strategy = SampleMMStrategy(settings)
        decision = strategy.decide(context)

        assert decision.should_halt
        assert "stale" in decision.halt_reason.lower() or "mid price" in decision.halt_reason.lower()

    def test_halt_on_position_limit(
        self,
        settings: MarketMakerSettings,
        context: MarketContext,
    ) -> None:
        """Test that strategy halts when position exceeds limit."""
        strategy = SampleMMStrategy(settings)

        # Exceed max net buy
        context.net_filled_buy = Decimal("15")

        decision = strategy.decide(context)

        assert decision.should_halt
        assert "exceeded" in decision.halt_reason.lower()
