"""SQLAlchemy models.

Import every model module here so that `Base.metadata` knows about it
(required by Alembic autogenerate), e.g.:

    from app.models.user import User  # noqa: F401
"""

from app.db.base import Base
from app.models.cv_document import CVDocument  # noqa: F401
from app.models.job_offer import JobOffer, UserOffer  # noqa: F401
from app.models.offer_analysis import OfferAnalysis  # noqa: F401
from app.models.profile import Profile  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "Base",
    "CVDocument",
    "JobOffer",
    "OfferAnalysis",
    "Profile",
    "User",
    "UserOffer",
]
