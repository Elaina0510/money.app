"""Record Pydantic schemas."""

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    """Schema for creating a new record."""

    amount: float = Field(..., gt=0, le=99999999.99)
    type: str = Field(..., pattern=r"^(income|expense)$")
    category_id: int = Field(..., gt=0)
    tags: list[str] = Field(default_factory=list)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    created_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


class RecordUpdate(BaseModel):
    """Schema for updating an existing record."""

    amount: float | None = Field(default=None, gt=0, le=99999999.99)
    type: str | None = Field(default=None, pattern=r"^(income|expense)$")
    category_id: int | None = Field(default=None, gt=0)
    tags: list[str] | None = Field(default=None)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    created_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


class RecordResponse(BaseModel):
    """Schema for record detail response."""

    id: int
    amount: float
    type: str
    category_id: int
    category_name: str = ""
    tags: list[str] = []
    attachment_ids: list[int] = []
    date: str
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
