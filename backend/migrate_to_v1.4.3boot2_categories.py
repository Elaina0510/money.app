"""Migration script: v1.4.3-boot2 M2 —— 「其他支出 / 其他收入」归并入「其他」（需求二）.

现场库（未执行 `migrate_to_v1.4.3.py`）**并存**三个「其他」类行：预设「其他」(sort=14)
+ 旧预设「其他支出」「其他收入」(sort=99 压在其后)，用户副本桶同形。本脚本按
`user_id` 分桶把桶内家族行归并为**单一「其他」**（引用重定向后删旧行、keeper 置尾），
使分类页三行变一行、历史账单/模板/预算关联全部指向「其他」。

设计依据：`doc/detailed-designv1.4.3boot2.md` §二（§2.2.1 脚本设计、§2.2.2/§2.2.3
独立性核查、§2.4 测试）。**零运行期代码改动**（`app/` 一字不动）。

以 `migrate_to_v1.4.3.py` 的 `_normalize_other`(:310-336) / `_redirect_and_delete`
(:339-356) / 重排(:359-374) 为**蓝本独立实现**（不 import、不修改、不绑定该脚本，D11）：

* 范围收窄为「只并其他家族」——不做同名合并、不做整表重建、不做 1..n 全量重排
  （那些属 v1.4.3 阶段 A/B，两脚本任意顺序均收敛，见 §2.2.3 与本文件末尾「独立性」段）；
* 家族常量**脚本侧独立定义**（不 import `app/`，保证停服窗口裸库可执行），
  与 `app/services/category_service.py` 的同名常量以 **⊇/⊆ 双向一致性断言**钉住
  （`test_categories_reorder.py` §5.4 + `test_migration_v143boot2_categories.py` §3.2）。

用法：
    cd backend
    python migrate_to_v1.4.3boot2_categories.py            # 默认 ./money.db
    python migrate_to_v1.4.3boot2_categories.py /path/db   # 指定库路径

幂等：判据 = 每桶家族行数 ≤1 且该 keeper 已名「其他」+ icon `mdi-cash-minus` + 已处
桶内末位 → 全部统计归 0（`[SKIP] ... no-op`）。二次执行零改动即幂等证明。

事务：全程**单事务**（`engine.begin()`），任何一步失败整体回滚，库保持执行前状态，
可直接重跑（沿蓝本手法）。执行前置检查只读：`PRAGMA integrity_check` 摘要 + 家族行
清单打印（integrity 非 ok 时**只告警不中止**——备份与人工判读属发布窗口纪律）。

备份：**本脚本不做备份**（附录 A 把「先备份现场库文件」固化为发布窗口操作序第 1 步）。

已知边界（§2.2.3 未跑 v1.4.3 的极旧库）：预算关联落在旧列 `budgets.category_id` 上
时**不**在本期重定向集合内（设计 §2.2.1 集合无它；且旧形 `UNIQUE(category_id, month)`
下重定向可能撞形、只能靠删预算让位，超出「不丢覆盖」的范围）。该形库若挂过家族
loser，其后执行 `migrate_to_v1.4.3.py` 阶段 B 会按 merge_map/「未知分类」承接。
现场库实测（副本取证）该形制下 6 条预算均未挂家族行，不受影响。

运行期兼容（D2，M1 已交付）：脚本执行**前**，后端 `OTHER_FAMILY_RANK` 与前端
`normalizeTail` 已按三名集合把家族行统一置尾，拖拽不卡死；执行**后**只剩本名
「其他」，同一套判据自然退化为单行末位——脚本可随时执行、可单独重跑、可与
`migrate_to_v1.4.3boot2_dormant.py` 任意顺序（D11）。
"""

import asyncio
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ── 家族常量（脚本侧独立定义；与 category_service 逐名一致，一致性断言钉住）──
OTHER_CATEGORY_NAME = "其他"
LEGACY_OTHER_NAMES = ("其他支出", "其他收入")
# 家族固定名次（D6）：其他支出 < 其他收入 < 其他——「其他」恒最大。
OTHER_FAMILY_RANK: dict[str, int] = {"其他支出": 0, "其他收入": 1, "其他": 2}
# keeper 优先级（设计 §2.2.1「与蓝本一致」）：**其他 > 其他支出 > 其他收入**。
# 注意这**不是** OTHER_FAMILY_RANK 的倒序——名次表是「置尾时的排列序」
# （其他支出 < 其他收入 < 其他），keeper 优先级另有一层语义：本名行优先，
# 两个旧名行里「其他支出」优先（蓝本 :325-327 即 `其他` → `LEGACY_OTHER_NAMES[0]`
# → family[0] 的次序）。两者混用会把 keeper 选到语义上应让位的那一行。
KEEPER_PRIORITY: tuple[str, ...] = (OTHER_CATEGORY_NAME, *LEGACY_OTHER_NAMES)
# keeper 图标：对齐 `app/main.py` 预设 14 条单套里「其他」的固定值
OTHER_CATEGORY_ICON = "mdi-cash-minus"

_FAMILY_NAMES: frozenset[str] = frozenset(OTHER_FAMILY_RANK)

# categories 读取列（缺列按默认值补齐，不假设库处于标准态——沿蓝本附录 A 第 5 条）
_CATEGORY_COLUMNS = ("id", "name", "icon", "sort_order", "user_id")
# 只回写这三列：type/is_preset/created_at 一律原样不损（本期不改语义）
_KEEPER_WRITABLE_COLUMNS = ("name", "icon", "sort_order")

# loser 引用重定向表（设计 §2.2.1）：`records` / `quick_templates` / `tags`（其
# category_id 列真实存在，逐表探测）+ **`budget_categories`（本期新增，蓝本没有）**。
# `record_tags` **不列入**：它只关联 (record_id, tag_id)、无 category_id 列，
# 其对分类的引用经 records 已覆盖（同 §2.2.1「record_tags→经 records 无需」）。
_CATEGORY_REF_TABLES = ("records", "tags", "quick_templates", "budget_categories")
# 带 (兄弟列, category_id) 表级唯一约束的关联表：keeper 已被同一预算关联时，
# 重定向会撞形 → 该 loser 关联行**先去重删除**（覆盖本已存在，预算覆盖不因此改变）。
_DEDUPE_LINK_COLUMNS: dict[str, str] = {"budget_categories": "budget_id"}


def _db_url(argv: list[str]) -> str:
    path = argv[1] if len(argv) > 1 else "./money.db"
    return f"sqlite+aiosqlite:///{path}"


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
    return [str(r[1]) for r in rows]


async def _count(conn: Any, table: str, category_id: int) -> int:
    row = (
        await conn.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE category_id = :c"),
            {"c": category_id},
        )
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


# ── 读取与分桶 ────────────────────────────────────────────────────────────
async def _load_categories(conn: Any) -> list[dict[str, Any]]:
    """按实际存在的列读 categories（旧库可能缺 user_id 列 → 全量落预设桶）。"""
    cols = await _columns_of(conn, "categories")
    if "id" not in cols or "name" not in cols:
        raise RuntimeError("categories 表缺 id/name 列，无法识别「其他家族」行，已回滚")
    present = [c for c in _CATEGORY_COLUMNS if c in cols]
    order_cols = (
        ["user_id", "sort_order", "id"] if "user_id" in cols else ["sort_order", "id"]
    )
    order = ", ".join(order_cols)
    fetched = (
        await conn.execute(text(f"SELECT {', '.join(present)} FROM categories ORDER BY {order}"))
    ).fetchall()
    rows: list[dict[str, Any]] = []
    for record in fetched:
        row = dict(zip(present, record, strict=True))
        row.setdefault("icon", "")
        row.setdefault("sort_order", 0)
        row.setdefault("user_id", None)
        row["id"] = int(row["id"])
        row["name"] = str(row["name"] or "")
        row["icon"] = str(row["icon"] or "")
        row["sort_order"] = int(row["sort_order"] or 0)
        row["deleted"] = False
        rows.append(row)
    return rows


def bucket_by_user(rows: list[dict[str, Any]]) -> dict[Any, list[dict[str, Any]]]:
    """按 `user_id` 分桶（键 `None` = 预设桶；跨桶不合并，§2.2.1）。"""
    buckets: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(row["user_id"], []).append(row)
    return buckets


def pick_keeper(family: list[dict[str, Any]]) -> dict[str, Any]:
    """keeper 选取：按 `KEEPER_PRIORITY`（其他 > 其他支出 > 其他收入）；同名行 tie-break。

    tie-break = (sort_order, id) 先者——与蓝本「读表序第一个」等价（`_load_categories`
    已按 (user_id, sort_order, id) 稳定排序），保证同输入同输出、可复算。
    """

    def rank_key(row: dict[str, Any]) -> tuple[int, int, int]:
        return (
            KEEPER_PRIORITY.index(str(row["name"])),
            int(row["sort_order"]),
            int(row["id"]),
        )

    return min(family, key=rank_key)


def _family_rows(bucket: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in bucket if not r["deleted"] and str(r["name"]) in _FAMILY_NAMES]


# ── 前置只读检查 ──────────────────────────────────────────────────────────
async def _precheck(conn: Any, buckets: dict[Any, list[dict[str, Any]]]) -> None:
    check = (await conn.execute(text("PRAGMA integrity_check"))).fetchone()
    verdict = str(check[0]) if check else "no-result"
    if verdict.lower() != "ok":
        print(f"  [WARN] PRAGMA integrity_check → {verdict}（请先备份并人工判读）")
    else:
        print("  [pre-check] PRAGMA integrity_check → ok")
    total = sum(len(_family_rows(bucket)) for bucket in buckets.values())
    print(f"  [pre-check] 家族行清单（共 {total} 行，按桶）：")
    ordered_buckets = sorted(
        buckets.values(),
        key=lambda b: (b[0]["user_id"] is not None, b[0]["user_id"]),
    )
    for bucket in ordered_buckets:
        for row in _family_rows(bucket):
            print(
                f"      user_id={row['user_id']!r} id={row['id']} name={row['name']!r}"
                f" icon={row['icon']!r} sort_order={row['sort_order']}"
            )


# ── 引用重定向 + loser 删除 ───────────────────────────────────────────────
async def _drop_dupe_links(
    conn: Any, table: str, link_col: str, loser: int, kept: int
) -> int:
    """删除「同一 link_col（预算）既挂 loser 又挂 keeper」的 loser 关联行，返回条数。

    关联表的 `(link_col, category_id)` 表级唯一约束会让随后的 UPDATE 撞形；这类
    loser 行的语义已被 keeper 覆盖承载，删掉即等价于「重定向后自动去重」。
    """
    sql = (
        f"DELETE FROM {table} WHERE category_id = :loser AND {link_col} IN"
        f" (SELECT {link_col} FROM {table} WHERE category_id = :kept)"
    )
    rowcount = (await conn.execute(text(sql), {"loser": loser, "kept": kept})).rowcount
    return int(rowcount) if rowcount and rowcount > 0 else 0


async def _redirect_and_delete(
    conn: Any, merge_map: dict[int, int]
) -> tuple[dict[str, int], dict[str, int]]:
    """loser 引用逐表重定向到 keeper 后 DELETE loser 行；缺表/缺列探测跳过。

    返回 `(redirected_per_table, deduped_per_table)`。表级唯一约束可能撞形
    （`budget_categories(budget_id, category_id)`），故这类表先把「keeper 已被同一
    预算关联」的 loser 行去重删除，再重定向其余行。
    """
    redirected: dict[str, int] = {}
    deduped: dict[str, int] = {}
    if not merge_map:
        return redirected, deduped

    for table in _CATEGORY_REF_TABLES:
        if not await _table_exists(conn, table):
            print(f"  [..] {table} 表不存在（版本混跑）→ 跳过")
            continue
        if "category_id" not in await _columns_of(conn, table):
            print(f"  [..] {table} 无 category_id 列 → 跳过")
            continue
        link_col = _DEDUPE_LINK_COLUMNS.get(table)
        for loser, kept in sorted(merge_map.items()):
            if link_col:
                deduped[table] = deduped.get(table, 0) + await _drop_dupe_links(
                    conn, table, link_col, loser, kept
                )
            pending = await _count(conn, table, loser)
            if pending:
                await conn.execute(
                    text(f"UPDATE {table} SET category_id = :kept WHERE category_id = :loser"),
                    {"kept": kept, "loser": loser},
                )
                redirected[table] = redirected.get(table, 0) + pending

    # 重定向完成后才删 loser——顺序不可换（否则子记录悬挂/外键报错）
    for loser in sorted(merge_map):
        await conn.execute(text("DELETE FROM categories WHERE id = :i"), {"i": loser})
    return redirected, deduped


# ── keeper 行回写（改名/刷图标/置尾）─────────────────────────────────────
async def _apply_keepers(conn: Any, changed: list[dict[str, Any]]) -> None:
    """把 keeper 的改名/图标/置尾结果写回库（**必须在 loser 删除之后**）。

    UNIQUE(name,user_id) 撞形说明（蓝本 :313-336 同款）：keeper 由「其他支出」改名
    为「其他」时，桶内原名「其他」的 loser 仍在表里，改名会直接撞唯一约束，
    故 **先 DELETE loser 再改 keeper 名**；旧形 UNIQUE(name,type,user_id) 下同样成立
    （loser 删净后桶内该名字唯一，不受 type 残值影响）。
    """
    if not changed:
        return
    cols = set(await _columns_of(conn, "categories"))
    writable = {c for c in _KEEPER_WRITABLE_COLUMNS if c in cols}
    if not writable:
        return
    for row in sorted(changed, key=lambda r: int(r["id"])):
        # 只回写「本行确实变更 + 该库确实存在」的列（缺列库不炸、未变更列不覆写）
        payload: dict[str, Any] = {c: row[c] for c in writable if c in row}
        if not payload:
            continue
        set_clause = ", ".join(f"{c} = :{c}" for c in payload)
        payload["id"] = row["id"]
        await conn.execute(
            text(f"UPDATE categories SET {set_clause} WHERE id = :id"), payload
        )


def plan_buckets(
    buckets: dict[Any, list[dict[str, Any]]]
) -> tuple[dict[int, int], list[dict[str, Any]], dict[str, int]]:
    """纯计算：桶内家族行归一（keeper 选取 + loser 标记）→ (merge_map, keeper 行, 统计)."""
    merge_map: dict[int, int] = {}
    keepers: list[dict[str, Any]] = []
    counts = {"merged_rows": 0, "keepers_normalized": 0}
    for bucket in buckets.values():
        family = _family_rows(bucket)
        if not family:
            continue
        keeper = pick_keeper(family)
        for row in family:
            if row is keeper:
                continue
            row["deleted"] = True  # 内存标记：真正 DELETE 在 _redirect_and_delete
            merge_map[int(row["id"])] = int(keeper["id"])
        counts["merged_rows"] += len(family) - 1
        # keeper 归一：改名 + 刷图标（幂等：已是「其他」+ 固定图标则零改动）
        needs_name = str(keeper["name"]) != OTHER_CATEGORY_NAME
        needs_icon = str(keeper["icon"]) != OTHER_CATEGORY_ICON
        if needs_name or needs_icon:
            keeper["new_name"] = OTHER_CATEGORY_NAME
            keeper["new_icon"] = OTHER_CATEGORY_ICON
            counts["keepers_normalized"] += 1
        keepers.append(keeper)
    return merge_map, keepers, counts


def fix_tails(
    buckets: dict[Any, list[dict[str, Any]]], keepers: list[dict[str, Any]]
) -> int:
    """置尾：每桶 keeper `sort_order` = 桶内可见**存活**行最大 sort + 1；已是最大不动。

    `> max(others)` 判据保证幂等——回写后 keeper 严格大于其余行，二次执行不再触发。
    """
    tail_fixed = 0
    for keeper in keepers:
        bucket = buckets[keeper["user_id"]]
        others = [
            r for r in bucket if r is not keeper and not r["deleted"]
        ]
        if not others:
            continue  # 桶内仅家族一行 → 天然末位
        max_other = max(int(r["sort_order"]) for r in others)
        if int(keeper["sort_order"]) <= max_other:
            keeper["new_sort_order"] = max_other + 1
            tail_fixed += 1
    return tail_fixed


def _changed_keeper_rows(keepers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把归一/置尾结果落成回写行（未变更的 keeper 不进回写集合 → 幂等）。"""
    rows: list[dict[str, Any]] = []
    for keeper in keepers:
        out: dict[str, Any] = {"id": keeper["id"]}
        if "new_name" in keeper:
            out["name"] = keeper["new_name"]
            out["icon"] = keeper["new_icon"]
        if "new_sort_order" in keeper:
            out["sort_order"] = keeper["new_sort_order"]
        if len(out) > 1:
            rows.append(out)
    return rows


def new_stats() -> dict[str, Any]:
    return {
        "buckets_scanned": 0,
        "merged_rows": 0,
        "keepers_normalized": 0,
        "tail_fixed": 0,
        "redirected_references": {},
        "deduped_references": {},
    }


def is_noop(stats: dict[str, Any]) -> bool:
    return (
        int(stats["merged_rows"]) == 0
        and int(stats["keepers_normalized"]) == 0
        and int(stats["tail_fixed"]) == 0
        and sum(int(v) for v in stats["redirected_references"].values()) == 0
        and sum(int(v) for v in stats["deduped_references"].values()) == 0
    )


async def migrate_other_family(conn: Any) -> dict[str, Any]:
    """单桶计划 → 重定向删 loser → keeper 改名/刷图标 → 置尾回写；返回统计。"""
    stats = new_stats()
    if not await _table_exists(conn, "categories"):
        print("  [SKIP] categories 表不存在（新库将由应用自动建表）")
        return stats

    buckets = bucket_by_user(await _load_categories(conn))
    stats["buckets_scanned"] = len(buckets)
    await _precheck(conn, buckets)

    merge_map, keepers, counts = plan_buckets(buckets)
    for key, value in counts.items():
        stats[key] = int(value)

    # 1) 先重定向 + DELETE loser（改名前置条件，见 _apply_keepers 撞形说明）
    redirected, deduped = await _redirect_and_delete(conn, merge_map)
    stats["redirected_references"] = redirected
    stats["deduped_references"] = deduped

    # 2) 置尾（loser 已从存活集合剔除）+ 3) 回写 keeper
    cols = await _columns_of(conn, "categories")
    if "sort_order" in cols:
        stats["tail_fixed"] = fix_tails(buckets, keepers)
    elif keepers:
        print("  [..] categories 无 sort_order 列 → 跳过置尾（行集仍已归一）")
    await _apply_keepers(conn, _changed_keeper_rows(keepers))
    return stats


def print_stats(stats: dict[str, Any]) -> None:
    if is_noop(stats):
        print(
            "  [SKIP] 各桶家族行已是单一「其他」（末位、icon 固定）→ 本次 no-op"
            f"（扫描 {stats['buckets_scanned']} 桶）"
        )
        return
    print(
        f"  [OK] 归并 loser {stats['merged_rows']} 行"
        f" / keeper 归一（改名·刷图标）{stats['keepers_normalized']} 行"
        f" / 置尾 {stats['tail_fixed']} 桶"
        f" / 重定向引用 {stats['redirected_references'] or '{}'}"
        f" / 撞形去重 {stats['deduped_references'] or '{}'}"
        f"（扫描 {stats['buckets_scanned']} 桶）"
    )


async def run_migration(db_path: str) -> dict[str, Any]:
    """执行迁移（单事务），返回统计摘要（供测试与发布窗口核对）。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    try:
        async with engine.begin() as conn:  # 失败即整体回滚，可重跑
            stats = await migrate_other_family(conn)
            print_stats(stats)
    finally:
        await engine.dispose()
    return stats


async def migrate(argv: list[str]) -> int:
    print(f"[v1.4.3-boot2 categories migration] target: {_db_url(argv)}")
    await run_migration(argv[1] if len(argv) > 1 else "./money.db")
    print("[v1.4.3-boot2 categories migration] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate(sys.argv)))
