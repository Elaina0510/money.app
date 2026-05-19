"""Record-Tag association model (many-to-many)."""

from sqlmodel import Field, SQLModel


class RecordTag(SQLModel, table=True):
    """Association table between records and tags."""

    __tablename__ = "record_tags"

    id: int | None = Field(default=None, primary_key=True)
    record_id: int = Field(
        nullable=False, foreign_key="records.id", ondelete="CASCADE"
    )
    tag_id: int = Field(
        nullable=False, foreign_key="tags.id", ondelete="CASCADE"
    )
