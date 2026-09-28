"""Migration script: v1.4.4 M2 —— `categories` 补 `source` 出身列 + 存量回填.

对应需求 REQ-003（出身徽章）/ REQ-004（自建归位）：

M2 给分类引入「出身」这一独立维度：`source = 1` 表示系统预设**或其 Copy-on-Write 用户副本**，
`source = 0` 表示用户自建。它必须与既有的 `is_preset` 分列存在（§0.6 红线：`is_preset` 语义
一字不动，仍只描述「全局预设行」），因为徽章与「不可单删」要落在**派生副本**上，而副本的
`is_preset` 恒为 0。故 `categories` 新增 `source INTEGER NOT NULL DEFAULT 0`。

设计依据：`doc/detailed-designv1.4.4.md` §三（§3.1 列定义、§3.2 预设 SSOT、任务 3.1–3.6）。
**运行期代码**（`app/`）由 M2 后端半区另行交付，本文件只负责存量库收敛。

⚠ 执行窗口硬约定（沿 v1.4.3-boot2 D11 口径，**发布窗口操作序的一步**）：
    1. 备份现场库文件（项目红线，操作纪律，本脚本**不做备份**）；
    2. 停服 → **本脚本必须在替换/启动新版后端之前执行完毕**；
    3. 原因：新版后端在启动期即会按 `source` 读取分类（徽章口径、恢复默认的分堆判据都依赖它）。
       先起服务后跑脚本，窗口期内的恢复默认操作会把「本应是预设派生副本」的行当自建行删除
       （账单被改挂「其他」而非改指全局行），这与 REQ-005「不迁移、不乱动」相反且不可逆；
    4. 违序处置：与 dormant 脚本不同，本脚本的三条 UPDATE 判据**只依赖行自身的历史字段**
       （`is_preset` / `user_id` / `name`），不受窗口期新数据影响，故**重跑即收敛**；
       但违序窗口内已执行的恢复默认造成的账单改挂无法回溯（登记于发布备忘，属人工判读项）。

用法：
    cd backend
    python migrate_to_v1.4.4_source.py            # 默认 ./money.db
    python migrate_to_v1.4.4_source.py /path/db   # 指定库路径

幂等（判据即设计任务 3.1）：
  * `PRAGMA table_info(categories)` **已含 `source` 列 → 整体 no-op**（加列与两条回填 UPDATE
    一并跳过，二次执行统计归 0，打印 `[SKIP]`）；
  * 列由本次新增时，两条 UPDATE 各自只把 0 改 1，本身亦幂等（同判据重跑命中 0 行）。

事务与失败收敛：全程 `engine.begin()`，DML 可回滚，而 SQLite 的 **DDL 由驱动即时提交**
（沿 dormant 脚本副本实测的驱动事实）。故中途失败的终态 = 「`source` 列已加、回填未完成」，
二次执行按幂等判据整体 no-op → 该形态由脚本的**只读 WARN**暴露（列出仍未归位的行数与
可人工执行的 UPDATE 语句），不自动改写（幂等判据优先，避免绕过发布窗口的判读纪律）。

回填范围与已知边界（刻意不修，登记于此）：
  * `is_preset = 1` 的全局预设行 → `source = 1`；
  * `is_preset = 0 AND user_id IS NOT NULL AND name ∈ 14 个预设名` 的 CoW 副本 → `source = 1`；
  * **已知边界**：v1.4.2 之前「同名删除重建」历史遗留的**自建行**（用户删掉预设后重建同名分类）
    与副本在数据上无法区分，会被一并回填为 `source=1`（表现为「有徽章且不可单删」）。
    处置不需要脚本：用户删除后重建同名即归位 `source=0`，与 REQ-004 语义自洽（设计 §3.1）；
  * 匿名自建（`user_id IS NULL AND is_preset = 0`）恒留 `source=0`，不参与回填；
  * 不碰 `records` / `budgets` / `budget_categories` / `tags` 的行集，也不碰 `is_preset` 列值。

零新增依赖：仅 stdlib + 项目既有 sqlalchemy/aiosqlite；**不 import `app/`**（停服窗口
裸库可执行，不依赖应用包可导入），故 14 个预设名在脚本内**独立硬编码**，与
`app/presets.py` 的 `PRESET_SPECS` 由 `tests/test_category_source.py`（任务 8.1.8）的一致性
断言钉住（沿 boot2 脚本家族常量的防漂移惯例）。
"""

import asyncio
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 与 `app/presets.py::PRESET_SPECS` 的 name 列逐字同序（一致性断言见 M2 用例 8.1.8）
PRESET_NAMES: tuple[str, ...] = (
    "餐饮",
    "出行",
    "购物",
    "娱乐",
    "医疗",
    "居住",
    "通讯",
    "工作",
    "旅行",
    "账单与费用",
    "工资",
    "红包",
    "理财",
    "其他",
)

# 新增列定义：SQLite 的「带常量默认值单语句加列」不重写行、原子且安全，
# 且 NOT NULL + DEFAULT 0 使存量行自动落 0（= 用户自建），回填只标需要改的那部分。
SOURCE_COLUMN_DDL = "ALTER TABLE categories ADD COLUMN source INTEGER NOT NULL DEFAULT 0"

# 回填判据 1：全局预设行（与 models/category.py 的 is_preset 语义一致）
BACKFILL_PRESET_DDL = "UPDATE categories SET source = 1 WHERE is_preset = 1"


def _db_url(argv: list[str]) -> str:
    path = argv[1] if len(argv) > 1 else "./money.db"
    return f"sqlite+aiosqlite:///{path}"


def _name_params() -> dict[str, str]:
    """14 个预设名的绑定参数（不拼字符串，杜绝注入与转义问题）。"""
    return {f"preset_name_{i}": name for i, name in enumerate(PRESET_NAMES)}


def _cow_predicate() -> str:
    """回填判据 2 的 WHERE 片段（唯一真源：UPDATE 与两条只读统计共用，避免判据漂移）。"""
    placeholders = ", ".join(f":preset_name_{i}" for i in range(len(PRESET_NAMES)))
    return (
        "is_preset = 0 AND user_id IS NOT NULL"  # 用户副本（is_preset 语义未动，D3）
        f" AND name IN ({placeholders})"  # 命中 14 个预设名
    )


def _cow_backfill_stmt() -> Any:
    """回填判据 2：预设派生的用户副本（`is_preset=0` 且归属某用户且命中预设名）。"""
    return text(f"UPDATE categories SET source = 1 WHERE {_cow_predicate()}")


def _cow_count_stmt(*, only_pending: bool) -> Any:
    """副本判据的只读统计。

    `only_pending=False`：**加列前**的候选行数（此时候选列还不存在，语句不得引用 `source`）；
    `only_pending=True`：列已在场时「应归位却仍为 0」的遗漏探测（中断终态判读用）。
    """
    extra = " AND source = 0" if only_pending else ""
    return text(f"SELECT COUNT(*) FROM categories WHERE {_cow_predicate()}{extra}")


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
    """统计摘要（`backfilled_*` 两键为任务 3.2 点名输出；其余供发布窗口核对）。"""
    return {
        "column_added": 0,  # 1 = 本次执行补加了 source 列
        "backfilled_presets": 0,  # is_preset=1 → source=1 的条数
        "backfilled_cow_copies": 0,  # 预设派生副本 → source=1 的条数
        "scanned_categories": 0,  # categories 现存行数（no-op 时亦给出，便于核对）
        "skipped_reason": "",  # 非空 = 整体未动作的原因
    }


def is_noop(stats: dict[str, Any]) -> bool:
    return (
        int(stats["column_added"]) == 0
        and int(stats["backfilled_presets"]) == 0
        and int(stats["backfilled_cow_copies"]) == 0
    )


async def _precheck(conn: Any) -> None:
    """只读前置检查：完整性摘要 + 回填前的行数分布（不改数据）。"""
    check = (await conn.execute(text("PRAGMA integrity_check"))).first()
    verdict = str(check[0]) if check else "no-result"
    if verdict.lower() != "ok":
        print(f"  [WARN] PRAGMA integrity_check → {verdict}（请先备份并人工判读）")
    else:
        print("  [pre-check] PRAGMA integrity_check → ok")
    presets = await conn.execute(text("SELECT COUNT(*) FROM categories WHERE is_preset = 1"))
    copies = await conn.execute(_cow_count_stmt(only_pending=False), _name_params())
    print(
        f"  [pre-check] 待回填：全局预设行 {int((presets.first() or [0])[0])} 行"
        f" / 预设派生副本 {int((copies.first() or [0])[0])} 行"
        "（其余自建行保持 source=0）"
    )


async def _warn_if_unbackfilled(conn: Any) -> None:
    """source 列已在场却仍有应归位行 → 只提示不改写（幂等判据优先）。

    成因固定为「上次执行在『加列已提交』与『回填已提交』之间中断」。脚本不绕过幂等判据
    自动补写（那会让发布窗口的「先判读再动作」纪律失效），改为打印人工可执行的语句。
    """
    pending_stmt = text("SELECT COUNT(*) FROM categories WHERE is_preset = 1 AND source = 0")
    presets = await conn.execute(pending_stmt)
    pending_preset = int((presets.first() or [0])[0])
    copies = await conn.execute(_cow_count_stmt(only_pending=True), _name_params())
    pending_copy = int((copies.first() or [0])[0])
    if not (pending_preset or pending_copy):
        print("  [SKIP] categories 已含 source 列且回填无遗漏 → 本次 no-op")
        return
    print(
        f"  [WARN] source 列已存在但回填未收敛（预设行 {pending_preset}"
        f" / 副本 {pending_copy} 仍为 source=0），疑为上次执行中断。"
        "按幂等判据**不自动改写**，请人工判读后执行："
    )
    print(f"      {BACKFILL_PRESET_DDL}")
    print(
        "      UPDATE categories SET source = 1 WHERE is_preset = 0 AND user_id IS NOT NULL"
        f" AND name IN ({', '.join(repr(n) for n in PRESET_NAMES)})"
    )


async def _backfill(conn: Any) -> tuple[int, int]:
    """两条回填 UPDATE（仅由 `add_source_column` 在加列之后调用）。

    返回 `(全局预设行数, 命中 14 名的用户副本行数)`。独立成函数是为了让「加列已提交、
    回填被回滚」这一中断终态可被测试注入（任务 8.1.8），并让判据只写在一处。
    """
    presets = await conn.execute(text(BACKFILL_PRESET_DDL))
    copies = await conn.execute(_cow_backfill_stmt(), _name_params())
    return int(presets.rowcount or 0), int(copies.rowcount or 0)


async def add_source_column(conn: Any) -> dict[str, Any]:
    """探测 → 加列 → 两条回填 UPDATE；返回统计（缺表/已含列一律整体 no-op）。"""
    stats = new_stats()
    if not await _table_exists(conn, "categories"):
        stats["skipped_reason"] = "categories 表不存在"
        print("  [SKIP] categories 表不存在（新库将由应用自动建表）→ 本次 no-op")
        return stats

    cols = await _columns_of(conn, "categories")
    total = (await conn.execute(text("SELECT COUNT(*) FROM categories"))).first()
    stats["scanned_categories"] = int(total[0]) if total else 0

    if "source" in cols:
        stats["skipped_reason"] = "categories 已含 source 列"
        print(
            f"  [SKIP] categories 已含 source 列（存量 {stats['scanned_categories']} 行）"
            " → 加列与回填一并 no-op"
        )
        await _warn_if_unbackfilled(conn)  # 只提示，不改写（幂等判据优先）
        return stats

    await _precheck(conn)

    # 1) 单语句加列（带默认值，SQLite 不重写行；NOT NULL 存量行自动落 0）
    await conn.execute(text(SOURCE_COLUMN_DDL))
    stats["column_added"] = 1
    print("  [OK] categories 加列 source（NOT NULL DEFAULT 0，单语句安全）")

    # 2) 两条回填 UPDATE（独立函数 = 测试的失败注入点，用以验证「加列已提交、
    #    回填被回滚」的中断终态；DML 在 engine.begin() 内可整体回滚）
    presets_count, copies_count = await _backfill(conn)
    stats["backfilled_presets"] = presets_count
    stats["backfilled_cow_copies"] = copies_count
    print(f"  [OK] is_preset=1 的全局预设行回填 source=1：{presets_count} 行")
    print(
        f"  [OK] 命中 14 个预设名的用户副本回填 source=1：{copies_count} 行"
        "（同名自建行数据上不可区分，一并回填 = 已知边界，见文件头）"
    )
    return stats


def print_stats(stats: dict[str, Any]) -> None:
    if is_noop(stats):
        print(
            f"  [SKIP] categories 无动作（原因：{stats['skipped_reason'] or '无需变更'}；"
            f"扫描 {stats['scanned_categories']} 行）→ 本次 no-op"
        )
        return
    print(
        f"  [OK] 加列 {stats['column_added']}"
        f" / 回填预设 {stats['backfilled_presets']}"
        f" / 回填副本 {stats['backfilled_cow_copies']}"
        f"（扫描 {stats['scanned_categories']} 行；其余保持 source=0 自建出身）"
    )


async def run_migration(db_path: str) -> dict[str, Any]:
    """执行迁移（单事务），返回统计摘要（供测试与发布窗口核对）。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    try:
        async with engine.begin() as conn:  # 失败即整体回滚，可重跑
            stats = await add_source_column(conn)
            print_stats(stats)
    finally:
        await engine.dispose()
    return stats


async def migrate(argv: list[str]) -> int:
    print(f"[v1.4.4 source migration] target: {_db_url(argv)}")
    print("  [注意] 必须先于新版后端服务启动执行；已启动者见文件头处置口径")
    await run_migration(argv[1] if len(argv) > 1 else "./money.db")
    print("[v1.4.4 source migration] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate(sys.argv)))
