"""Statistics Pydantic schemas."""

from pydantic import BaseModel


class CategoryStatItem(BaseModel):
    """Schema for a single category statistic item."""

    category_id: int
    category_name: str = ""
    icon: str = ""
    total: float = 0
    percentage: float = 0
    count: int = 0


class TagStatItem(BaseModel):
    """Schema for a single tag statistic item."""

    tag_name: str = ""
    total: float = 0
    count: int = 0


class TrendItem(BaseModel):
    """Schema for a single trend data point."""

    period: str = ""
    income: float = 0
    expense: float = 0
    balance: float = 0
