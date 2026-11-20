"""US08: one saved offer per URL and user

Revision ID: d3c4e5f6a7b8
Revises: c2b3d4e5f6a7
Create Date: 2026-11-20 00:00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3c4e5f6a7b8"
down_revision: str | None = "c2b3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = "uq_job_offers_user_source_url"


def upgrade() -> None:
    # Keep a single row per (user, url) so the constraint can be created on existing data.
    op.execute(
        """
        DELETE FROM job_offers AS a
        USING job_offers AS b
        WHERE a.user_id = b.user_id
          AND a.source_url = b.source_url
          AND a.id > b.id
        """
    )
    op.create_unique_constraint(CONSTRAINT, "job_offers", ["user_id", "source_url"])


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, "job_offers", type_="unique")
