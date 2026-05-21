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


class TagResponse(BaseModel):
    """Schema for tag response."""

    id: int
    name: str
    category_id: int | None = None  # v1.1 新增
    created_at: str
