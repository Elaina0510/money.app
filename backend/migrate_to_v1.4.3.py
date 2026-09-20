"""Migration script: v1.4.3 — categories 统一（阶段 A）+ budgets 命名预算（阶段 B）.

v1.4.3 M8 建立骨架并交付**阶段 A（分类合并）**；阶段 B（预算重建）由 M12 在同一
脚本、同一事务内续写（设计 §8.2.6 与决策 D1：分类在前、预算在后）。

阶段 A 做什么（需求八 / 设计 §8.2.6）：
  1. 按 user_id 分桶（NULL=预设桶），桶内**同名即合并**（保留原 type=expense 行）；
  2. loser 行的引用重定向（records / tags / quick_templates）后删除；
     映射 merge_map[loser]=kept 在内存中直接服务阶段 B（同事务同进程）；
     budgets 归阶段 B 处理，本阶段原样不损；
  3. 「其他支出 / 其他收入」归一为「其他」（icon 固定 mdi-cash-minus、恒末位）；
  4. 桶内 sort_order 重排为 1..n 无空洞（支出组 → 仅收入侧行 → 其他）；
  5. 预设桶按 14 条单套清单校准 icon；
  6. categories **整表重建**完成表级 UNIQUE 换形 (name,type,user_id) → (name,user_id)。

用法：
    cd backend
    python migrate_to_v1.4.3.py            # 默认 ./money.db
    python migrate_to_v1.4.3.py /path/db   # 指定库路径

幂等：判据 = `sqlite_master` 中 categories 的 **CREATE TABLE 文本**（归一空白后）已含
`UNIQUE (name, user_id)` → 阶段 A 整体 [SKIP]。**不可用 `PRAGMA index_list` 判名**——
表级约束的支撑索引恒为 `sqlite_autoindex_categories_N`，自定义约束名永不出现。
识别两代旧形：`UNIQUE (name, type)`（v1.2 前）与 `UNIQUE (name, type, user_id)`（v1.4 起）。

事务：全程**单事务**（`engine.begin()`），任何一步失败整体回滚，库保持迁移前状态
（SQLite 的 DDL 参与事务，故阶段 A + 阶段 B 原子完成）。

回滚说明（任务 7.10）：**不提供 downgrade 代码路径**。个人库场景下的回滚 =
恢复发布流程中的 db 备份文件（沿 v1.4.2 口径）。发布步骤 = 停服 → **备份 money.db**
→ 跑本脚本并核对 `[OK]/[SKIP]` → 部署新前后端 → 升级抽检。
开发库旧形制登记（附录 A 第 5 条）：不假设库必处于 v1.4.2 后标准态——实测开发库
`money.db` 的 budgets 为 `UNIQUE(category_id, month)`（无 user_id）、quick_templates
无 kind 列；升级抽检请以 `sqlite_master` 输出核对现场形制后再执行。
"""

import asyncio
import re
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ── 阶段 A 判据常量 ───────────────────────────────────────────────────────
NEW_UNIQUE_SHAPE = "UNIQUE (name, user_id)"
LEGACY_UNIQUE_SHAPES = ("UNIQUE (name, type, user_id)", "UNIQUE (name, type)")

# 「其他」归一（D11）：新名 + 旧双套名 + 固定图标
OTHER_CATEGORY_NAME = "其他"
LEGACY_OTHER_NAMES = ("其他支出", "其他收入")
OTHER_CATEGORY_ICON = "mdi-cash-minus"

# 14 条单套预设（设计 §8.2.4，name/icon/sort_order 三元组；与 app/main.py
# PRESET_CATEGORIES 同序同值——test_migration_v143.py 有一致性断言防漂移）
PRESET_TRIPLES: tuple[tuple[str, str, int], ...] = (
    ("餐饮", "mdi-food", 1),
    ("出行", "mdi-bus", 2),
    ("购物", "mdi-cart", 3),
    ("娱乐", "mdi-gamepad", 4),
    ("医疗", "mdi-hospital-box", 5),
    ("居住", "mdi-home", 6),
    ("通讯", "mdi-cellphone", 7),
    ("工作", "mdi-briefcase", 8),
    ("旅行", "mdi-bag-suitcase", 9),
    ("账单与费用", "mdi-receipt-text", 10),
    ("工资", "mdi-wallet", 11),
    ("红包", "mdi-gift", 12),
    ("理财", "mdi-finance", 13),
    ("其他", "mdi-cash-minus", 14),
)

# categories 规范列（整表重建按此顺序建表；旧库缺列时以默认值补齐）
_CATEGORY_COLUMNS = (
    "id",
    "name",
    "type",
    "icon",
    "sort_order",
    "is_preset",
    "created_at",
    "user_id",
)

_CATEGORY_DDL = """
CREATE TABLE categories_new (
    id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    icon VARCHAR NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_preset INTEGER NOT NULL DEFAULT 0,
    created_at VARCHAR NOT NULL DEFAULT '',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (id),
    CONSTRAINT idx_categories_name_user UNIQUE (name, user_id)
)
"""

# loser 引用重定向表（任务 7.4；operation_history 快照文本属历史审计，不追改）
_CATEGORY_REF_TABLES = ("records", "tags", "quick_templates")

# ── 阶段 B 判据常量（M12：budgets 重建 + budget_categories 关联表）────────────
# 迁移产出的「未知分类」只读态预算名（设计 §12.2.6 第 2 步；与 app/models/budget.py
# 的 UNKNOWN_CATEGORY_NAME 同值，脚本自带常量以保持独立可执行）
UNKNOWN_CATEGORY_NAME = "未知分类"

# 幂等判据（任务 9.1）：PRAGMA table_info 已含新形列 → SKIP。
# budgets 与 categories 的换形不同——categories 新旧列集完全相同（只有表级约束换形，
# 故 D1 规定必须读 sqlite_master 文本），budgets 的列集本身变了，PRAGMA 即可判定；
# 两条判据**同时成立**才 SKIP，再叠加下面的建表文本标记，防半截形制被误判。
_BUDGETS_NEW_COLUMNS = ("name", "scope_mode")
_BUDGETS_NEW_SHAPE_MARKERS = ("name VARCHAR NOT NULL", "scope_mode VARCHAR NOT NULL")
# budgets 新形不再有 category_id 列（关联改走 budget_categories）
_LEGACY_BUDGET_REQUIRED = ("category_id", "month", "amount")
# 旧形表级 UNIQUE 的两代写法——**仅用于日志登记**：阶段 B 按「实际存在的列」整表
# 搬运，不据约束名分支（任务 10.6 / 附录 A 第 5 条：开发库 budgets 为
# UNIQUE(category_id, month) 无 user_id，与模型声明不一致，不假设库形制）。
_LEGACY_BUDGET_UNIQUE_SHAPES = (
    "UNIQUE (category_id, month, user_id)",
    "UNIQUE (category_id, month)",
)

# 旧 budgets 的规范列（按此顺序读取；缺列按默认值补齐）
_BUDGET_LEGACY_COLUMNS = (
    "id",
    "user_id",
    "category_id",
    "month",
    "amount",
    "created_at",
    "updated_at",
)

# 新 budgets（无任何表级 UNIQUE：同月多条、同名多条均合法——任务 1.1）
_BUDGETS_NEW_DDL = """
CREATE TABLE budgets_new (
    id INTEGER NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    month VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    scope_mode VARCHAR NOT NULL DEFAULT 'include',
    created_at VARCHAR NOT NULL DEFAULT '',
    updated_at VARCHAR NOT NULL DEFAULT '',
    PRIMARY KEY (id)
)
"""

# 关联表（任务 1.2）：预算 ↔ 分类多对多，ondelete=CASCADE 仅作模式声明
# （连接未启用 PRAGMA foreign_keys，运行时的级联由 category_service 显式完成）
_BUDGET_CATEGORIES_DDL = """
CREATE TABLE budget_categories (
    id INTEGER NOT NULL,
    budget_id INTEGER NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    PRIMARY KEY (id),
    CONSTRAINT idx_budgetcat_budget_category UNIQUE (budget_id, category_id)
)
"""


def _db_url(argv: list[str]) -> str:
    path = argv[1] if len(argv) > 1 else "./money.db"
    return f"sqlite+aiosqlite:///{path}"


def _normalize_ddl(ddl: str) -> str:
    """建表文本归一：折叠空白 + 大写关键字比对用（幂等判据读的就是这个）。"""
    return re.sub(r"\s+", " ", ddl).strip()


async def _table_ddl(conn: Any, table: str) -> str | None:
    row = (
        await conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name = :t"),
            {"t": table},
        )
    ).fetchone()
    return row[0] if row and row[0] else None


async def _table_exists(conn: Any, table: str) -> bool:
    row = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name = :t"),
            {"t": table},
        )
    ).fetchone()
    return row is not None


async def _columns_of(conn: Any, table: str) -> list[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
    return [r[1] for r in rows]


# ── 阶段 A：分类合并 ──────────────────────────────────────────────────────
async def migrate_categories_phase_a(conn: Any) -> dict[int, int]:
    """执行阶段 A，返回 merge_map（loser id → kept id）供同事务的阶段 B 内存接力。"""
    ddl = await _table_ddl(conn, "categories")
    if ddl is None:
        print("  [SKIP] categories 表不存在（新库将由应用自动建表）")
        return {}

    norm = _normalize_ddl(ddl)
    if NEW_UNIQUE_SHAPE in norm:
        print(f"  [SKIP] categories 已是 v1.4.3 形制（{NEW_UNIQUE_SHAPE}）")
        return {}

    detected = next((s for s in LEGACY_UNIQUE_SHAPES if s in norm), None)
    if detected is None:
        raise RuntimeError(
            "categories 建表文本未匹配到任何已知形制，拒绝猜测执行整表重建；"
            "请以 `SELECT sql FROM sqlite_master WHERE name='categories'` 核对现场形制"
        )
    print(f"  [..] 识别 categories 旧形：{detected}")

    rows = await _load_categories(conn)
    buckets: dict[int | None, list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(row["user_id"], []).append(row)

    merge_map: dict[int, int] = {}
    merged_groups = 0
    renamed_others = 0
    for bucket in buckets.values():
        merged_groups += _merge_same_name(bucket, merge_map)
        renamed_others += _normalize_other(bucket, merge_map)

    redirected = await _redirect_and_delete(conn, merge_map)
    renumbered_buckets = _renumber_sort(buckets)
    await _apply_rows(conn, bucket_rows(buckets))

    # 整表重建：表级 UNIQUE 不可 ALTER、其 autoindex 不可 DROP —— 唯一换形路径
    await _rebuild_categories_table(conn)

    # 本阶段自有外键自检（budgets 的悬挂引用由阶段 B 用 merge_map 消解后统一全局校验）
    dangling = (await conn.execute(text("PRAGMA foreign_key_check(categories)"))).fetchall()
    if dangling:
        raise RuntimeError(f"categories 自身外键校验存在 {len(dangling)} 条违规，已回滚")

    print(
        f"  [OK] 合并 {merged_groups} 组同名分类 / 重定向 {redirected} 条引用 "
        f"/ 归一 {renamed_others} 个「{OTHER_CATEGORY_NAME}」 / 重排 {renumbered_buckets} 个桶"
        f"（merge_map {len(merge_map)} 条已移交阶段 B）"
    )
    return merge_map


def bucket_rows(buckets: dict[int | None, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """展平各桶存活行（loser 已标记 deleted，不入库）。"""
    return [r for bucket in buckets.values() for r in bucket if not r["deleted"]]


async def _load_categories(conn: Any) -> list[dict[str, Any]]:
    cols = await _columns_of(conn, "categories")
    select_cols = ", ".join(
        (f"IFNULL({c}, '')" if c in ("name", "type", "icon", "created_at")
         else f"COALESCE({c}, 0)" if c in ("sort_order", "is_preset") else c)
        for c in cols
    )
    order = ", ".join(
        ["sort_order", "id"] if {"sort_order", "id"} <= set(cols) else ["id"]
    )
    fetched = (
        await conn.execute(text(f"SELECT {select_cols} FROM categories ORDER BY {order}"))
    ).fetchall()
    rows: list[dict[str, Any]] = []
    for record in fetched:
        row = dict(zip(cols, record, strict=True))
        for missing in [c for c in _CATEGORY_COLUMNS if c not in cols]:
            row[missing] = "" if missing in ("name", "type", "icon", "created_at") else None
        if row["type"] == "":
            row["type"] = "expense"
        if row["icon"] == "":
            row["icon"] = "mdi-circle"
        row["sort_order"] = int(row["sort_order"] or 0)
        row["is_preset"] = int(row["is_preset"] or 0)
        row["deleted"] = False
        rows.append(row)
    return rows


def _merge_same_name(bucket: list[dict[str, Any]], merge_map: dict[int, int]) -> int:
    """任务 7.3：桶内按 name 分组，同名多行保留 expense 行、其余作 loser 并入。

    Returns:
        发生合并的同名组数。
    """
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in bucket:
        by_name.setdefault(row["name"], []).append(row)

    groups = 0
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        groups += 1
        keepers = [r for r in group if r["type"] == "expense"]
        kept = keepers[0] if keepers else group[0]
        for row in group:
            if row is kept:
                continue
            row["deleted"] = True
            merge_map[row["id"]] = kept["id"]
    return groups


def _normalize_other(
    bucket: list[dict[str, Any]], merge_map: dict[int, int]
) -> int:
    """任务 7.5：桶内「其他支出 / 其他收入 / 自建其他」归一为唯一「其他」。

    优先级：已存在名为「其他」的行 > 「其他支出」 > 「其他收入」——其余作 loser
    并入（改名会撞新 UNIQUE(name,user_id) 的行必须由被改名行让位，故先删后改名）。
    """
    family = [
        r for r in bucket
        if not r["deleted"] and r["name"] in (OTHER_CATEGORY_NAME, *LEGACY_OTHER_NAMES)
    ]
    if not family:
        return 0

    keeper = next((r for r in family if r["name"] == OTHER_CATEGORY_NAME), None)
    if keeper is None:
        keeper = next((r for r in family if r["name"] == LEGACY_OTHER_NAMES[0]), family[0])
    for row in family:
        if row is keeper:
            continue
        row["deleted"] = True
        merge_map[row["id"]] = keeper["id"]
    keeper["name"] = OTHER_CATEGORY_NAME
    keeper["icon"] = OTHER_CATEGORY_ICON
    keeper["is_other"] = True
    return 1 if len(family) > 1 else 0


async def _redirect_and_delete(conn: Any, merge_map: dict[int, int]) -> int:
    """任务 7.4：loser 引用重定向（records/tags/quick_templates）后 DELETE loser 行。"""
    if not merge_map:
        return 0
    redirected = 0
    for table in _CATEGORY_REF_TABLES:
        if not await _table_exists(conn, table):
            continue
        for loser, kept in merge_map.items():
            res = await conn.execute(
                text(f"UPDATE {table} SET category_id = :kept WHERE category_id = :loser"),
                {"kept": kept, "loser": loser},
            )
            redirected += res.rowcount or 0
    loser_ids = list(merge_map)
    for loser in loser_ids:
        await conn.execute(text("DELETE FROM categories WHERE id = :i"), {"i": loser})
    return redirected


def _renumber_sort(buckets: dict[int | None, list[dict[str, Any]]]) -> int:
    """任务 7.6 + 7.7：桶内序 = 支出组 → 仅收入侧行 → 「其他」，sort_order 重写 1..n。"""
    for user_id, bucket in buckets.items():
        alive = [r for r in bucket if not r["deleted"]]
        expense_part = [r for r in alive if not r.get("is_other") and r["type"] == "expense"]
        income_part = [r for r in alive if not r.get("is_other") and r["type"] != "expense"]
        other_part = [r for r in alive if r.get("is_other")]
        ordered = (
            sorted(expense_part, key=lambda r: (r["sort_order"], r["id"]))
            + sorted(income_part, key=lambda r: (r["sort_order"], r["id"]))
            + sorted(other_part, key=lambda r: (r["sort_order"], r["id"]))
        )
        if user_id is None:
            _calibrate_presets(ordered)
        for position, row in enumerate(ordered, start=1):
            row["sort_order"] = position
    return len(buckets)


def _calibrate_presets(ordered: list[dict[str, Any]]) -> None:
    """任务 7.7：预设桶逐条以 name 定位纠 icon（多余预设行仅「其他收入」已在归一步删除）。"""
    icons = {name: icon for name, icon, _ in PRESET_TRIPLES}
    for row in ordered:
        if row["name"] in icons:
            row["icon"] = icons[row["name"]]


async def _apply_rows(conn: Any, rows: list[dict[str, Any]]) -> None:
    """把内存中的改名/纠图标/重排结果写回旧表（整表重建前的唯一数据修正窗口）。

    只写旧表真实存在的列：开发库可能缺 user_id / created_at / is_preset 等列
    （附录 A 第 5 条「不假设库处于标准态」），无条件 SET 会直接中断迁移。
    """
    cols = set(await _columns_of(conn, "categories"))
    candidates = ("name", "type", "icon", "sort_order", "is_preset", "created_at", "user_id")
    writable = [c for c in candidates if c in cols]
    if not writable:
        return
    set_clause = ", ".join(f"{c} = :{c}" for c in writable)
    for row in sorted(rows, key=lambda r: r["id"]):
        params: dict[str, Any] = {c: row[c] for c in writable}
        if "type" in params and not params["type"]:
            params["type"] = "expense"
        params["id"] = row["id"]
        await conn.execute(
            text(f"UPDATE categories SET {set_clause} WHERE id = :id"), params
        )


async def _rebuild_categories_table(conn: Any) -> None:
    """任务 7.8：categories 整表重建（约束换形唯一路径）。"""
    cols = await _columns_of(conn, "categories")
    target_cols = [c for c in _CATEGORY_COLUMNS if c in cols]
    select_exprs = ", ".join(
        (f"COALESCE({c}, '')" if c in ("name", "type", "icon", "created_at")
         else f"COALESCE({c}, 0)" if c in ("sort_order", "is_preset") else c)
        for c in target_cols
    )
    await conn.execute(text(_CATEGORY_DDL))
    await conn.execute(
        text(
            f"INSERT INTO categories_new ({', '.join(target_cols)}) "
            f"SELECT {select_exprs} FROM categories"
        )
    )
    await conn.execute(text("DROP TABLE categories"))
    await conn.execute(text("ALTER TABLE categories_new RENAME TO categories"))


# ── 阶段 B：预算重建（设计 §12.2.6，与阶段 A 同事务）───────────────────────
async def _convert_legacy_budgets(
    conn: Any, merge_map: dict[int, int]
) -> tuple[list[dict[str, Any]], list[tuple[int, int]], int, int]:
    """旧 budgets 逐行 1:1 转换（任务 9.2–9.4）。

    Returns:
        ``(预算行, 关联行 (budget_id, category_id), 重定向条数, 未知分类条数)``

    * ``cid' = merge_map.get(old.cid, old.cid)``——阶段 A 的内存映射直接接力，
      被合并分类的预算引用随之指向保留行（同事务内已看不到 loser id）；
    * ``name`` = 保留分类行的**当前**名（阶段 A 可能已把它改名，如「其他收入」→「其他」）；
    * 分类已被彻底删除 → 名「未知分类」、无关联行、scope 仍 include（只读态：
      正常展示、spent=0、可删，仅 PUT 重保存被「include ≥1」校验拦截——任务 9.3）；
    * 同月多条 → 多条新记录，**不做任何合并**（任务 9.4），原 id 原样保留。
    """
    old_cols = set(await _columns_of(conn, "budgets"))
    read_cols = [c for c in _BUDGET_LEGACY_COLUMNS if c in old_cols]
    rows = (
        await conn.execute(
            text(f"SELECT {', '.join(read_cols)} FROM budgets ORDER BY id")
        )
    ).fetchall()
    # 阶段 A 之后的分类现状（id → name）：loser 已删、保留行可能已改名
    cat_names = {
        int(r[0]): str(r[1])
        for r in (
            await conn.execute(text("SELECT id, name FROM categories"))
        ).fetchall()
        if r[0] is not None
    }

    budgets: list[dict[str, Any]] = []
    links: list[tuple[int, int]] = []
    redirected = 0
    unknown = 0

    for raw in rows:
        row = dict(zip(read_cols, raw, strict=True))
        old_cid = row.get("category_id")
        cid: int | None = None
        if old_cid is not None:
            cid = merge_map.get(int(old_cid), int(old_cid))
            if cid != int(old_cid):
                redirected += 1
        if cid is not None and cid in cat_names:
            name = cat_names[cid]
        else:
            name = UNKNOWN_CATEGORY_NAME
            cid = None
            unknown += 1

        budget_id = int(row["id"]) if row.get("id") is not None else None
        if budget_id is None:  # 理论不可达：旧表 id 为主键
            continue
        budgets.append(
            {
                "id": budget_id,
                "user_id": row.get("user_id"),
                "name": name,
                "month": str(row.get("month") or ""),
                "amount": float(row.get("amount") or 0),
                "scope_mode": "include",
                "created_at": str(row.get("created_at") or ""),
                "updated_at": str(row.get("updated_at") or row.get("created_at") or ""),
            }
        )
        if cid is not None:
            links.append((budget_id, cid))

    # 同一条旧预算不会重复挂同一分类，但旧库无外键约束、极端数据可能重复 → 去重
    deduped: list[tuple[int, int]] = list(dict.fromkeys(links))
    return budgets, deduped, redirected, unknown


async def _rebuild_budgets_table(
    conn: Any, budgets: list[dict[str, Any]], links: list[tuple[int, int]]
) -> None:
    """任务 9.5：整表重建 budgets（与阶段 A 同法）+ 新建 budget_categories。

    顺序要点：先 RENAME 归位 budgets，再建引用它的 budget_categories，
    使关联表的 FK 文本直接落在最终表名上。全程只用传入的 conn（单事务）。
    """
    await conn.execute(text(_BUDGETS_NEW_DDL))
    for row in budgets:
        await conn.execute(
            text(
                "INSERT INTO budgets_new (id, user_id, name, month, amount, scope_mode,"
                " created_at, updated_at) VALUES (:id, :user_id, :name, :month, :amount,"
                " :scope_mode, :created_at, :updated_at)"
            ),
            row,
        )
    await conn.execute(text("DROP TABLE budgets"))
    await conn.execute(text("ALTER TABLE budgets_new RENAME TO budgets"))

    # 关联表整体重建（旧库可能残留半截表，此处按本阶段的行集唯一真源重写）
    await conn.execute(text("DROP TABLE IF EXISTS budget_categories"))
    await conn.execute(text(_BUDGET_CATEGORIES_DDL))
    for budget_id, category_id in links:
        await conn.execute(
            text(
                "INSERT INTO budget_categories (budget_id, category_id)"
                " VALUES (:b, :c)"
            ),
            {"b": budget_id, "c": category_id},
        )


async def migrate_budgets_phase_b(conn: Any, merge_map: dict[int, int]) -> None:
    """阶段 B（M12）：budgets 重建为「每月多条命名预算」+ budget_categories 关联表。

    约束（D1）：与阶段 A 同处 `engine.begin()` 的连接内、**不 commit 也不 rollback**，
    阶段 A 产出的 ``merge_map``（loser→kept）在内存中直接接力；阶段 B 任何一步失败
    即整体回滚（SQLite 的 DDL 参与事务），阶段 A 同样不落库。
    """
    if not await _table_exists(conn, "budgets"):
        print("  [SKIP] budgets 表不存在（新库将由应用自动建表）")
        return

    ddl = await _table_ddl(conn, "budgets")
    norm = _normalize_ddl(ddl or "")
    cols = set(await _columns_of(conn, "budgets"))

    # 幂等判据（任务 9.1）：新形列齐 → 再按 D1 读建表文本确认，两者同时成立才 SKIP
    if all(c in cols for c in _BUDGETS_NEW_COLUMNS) and "category_id" not in cols:
        if all(marker in norm for marker in _BUDGETS_NEW_SHAPE_MARKERS):
            print("  [SKIP] budgets 已是 v1.4.3 形制（name/scope_mode + budget_categories）")
            return
        raise RuntimeError(
            "budgets 列形为新形但建表文本不含预期标记，拒绝猜测执行整表重建；"
            "请以 `SELECT sql FROM sqlite_master WHERE name='budgets'` 核对现场形制"
        )
    missing = [c for c in _LEGACY_BUDGET_REQUIRED if c not in cols]
    if missing:
        raise RuntimeError(
            f"budgets 既非 v1.4.3 新形也非可识别的旧形（缺列 {missing}），拒绝猜测执行"
            "整表重建；请以 `PRAGMA table_info(budgets)` 核对现场形制"
        )

    detected = next((s for s in _LEGACY_BUDGET_UNIQUE_SHAPES if s in norm), None)
    print(f"  [..] 识别 budgets 旧形：{detected or '无表级 UNIQUE 约束（按列搬运）'}")

    budgets, links, redirected, unknown = await _convert_legacy_budgets(conn, merge_map)
    await _rebuild_budgets_table(conn, budgets, links)

    # 本阶段自有外键自检（budgets→users；budget_categories→budgets/categories）
    for table in ("budgets", "budget_categories"):
        violations = (
            await conn.execute(text(f"PRAGMA foreign_key_check({table})"))
        ).fetchall()
        if violations:
            raise RuntimeError(
                f"{table} 外键校验存在 {len(violations)} 条违规（阶段 B 后应零悬挂），已回滚"
            )

    print(
        f"  [OK] 转换 {len(budgets)} 条预算（含 {redirected} 条重定向分类引用）"
    )
    if unknown:
        print(
            f"  [..] 其中 {unknown} 条引用的分类已不存在 → 「{UNKNOWN_CATEGORY_NAME}」"
            "只读态（可展示/删除，重保存需补选分类）"
        )


async def migrate(argv: list[str]) -> int:
    database_url = _db_url(argv)
    print(f"[v1.4.3 migration] target: {database_url}")
    engine = create_async_engine(database_url, echo=False)
    try:
        # 单事务：阶段 A + 阶段 B 原子完成（SQLite DDL 参与事务）
        async with engine.begin() as conn:
            merge_map = await migrate_categories_phase_a(conn)
            await migrate_budgets_phase_b(conn, merge_map)
            # 全局外键自检：阶段 B 用 merge_map 消解 budgets 悬挂引用后必须零违规
            dangling = (await conn.execute(text("PRAGMA foreign_key_check"))).fetchall()
            if dangling:
                raise RuntimeError(f"迁移后 foreign_key_check 存在 {len(dangling)} 条违规，已回滚")
    finally:
        await engine.dispose()

    print("[v1.4.3 migration] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate(sys.argv)))
