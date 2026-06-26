"""prevent duplicate open holds

Revision ID: 8f6b4adfd12f
Revises: 14d2433d318c
Create Date: 2026-06-26 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f6b4adfd12f"
down_revision: Union[str, Sequence[str], None] = "14d2433d318c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Portfolio-quality invariant: the DB rejects duplicate open holds even if
    # concurrent requests race past the use-case precheck.
    #
    # Use a plain CREATE INDEX, not batch_alter_table: SQLite supports partial
    # index creation in place, and batch mode would rebuild `holds` from
    # Base.metadata (which already declares this index) and then collide with
    # the explicit create — that breaks the on-startup migration the app runs.
    op.create_index(
        "uq_open_hold_per_patron_manifestation",
        "holds",
        ["manifestation_id", "patron_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'ready')"),
        postgresql_where=sa.text("status IN ('pending', 'ready')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_open_hold_per_patron_manifestation",
        table_name="holds",
        sqlite_where=sa.text("status IN ('pending', 'ready')"),
        postgresql_where=sa.text("status IN ('pending', 'ready')"),
    )
