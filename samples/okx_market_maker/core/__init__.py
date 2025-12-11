"""Core layer - infrastructure and configuration.

Contains configuration, utilities, and other infrastructure code.
No dependencies on other layers (self-contained).
"""

from samples.okx_market_maker.core.config.settings import MarketMakerSettings

__all__ = [
    "MarketMakerSettings",
]
