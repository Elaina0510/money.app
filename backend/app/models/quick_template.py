"""Quick Template model for manually added quick-accounting templates."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class QuickTemplate(SQLModel, table=True):
    """Quick template for manually added quick-accounting shortcuts."""

    __tablename__ = "quick_templates"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE"
    )
    tag_id: int | None = Field(
        default=None, nullable=True, foreign_key="tags.id", ondelete="SET NULL"
    )
    category_id: int | None = Field(
        default=None, nullable=True, foreign_key="categories.id", ondelete="SET NULL"
    )
    type: str = Field(nullable=False)  # "expense" / "income"
    amount: float = Field(nullable=False)
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
