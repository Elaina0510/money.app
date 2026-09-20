"""v1.4.3 迁移脚本测试（backend/migrate_to_v1.4.3.py）。

M8 交付**阶段 A（分类合并）**断言 9.3 ①–⑦；M12 在本文件续写**阶段 B（预算重建）**断言
（任务 11.3：1:1 转换 / 被合并分类引用重定向 / 「未知分类」只读态 / 二次 SKIP / 单事务回滚）。

两阶段归一个脚本后的断言分工（D1「分类在前、预算在后」）：
  * ``test_phase_a_merges_and_rewrites`` 跑的是**整脚本**，故其 ⑦ 段核对 A→B 串联结果
    （旧预算行 1:1 转换、name 取保留分类**当前**名、month/amount/id/user_id 原样）；
  * 「阶段 A 单独执行时 budgets 表逐字段原样不损」（M8 挂点契约）改由
    ``test_phase_a_unit_leaves_budgets_untouched`` 直接调阶段 A 函数锁死——
    整脚本里该不变量已不成立（阶段 B 就要重建它），故必须显式拆出而非删断言；
  * 阶段 B 自有形态（loser 重定向、悬挂分类、无 user_id 的开发库旧形、回滚）各一例。

手法要点（设计 §8.4 / prompt §7.2 / progress.md 审查记录 ④）：
  * 临时 SQLite 文件库 + **手写旧形 CREATE TABLE**——conftest 的 `create_all` 会直接
    产出新形库，且 `conftest.PRESET_CATEGORIES` 是**过期 7 条预设副本**（9.3a 陷阱），
    故本文件一律不用 conftest fixture，预设真源改 import `app.main.PRESET_CATEGORIES`；
  * 旧形覆盖两代：`UNIQUE (name, type)`（v1.2 前，无 user_id 列）与
    `UNIQUE (name, type, user_id)`（v1.4 起，与真实 money.db 现场一致）；
    budgets 另覆盖开发库形制 `UNIQUE (category_id, month)` 无 user_id（任务 10.6）；
  * 幂等判据一律读 `sqlite_master` 建表文本（`PRAGMA index_list` 判名是错的——
    表级约束的支撑索引恒为 `sqlite_autoindex_*`）；
  * **禁止对真实 money.db 执行任何写操作或迁移**（红线 9）——只在 tmp_path 沙盒跑。
"""

import asyncio
import importlib.util
import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

# ── 被测脚本（文件名含点号，只能按路径加载；单例加载以便回滚用例打桩）──────
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "migrate_to_v1.4.3.py"


def _load_migration_module() -> Any:
    spec = importlib.util.spec_from_file_location("migrate_to_v1_4_3", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration_module()

# ── v1.4.2 现场预设快照（15 条双套；真源已随 M8 换为 14 条单套，故此处手写）──
LEGACY_PRESETS: list[tuple[str, str, str, int]] = [
    # (name, type, icon, sort_order)
    ("餐饮", "expense", "mdi-food", 1),
    ("出行", "expense", "mdi-bus", 2),
    ("购物", "expense", "mdi-cart", 3),
    ("娱乐", "expense", "mdi-gamepad", 4),
    ("医疗", "expense", "mdi-hospital-box", 5),
    ("居住", "expense", "mdi-home", 6),
    ("通讯", "expense", "mdi-cellphone", 7),
    ("工作", "expense", "mdi-briefcase", 8),
    ("旅行", "expense", "mdi-bag-suitcase", 9),
    ("账单与费用", "expense", "mdi-receipt-text", 10),
    ("其他支出", "expense", "mdi-cash-minus", 99),
    ("工资", "income", "mdi-wallet", 1),
    ("红包", "income", "mdi-gift", 2),
    ("理财", "income", "mdi-finance", 3),
    ("其他收入", "income", "mdi-cash-plus", 99),
]

# 现场漂移（真实 money.db 实测）：预设行的 icon 可能被早期版本写成别的值
# （开发库「账单与费用」现为 mdi-cash），迁移须按 14 条单套清单纠偏——
# 故刻意在旧形快照上注入漂移，否则「预设 icon 校准」断言会空转。
LEGACY_PRESET_DRIFT: dict[str, str] = {"账单与费用": "mdi-cash"}

# 旧形 A：v1.2 前——无 user_id 列，表级 UNIQUE (name, type)
_CATEGORIES_DDL_ANCIENT = """
CREATE TABLE categories (
    id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    icon VARCHAR NOT NULL,
    sort_order INTEGER NOT NULL,
    is_preset INTEGER NOT NULL,
    created_at VARCHAR NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT idx_categories_name_type UNIQUE (name, type)
)
"""

# 旧形 B：v1.4 起——表级 UNIQUE (name, type, user_id)（真实 money.db 现场形制）
_CATEGORIES_DDL_V142 = """
CREATE TABLE categories (
    id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    icon VARCHAR NOT NULL,
    sort_order INTEGER NOT NULL,
    is_preset INTEGER NOT NULL,
    created_at VARCHAR NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (id),
    CONSTRAINT idx_categories_name_type_user UNIQUE (name, type, user_id)
)
"""

# 新形（已迁移库）：表级 UNIQUE (name, user_id)
_CATEGORIES_DDL_NEW = """
CREATE TABLE categories (
    id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    icon VARCHAR NOT NULL,
    sort_order INTEGER NOT NULL,
    is_preset INTEGER NOT NULL,
    created_at VARCHAR NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (id),
    CONSTRAINT idx_categories_name_user UNIQUE (name, user_id)
)
"""

# 其余表按 v1.4.2 现场形制建表（tags/records/quick_templates/budgets 引用 categories）
_OTHER_TABLES_DDL = """
CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
);
CREATE TABLE tags (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at VARCHAR NOT NULL,
    deleted_at TEXT
);
CREATE TABLE records (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    type VARCHAR NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,
    consume_time VARCHAR NOT NULL,
    note VARCHAR,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
);
CREATE TABLE quick_templates (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    type VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    created_at VARCHAR NOT NULL
);
CREATE TABLE budgets (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    month VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
);
CREATE TABLE operation_history (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER,
    operation_type VARCHAR NOT NULL,
    table_name VARCHAR NOT NULL,
    record_id INTEGER,
    snapshot_data TEXT,
    created_at VARCHAR NOT NULL
);
"""


def _script(*ddls: str) -> str:
    """串多条建表语句（categories 常量末尾无分号，直接拼接会语法错）。"""
    return ";\n".join(d.strip().rstrip(";") for d in ddls if d.strip()) + ";"


def _create_legacy_db(db_path: Path, shape: str) -> sqlite3.Connection:
    """手写旧形建表（禁依赖 conftest create_all 产出的新形库）。"""
    ddl = {"ancient": _CATEGORIES_DDL_ANCIENT, "v142": _CATEGORIES_DDL_V142}[shape]
    conn = sqlite3.connect(db_path)
    conn.executescript(_script(ddl, _OTHER_TABLES_DDL))
    return conn


def _insert_category(
    conn: sqlite3.Connection,
    cat_id: int,
    name: str,
    cat_type: str,
    icon: str,
    sort_order: int,
    is_preset: int,
    user_id: int | None,
    with_user_column: bool,
) -> None:
    if with_user_column:
        conn.execute(
            "INSERT INTO categories (id, name, type, icon, sort_order, is_preset, created_at,"
            " user_id) VALUES (?, ?, ?, ?, ?, ?, '2026-01-01 00:00:00', ?)",
            (cat_id, name, cat_type, icon, sort_order, is_preset, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO categories (id, name, type, icon, sort_order, is_preset, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, '2026-01-01 00:00:00')",
            (cat_id, name, cat_type, icon, sort_order, is_preset),
        )


def _seed_v142_state(conn: sqlite3.Connection, shape: str) -> dict[str, int]:
    """造 v1.4.2 态数据：15 预设 + 用户 A 双套同名「餐饮」+ 仅收入「报销」
    + 各自账单 + 「其他收入」CoW 副本 + 引用 loser 分类的 tag/模板。

    `ancient` 形制无 user_id 列（v1.2 前单用户时代），故只造预设桶 + 挂在预设上的
    账单/标签/模板；同名合并与引用重定向在预设桶同样成立。
    """
    cur = conn.cursor()
    with_user = shape == "v142"
    cur.execute(
        "INSERT INTO users (id, username, hashed_password, created_at, updated_at)"
        " VALUES (1, 'alice', 'x', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
    )

    ids: dict[str, int] = {}
    next_id = 1
    for name, cat_type, icon, sort_order in LEGACY_PRESETS:
        _insert_category(
            conn, next_id, name, cat_type, icon, sort_order, 1, None, with_user
        )
        ids[f"preset:{name}"] = next_id
        next_id += 1

    owner_pred = " AND user_id IS NULL" if with_user else ""
    for name, stale_icon in LEGACY_PRESET_DRIFT.items():
        cur.execute(
            f"UPDATE categories SET icon = ? WHERE name = ?{owner_pred}",
            (stale_icon, name),
        )

    if with_user:
        # 用户 A：双套同名「餐饮」（expense kept + income loser）
        _insert_category(conn, next_id, "餐饮", "expense", "mdi-food", 20, 0, 1, True)
        ids["a_food_expense"] = next_id
        next_id += 1
        _insert_category(conn, next_id, "餐饮", "income", "mdi-cash-plus", 2, 0, 1, True)
        ids["a_food_income"] = next_id
        next_id += 1
        # 用户 A：仅收入侧「报销」
        _insert_category(conn, next_id, "报销", "income", "mdi-file-document", 5, 0, 1, True)
        ids["a_refund_income"] = next_id
        next_id += 1
        # 用户 A：曾把收入预设 CoW 改名（红包 → 退款）——边界 8.1 的追加段
        _insert_category(conn, next_id, "退款", "income", "mdi-gift", 2, 0, 1, True)
        ids["a_refund_cow"] = next_id
        next_id += 1
        # 用户 A：「其他收入」CoW 副本（桶内仅此一侧的「其他」）
        _insert_category(conn, next_id, "其他收入", "income", "mdi-cash-plus", 99, 0, 1, True)
        ids["a_other_income"] = next_id
        next_id += 1
        loser = ids["a_food_income"]
        kept = ids["a_food_expense"]
    else:
        # 无 user_id 列的一代：以预设桶内的「其他收入」作 loser、「其他支出」作 kept
        loser = ids["preset:其他收入"]
        kept = ids["preset:其他支出"]

    records = [
        (kept, "income", 30.0, "2026-02-11 12:00"),
        (kept, "income", 12.34, "2026-03-02 09:00"),
        (ids["preset:工资"], "income", 1000.0, "2026-02-28 09:00"),
        (ids["preset:餐饮"], "expense", 88.5, "2026-02-05 12:00"),
        (ids["preset:其他支出"], "expense", 5.0, "2026-03-01 09:00"),
    ]
    if with_user:
        records += [
            (ids["a_refund_income"], "income", 500.0, "2026-03-07 09:00"),
            (ids["a_refund_cow"], "income", 66.6, "2026-03-09 09:00"),
            (ids["a_other_income"], "income", 7.7, "2026-02-20 09:00"),
        ]
    for category_id, rec_type, amount, consume_time in records:
        cur.execute(
            "INSERT INTO records (id, user_id, amount, type, category_id, tag_id,"
            " consume_time, created_at, updated_at) VALUES (NULL, 1, ?, ?, ?, NULL, ?,"
            " '2026-01-02 00:00:00', '2026-01-02 00:00:00')",
            (amount, rec_type, category_id, consume_time),
        )
        ids[f"record:{amount}"] = category_id

    # tag + 手动模板挂在 **loser** 上：验证重定向
    cur.execute(
        "INSERT INTO tags (id, user_id, name, category_id, created_at)"
        " VALUES (NULL, 1, '午饭', ?, '2026-01-02 00:00:00')",
        (loser,),
    )
    ids["tag_lunch"] = cur.lastrowid
    cur.execute(
        "INSERT INTO quick_templates (id, user_id, tag_id, category_id, type, amount,"
        " created_at) VALUES (NULL, 1, ?, ?, 'income', 30.0, '2026-01-02 00:00:00')",
        (ids["tag_lunch"], loser),
    )
    ids["qt"] = cur.lastrowid

    # budgets：阶段 A 单元不动它、阶段 B 按 merge_map 1:1 重建（挂在 kept 行上，
    # 使阶段 A 不产生悬挂引用；loser 重定向与「未知分类」另用例专门造形）
    cur.execute(
        "INSERT INTO budgets (id, user_id, category_id, month, amount, created_at,"
        " updated_at) VALUES (NULL, 1, ?, '2026-02', 800.0,"
        " '2026-01-02 00:00:00', '2026-01-02 00:00:00')",
        (kept,),
    )
    ids["budget"] = cur.lastrowid

    # operation_history 快照文本：属历史审计，不追改
    cur.execute(
        "INSERT INTO operation_history (id, user_id, operation_type, table_name, record_id,"
        " snapshot_data, created_at) VALUES (NULL, 1, 'update', 'records', 1, ?,"
        " '2026-01-02 00:00:00')",
        (f'{{"category_id": {loser}}}',),
    )
    ids["loser"] = loser
    ids["kept"] = kept

    conn.commit()
    return ids


def _migrate(db_path: Path) -> int:
    return asyncio.run(migration.migrate(["migrate_to_v1.4.3.py", str(db_path)]))


def _query(db_path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _monthly_totals(db_path: Path) -> list[tuple[Any, ...]]:
    """按月 group by type 的收支合计（逐分不差的比对基准）。"""
    return _query(
        db_path,
        "SELECT substr(consume_time,1,7) AS m, type, ROUND(SUM(amount), 2), COUNT(*)"
        " FROM records GROUP BY m, type ORDER BY m, type",
    )


def _categories_ddl(db_path: Path) -> str:
    return _table_ddl(db_path, "categories")


def _table_ddl(db_path: Path, table: str) -> str:
    """任意表的建表文本（幂等判据/换形核对都读它，不读 PRAGMA index_list）。"""
    rows = _query(
        db_path,
        "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return rows[0][0] if rows else ""


def _budget_rows(db_path: Path, columns: str = "*") -> list[tuple[Any, ...]]:
    return _query(db_path, f"SELECT {columns} FROM budgets ORDER BY id")


def _tables(db_path: Path) -> set[str]:
    return {
        str(r[0])
        for r in _query(db_path, "SELECT name FROM sqlite_master WHERE type='table'")
    }


# ── ①–⑦ 阶段 A 断言（两代旧形各跑一遍）────────────────────────────────────
@pytest.mark.parametrize("shape", ["v142", "ancient"])
def test_phase_a_merges_and_rewrites(tmp_path: Path, shape: str, capsys: Any) -> None:
    db_path = tmp_path / "legacy.db"
    conn = _create_legacy_db(db_path, shape)
    ids = _seed_v142_state(conn, shape)
    conn.close()

    totals_before = _monthly_totals(db_path)
    budgets_before = _query(db_path, "SELECT * FROM budgets ORDER BY id")

    assert _migrate(db_path) == 0
    out = capsys.readouterr().out
    assert "[OK] 合并" in out

    # ── ④ 幂等判据读 sqlite_master 建表文本（禁用 PRAGMA index_list 判名）
    norm = re.sub(r"\s+", " ", _categories_ddl(db_path))
    assert "UNIQUE (name, user_id)" in norm
    assert "(name, type, user_id)" not in norm
    assert "UNIQUE (name, type)" not in norm
    assert "categories_new" not in norm  # 中间表已 RENAME 归位

    # ── ① 无同名重复（按桶）、loser 行删除、records/tags/quick_templates 重定向
    assert _query(
        db_path,
        "SELECT name, user_id, COUNT(*) FROM categories GROUP BY name, user_id"
        " HAVING COUNT(*) > 1",
    ) == []
    assert _query(db_path, "SELECT COUNT(*) FROM categories WHERE id = ?", (ids["loser"],))[0][0] == 0
    kept = ids["kept"]
    for amount in (30.0, 12.34):
        assert _query(
            db_path, "SELECT category_id FROM records WHERE amount = ?", (amount,)
        )[0][0] == kept
    assert _query(
        db_path, "SELECT category_id FROM tags WHERE id = ?", (ids["tag_lunch"],)
    )[0][0] == kept
    assert _query(
        db_path, "SELECT category_id FROM quick_templates WHERE id = ?", (ids["qt"],)
    )[0][0] == kept
    assert _query(db_path, "PRAGMA foreign_key_check") == []
    # operation_history 快照文本属历史审计，不追改
    assert str(ids["loser"]) in _query(
        db_path, "SELECT snapshot_data FROM operation_history WHERE table_name='records'"
    )[0][0]

    # ── ② 「其他」唯一、icon=mdi-cash-minus、置末
    owners = ["user_id IS NULL"] + (["user_id = 1"] if shape == "v142" else [])
    for owner in owners:
        others = _query(
            db_path,
            f"SELECT id, icon, sort_order, (SELECT MAX(sort_order) FROM categories"
            f"  WHERE {owner}) FROM categories WHERE name = '其他' AND {owner}",
        )
        assert len(others) == 1, f"桶 {owner} 的「其他」不唯一"
        assert others[0][1] == "mdi-cash-minus"
        assert others[0][2] == others[0][3]  # 恒末位
    # 「其他」由支出侧行改名而来（图标天然取支出侧）
    assert _query(
        db_path, "SELECT id FROM categories WHERE name = '其他' AND user_id IS NULL"
    )[0][0] == ids["preset:其他支出"]
    assert _query(db_path, "SELECT COUNT(*) FROM categories WHERE name IN ('其他支出','其他收入')")[0][0] == 0

    # ── ③ sort_order 连续 1..n 且顺序 = 支出组 → 仅收入侧行 → 其他
    for owner in owners:
        sorts = [
            r[0]
            for r in _query(
                db_path,
                f"SELECT sort_order FROM categories WHERE {owner} ORDER BY sort_order",
            )
        ]
        assert sorts == list(range(1, len(sorts) + 1)), f"桶 {owner} 存在空洞/重号"
    preset_order = [
        r[0]
        for r in _query(
            db_path,
            "SELECT name FROM categories WHERE user_id IS NULL ORDER BY sort_order",
        )
    ]
    assert preset_order == [
        "餐饮", "出行", "购物", "娱乐", "医疗", "居住", "通讯", "工作", "旅行",
        "账单与费用", "工资", "红包", "理财", "其他",
    ]
    # 预设 icon 纠偏（种子含现场漂移 mdi-cash）+ 旧 99 等空洞消除
    assert _query(
        db_path, "SELECT icon FROM categories WHERE name = '账单与费用' AND user_id IS NULL"
    )[0][0] == "mdi-receipt-text"
    assert _query(
        db_path, "SELECT MAX(sort_order) FROM categories WHERE user_id IS NULL"
    )[0][0] == 14

    if shape == "v142":
        user_order = [
            r[0]
            for r in _query(
                db_path,
                "SELECT name FROM categories WHERE user_id = 1 ORDER BY sort_order",
            )
        ]
        assert user_order == ["餐饮", "退款", "报销", "其他"]

    # ── ⑤ 迁移前后按月 group by type 的收支合计逐分不差
    assert _monthly_totals(db_path) == totals_before

    # ── ⑦ 整脚本 = 阶段 A + 阶段 B（D1「分类在前、预算在后」同事务）：
    #       旧预算行 1:1 转换、name 取保留分类**当前**名、月份/金额/id 原样（任务 9.2）
    legacy_row = budgets_before[0]  # (id, user_id, category_id, month, amount, created_at, updated_at)
    kept_name = _query(db_path, "SELECT name FROM categories WHERE id = ?", (kept,))[0][0]
    new_rows = _budget_rows(
        db_path, "id, user_id, name, month, amount, scope_mode, created_at, updated_at"
    )
    assert len(new_rows) == len(budgets_before), "阶段 B 不得合并或丢行（任务 9.4）"
    assert new_rows[0][0] == legacy_row[0], "id 原样保留"
    assert new_rows[0][1] == legacy_row[1], "user_id 原样"
    assert new_rows[0][2] == kept_name, "name = 保留分类行当前名（可能已被阶段 A 改名）"
    assert new_rows[0][3] == legacy_row[3], "month 原样"
    assert new_rows[0][4] == legacy_row[4], "amount 原样"
    assert new_rows[0][5] == "include", "旧分类预算 → include 单分类命名预算"
    assert (new_rows[0][6], new_rows[0][7]) == (legacy_row[5], legacy_row[6]), "时间戳原样"
    # merge_map 接力：关联行落在保留分类 id 上（阶段 A 的 loser id 已不可见）
    assert _query(
        db_path, "SELECT budget_id, category_id FROM budget_categories ORDER BY budget_id"
    ) == [(legacy_row[0], kept)]
    # budgets 已换形（无 category_id 列）+ 中间表归位（与阶段 A 同法整表重建）
    budgets_norm = re.sub(r"\s+", " ", _table_ddl(db_path, "budgets"))
    assert "category_id" not in budgets_norm
    assert "name VARCHAR NOT NULL" in budgets_norm and "scope_mode VARCHAR NOT NULL" in budgets_norm
    assert "budgets_new" not in budgets_norm
    assert "budget_categories" in _tables(db_path)
    assert "[OK] 转换 1 条预算" in out

    # ── ⑥ 二次运行整体 SKIP（幂等），数据不再变化
    capsys.readouterr()
    cats_before = _query(
        db_path,
        "SELECT id, name, type, icon, sort_order, is_preset, user_id FROM categories ORDER BY id",
    )
    budgets_after_first = _budget_rows(
        db_path, "id, user_id, name, month, amount, scope_mode, created_at, updated_at"
    )
    links_after_first = _query(
        db_path, "SELECT id, budget_id, category_id FROM budget_categories ORDER BY id"
    )
    assert _migrate(db_path) == 0
    again = capsys.readouterr().out
    assert "[SKIP] categories 已是 v1.4.3 形制" in again
    assert "[SKIP] budgets 已是 v1.4.3 形制" in again
    assert _monthly_totals(db_path) == totals_before
    assert _budget_rows(
        db_path, "id, user_id, name, month, amount, scope_mode, created_at, updated_at"
    ) == budgets_after_first
    assert _query(
        db_path, "SELECT id, budget_id, category_id FROM budget_categories ORDER BY id"
    ) == links_after_first
    assert _query(
        db_path,
        "SELECT id, name, type, icon, sort_order, is_preset, user_id FROM categories ORDER BY id",
    ) == cats_before
    assert re.sub(r"\s+", " ", _categories_ddl(db_path)) == norm


def test_preset_triples_match_app_source() -> None:
    """脚本预设清单与 app 真源一致（9.3a：不依赖 conftest 的过期 7 条副本）。"""
    from app.main import PRESET_CATEGORIES

    assert [(p["name"], p["icon"], p["sort_order"]) for p in PRESET_CATEGORIES] == list(
        migration.PRESET_TRIPLES
    )


def test_phase_a_single_transaction_rolls_back_on_failure(tmp_path: Path, capsys: Any) -> None:
    """单事务：阶段 A 中途失败 → 整体回滚，库保持迁移前状态（不残半截重建）。"""
    db_path = tmp_path / "rollback.db"
    conn = _create_legacy_db(db_path, "v142")
    _seed_v142_state(conn, "v142")
    conn.close()

    rows_before = _query(
        db_path, "SELECT id, name, type, icon, sort_order, user_id FROM categories ORDER BY id"
    )
    ddl_before = _categories_ddl(db_path)

    original = migration._renumber_sort

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("injected phase-A failure")

    migration._renumber_sort = _boom  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError, match="injected phase-A failure"):
            _migrate(db_path)
    finally:
        migration._renumber_sort = original  # type: ignore[assignment]
    capsys.readouterr()

    assert _query(
        db_path, "SELECT id, name, type, icon, sort_order, user_id FROM categories ORDER BY id"
    ) == rows_before
    assert _categories_ddl(db_path) == ddl_before
    assert _query(
        db_path, "SELECT COUNT(*) FROM sqlite_master WHERE name='categories_new'"
    )[0][0] == 0


def test_phase_a_skips_new_shape_and_missing_table(tmp_path: Path, capsys: Any) -> None:
    """新形库（建表文本已含 UNIQUE (name, user_id)）与空库均 [SKIP] 且不改数据。"""
    db_path = tmp_path / "already_new.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(_script(_CATEGORIES_DDL_NEW, _OTHER_TABLES_DDL))
    conn.execute(
        "INSERT INTO categories (id, name, type, icon, sort_order, is_preset, created_at,"
        " user_id) VALUES (1, '餐饮', 'expense', 'mdi-food', 1, 1,"
        " '2026-01-01 00:00:00', NULL)"
    )
    conn.commit()
    conn.close()

    assert _migrate(db_path) == 0
    out = capsys.readouterr().out
    assert "[SKIP] categories 已是 v1.4.3 形制" in out
    assert _query(db_path, "SELECT COUNT(*) FROM categories")[0][0] == 1
    # 两阶段判据互相独立：categories 已 SKIP，budgets 仍是旧形（_OTHER_TABLES_DDL）
    # → 阶段 B 照常整表重建（任务 9.1 的判据只属于 budgets 自己）
    assert "[OK] 转换 0 条预算" in out
    budgets_norm = re.sub(r"\s+", " ", _table_ddl(db_path, "budgets"))
    assert "category_id" not in budgets_norm and "name VARCHAR NOT NULL" in budgets_norm
    assert "budget_categories" in _tables(db_path)

    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()
    assert _migrate(empty) == 0
    out = capsys.readouterr().out
    assert "[SKIP] categories 表不存在" in out
    assert "[SKIP] budgets 表不存在" in out
    assert _tables(empty) == set()


# ── 阶段 B：预算重建（M12 任务 11.3）───────────────────────────────────────

# 新形 budgets 的读取列序（多处断言复用，避免逐处拼写漂移）
_NEW_BUDGET_COLS = "id, user_id, name, month, amount, scope_mode, created_at, updated_at"

# 开发库实测的 budgets 旧形（附录 A 第 5 条 / 任务 10.6）：**无 user_id 列** +
# 表级 UNIQUE (category_id, month)，与模型声明不一致——阶段 B 按实际存在的列搬运，
# 不据约束名分支、不假设库形制。
_BUDGETS_DDL_DEVDB = """
CREATE TABLE budgets (
    id INTEGER NOT NULL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    month VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    CONSTRAINT idx_budget_category_month UNIQUE (category_id, month)
)
"""

# v1.4.3 新形 budgets（脚本自己的 DDL 改表名而来）——用于「阶段 B 已跑过」的库形
_BUDGETS_DDL_V143 = migration._BUDGETS_NEW_DDL.replace("budgets_new", "budgets")


def _insert_legacy_budget(
    conn: sqlite3.Connection,
    budget_id: int,
    category_id: int,
    month: str,
    amount: float,
    user_id: int | None = 1,
) -> None:
    """旧形 budgets 造行（显式 id，便于核对「id 原样保留」）。"""
    conn.execute(
        "INSERT INTO budgets (id, user_id, category_id, month, amount, created_at,"
        " updated_at) VALUES (?, ?, ?, ?, ?, '2026-01-02 00:00:00',"
        " '2026-01-02 00:00:00')",
        (budget_id, user_id, category_id, month, amount),
    )


def _migrate_categories_only(db_path: Path) -> dict[int, int]:
    """只跑阶段 A（同一 `engine.begin()` 事务），返回 merge_map。

    用途：锁 M8 挂点契约「阶段 A 单元不碰 budgets」——整脚本里该不变量已不成立
    （阶段 B 本就要重建它），故必须按阶段粒度单独验。
    """

    async def _run() -> dict[int, int]:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        try:
            async with engine.begin() as conn:
                return await migration.migrate_categories_phase_a(conn)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def test_phase_a_unit_leaves_budgets_untouched(tmp_path: Path) -> None:
    """阶段 A 单元：budgets 表逐字段原样不损、不新建关联表，且产出 merge_map。"""
    db_path = tmp_path / "phase_a_only.db"
    conn = _create_legacy_db(db_path, "v142")
    ids = _seed_v142_state(conn, "v142")
    conn.close()

    budgets_before = _query(db_path, "SELECT * FROM budgets ORDER BY id")
    ddl_before = _table_ddl(db_path, "budgets")

    merge_map = _migrate_categories_only(db_path)

    assert _query(db_path, "SELECT * FROM budgets ORDER BY id") == budgets_before
    assert _table_ddl(db_path, "budgets") == ddl_before
    assert "budget_categories" not in _tables(db_path)
    # merge_map 是阶段 B 的唯一接力通道（§8.2 注意事项 2 / 任务 9.2）
    assert merge_map[ids["a_food_income"]] == ids["a_food_expense"]


def test_phase_b_converts_redirects_and_marks_unknown(tmp_path: Path, capsys: Any) -> None:
    """阶段 B 全形制：1:1 转换 + loser 引用重定向 + 悬挂分类只读态 + 同月多条不合并."""
    db_path = tmp_path / "phase_b.db"
    conn = _create_legacy_db(db_path, "v142")
    ids = _seed_v142_state(conn, "v142")  # 已含 1 条挂在 kept 上的旧预算（2026-02/800）
    kept = ids["kept"]
    loser = ids["loser"]
    seed_budget_id = ids["budget"]
    # 挂在 **loser** 上：阶段 A 已删该行，阶段 B 须按 merge_map 重定向到 kept（任务 9.2）
    _insert_legacy_budget(conn, seed_budget_id + 1, loser, "2026-03", 300.0)
    # 与上一条同月：多行独立，**不做任何合并**（任务 9.4）
    _insert_legacy_budget(conn, seed_budget_id + 2, ids["a_refund_income"], "2026-03", 400.0)
    # 引用根本不存在的分类：旧库无外键约束的极端数据 → 只读态「未知分类」（任务 9.3）
    _insert_legacy_budget(conn, seed_budget_id + 3, 4242, "2026-04", 500.0)
    # 挂在「其他收入」CoW 副本上：阶段 A 把它改名为「其他」→ name 须取**当前**名
    _insert_legacy_budget(conn, seed_budget_id + 4, ids["a_other_income"], "2026-05", 600.0)
    conn.commit()
    conn.close()

    assert _migrate(db_path) == 0
    out = capsys.readouterr().out
    assert "[OK] 转换 5 条预算（含 1 条重定向分类引用）" in out  # 任务 9.6 原文
    assert "其中 1 条引用的分类已不存在" in out

    rows = _budget_rows(db_path, _NEW_BUDGET_COLS)
    assert [r[0] for r in rows] == [seed_budget_id + i for i in range(5)], "id 原样、不丢不并"
    by_id = {r[0]: r for r in rows}
    assert by_id[seed_budget_id][2] == "餐饮"          # kept 行当前名
    assert by_id[seed_budget_id + 1][2] == "餐饮"      # loser 重定向后的保留行名
    assert by_id[seed_budget_id + 2][2] == "报销"      # 仅收入侧行同样保留
    assert by_id[seed_budget_id + 3][2] == "未知分类"  # 只读态
    assert by_id[seed_budget_id + 4][2] == "其他"      # 阶段 A 改名后的当前名
    # amount/month/user_id/时间戳原样；scope 恒 include（旧预算无排除语义）
    assert [(r[1], r[3], r[4], r[5]) for r in rows] == [
        (1, "2026-02", 800.0, "include"),
        (1, "2026-03", 300.0, "include"),
        (1, "2026-03", 400.0, "include"),
        (1, "2026-04", 500.0, "include"),
        (1, "2026-05", 600.0, "include"),
    ]
    assert all(r[6] == r[7] == "2026-01-02 00:00:00" for r in rows)

    # 关联表：只读态零关联（spent 恒 0、可删、PUT 被 include≥1 拦），其余一条一关联
    assert _query(
        db_path, "SELECT budget_id, category_id FROM budget_categories ORDER BY budget_id"
    ) == [
        (seed_budget_id, kept),
        (seed_budget_id + 1, kept),           # merge_map 重定向
        (seed_budget_id + 2, ids["a_refund_income"]),
        (seed_budget_id + 4, ids["a_other_income"]),
    ]
    # 阶段 B 后全局零悬挂（loser 已删、4242 本就不存在 → 关系行不落库）
    assert _query(db_path, "PRAGMA foreign_key_check") == []
    # 关联表按新 DDL 重建：命名 UNIQUE 约束文本落位（判据读文本，不读 index_list）
    link_norm = re.sub(r"\s+", " ", _table_ddl(db_path, "budget_categories"))
    assert "CONSTRAINT idx_budgetcat_budget_category UNIQUE (budget_id, category_id)" in link_norm
    assert not [t for t in _tables(db_path) if t.endswith("_new")], "中间表未 RENAME 归位"

    # 二次运行：阶段 B 亦 [SKIP]，预算与关联行不再变化（任务 9.1 / 11.3）
    again_rows = _budget_rows(db_path, _NEW_BUDGET_COLS)
    assert _migrate(db_path) == 0
    again = capsys.readouterr().out
    assert "[SKIP] budgets 已是 v1.4.3 形制" in again
    assert _budget_rows(db_path, _NEW_BUDGET_COLS) == again_rows


def test_phase_b_handles_shape_without_user_id(tmp_path: Path, capsys: Any) -> None:
    """开发库形制（budgets 无 user_id + UNIQUE(category_id,month)）照样整表重建。"""
    db_path = tmp_path / "devdb.db"
    conn = _create_legacy_db(db_path, "ancient")
    ids = _seed_v142_state(conn, "ancient")
    conn.execute("DROP TABLE budgets")
    conn.executescript(_script(_BUDGETS_DDL_DEVDB))
    conn.execute(
        "INSERT INTO budgets (id, category_id, month, amount, created_at, updated_at)"
        " VALUES (11, ?, '2026-06', 222.5, '2026-01-02 00:00:00', '2026-01-02 00:00:00')",
        (ids["kept"],),
    )
    conn.commit()
    conn.close()

    assert _migrate(db_path) == 0
    out = capsys.readouterr().out
    assert "UNIQUE (category_id, month)" in out  # 旧形登记（仅日志，不据此分支）
    assert _budget_rows(db_path, _NEW_BUDGET_COLS) == [
        (11, None, "其他", "2026-06", 222.5, "include", "2026-01-02 00:00:00",
         "2026-01-02 00:00:00")
    ]
    assert _query(
        db_path, "SELECT budget_id, category_id FROM budget_categories"
    ) == [(11, ids["kept"])]
    assert _query(db_path, "PRAGMA foreign_key_check") == []


def test_phase_b_failure_rolls_back_phase_a(tmp_path: Path, capsys: Any) -> None:
    """单事务（任务 11.3）：阶段 B 失败 → 阶段 A 的分类结果同样不落库。"""
    db_path = tmp_path / "rollback_b.db"
    conn = _create_legacy_db(db_path, "v142")
    _seed_v142_state(conn, "v142")
    conn.close()

    cats_before = _query(
        db_path, "SELECT id, name, type, icon, sort_order, user_id FROM categories ORDER BY id"
    )
    budgets_before = _query(db_path, "SELECT * FROM budgets ORDER BY id")
    ddl_before = _categories_ddl(db_path)

    original = migration._rebuild_budgets_table

    async def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("injected phase-B failure")

    migration._rebuild_budgets_table = _boom  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError, match="injected phase-B failure"):
            _migrate(db_path)
    finally:
        migration._rebuild_budgets_table = original  # type: ignore[assignment]
    capsys.readouterr()

    assert _query(
        db_path, "SELECT id, name, type, icon, sort_order, user_id FROM categories ORDER BY id"
    ) == cats_before, "阶段 B 失败必须把阶段 A 一起回滚（同事务）"
    assert _categories_ddl(db_path) == ddl_before
    assert _query(db_path, "SELECT * FROM budgets ORDER BY id") == budgets_before
    tables = _tables(db_path)
    assert "budget_categories" not in tables
    assert "budgets_new" not in tables and "categories_new" not in tables


def test_phase_b_skips_when_budgets_already_new(tmp_path: Path, capsys: Any) -> None:
    """categories 旧 + budgets 新：阶段 A 照跑、阶段 B [SKIP] 且预算数据不被改写。"""
    db_path = tmp_path / "budgets_already_new.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(_script(_CATEGORIES_DDL_V142, _OTHER_TABLES_DDL))
    conn.execute("DROP TABLE budgets")  # _OTHER_TABLES_DDL 给的是旧形，此库要模拟「B 已跑过」
    conn.executescript(_script(_BUDGETS_DDL_V143, migration._BUDGET_CATEGORIES_DDL))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (id, username, hashed_password, created_at, updated_at)"
        " VALUES (1, 'alice', 'x', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
    )
    for cat_id, (name, cat_type) in enumerate([("餐饮", "expense"), ("餐饮", "income")], start=1):
        _insert_category(
            conn, cat_id, name, cat_type, "mdi-food", cat_id, 0, 1, with_user_column=True
        )
    cur.execute(
        "INSERT INTO budgets (id, user_id, name, month, amount, scope_mode, created_at,"
        " updated_at) VALUES (7, 1, '日常开销', '2026-06', 1234.5, 'exclude',"
        " '2026-01-02 00:00:00', '2026-01-02 00:00:00')"
    )
    # 关联挂在**保留行**（expense 侧 id=1）上：阶段 A 删 income 侧 loser 后不得留悬挂
    cur.execute("INSERT INTO budget_categories (budget_id, category_id) VALUES (7, 1)")
    conn.commit()
    conn.close()

    rows_before = _budget_rows(db_path, _NEW_BUDGET_COLS)
    links_before = _query(
        db_path, "SELECT id, budget_id, category_id FROM budget_categories ORDER BY id"
    )

    assert _migrate(db_path) == 0
    out = capsys.readouterr().out
    assert "[OK] 合并 1 组同名分类" in out
    assert "[SKIP] budgets 已是 v1.4.3 形制" in out
    assert "[OK] 转换" not in out, "阶段 B 已 SKIP 时不得再改写 budgets"
    assert _budget_rows(db_path, _NEW_BUDGET_COLS) == rows_before
    assert _query(
        db_path, "SELECT id, budget_id, category_id FROM budget_categories ORDER BY id"
    ) == links_before
    assert _query(db_path, "PRAGMA foreign_key_check") == []
