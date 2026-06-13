"""OperationHistory model for tracking rollback-able operations."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class OperationHistory(SQLModel, table=True):
    """Operation history for data rollback."""

    __tablename__ = "operation_history"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE", index=True
    )
    operation_type: str = Field(max_length=20)  # create/update/delete/batch_delete/csv_import
    description: str
    snapshot_before: str | None = Field(default=None)  # JSON string
    snapshot_after: str | None = Field(default=None)   # JSON string
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
