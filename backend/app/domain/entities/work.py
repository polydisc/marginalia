from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Work:
    """An abstract intellectual creation (FRBR Work).

    Carries author and original title; groups Manifestations (editions) of the
    same creation. Aggregate root, referenced by Manifestation by ID only.
    """

    title: str
    author: str
    id: int | None = None
