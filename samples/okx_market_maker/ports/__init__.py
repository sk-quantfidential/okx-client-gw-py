"""Ports layer - protocol definitions (interfaces).

Contains abstract protocols that define contracts for
dependency injection and external integrations.
"""

from samples.okx_market_maker.ports.strategy import StrategyProtocol

__all__ = [
    "StrategyProtocol",
]
