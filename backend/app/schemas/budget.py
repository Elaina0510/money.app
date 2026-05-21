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


class BudgetResponse(BaseModel):
    """Schema for budget response."""

    id: int
    category_id: int
    category_name: str = ""
    type: str = ""
    month: str
    amount: float
    spent: float = 0
    remaining: float = 0
    percentage: float = 0
    created_at: str
    updated_at: str


class BudgetOverviewCategory(BaseModel):
    """Schema for a single category in budget overview."""

    category_id: int
    category_name: str = ""
    icon: str = ""
    budget: float = 0
    spent: float = 0
    remaining: float = 0
    percentage: float = 0
    status: str = "normal"  # normal / warning / exceeded


class BudgetOverviewResponse(BaseModel):
    """Schema for budget overview."""

    month: str
    total_budget: float = 0
    total_spent: float = 0
    total_remaining: float = 0
    overall_percentage: float = 0
    categories: list[BudgetOverviewCategory] = []


class BatchBudgetItem(BaseModel):
    """Schema for a single item in batch budget."""

    category_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0, le=99999999.99)


class BatchBudgetRequest(BaseModel):
    """Schema for batch budget creation/update."""

    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    budgets: list[BatchBudgetItem] = Field(..., min_length=1)
