"""Shared FastAPI path-parameter constraints.

Keeping these aliases in one interface-layer module makes the OpenAPI contract
and validation behavior consistent across staff and OPAC routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Path

# Database surrogate keys are signed 64-bit (SQLite INTEGER / PostgreSQL bigint).
# Reject anything above the range at the boundary: an out-of-range id would
# otherwise overflow while binding the lookup and surface as a 500 instead of a
# clean 422.
DB_ID_MAX = 2**63 - 1

# Path values do not go through request-body schemas, so they need equivalent
# bounds here to avoid unbounded lookups/log messages from arbitrary API clients.
CodePath = Annotated[
    str, Path(min_length=1, max_length=64, pattern=r".*\S.*")
]
IdPath = Annotated[int, Path(ge=1, le=DB_ID_MAX)]
