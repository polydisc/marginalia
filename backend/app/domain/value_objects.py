"""Domain value objects and enumerations.

Pure Python — the innermost layer imports nothing outward (ADR 0001).
"""

from __future__ import annotations

from enum import Enum


class ItemState(str, Enum):
    """The single *intrinsic* state an Item stores (CONTEXT.md).

    ``on_loan`` and ``on_hold_shelf`` are deliberately absent: they are derived
    from the existence of an open Loan / an assigned ready Hold, never stored.
    """

    available = "available"
    in_repair = "in_repair"
    lost = "lost"
    withdrawn = "withdrawn"  # terminal


class PatronCategory(str, Enum):
    general = "general"
    student = "student"
    child = "child"


class PatronStatus(str, Enum):
    active = "active"
    suspended = "suspended"


class MaterialType(str, Enum):
    book = "book"
    reference = "reference"
    audiovisual = "audiovisual"


class HoldStatus(str, Enum):
    pending = "pending"
    ready = "ready"  # an Item has been assigned and set aside on the hold shelf
    fulfilled = "fulfilled"
    expired = "expired"  # readied but not picked up by its pickup-by date
    cancelled = "cancelled"


class Availability(str, Enum):
    """The *derived* availability of an Item, composed at read time."""

    available = "available"
    on_loan = "on_loan"
    on_hold_shelf = "on_hold_shelf"
    in_repair = "in_repair"
    lost = "lost"
    withdrawn = "withdrawn"
