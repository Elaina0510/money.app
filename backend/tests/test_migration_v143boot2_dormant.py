"""v1.4.3-boot2 M3 `dormant` 迁移脚本测试（backend/migrate_to_v1.4.3boot2_dormant.py）。

任务 8.6 的四态 + 事务/幂等/常量一致性：
  ① **缺列库** → 加列 + backfill 命中「构造的异常空集行」，其余正常行逐字段不动；
  ② **二次执行** → 整体 no-op（列在即跳过）、数据不变；
  ③ **已含列库** → 直接 no-op（dormant=1 行原样保留；仍有候选行时只 WARN 不改写）；
  ④ **旧形/缺表**（无 `scope_mode` 列、无 `budget_categories` 表、无 `budgets` 表）
     → 加列（或直接跳过）但**宁漏不错标**，backfill 计 0。

手法要点（沿 `test_migration_v143.py` 的项目惯例）：
  * 临时 SQLite **文件**库 + 手写 `budgets` / `budget_categories` DDL——conftest 的
    `create_all` 只会产出「已含 dormant」的新形库，测不到加列路径；
  * 脚本文件名含点号 → 只能 `importlib` 按路径加载；执行统一走
    `asyncio.run(run_migration(path))`（同步用例内跑协程，避免与 pytest-asyncio 抢循环）；
  * **禁止对真实 `backend/money.db` 做任何写操作或迁移**（红线）——只在 `tmp_path` 沙盒跑；
  * 幂等判据一律读 `PRAGMA table_info`（列形），不看索引名。
"""

import asyncio
import importlib.util
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from sqlmodel import SQLModel

from app.models.budget import SCOPE_INCLUDE as APP_SCOPE_INCLUDE
from app.models.budget import Budget

# ── 被测脚本（文件名含点号，按路径加载）────────────────────────────────────
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "migrate_to_v1.4.3boot2_dormant.py"


def _load_migration_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "migrate_to_v1_4_3_boot2_dormant", _SCRIPT_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dormant = _load_migration_module()

# ── 现场形态 DDL ──────────────────────────────────────────────────────────
# v1.4.3 M12 之后、boot2 M3 之前：budgets 有 name/scope_mode、**无 dormant** 列
_BUDGETS_DDL = """
CREATE TABLE budgets (
    id INTEGER NOT NULL,
    user_id INTEGER,
    name VARCHAR NOT NULL,
    month VARCHAR NOT NULL,
    amount REAL NOT NULL,
    scope_mode VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    PRIMARY KEY (id)
)
"""

# 已执行过本脚本的库（③ 态）：列在、且已有一行 dormant=1
_BUDGETS_DDL_WITH_DORMANT = _BUDGETS_DDL.replace(
    "    scope_mode VARCHAR NOT NULL,",
    "    scope_mode VARCHAR NOT NULL,\n    dormant INTEGER NOT NULL DEFAULT 0,",
)

# 未跑 v1.4.3 迁移的极旧库：预算挂单列 category_id，**无** scope_mode
_BUDGETS_DDL_PRE_V143 = """
CREATE TABLE budgets (
    id INTEGER NOT NULL,
    user_id INTEGER,
    category_id INTEGER,
    month VARCHAR NOT NULL,
    amount REAL NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    PRIMARY KEY (id)
)
"""

_BUDGET_CATEGORIES_DDL = """
CREATE TABLE budget_categories (
    id INTEGER NOT NULL,
    budget_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT idx_budgetcat_budget_category UNIQUE (budget_id, category_id)
)
"""

# (id, name, month, amount, scope_mode)——刻意把「异常行」与三类正常行混排
_ROWS = [
    (1, "餐饮月预算", "2026-06", 800.0, "include"),  # include + 有 links → 不动
    (2, "未知分类", "2026-06", 500.0, "include"),  # include + **零 links** → 命中
    (3, "全支出", "2026-06", 3000.0, "exclude"),  # exclude + 零 links → 不标
    (4, "除餐饮外", "2026-06", 1000.0, "exclude"),  # exclude + 有 links → 不标
    (5, "多关联", "2026-05", 200.0, "include"),  # include + 多 links → 不动
]
_LINKS = [(1, 10), (4, 10), (4, 11), (5, 10), (5, 12)]  # (budget_id, category_id)


def _execute(path: Path, statements: list[str], params: list[tuple] = ()) -> None:
    conn = sqlite3.connect(path)
    try:
        for sql in statements:
            conn.execute(sql)
        for row in params:
            conn.execute(*row)
        conn.commit()
    finally:
        conn.close()


def _query(path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _columns(path: Path, table: str) -> list[str]:
    return [str(r[1]) for r in _query(path, f"PRAGMA table_info({table})")]


def _dormant_map(path: Path) -> dict[int, int]:
    return {int(r[0]): int(r[1]) for r in _query(path, "SELECT id, dormant FROM budgets")}


def _snapshot(path: Path) -> list[tuple[Any, ...]]:
    """除 dormant 外的全列快照（「其它数据原样不损」的比对基准）。"""
    return _query(
        path,
        "SELECT id, user_id, name, month, amount, scope_mode, created_at, updated_at"
        " FROM budgets ORDER BY id",
    )


def _prepare(
    tmp_path: Path,
    *,
    budgets_ddl: str = _BUDGETS_DDL,
    with_links_table: bool = True,
    with_rows: bool = True,
    name: str = "site.db",
) -> Path:
    """造「现场形态」文件库：默认 = M12 列形（无 dormant）+ 五行预算 + 关联行。"""
    db = tmp_path / name
    statements = [budgets_ddl]
    if with_links_table:
        statements.append(_BUDGET_CATEGORIES_DDL)
    if with_rows:
        for bid, bname, month, amount, scope_mode in _ROWS:
            statements.append(
                "INSERT INTO budgets (id, user_id, name, month, amount, scope_mode,"
                " created_at, updated_at) VALUES"
                f" ({bid}, 1, '{bname}', '{month}', {amount}, '{scope_mode}',"
                " '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        if with_links_table:
            for budget_id, category_id in _LINKS:
                statements.append(
                    "INSERT INTO budget_categories (budget_id, category_id) VALUES"
                    f" ({budget_id}, {category_id})"
                )
    _execute(db, statements)
    return db


def _run(db: Path) -> dict[str, Any]:
    return asyncio.run(dormant.run_migration(str(db)))


# ===========================================================================
# ① 缺列库：加列 + backfill 命中构造的异常行、正常行不动
# ===========================================================================


def test_missing_column_adds_dormant_and_backfills_anomaly(tmp_path):
    db = _prepare(tmp_path)
    assert "dormant" not in _columns(db, "budgets"), "前置：现场库确无该列"
    before = _snapshot(db)

    stats = _run(db)

    assert stats["column_added"] == 1
    assert stats["backfilled_dormant"] == 1, "仅 id=2（include 且零关联）命中（任务 1.3）"
    assert stats["scanned_budgets"] == len(_ROWS)
    assert stats["skipped_reason"] == ""
    assert "dormant" in _columns(db, "budgets")
    assert _dormant_map(db) == {1: 0, 2: 1, 3: 0, 4: 0, 5: 0}, (
        "include 有 links / exclude 两种形态**都不标**"
    )
    assert _snapshot(db) == before, "只加列 + 标休眠，其余列逐字段不损"
    links = _query(db, "SELECT budget_id, category_id FROM budget_categories ORDER BY id")
    assert links == [(b, c) for b, c in _LINKS], "不碰关联表（M2 领地）"


def test_added_column_is_not_null_with_zero_default(tmp_path):
    """加列语义核验：`NOT NULL DEFAULT 0` ——新行默认 0（非休眠），NULL 被拒。"""
    db = _prepare(tmp_path)
    _run(db)
    _execute(
        db,
        [
            "INSERT INTO budgets (id, user_id, name, month, amount, scope_mode,"
            " created_at, updated_at) VALUES (9, 1, '新行', '2026-07', 10.0, 'include',"
            " '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        ],
    )
    assert _dormant_map(db)[9] == 0, "DEFAULT 0 → 新建即非休眠（D9：休眠只由级联置 1）"

    conn = sqlite3.connect(db)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO budgets (id, name, month, amount, scope_mode, dormant)"
                " VALUES (10, '空列', '2026-07', 1.0, 'include', NULL)"
            )
    finally:
        conn.close()


# ===========================================================================
# ② 二次执行 no-op
# ===========================================================================


def test_second_run_is_noop(tmp_path):
    db = _prepare(tmp_path)
    first = _run(db)
    snapshot_after_first = _snapshot(db)
    dormant_after_first = _dormant_map(db)
    assert not dormant.is_noop(first)

    second = _run(db)

    assert dormant.is_noop(second), f"二次执行必须归 0：{second}"
    assert second["column_added"] == 0 and second["backfilled_dormant"] == 0
    assert second["skipped_reason"] == "budgets 已含 dormant 列"
    assert second["scanned_budgets"] == len(_ROWS)
    assert _dormant_map(db) == dormant_after_first
    assert _snapshot(db) == snapshot_after_first


# ===========================================================================
# ③ 已含列库直接 no-op（含「列在但未 backfill」的良性漏标）
# ===========================================================================


def test_library_already_having_column_is_direct_noop(tmp_path):
    db = _prepare(tmp_path, budgets_ddl=_BUDGETS_DDL_WITH_DORMANT)
    _execute(
        db,
        [
            "UPDATE budgets SET dormant = 1 WHERE id = 4",  # 人工置的休眠行
        ],
    )
    before_map = {1: 0, 2: 0, 3: 0, 4: 1, 5: 0}
    assert _dormant_map(db) == before_map

    stats = _run(db)

    assert dormant.is_noop(stats)
    assert stats["column_added"] == 0 and stats["backfilled_dormant"] == 0
    # 列在 → **整体** no-op：候选行 id=2（include 零 links、dormant=0）不被改写
    # （幂等判据优先；错标会凭空造置灰卡，违「宁漏不错标」）
    assert _dormant_map(db) == before_map


def test_unbackfilled_column_state_warns_but_never_rewrites(tmp_path, monkeypatch):
    """④（附加）中途失败实测：DDL 即时提交、DML 可回滚 → 终态「列在、休眠未标」；

    再跑一次**只 WARN 不改写**（脚本头「事务与失败收敛」段登记的驱动事实）。
    """

    async def boom(conn: Any) -> None:
        raise RuntimeError("注入：加列之后、backfill 之前中断")

    db = _prepare(tmp_path)
    monkeypatch.setattr(dormant, "_precheck", boom)
    with pytest.raises(RuntimeError):
        _run(db)

    assert "dormant" in _columns(db, "budgets"), "SQLite DDL 由驱动即时提交（实测）"
    assert _dormant_map(db) == {r[0]: 0 for r in _ROWS}, "backfill 的 UPDATE 已回滚"

    stats = _run(db)  # 重跑：整体 no-op，不漏标成错标
    assert dormant.is_noop(stats)
    assert _dormant_map(db) == {r[0]: 0 for r in _ROWS}, "只提示、不改写（良性漏标）"


# ===========================================================================
# ④ 旧形 / 缺表：宁漏不错标
# ===========================================================================


def test_pre_v143_shape_adds_column_but_skips_backfill(tmp_path):
    """无 `scope_mode` 列（未跑 v1.4.3 迁移）→ include 语义尚不存在，跳过 backfill。"""
    db = _prepare(tmp_path, budgets_ddl=_BUDGETS_DDL_PRE_V143, with_rows=False)
    _execute(
        db,
        [
            "INSERT INTO budgets (id, user_id, category_id, month, amount, created_at,"
            " updated_at) VALUES (1, 1, 10, '2026-06', 500.0,"
            " '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        ],
    )

    stats = _run(db)

    assert stats["column_added"] == 1
    assert stats["backfilled_dormant"] == 0
    assert "无 scope_mode" in stats["skipped_reason"]
    assert _query(db, "SELECT dormant FROM budgets") == [(0,)]


def test_missing_links_table_skips_backfill(tmp_path):
    """有 scope_mode 但**无 budget_categories 表**（版本混跑）→ 判据不可用，跳过。"""
    db = _prepare(tmp_path, with_links_table=False)
    stats = _run(db)
    assert stats["column_added"] == 1
    assert stats["backfilled_dormant"] == 0, "无「零关联」判据时宁漏不错标"
    assert "budget_categories" in stats["skipped_reason"]
    assert _dormant_map(db) == {r[0]: 0 for r in _ROWS}


def test_missing_budgets_table_is_noop(tmp_path):
    db = tmp_path / "empty.db"
    _execute(db, ["CREATE TABLE users (id INTEGER PRIMARY KEY)"])
    stats = _run(db)
    assert dormant.is_noop(stats)
    assert stats["skipped_reason"] == "budgets 表不存在"
    assert _columns(db, "users") == ["id"]


# ===========================================================================
# 常量一致性（脚本不 import app/ → 用断言钉住漂移）+ CLI 入口
# ===========================================================================


def test_script_constants_match_model_and_ddl(tmp_path):
    assert dormant.SCOPE_INCLUDE == APP_SCOPE_INCLUDE, "backfill 判据与模型常量同值"
    col = Budget.__table__.columns["dormant"]
    assert col is not None and col.nullable is False
    assert "dormant" in _columns_via_metadata()
    ddl = dormant.DORMANT_COLUMN_DDL
    assert ddl.startswith("ALTER TABLE budgets ADD COLUMN dormant ")
    assert ddl.endswith("NOT NULL DEFAULT 0"), "与模型的 NOT NULL + server_default '0' 同形"


def _columns_via_metadata() -> list[str]:
    return [c.name for c in SQLModel.metadata.tables["budgets"].columns]


def test_cli_entrypoint_and_default_db_path(tmp_path, capsys):
    """CLI：`python migrate_..._dormant.py <db>` 走同一实现并打印统计（发布窗口手跑口径）。"""
    db = _prepare(tmp_path, name="cli.db")
    code = asyncio.run(dormant.migrate(["migrate_to_v1.4.3boot2_dormant.py", str(db)]))
    assert code == 0
    out = capsys.readouterr().out
    assert "必须先于新版后端服务启动执行" in out, "D11 执行窗口约定在运行时也提醒"
    assert "backfilled_dormant 1" in out, "任务 1.3 点名的统计输出"
    assert _dormant_map(db) == {1: 0, 2: 1, 3: 0, 4: 0, 5: 0}
