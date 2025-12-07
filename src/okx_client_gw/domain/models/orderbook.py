"""Order book domain models."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from okx_client_gw.domain.enums import OrderBookAction


class OrderBookLevel(BaseModel):
    """Single price level in order book.

    OKX returns order book levels as arrays: [price, size, liquidatedOrders, numOrders]

    Attributes:
        price: Price level.
        size: Total size at this price level.
        liquidated_orders: Number of liquidated orders (derivatives only).
        num_orders: Number of orders at this price level.
    """

    price: Decimal = Field(description="Price level")
    size: Decimal = Field(description="Total size at price level")
    liquidated_orders: int = Field(default=0, description="Number of liquidated orders")
    num_orders: int = Field(description="Number of orders at price level")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_array(cls, data: list[str]) -> "OrderBookLevel":
        """Create an OrderBookLevel from OKX API array.

        Args:
            data: Array from OKX API [price, size, liquidatedOrders, numOrders]

        Returns:
            OrderBookLevel instance.
        """
        return cls(
            price=Decimal(data[0]),
            size=Decimal(data[1]),
            liquidated_orders=int(data[2]) if len(data) > 2 else 0,
            num_orders=int(data[3]) if len(data) > 3 else 1,
        )


class OrderBook(BaseModel):
    """Order book snapshot or update.

    See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-order-book

    Attributes:
        inst_id: Instrument ID (e.g., "BTC-USDT").
        bids: List of bid levels (sorted by price descending).
        asks: List of ask levels (sorted by price ascending).
        ts: Order book timestamp.
        action: Whether this is a snapshot or update.
        checksum: Checksum for order book verification.
        prev_seq_id: Previous sequence ID (for updates).
        seq_id: Current sequence ID.
    """

    inst_id: str = Field(description="Instrument ID")
    bids: list[OrderBookLevel] = Field(description="Bid levels (sorted by price descending)")
    asks: list[OrderBookLevel] = Field(description="Ask levels (sorted by price ascending)")
    ts: datetime = Field(description="Order book timestamp")
    action: OrderBookAction = Field(
        default=OrderBookAction.SNAPSHOT,
        description="Snapshot or update",
    )
    checksum: int | None = Field(default=None, description="Checksum for verification")
    prev_seq_id: int | None = Field(default=None, description="Previous sequence ID")
    seq_id: int | None = Field(default=None, description="Current sequence ID")

    model_config = {"frozen": True}

    @classmethod
    def from_okx_dict(cls, data: dict, inst_id: str | None = None) -> "OrderBook":
        """Create an OrderBook from OKX API dict response.

        Args:
            data: Dict from OKX API order book response.
            inst_id: Instrument ID. If not provided, must be present in data
                     as "instId" (WebSocket push format).

        Returns:
            OrderBook instance.

        Raises:
            ValueError: If inst_id is not provided and not in data.
        """
        # WebSocket push messages include instId in the data
        resolved_inst_id = inst_id or data.get("instId")
        if not resolved_inst_id:
            raise ValueError("inst_id must be provided or present in data as 'instId'")

        return cls(
            inst_id=resolved_inst_id,
            bids=[OrderBookLevel.from_okx_array(b) for b in data.get("bids", [])],
            asks=[OrderBookLevel.from_okx_array(a) for a in data.get("asks", [])],
            ts=datetime.fromtimestamp(int(data["ts"]) / 1000),
            action=OrderBookAction(data.get("action", "snapshot")),
            checksum=int(data["checksum"]) if data.get("checksum") else None,
            prev_seq_id=int(data["prevSeqId"]) if data.get("prevSeqId") else None,
            seq_id=int(data["seqId"]) if data.get("seqId") else None,
        )

    @property
    def best_bid(self) -> OrderBookLevel | None:
        """Get best bid level (highest price)."""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> OrderBookLevel | None:
        """Get best ask level (lowest price)."""
        return self.asks[0] if self.asks else None

    @property
    def best_bid_price(self) -> Decimal | None:
        """Get best bid price."""
        return self.best_bid.price if self.best_bid else None

    @property
    def best_ask_price(self) -> Decimal | None:
        """Get best ask price."""
        return self.best_ask.price if self.best_ask else None

    @property
    def spread(self) -> Decimal | None:
        """Calculate bid-ask spread."""
        if self.best_bid_price and self.best_ask_price:
            return self.best_ask_price - self.best_bid_price
        return None

    @property
    def spread_percent(self) -> Decimal | None:
        """Calculate bid-ask spread as percentage of mid price."""
        mid = self.mid_price
        spread = self.spread
        if mid and spread and mid != 0:
            return (spread / mid) * 100
        return None

    @property
    def mid_price(self) -> Decimal | None:
        """Calculate mid price."""
        if self.best_bid_price and self.best_ask_price:
            return (self.best_bid_price + self.best_ask_price) / 2
        return None

    @property
    def total_bid_size(self) -> Decimal:
        """Calculate total size on bid side."""
        return sum((level.size for level in self.bids), Decimal("0"))

    @property
    def total_ask_size(self) -> Decimal:
        """Calculate total size on ask side."""
        return sum((level.size for level in self.asks), Decimal("0"))

    @property
    def imbalance(self) -> Decimal | None:
        """Calculate order book imbalance (bid_size - ask_size) / (bid_size + ask_size).

        Returns value between -1 (all asks) and 1 (all bids).
        """
        bid_size = self.total_bid_size
        ask_size = self.total_ask_size
        total = bid_size + ask_size
        if total == 0:
            return None
        return (bid_size - ask_size) / total
