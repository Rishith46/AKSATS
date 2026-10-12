from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    kind: str
    original_filename: str
    mime_type: str | None
    size_bytes: int | None
    sha256: str | None
    version_no: int | None
    is_current: bool
    uploaded_by: int | None
    uploaded_at: datetime