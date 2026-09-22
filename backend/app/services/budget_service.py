"""Budget business logic (v1.4.3 M12：某自然月下的多条具名预算).

设计 §12.2.3 的口径要点：
  * 一个月份/一年的 spent 均以**单条 GROUP BY 聚合查询**取「分类 → 支出」映射，
    再在 Python 内按 include/exclude 规则逐预算求和——杜绝旧版逐条 enrich 的 N+1；
  * 聚合谓词与旧 ``_enrich_budget`` 同源（``type='expense'`` + ``consume_time`` 月首/月末），
    唯一的裁定性偏离是补 ``user_id`` 隔离（progress.md 审查记录②，2026-09-20 用户已认可）；
  * 金额一律经 ``round_money``；聚合 float 先求和再 round，与旧逐条口径一致。
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import (
    SCOPE_INCLUDE,
    SCOPE_MODES,
    UNKNOWN_CATEGORY_NAME,
    Budget,
    BudgetCategory,
)
from app.models.category import Category
from app.models.record import Record
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.utils.money import round_money

# 未分类支出（``Record.category_id IS NULL``）在聚合映射里的归并键。
# 分类 id 为自增主键（恒 ≥ 1），0 可安全占用；该桶只并入 exclude 的「当月全部支出」，
# 不进入 details（无分类可名）。
_UNCATEGORIZED_KEY = 0

_NAME_MAX = 50


@dataclass
class _BudgetSnapshot:
    """预算行的标量快照。

    旧实现靠「commit 后重新查询」规避 async 会话的属性过期（MissingGreenlet）；
    本模块改为**先取快照、再做后续查询**，从根上不依赖过期时机。
    """

    id: int | None
    name: str
    month: str
    amount: float
    scope_mode: str
    dormant: int  # 1 = 关联分类被删光的休眠预算（v1.4.3-boot2 M3 / D4）
    created_at: str
    updated_at: str

    @classmethod
    def from_budget(cls, budget: Budget) -> "_BudgetSnapshot":
        return cls(
            id=budget.id,
            name=budget.name,
            month=budget.month,
            amount=budget.amount,
            scope_mode=budget.scope_mode,
            dormant=budget.dormant,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
        )


def _get_month_date_range(month: str) -> tuple[str, str]:
    """Get start and end date for a month string (YYYY-MM).

    口径登记：月末边界沿用旧 ``_enrich_budget`` 的 ``consume_time <= 'YYYY-MM-DD'``
    （任务 3.1「谓词完全同源」，本版唯一裁定性偏离是 user_id 隔离）。
    """
    try:
        year_str, month_str = month.split("-")
        year, mon = int(year_str), int(month_str)
        _, last_day = monthrange(year, mon)
    except (ValueError, TypeError) as exc:  # 形如 2026-13 / 非数字：拒绝而非 500
        raise ValueError(f"月份格式非法：{month}") from exc
    return f"{year}-{mon:02d}-01", f"{year}-{mon:02d}-{last_day:02d}"


def _validate_budget_fields(
    name: str, amount: float, month: str, scope_mode: str, category_ids: list[int]
) -> list[int]:
    """服务层校验（任务 1.3）；返回去重后的 category_ids。

    ``name``/``amount``/``scope_mode``/``month`` 的**类型级**约束已在 pydantic
    （非法即 422），此处是设计明列的服务层权威校验：
    去空、id 为正整数。

    v1.4.3-boot2 M3（任务 2.1 / 决策 D3）：原「include 且空集 → ValueError」
    **已删除**——「一个都不选」现在是合法语义 = **动态全部分类**（dormant=0 时，
    后续新增分类自动计入）；两种空集由 ``budgets.dormant`` 列区分（D3）。
    exclude 的空排除集本就等于全部分类，口径不变。

    Raises:
        ValueError: 路由层据此回 Code.PARAM_ERROR。
    """
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("预算名称不能为空")
    if len(clean_name) > _NAME_MAX:
        raise ValueError(f"预算名称最长 {_NAME_MAX} 个字符")
    if amount is None or amount <= 0:
        raise ValueError("预算金额必须大于 0")
    _get_month_date_range(month)  # 月份合法性（pydantic pattern 放行 2026-13，此处兜底）
    if scope_mode not in SCOPE_MODES:
        raise ValueError("范围模式仅支持 include / exclude")
    ids = list(dict.fromkeys(category_ids))  # 去重且保序
    if any(not isinstance(cid, int) or cid <= 0 for cid in ids):
        raise ValueError("分类 id 非法")
    return ids


async def _ensure_categories_exist(db: AsyncSession, category_ids: list[int]) -> None:
    """关联分类必须存在（与 record_service 同一口径：仅校验存在性，不过滤可见性）。

    只校验存在而不按 user_id 过滤，是为了不阻断「预设分类被用户同名副本遮蔽」
    后仍指向预设 id 的存量预算（M8 CoW 语义）重保存。

    ``cast(Any, ...)`` 说明（本模块同）：SQLModel 把类字段声明成 `id: int | None`，
    mypy 看不到它运行时的 instrumented Column 身份，故 Core 表达式操作（``in_`` /
    ``order_by`` / ``is_``）需显式放宽；运行时传的就是原对象，行为不变。
    """
    if not category_ids:
        return
    stmt = select(Category.id).where(cast("Any", Category.id).in_(category_ids))
    found = {cid for cid in (await db.exec(stmt)).all() if cid is not None}
    if missing := [cid for cid in category_ids if cid not in found]:
        raise ValueError(f"分类不存在：{', '.join(str(m) for m in missing)}")


def _apply_budget_owner_filter(stmt: Any, user_id: int | None) -> Any:
    """预算归属过滤：登录用户只见自己的预算，匿名只见 user_id IS NULL（沿旧口径）。"""
    if user_id is not None:
        return stmt.where(Budget.user_id == user_id)
    return stmt.where(cast("Any", Budget.user_id).is_(None))


async def _month_expense_by_category(
    db: AsyncSession, month: str, user_id: int | None
) -> dict[int, float]:
    """单查询取「分类 → 该月支出」映射（任务 3.1，杜绝逐条 enrich 的 N+1）。

    谓词与旧 ``_enrich_budget`` 同源（``type='expense'`` + ``consume_time`` 月首→月末 +
    ``GROUP BY category_id``），并按审查记录②补 ``user_id`` 隔离——旧实现缺该谓词，
    会把他人同分类支出计入本人 spent（虚高），属既有缺陷的修复。
    """
    start_date, end_date = _get_month_date_range(month)
    stmt = (
        select(
            func.coalesce(Record.category_id, _UNCATEGORIZED_KEY),
            func.coalesce(func.sum(Record.amount), 0),
        )
        .where(
            Record.type == "expense",
            Record.consume_time >= start_date,
            Record.consume_time <= end_date,
        )
        .group_by(func.coalesce(Record.category_id, _UNCATEGORIZED_KEY))
    )
    if user_id is not None:
        stmt = stmt.where(Record.user_id == user_id)
    else:
        stmt = stmt.where(cast("Any", Record.user_id).is_(None))
    rows = (await db.exec(stmt)).all()
    return {int(row[0]): float(row[1] or 0) for row in rows}


async def _year_expense_by_month_category(
    db: AsyncSession, year: int, user_id: int | None
) -> dict[str, dict[int, float]]:
    """全年一次聚合：``GROUP BY substr(consume_time,1,7), category_id``（任务 3.5）。

    12 月 × N 预算共用这一份映射，零 N+1。
    """
    stmt = (
        select(
            func.substr(Record.consume_time, 1, 7),
            func.coalesce(Record.category_id, _UNCATEGORIZED_KEY),
            func.coalesce(func.sum(Record.amount), 0),
        )
        .where(
            Record.type == "expense",
            Record.consume_time >= f"{year}-01-01",
            Record.consume_time <= f"{year}-12-31",
        )
        .group_by(
            func.substr(Record.consume_time, 1, 7),
            func.coalesce(Record.category_id, _UNCATEGORIZED_KEY),
        )
    )
    if user_id is not None:
        stmt = stmt.where(Record.user_id == user_id)
    else:
        stmt = stmt.where(cast("Any", Record.user_id).is_(None))
    rows = (await db.exec(stmt)).all()
    by_month: dict[str, dict[int, float]] = {}
    for month, cid, total in rows:
        if month is None:
            continue
        by_month.setdefault(str(month), {})[int(cid)] = float(total or 0)
    return by_month


async def _category_info_by_ids(
    db: AsyncSession, category_ids: set[int]
) -> dict[int, tuple[str, str, int]]:
    """一次取回分类展示信息 (name, icon, sort_order)；空集合不发查询。"""
    if not category_ids:
        return {}
    stmt = select(
        Category.id, Category.name, Category.icon, Category.sort_order
    ).where(cast("Any", Category.id).in_(category_ids))
    info: dict[int, tuple[str, str, int]] = {}
    for row in (await db.exec(stmt)).all():
        cid = row[0]
        if cid is None:
            continue
        info[int(cid)] = (str(row[1]), str(row[2]), int(row[3]))
    return info


async def _budget_category_ids(
    db: AsyncSession, budget_ids: list[int]
) -> dict[int, list[int]]:
    """一次取回多条预算的关联分类（budget_id → [category_id]）。"""
    if not budget_ids:
        return {}
    stmt = (
        select(BudgetCategory.budget_id, BudgetCategory.category_id)
        .where(cast("Any", BudgetCategory.budget_id).in_(budget_ids))
        .order_by(cast("Any", BudgetCategory.id))
    )
    rows = (await db.exec(stmt)).all()
    links: dict[int, list[int]] = {}
    for budget_id, category_id in rows:
        links.setdefault(int(budget_id), []).append(int(category_id))
    return links


def _detail_entry(
    cid: int, spent: float, info: dict[int, tuple[str, str, int]]
) -> dict[str, Any]:
    cat = info.get(cid)
    return {
        "category_id": cid,
        "category_name": cat[0] if cat else UNKNOWN_CATEGORY_NAME,
        "icon": cat[1] if cat else "mdi-cash",
        "spent": round_money(spent),
    }


def _ordered(ids: list[int], info: dict[int, tuple[str, str, int]]) -> list[int]:
    """按分类自身排序（sort_order, id）呈现——与分类列表/明细同一顺序。"""
    return sorted(ids, key=lambda cid: (info[cid][2] if cid in info else 10**9, cid))


def _build_detail(
    snap: _BudgetSnapshot,
    category_ids: list[int],
    info: dict[int, tuple[str, str, int]],
    spent_by_cat: dict[int, float],
) -> dict[str, Any]:
    """按 include/exclude 规则算出 spent / details（任务 3.2–3.6，纯计算无 IO）。

    v1.4.3-boot2 M3（任务 2.3）分支表——**分支顺序即口径，勿重排**：

    1. ``dormant``：关联分类已被删光的休眠预算 → spent 恒 0、无明细（D4）；
    2. ``INCLUDE`` 且**空集**（非休眠）：「一个都不选」= **动态全部分类**（D3），
       spent 与 exclude 的空排除集**完全同口径**（D5，含未分类桶），
       明细列「花费 > 0 且非未分类桶」的全部类目；
    3. ``INCLUDE`` 显式所选：仅 Σ 所选分类（现状不变）；
    4. ``exclude``：当月全部支出 − Σ 排除类（现状不变，空排除集即全额）。
    """
    amt = round_money(snap.amount)
    month_total = sum(spent_by_cat.values())  # 含未分类桶（键 0），全额口径用

    if snap.dormant:
        # 分支 1：休眠预算保留记录但不再覆盖任何分类 → 花费恒 0、明细空
        spent_raw, detail_pairs = 0.0, []
    elif snap.scope_mode == SCOPE_INCLUDE and not category_ids:
        # 分支 2：不选 = 动态全部分类（含 category_id NULL / 失效分类的极端数据，D5）
        spent_raw = month_total
        # 明细与 exclude 空排除集同款过滤（excluded = ∅）；未分类桶计入 spent 但无名可列
        detail_pairs = [
            (cid, val)
            for cid, val in spent_by_cat.items()
            if cid != _UNCATEGORIZED_KEY and val > 0
        ]
    elif snap.scope_mode == SCOPE_INCLUDE:
        # 分支 3：显式所选 → 仅 Σ 所选分类；选中类逐一列出，0 花费显示 0（任务 3.3）
        spent_raw = sum(spent_by_cat.get(cid, 0.0) for cid in category_ids)
        detail_pairs = [(cid, spent_by_cat.get(cid, 0.0)) for cid in category_ids]
    else:
        # 分支 4：exclude
        excluded = set(category_ids)
        # 空排除集 = 全部分类 = 全额（任务 1.3 / 3.2）
        spent_raw = month_total - sum(spent_by_cat.get(cid, 0.0) for cid in excluded)
        # 明细只列「计入且有实际花费」的分类（需求 12.3）；未分类桶无名可列
        detail_pairs = [
            (cid, val)
            for cid, val in spent_by_cat.items()
            if cid not in excluded and cid != _UNCATEGORIZED_KEY and val > 0
        ]

    spent = round_money(spent_raw)
    remaining = round_money(max(amt - spent, 0))
    percentage = round(spent / amt * 100, 1) if amt > 0 else 0
    ordered_ids = _ordered(category_ids, info)

    return {
        "id": snap.id,
        "month": snap.month,
        "name": snap.name,
        "amount": amt,
        "spent": spent,
        "remaining": remaining,
        "percentage": percentage,
        "scope_mode": snap.scope_mode,
        # 1 → 前端置灰「分类已删除，预算保留」；汇总侧已按 D10 剔除
        "dormant": bool(snap.dormant),
        "category_ids": ordered_ids,
        "category_names": [
            info[cid][0] if cid in info else UNKNOWN_CATEGORY_NAME for cid in ordered_ids
        ],
        "details": [
            _detail_entry(cid, val, info)
            for cid, val in sorted(detail_pairs, key=lambda kv: _order_key(kv[0], info))
        ],
        "created_at": snap.created_at,
        "updated_at": snap.updated_at,
    }


def _order_key(cid: int, info: dict[int, tuple[str, str, int]]) -> tuple[int, int]:
    return (info[cid][2] if cid in info else 10**9, cid)


async def _details_for(
    db: AsyncSession,
    snapshots: list[_BudgetSnapshot],
    spent_cache: dict[str, dict[int, float]],
    user_id: int | None,
) -> list[dict[str, Any]]:
    """把若干预算（可跨月）渲染成 BudgetDetail：分类关联与展示信息各一次查询。"""
    budget_ids = [s.id for s in snapshots if s.id is not None]
    links = await _budget_category_ids(db, budget_ids)
    needed = {cid for ids in links.values() for cid in ids}
    for snap in snapshots:
        if snap.month not in spent_cache:
            spent_cache[snap.month] = await _month_expense_by_category(
                db, snap.month, user_id
            )
        needed.update(spent_cache[snap.month].keys())
    info = await _category_info_by_ids(db, {cid for cid in needed if cid != _UNCATEGORIZED_KEY})
    return [
        _build_detail(
            snap,
            links.get(snap.id or 0, []),
            info,
            spent_cache[snap.month],
        )
        for snap in snapshots
    ]


async def get_budgets(
    db: AsyncSession, month: str, current_user: User | None = None
) -> list[dict[str, Any]]:
    """某月的全部预算（任务 2.1：去 type 参数，按 id 升序 = 创建序）。"""
    _get_month_date_range(month)  # 2026-13 过得了 pattern、过不了月历：400 而非静默空列表
    user_id = current_user.id if current_user else None
    stmt = _apply_budget_owner_filter(
        select(Budget).where(Budget.month == month).order_by(cast("Any", Budget.id)), user_id
    )
    result = await db.exec(stmt)
    snapshots = [_BudgetSnapshot.from_budget(b) for b in result.all()]
    return await _details_for(db, snapshots, {}, user_id)


async def get_year_summary(
    db: AsyncSession, year: int, current_user: User | None = None
) -> dict[str, Any]:
    """Get budgets grouped by month for a given year (fixed 12 months).

    用于统计页年视图的逐月预算概览：无论该月是否有预算，
    ``months`` 固定返回 01→12 共 12 项，无预算的月份 budgets 为空数组、
    total_amount/total_spent 为 0。

    逐月 total_amount / total_spent = **Σ 各预算**（决策 D4）：范围重叠时
    Σ spent 可大于当月实际支出，属已裁定的预期口径（设计 §12.3）。
    v1.4.3-boot2 M3（决策 D10）：求和**剔除 dormant 预算**，``budgets`` 数组仍
    原样返回 dormant 行（月卡片置灰展示需要它）。

    Args:
        db: 异步数据库会话。
        year: 年份（YYYY）。
        current_user: 当前登录用户，用于数据隔离。

    Returns:
        ``{"year": year, "months": [{"month", "total_amount",
        "total_spent", "budgets"} × 12]}``
    """
    user_id = current_user.id if current_user else None
    stmt = _apply_budget_owner_filter(
        select(Budget)
        .where(Budget.month >= f"{year}-01", Budget.month <= f"{year}-12")
        .order_by(cast("Any", Budget.id)),
        user_id,
    )
    result = await db.exec(stmt)
    snapshots = [_BudgetSnapshot.from_budget(b) for b in result.all()]

    # 全年一次聚合（任务 3.5），12 个月全部预热进 spent_cache：
    # 于是整年只剩「关联分类 + 分类信息」各一条查询，逐月逐预算在 Python 内求和，零 N+1
    year_map = await _year_expense_by_month_category(db, year, user_id)
    spent_cache: dict[str, dict[int, float]] = {
        f"{year}-{m:02d}": year_map.get(f"{year}-{m:02d}", {}) for m in range(1, 13)
    }
    details = await _details_for(db, snapshots, spent_cache, user_id)

    by_month: dict[str, list[dict[str, Any]]] = {}
    for detail in details:
        by_month.setdefault(detail["month"], []).append(detail)

    months: list[dict[str, Any]] = []
    for m in range(1, 13):
        month = f"{year}-{m:02d}"
        items = by_month.get(month, [])
        # D10（任务 4.2）：休眠预算不进年汇总 total；但 budgets 明细**保留返回**，
        # 供前端逐月卡片置灰展示（勿误过滤）
        counted = [i for i in items if not i["dormant"]]
        months.append(
            {
                "month": month,
                "total_amount": round_money(sum(i["amount"] for i in counted)),
                "total_spent": round_money(sum(i["spent"] for i in counted)),
                "budgets": items,
            }
        )

    return {"year": year, "months": months}


async def _replace_budget_categories(
    db: AsyncSession, budget_id: int, category_ids: list[int]
) -> None:
    """重写某预算的关联分类。

    连接未启用 ``PRAGMA foreign_keys``（沿本项目实测口径），``ondelete=CASCADE``
    仅是模式声明、运行时不生效，故关联行的删除全部由本层显式完成。
    """
    stmt = select(BudgetCategory).where(BudgetCategory.budget_id == budget_id)
    for link in (await db.exec(stmt)).all():
        await db.delete(link)
    # 必须先落 DELETE：SQLAlchemy unit-of-work 在同一次 flush 里**先插后删**，
    # 保留原分类的 PUT 会撞 UNIQUE (budget_id, category_id) 而 500
    await db.flush()
    for cid in category_ids:
        db.add(BudgetCategory(budget_id=budget_id, category_id=cid))


async def create_budget(
    db: AsyncSession, data: BudgetCreate, current_user: User | None = None
) -> dict[str, Any]:
    """纯创建一条命名预算（任务 2.2：同月同名多条允许，不再是 upsert）。

    口径（v1.4.3-boot2 M3 / 决策 D3）：``scope_mode='include'`` 且 ``category_ids``
    为空 = **动态全部分类**（后续新增分类自动计入），不报错、正常落库；
    新建预算恒 ``dormant=0``（D9：休眠只由分类删除级联置 1）。

    Raises:
        ValueError: 服务层校验不通过（名称/金额/月份/分类 id）→ 路由层 PARAM_ERROR。
    """
    user_id = current_user.id if current_user else None
    name = (data.name or "").strip()
    ids = _validate_budget_fields(
        name, data.amount, data.month, data.scope_mode, data.category_ids
    )
    await _ensure_categories_exist(db, ids)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    budget = Budget(
        user_id=user_id,
        name=name,
        month=data.month,
        amount=round_money(data.amount),
        scope_mode=data.scope_mode,
        dormant=0,  # 新建永不休眠（D9）
        created_at=now,
        updated_at=now,
    )
    db.add(budget)
    await db.flush()
    if budget.id is None:  # 理论不可达：flush 后主键已回填
        raise RuntimeError("预算创建后未取回主键")
    for cid in ids:
        db.add(BudgetCategory(budget_id=budget.id, category_id=cid))
    await db.commit()

    snap = _BudgetSnapshot.from_budget(budget)
    items = await _details_for(db, [snap], {}, user_id)
    return items[0]


async def get_budget_detail(
    db: AsyncSession, budget: Budget, current_user: User | None = None
) -> dict[str, Any]:
    """渲染单条预算为 BudgetDetail（供 PUT 响应复用；spent 按该预算自身月份）。"""
    snap = _BudgetSnapshot.from_budget(budget)
    user_id = current_user.id if current_user else None
    items = await _details_for(db, [snap], {}, user_id)
    return items[0]


async def update_budget(
    db: AsyncSession,
    budget_id: int,
    data: BudgetUpdate,
    current_user: User | None = None,
) -> dict[str, Any] | None:
    """全字段编辑（任务 2.3）：``month`` 不在载荷契约内、传入即忽略。

    唤醒（v1.4.3-boot2 M3 任务 3.5 / 决策 D9）：**任何一次成功保存一律落
    ``dormant=0``**——用户编辑休眠预算重新保存（重选分类，或一个都不选=动态全部）
    即恢复计入统计；无独立唤醒接口。休眠置 1 只由分类删除级联完成。
    同一 D3 口径：include 空集合法 = 动态全部分类；改 scope_mode=exclude 同样清休眠。

    Returns:
        更新后的 BudgetDetail；预算不存在时返回 None。
    Raises:
        PermissionError: 非归属者（IDOR）→ 403。
        ValueError: 服务层校验不通过 → PARAM_ERROR。
    """
    budget = (await db.exec(select(Budget).where(Budget.id == budget_id))).first()
    if not budget:
        return None
    if current_user is not None and budget.user_id != current_user.id:
        raise PermissionError("无权操作此预算")

    name = (data.name or "").strip()
    ids = _validate_budget_fields(
        name, data.amount, budget.month, data.scope_mode, data.category_ids
    )
    await _ensure_categories_exist(db, ids)

    budget.name = name
    budget.amount = round_money(data.amount)
    budget.scope_mode = data.scope_mode
    budget.dormant = 0  # D9：成功保存即唤醒（含 include 空集 → 动态全部）
    budget.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.add(budget)
    await _replace_budget_categories(db, int(budget_id), ids)
    await db.commit()

    snap = _BudgetSnapshot.from_budget(budget)
    user_id = current_user.id if current_user else None
    items = await _details_for(db, [snap], {}, user_id)
    return items[0]


async def delete_budget(
    db: AsyncSession, budget_id: int, current_user: User | None = None
) -> bool:
    """Delete a budget. Raises PermissionError if not owner. Returns False if not found.

    关联行显式删除（见 ``_replace_budget_categories`` 的 foreign_keys 说明）。
    """
    budget = (await db.exec(select(Budget).where(Budget.id == budget_id))).first()
    if not budget:
        return False
    if current_user is not None and budget.user_id != current_user.id:
        raise PermissionError("无权操作此预算")
    await _replace_budget_categories(db, budget_id, [])
    await db.delete(budget)
    await db.commit()
    return True


async def get_budget_overview(
    db: AsyncSession, month: str, current_user: User | None = None
) -> dict[str, Any]:
    """Get budget overview for a month（``GET /api/statistics/budget-overview``）.

    v1.4.3 M12 适配：预算不再「每分类一条」，故 ``categories`` 明细改为
    **按 (预算 × 计入分类)** 逐条归属——旧数据（每分类一条 include 预算）下
    输出与 v1.4.2 完全一致；``total_*`` 恒按预算本体求和（与 D4 同一口径）。

    v1.4.3-boot2 M3（决策 D10，任务 4.1）：概览口径**剔除 dormant 预算**——
    快照构建阶段即跳过，故 total 与 categories 明细都不含休眠行。
    月度预算列表（``get_budgets``）**不**过滤 dormant，前端置灰需要它。
    """
    user_id = current_user.id if current_user else None
    stmt = _apply_budget_owner_filter(
        select(Budget).where(Budget.month == month).order_by(cast("Any", Budget.id)), user_id
    )
    snapshots = [
        _BudgetSnapshot.from_budget(b)
        for b in (await db.exec(stmt)).all()
        if not b.dormant  # D10：休眠预算不进月概览
    ]
    details = await _details_for(db, snapshots, {}, user_id)

    total_budget = 0.0
    total_spent = 0.0
    categories_data: list[dict[str, Any]] = []

    for detail in details:
        total_budget += detail["amount"]
        total_spent += detail["spent"]
        for entry in detail["details"]:
            pct = entry["spent"] / detail["amount"] * 100 if detail["amount"] > 0 else 0
            categories_data.append(
                {
                    "budget_id": detail["id"],
                    "budget_name": detail["name"],
                    "category_id": entry["category_id"],
                    "category_name": entry["category_name"],
                    "icon": entry["icon"],
                    "budget": detail["amount"],
                    "spent": entry["spent"],
                    "remaining": round_money(max(detail["amount"] - entry["spent"], 0)),
                    "percentage": round(pct, 1),
                    "status": (
                        "exceeded" if pct > 100 else "warning" if pct >= 80 else "normal"
                    ),
                }
            )

    total_remaining = round_money(max(total_budget - total_spent, 0))
    overall_percentage = (
        round(total_spent / total_budget * 100, 1) if total_budget > 0 else 0
    )

    return {
        "month": month,
        "total_budget": round_money(total_budget),
        "total_spent": round_money(total_spent),
        "total_remaining": total_remaining,
        "overall_percentage": overall_percentage,
        "categories": categories_data,
    }
