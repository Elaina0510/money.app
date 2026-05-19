"""Category Pydantic schemas."""

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Schema for creating a new category."""

    name: str = Field(..., min_length=1, max_length=50)
    type: str = Field(..., pattern=r"^(income|expense)$")
    icon: str = Field(default="mdi-cash", max_length=50)
    sort_order: int = Field(default=0, ge=0)


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = Field(default=None, max_length=50)
    sort_order: int | None = Field(default=None, ge=0)


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: int
    name: str
    type: str
    icon: str
    sort_order: int
    is_preset: int
    created_at: str
