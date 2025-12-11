"""Configuration constants for portfolio margin monitoring.

Margin thresholds (OKX uses percentage format where 100% = liquidation).
"""

# Warning level - OKX sends warning at 300%
MARGIN_WARNING_THRESHOLD = 300

# Danger level - you probably want to act here
MARGIN_DANGER_THRESHOLD = 150

# Liquidation level - forced liquidation triggered
MARGIN_LIQUIDATION_THRESHOLD = 100
