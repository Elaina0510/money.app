"""Tag Pydantic schemas."""

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    """Schema for creating a new tag."""

    name: str = Field(..., min_length=1, max_length=100)
    category_id: int | None = Field(default=None, gt=0)  # v1.1 新增


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    category_id: int | None = Field(default=None, gt=0)  # v1.1 新增


class TagBatchDelete(BaseModel):
    """Schema for batch tag soft-delete (v1.4.4 M1)."""

    # 数量无上限（需求裁定 M 为数十至数百级）；空数组/缺失由 FastAPI 默认 422 兜底
    ids: list[int] = Field(..., min_length=1)


class TagResponse(BaseModel):
    """Schema for tag response."""

    id: int
    name: str
    category_id: int | None = None  # v1.1 新增
    created_at: str
