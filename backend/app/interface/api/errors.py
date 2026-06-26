"""Translate domain errors to HTTP status codes at the boundary.

The domain raises framework-free exceptions; only here do they become HTTP.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.domain import errors

_STATUS: list[tuple[type[Exception], int]] = [
    # most specific first
    (errors.NotFoundError, 404),
    (errors.DuplicateBarcode, 409),
    (errors.DuplicateCardNumber, 409),
    (errors.ItemNotAvailable, 409),
    (errors.InvalidItemTransition, 409),
    (errors.LoanNotOpen, 409),
    (errors.RenewalLimitReached, 409),
    (errors.RenewalBlockedByHold, 409),
    (errors.DuplicateHold, 409),
    (errors.HoldNotPending, 409),
    (errors.HoldNotReady, 409),
    (errors.HoldNotOpen, 409),
    (errors.NotForLoan, 422),
    (errors.PatronCannotBorrow, 422),
    (errors.DomainError, 400),  # fallback
]


def _status_for(exc: Exception) -> int:
    for exc_type, status in _STATUS:
        if isinstance(exc, exc_type):
            return status
    return 400


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(errors.DomainError)
    async def _handle_domain_error(
        request: Request, exc: errors.DomainError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for(exc),
            content={"detail": str(exc), "error": type(exc).__name__},
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity_error(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        # A unique constraint fired under concurrency — the DB backstops what the
        # domain pre-check raced past (ADR 0003: no double loan; also duplicate
        # barcode / card number). Surface it as a conflict, not a 500.
        return JSONResponse(
            status_code=409,
            content={
                "detail": "conflicting concurrent write was rejected",
                "error": "Conflict",
            },
        )
