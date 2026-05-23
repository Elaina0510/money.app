"""Budget model for monthly budget management."""

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Budget(SQLModel, table=True):
    """Budget model for monthly category budgets."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("category_id", "month", "user_id", name="idx_budgets_category_month_user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE"
    )
    category_id: int = Field(nullable=False, foreign_key="categories.id")
    month: str = Field(nullable=False)  # YYYY-MM format
    amount: float = Field(nullable=False)  # Budget amount
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
