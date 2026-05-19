"""Record model."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Record(SQLModel, table=True):
    """Record model for income/expense transactions."""

    __tablename__ = "records"

    id: int | None = Field(default=None, primary_key=True)
    amount: float = Field(nullable=False)  # Always positive, type distinguishes income/expense
    type: str = Field(nullable=False)  # "income" or "expense"
    category_id: int = Field(nullable=False, foreign_key="categories.id")
    date: str = Field(nullable=False)  # YYYY-MM-DD
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
