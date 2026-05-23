"""Record Pydantic schemas."""

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    """Schema for creating a new record."""

    amount: float = Field(..., gt=0, le=99999999.99)
    type: str = Field(..., pattern=r"^(income|expense)$")
    category_id: int = Field(..., gt=0)
    # v1.1 变更：从 tags: list[str] 改为 tag_id: int | None
    tag_id: int | None = Field(default=None, gt=0)
    # v1.1 变更：从 date 改为 consume_time
    consume_time: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",
    )
    # v1.1 新增
    note: str | None = Field(default=None, max_length=500)


class RecordUpdate(BaseModel):
    """Schema for updating an existing record."""

    amount: float | None = Field(default=None, gt=0, le=99999999.99)
    type: str | None = Field(default=None, pattern=r"^(income|expense)$")
    category_id: int | None = Field(default=None, gt=0)
    tag_id: int | None = Field(default=None, gt=0)
    consume_time: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",
    )
    note: str | None = Field(default=None, max_length=500)


class BatchDeleteRequest(BaseModel):
    """Schema for batch delete request."""

    ids: list[int] = Field(..., min_length=1)
