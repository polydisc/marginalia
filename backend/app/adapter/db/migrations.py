"""Programmatic Alembic upgrade, so ``uvicorn app.main:create_app --factory``
stays self-contained: a fresh ``library.db`` gets its schema applied on startup
without a separate ``alembic upgrade`` step (keeps E2E / all-in-one working).

This is the real-DB bootstrap only. Tests build their own schema via
``Base.metadata.create_all`` and never reach this path.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

import app.adapter.db.models  # noqa: F401  (register tables)
from alembic import command
from app.adapter.db.base import Base

# backend/  (contains alembic.ini and the alembic/ dir)
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _BACKEND_ROOT / "alembic.ini"
_ALEMBIC_DIR = _BACKEND_ROOT / "alembic"


def _make_alembic_config(database_url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    # Point at the migrations dir explicitly (robust to the process cwd) and
    # override the URL so we migrate exactly the app's database.
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _is_pre_alembic_db(database_url: str) -> bool:
    """True if the DB predates Alembic: it already has the app's tables (built
    by the old ``create_all``) but no ``alembic_version`` bookkeeping table.

    Such a DB would crash ``upgrade head`` with "table already exists", so it
    must be stamped to head instead of upgraded.
    """
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
    finally:
        engine.dispose()

    if "alembic_version" in existing:
        return False
    app_tables = set(Base.metadata.tables)
    # All app tables present, yet unversioned -> a legacy create_all DB.
    return bool(app_tables) and app_tables.issubset(existing)


def upgrade_to_head(database_url: str) -> None:
    """Bring the database at ``database_url`` to the latest schema.

    Normally runs ``alembic upgrade head``. But a legacy ``create_all`` DB
    already has the initial tables and no ``alembic_version`` row, which would
    make ``upgrade`` fail on the first migration ("table already exists"). For
    that case we stamp it at the *initial* revision (whose schema the legacy
    ``create_all`` already produced) and then upgrade, so every later migration
    — e.g. added partial indexes — still runs. Stamping straight to head would
    silently skip those post-initial migrations on legacy databases.
    """
    cfg = _make_alembic_config(database_url)
    if _is_pre_alembic_db(database_url):
        script = ScriptDirectory.from_config(cfg)
        (base_revision,) = script.get_bases()
        command.stamp(cfg, base_revision)
    command.upgrade(cfg, "head")
