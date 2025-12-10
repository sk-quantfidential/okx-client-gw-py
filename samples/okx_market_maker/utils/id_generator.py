"""Client order ID generation.

Generates unique client order IDs for tracking orders.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator


def generate_client_order_id(prefix: str = "mm") -> str:
    """Generate a unique client order ID.

    Format: {prefix}_{timestamp_ms}_{uuid_short}

    Args:
        prefix: Prefix for the ID (default: "mm")

    Returns:
        Unique client order ID

    Example:
        >>> generate_client_order_id()
        'mm_1704067200000_a1b2c3d4'
    """
    timestamp_ms = int(time.time() * 1000)
    uuid_short = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp_ms}_{uuid_short}"


class OrderIdGenerator:
    """Sequential order ID generator.

    Generates sequential IDs with prefix for easier tracking.

    Example:
        gen = OrderIdGenerator(prefix="mm")
        id1 = gen.next()  # mm_000001
        id2 = gen.next()  # mm_000002
    """

    def __init__(self, prefix: str = "mm", start: int = 1) -> None:
        """Initialize generator.

        Args:
            prefix: Prefix for IDs
            start: Starting sequence number
        """
        self._prefix = prefix
        self._counter = start

    def next(self) -> str:
        """Generate next sequential ID.

        Returns:
            Next client order ID
        """
        order_id = f"{self._prefix}_{self._counter:06d}"
        self._counter += 1
        return order_id

    def __iter__(self) -> Iterator[str]:
        """Iterate over generated IDs."""
        return self

    def __next__(self) -> str:
        """Get next ID via iterator protocol."""
        return self.next()

    @property
    def current(self) -> int:
        """Get current counter value."""
        return self._counter

    def reset(self, start: int = 1) -> None:
        """Reset counter.

        Args:
            start: New starting value
        """
        self._counter = start
