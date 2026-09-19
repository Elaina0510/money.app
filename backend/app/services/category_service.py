"""Category business logic."""

from typing import Any

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget
from app.models.category import Category
from app.models.record import Record
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate

# 「其他」分类判定唯一真源（M2 create/update 与 M3 reorder 共用，禁止散落字面量）
# 判据 = 类型对应且同名（决策 D3）：预设行与其 Copy-on-Write 用户副本同名，一并命中
OTHER_CATEGORY_NAMES: dict[str, str] = {"expense": "其他支出", "income": "其他收入"}


def _is_other_category(cat: Category) -> bool:
    """「其他」= 类型对应且同名（预设行与其 Copy-on-Write 用户副本同名，一并命中）。"""
    return cat.name == OTHER_CATEGORY_NAMES.get(cat.type)


def _is_other_row(type_: str, name: str) -> bool:
    """按类型 + 名称判定是否「其他」分类行（尚未落库的行同样适用）。"""
    return name == OTHER_CATEGORY_NAMES.get(type_)


async def _visible_categories(
    db: AsyncSession, type_filter: str | None = None, current_user: User | None = None
) -> list[Category]:
    """该用户（可选类型）可见的分类集合，按 (sort_order, id) 升序。

    与 get_categories 同一查询逻辑，供 create 的排序计算与 reorder 复用：
    presets + own custom ones；已有用户副本（同 name+type）的预设被排除，
    即副本生效、预设隐藏，不会重复计入。
    """
    query = select(Category).order_by(Category.sort_order, Category.id)
    if type_filter:
        query = query.where(Category.type == type_filter)
    if current_user:
        # Subquery: (name, type) pairs of user's custom categories
        user_custom = (
            select(Category.name, Category.type)
            .where(
                Category.user_id == current_user.id,
                Category.is_preset == 0,
            )
            .subquery()
        )
        # Include: user's own categories + presets NOT overridden by user
        not_overridden = (
            select(user_custom.c.name)
            .where(
                user_custom.c.name == Category.name,
                user_custom.c.type == Category.type,
            )
            .exists()
        )
        query = query.where(
            (Category.user_id == current_user.id)
            | ((Category.is_preset == 1) & ~not_overridden)
        )
    else:
        query = query.where(Category.user_id.is_(None))
    result = await db.exec(query)
    return list(result.all())


async def get_categories(
    db: AsyncSession, type_filter: str | None = None, current_user: User | None = None
) -> list[Category]:
    """Get all categories visible to the user: presets + own custom ones.

    Presets that have a user-specific copy (same name+type) are excluded
    to avoid duplicates — the user copy takes precedence.
    """
    return await _visible_categories(db, type_filter, current_user)


async def _next_sort_order(
    db: AsyncSession, type_: str, current_user: User | None = None
) -> int:
    """新增分类的服务端排序：追加到该类型分组末尾、「其他」之前。

    规则（设计 §2.2.2）：
    1. base = 可见集合中非「其他」行的最大 sort_order（空集合按 0）；
    2. 组内存在「其他」时结果钳制为严格小于其 sort——「其他」恒置尾是硬约束，
       「其他」本身不在末尾的异常数据同样自愈；
    3. 组内无「其他」时直接 max+1 追加末尾。
    """
    visible = await _visible_categories(db, type_, current_user)
    base = max((c.sort_order for c in visible if not _is_other_category(c)), default=0)
    other = next((c for c in visible if _is_other_category(c)), None)
    if other is None:
        return base + 1
    return min(base + 1, other.sort_order - 1)


async def create_category(
    db: AsyncSession, data: CategoryCreate, current_user: User | None = None
) -> Category:
    """Create a new custom category.

    sort_order 未提供（None）时由服务端计算追加位置；显式传入则原样写入（向后兼容）。
    """
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

    sort_order = data.sort_order
    if sort_order is None:
        sort_order = await _next_sort_order(db, data.type, current_user)

    category = Category(
        name=data.name,
        type=data.type,
        icon=data.icon,
        sort_order=sort_order,
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
    """Update an existing category.

    For preset categories, implements copy-on-write: instead of modifying
    the global preset, creates (or updates) a user-specific copy.

    v1.4.2 起：「其他」分类名称不可修改；单个分类 PUT 一律忽略 sort_order
    （排序只经 M3 的批量重排接口变更）。
    """
    category = await db.get(Category, category_id)
    if not category:
        return None

    # 禁改「其他」名（决策 D3）：校验置于 CoW 与普通更新两条路径之前
    if _is_other_row(category.type, category.name):
        new_name = data.name
        if new_name and not _is_other_row(category.type, new_name):
            raise ValueError("「其他」分类名称不可修改")

    user_id = current_user.id if current_user else None
    update_data = data.model_dump(exclude_unset=True)
    # 排序不随单个 PUT 变化：剔除后 CoW 副本恒继承预设自身 sort_order
    update_data.pop("sort_order", None)

    # Copy-on-Write: modifying a preset → create/update user copy
    if category.is_preset == 1 and user_id is not None:
        # Check if user already has a custom copy with same name+type
        dup_stmt = select(Category).where(
            Category.name == category.name,
            Category.type == category.type,
            Category.user_id == user_id,
            Category.is_preset == 0,
        )
        existing = (await db.exec(dup_stmt)).first()

        if existing:
            for key, value in update_data.items():
                setattr(existing, key, value)
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            copy = Category(
                name=category.name,
                type=category.type,
                icon=update_data.get("icon", category.icon),
                sort_order=update_data.get("sort_order", category.sort_order),
                is_preset=0,
                user_id=user_id,
            )
            db.add(copy)
            await db.commit()
            await db.refresh(copy)
            return copy

    # Non-preset: ownership check
    if category.is_preset == 0:
        if current_user is None:
            if category.user_id is not None:
                raise PermissionError("无权修改此分类")
        elif category.user_id != current_user.id:
            raise PermissionError("无权修改此分类")

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

    # Preset categories cannot be deleted
    if category.is_preset == 1:
        raise PermissionError("预设分类不可删除")

    # Ownership check: custom categories only deletable by creator
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
