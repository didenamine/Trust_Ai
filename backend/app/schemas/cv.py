import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
