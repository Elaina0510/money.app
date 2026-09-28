"""Category business logic."""

from collections.abc import Sequence
from typing import Any, cast

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import SCOPE_INCLUDE, Budget, BudgetCategory
from app.models.category import LEGACY_CATEGORY_TYPE, Category
from app.models.record import Record
from app.models.tag import Tag
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
        # v1.4.4 M2（§0.4-6 造行点）：服务层新建 = 用户自建，显式写 0（列默认亦为 0）
        source=0,
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
                # v1.4.4 M2（§0.4-6 造行点 / D3）：CoW 副本**出身仍为预设**——is_preset
                # 保持 0（「非全局预设行」语义不变），徽章与不可单删由 source=1 承载
                source=1,
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
    """把新排序写入用户可见行：全局预设行 Copy-on-Write，用户自有行直接改位。

    - 无 current_user（全局维护态），或该行**已归属本用户**（``row.user_id`` 非空，
      含历史「``is_preset=1`` 且 ``user_id`` 非空」的形制行）：直接更新 ``sort_order``；
    - 仅当该行为**全局预设**（``row.user_id is None``）才走 CoW：
      * 本用户已有同名行（UNIQUE(name,user_id) 保证至多一条）→ 更新它；
      * 无同名行 → 按预设字段建副本（``is_preset=0``、新 ``sort_order``）后写位。

    全局预设行（``user_id IS NULL``）永不被写脏。
    """
    if user_id is None or row.user_id is not None:
        row.sort_order = sort_order
        db.add(row)
        return

    if row.sort_order == sort_order:
        # 全局预设本就在目标位：无需建副本，避免无意义的 CoW 膨胀（全局预设行不被写）
        return

    dup_stmt = select(Category).where(
        Category.name == row.name,
        Category.user_id == user_id,
    )
    existing = (await db.exec(dup_stmt)).first()
    if existing is None:
        existing = Category(
            name=row.name,
            type=row.type,
            icon=row.icon,
            sort_order=sort_order,
            is_preset=0,
            # v1.4.4 M2（§0.4-6 造行点）：拖序触发的 CoW 副本同样出身预设
            source=1,
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
    # v1.4.4 M2（D8 / 任务 5.1）：判据从「全局预设行」扩到**出身**——预设派生的用户副本
    # （is_preset=0 而 source=1）同样不可单删，副本的消失只经「恢复默认」全量丢弃
    # （用户裁定 a=维持：执行期不得加单点回退入口）。
    if category.is_preset == 1 or category.source == 1:
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


def compute_discarded_customizations(
    rows: Sequence[Category], presets: Sequence[tuple[str, str, int]]
) -> int:
    """恢复默认时被丢弃的定制数 M（设计 §3.4「定制判据」，**前后端唯一口径**）。

    输入 ``rows`` = 恢复前的**可见列表**（``sort_order, id`` 升序，与前端 store 的列表
    同源），``presets`` = ``app.presets.PRESET_SPECS`` 的 (name, icon, sort_order)
    有序表（其**顺序**即默认排序，与 ``GET /categories/presets`` 同序）。

    判据两腿，**一行至多计一次**（M 计的是「预设分类的条数」，非破坏属性数）：

    1. 名/图标破坏：``source==1`` 且「名称不在预设名集合内」或「图标 ≠ 预设原图标」
       → 计 1（副本改名后已不属任何预设 ⇒ 恢复时并入自建堆删除，同样算丢弃）；
       命中本腿的行**不再进入第二腿**（否则 8.1.3 黄金链路的「换图标 + 改序」会双计）。
    2. 序尾记（改序判据）：把剩余 ``source==1`` 行的预设下标按可见序排成一列，
       自上而下贪心匹配 ``presets`` 序——严格大于游标者前进，否则该行是「非单调
       子序列的破坏者」计 1（整表单调 ⇒ 计 0）。「其他家族」行（``其他支出/其他收入/
       其他``）剔除：其置尾名次由 ``OTHER_FAMILY_RANK`` 归一化强制决定，不是用户定制。

    与前端 ``SettingsCategoriesPage.vue::computeRestoreCounts`` 逐字同源，
    共用 §8.1.10 = §8.2.3 那张具体整数用例表（禁止「或」字多解、禁止各改各的表）。
    """
    index_of = {name: pos for pos, (name, _icon, _sort) in enumerate(presets)}
    icon_of = {name: icon for name, icon, _sort in presets}

    broken = 0
    order_marks: list[int] = []
    for row in rows:
        if row.source != 1:
            continue  # 自建行不属于「预设定制」口径
        pos = index_of.get(row.name)
        if pos is None or row.icon != icon_of[row.name]:
            broken += 1
            continue
        if _is_other_row(row.name):
            continue
        order_marks.append(pos)

    tail = 0
    cursor = -1
    for pos in order_marks:
        if pos > cursor:
            cursor = pos
        else:
            tail += 1
    return broken + tail


async def _global_preset_row(db: AsyncSession, name: str) -> Category | None:
    """按 name 取**合法的全局预设行**（``user_id IS NULL`` 且 ``is_preset == 1``）。

    设计 §3.7「宁删不错并」的落点：只按 name 查会撞上「同名但 is_preset=0 的脏全局行」，
    那种行不是副本的归属，故此处再过一道 ``is_preset==1 AND user_id IS NULL`` 硬校验，
    不通过即返回 None（调用方把副本并入自建堆删除，绝不错并）。
    """
    rows = list(
        (
            await db.exec(
                select(Category).where(
                    Category.name == name,
                    cast("Any", Category.user_id).is_(None),
                )
            )
        ).all()
    )
    for row in rows:
        if row.is_preset == 1 and row.user_id is None:
            return row
    return None


async def _relink_budget_categories(db: AsyncSession, from_id: int, to_id: int) -> None:
    """副本的预算关联逐条改指全局行；``(budget_id, to_id)`` 已存在则删副本侧关联行。

    ``budget_categories`` 有 ``UNIQUE(budget_id, category_id)``（§0.4-8），改指前不去重
    会撞约束。两条分支都保证受影响预算**仍至少关联一条分类**（改指成功、或目标关联
    本就在），故**不触发休眠**（任务 4.2-②；休眠只由 §3.2.3「删光关联」路径产生）。
    ``scope_mode`` 为 exclude 的关联同法处理——只动关联行，语义无差（设计 §3.7）。
    """
    links_stmt = select(BudgetCategory).where(BudgetCategory.category_id == from_id)
    links = list((await db.exec(links_stmt)).all())
    if not links:
        return
    existing_stmt = select(BudgetCategory.budget_id).where(BudgetCategory.category_id == to_id)
    kept = {int(budget_id) for budget_id in (await db.exec(existing_stmt)).all()}
    for link in links:
        budget_id = int(link.budget_id)
        if budget_id in kept:
            await db.delete(link)  # UNIQUE 冲突防御：丢副本侧那条
            continue
        link.category_id = to_id
        db.add(link)
        kept.add(budget_id)
    await db.flush()


async def _move_tag_links(
    db: AsyncSession, from_id: int, to_id: int | None, user_id: int | None
) -> None:
    """收口指向 ``from_id`` 的 tags 引用：本用户行改指 ``to_id``，其余置 NULL。

    副本/自建行紧接着被删除，任何残留引用都会成为**新增** FK 违规（任务 8.1.9 断言
    零新增）；跨用户与匿名脏引用无从改指（``to_id`` 属本用户的可见集合），一律置 NULL
    ——对齐 README 导入须知的 FK 清理口径。``tags.category_id`` 本身可空，置 NULL 合法。
    """
    tags = list((await db.exec(select(Tag).where(Tag.category_id == from_id))).all())
    for tag in tags:
        owned = user_id is not None and tag.user_id == user_id
        tag.category_id = to_id if (to_id is not None and owned) else None
        db.add(tag)


async def restore_default_categories(
    db: AsyncSession, current_user: User | None = None
) -> dict[str, int]:
    """恢复默认分类：**副本合并回全局行** + 预设复位（v1.4.4 M2 / 设计 §3.4 五步）。

    单事务控制流（步骤 1-4 全部写完才一次 ``commit``；任意一步抛异常即不 commit，
    由会话关闭整体回滚——原子性红线，任务 8.1.6 用「mock 步骤 3 抛错 → 零变更」钉住）：

    1. **分堆**：载入当前用户全部行 → ``derived``（``source==1`` 且 user_id 非空，即预设
       派生副本）与 ``custom``（``source==0``）。M（丢弃定制数）在**恢复前**的可见集合上
       按 §3.4 判据算一次，与前端 D6 弹窗数字同判据同输入。
    2. **副本堆合并**：逐行按 name 找全局预设行（§3.7 硬校验），命中则账单改指全局行 id
       （REQ-005「不迁移、不乱动」）、预算关联改指（去重、不休眠）、tags 改指或置 NULL，
       删副本并计 ``merged_presets``；未命中（预设改名史遗留影子行、脏全局行）→ 转入
       ``custom`` 堆按步骤 3 处理（宁删不错并）。
    3. **自建堆**：维持现状语义——账单改挂「其他」全局行（``records.category_id`` NOT NULL，
       不能置 NULL；无「其他」行时删行兜底）、tags 引用置 NULL、预算走 §3.2.3 休眠级联、
       删行并计 ``deleted_categories`` / ``affected_records`` / ``dormant_budgets``。
    4. **预设复位**：遍历 presets，把**全局行**的 name/icon/sort_order 写回默认值并置
       ``source=1, is_preset=1``（幂等保险）。全局预设行仅此处合法写入，其余路径零写入。
    5. 一次 commit，返回五键（设计 §3.3）。
    """
    from app.presets import PRESET_SPECS

    user_id = current_user.id if current_user else None

    # ── 步骤 1：分堆 + M 判据（恢复前状态） ─────────────────────────────
    visible = await _visible_categories(db, current_user)
    discarded_customizations = compute_discarded_customizations(visible, PRESET_SPECS)

    user_rows = list((await db.exec(select(Category).where(Category.user_id == user_id))).all())
    derived: list[Category] = []
    custom: list[Category] = []
    for row in user_rows:
        if row.source == 1 and row.user_id is not None:
            derived.append(row)
        elif row.user_id is None and row.is_preset == 1:
            continue  # 全局预设行：只由步骤 4 复位，绝不进删除堆
        else:
            custom.append(row)
    # 合并/删除次序按可见序（sort_order, id），与前端所见一致；Python 排序避免新查询
    derived.sort(key=lambda r: (r.sort_order, r.id or 0))
    custom.sort(key=lambda r: (r.sort_order, r.id or 0))

    # ── 步骤 2：副本堆合并回全局预设行 ──────────────────────────────────
    merged_presets = 0
    for row in derived:
        copy_id = row.id
        if copy_id is None:  # 理论不可达：已入库行必有主键
            continue
        target = await _global_preset_row(db, row.name)
        if target is None or target.id is None:
            custom.append(row)  # 影子行/脏全局行 → 宁删不错并
            continue
        # ① 账单改指全局行 id（REQ-005：不迁移、不乱动）
        records = list((await db.exec(select(Record).where(Record.category_id == copy_id))).all())
        for record in records:
            record.category_id = target.id
            db.add(record)
        # ② 预算关联改指（UNIQUE 去重，不触发休眠）③ tags 改指或置 NULL
        await _relink_budget_categories(db, copy_id, target.id)
        await _move_tag_links(db, copy_id, target.id, user_id)
        # ④ 删副本
        await db.delete(row)
        merged_presets += 1
    custom.sort(key=lambda r: (r.sort_order, r.id or 0))

    # ── 步骤 3：自建堆（含步骤 2 转入的影子行）维持现状语义 ──────────────
    # 回退分类「其他」预设（全局，user_id IS NULL）：删除自定义分类时其下账单改挂到它。
    # v1.4.3 起 records.category_id NOT NULL，置 NULL 会 IntegrityError → 500。
    other_row = (
        await db.exec(
            select(Category).where(
                Category.name == OTHER_CATEGORY_NAME,
                cast("Any", Category.user_id).is_(None),
            )
        )
    ).first()
    fallback_id: int | None = other_row.id if other_row is not None else None

    deleted_count = 0
    affected_records = 0
    dormant_budgets = 0

    for cat in custom:
        cat_id = cat.id
        if cat_id is None:  # 理论不可达：已入库行必有主键
            continue

        # Count associated records
        count_stmt = select(func.count(Record.id)).where(Record.category_id == cat_id)
        count_result = await db.exec(count_stmt)
        record_count = count_result.one() or 0
        affected_records += record_count

        # 关联账单改挂「其他」预设（NOT NULL 约束下不可置 NULL）
        record_stmt = select(Record).where(Record.category_id == cat_id)
        record_result = await db.exec(record_stmt)
        for record in list(record_result.all()):
            if fallback_id is not None:
                record.category_id = fallback_id
            else:
                await db.delete(record)  # 极端兜底：无「其他」预设时按删除处理，绝不留违规

        # tags 引用置 NULL（副本/自建行即将删除，免留新增 FK 违规）
        await _move_tag_links(db, cat_id, None, user_id)

        # Budget dormancy cascade（与 delete_category 同一函数，任务 3.3/4.4）
        dormant_budgets += await _dormant_budgets_for_deleted_category(db, cat_id)

        # Delete the category
        await db.delete(cat)
        deleted_count += 1

    # ── 步骤 4：预设复位（全局预设行唯一合法写点，按 name 定位） ─────────
    for name, icon, sort_order in PRESET_SPECS:
        rows = list(
            (
                await db.exec(
                    select(Category).where(
                        Category.name == name,
                        cast("Any", Category.user_id).is_(None),
                    )
                )
            ).all()
        )
        for row in rows:
            if row.is_preset != 1:
                continue  # 脏全局行不动（宁漏不错写，§3.7 同一取向）
            # 名称本不可变，显式写回为幂等保险
            row.name = name
            row.icon = icon
            row.sort_order = sort_order
            row.source = 1
            row.is_preset = 1
            db.add(row)

    # ── 步骤 5：一次提交（前面任意一步抛异常都到不了这里 → 整体回滚） ────
    await db.commit()
    return {
        "deleted_categories": deleted_count,
        "affected_records": affected_records,
        "dormant_budgets": dormant_budgets,
        "merged_presets": merged_presets,
        "discarded_customizations": discarded_customizations,
    }
