"""Domain enumerations for market maker.

Contains enums used across the domain layer.
"""

from __future__ import annotations

from enum import Enum


class OrderState(Enum):
    """Order lifecycle states.

    State transitions:
        PENDING -> SENT (on send)
        SENT -> ACK (on order accepted)
        SENT -> REJECTED (on order rejected)
        ACK -> LIVE (on order confirmed live)
        LIVE -> PARTIALLY_FILLED (on partial fill)
        LIVE -> FILLED (on complete fill)
        LIVE -> CANCELED (on cancel)
        PARTIALLY_FILLED -> FILLED (on remaining fill)
        PARTIALLY_FILLED -> CANCELED (on cancel remaining)
        * -> AMENDING (on amend request)
        AMENDING -> LIVE (on amend confirmed)
        AMENDING -> REJECTED (on amend rejected)
    """

    PENDING = "pending"           # Created but not sent
    SENT = "sent"                 # Sent to exchange
    ACK = "ack"                   # Acknowledged by exchange
    LIVE = "live"                 # Active on exchange
    PARTIALLY_FILLED = "partial"  # Partially filled
    FILLED = "filled"             # Completely filled
    CANCELED = "canceled"         # Canceled
    REJECTED = "rejected"         # Rejected by exchange
    AMENDING = "amending"         # Amendment in progress
