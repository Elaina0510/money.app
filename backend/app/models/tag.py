"""Tag model."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    """Tag model for free-text labels on records."""

    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
