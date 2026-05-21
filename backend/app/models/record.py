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
    # v1.1 变更：从多标签改为单标签，直接存 tag_id
    tag_id: int | None = Field(
        default=None,
        nullable=True,
        foreign_key="tags.id",
        ondelete="SET NULL",
    )
    # v1.1 变更：新增 consume_time，替代原有的 date
    consume_time: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"),
        nullable=False,
    )
    # v1.1 新增：备注
    note: str | None = Field(default=None, nullable=True)
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
