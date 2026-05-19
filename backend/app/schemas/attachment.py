"""Attachment Pydantic schemas."""

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    """Schema for attachment response."""

    id: int
    record_id: int | None = None
    filename: str
    url: str = ""
    file_size: int
    mime_type: str
    created_at: str


class AttachmentListResponse(BaseModel):
    """Schema for list of attachments."""

    items: list[AttachmentResponse] = []
