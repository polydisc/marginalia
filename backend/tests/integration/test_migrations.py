"""The real-DB bootstrap (`upgrade_to_head`) must be safe both for a fresh
database and for a legacy ``create_all`` database that predates Alembic."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.infrastructure.db.base import Base
from app.infrastructure.db.migrations import upgrade_to_head

# Added by 8f6b4adfd12f; a legacy DB stamped straight to head would never get it.
_HOLD_INDEX = "uq_open_hold_per_patron_manifestation"


def _hold_indexes(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return {ix["name"] for ix in inspect(engine).get_indexes("holds")}
    finally:
        engine.dispose()


def test_fresh_db_upgrades_to_head_with_all_indexes(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"

    upgrade_to_head(url)

    assert _HOLD_INDEX in _hold_indexes(url)


def test_legacy_create_all_db_gets_post_initial_migrations(tmp_path):
    # Simulate a pre-Alembic DB: the app tables exist (old create_all) but there
    # is no alembic_version bookkeeping yet. Drop the index that post-initial
    # migrations introduce so the schema matches the build that created it.
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    legacy_engine = create_engine(url)
    try:
        Base.metadata.create_all(legacy_engine)
        with legacy_engine.begin() as conn:
            conn.execute(text(f"DROP INDEX {_HOLD_INDEX}"))
    finally:
        legacy_engine.dispose()

    # Stamping straight to head used to skip this index on legacy databases.
    assert _HOLD_INDEX not in _hold_indexes(url)

    upgrade_to_head(url)

    assert _HOLD_INDEX in _hold_indexes(url)
