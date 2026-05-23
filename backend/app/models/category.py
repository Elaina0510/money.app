"""Category model."""

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Category(SQLModel, table=True):
    """Category model for income/expense classification."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", "type", "user_id", name="idx_categories_name_type_user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE"
    )
    name: str = Field(nullable=False)
    type: str = Field(nullable=False)  # "income" or "expense"
    icon: str = Field(default="mdi-cash", nullable=False)
    sort_order: int = Field(default=0, nullable=False)
    is_preset: int = Field(default=0, nullable=False)  # 0=custom, 1=preset
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
