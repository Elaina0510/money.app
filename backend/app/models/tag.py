"""Tag model."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    """Tag model for free-text labels on records."""

    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    # v1.1 新增：关联分类，可为 null
    category_id: int | None = Field(
        default=None,
        nullable=True,
        foreign_key="categories.id",
        ondelete="SET NULL",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
