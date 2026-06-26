from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects import MaterialType


@dataclass
class Manifestation:
    """A specific published embodiment of a Work (FRBR Manifestation).

    The practical center of cataloguing; loan policy keys off its material type.
    References its Work by ID only.
    """

    work_id: int
    title: str
    material_type: MaterialType
    isbn: str | None = None
    publisher: str | None = None
    id: int | None = None
