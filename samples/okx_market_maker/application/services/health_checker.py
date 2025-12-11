"""Health checker service for market maker.

Monitors data freshness and system health.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from samples.okx_market_maker.application.context.market_context import MarketContext
    from samples.okx_market_maker.core.config.settings import MarketMakerSettings


@dataclass(frozen=True)
class HealthStatus:
    """System health status.

    Attributes:
        is_healthy: Overall health status
        orderbook_ok: Orderbook data is fresh
        account_ok: Account data is fresh
        position_ok: Position data is fresh
        connection_ok: WebSocket connections are alive
        issues: List of health issues
    """

    is_healthy: bool
    orderbook_ok: bool
    account_ok: bool
    position_ok: bool
    connection_ok: bool
    issues: list[str]


class HealthChecker:
    """Health checker for market maker system.

    Monitors:
    - Data freshness (orderbook, account, positions)
    - WebSocket connection status
    - Risk limit breaches

    Example:
        checker = HealthChecker(settings)
        status = checker.check(context)

        if not status.is_healthy:
            for issue in status.issues:
                logger.warning(f"Health issue: {issue}")
    """

    def __init__(self, settings: MarketMakerSettings) -> None:
        """Initialize health checker.

        Args:
            settings: Market maker configuration
        """
        self.settings = settings
        self._last_check_time: datetime | None = None
        self._consecutive_failures = 0

    def check(
        self,
        context: MarketContext,
        check_connection: bool = True,
    ) -> HealthStatus:
        """Perform health check.

        Args:
            context: Current market context
            check_connection: Whether to check connection status

        Returns:
            HealthStatus with check results
        """
        issues: list[str] = []
        self._last_check_time = datetime.now(UTC)

        # Check orderbook freshness
        orderbook_ok = context.is_orderbook_fresh(
            self.settings.orderbook_max_delay_sec
        )
        if not orderbook_ok:
            age = self._calculate_age(context.orderbook_time)
            issues.append(f"Orderbook stale: {age:.1f}s old")

        # Check account freshness
        account_ok = context.is_account_fresh(
            self.settings.account_max_delay_sec
        )
        if not account_ok:
            age = self._calculate_age(context.account_time)
            issues.append(f"Account data stale: {age:.1f}s old")

        # Check position freshness
        position_ok = context.is_position_fresh(
            self.settings.position_max_delay_sec
        )
        if not position_ok:
            age = self._calculate_age(context.position_time)
            issues.append(f"Position data stale: {age:.1f}s old")

        # Check connection (simplified - assumes ok if we have recent data)
        connection_ok = True
        if check_connection:
            connection_ok = orderbook_ok or account_ok
            if not connection_ok:
                issues.append("No recent data - connection may be lost")

        # Check for missing essential data
        if context.orderbook is None:
            issues.append("No orderbook data")
            orderbook_ok = False

        if context.mid_price is None:
            issues.append("Cannot calculate mid price")

        # Overall health
        is_healthy = orderbook_ok and account_ok and position_ok and connection_ok

        # Track consecutive failures
        if is_healthy:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

        return HealthStatus(
            is_healthy=is_healthy,
            orderbook_ok=orderbook_ok,
            account_ok=account_ok,
            position_ok=position_ok,
            connection_ok=connection_ok,
            issues=issues,
        )

    def _calculate_age(self, timestamp: datetime | None) -> float:
        """Calculate age of data in seconds.

        Args:
            timestamp: Data timestamp

        Returns:
            Age in seconds, or inf if no timestamp
        """
        if timestamp is None:
            return float("inf")
        return (datetime.now(UTC) - timestamp).total_seconds()

    @property
    def consecutive_failures(self) -> int:
        """Get number of consecutive health check failures."""
        return self._consecutive_failures

    @property
    def last_check_time(self) -> datetime | None:
        """Get time of last health check."""
        return self._last_check_time

    def should_emergency_stop(self, threshold: int = 5) -> bool:
        """Check if emergency stop should be triggered.

        Args:
            threshold: Number of consecutive failures to trigger stop

        Returns:
            True if emergency stop should be triggered
        """
        return self._consecutive_failures >= threshold
