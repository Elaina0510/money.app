"""Budget model for monthly budget management."""

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Budget(SQLModel, table=True):
    """Budget model for monthly category budgets."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("category_id", "month", name="idx_budgets_category_month"),
    )

    id: int | None = Field(default=None, primary_key=True)
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
