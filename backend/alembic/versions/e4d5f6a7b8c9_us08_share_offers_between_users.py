"""US08: share URL offers between users (user_offers link table)

Revision ID: e4d5f6a7b8c9
Revises: d3c4e5f6a7b8
Create Date: 2026-11-20 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4d5f6a7b8c9"
down_revision: str | None = "d3c4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_offers",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["job_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "offer_id"),
    )
    op.create_index(op.f("ix_user_offers_offer_id"), "user_offers", ["offer_id"], unique=False)

    # Every existing offer becomes a link between its owner and the offer.
    op.execute(
        "INSERT INTO user_offers (user_id, offer_id, created_at) "
        "SELECT user_id, id, created_at FROM job_offers"
    )

    # Offers saved by several users under the same URL: keep the oldest, move the links to it.
    op.execute(
        """
        CREATE TEMPORARY TABLE offer_merge ON COMMIT DROP AS
        SELECT id,
               first_value(id) OVER (PARTITION BY source_url ORDER BY created_at, id) AS keep_id
        FROM job_offers
        WHERE source_url IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE user_offers AS uo
        SET offer_id = m.keep_id
        FROM offer_merge AS m
        WHERE uo.offer_id = m.id AND m.id <> m.keep_id
        """
    )
    op.execute(
        """
        DELETE FROM job_offers AS j
        USING offer_merge AS m
        WHERE j.id = m.id AND m.id <> m.keep_id
        """
    )

    # The owner now lives in user_offers; a URL is unique across all users.
    op.drop_constraint("uq_job_offers_user_source_url", "job_offers", type_="unique")
    op.drop_index("ix_job_offers_user_id", table_name="job_offers")
    op.drop_column("job_offers", "user_id")
    op.create_unique_constraint("uq_job_offers_source_url", "job_offers", ["source_url"])


def downgrade() -> None:
    raise NotImplementedError("Shared offers cannot be split back per user safely.")
