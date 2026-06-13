"""Import request schemas."""

from pydantic import BaseModel, Field


class CategoryMappingItem(BaseModel):
    """Single category mapping item."""

    action: str = Field(..., pattern="^(map|create)$")
    target_id: int | None = None  # Required when action="map"
    type: str | None = None  # Required when action="create" (expense/income)


class TagMappingItem(BaseModel):
    """Single tag mapping item."""

    action: str = Field(..., pattern="^(map|create)$")
    target_id: int | None = None  # Required when action="map"
    category_id: int | None = None  # Required when action="create"


class ImportCsvRequest(BaseModel):
    """CSV import confirm request body."""

    cache_id: str
    format: str = Field(..., pattern="^(native|cashew)$")
    category_mapping: dict[str, CategoryMappingItem]
    tag_mapping: dict[str, TagMappingItem]


class ImportSqlRequest(BaseModel):
    """SQL import confirm request body."""

    cache_id: str
    format: str = Field(..., pattern="^(text_sql|sqlite_binary)$")
    is_third_party: bool = False
    merge_mode: str = Field(default="insert_all", pattern="^insert_all$")
    category_mapping: dict[str, CategoryMappingItem] | None = None
    tag_mapping: dict[str, TagMappingItem] | None = None
