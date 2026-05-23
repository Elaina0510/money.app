"""Budget business logic."""

from calendar import monthrange
from datetime import datetime
from typing import Any

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget
from app.models.category import Category
from app.models.record import Record
from app.models.user import User
from app.schemas.budget import BatchBudgetRequest, BudgetCreate, BudgetUpdate


def _get_month_date_range(month: str) -> tuple[str, str]:
    """Get start and end date for a month string (YYYY-MM)."""
    year_str, month_str = month.split("-")
    start_date = f"{year_str}-{month_str}-01"
    _, last_day = monthrange(int(year_str), int(month_str))
    end_date = f"{year_str}-{month_str}-{last_day:02d}"
    return start_date, end_date


async def get_budgets(
    db: AsyncSession,
    month: str,
    type_filter: str | None = None,
    current_user: User | None = None,
) -> list[dict[str, Any]]:
    """Get budgets for a given month, optionally filtered by category type."""
    if type_filter:
        # Join with categories to filter by type
        stmt = (
            select(Budget)
            .join(Category, Budget.category_id == Category.id)
            .where(Budget.month == month, Category.type == type_filter)
        )
    else:
        stmt = select(Budget).where(Budget.month == month)

    # Data isolation: filter by user_id
    if current_user:
        stmt = stmt.where(Budget.user_id == current_user.id)
    else:
        stmt = stmt.where(Budget.user_id.is_(None))

    result = await db.exec(stmt)
    budgets = list(result.all())

    items = []
    for budget in budgets:
        items.append(await _enrich_budget(db, budget, month))

    return items


async def _enrich_budget(
    db: AsyncSession, budget: Budget, month: str,
    category_id: int | None = None,
    budget_amount: float | None = None,
) -> dict[str, Any]:
    """Enrich a budget with category info and spent amount."""
    # Extract all scalar values immediately before any DB operations,
    # because the model may become expired after subsequent commits
    # in the same session.
    bid = budget.id
    cid = category_id if category_id is not None else budget.category_id
    amt = budget_amount if budget_amount is not None else budget.amount
    bmonth = budget.month
    bcreated = budget.created_at
    bupdated = budget.updated_at

    cat_stmt = select(Category).where(Category.id == cid)
    cat_result = await db.exec(cat_stmt)
    category = cat_result.first()
    category_name = category.name if category else "未知"
    cat_type = category.type if category else "expense"

    # Calculate spent amount for this category in the given month
    start_date, end_date = _get_month_date_range(month)

    spent_stmt = select(
        func.coalesce(func.sum(Record.amount), 0)
    ).where(
        Record.category_id == cid,
        Record.type == "expense",
        Record.consume_time >= start_date,
        Record.consume_time <= end_date,
    )
    spent_result = await db.exec(spent_stmt)
    spent = float(spent_result.one() or 0)

    remaining = max(amt - spent, 0)
    percentage = round((spent / amt * 100), 1) if amt > 0 else 0

    return {
        "id": bid,
        "category_id": cid,
        "category_name": category_name,
        "type": cat_type,
        "month": bmonth,
        "amount": amt,
        "spent": spent,
        "remaining": remaining,
        "percentage": percentage,
        "created_at": bcreated,
        "updated_at": bupdated,
    }


async def create_or_update_budget(
    db: AsyncSession, data: BudgetCreate, current_user: User | None = None
) -> Budget:
    """Create a budget or update if exists (upsert)."""
    user_id = current_user.id if current_user else None
    # Check if budget already exists for this category and month
    stmt = select(Budget).where(
        Budget.category_id == data.category_id,
        Budget.month == data.month,
        Budget.user_id == user_id,
    )
    result = await db.exec(stmt)
    existing = result.first()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if existing:
        budget_id = existing.id
        existing.amount = data.amount
        existing.updated_at = now
        await db.commit()
        # Re-query to avoid expired attribute issues with async greenlet
        fresh_stmt = select(Budget).where(Budget.id == budget_id)
        fresh_result = await db.exec(fresh_stmt)
        return fresh_result.first()

    budget = Budget(
        category_id=data.category_id,
        month=data.month,
        amount=data.amount,
        user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(budget)
    await db.flush()
    budget_id = budget.id
    await db.commit()
    # Re-query to avoid expired attribute issues with async greenlet
    fresh_stmt = select(Budget).where(Budget.id == budget_id)
    fresh_result = await db.exec(fresh_stmt)
    return fresh_result.first()


async def update_budget(
    db: AsyncSession, budget_id: int, data: BudgetUpdate
) -> Budget | None:
    """Update an existing budget."""
    budget_stmt = select(Budget).where(Budget.id == budget_id)
    result = await db.exec(budget_stmt)
    budget = result.first()
    if not budget:
        return None

    budget.amount = data.amount
    budget.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.commit()
    # Re-query to avoid expired attribute issues with async greenlet
    fresh_stmt = select(Budget).where(Budget.id == budget_id)
    fresh_result = await db.exec(fresh_stmt)
    return fresh_result.first()


async def delete_budget(db: AsyncSession, budget_id: int) -> bool:
    """Delete a budget. Returns True if deleted, False if not found."""
    budget_stmt = select(Budget).where(Budget.id == budget_id)
    result = await db.exec(budget_stmt)
    budget = result.first()
    if not budget:
        return False
    await db.delete(budget)
    await db.commit()
    return True


async def batch_set_budgets(
    db: AsyncSession, data: BatchBudgetRequest, current_user: User | None = None
) -> list[dict[str, Any]]:
    """Batch upsert budgets for a given month and return enriched data."""
    results = []
    for item in data.budgets:
        budget_data = BudgetCreate(
            category_id=item.category_id,
            month=data.month,
            amount=item.amount,
        )
        budget = await create_or_update_budget(db, budget_data, current_user)
        # Enrich immediately while the model is still fresh,
        # before any subsequent commits can expire it.
        enriched = await _enrich_budget(
            db, budget, data.month,
            category_id=item.category_id,
            budget_amount=item.amount,
        )
        results.append(enriched)
    return results


async def get_budget_overview(
    db: AsyncSession, month: str, current_user: User | None = None
) -> dict[str, Any]:
    """Get budget overview for a month."""
    start_date, end_date = _get_month_date_range(month)

    # Get all budgets for this month
    stmt = select(Budget).where(Budget.month == month)
    if current_user:
        stmt = stmt.where(Budget.user_id == current_user.id)
    else:
        stmt = stmt.where(Budget.user_id.is_(None))
    result = await db.exec(stmt)
    budgets = list(result.all())

    total_budget = 0.0
    total_spent = 0.0
    categories_data: list[dict[str, Any]] = []

    for budget in budgets:
        cat_stmt = select(Category).where(Category.id == budget.category_id)
        cat_result = await db.exec(cat_stmt)
        category = cat_result.first()
        category_name = category.name if category else "未知"
        icon = category.icon if category else "mdi-cash"
        cid = budget.category_id

        # Calculate spent
        spent_stmt = select(
            func.coalesce(func.sum(Record.amount), 0)
        ).where(
            Record.category_id == cid,
            Record.type == "expense",
            Record.consume_time >= start_date,
            Record.consume_time <= end_date,
        )
        spent_result = await db.exec(spent_stmt)
        spent = float(spent_result.one() or 0)

        remaining = max(budget.amount - spent, 0)
        percentage = round((spent / budget.amount * 100), 1) if budget.amount > 0 else 0

        # Determine status
        if percentage > 100:
            status = "exceeded"
        elif percentage >= 80:
            status = "warning"
        else:
            status = "normal"

        total_budget += budget.amount
        total_spent += spent

        categories_data.append({
            "category_id": budget.category_id,
            "category_name": category_name,
            "icon": icon,
            "budget": budget.amount,
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage,
            "status": status,
        })

    total_remaining = max(total_budget - total_spent, 0)
    overall_percentage = (
        round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0
    )

    return {
        "month": month,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "overall_percentage": overall_percentage,
        "categories": categories_data,
    }
