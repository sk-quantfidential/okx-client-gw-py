"""Core layer - configuration and infrastructure."""

from samples.okx_multicurrency_margin_monitor.core.config import (
    MARGIN_DANGER_THRESHOLD,
    MARGIN_LIQUIDATION_THRESHOLD,
    MARGIN_WARNING_THRESHOLD,
)

__all__ = [
    "MARGIN_DANGER_THRESHOLD",
    "MARGIN_LIQUIDATION_THRESHOLD",
    "MARGIN_WARNING_THRESHOLD",
]
