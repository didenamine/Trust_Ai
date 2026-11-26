import re
import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

OfferText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=50, max_length=50_000)
]
# Control characters (except tab and newline) that PostgreSQL or the analysis cannot handle.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class JobOfferCreate(BaseModel):
    """A job offer is added either as pasted `text` or as a `url` to fetch, never both."""

    text: OfferText | None = None
    url: HttpUrl | None = None

    @field_validator("text", mode="before")
    @classmethod
    def clean_text(cls, value: object) -> object:
        """Accept any pasted text: normalize line endings and drop control characters."""
        if isinstance(value, str):
            return _CONTROL_CHARS_RE.sub("", value.replace("\r\n", "\n").replace("\r", "\n"))
        return value

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


class JobOfferSummary(BaseModel):
    """An offer as listed on the "my offers" page: title and description, no raw content."""

    id: uuid.UUID
    source_type: str
    source_url: str | None = None
    title: str
    description: str
    created_at: datetime
