"""Attachment model."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Attachment(SQLModel, table=True):
    """Attachment model for image files associated with records."""

    __tablename__ = "attachments"

    id: int | None = Field(default=None, primary_key=True)
    record_id: int | None = Field(
        default=None,
        nullable=True,
        foreign_key="records.id",
        ondelete="SET NULL",
    )
    filename: str = Field(nullable=False)  # Original filename
    stored_path: str = Field(nullable=False)  # Relative path from uploads/
    file_size: int = Field(nullable=False)  # Size in bytes
    mime_type: str = Field(nullable=False)  # MIME type
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
