"""Candle factory implementation for OKX.

@package okx_client_gw.adapters
"""

from datetime import datetime, timedelta
from decimal import Decimal

from okx_client_gw.domain.models.candle import Candle


class OkxCandleFactory:
    """Factory for creating OKX Candle instances.

    Implements CandleFactory protocol from client-gw-core for use
    with generic candle processing utilities.

    Note: OKX uses Decimal for prices. This factory converts float inputs
    (from interpolation) to Decimal for type consistency.
    """

    def create(
        self,
        timestamp: datetime,
        time_delta: timedelta,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
    ) -> Candle:
        """Create an OKX Candle instance.

        Args:
            timestamp: Candle start timestamp (UTC)
            time_delta: Candle duration/granularity
            open: Opening price (converted to Decimal)
            high: Highest price (converted to Decimal)
            low: Lowest price (converted to Decimal)
            close: Closing price (converted to Decimal)
            volume: Trading volume (0.0 for interpolated candles)

        Returns:
            OKX Candle instance
        """
        return Candle(
            timestamp=timestamp,
            time_delta=time_delta,
            open=Decimal(str(open)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=Decimal(str(volume)),
            volume_ccy=Decimal("0"),  # Unknown for interpolated
            volume_ccy_quote=Decimal("0"),  # Unknown for interpolated
            confirm=True,  # Interpolated candles are considered confirmed
        )
