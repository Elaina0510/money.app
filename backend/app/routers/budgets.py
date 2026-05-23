"""Budget API router."""

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.budget import (
    BatchBudgetRequest,
    BudgetCreate,
    BudgetUpdate,
)
from app.services import budget_service
from app.utils.auth import get_current_user
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/budgets", tags=["预算管理"])


@router.get("")
async def list_budgets(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="月份 YYYY-MM"),
    type: str | None = Query(None, description="分类类型: income/expense"),
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Get budgets for a given month, optionally filtered by category type."""
    budgets = await budget_service.get_budgets(db, month, type, current_user)
    return success_response(data=budgets)


@router.post("")
async def create_budget(
    data: BudgetCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Create or update a budget (upsert)."""
    try:
        budget = await budget_service.create_or_update_budget(db, data, current_user)
        # Enrich for response
        enriched = await budget_service._enrich_budget(
            db, budget, data.month, category_id=data.category_id, budget_amount=data.amount
        )
        return success_response(data=enriched, message="预算设置成功")
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return error_response(Code.CONFLICT, "该预算已存在")
        raise


@router.put("/{budget_id}")
async def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update a budget."""
    budget = await budget_service.update_budget(db, budget_id, data)
    if not budget:
        return error_response(Code.NOT_FOUND, "预算不存在")
    # Read month and amount from the data object since budget model
    # may have expired attributes after commit
    enriched = await budget_service._enrich_budget(
        db, budget, budget.month, budget_amount=data.amount
    )
    return success_response(data=enriched, message="预算更新成功")


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a budget."""
    deleted = await budget_service.delete_budget(db, budget_id)
    if not deleted:
        return error_response(Code.NOT_FOUND, "预算不存在")
    return success_response(message="预算删除成功")


@router.post("/batch")
async def batch_set_budgets(
    data: BatchBudgetRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Batch set budgets (upsert)."""
    enriched_list = await budget_service.batch_set_budgets(db, data, current_user)
    return success_response(data=enriched_list, message="预算批量设置成功")

