"""US08: create job_offers table

Revision ID: c2b3d4e5f6a7
Revises: ffcdc0e04993
Create Date: 2026-11-19 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2b3d4e5f6a7"
down_revision: str | None = "ffcdc0e04993"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=10), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_offers_user_id"), "job_offers", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_offers_user_id"), table_name="job_offers")
    op.drop_table("job_offers")
