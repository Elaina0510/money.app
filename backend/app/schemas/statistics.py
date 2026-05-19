"""Statistics Pydantic schemas."""

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    """Schema for summary statistics."""

    total_income: float = 0
    total_expense: float = 0
    balance: float = 0
    transaction_count: int = 0
    period: str = ""
    start_date: str = ""
    end_date: str = ""


class CategoryStatItem(BaseModel):
    """Schema for a single category statistic item."""

    category_id: int
    category_name: str = ""
    icon: str = ""
    total: float = 0
    percentage: float = 0
    count: int = 0


class CategoryStatResponse(BaseModel):
    """Schema for category statistics."""

    items: list[CategoryStatItem] = []
    total_expense: float = 0


class TagStatItem(BaseModel):
    """Schema for a single tag statistic item."""

    tag_name: str = ""
    total: float = 0
    count: int = 0


class TagStatResponse(BaseModel):
    """Schema for tag statistics."""

    items: list[TagStatItem] = []


class TrendItem(BaseModel):
    """Schema for a single trend data point."""

    period: str = ""
    income: float = 0
    expense: float = 0
    balance: float = 0


class TrendResponse(BaseModel):
    """Schema for trend statistics."""

    items: list[TrendItem] = []
