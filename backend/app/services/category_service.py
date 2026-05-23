"""Category business logic."""

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.category import Category
from app.models.record import Record
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.response import Code


async def get_categories(
    db: AsyncSession, type_filter: str | None = None, current_user: User | None = None
) -> list[Category]:
    """Get all categories visible to the user: presets + own custom ones."""
    query = select(Category).order_by(Category.sort_order, Category.id)
    if type_filter:
        query = query.where(Category.type == type_filter)
    # Filter by user_id: preset categories visible to all, custom only to owner
    if current_user:
        query = query.where(
            (Category.is_preset == 1) | (Category.user_id == current_user.id)
        )
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
    db: AsyncSession, category_id: int, data: CategoryUpdate
) -> Category | None:
    """Update an existing category."""
    category = await db.get(Category, category_id)
    if not category:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int) -> dict | None:
    """Delete a category. Returns None if successful, or an error dict."""
    category = await db.get(Category, category_id)
    if not category:
        return {"code": Code.NOT_FOUND, "message": "分类不存在"}

    # Check if any records reference this category
    stmt = select(func.count(Record.id)).where(Record.category_id == category_id)
    result = await db.exec(stmt)
    count = result.one()
    if count > 0:
        return {
            "code": Code.CONFLICT,
            "message": f"该分类下有 {count} 条记录，无法删除",
        }

    await db.delete(category)
    await db.commit()
    return None
