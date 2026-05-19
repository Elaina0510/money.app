"""Tag Pydantic schemas."""

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    """Schema for creating a new tag."""

    name: str = Field(..., min_length=1, max_length=100)


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: str = Field(..., min_length=1, max_length=100)


class TagResponse(BaseModel):
    """Schema for tag response."""

    id: int
    name: str
    created_at: str
