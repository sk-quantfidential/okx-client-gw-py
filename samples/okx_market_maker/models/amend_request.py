"""Typed amend request model.

Provides a properly typed POD (Plain Old Data) object for order amendments
instead of using raw dicts, improving type safety and validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class AmendRequest:
    """Request to amend an existing order.

    OKX allows amending price and/or size of live orders.
    Either cl_ord_id or ord_id must be provided to identify the order.
    At least one of new_px or new_sz must be provided.

    Attributes:
        inst_id: Instrument ID (e.g., "BTC-USDT")
        cl_ord_id: Client order ID (optional if ord_id provided)
        ord_id: Exchange order ID (optional if cl_ord_id provided)
        new_px: New price (optional)
        new_sz: New size (optional)

    Example:
        # Amend price only
        amend = AmendRequest(
            inst_id="BTC-USDT",
            cl_ord_id="mm_000001",
            new_px=Decimal("50100"),
        )

        # Amend both price and size
        amend = AmendRequest(
            inst_id="BTC-USDT",
            ord_id="1234567890",
            new_px=Decimal("50100"),
            new_sz=Decimal("0.002"),
        )
    """

    inst_id: str
    cl_ord_id: str | None = None
    ord_id: str | None = None
    new_px: Decimal | None = None
    new_sz: Decimal | None = None

    def __post_init__(self) -> None:
        """Validate the amend request.

        Raises:
            ValueError: If neither order ID is provided or no changes specified.
        """
        if not self.cl_ord_id and not self.ord_id:
            raise ValueError("Either cl_ord_id or ord_id must be provided")
        if self.new_px is None and self.new_sz is None:
            raise ValueError("At least one of new_px or new_sz must be provided")

    def to_okx_dict(self) -> dict[str, str]:
        """Convert to OKX API format.

        Returns:
            Dictionary suitable for OKX amend-order API.
        """
        d: dict[str, str] = {"instId": self.inst_id}

        if self.cl_ord_id:
            d["clOrdId"] = self.cl_ord_id
        if self.ord_id:
            d["ordId"] = self.ord_id
        if self.new_px is not None:
            d["newPx"] = str(self.new_px)
        if self.new_sz is not None:
            d["newSz"] = str(self.new_sz)

        return d

    @classmethod
    def from_okx_dict(cls, data: dict) -> AmendRequest:
        """Create from OKX API format.

        Args:
            data: Dictionary from OKX API.

        Returns:
            AmendRequest instance.
        """
        return cls(
            inst_id=data["instId"],
            cl_ord_id=data.get("clOrdId"),
            ord_id=data.get("ordId"),
            new_px=Decimal(data["newPx"]) if data.get("newPx") else None,
            new_sz=Decimal(data["newSz"]) if data.get("newSz") else None,
        )
