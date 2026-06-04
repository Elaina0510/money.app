"""Category business logic."""

from typing import Any

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget
from app.models.category import Category
from app.models.record import Record
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate


async def get_categories(
    db: AsyncSession, type_filter: str | None = None, current_user: User | None = None
) -> list[Category]:
    """Get all categories visible to the user: presets + own custom ones."""
    query = select(Category).order_by(Category.sort_order, Category.id)
    if type_filter:
        query = query.where(Category.type == type_filter)
    # Filter by user_id: preset categories visible to all, custom only to owner
    if current_user:
        query = query.where((Category.is_preset == 1) | (Category.user_id == current_user.id))
    else:
        query = query.where(Category.user_id.is_(None))
    result = await db.exec(query)
    return list(result.all())


async def create_category(
    db: AsyncSession, data: CategoryCreate, current_user: User | None = None
) -> Category:
    """Create a new custom category."""
    # Check for duplicate name+type for this user
    user_id = current_user.id if current_user else None
    dup_stmt = select(Category).where(
        Category.name == data.name,
        Category.type == data.type,
        Category.user_id == user_id,
    )
    dup_result = await db.exec(dup_stmt)
    if dup_result.first():
        raise ValueError("该名称的分类已存在")

    category = Category(
        name=data.name,
        type=data.type,
        icon=data.icon,
        sort_order=data.sort_order,
        is_preset=0,
        user_id=user_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    category_id: int,
    data: CategoryUpdate,
    current_user: User | None = None,
) -> Category | None:
    """Update an existing category."""
    category = await db.get(Category, category_id)
    if not category:
        return None
    # Ownership check: preset categories editable by all, custom only by creator
    if category.is_preset == 0:
        if current_user is None:
            # Anonymous user: only allowed to modify anonymous data (user_id=None)
            if category.user_id is not None:
                raise PermissionError("无权修改此分类")
        elif category.user_id != current_user.id:
            raise PermissionError("无权修改此分类")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(
    db: AsyncSession, category_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Delete a category with cascade (records + budgets).

    Returns None on error (not found), or a dict with deleted_records count on success.
    Raises PermissionError if the user is not authorized.
    """
    category = await db.get(Category, category_id)
    if not category:
        return None

    # Ownership check: preset categories deletable by all, custom only by creator
    if category.is_preset == 0:
        if current_user is None:
            # Anonymous user: only allowed to delete anonymous data (user_id=None)
            if category.user_id is not None:
                raise PermissionError("无权删除此分类")
        elif category.user_id != current_user.id:
            raise PermissionError("无权删除此分类")

    # Count associated records for the response
    count_stmt = select(func.count(Record.id)).where(Record.category_id == category_id)
    count_result = await db.exec(count_stmt)
    record_count: int = count_result.one() or 0

    # Cascade delete: remove associated budgets first, then records, then category
    budget_stmt = select(Budget).where(Budget.category_id == category_id)
    budget_result = await db.exec(budget_stmt)
    for budget in budget_result.all():
        await db.delete(budget)

    record_stmt = select(Record).where(Record.category_id == category_id)
    record_result = await db.exec(record_stmt)
    for record in record_result.all():
        await db.delete(record)

    await db.delete(category)
    await db.commit()
    return {"deleted_records": record_count}


async def restore_default_categories(
    db: AsyncSession, current_user: User | None = None
) -> dict[str, int]:
    """Restore default categories: delete custom ones, reset preset sort_order.

    - Delete all is_preset=0 custom categories for the user
    - Associated records保留, category_id set to NULL
    - Associated budgets deleted
    - Reset preset categories' sort_order to defaults
    """
    from app.main import PRESET_CATEGORIES

    user_id = current_user.id if current_user else None

    # Step 1: Delete custom categories (is_preset=0)
    custom_query = select(Category).where(
        Category.is_preset == 0,
        Category.user_id == user_id,
    )
    custom_result = await db.exec(custom_query)
    custom_categories = list(custom_result.all())

    deleted_count = 0
    affected_records = 0

    for cat in custom_categories:
        # Count associated records
        count_stmt = select(func.count(Record.id)).where(Record.category_id == cat.id)
        count_result = await db.exec(count_stmt)
        record_count = count_result.one() or 0
        affected_records += record_count

        # Set associated records' category_id to NULL (preserve records)
        record_stmt = select(Record).where(Record.category_id == cat.id)
        record_result = await db.exec(record_stmt)
        for record in record_result.all():
            record.category_id = None

        # Delete associated budgets
        budget_stmt = select(Budget).where(Budget.category_id == cat.id)
        budget_result = await db.exec(budget_stmt)
        for budget in budget_result.all():
            await db.delete(budget)

        # Delete the category
        await db.delete(cat)
        deleted_count += 1

    # Step 2: Reset preset categories' sort_order
    for preset in PRESET_CATEGORIES:
        stmt = select(Category).where(
            Category.name == preset["name"],
            Category.type == preset["type"],
            Category.is_preset == 1,
        )
        result = await db.exec(stmt)
        category = result.first()
        if category:
            category.sort_order = preset["sort_order"]
            category.icon = preset["icon"]

    await db.commit()
    return {"deleted_categories": deleted_count, "affected_records": affected_records}
