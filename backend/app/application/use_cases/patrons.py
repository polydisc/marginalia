"""Patron use cases: registration and lifecycle (suspend / reinstate)."""

from __future__ import annotations

from datetime import date

from app.application.dto import PatronResult
from app.application.unit_of_work import UnitOfWork
from app.domain.entities import Patron
from app.domain.errors import DuplicateCardNumber, PatronNotFound
from app.domain.value_objects import PatronCategory


def _result(patron: Patron) -> PatronResult:
    return PatronResult(
        id=patron.id,
        card_number=patron.card_number,
        category=patron.category.value,
        status=patron.status.value,
        expires_on=patron.expires_on,
    )


class RegisterPatron:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        card_number: str,
        category: PatronCategory,
        expires_on: date | None = None,
    ) -> PatronResult:
        with self._uow as uow:
            if uow.patrons.get_by_card_number(card_number) is not None:
                raise DuplicateCardNumber(
                    f"card number {card_number} already registered"
                )
            patron = uow.patrons.add(
                Patron(
                    card_number=card_number,
                    category=category,
                    expires_on=expires_on,
                )
            )
            uow.commit()
            return _result(patron)


class UpdatePatron:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        card_number: str,
        category: PatronCategory,
        expires_on: date | None = None,
    ) -> PatronResult:
        with self._uow as uow:
            patron = uow.patrons.get_by_card_number(card_number)
            if patron is None:
                raise PatronNotFound(f"patron {card_number} does not exist")
            patron.category = category
            patron.expires_on = expires_on
            uow.patrons.update(patron)
            uow.commit()
            return _result(patron)


class SuspendPatron:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, card_number: str) -> PatronResult:
        with self._uow as uow:
            patron = uow.patrons.get_by_card_number(card_number)
            if patron is None:
                raise PatronNotFound(f"patron {card_number} does not exist")
            patron.suspend()
            uow.patrons.update(patron)
            uow.commit()
            return _result(patron)


class ReinstatePatron:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, card_number: str) -> PatronResult:
        with self._uow as uow:
            patron = uow.patrons.get_by_card_number(card_number)
            if patron is None:
                raise PatronNotFound(f"patron {card_number} does not exist")
            patron.reinstate()
            uow.patrons.update(patron)
            uow.commit()
            return _result(patron)
