import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

OfferText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=50, max_length=50_000)
]


class JobOfferCreate(BaseModel):
    text: OfferText


class JobOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: str
    source_url: str | None = None
    content: str
    created_at: datetime
