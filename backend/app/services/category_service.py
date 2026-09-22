"""Category business logic."""

from typing import Any, cast

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import SCOPE_INCLUDE, Budget, BudgetCategory
from app.models.category import LEGACY_CATEGORY_TYPE, Category
from app.models.record import Record
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate

# 「其他」分类判定唯一真源（create/update 与 reorder 共用，禁止散落字面量）
# v1.4.3 M8（D11）：判据从「类型对应且同名」改「同名即其他类」——
# 预设行与其 Copy-on-Write 用户副本同名，一并命中
OTHER_CATEGORY_NAME = "其他"
# v1.4.3-boot2（D2/D6）「其他家族」：M2 迁移脚本执行前现场库仍并存旧名行
# （副本实测「其他支出」「其他收入」两预设行 sort_order=99 压在「其他」之后），
# 拖拽可用性不以数据干净为前提，故置尾判据放宽为三名集合。
# OTHER_FAMILY_RANK 即置尾归一化的唯一名次口径，前端 SettingsCategoriesPage 的
# 同名表与之逐位一致（否则出现「保存后二次跳变」）；与 M2 脚本常量以一致性断言钉住。
LEGACY_OTHER_NAMES = ("其他支出", "其他收入")
OTHER_FAMILY_RANK: dict[str, int] = {"其他支出": 0, "其他收入": 1, "其他": 2}


def _is_other_category(cat: Category) -> bool:
    """「其他家族」= 仅按名称判定（预设行与其 CoW 用户副本一并命中）。"""
    return cat.name in OTHER_FAMILY_RANK


def _is_other_row(name: str) -> bool:
    """按名称判定是否「其他家族」行（尚未落库的行同样适用）。"""
    return name in OTHER_FAMILY_RANK


async def _visible_categories(
    db: AsyncSession, current_user: User | None = None
) -> list[Category]:
    """该用户可见的分类集合（单列表，不分收支），按 (sort_order, id) 升序。

    与 get_categories 同一查询逻辑，供 create 的排序计算与 reorder 复用：
    presets + own custom ones；已有用户副本（**同名**，v1.4.3 M8 起仅按 name 匹配，
    无论列上残留 type 值）的预设被排除，即副本生效、预设隐藏，不会重复计入。
    """
    query = select(Category).order_by(Category.sort_order, Category.id)
    if current_user:
        # Subquery: names of user's custom categories
        user_custom = (
            select(Category.name)
            .where(
                Category.user_id == current_user.id,
                Category.is_preset == 0,
            )
            .subquery()
        )
        # Include: user's own categories + presets NOT overridden by user
        not_overridden = (
            select(user_custom.c.name)
            .where(user_custom.c.name == Category.name)
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

    v1.4.3 M8：`type_filter` 保留签名但**一律忽略**（不报错、不过滤，响应恒为全量单列表）；
    预设行若已被用户同名副本遮蔽则不再重复计入。
    """
    del type_filter  # 收支语义自 v1.4.3 起废弃（D2）：参数仅保持接口签名兼容
    return await _visible_categories(db, current_user)


async def _next_sort_order(db: AsyncSession, current_user: User | None = None) -> int:
    """新增分类的服务端排序：追加到全列表末尾、「其他家族」之前。

    规则（设计 §8.2.3 + v1.4.3-boot2 §1.2.1-2）：
    1. base = 可见集合中非家族行的最大 sort_order（空集合按 0）；
    2. 全列表存在家族行（「其他支出 / 其他收入 / 其他」任一）时结果钳制为严格小于
       **家族中 sort 最小者**的 sort——新建行恒落在所有家族行之前，家族不在末位的
       异常数据同样自愈；
    3. 全列表无家族行时直接 max+1 追加末位；
    4. 结果下钳 0：脏数据态（家族行 sort=0 或不在末位）下 `other.sort_order - 1`
       可能 ≤0，SQLite 列无 CHECK，负值会破坏排序假设；钳 0 与导入建的 sort=0 行
       同区，由下一次成功 reorder 归一化 1..n 自愈，不新增状态。
    """
    visible = await _visible_categories(db, current_user)
    base = max((c.sort_order for c in visible if not _is_other_category(c)), default=0)
    family = [c.sort_order for c in visible if _is_other_category(c)]
    if not family:
        return base + 1
    return max(min(base + 1, min(family) - 1), 0)


async def create_category(
    db: AsyncSession, data: CategoryCreate, current_user: User | None = None
) -> Category:
    """Create a new custom category.

    sort_order 未提供（None）时由服务端计算追加位置；显式传入则原样写入（向后兼容）。
    v1.4.3 M8：查重按 name + user_id（跨原收支语义同名亦拒），type 列写占位值。
    """
    # Check for duplicate name for this user
    user_id = current_user.id if current_user else None
    dup_stmt = select(Category).where(
        Category.name == data.name,
        Category.user_id == user_id,
    )
    dup_result = await db.exec(dup_stmt)
    if dup_result.first():
        raise ValueError("该名称的分类已存在")

    sort_order = data.sort_order
    if sort_order is None:
        sort_order = await _next_sort_order(db, current_user)

    category = Category(
        name=data.name,
        type=LEGACY_CATEGORY_TYPE,
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
    （排序只经批量重排接口变更）。v1.4.3 M8 起「其他」判据仅按 name。
    """
    category = await db.get(Category, category_id)
    if not category:
        return None

    # 禁改「其他」名（决策 D11）：校验置于 CoW 与普通更新两条路径之前
    # v1.4.3-boot2（§1.2.1-3）判据**刻意不收家族**：旧名「其他支出 / 其他收入」两行属
    # M2 迁移执行前的过渡态数据，允许改名（改出家族即成普通行，符合用户自助清理的直觉）；
    # 仅「其他」本名维持不可改。故此处用本名比较而非 _is_other_row（家族口径）。
    if category.name == OTHER_CATEGORY_NAME:
        new_name = data.name
        if new_name and new_name != OTHER_CATEGORY_NAME:
            raise ValueError('"其他"分类名称不可修改')

    user_id = current_user.id if current_user else None
    update_data = data.model_dump(exclude_unset=True)
    # 排序不随单个 PUT 变化：剔除后 CoW 副本恒继承预设自身 sort_order
    update_data.pop("sort_order", None)

    # Copy-on-Write: modifying a preset → create/update user copy
    if category.is_preset == 1 and user_id is not None:
        # Check if user already has a custom copy with the same name
        dup_stmt = select(Category).where(
            Category.name == category.name,
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


async def _set_sort_order(
    db: AsyncSession, row: Category, sort_order: int, user_id: int | None
) -> None:
    """把新排序写入用户可见行：预设行走 Copy-on-Write，全局预设行永不被写脏。

    - 用户自有行（is_preset=0）：直接更新；
    - 预设已有用户副本（同名）：更新副本；
    - 预设无副本：按预设字段建副本（is_preset=0、新 sort_order）后写位。
    """
    if row.is_preset == 0 or user_id is None:
        row.sort_order = sort_order
        db.add(row)
        return

    if row.sort_order == sort_order:
        # 预设行本就在目标位：无需建副本，避免无意义的 CoW 膨胀（全局预设行不被写）
        return

    dup_stmt = select(Category).where(
        Category.name == row.name,
        Category.user_id == user_id,
        Category.is_preset == 0,
    )
    existing = (await db.exec(dup_stmt)).first()
    if existing is None:
        existing = Category(
            name=row.name,
            type=row.type,
            icon=row.icon,
            sort_order=sort_order,
            is_preset=0,
            user_id=user_id,
        )
    else:
        existing.sort_order = sort_order
    db.add(existing)


async def reorder_categories(
    db: AsyncSession,
    ids: list[int],
    current_user: User | None = None,
) -> list[Category]:
    """批量重排全量分类排序：单次原子提交、归一化为 1..n 连续。

    规则（设计 §8.2.2 + v1.4.3-boot2 §1.2.1-1）：
    1. ``ids`` 必须是该用户可见集合的全量有序 id——**防漏位的唯一守门**；
    2. 「其他家族」无论提交落点，整体归一化到末尾并按固定名次排尾
       （``OTHER_FAMILY_RANK``：其他支出 < 其他收入 < 其他，「其他」恒最后），
       非家族行保持提交相对次序；本口径与前端 ``normalizeTail`` **逐位一致**，
       否则出现「前端提交序 ≠ 后端落库序」的保存后二次跳变；
    3. 预设行的改序落到用户副本上，全局预设行 sort_order 永不写脏。

    v1.4.3-boot2（D8）：原「可见集合无『其他』行 → ValueError」硬校验已删除——
    防漏位职责已由规则 1 完全覆盖，保留它反而在「用户可见集合无其他行」的极端态
    （如导入产生）把 reorder 再次打死，违背 D1「拖拽永远可用」。

    Raises:
        ValueError: 提交与当前可见分类不一致（缺项/多项/重复）。
    """
    visible = await _visible_categories(db, current_user)
    visible_ids = {c.id for c in visible}
    if len(set(ids)) != len(ids) or set(ids) != visible_ids:
        raise ValueError("排序列表与当前分类不一致")

    by_id = {c.id: c for c in visible}
    submitted = [by_id[cid] for cid in ids]
    # 家族行按名次稳定排序后置尾（sorted 稳定性保证：同名次保持提交序）
    family = sorted(
        (c for c in submitted if _is_other_category(c)),
        key=lambda c: OTHER_FAMILY_RANK[c.name],
    )
    ordered = [c for c in submitted if not _is_other_category(c)] + family

    user_id = current_user.id if current_user else None
    for position, row in enumerate(ordered, start=1):
        await _set_sort_order(db, row, position, user_id)
    await db.commit()

    return await _visible_categories(db, current_user)


async def _dormant_budgets_for_deleted_category(
    db: AsyncSession, category_id: int
) -> int:
    """分类删除的预算级联（v1.4.3-boot2 M3 §3.2.3，任务 3.1–3.3）；
    返回**本次新置为休眠**的预算条数（原语义「返回被整体删掉的预算条数」已改向）。

    v1.4.3 M12 起预算不再挂 ``category_id`` 列，改由 ``budget_categories`` 关联：

    * 先显式删该分类的关联行——连接未启用 ``PRAGMA foreign_keys``，声明式的
      ``ondelete=CASCADE`` 运行时不生效，删除必须由服务层完成（任务 4.1）；
    * **include** 预算若因此不再关联任何分类 → **``budget.dormant = 1`` 休眠保留**，
      不再删除预算行（决策 D4：保留记录、置灰展示、编辑保存即唤醒）；
      空集不再是「无效」而由 dormant 列区分「被删光」与「主动不选=动态全部」（D3）；
    * **exclude** 预算行为不变：仅移出排除集，预算覆盖范围自动扩大，**无休眠概念**
      （它永远有覆盖）——任务 3.2。

    ``delete_category`` 与 ``restore_default_categories`` 共用本函数（任务 3.3），
    全程两条查询（关联行 + 受影响预算的剩余关联），无逐预算 N+1。
    """
    link_stmt = select(BudgetCategory).where(BudgetCategory.category_id == category_id)
    links = list((await db.exec(link_stmt)).all())
    affected = sorted({int(link.budget_id) for link in links})
    for link in links:
        await db.delete(link)
    # DELETE 必须先落盘：SQLAlchemy 同一次 flush 先插后删，且下面的「剩余关联」
    # 查询必须看不到刚被移除的行
    await db.flush()
    if not affected:
        return 0

    # cast(Any, ...)：SQLModel 类字段在 mypy 视角是普通 int 值，其 instrumented
    # Column 身份（`.in_()` 等 Core 表达式操作）不可见；运行时传的就是原对象。
    budget_stmt = select(Budget).where(cast("Any", Budget.id).in_(affected))
    budgets = list((await db.exec(budget_stmt)).all())
    include_ids = [
        int(b.id) for b in budgets if b.scope_mode == SCOPE_INCLUDE and b.id is not None
    ]
    if not include_ids:
        return 0  # 全是 exclude：只移出排除集

    remain_stmt = select(BudgetCategory.budget_id, BudgetCategory.category_id).where(
        cast("Any", BudgetCategory.budget_id).in_(include_ids)
    )
    still_linked = {int(row[0]) for row in (await db.exec(remain_stmt)).all()}

    dormant = 0
    for budget_id in include_ids:
        if budget_id in still_linked:
            continue
        budget = next((b for b in budgets if b.id == budget_id), None)
        if budget is not None:
            budget.dormant = 1  # D4：休眠保留，替代原 db.delete(budget)
            db.add(budget)
            dormant += 1
    return dormant


async def delete_category(
    db: AsyncSession, category_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Delete a category with cascade (records + budget dormancy).

    Returns None on error (not found), or a dict with deleted_records /
    dormant_budgets counts on success（v1.4.3-boot2 M3：include 预算不再被删除，
    失去全部关联时置 ``dormant=1`` 休眠保留，决策 D4）。
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

    # Cascade: budgets（include 失去全部关联 → 置休眠；exclude 仅移出排除集，见 §3.2.3）
    # → records → category
    dormant_budgets = await _dormant_budgets_for_deleted_category(db, category_id)

    record_stmt = select(Record).where(Record.category_id == category_id)
    record_result = await db.exec(record_stmt)
    for record in record_result.all():
        await db.delete(record)

    await db.delete(category)
    await db.commit()
    return {"deleted_records": record_count, "dormant_budgets": dormant_budgets}


async def restore_default_categories(
    db: AsyncSession, current_user: User | None = None
) -> dict[str, int]:
    """Restore default categories: delete custom ones, reset preset sort_order.

    - Delete all is_preset=0 custom categories for the user
    - Associated records保留, category_id set to NULL
    - Associated budgets 走 §3.2.3 同一休眠级联（任务 3.3/4.4）：include 预算失去最后
      一个关联分类 → 置 ``dormant=1`` 休眠保留（不再删除，决策 D4）；
      exclude 预算仅移出排除集
    - Reset preset categories' sort_order to defaults

    v1.4.3 M8：预设复位改按新预设集 **name** 匹配（原按 (name,type)）。
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
    dormant_budgets = 0

    for cat in custom_categories:
        cat_id = cat.id
        if cat_id is None:  # 理论不可达：已入库行必有主键
            continue

        # Count associated records
        count_stmt = select(func.count(Record.id)).where(Record.category_id == cat_id)
        count_result = await db.exec(count_stmt)
        record_count = count_result.one() or 0
        affected_records += record_count

        # Set associated records' category_id to NULL (preserve records)
        record_stmt = select(Record).where(Record.category_id == cat_id)
        record_result = await db.exec(record_stmt)
        for record in record_result.all():
            record.category_id = None

        # Budget dormancy cascade（与 delete_category 同一函数，任务 3.3/4.4）
        dormant_budgets += await _dormant_budgets_for_deleted_category(db, cat_id)

        # Delete the category
        await db.delete(cat)
        deleted_count += 1

    # Step 2: Reset preset categories' sort_order (仅按 name 定位)
    for preset in PRESET_CATEGORIES:
        stmt = select(Category).where(
            Category.name == preset["name"],
            Category.is_preset == 1,
        )
        result = await db.exec(stmt)
        category = result.first()
        if category:
            category.sort_order = preset["sort_order"]
            category.icon = preset["icon"]

    await db.commit()
    return {
        "deleted_categories": deleted_count,
        "affected_records": affected_records,
        "dormant_budgets": dormant_budgets,
    }
