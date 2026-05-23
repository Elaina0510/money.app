"""Budget Pydantic schemas."""

from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    """Schema for creating a new budget."""

    category_id: int = Field(..., gt=0)
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    amount: float = Field(..., gt=0, le=99999999.99)


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""

    amount: float = Field(..., gt=0, le=99999999.99)


class BatchBudgetItem(BaseModel):
    """Schema for a single item in batch budget."""

    category_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0, le=99999999.99)


class BatchBudgetRequest(BaseModel):
    """Schema for batch budget creation/update."""

    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    budgets: list[BatchBudgetItem] = Field(..., min_length=1)
