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


class RecordResponse(BaseModel):
    """Schema for record detail response."""

    id: int
    amount: float
    type: str
    category_id: int
    category_name: str = ""
    category_icon: str = ""  # v1.1 新增
    tag: dict | None = None  # v1.1 变更：替换 tags: list[str]
    attachment_ids: list[int] = []
    consume_time: str  # v1.1 变更：替换 date
    note: str | None = None  # v1.1 新增
    created_at: str
    updated_at: str


class RecordListResponse(BaseModel):
    """Schema for paginated record list response."""

    items: list[RecordResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class BatchDeleteRequest(BaseModel):
    """Schema for batch delete request."""

    ids: list[int] = Field(..., min_length=1)
