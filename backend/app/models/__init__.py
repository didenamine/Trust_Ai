"""SQLAlchemy models.

Import every model module here so that `Base.metadata` knows about it
(required by Alembic autogenerate), e.g.:

    from app.models.user import User  # noqa: F401
"""

from app.db.base import Base

__all__ = ["Base"]
