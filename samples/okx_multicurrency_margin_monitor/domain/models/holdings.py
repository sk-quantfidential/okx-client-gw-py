"""Domain models for spot holdings."""

from dataclasses import dataclass


@dataclass
class SpotHolding:
    """Spot asset holding extracted from account balance.

    Attributes:
        currency: Currency code (e.g., "BTC", "ETH")
        balance: Available balance
        equity: Total equity in this currency
        usd_value: USD value of the equity
        discount_rate: OKX discount/haircut rate for collateral
        discounted_value: Value after haircut applied
    """

    currency: str
    balance: float
    equity: float
    usd_value: float
    discount_rate: float
    discounted_value: float
