"""Instrument utility functions.

Price and size rounding to tick/lot sizes.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal


def round_price_to_tick(
    price: Decimal,
    tick_size: Decimal,
    rounding: str = ROUND_HALF_UP,
) -> Decimal:
    """Round price to nearest tick size.

    Args:
        price: Price to round
        tick_size: Minimum price increment
        rounding: Rounding mode (default: ROUND_HALF_UP)

    Returns:
        Price rounded to tick size

    Example:
        >>> round_price_to_tick(Decimal("100.123"), Decimal("0.01"))
        Decimal('100.12')
    """
    if tick_size <= 0:
        return price

    return (price / tick_size).quantize(Decimal("1"), rounding=rounding) * tick_size


def round_size_to_lot(
    size: Decimal,
    lot_size: Decimal,
    rounding: str = ROUND_DOWN,
) -> Decimal:
    """Round size to lot size (always rounds down).

    Args:
        size: Size to round
        lot_size: Minimum size increment
        rounding: Rounding mode (default: ROUND_DOWN for safety)

    Returns:
        Size rounded to lot size

    Example:
        >>> round_size_to_lot(Decimal("0.00123"), Decimal("0.0001"))
        Decimal('0.0012')
    """
    if lot_size <= 0:
        return size

    return (size / lot_size).quantize(Decimal("1"), rounding=rounding) * lot_size


def calculate_tick_precision(tick_size: Decimal) -> int:
    """Calculate decimal precision from tick size.

    Args:
        tick_size: Minimum price increment

    Returns:
        Number of decimal places

    Example:
        >>> calculate_tick_precision(Decimal("0.01"))
        2
        >>> calculate_tick_precision(Decimal("0.00001"))
        5
    """
    if tick_size >= 1:
        return 0

    # Count decimal places
    tick_str = str(tick_size)
    if "." not in tick_str:
        return 0

    return len(tick_str.split(".")[1].rstrip("0"))


def price_distance_pct(price1: Decimal, price2: Decimal) -> Decimal:
    """Calculate percentage distance between two prices.

    Args:
        price1: First price
        price2: Second price (reference)

    Returns:
        Percentage difference (positive = price1 > price2)

    Example:
        >>> price_distance_pct(Decimal("101"), Decimal("100"))
        Decimal('0.01')  # 1%
    """
    if price2 == 0:
        return Decimal("0")

    return (price1 - price2) / price2
