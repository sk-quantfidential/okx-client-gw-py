"""Strategy module for market maker.

Provides pluggable strategy implementations:
- SampleMMStrategy: Basic symmetric grid
- InventorySkewStrategy: Inventory-based price skewing
- VolatilityStrategy: Volatility-adjusted spreads
"""

from samples.okx_market_maker.strategy.base_strategy import BaseStrategy
from samples.okx_market_maker.strategy.inventory_skew_strategy import InventorySkewStrategy
from samples.okx_market_maker.strategy.sample_mm_strategy import SampleMMStrategy
from samples.okx_market_maker.strategy.strategy_protocol import (
    Quote,
    StrategyDecision,
    StrategyProtocol,
)
from samples.okx_market_maker.strategy.volatility_strategy import VolatilityStrategy

__all__ = [
    # Protocol
    "StrategyProtocol",
    "StrategyDecision",
    "Quote",
    # Base
    "BaseStrategy",
    # Strategies
    "SampleMMStrategy",
    "InventorySkewStrategy",
    "VolatilityStrategy",
]
