"""Migration script: v1.4.3-boot2 M3 —— `budgets` 补 `dormant` 列 + 存量休眠回填（需求三）.

M3 把「include 且分类集为空」从**非法载荷**改判为**动态全部分类**（决策 D3），于是
「空集」一词从此承载两种历史：① 用户一个都不选（= 全部，dormant=0）；② 原本选了
分类、后来关联被删光（= 休眠，dormant=1，D4）。二者必须以显式列区分，故 `budgets`
新增 `dormant INTEGER NOT NULL DEFAULT 0`。

设计依据：`doc/detailed-designv1.4.3boot2.md` §三（§3.2.4 脚本设计、D9/D10/D11 裁定、
§3.4 测试）。**运行期代码**（`app/`）由 M3 后端半区另行交付，本文件只负责存量库收敛。

⚠ 执行窗口硬约定（决策 D11，**发布窗口操作序第 2 步，先于新版后端启动**）：
    1. 备份现场库文件（项目红线，操作纪律，本脚本**不做备份**）；
    2. 停服 → **本脚本必须在替换/启动新版后端之前执行完毕**；
    3. 原因：新版后端启动后「include 空集」是合法的**动态全部**态（dormant=0），
       而本脚本的 backfill 判据正是「include 且无任何关联」——先起服务再跑脚本，
       窗口期内用户新建的「不选=全部」预算会被误标为休眠；
    4. 违反顺序的处置（已裁定，**不写反悔脚本**）：低概率且可自救——用户在前端把
       被误标的预算**编辑并重新保存一次**即清 dormant（D9：任何成功保存一律落 0）。
       不为该假设场景增删代码或提供反向脚本（设计 §3.2.4）。

用法：
    cd backend
    python migrate_to_v1.4.3boot2_dormant.py            # 默认 ./money.db
    python migrate_to_v1.4.3boot2_dormant.py /path/db   # 指定库路径

幂等（两重）：
  * 判据 = `PRAGMA table_info(budgets)` **已含 `dormant` 列 → 整体 no-op**（加列与
    backfill 一并跳过，二次执行统计归 0，`[SKIP]`）；
  * 即使列是本次新增，backfill 也只标「include 且零关联」的行，重跑不再命中。

事务与失败收敛（**副本实测登记的驱动事实**）：全程 `engine.begin()`，其中 DML 可回滚，
而 SQLite 的 **DDL 由驱动即时提交**（临时库注入失败实测：`dormant` 列留下、backfill 的
UPDATE 回滚）。故中途失败的终态 = 「列已加、休眠未标」，二次执行按幂等判据整体 no-op
→ 后果只是**漏标**（良性方向：漏标行按「动态全部」渲染，用户编辑保存即归位，D3/D9），
脚本对该形态**只 WARN 不自动改写**（同一判据也覆盖 D11 违序窗口，见下）。
前置检查只读：`PRAGMA integrity_check` 非 ok 时**只告警不中止**（人工判读属发布窗口
纪律）+ backfill 候选行清单打印。

范围（刻意的**不**作为）：
  * 只标休眠，**不**删除任何预算行（D4 的落点恰是「不再删除」）；
  * 不碰 `categories` / `records` / `budget_categories` 的行集（M2 脚本的领地）；
  * 旧形库（未跑 `migrate_to_v1.4.3.py`，`budgets` 无 `scope_mode` 列或无
    `budget_categories` 表）**不猜**休眠行——「宁漏不错标」：漏标者由 D9（编辑保存即
    唤醒）自救，错标者会凭空制造置灰卡片。打印 `[..]` 说明后 backfill 计 0；
  * 与 `migrate_to_v1.4.3boot2_categories.py` 互不依赖、任意顺序均收敛（D11）。

零新增依赖：仅 stdlib + 项目既有 sqlalchemy/aiosqlite；**不 import `app/`**（停服窗口
裸库可执行，不依赖应用包可导入），故 `SCOPE_INCLUDE` 在脚本侧独立定义，与
`app/models/budget.py` 的同名常量由 `tests/test_migration_v143boot2_dormant.py` 的一致性
断言钉住（沿 M2 家族常量的防漂移惯例）。
"""

import asyncio
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 与 `app/models/budget.py` 的 SCOPE_INCLUDE 逐字一致（一致性断言见 M3 迁移用例 §3.4）
SCOPE_INCLUDE = "include"

# 新增列定义：SQLite 的「带常量默认值单语句加列」不重写行、原子且安全，
# 且 NOT NULL + DEFAULT 0 使存量行自动落 0（= 非休眠），无需回填默认值。
DORMANT_COLUMN_DDL = "ALTER TABLE budgets ADD COLUMN dormant INTEGER NOT NULL DEFAULT 0"


def _db_url(argv: list[str]) -> str:
    path = argv[1] if len(argv) > 1 else "./money.db"
    return f"sqlite+aiosqlite:///{path}"


async def _table_exists(conn: Any, table: str) -> bool:
    row = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name = :t"),
            {"t": table},
        )
    ).first()
    return row is not None


async def _columns_of(conn: Any, table: str) -> list[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
    return [str(r[1]) for r in rows]


def new_stats() -> dict[str, Any]:
    """统计摘要（`backfilled_dormant` 为任务 1.3 点名输出；其余供发布窗口核对）。"""
    return {
        "column_added": 0,  # 1 = 本次执行补加了 dormant 列
        "backfilled_dormant": 0,  # 本次置 dormant=1 的存量预算条数
        "scanned_budgets": 0,  # budgets 现存行数（no-op 时亦给出，便于核对）
        "skipped_reason": "",  # 非空 = 整体未动作的原因
    }


def is_noop(stats: dict[str, Any]) -> bool:
    return int(stats["column_added"]) == 0 and int(stats["backfilled_dormant"]) == 0


async def _backfill_candidates(conn: Any) -> list[Any]:
    """backfill 判据的唯一真源（只读）：`include` 且无任何 `budget_categories` 关联。

    旧校验保证存量 include 预算必有 ≥1 关联，故理论命中 0 条；真正命中者 = 「删分类
    未级联干净的异常行」/「v1.4.3 阶段 B 产出的『未知分类』行」，标休眠与 D4 一致。
    """
    return list(
        (
            await conn.execute(
                text(
                    "SELECT id, name, month FROM budgets WHERE scope_mode = :inc"
                    " AND NOT EXISTS"
                    " (SELECT 1 FROM budget_categories bc WHERE bc.budget_id = budgets.id)"
                    " ORDER BY id"
                ),
                {"inc": SCOPE_INCLUDE},
            )
        ).fetchall()
    )


async def _precheck(conn: Any) -> None:
    """只读前置检查：完整性摘要 + backfill 候选行清单（不改数据）。"""
    check = (await conn.execute(text("PRAGMA integrity_check"))).first()
    verdict = str(check[0]) if check else "no-result"
    if verdict.lower() != "ok":
        print(f"  [WARN] PRAGMA integrity_check → {verdict}（请先备份并人工判读）")
    else:
        print("  [pre-check] PRAGMA integrity_check → ok")
    rows = await _backfill_candidates(conn)
    print(f"  [pre-check] backfill 候选（include 且零关联）共 {len(rows)} 行：")
    for row in rows:
        print(f"      id={int(row[0])} name={str(row[1])!r} month={str(row[2])!r}")


async def _warn_if_unbackfilled(conn: Any) -> None:
    """列已存在却仍有候选行 → 只提示、不改写（幂等判据优先，见文件头「事务」段）。

    两种成因同形：① 上次执行在「加列已提交、backfill 未提交」之间中断；② 违 D11
    先起了新版服务，窗口期用户新建的「不选 = 全部」预算。二者都**不能**靠再跑一次
    UPDATE 区分（那会把合法动态全部预算错标成休眠），处置一律是前端编辑重新保存
    （D9）——故此处仅打印人工核对清单。
    """
    rows = await _backfill_candidates(conn)
    if rows:
        print(
            f"  [WARN] 列已存在但仍有 {len(rows)} 行「include 且零关联」未标休眠"
            "（上次执行中断 或 违 D11 先启服务）→ 按幂等判据**不自动改写**；"
            "请人工判读：确属被删光者在前端编辑保存一次即可（D9）"
        )
        for row in rows:
            print(f"      id={int(row[0])} name={str(row[1])!r} month={str(row[2])!r}")


async def add_dormant_column(conn: Any) -> dict[str, Any]:
    """探测 → 加列 → backfill；返回统计（缺表/已含列一律整体 no-op）。"""
    stats = new_stats()
    if not await _table_exists(conn, "budgets"):
        stats["skipped_reason"] = "budgets 表不存在"
        print("  [SKIP] budgets 表不存在（新库将由应用自动建表）→ 本次 no-op")
        return stats

    cols = await _columns_of(conn, "budgets")
    total = (await conn.execute(text("SELECT COUNT(*) FROM budgets"))).first()
    stats["scanned_budgets"] = int(total[0]) if total else 0

    if "dormant" in cols:
        stats["skipped_reason"] = "budgets 已含 dormant 列"
        print(
            f"  [SKIP] budgets 已含 dormant 列（存量 {stats['scanned_budgets']} 行）"
            " → 加列与 backfill 一并 no-op"
        )
        if "scope_mode" in cols and await _table_exists(conn, "budget_categories"):
            await _warn_if_unbackfilled(conn)  # 只提示，不改写（幂等判据优先）
        return stats

    # 1) 单语句加列（带默认值，SQLite 不重写行；NOT NULL 存量行自动落 0）
    await conn.execute(text(DORMANT_COLUMN_DDL))
    stats["column_added"] = 1
    print("  [OK] budgets 加列 dormant（NOT NULL DEFAULT 0，单语句安全）")

    # 2) backfill 前置探测：判据依赖 scope_mode 列 + budget_categories 表，
    #    缺任一即处于「未跑 v1.4.3 迁移」的旧形，**宁漏不错标**（见文件头「范围」）
    if "scope_mode" not in cols:
        stats["skipped_reason"] = "budgets 无 scope_mode 列（未跑 v1.4.3 迁移）"
        print("  [..] budgets 无 scope_mode 列 → include 语义尚不存在，跳过 backfill")
        return stats
    if not await _table_exists(conn, "budget_categories"):
        stats["skipped_reason"] = "budget_categories 表不存在（版本混跑）"
        print("  [..] budget_categories 表不存在 → 无「零关联」判据，跳过 backfill")
        return stats

    # 3) backfill：旧校验保证存量 include 预算必有 ≥1 关联，故理论命中 0 条；
    #    真正命中者 = 「删分类未级联干净的异常行」，标休眠与 D4 语义一致
    await _precheck(conn)
    result = await conn.execute(
        text(
            "UPDATE budgets SET dormant = 1 WHERE scope_mode = :inc AND NOT EXISTS"
            " (SELECT 1 FROM budget_categories bc WHERE bc.budget_id = budgets.id)"
        ),
        {"inc": SCOPE_INCLUDE},
    )
    stats["backfilled_dormant"] = int(result.rowcount or 0)
    return stats


def print_stats(stats: dict[str, Any]) -> None:
    if is_noop(stats):
        print(
            f"  [SKIP] budgets 无动作（原因：{stats['skipped_reason'] or '无需变更'}；"
            f"扫描 {stats['scanned_budgets']} 行）→ 本次 no-op"
        )
        return
    print(
        f"  [OK] 加列 {stats['column_added']}"
        f" / backfilled_dormant {stats['backfilled_dormant']}"
        f"（扫描 {stats['scanned_budgets']} 行；include 且零关联者标休眠）"
    )


async def run_migration(db_path: str) -> dict[str, Any]:
    """执行迁移（单事务），返回统计摘要（供测试与发布窗口核对）。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    try:
        async with engine.begin() as conn:  # 失败即整体回滚，可重跑
            stats = await add_dormant_column(conn)
            print_stats(stats)
    finally:
        await engine.dispose()
    return stats


async def migrate(argv: list[str]) -> int:
    print(f"[v1.4.3-boot2 dormant migration] target: {_db_url(argv)}")
    print("  [注意] 必须先于新版后端服务启动执行（D11）；已启动者见文件头处置口径")
    await run_migration(argv[1] if len(argv) > 1 else "./money.db")
    print("[v1.4.3-boot2 dormant migration] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate(sys.argv)))
