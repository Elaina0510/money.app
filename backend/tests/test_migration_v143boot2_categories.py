"""v1.4.3-boot2 M2 迁移脚本测试（`backend/migrate_to_v1.4.3boot2_categories.py`）。

对应任务 `doc/tasksv1.4.3boot2/m2-merge-other-categories.md` §3（设计 §2.4）逐条：

  * **3.1** 夹具「现场形态」：旧名预设（user_id=NULL）+ 用户旧名副本 + 预设「其他」
    + records/quick_templates/**budget_categories** 引用行 —— `test_3_1_*`；
  * **3.2** 家族常量 ⊇/⊆ 双向互钉（P3 闭环的脚本侧落点）—— `test_3_2_*`；
  * **3.3** 合并断言（每桶单一「其他」+ icon + 置尾 + 分表重定向计数 + loser 删除）
    —— `test_3_3_*`（另含 CoW 遮蔽、单旧名行归一两组补充）；
  * **3.4** 幂等：二次执行统计全 0、数据不变 —— `test_3_4_*`；
  * **3.5** 环境变体：旧 UNIQUE 形 / `budget_categories` 缺表各一组 —— `test_3_5_*`；
  * **3.6** 顺序收敛：v1.4.3 → boot2 与 boot2 → v1.4.3 双向 —— `test_3_6_*`；
  * **1.3** 处置顺序（先 DELETE loser 再改 keeper 名）与 **1.8** 单事务回滚 ——
    `test_1_3_*` / `test_1_8_*`。

手法要点（沿 `test_migration_v143.py` 既有惯例）：

  * 一律在 **tmp_path 临时 SQLite 库**上手写建表 + 造数据，**绝不对 `backend/money.db`
    做任何写操作或迁移**（项目红线；全部门槛命令同样不触真库）；
  * 被测脚本文件名含点号 → 只能 `spec_from_file_location` 按路径加载（`import` 机制把
    dots 当包分隔符，会抛 SyntaxError 而非 ImportError）。`migrate_to_v1.4.3.py` 同理
    **仅按路径加载用于 §3.6 顺序联测**——本模块脚本与运行期代码都不 import 它（§2.2.3）；
  * 预设真源 import `app.main.PRESET_CATEGORIES`，不用 conftest 的过期 7 条副本；
  * `app/` 运行期代码只读 import（常量一致性），零修改。
"""

import asyncio
import importlib.util
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from app.main import PRESET_CATEGORIES

# ── 被测脚本（文件名含点号，按路径加载；模块级单例便于打桩）──────────────────
_BACKEND = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _BACKEND / "migrate_to_v1.4.3boot2_categories.py"
_V143_SCRIPT_PATH = _BACKEND / "migrate_to_v1.4.3.py"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load("migrate_to_v1_4_3_boot2_categories", _SCRIPT_PATH)

FAMILY_NAMES = ("其他", "其他支出", "其他收入")

# ── 建表 DDL：新形（已跑 v1.4.3）与旧形（未跑 v1.4.3）───────────────────────
_USERS_DDL = """
CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
)
"""

# 新形 categories：表级 UNIQUE (name, user_id)
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

# 旧形 categories：v1.4 起真实 money.db 的形制，表级 UNIQUE (name, type, user_id)
_CATEGORIES_DDL_OLD_UNIQUE = """
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

_TAGS_DDL = """
CREATE TABLE tags (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at VARCHAR NOT NULL,
    deleted_at TEXT
)
"""

_RECORDS_DDL = """
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
)
"""

_QUICK_TEMPLATES_DDL = """
CREATE TABLE quick_templates (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    type VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    created_at VARCHAR NOT NULL
)
"""

# record_tags：**无 category_id 列**（分类引用经 records 覆盖）→ 不在重定向集合内，
# 用例断言其行数与内容一字不变（任务 1.4「tags 如有关联表一并处理」的核查落点）。
_RECORD_TAGS_DDL = """
CREATE TABLE record_tags (
    record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (record_id, tag_id)
)
"""

# v1.4.3 新形 budgets（无 category_id 列）+ 关联表
_BUDGETS_DDL_NEW = """
CREATE TABLE budgets (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    month VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    scope_mode VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
)
"""

_BUDGET_CATEGORIES_DDL = """
CREATE TABLE budget_categories (
    id INTEGER NOT NULL PRIMARY KEY,
    budget_id INTEGER NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    CONSTRAINT idx_budgetcat_budget_category UNIQUE (budget_id, category_id)
)
"""

# v1.4.3 之前的旧形 budgets：分类挂在 category_id 列上（本期**不**重定向，见脚本头
# 「已知边界」段——设计 §2.2.1 的表集合里没有它）
_BUDGETS_DDL_OLD = """
CREATE TABLE budgets (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    month VARCHAR NOT NULL,
    amount FLOAT NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    CONSTRAINT idx_budget_category_month UNIQUE (category_id, month)
)
"""

_OPERATION_HISTORY_DDL = """
CREATE TABLE operation_history (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER,
    operation_type VARCHAR NOT NULL,
    table_name VARCHAR NOT NULL,
    record_id INTEGER,
    snapshot_data TEXT,
    created_at VARCHAR NOT NULL
)
"""

_COMMON_TABLES_DDL = (
    _USERS_DDL, _TAGS_DDL, _RECORDS_DDL, _QUICK_TEMPLATES_DDL, _RECORD_TAGS_DDL,
    _OPERATION_HISTORY_DDL,
)


def _joined(ddls: tuple[str, ...]) -> str:
    return ";\n".join(d.strip().rstrip(";") for d in ddls if d.strip()) + ";"


def _create(db_path: Path, *ddls: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(_joined(ddls))
    return conn


def _insert_users(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO users (id, username, hashed_password, created_at, updated_at)"
        " VALUES (?, ?, 'x', '2026-01-01 00:00:00', '2026-01-01 00:00:00')",
        [(1, "alice"), (2, "bob")],
    )


def _insert_category(
    conn: sqlite3.Connection,
    cat_id: int,
    name: str,
    cat_type: str,
    icon: str,
    sort_order: int,
    is_preset: int,
    user_id: int | None,
) -> None:
    conn.execute(
        "INSERT INTO categories (id, name, type, icon, sort_order, is_preset, created_at,"
        " user_id) VALUES (?, ?, ?, ?, ?, ?, '2026-01-01 00:00:00', ?)",
        (cat_id, name, cat_type, icon, sort_order, is_preset, user_id),
    )


def _insert_preset(
    conn: sqlite3.Connection, cat_id: int, preset: dict[str, object]
) -> None:
    """`app.main.PRESET_CATEGORIES` 的一条 → 预设分类行（值形 object，逐列窄化）。"""
    _insert_category(
        conn, cat_id, str(preset["name"]), str(preset["type"]), str(preset["icon"]),
        int(str(preset["sort_order"])), 1, None,
    )


# ── 分类行 id 约定（夹具与断言共用，避免两侧硬编码漂移）─────────────────────
CAT_PRESET_OTHER = 14          # 预设「其他」（keeper，sort 14）
CAT_PRESET_OTHER_EXP = 15      # 预设「其他支出」sort 99（现场实测压在「其他」之后）
CAT_PRESET_OTHER_INC = 16      # 预设「其他收入」sort 99
CAT_A_FOOD = 21
CAT_A_OTHER_INC = 22           # 用户 1 的「其他收入」副本 → loser
CAT_A_OTHER_EXP = 23           # 用户 1 的「其他支出」副本 → keeper（优先级见 3.2）
CAT_A_PET = 24                 # 用户 1 自建「宠物」sort 20 → 决定 keeper 置尾落点
CAT_B_OTHER = 31               # 用户 2 的「其他」副本（icon 漂移 mdi-cash）
CAT_B_OTHER_EXP = 32
CAT_B_TRAVEL = 33

LOSER_IDS = (CAT_PRESET_OTHER_EXP, CAT_PRESET_OTHER_INC, CAT_A_OTHER_INC, CAT_B_OTHER_EXP)


def seed_live_shape(db_path: Path) -> None:
    """3.1 主夹具：新形库 + 「现场形态」三桶家族行 + 四类引用行。

    桶构成（脚本按 `user_id` 分桶、跨桶不合并）：
      * 预设桶（NULL）：新 14 条单套（含「其他」sort 14）**外加**两旧名预设行 sort 99；
      * 用户 1 桶：两旧名副本（无「其他」副本）+ 餐饮副本 + 自建「宠物」sort 20；
      * 用户 2 桶：「其他」副本（icon 漂移）+「其他支出」副本 + 旅行副本。
    引用行刻意覆盖三种形态：仅挂 loser / 同挂 loser 与 keeper（`UNIQUE(budget_id,
    category_id)` 撞形）/ 只挂 keeper 与非家族行（对照不动）。
    """
    conn = _create(db_path, _CATEGORIES_DDL_NEW, *_COMMON_TABLES_DDL, _BUDGETS_DDL_NEW,
                   _BUDGET_CATEGORIES_DDL)
    _insert_users(conn)

    next_id = 1
    for preset in PRESET_CATEGORIES:
        if preset["name"] == script.OTHER_CATEGORY_NAME:
            cat_id = CAT_PRESET_OTHER
        else:
            cat_id = next_id
            next_id += 1
        _insert_preset(conn, cat_id, preset)
    _insert_category(conn, CAT_PRESET_OTHER_EXP, "其他支出", "expense", "mdi-cash-minus",
                     99, 1, None)
    _insert_category(conn, CAT_PRESET_OTHER_INC, "其他收入", "income", "mdi-cash-plus",
                     99, 1, None)

    _insert_category(conn, CAT_A_FOOD, "餐饮", "expense", "mdi-food", 1, 0, 1)
    _insert_category(conn, CAT_A_OTHER_INC, "其他收入", "income", "mdi-cash-plus", 2, 0, 1)
    _insert_category(conn, CAT_A_OTHER_EXP, "其他支出", "expense", "mdi-cash-minus", 3, 0, 1)
    _insert_category(conn, CAT_A_PET, "宠物", "expense", "mdi-paw", 20, 0, 1)
    _insert_category(conn, CAT_B_OTHER, "其他", "expense", "mdi-cash", 3, 0, 2)
    _insert_category(conn, CAT_B_OTHER_EXP, "其他支出", "expense", "mdi-cash-minus", 8, 0, 2)
    _insert_category(conn, CAT_B_TRAVEL, "旅行", "expense", "mdi-airplane", 5, 0, 2)

    conn.executemany(
        "INSERT INTO records (id, user_id, amount, type, category_id, tag_id, consume_time,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, '2026-01-02 00:00:00',"
        " '2026-01-02 00:00:00')",
        [
            (101, 1, 5.0, "expense", CAT_PRESET_OTHER_EXP, None, "2026-07-01 09:00"),
            (102, 1, 12.5, "expense", CAT_PRESET_OTHER_EXP, None, "2026-07-02 09:00"),
            (103, 1, 30.0, "income", CAT_PRESET_OTHER_INC, None, "2026-07-03 09:00"),
            (104, 1, 99.0, "expense", CAT_PRESET_OTHER, None, "2026-07-04 09:00"),
            (105, 1, 7.7, "income", CAT_A_OTHER_INC, None, "2026-07-05 09:00"),
            (106, 2, 3.3, "expense", CAT_B_OTHER_EXP, None, "2026-07-06 09:00"),
            (107, 1, 88.0, "expense", CAT_A_FOOD, None, "2026-07-07 09:00"),
        ],
    )
    conn.execute(
        "INSERT INTO tags (id, user_id, name, category_id, created_at)"
        " VALUES (201, 1, '杂项标签', ?, '2026-01-02 00:00:00')",
        (CAT_PRESET_OTHER_EXP,),
    )
    conn.execute(
        "INSERT INTO record_tags (record_id, tag_id) VALUES (101, 201)"
    )
    conn.executemany(
        "INSERT INTO quick_templates (id, user_id, tag_id, category_id, type, amount,"
        " created_at) VALUES (?, 1, NULL, ?, ?, ?, '2026-01-02 00:00:00')",
        [
            (301, CAT_PRESET_OTHER_INC, "income", 30.0),
            (302, CAT_A_OTHER_INC, "income", 7.7),
        ],
    )
    conn.executemany(
        "INSERT INTO budgets (id, user_id, name, month, amount, scope_mode, created_at,"
        " updated_at) VALUES (?, ?, ?, '2026-07', ?, 'include',"
        " '2026-01-02 00:00:00', '2026-01-02 00:00:00')",
        [(401, 1, "日常", 1000.0), (402, 1, "杂项", 200.0),
         (403, 2, "家庭", 500.0), (404, 1, "预设口径", 300.0)],
    )
    conn.executemany(
        "INSERT INTO budget_categories (id, budget_id, category_id) VALUES (?, ?, ?)",
        [
            (501, 401, CAT_A_FOOD),
            (502, 401, CAT_A_OTHER_INC),       # 仅挂 loser → 重定向到同桶 keeper
            (503, 402, CAT_A_OTHER_INC),       # 与 504 同预算：重定向撞形 → 去重删除
            (504, 402, CAT_A_OTHER_EXP),
            (505, 403, CAT_B_OTHER),
            (506, 403, CAT_B_OTHER_EXP),       # 撞形去重
            (507, 404, CAT_PRESET_OTHER_EXP),  # 预设桶 loser → 重定向到预设 keeper
        ],
    )
    conn.commit()
    conn.close()


def seed_legacy_shape(db_path: Path) -> None:
    """3.5 变体（a）+ 3.6 顺序联测夹具：未跑 `migrate_to_v1.4.3.py` 的旧形库。

    categories 为表级 `UNIQUE (name, type, user_id)`、budgets 为旧形（category_id 列）、
    **无 `budget_categories` 表**——同时命中「旧 UNIQUE 形」与「缺表探测」两个变体点。
    """
    conn = _create(db_path, _CATEGORIES_DDL_OLD_UNIQUE, *_COMMON_TABLES_DDL,
                   _BUDGETS_DDL_OLD)
    _insert_users(conn)
    _insert_category(conn, 1, "餐饮", "expense", "mdi-food", 1, 1, None)
    _insert_category(conn, 2, "工资", "income", "mdi-wallet", 1, 1, None)
    _insert_category(conn, 3, "其他", "expense", "mdi-cash-minus", 14, 1, None)
    _insert_category(conn, 4, "其他支出", "expense", "mdi-cash-minus", 99, 1, None)
    _insert_category(conn, 5, "其他收入", "income", "mdi-cash-plus", 99, 1, None)
    _insert_category(conn, 6, "其他支出", "expense", "mdi-cash-minus", 2, 0, 1)
    _insert_category(conn, 7, "其他收入", "income", "mdi-cash-plus", 3, 0, 1)
    _insert_category(conn, 8, "宠物", "expense", "mdi-paw", 10, 0, 1)

    conn.executemany(
        "INSERT INTO records (id, user_id, amount, type, category_id, tag_id, consume_time,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, '2026-01-02 00:00:00',"
        " '2026-01-02 00:00:00')",
        [
            (11, 1, 5.0, "expense", 4, None, "2026-07-01 09:00"),
            (12, 1, 30.0, "income", 5, None, "2026-07-02 09:00"),
            (13, 1, 7.7, "income", 7, None, "2026-07-03 09:00"),
            (14, 1, 66.0, "expense", 3, None, "2026-07-04 09:00"),
        ],
    )
    conn.execute(
        "INSERT INTO tags (id, user_id, name, category_id, created_at)"
        " VALUES (21, 1, '旧标签', 5, '2026-01-02 00:00:00')"
    )
    conn.execute(
        "INSERT INTO record_tags (record_id, tag_id) VALUES (12, 21)"
    )
    conn.execute(
        "INSERT INTO quick_templates (id, user_id, tag_id, category_id, type, amount,"
        " created_at) VALUES (31, 1, NULL, 7, 'income', 7.7, '2026-01-02 00:00:00')"
    )
    # 旧形 budgets 只挂 keeper / 非家族行：loser 上的旧形预算行属脚本头登记的已知边界
    conn.executemany(
        "INSERT INTO budgets (id, user_id, category_id, month, amount, created_at,"
        " updated_at) VALUES (?, ?, ?, '2026-08', ?, '2026-01-02 00:00:00',"
        " '2026-01-02 00:00:00')",
        [(901, 1, 3, 500.0), (902, 1, 1, 800.0)],
    )
    conn.commit()
    conn.close()


# ── 执行与读取工具 ──────────────────────────────────────────────────────────
def boot2(db_path: Path) -> dict[str, Any]:
    """执行本模块脚本，返回统计摘要（`merged_rows` / `redirected_references` …）。"""
    stats: dict[str, Any] = asyncio.run(script.run_migration(str(db_path)))
    return stats


def boot2_via_cli(db_path: Path) -> int:
    """走 CLI 入口（发布窗口手法：`python migrate_to_v1.4.3boot2_categories.py <db>`）。"""
    return int(asyncio.run(script.migrate([str(_SCRIPT_PATH), str(db_path)])))


def run_v143(db_path: Path) -> int:
    """按路径加载并执行 `migrate_to_v1.4.3.py`（仅 §3.6 顺序联测；不 import 进产品码）。"""
    v143 = _load("migrate_to_v1_4_3", _V143_SCRIPT_PATH)
    return int(asyncio.run(v143.migrate([str(_V143_SCRIPT_PATH), str(db_path)])))


def query(db_path: Path, sql: str, params: Any = ()) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def tables(db_path: Path) -> set[str]:
    return {str(r[0]) for r in query(db_path, "SELECT name FROM sqlite_master")}


def family_rows(db_path: Path) -> list[tuple[Any, ...]]:
    """全库家族行 (user_id, id, name, icon, sort_order)——「每桶仅剩一行」的核对口径。"""
    return query(
        db_path,
        "SELECT user_id, id, name, icon, sort_order FROM categories WHERE name IN (?,?,?)"
        " ORDER BY user_id IS NOT NULL, user_id, id",
        FAMILY_NAMES,
    )


def links(db_path: Path) -> list[tuple[Any, ...]]:
    if "budget_categories" not in tables(db_path):
        return []
    return query(
        db_path,
        "SELECT budget_id, category_id FROM budget_categories ORDER BY budget_id,"
        " category_id",
    )


def snapshot(db_path: Path) -> dict[str, list[tuple[Any, ...]]]:
    """全量数据快照（幂等/回滚用例的「一字不差」比对基准）。"""
    has_legacy_budget_col = "category_id" in [r[1] for r in
                                              query(db_path, "PRAGMA table_info(budgets)")]
    if "budgets" not in tables(db_path):
        budget_rows: list[tuple[Any, ...]] = []
    elif has_legacy_budget_col:
        budget_rows = query(
            db_path, "SELECT id, user_id, category_id, month, amount FROM budgets ORDER BY id"
        )
    else:
        budget_rows = query(
            db_path,
            "SELECT id, user_id, name, month, amount, scope_mode FROM budgets ORDER BY id",
        )
    data: dict[str, list[tuple[Any, ...]]] = {
        "categories": query(
            db_path,
            "SELECT id, name, type, icon, sort_order, is_preset, user_id FROM categories"
            " ORDER BY id",
        ),
        "records": query(
            db_path, "SELECT id, amount, type, category_id, tag_id FROM records ORDER BY id"
        ),
        "tags": query(db_path, "SELECT id, name, category_id FROM tags ORDER BY id"),
        "record_tags": query(
            db_path, "SELECT record_id, tag_id FROM record_tags ORDER BY record_id, tag_id"
        )
        if "record_tags" in tables(db_path)
        else [],
        "quick_templates": query(
            db_path, "SELECT id, category_id, type, amount FROM quick_templates ORDER BY id"
        ),
        "budgets": budget_rows,
        "budget_categories": links(db_path),
    }
    return data


def visible_family_rows(db_path: Path, user_id: int | None) -> list[tuple[Any, ...]]:
    """复刻 `category_service._visible_categories` 的 CoW 遮蔽语义（预设仅按 name 匹配）。

    用途：验证「跨桶不合并 + 用户副本改名后天然遮蔽预设行」（任务 1.5）。
    """
    if user_id is None:
        return query(
            db_path,
            "SELECT id, name FROM categories WHERE user_id IS NULL AND name IN (?,?,?)"
            " ORDER BY sort_order, id",
            FAMILY_NAMES,
        )
    rows = query(
        db_path,
        "SELECT c.id, c.name FROM categories c WHERE (c.user_id = :u OR (c.is_preset = 1"
        " AND NOT EXISTS (SELECT 1 FROM categories oc WHERE oc.name = c.name"
        "  AND oc.user_id = :u AND oc.is_preset = 0)))"
        " AND c.name IN (:f0, :f1, :f2) ORDER BY c.sort_order, c.id",
        {"u": user_id, "f0": FAMILY_NAMES[0], "f1": FAMILY_NAMES[1], "f2": FAMILY_NAMES[2]},
    )
    return rows


def monthly_totals(db_path: Path) -> list[tuple[Any, ...]]:
    """按月 group by type 的收支合计（串联两脚本的「不丢不重」比对基准）。"""
    return query(
        db_path,
        "SELECT substr(consume_time,1,7) AS m, type, ROUND(SUM(amount), 2), COUNT(*)"
        " FROM records GROUP BY m, type ORDER BY m, type",
    )


# ── 3.1 夹具即「现场形态」（钉住夹具，防后续断言空转）───────────────────────
def test_3_1_fixture_reproduces_the_live_shape(tmp_path: Path) -> None:
    db = tmp_path / "live.db"
    seed_live_shape(db)

    # 三桶家族行并存：预设桶 3 行、用户 1 桶 2 行、用户 2 桶 2 行
    assert [(r[0], r[1]) for r in family_rows(db)] == [
        (None, CAT_PRESET_OTHER), (None, CAT_PRESET_OTHER_EXP), (None, CAT_PRESET_OTHER_INC),
        (1, CAT_A_OTHER_INC), (1, CAT_A_OTHER_EXP),
        (2, CAT_B_OTHER), (2, CAT_B_OTHER_EXP),
    ]
    # 旧名预设行确实「压」在预设「其他」之后（§0.4 现场取证形态：99 vs 14）
    assert query(
        db,
        "SELECT id, sort_order FROM categories WHERE is_preset = 1 AND user_id IS NULL"
        " AND sort_order > 14 ORDER BY id",
    ) == [(CAT_PRESET_OTHER_EXP, 99), (CAT_PRESET_OTHER_INC, 99)]
    # 四类引用表都持有挂在家族行上的引用行（含本期新增的 budget_categories）
    placeholders = ", ".join("?" for _ in LOSER_IDS)
    assert query(
        db, f"SELECT COUNT(*) FROM records WHERE category_id IN ({placeholders})",
        LOSER_IDS,
    )[0][0] == 5
    assert query(
        db, f"SELECT COUNT(*) FROM tags WHERE category_id IN ({placeholders})", LOSER_IDS
    )[0][0] == 1
    assert query(
        db, f"SELECT COUNT(*) FROM quick_templates WHERE category_id IN ({placeholders})",
        LOSER_IDS,
    )[0][0] == 2
    assert links(db) == [
        (401, CAT_A_FOOD), (401, CAT_A_OTHER_INC), (402, CAT_A_OTHER_INC),
        (402, CAT_A_OTHER_EXP), (403, CAT_B_OTHER), (403, CAT_B_OTHER_EXP),
        (404, CAT_PRESET_OTHER_EXP),
    ]
    # 关联表 record_tags 在位（无 category_id 列，脚本按集合排除）
    assert query(db, "SELECT record_id, tag_id FROM record_tags") == [(101, 201)]


# ── 3.2 家族常量 ⊇/⊆ 双向互钉（P3 闭环的脚本侧落点）────────────────────────
def test_3_2_family_constants_are_pinned_in_both_directions() -> None:
    from app.services import category_service as svc

    # 双向包含（⊇ 且 ⊆）：任一侧增删家族名都会炸掉其中一条断言
    assert set(script.OTHER_FAMILY_RANK) >= set(svc.OTHER_FAMILY_RANK)
    assert set(script.OTHER_FAMILY_RANK) <= set(svc.OTHER_FAMILY_RANK)
    assert script.OTHER_FAMILY_RANK == svc.OTHER_FAMILY_RANK
    # 每侧自身同构：家族 = 本名 + 旧名（防「只改一侧的名字表」）
    assert set(script.OTHER_FAMILY_RANK) == {script.OTHER_CATEGORY_NAME,
                                             *script.LEGACY_OTHER_NAMES}
    assert set(svc.OTHER_FAMILY_RANK) == {svc.OTHER_CATEGORY_NAME, *svc.LEGACY_OTHER_NAMES}
    assert script.OTHER_CATEGORY_NAME == svc.OTHER_CATEGORY_NAME
    assert tuple(script.LEGACY_OTHER_NAMES) == tuple(svc.LEGACY_OTHER_NAMES)
    # 名次表逐位一致（D6：其他支出 < 其他收入 < 其他，「其他」恒最大）
    assert script.OTHER_FAMILY_RANK == {"其他支出": 0, "其他收入": 1, "其他": 2}
    assert svc.OTHER_FAMILY_RANK[svc.OTHER_CATEGORY_NAME] == max(
        svc.OTHER_FAMILY_RANK.values()
    )
    # keeper 优先级 = 设计 §2.2.1「其他 > 其他支出 > 其他收入」，**不是**名次表的倒序
    assert script.KEEPER_PRIORITY == ("其他", "其他支出", "其他收入")
    assert script.KEEPER_PRIORITY[0] == script.OTHER_CATEGORY_NAME
    assert set(script.KEEPER_PRIORITY) == set(svc.OTHER_FAMILY_RANK)


def test_3_2b_keeper_icon_matches_the_app_preset_source() -> None:
    """keeper 图标对齐 `app/main.py` 预设 14 条单套里「其他」的固定值（任务 1.2）。"""
    preset_icon = next(
        p["icon"] for p in PRESET_CATEGORIES if p["name"] == script.OTHER_CATEGORY_NAME
    )
    assert script.OTHER_CATEGORY_ICON == preset_icon == "mdi-cash-minus"


# ── 3.3 合并断言 ────────────────────────────────────────────────────────────
def test_3_3_merges_each_bucket_and_redirects_every_reference_table(
    tmp_path: Path, capsys: Any
) -> None:
    db = tmp_path / "live.db"
    seed_live_shape(db)
    non_family_before = query(
        db, "SELECT id, name, type, icon, sort_order, is_preset, user_id FROM categories"
        " WHERE name NOT IN (?,?,?) ORDER BY id",
        FAMILY_NAMES,
    )

    stats = boot2(db)
    capsys.readouterr()

    # 统计：3 桶 / loser 4 行 / keeper 归一 2 行 / 置尾 2 桶 / 分表重定向计数
    assert stats["buckets_scanned"] == 3
    assert stats["merged_rows"] == 4
    assert stats["keepers_normalized"] == 2
    assert stats["tail_fixed"] == 2
    assert stats["redirected_references"] == {
        "records": 5, "tags": 1, "quick_templates": 2, "budget_categories": 2,
    }
    assert stats["deduped_references"] == {"budget_categories": 2}

    # 全库家族行仅剩各桶一个「其他」，名字统一、icon 固定、各桶末位
    assert family_rows(db) == [
        (None, CAT_PRESET_OTHER, "其他", "mdi-cash-minus", 14),
        (1, CAT_A_OTHER_EXP, "其他", "mdi-cash-minus", 21),
        (2, CAT_B_OTHER, "其他", "mdi-cash-minus", 6),
    ]
    placeholders = ", ".join("?" for _ in LOSER_IDS)
    assert query(
        db, f"SELECT COUNT(*) FROM categories WHERE id IN ({placeholders})", LOSER_IDS
    )[0][0] == 0
    # keeper 优先级（其他支出 > 其他收入）：用户 1 桶保留 23 而非 22
    assert query(
        db, "SELECT id FROM categories WHERE user_id = 1 AND name = '其他'"
    )[0][0] == CAT_A_OTHER_EXP
    # 置尾恒等式：每桶 keeper 的 sort_order = 该桶存活行最大值（任务 1.6）
    for pred in ("user_id IS NULL", "user_id = 1", "user_id = 2"):
        assert query(
            db,
            f"SELECT sort_order = (SELECT MAX(sort_order) FROM categories WHERE {pred})"
            f" FROM categories WHERE name = '其他' AND {pred}",
        )[0][0] == 1, f"桶 {pred} 的「其他」不在末位"
    # 预设桶「其他」已是最大 → 不动（幂等判据的另一半）
    assert query(
        db, "SELECT sort_order FROM categories WHERE id = ?", (CAT_PRESET_OTHER,)
    )[0][0] == 14

    # 引用重定向落到**同桶** keeper（跨桶不合并）
    assert dict(query(
        db, "SELECT id, category_id FROM records WHERE id IN (101,102,103,105,106)"
        " ORDER BY id",
    )) == {
        101: CAT_PRESET_OTHER, 102: CAT_PRESET_OTHER, 103: CAT_PRESET_OTHER,
        105: CAT_A_OTHER_EXP, 106: CAT_B_OTHER,
    }
    assert query(
        db, "SELECT category_id FROM records WHERE id IN (104, 107) ORDER BY id"
    ) == [(CAT_PRESET_OTHER,), (CAT_A_FOOD,)]
    assert query(
        db, "SELECT category_id FROM tags WHERE id = 201"
    )[0][0] == CAT_PRESET_OTHER
    assert dict(query(db, "SELECT id, category_id FROM quick_templates ORDER BY id")) == {
        301: CAT_PRESET_OTHER, 302: CAT_A_OTHER_EXP,
    }
    # **budget_categories**（本期新增、蓝本没有的表）：重定向 + 撞形去重后覆盖不丢
    assert links(db) == [
        (401, CAT_A_FOOD), (401, CAT_A_OTHER_EXP), (402, CAT_A_OTHER_EXP),
        (403, CAT_B_OTHER), (404, CAT_PRESET_OTHER),
    ]
    # 非家族行一字未动（脚本只碰家族行与 keeper 的 name/icon/sort_order）
    assert query(
        db, "SELECT id, name, type, icon, sort_order, is_preset, user_id FROM categories"
        " WHERE name NOT IN (?,?,?) ORDER BY id",
        FAMILY_NAMES,
    ) == non_family_before
    # 合并后不留任何悬挂引用
    assert query(db, "PRAGMA foreign_key_check") == []


def test_3_3b_cow_shadowing_keeps_buckets_independent(tmp_path: Path) -> None:
    """任务 1.5：用户副本改名「其他」后按 CoW 遮蔽预设行，**不**重定向到预设 id。"""
    db = tmp_path / "live.db"
    seed_live_shape(db)
    boot2(db)

    assert visible_family_rows(db, 1) == [(CAT_A_OTHER_EXP, "其他")]   # 预设 14 被遮蔽
    assert visible_family_rows(db, 2) == [(CAT_B_OTHER, "其他")]       # 同理
    assert visible_family_rows(db, None) == [(CAT_PRESET_OTHER, "其他")]
    # 预设桶的账单仍指向预设 keeper（没有被并进任一用户桶）：3 笔重定向 + 1 笔对照
    assert query(
        db, "SELECT COUNT(*) FROM records WHERE category_id = ?", (CAT_PRESET_OTHER,)
    )[0][0] == 4


def test_3_3c_single_legacy_row_is_normalized_without_merging(tmp_path: Path) -> None:
    """任务 1.2：桶内家族行只有 1 行时不合并（merged_rows=0），但仍归名 + 刷图标。"""
    db = tmp_path / "single.db"
    conn = _create(db, _CATEGORIES_DDL_NEW, *_COMMON_TABLES_DDL, _BUDGETS_DDL_NEW,
                   _BUDGET_CATEGORIES_DDL)
    _insert_users(conn)
    _insert_category(conn, 1, "其他", "expense", "mdi-cash-minus", 1, 1, None)
    _insert_category(conn, 2, "其他收入", "income", "mdi-cash-plus", 5, 0, 1)
    conn.commit()
    conn.close()

    stats = boot2(db)

    assert stats["merged_rows"] == 0          # 无 loser → 不合并
    assert stats["keepers_normalized"] == 1   # 单行也收敛为「其他」
    assert stats["tail_fixed"] == 0           # 桶内家族仅一行 → 天然末位
    # 预设桶的「其他」原样不动（跨桶不合并），用户桶旧名单行归名为「其他」
    assert family_rows(db) == [
        (None, 1, "其他", "mdi-cash-minus", 1),
        (1, 2, "其他", "mdi-cash-minus", 5),
    ]
    assert script.is_noop(boot2(db)) is True


def test_3_3d_keeper_priority_is_pure_and_deterministic() -> None:
    """keeper 选取纯函数口径（任务 1.1/1.2）：其他 > 其他支出 > 其他收入。"""
    pick = script.pick_keeper  # 局部别名，读起来短一点
    assert pick([_cat(3, "其他", 9)])["id"] == 3
    assert pick([_cat(1, "其他收入", 1), _cat(2, "其他支出", 2)])["id"] == 2
    assert pick([_cat(1, "其他收入", 1)])["id"] == 1
    # 本名行 sort 最大也仍胜（优先级高于位置）
    assert pick([_cat(1, "其他", 99), _cat(2, "其他支出", 1)])["id"] == 1
    # 同一优先级内 tie-break = (sort_order, id)
    assert pick([_cat(7, "其他支出", 5), _cat(6, "其他支出", 5)])["id"] == 6
    assert pick([_cat(7, "其他支出", 5), _cat(6, "其他支出", 4)])["id"] == 6


def _cat(cat_id: int, name: str, sort_order: int) -> dict[str, Any]:
    return {
        "id": cat_id, "name": name, "icon": "", "sort_order": sort_order,
        "user_id": None, "deleted": False,
    }


# ── 3.4 幂等 ────────────────────────────────────────────────────────────────
def test_3_4_second_run_is_a_full_noop(tmp_path: Path, capsys: Any) -> None:
    db = tmp_path / "live.db"
    seed_live_shape(db)

    assert boot2(db)["merged_rows"] == 4
    capsys.readouterr()
    before = snapshot(db)

    stats = boot2(db)
    out = capsys.readouterr().out

    assert "[SKIP]" in out and "no-op" in out
    assert stats["merged_rows"] == 0
    assert stats["keepers_normalized"] == 0
    assert stats["tail_fixed"] == 0
    assert sum(stats["redirected_references"].values()) == 0
    assert sum(stats["deduped_references"].values()) == 0
    assert script.is_noop(stats) is True
    assert snapshot(db) == before
    # 第三次仍 no-op（不是「第二次刚好收敛」的巧合）
    assert script.is_noop(boot2(db)) is True
    assert snapshot(db) == before


def test_3_4b_clean_database_is_left_untouched(tmp_path: Path, capsys: Any) -> None:
    """正常态库（新 14 条单套、只有「其他」）执行 = no-op，不产生任何写入。"""
    db = tmp_path / "clean.db"
    conn = _create(db, _CATEGORIES_DDL_NEW, *_COMMON_TABLES_DDL, _BUDGETS_DDL_NEW,
                   _BUDGET_CATEGORIES_DDL)
    _insert_users(conn)
    for cat_id, preset in enumerate(PRESET_CATEGORIES, start=1):
        _insert_preset(conn, cat_id, preset)
    conn.commit()
    conn.close()

    before = snapshot(db)
    stats = boot2(db)
    capsys.readouterr()

    assert script.is_noop(stats) is True
    assert snapshot(db) == before


# ── 1.3 处置顺序 / 1.8 单事务回滚 ───────────────────────────────────────────
_RENAME_PROBE_TRIGGER = """
CREATE TRIGGER probe_rename_after_delete BEFORE UPDATE OF name ON categories
WHEN NEW.name = '其他' AND EXISTS (
    SELECT 1 FROM categories WHERE id <> OLD.id AND user_id IS OLD.user_id
      AND name IN ('其他', '其他支出', '其他收入'))
BEGIN
    SELECT RAISE(ABORT, '改名时桶内仍有家族行：未先 DELETE loser');
END;
"""


def test_1_3_losers_are_deleted_before_the_keeper_is_renamed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """先 DELETE loser 再改 keeper 名（`UNIQUE(name,user_id)` 撞形规避，蓝本同款注释）。

    手法：夹具建好后挂一个 `BEFORE UPDATE OF name` 触发器，把「改名那一刻桶内不得
    再有任何其它家族行」写成库级硬约束——顺序写反即 RAISE 中止，本用例随之失败。
    再以调用序打桩复核同一事实（`_redirect_and_delete` 先于 `_apply_keepers`）。
    """
    db = tmp_path / "probe.db"
    seed_live_shape(db)
    conn = sqlite3.connect(db)
    conn.executescript(_RENAME_PROBE_TRIGGER)
    conn.commit()
    conn.close()

    stats = boot2(db)  # 若先改名后删行，这里会抛 IntegrityError/OperationalError
    assert stats["merged_rows"] == 4
    assert family_rows(db) == [
        (None, CAT_PRESET_OTHER, "其他", "mdi-cash-minus", 14),
        (1, CAT_A_OTHER_EXP, "其他", "mdi-cash-minus", 21),
        (2, CAT_B_OTHER, "其他", "mdi-cash-minus", 6),
    ]

    calls: list[str] = []

    async def spy_redirect(conn: Any, merge_map: dict[int, int]) -> Any:
        del conn, merge_map  # 仅记录调用序
        calls.append("redirect_and_delete")
        return {}, {}

    async def spy_apply(conn: Any, changed: list[dict[str, Any]]) -> None:
        del conn, changed
        calls.append("apply_keepers")

    monkeypatch.setattr(script, "_redirect_and_delete", spy_redirect)
    monkeypatch.setattr(script, "_apply_keepers", spy_apply)
    boot2(db)
    assert calls == ["redirect_and_delete", "apply_keepers"]


def test_1_8_midway_failure_rolls_back_and_can_be_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """单事务：中途失败整体回滚（库保持执行前状态），排除故障后直接重跑即可。"""
    db = tmp_path / "rollback.db"
    seed_live_shape(db)
    before = snapshot(db)

    def _boom(*_args: Any, **_kwargs: Any) -> int:
        raise RuntimeError("injected M2 failure")

    monkeypatch.setattr(script, "fix_tails", _boom)
    with pytest.raises(RuntimeError, match="injected M2 failure"):
        boot2(db)
    monkeypatch.undo()

    assert snapshot(db) == before, "失败必须整体回滚，不得残半截合并"

    assert boot2(db)["merged_rows"] == 4        # 回滚后原样重跑
    assert script.is_noop(boot2(db)) is True    # 再跑 no-op


# ── 3.5 环境变体 ────────────────────────────────────────────────────────────
def test_3_5a_legacy_unique_shape_merges_and_renames(tmp_path: Path, capsys: Any) -> None:
    """变体（a）：未跑 v1.4.3 的库（表级 `UNIQUE (name, type, user_id)` + 缺关联表）。

    「先删 loser 再改名」在旧形下同样成立；`budget_categories` 缺表按探测跳过。
    """
    db = tmp_path / "old-unique.db"
    seed_legacy_shape(db)

    stats = boot2(db)
    out = capsys.readouterr().out

    assert "budget_categories 表不存在（版本混跑）→ 跳过" in out
    assert "[pre-check] PRAGMA integrity_check → ok" in out
    assert "家族行清单（共 5 行" in out
    assert stats["merged_rows"] == 3            # 预设桶 2 + 用户 1 桶 1
    assert stats["keepers_normalized"] == 1     # 用户 1 的「其他支出」→「其他」
    assert stats["tail_fixed"] == 1
    assert stats["redirected_references"] == {
        "records": 3, "tags": 1, "quick_templates": 1,
    }
    assert "budget_categories" not in stats["redirected_references"]
    assert family_rows(db) == [
        (None, 3, "其他", "mdi-cash-minus", 14),
        (1, 6, "其他", "mdi-cash-minus", 11),
    ]
    # 旧形 budgets 的 category_id 行未被波及（keeper id 不变 → 预算覆盖天然延续）
    assert query(db, "SELECT id, category_id, month, amount FROM budgets ORDER BY id") == [
        (901, 3, "2026-08", 500.0), (902, 1, "2026-08", 800.0),
    ]
    assert query(db, "PRAGMA foreign_key_check") == []
    assert script.is_noop(boot2(db)) is True


def test_3_5b_missing_budget_categories_table_is_skipped(
    tmp_path: Path, capsys: Any
) -> None:
    """变体（b）：新形库但 `budget_categories` 缺表 → 探测跳过，其余照常归并。"""
    db = tmp_path / "no-link-table.db"
    seed_live_shape(db)
    conn = sqlite3.connect(db)
    conn.executescript("DROP TABLE budget_categories;")
    conn.commit()
    conn.close()
    assert "budget_categories" not in tables(db)

    stats = boot2(db)
    out = capsys.readouterr().out

    assert "budget_categories 表不存在（版本混跑）→ 跳过" in out
    assert stats["merged_rows"] == 4
    assert set(stats["redirected_references"]) == {"records", "tags", "quick_templates"}
    assert stats["deduped_references"] == {}
    assert [r[1] for r in family_rows(db)] == [
        CAT_PRESET_OTHER, CAT_A_OTHER_EXP, CAT_B_OTHER,
    ]
    # budgets 表数据不受影响（本期不碰该表）
    assert query(db, "SELECT id, user_id, name, month, amount FROM budgets ORDER BY id") == [
        (401, 1, "日常", "2026-07", 1000.0), (402, 1, "杂项", "2026-07", 200.0),
        (403, 2, "家庭", "2026-07", 500.0), (404, 1, "预设口径", "2026-07", 300.0),
    ]
    assert script.is_noop(boot2(db)) is True


def test_3_5c_empty_database_is_skipped_without_error(tmp_path: Path, capsys: Any) -> None:
    """空库（无 categories 表）：直接跳过、不报错（版本混跑安全）。"""
    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()

    stats = boot2(empty)
    out = capsys.readouterr().out

    assert script.is_noop(stats) is True
    assert "[SKIP] categories 表不存在" in out
    assert tables(empty) == set()


# ── 3.6 顺序收敛（与 migrate_to_v1.4.3.py 任意顺序互不冲突）─────────────────
def test_3_6a_boot2_after_v143_is_a_noop(tmp_path: Path, capsys: Any) -> None:
    """v1.4.3 迁移跑过之后，本脚本必然 no-op（每桶已只剩末位「其他」）。"""
    db = tmp_path / "v143-first.db"
    seed_legacy_shape(db)
    assert run_v143(db) == 0
    capsys.readouterr()

    before = snapshot(db)
    stats = boot2(db)
    out = capsys.readouterr().out

    assert script.is_noop(stats) is True, f"v1.4.3 之后仍产生写入：{stats}"
    assert "[SKIP]" in out and "no-op" in out
    assert snapshot(db) == before
    assert [r[2] for r in family_rows(db)] == ["其他", "其他"]


def test_3_6b_v143_after_boot2_converges(tmp_path: Path, capsys: Any) -> None:
    """本脚本先跑，v1.4.3 迁移照常完成（其 `_normalize_other` 见单桶单家族行自然 no-op）。"""
    db = tmp_path / "boot2-first.db"
    seed_legacy_shape(db)

    totals_before = monthly_totals(db)
    assert boot2(db)["merged_rows"] == 3
    capsys.readouterr()

    assert run_v143(db) == 0     # 其内部含「迁移后 foreign_key_check 必须零违规」自检
    assert monthly_totals(db) == totals_before, "串联不得改变按月收支合计"
    assert [r[2] for r in family_rows(db)] == ["其他", "其他"]
    assert query(db, "PRAGMA foreign_key_check") == []
    # 旧形预算行经 v1.4.3 阶段 B 转具名预算，name 取分类**当前**名（本脚本已改名）
    assert query(db, "SELECT id, name FROM budgets ORDER BY id") == [(901, "其他"),
                                                                     (902, "餐饮")]
    capsys.readouterr()
    assert script.is_noop(boot2(db)) is True, "串联之后再跑本脚本仍须 no-op"


# ── 执行面：CLI 入口与路径参数（发布窗口手法）───────────────────────────────
def test_cli_entry_point_runs_and_reports(tmp_path: Path, capsys: Any) -> None:
    db = tmp_path / "cli.db"
    seed_live_shape(db)

    assert boot2_via_cli(db) == 0
    out = capsys.readouterr().out

    assert "v1.4.3-boot2 categories migration" in out
    assert "[pre-check] 家族行清单（共 7 行，按桶）：" in out
    assert "user_id=None id=15 name='其他支出'" in out
    assert "[OK] 归并 loser 4 行" in out
    assert "重定向引用" in out and "budget_categories" in out
    assert script.is_noop(boot2(db)) is True


def test_default_target_is_the_relative_money_db_path() -> None:
    """缺省目标 = `./money.db`（纯字符串拼接；脚本自身绝不碰仓库里的 backend/money.db）。"""
    assert script._db_url(["migrate"]) == "sqlite+aiosqlite:///./money.db"
    assert script._db_url(["migrate", "H:/tmp/x.db"]) == "sqlite+aiosqlite:///H:/tmp/x.db"
    assert _SCRIPT_PATH.exists() and _SCRIPT_PATH.parent == _BACKEND
