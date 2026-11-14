from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for every SQLAlchemy model.

    Import new models in app/models/__init__.py so Alembic autogenerate can see them.
    """
