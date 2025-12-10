"""Market maker settings using Pydantic Settings.

Supports configuration from YAML file and environment variable overrides.
Environment variables use MM_ prefix (e.g., MM_INST_ID, MM_STEP_PCT).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketMakerSettings(BaseSettings):
    """Market maker configuration settings.

    Loads configuration from:
    1. params.yaml file (if exists)
    2. Environment variables (override YAML values)

    Environment variables use MM_ prefix:
    - MM_INST_ID: Instrument ID
    - MM_STEP_PCT: Price step percentage
    - MM_NUM_ORDERS_PER_SIDE: Orders per side
    etc.

    Example:
        # Load from default params.yaml
        settings = MarketMakerSettings()

        # Load from custom YAML file
        settings = MarketMakerSettings.from_yaml("custom_params.yaml")

        # Override with environment
        export MM_INST_ID="ETH-USDT"
        settings = MarketMakerSettings()  # Uses ETH-USDT
    """

    model_config = SettingsConfigDict(
        env_prefix="MM_",
        env_file=".env",
        extra="ignore",
    )

    # Instrument settings
    inst_id: str = Field(
        default="BTC-USDT",
        description="Instrument ID to trade",
    )
    trading_mode: Literal["cash", "cross", "isolated"] = Field(
        default="cash",
        description="Trading mode (cash for spot, cross/isolated for margin)",
    )
    use_demo: bool = Field(
        default=True,
        description="Use demo trading environment",
    )

    # Strategy parameters
    strategy_type: Literal["grid", "inventory_skew", "volatility"] = Field(
        default="grid",
        description="Strategy type to use",
    )
    step_pct: Decimal = Field(
        default=Decimal("0.001"),
        description="Price step between orders as percentage (0.001 = 0.1%)",
    )
    num_orders_per_side: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of orders per side (buy/sell)",
    )
    single_order_size: Decimal = Field(
        default=Decimal("0.001"),
        description="Size for each individual order",
    )
    single_order_size_multiplier: Decimal = Field(
        default=Decimal("1.0"),
        description="Multiplier applied to order size",
    )

    # Risk limits
    max_net_buy: Decimal = Field(
        default=Decimal("100.0"),
        description="Maximum net buy position size",
    )
    max_net_sell: Decimal = Field(
        default=Decimal("100.0"),
        description="Maximum net sell position size",
    )
    max_position_value_usd: Decimal = Field(
        default=Decimal("10000.0"),
        description="Maximum position value in USD",
    )

    # Health check thresholds
    orderbook_max_delay_sec: float = Field(
        default=5.0,
        description="Maximum orderbook staleness in seconds",
    )
    account_max_delay_sec: float = Field(
        default=10.0,
        description="Maximum account data staleness in seconds",
    )
    position_max_delay_sec: float = Field(
        default=10.0,
        description="Maximum position data staleness in seconds",
    )

    # Main loop settings
    main_loop_interval_sec: float = Field(
        default=1.0,
        description="Interval between strategy iterations",
    )

    # Inventory skew strategy settings
    skew_factor: Decimal = Field(
        default=Decimal("0.5"),
        description="How aggressively to skew prices based on inventory (0-1)",
    )
    max_skew_pct: Decimal = Field(
        default=Decimal("0.005"),
        description="Maximum price skew as percentage (0.005 = 0.5%)",
    )

    # Volatility strategy settings
    volatility_lookback: int = Field(
        default=20,
        description="Number of candles for volatility calculation",
    )
    volatility_multiplier: Decimal = Field(
        default=Decimal("2.0"),
        description="Multiplier for volatility-based spread",
    )
    min_spread_pct: Decimal = Field(
        default=Decimal("0.001"),
        description="Minimum spread percentage",
    )
    max_spread_pct: Decimal = Field(
        default=Decimal("0.01"),
        description="Maximum spread percentage",
    )

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> MarketMakerSettings:
        """Load settings from a YAML file with environment overrides.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            MarketMakerSettings with values from YAML and env overrides
        """
        yaml_path = Path(yaml_path)
        if yaml_path.exists():
            with open(yaml_path) as f:
                yaml_config = yaml.safe_load(f) or {}
            return cls(**yaml_config)
        return cls()

    @classmethod
    def default_yaml_path(cls) -> Path:
        """Get the default params.yaml path relative to this module."""
        return Path(__file__).parent / "params.yaml"

    @classmethod
    def load(cls) -> MarketMakerSettings:
        """Load settings from default params.yaml with env overrides.

        Convenience method that loads from the default params.yaml location.

        Returns:
            MarketMakerSettings instance
        """
        return cls.from_yaml(cls.default_yaml_path())

    @property
    def effective_order_size(self) -> Decimal:
        """Calculate effective order size with multiplier."""
        return self.single_order_size * self.single_order_size_multiplier
