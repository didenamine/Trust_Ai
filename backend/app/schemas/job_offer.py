import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, HttpUrl, StringConstraints, model_validator

OfferText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=50, max_length=50_000)
]


class JobOfferCreate(BaseModel):
    """A job offer is added either as pasted `text` or as a `url` to fetch, never both."""

    text: OfferText | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def check_exactly_one_source(self) -> Self:
        if (self.text is None) == (self.url is None):
            raise ValueError("Fournissez soit 'url', soit 'text' (un seul des deux).")
        return self


class JobOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: str
    source_url: str | None = None
    content: str
    created_at: datetime
