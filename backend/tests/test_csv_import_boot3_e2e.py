"""M5 端到端真实样例回归（v1.4.3-boot3 需求 A/B/C/D/E 总验，设计 §五、任务 §1–§2）。

**本文件只做 HTTP 端到端**（`httpx.AsyncClient` 打 `/api/import/csv/preview`、
`/api/import/csv`、`/api/records`、`/api/statistics/trend`、`/api/budgets`、
`/api/export/csv`），**不重复** M1/M2/M6 的纯函数级断言：识别层的表头定位与列角色
（M1）、金额/日期/收支三态清洗（M2）、xlsx 容器读表（M6）已在各自模块单测里钉死；
本文件证明的是「用户真的能把这份文件导进来，并且从读取侧看是对的」。

样例性质登记（任务 §1，禁止把夹具当真实账单）
--------------------------------------------
1. **真实模板的逐字副本（实证）**：``backend/tests/fixtures/csv/cashew_import_template.csv``
   （M3 §5.0 建，181 B / 3 行通用英文示例值、无用户数据）。本文件**只读该可跟踪夹具**
   （路径经 ``tests.test_csv_import_export.CASHEW_TEMPLATE_FIXTURE`` 复用），
   不重复落文件、不改其内容（D21）。
2. **真实产物（实证）**：``GET /api/export/csv`` 返回的**带 UTF-8 BOM 字节**，
   直接喂 preview + confirm 验需求 D 的闭环（§2.4）。
3. **合成（表头原文真实、数据行合成）**：
   - **Cashew 全量导出形态**：设计 §0.4-10 **未逐字登记 17 列表头原文**（D21 自指落空，
     M1 已发现并登记勘误）→ 本文件**沿用 M1/M3 的 10 列合成口径**（6 角色列 + 4 丢弃列），
     列名经 ``tests.test_csv_import_export.CASHEW_EXPORT_HEADER`` 复用，
     **不凭记忆编 17 个列名**（D6 精神）。
   - **微信 / 支付宝 CSV 形态**：表头**逐字**取设计 §0.4-10 的一手调研样本原文
     （微信 11 列；支付宝 13 列含**空尾列** = 样本末尾那个多余逗号），经
     ``tests.test_csv_import_export.WECHAT_HEADER`` / ``ALIPAY_HEADER`` 复用；
     **数据行全部自造**（`¥28.16`、`不计收支`、`/` 占位等形态按样本复现）。
   - **随手记 / 京东金融 / 银行流水形态**（§1.6）：这三类**一手表头查证不到 → 不内置**
     （D6），其列名是**我方按常见导出形态自拟的合成表头、未与任何真实文件核对**；
     用例只证明「它们落到 `custom` + 用户手选列」这条路径可用（红线 7）。
4. **xlsx = 结构镜像 + 数据全合成（任务 §1.3b）**：真实微信账单 `.xlsx` 是一手实证，
   但**含用户真实交易数据、且所在目录 git 未跟踪 → 禁止入库、禁止抄其值**（红线 11），
   自动化用例**只 import 复用** M6 §4.1/§4.2 的构造器（`wechat_xlsx_bytes`、`build_xlsx`、
   `_zip_write` 与常量 `DATA_ROW_COUNT` / `DATE_TEXT` / `WECHAT_HEADERS`），本文件
   **不新建任何素材文件、不重写任何构造器**。该镜像 11 列表头逐字、前导说明含 4 条编号
   注释与单格分隔线、第 16 行整体缺失、稀疏列、serial 日期、`/` 占位，
   **数据行与金额全是合成值**。
5. **诚实口径**：本文件用例全绿只说明「上述形态在 HTTP 端到端上被正确识别、清洗、落库、
   读回」，**不构成**「用户真实账单导入成功」的证据。真实微信 `.xlsx` 的本机对照导入、
   真实支付宝账单、Excel 另存 CSV 的用户自助路径、真实 Cashew 导出文件均**留人工**
   （任务 §4.3，由主 Agent 在 P4 亲执）。

调研来源（任务 §1.5，同设计 §5.1）：微信 / 支付宝的一手表头样本出自
`WeChatPay_to_Notion` 仓库的 `wechat_raw(example).csv` 与 `alipay_raw(example).csv`、
`double-entry-generator` 的 Quick Start、BeeCount wiki（微信导入 / 支付宝账单导入）
与一篇复式记账自动化实践；Cashew 导入模板为本仓库现场样例目录实测的**逐字副本**。
**微信表头已由用户 2026-09-24 提供的一手 `.xlsx` 逐字证实**（11 列全等；前导行数与
注释条数以该文件为准修正为 17 行 / 4 条；中性交易在 `收/支` 列实测为 `/` →
§0.4-13、D31）。随手记 / 京东金融 / 各银行流水查证不到 → **不内置别名**（D6）。

其它纪律：现场库文件全程只读，用例一律走 conftest 的内存引擎（§2.8）；
**不引用本机未跟踪的现场样例目录路径**（红线 11）；§2.10 的前后端契约一致性
**只读**前端 `.vue` / `.js` 源码文本（不改前端任何文件、不引前端依赖）。

v1.4.4 三条用户新裁定对本文件的同步改写（V1 日期 / V2 角色 / V3 分类兜底）：
  * §2.2 微信用例的口径**反转**（`交易类型` 现为分类列、未选归入时挂「其他」而非丢行）；
  * §2.3 脏值夹具的斜杠日两例改写（无歧义者入库、真歧义者仍 `invalid_date`），
    另新增 `test_v1_4_4_unambiguous_slash_dates_import_and_ambiguous_still_skip`；
  * §2.2 支付宝 / §2.5 / §2.9.1 的 `note` 期望值改为「交易对方 · 商品」拼接形式。
"""

import ast
import csv
import io
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.schemas.import_ import ImportCsvRequest
from app.schemas.record import RecordCreate
from app.services import xlsx_reader
from app.services.csv_dialects import ROLES
from app.utils.response import Code
from tests.test_csv_import_export import (
    ALIPAY_HEADER,
    CASHEW_EXPORT_HEADER,
    CASHEW_TEMPLATE_FIXTURE,
    WECHAT_HEADER,
)
from tests.test_xlsx_reader import (
    DATA_ROW_COUNT,
    DATE_TEXT,
    WECHAT_HEADERS,
    _zip_write,
    build_xlsx,
    wechat_xlsx_bytes,
)

# ── 复用上游交付件（本文件不重写素材）────────────────────────────────
#
# CSV 侧：表头原文与夹具路径来自 M3 的 `test_csv_import_export.py`；
# xlsx 侧：合成构造器来自 M6 的 `test_xlsx_reader.py`。
# `import tests.test_*` 只**取常量 / 函数对象**——pytest 按文件路径收集，这两个模块
# 作为普通模块被 import 后进入 `sys.modules`，**不会重复执行其中任何用例**。

SKIPPED_REASON_KEYS = {
    "invalid_amount",
    "invalid_date",
    "type_ignored",
    "type_unresolved",
    "category_unresolved",
}


def schema_pattern(model: type[Any], field: str) -> str:
    """取 Pydantic 字段上 `pattern=` 的字面正则（pydantic v2 把它放进 metadata）。"""
    for meta in model.model_fields[field].metadata:  # type: ignore[index]
        pattern = getattr(meta, "pattern", None)
        if pattern:
            return str(pattern)
    raise AssertionError(f"{model.__name__}.{field} 上找不到 pattern 约束，契约已漂移")


CONSUME_TIME_PATTERN = schema_pattern(RecordCreate, "consume_time")
"""`consume_time` 的合法形制**直接取 `schemas/record.py` 的权威正则**（§2.3.4），
不在本文件重抄一遍——两条路径一旦漂移即红（M2 §2.4 同口径）。"""


def pattern_enum(pattern: str) -> set[str]:
    """`^(a|b|c)$` → `{"a","b","c"}`（封闭枚举两侧逐字对照用）。"""
    body = pattern.strip("^$")
    assert body.startswith("(") and body.endswith(")"), pattern
    return set(body[1:-1].split("|"))


# ── HTTP 手法（参考 M3 的 `test_csv_import_export.py`，本文件自建薄壳）──


async def preview_raw(auth_client: AsyncClient, raw: bytes, filename: str = "e2e.csv") -> Response:
    """上传预览，返回**原始 Response**（§2.4 / §2.9.4 需要整份响应文本做反向护栏）。"""
    return await auth_client.post(
        "/api/import/csv/preview",
        files={"file": (filename, raw, "application/octet-stream")},
    )


async def preview_data(auth_client: AsyncClient, raw: bytes, filename: str = "e2e.csv") -> dict[str, Any]:
    """预览并返回 `data`；**预览必须成功**（需求 A：不再整文件拒绝）。"""
    body = (await preview_raw(auth_client, raw, filename)).json()
    assert body["code"] == Code.SUCCESS, body["message"]
    return body["data"]


async def confirm(auth_client: AsyncClient, cache_id: str, format_: str, **extra: Any) -> dict[str, Any]:
    """确认导入，返回整个响应体（含 `code`/`message`/`data`）。"""
    resp = await auth_client.post(
        "/api/import/csv",
        json={
            "cache_id": cache_id,
            "format": format_,
            "category_mapping": {},
            "tag_mapping": {},
            **extra,
        },
    )
    return resp.json()


async def preview_and_confirm(
    auth_client: AsyncClient, raw: bytes, format_: str, filename: str = "e2e.csv", **extra: Any
) -> dict[str, Any]:
    """一步到位：预览 + 确认，返回确认响应体。"""
    data = await preview_data(auth_client, raw, filename)
    return await confirm(auth_client, data["cache_id"], format_, **extra)


async def records(auth_client: AsyncClient, **params: Any) -> list[dict[str, Any]]:
    body = (await auth_client.get("/api/records", params={"page_size": 100, **params})).json()
    return body["data"]["items"]


async def tags_of(auth_client: AsyncClient) -> list[dict[str, Any]]:
    return (await auth_client.get("/api/tags")).json()["data"]


async def tag_names(auth_client: AsyncClient) -> list[str]:
    return sorted(t["name"] for t in await tags_of(auth_client))


async def categories_of(auth_client: AsyncClient) -> list[dict[str, Any]]:
    return (await auth_client.get("/api/categories")).json()["data"]


async def category_id_by_name(auth_client: AsyncClient, name: str) -> int:
    return next(c["id"] for c in await categories_of(auth_client) if c["name"] == name)


async def new_category(auth_client: AsyncClient, name: str) -> int:
    resp = await auth_client.post(
        "/api/categories",
        json={"name": name, "type": "expense", "icon": "mdi-circle", "sort_order": 9},
    )
    return resp.json()["data"]["id"]


def tag_id_of(record: dict[str, Any]) -> int | None:
    """`/api/records` 列表项里标签是富化对象 `tag`（**没有**裸 `tag_id` 字段）。"""
    return record["tag"]["id"] if record["tag"] else None


def as_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def data_row_count_of(raw: str) -> int:
    """合成夹具的**数据行数**（去掉表头行；本文件的行尾恒为 `\\n`、无尾随空行）。"""
    return len(raw.strip("\n").splitlines()) - 1


# ══════════════════════════════════════════════════════════════════
#  §1.6 不内置的来源：一律走 `custom` + 用户手选列（D6 / 红线 7）
# ══════════════════════════════════════════════════════════════════

# 列名系**我方自拟的合成形态**（这三类一手表头查证不到，故不内置别名）。
# 用例证明的是「手选列这条路径可用」，不是「这些文件真长这样」。
UNBUILT_SOURCE_SHAPES: list[dict[str, Any]] = [
    {
        "name": "随手记形态（收入/支出拆成两列）",
        "raw": (
            "交易时间,交易类型,收入,支出,备注,分类\n"
            "2024-09-05 09:00:00,餐饮,0.00,35.00,楼下面馆,吃饭\n"
            "2024-09-06 20:30:00,娱乐,0.00,12.00,电影票,观影"
        ),
        "columns": {"consume_time": 0, "amount": 3},
        "type_source": "all_expense",
        "amounts": [35.0, 12.0],
        "types": ["expense", "expense"],
    },
    {
        "name": "京东金融形态（全列无别名）",
        "raw": (
            "完成时间,款项说明,收入金额,支出金额,账户\n"
            "2024-09-07 10:00,理财赎回,88.88,0.00,银行卡\n"
            "2024-09-08 11:00,红包提现,6.60,0.00,零钱"
        ),
        "columns": {"consume_time": 0, "amount": 2, "note": 1},
        "type_source": "all_income",
        "amounts": [88.88, 6.6],
        "types": ["income", "income"],
    },
    {
        "name": "银行流水形态（借贷分列）",
        "raw": (
            "日期,摘要,借方发生额,贷方发生额,余额\n"
            "2024/09/09 08:30,代发工资,0.00,5000.00,25000.00\n"
            "2024-09-10 09:00,跨行转入,0.00,300.00,25300.00"
        ),
        "columns": {"consume_time": 0, "amount": 3, "note": 1},
        "type_source": "all_income",
        "amounts": [5000.0, 300.0],
        "types": ["income", "income"],
    },
]


async def test_1_6_unbuilt_sources_fall_to_custom_and_import_by_manual_columns(
    auth_client: AsyncClient,
) -> None:
    """§1.6：随手记 / 京东金融 / 银行流水**不内置**（D6）→ `custom` + 手选列仍可用。

    同时钉住两件坏事：① 它们**不得**被判成任何内置方言（别名表被擅自扩键即红）；
    ② 它们**不再**被整文件拒绝（需求 A 的原点，「无法识别」不再出现）。
    """
    cat_id = await new_category(auth_client, "手选路径归入")
    for shape in UNBUILT_SOURCE_SHAPES:
        raw_text = str(shape["raw"])
        before = {r["id"] for r in await records(auth_client)}
        data = await preview_data(auth_client, as_bytes(raw_text))
        assert data["format"] == "custom", f"{shape['name']}：该形态不得内置（D6）"
        assert data["headers"] == raw_text.splitlines()[0].split(",")
        assert data["container"] == "csv"
        auto_amounts = [col for col in data["columns"] if col["role"] == "amount"]
        assert auto_amounts == [], f"{shape['name']}：未登记的列名不该自动拿到 amount 角色"

        body = await confirm(
            auth_client,
            data["cache_id"],
            "custom",
            columns=shape["columns"],
            type_source=shape["type_source"],
            fallback_category={"action": "map", "target_id": cat_id},
        )
        assert body["code"] == Code.SUCCESS, (shape["name"], body["message"])
        assert body["data"]["imported_count"] == data_row_count_of(raw_text), shape["name"]

        fresh = sorted(
            (r for r in await records(auth_client) if r["id"] not in before),
            key=lambda r: str(r["consume_time"]),
        )
        assert len(fresh) == data_row_count_of(raw_text), shape["name"]
        assert [r["amount"] for r in fresh] == shape["amounts"], shape["name"]
        assert [r["type"] for r in fresh] == shape["types"], shape["name"]
        assert all(r["category_id"] == cat_id for r in fresh)
        assert "无法识别" not in str(body)


# ══════════════════════════════════════════════════════════════════
#  §2.1 需求 A：任意表头 / 无表头都能进预览并由用户手选列角色
# ══════════════════════════════════════════════════════════════════


async def test_2_1_headerless_three_column_file_imports_after_manual_columns(
    auth_client: AsyncClient,
) -> None:
    """§2.1 无表头型（`1,2,3` 三列 + 数据行）→ 手选 `columns` → 成功入库。

    D2 的退化判据把「第一个非空单元格 ≥2 的行」当表头 → `1,2,3` 这行成了表头、
    全列 `role=None`；`warnings` 必须**提前**告知必需列缺失（预览不拒、确认才拒）。
    """
    raw = as_bytes(
        "1,2,3\n"
        "2024-06-01 10:00,-35.5,楼下超市\n"
        "2024-06-02 11:00,120.00,工资补发"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "custom"
    assert data["headers"] == ["1", "2", "3"]
    assert [col["role"] for col in data["columns"]] == [None, None, None]
    assert data["suggested_type_source"] == "sign", "custom 无收支列 → 默认符号法（D10）"
    assert data["row_count"] == 2
    assert any("缺少必需列" in warning for warning in data["warnings"]), data["warnings"]

    # 不发 `columns` 时被显式拒绝：中文 `ValueError` → `PARAM_ERROR`（不依赖 FastAPI 422）
    rejected = await confirm(auth_client, data["cache_id"], "custom")
    assert rejected["code"] == Code.PARAM_ERROR
    assert "必需列" in rejected["message"]

    cat_id = await new_category(auth_client, "无表头归入")
    data = await preview_data(auth_client, raw)
    body = await confirm(
        auth_client,
        data["cache_id"],
        "custom",
        columns={"consume_time": 0, "amount": 1, "note": 2},
        type_source="sign",
        fallback_category={"action": "map", "target_id": cat_id},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2

    rows = sorted(await records(auth_client), key=lambda r: r["consume_time"])
    assert [(r["amount"], r["type"], r["note"]) for r in rows] == [
        (35.5, "expense", "楼下超市"),
        (120.0, "income", "工资补发"),
    ]
    assert [r["consume_time"] for r in rows] == ["2024-06-01 10:00", "2024-06-02 11:00"]
    assert all(r["category_id"] == cat_id for r in rows)


async def test_2_1_arbitrary_chinese_header_imports_after_manual_columns(
    auth_client: AsyncClient,
) -> None:
    """§2.1 任意中文表头（`日期,花费,说明`）→ 手选 `columns` → 成功入库。

    `日期` 在别名表内、`花费`/`说明` **故意不登记**（不属任何内置方言）→ `custom`；
    用户手选后按角色落库，负数在 `sign` 下归支出、正数归收入（D10）。
    """
    raw = as_bytes(
        "日期,花费,说明\n"
        "2024/06/03 09:15,-18.80,打车去高铁站\n"
        "2024/06/04 19:40,66.00,同事还钱"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "custom"
    assert data["headers"] == ["日期", "花费", "说明"]
    by_header = {col["header"]: col["role"] for col in data["columns"]}
    assert by_header == {"日期": "consume_time", "花费": None, "说明": None}, (
        "只有登记过的别名才自动落位（D6）"
    )

    cat_id = await new_category(auth_client, "中文表头归入")
    body = await confirm(
        auth_client,
        data["cache_id"],
        "custom",
        columns={"consume_time": 0, "amount": 1, "note": 2},
        type_source="sign",
        fallback_category={"action": "map", "target_id": cat_id},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2

    rows = sorted(await records(auth_client), key=lambda r: r["consume_time"])
    assert [(r["amount"], r["type"], r["note"]) for r in rows] == [
        (18.8, "expense", "打车去高铁站"),
        (66.0, "income", "同事还钱"),
    ]


# ══════════════════════════════════════════════════════════════════
#  §2.2 需求 B：五方言逐一命中且入库结果符合该方言预设
# ══════════════════════════════════════════════════════════════════


async def test_2_2_native_dialect_roles_follow_headers_not_positions(
    auth_client: AsyncClient,
) -> None:
    """§2.2 native：同名映射 + **列序打乱也不错位**（D16 收口的现存隐患）。

    旧实现按位置 0..5 取值、完全不看表头 → 本用例把六列改名换序，若仍按位置读，
    `note` 会被当成 `amount`、整行报废。不发 `columns`，走后端推导路径（D18）。
    """
    raw = as_bytes(
        "note,consume_time,tag_name,amount,type,category_name\n"
        "原生乱序测试,2024-10-01 12:00,午餐,50.0,expense,餐饮"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "native"
    assert [col["role"] for col in data["columns"]] == [
        "note",
        "consume_time",
        "tag",
        "amount",
        "type",
        "category",
    ], "六列按**表头名**落位，与列序无关"

    body = await confirm(
        auth_client,
        data["cache_id"],
        "native",
        category_mapping={"餐饮": {"action": "create"}},
        tag_mapping={"午餐": {"action": "create", "category_id": None}},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 1

    rows = await records(auth_client)
    assert len(rows) == 1
    assert (rows[0]["amount"], rows[0]["type"]) == (50.0, "expense")
    assert rows[0]["consume_time"] == "2024-10-01 12:00"
    assert rows[0]["note"] == "原生乱序测试"
    assert rows[0]["tag"]["name"] == "午餐"


async def test_2_2_cashew_dialect_boolean_income_and_negative_amount(
    auth_client: AsyncClient,
) -> None:
    """§2.2 cashew：`income` 布尔列 + 负数金额（§1.3 **合成**形态，列集沿用 M1/M3 的 10 列口径）。

    `income` 既是列名别名（→ `type` 角色）也是值域（`true`/`false` → 收/支，D11）；
    入库金额一律 `abs()` 后两位小数（D13），收支方向只由 `type` 承载。
    """
    raw = as_bytes(
        CASHEW_EXPORT_HEADER + "\n"
        "午餐,餐饮,-50.00,false,测试,2024-09-01 12:00:00.000,子分类,账户,人民币,钱包\n"
        "工资,收入,1200.5,true,月薪,2024-09-02 09:05:00.123,,人民币,"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "cashew"
    assert data["suggested_type_source"] == "column"
    assert data["headers"] == CASHEW_EXPORT_HEADER.split(",")

    body = await preview_and_confirm(
        auth_client,
        raw,
        "cashew",
        category_mapping={"餐饮": {"action": "create"}, "收入": {"action": "create"}},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2

    rows = sorted(await records(auth_client), key=lambda r: r["consume_time"])
    assert [(r["amount"], r["type"]) for r in rows] == [(50.0, "expense"), (1200.5, "income")]


async def test_2_2_cashew_template_dialect_uses_sign_preset_on_real_fixture_copy(
    auth_client: AsyncClient,
) -> None:
    """§2.2 cashew_template：**真实模板逐字副本**（§1.1 夹具）+ 符号法收支（D10）。

    冒烟②的自动化版本：`-50` 落支出、`250` 落收入。夹具只读、内容不重抄、
    不引用任何未跟踪的现场样例目录（D21 / 红线 11）。
    """
    raw = CASHEW_TEMPLATE_FIXTURE.read_bytes()
    assert raw.splitlines()[0] == b"Date,Amount,Category,Title,Note,Account", "逐字副本在场"
    data = await preview_data(auth_client, raw, CASHEW_TEMPLATE_FIXTURE.name)
    assert data["format"] == "cashew_template"
    assert data["suggested_type_source"] == "sign"
    assert data["header_row_index"] == 0, "模板无前导说明行（§1.1）"
    assert data["row_count"] == 2

    body = await confirm(
        auth_client,
        data["cache_id"],
        "cashew_template",
        category_mapping={"Groceries": {"action": "create"}, "Bills & Fees": {"action": "create"}},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2

    rows = sorted(await records(auth_client), key=lambda r: r["amount"])
    assert [(r["amount"], r["type"]) for r in rows] == [(50.0, "expense"), (250.0, "income")]


async def test_2_2_alipay_dialect_auto_maps_transaction_category(
    auth_client: AsyncClient,
) -> None:
    """§2.2 alipay：`交易分类` 自动落 `category` 角色（D9），空尾列天然丢弃（数据行**合成**）。

    表头逐字取设计 §0.4-10（末尾那个多余逗号 = **第 13 个空列**）；
    D5 的顺序在此可见：同一份表头**必须**判 `alipay` 而非 `wechat`（超集关系）。
    """
    raw = as_bytes(
        ALIPAY_HEADER + "\n"
        "2024-04-05 10:00:00,餐饮美食,某餐馆,a***@b.com,午餐,支出,45.90,余额宝,交易成功,P0001,MP0001,/,\n"
        "2024-04-06 08:20:00,交通出行,某出行,a***@b.com,打车,支出,6.90,余额宝,交易成功,P0002,MP0002,/,\n"
        "2024-04-07 09:00:00,文化休闲,某平台,a***@b.com,会员,不计收支,0.00,余额宝,交易关闭,P0003,MP0003,/,"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "alipay", "支付宝表头不得被判成微信（D5）"
    assert data["headers"][-1] == "", "样本末尾的多余逗号 = 第 13 个空列"
    assert data["columns"][-1]["role"] is None
    assert sorted(data["categories_in_file"]) == ["交通出行", "文化休闲", "餐饮美食"]

    food_id = await new_category(auth_client, "餐饮美食")
    taxi_id = await new_category(auth_client, "交通出行")
    body = await confirm(
        auth_client,
        data["cache_id"],
        "alipay",
        category_mapping={
            "餐饮美食": {"action": "map", "target_id": food_id},
            "交通出行": {"action": "map", "target_id": taxi_id},
        },
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2
    assert body["data"]["skipped_reasons"]["type_ignored"] == 1

    rows = {r["note"]: r for r in await records(auth_client)}
    assert rows["某餐馆·午餐"]["category_id"] == food_id, "交易分类列自动落位到同名分类"
    assert rows["某出行·打车"]["category_id"] == taxi_id
    assert rows["某餐馆·午餐"]["amount"] == 45.9
    assert rows["某出行·打车"]["amount"] == 6.9, "裸数字 6.90 → 两位小数（D13）"


async def test_2_2_wechat_dialect_has_no_category_column_and_needs_fallback(
    auth_client: AsyncClient,
) -> None:
    """§2.2 wechat：**v1.4.4 V2/V3 翻案后本用例的口径已反转**（用例名保留、断言已改写）。

    旧事实（boot3 D8/D9）：微信全表无分类列（`交易类型` 故意不登记）→ 不发
    `fallback_category` 时整表计 `category_unresolved`、0 行入库。
    新事实（V2）：`交易类型` 登记为 `category` → 微信**有**分类列、「未识别到分类列」告警
    消失；（V3）不发 `fallback_category` 时「零钱支付」自动匹配落空 → 挂「其他」并入库。
    另钉 V2 的备注：`交易对方` + `商品` 拼一条、不建标签。表头 11 列逐字 §0.4-10、
    数据行**合成**。
    """
    raw = as_bytes(
        WECHAT_HEADER + "\n"
        "2024-04-01 09:15:00,零钱支付,某便利店,早餐,支出,¥12.50,零钱,支付成功,T0001,/,"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "wechat"
    assert "未识别到分类列：需指定默认分类" not in data["warnings"], "V2：微信已有分类列"
    roles = {col["header"]: col["role"] for col in data["columns"]}
    assert roles["交易类型"] == "category", "V2：微信分类来源 = 交易类型"
    assert roles["交易对方"] == "note", "V2：交易对方进备注、不再建标签"
    assert roles["商品"] == "note"
    assert data["categories_in_file"] == ["零钱支付"]

    first = await confirm(auth_client, data["cache_id"], "wechat")
    assert first["code"] == Code.SUCCESS, first["message"]
    assert first["data"]["imported_count"] == 1, "V3：分类落空的行不再被丢弃"
    assert first["data"]["skipped_reasons"]["category_unresolved"] == 0
    assert await tag_names(auth_client) == [], "V2：真实微信账单不再产生标签"

    other_id = await category_id_by_name(auth_client, "其他")
    rows = await records(auth_client)
    assert rows[0]["category_id"] == other_id, "自动匹配落空 → 挂「其他」"
    assert rows[0]["note"] == "某便利店·早餐", "V2：两列备注拼一条"
    assert rows[0]["amount"] == 12.5

    cat_id = await new_category(auth_client, "账单归入")
    data = await preview_data(auth_client, raw)
    body = await confirm(
        auth_client,
        data["cache_id"],
        "wechat",
        fallback_category={"action": "map", "target_id": cat_id},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 1
    fresh = [r for r in await records(auth_client) if r["id"] not in {row["id"] for row in rows}]
    assert [r["category_id"] for r in fresh] == [cat_id], "显式归入仍优先于自动匹配"


# ══════════════════════════════════════════════════════════════════
#  §2.3 需求 C 净效果：**从读取侧**证明脏值清洗真的贯通
# ══════════════════════════════════════════════════════════════════

DIRTY_HEADER = "amount,type,category_name,tag_name,consume_time,note"
DIRTY_CATEGORY = "脏值归一"
DIRTY_MONTH = "2024-05"

# (金额原值, 收支原值, 日期原值, note, 是否入库)；全部为**合成行**，形态逐条取自
# 设计 §2.3 的边界表 + v1.4.4 V1 的斜杠日两例（无歧义 → 采用、真歧义 → 照旧不猜）。
# 期望聚合数写死在下面，供 §2.3.2 / §2.3.3 做**读取侧**对照。
DIRTY_ROWS: list[tuple[str, str, str, str, bool]] = [
    ('"¥1,234.50"', "expense", "2024/05/10 08:30:00", "货币符号与千分位", True),
    ("12.00元", "支出", "2024年5月11日 9:05", "中文日期与单位", True),
    ("(20.00)", "expense", "2024-05-12T10:00:00", "括号负数与 T 分隔", True),
    ("１２．５", "income", "2024-05-13 07:00:00.123", "全角数字与毫秒", True),
    ("50.00", "expense", "2024-05-14~2024-05-14 09:00:00", "时间区间取前段", True),
    ("60.00", "expense", "2024-05-15", "仅日期补 00:00", True),
    # v1.4.4 V1：日位 24 只有一种解释合法 → 采用（仍落在 DIRTY_MONTH 这个月桶里）
    ("70.00", "expense", "05/24/2024", "斜杠日无歧义则采用（V1）", True),
    # 月/日两读皆合法（05-06 与 06-05）→ 真歧义，照旧不猜
    ("80.00", "expense", "05/06/2024", "斜杠日真歧义不猜（V1 另一半）", False),
    ("/", "expense", "2024-05-16 08:00", "占位金额不猜", False),
    ("90.00", "expense", "1727147274", "纯数字时间戳不猜（D15）", False),
]
DIRTY_KEPT_NOTES = sorted(note for _amount, _type, _time, note, kept in DIRTY_ROWS if kept)
DIRTY_KEPT_COUNT = len(DIRTY_KEPT_NOTES)
DIRTY_EXPECTED_EXPENSE = 1234.5 + 12.0 + 20.0 + 50.0 + 60.0 + 70.0
DIRTY_EXPECTED_INCOME = 12.5


def dirty_csv() -> bytes:
    """脏形态夹具（native 六列表头，不内置任何新方言）。"""
    return as_bytes(
        "\n".join(
            [DIRTY_HEADER]
            + [
                f"{amount},{type_},{DIRTY_CATEGORY},,{consume_time},{note}"
                for amount, type_, consume_time, note, _kept in DIRTY_ROWS
            ]
        )
    )


async def import_dirty_rows(auth_client: AsyncClient) -> dict[str, Any]:
    """导入脏值夹具并返回确认响应体（每用例一份全新内存库，互不干扰）。"""
    body = await preview_and_confirm(
        auth_client,
        dirty_csv(),
        "native",
        category_mapping={DIRTY_CATEGORY: {"action": "create"}},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    return body


async def test_2_3_1_records_month_filter_finds_rows_written_from_dirty_dates(
    auth_client: AsyncClient,
) -> None:
    """§2.3.1：`GET /api/records` 按 `start_date/end_date` 的月份过滤**能命中**这些记录。

    `record_service` 的区间比较是**纯字符串**比较 → 脏日期必然出圈：
    `2024/05/10 08:30:00` 的 `/`(U+002F) 与 `2024年5月11日 9:05` 的 `年`(U+5E74)
    都**大于** `-`(U+002D) → 旧实现里它们落在 `end_date` 之外。
    本用例即「清洗真的发生」的读取侧证据。
    """
    body = await import_dirty_rows(auth_client)
    assert body["data"]["imported_count"] == DIRTY_KEPT_COUNT
    assert body["data"]["skipped_reasons"] == {
        "invalid_amount": 1,
        "invalid_date": 2,
        "type_ignored": 0,
        "type_unresolved": 0,
        "category_unresolved": 0,
    }, "五键恒在、缺省 0（D12）"

    hits = await records(auth_client, start_date=f"{DIRTY_MONTH}-01", end_date=f"{DIRTY_MONTH}-31")
    assert len(hits) == DIRTY_KEPT_COUNT, "七行脏形态全部落进 2024-05 的区间（含 V1 的无歧义斜杠日）"
    assert sorted(r["note"] for r in hits) == DIRTY_KEPT_NOTES
    assert await records(auth_client, start_date="2024-06-01", end_date="2024-06-30") == [], (
        "过滤不是恒真：换个月份必须落空"
    )


async def test_2_3_2_trend_month_keys_are_legal_and_amounts_bucketed(auth_client: AsyncClient) -> None:
    """§2.3.2：月份趋势的月份键为合法 `YYYY-MM` 且金额进桶。

    `statistics_service` 用 `strftime('%Y-%m', consume_time)`：非 `YYYY-MM-DD …` 的文本
    经 `strftime` 得 **NULL** → 旧实现会在趋势里出现 `null` 月份键（图上凭空一点）。
    注：任务 §2.3.2 写的 `granularity=month` 在本仓库该端点上的实参名是 `group_by=month`
    （`routers/statistics.py`，本批未新增端点，红线 5）——同一处读取路径，无歧义。
    """
    await import_dirty_rows(auth_client)
    resp = await auth_client.get(
        "/api/statistics/trend",
        params={"group_by": "month", "start_date": f"{DIRTY_MONTH}-01", "end_date": f"{DIRTY_MONTH}-31"},
    )
    body = resp.json()
    assert body["code"] == Code.SUCCESS, body["message"]
    items = body["data"]["items"]
    assert len(items) == 1, items
    periods = [item["period"] for item in items]
    assert all(re.fullmatch(r"\d{4}-\d{2}", str(period)) for period in periods), periods
    assert periods == [DIRTY_MONTH]
    assert items[0]["expense"] == DIRTY_EXPECTED_EXPENSE
    assert items[0]["income"] == DIRTY_EXPECTED_INCOME
    assert items[0]["balance"] == round(DIRTY_EXPECTED_INCOME - DIRTY_EXPECTED_EXPENSE, 2)


async def test_2_3_3_budget_spent_counts_normalized_rows(auth_client: AsyncClient) -> None:
    """§2.3.3：`GET /api/budgets` 当月预算的 `spent` 含这些记录。

    `budget_service` 的谓词是 `substr(consume_time,1,7)` 同源的字符串区间 +
    `type='expense'` → 未归一的日期、未取 `abs()` 的符号都会让 `spent` 失真。
    """
    await import_dirty_rows(auth_client)
    cat_id = await category_id_by_name(auth_client, DIRTY_CATEGORY)
    created = await auth_client.post(
        "/api/budgets",
        json={
            "month": DIRTY_MONTH,
            "name": "脏值归一月预算",
            "amount": 5000.0,
            "scope_mode": "include",
            "category_ids": [cat_id],
        },
    )
    assert created.json()["code"] == Code.SUCCESS, created.json()

    budgets = (await auth_client.get("/api/budgets", params={"month": DIRTY_MONTH})).json()["data"]
    mine = [b for b in budgets if b["name"] == "脏值归一月预算"]
    assert len(mine) == 1
    assert mine[0]["spent"] == DIRTY_EXPECTED_EXPENSE, "括号负数取 abs 后仍按支出累加（D13）"
    assert mine[0]["remaining"] == round(5000.0 - DIRTY_EXPECTED_EXPENSE, 2)


async def test_2_3_4_every_stored_consume_time_is_canonical(auth_client: AsyncClient) -> None:
    """§2.3.4：库内 `consume_time` **全部**满足 `^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}$`。

    正则从 `RecordCreate` 的字段约束取（同一权威源，防两条路径漂移）。
    本批之前的现状是脏日期可原样入库（设计 §0.4-3），现在脏形态要么被归一、
    要么**整行跳过并计数**（D14/D15），没有第三种下场。
    本用例把 native / cashew / 微信 CSV / 微信 xlsx **四类夹具同时导入**后做全量扫描。
    """
    dirty_body = await import_dirty_rows(auth_client)
    cashew_body = await preview_and_confirm(
        auth_client,
        as_bytes(
            CASHEW_EXPORT_HEADER + "\n"
            "夜宵,餐饮,-9.9,false,烧烤,2024-05-20 23:59:59.999999,,人民币,,"
        ),
        "cashew",
        category_mapping={"餐饮": {"action": "create"}},
    )
    cat_id = await new_category(auth_client, "账单归入")
    wechat_body = await preview_and_confirm(
        auth_client,
        as_bytes(
            WECHAT_HEADER + "\n"
            "2024-05-21 07:30:00,零钱支付,甲店,豆浆,支出,¥3.50,零钱,支付成功,T1001,/,"
        ),
        "wechat",
        fallback_category={"action": "map", "target_id": cat_id},
    )
    xlsx_preview = await preview_data(auth_client, wechat_xlsx_bytes(), "wechat.xlsx")
    xlsx_body = await confirm(
        auth_client,
        xlsx_preview["cache_id"],
        "wechat",
        fallback_category={"action": "map", "target_id": cat_id},
    )

    assert dirty_body["data"]["imported_count"] == DIRTY_KEPT_COUNT, dirty_body["data"]
    assert cashew_body["data"]["imported_count"] == 1, cashew_body["data"]
    assert wechat_body["data"]["imported_count"] == 1, wechat_body["data"]
    assert xlsx_body["data"]["imported_count"] == DATA_ROW_COUNT - 1, xlsx_body["data"]

    rows = await records(auth_client)
    expected_total = DIRTY_KEPT_COUNT + 1 + 1 + (DATA_ROW_COUNT - 1)
    assert len(rows) == expected_total, f"四类夹具应各按其预设落库：{len(rows)} != {expected_total}"
    bad = [r["consume_time"] for r in rows if not re.fullmatch(CONSUME_TIME_PATTERN, r["consume_time"] or "")]
    assert bad == [], f"入库侧净效果被破坏（D14）：{bad}"
    assert "2024-05-20 23:59" in {r["consume_time"] for r in rows}, "6 位微秒走 %f 而非按 `.` 截断（D14）"
    assert DATE_TEXT[:16] in {r["consume_time"] for r in rows}, "xlsx serial 日期同样落在合法形制内（D24）"


# ══════════════════════════════════════════════════════════════════
#  §2.4 需求 D：自家导出 → 自家导入闭环（真实产物字节）
# ══════════════════════════════════════════════════════════════════


def row_signature(rows: Iterable[dict[str, Any]], names: dict[int, str]) -> set[tuple[Any, ...]]:
    """记录 → 可比指纹；分类与标签一律按**名字**比（导出前后 id 不同属正常）。

    两种来源同形化：`/api/records` 的列表项是富化对象 `category_id` + `tag`，
    而 `export_csv` 的行是裸名字 `category_name` + `tag_name`。
    """
    result = set()
    for row in rows:
        category_name = row.get("category_name")
        if category_name is None:
            category_name = names.get(row["category_id"], "")
        tag_name = row.get("tag_name")
        if tag_name is None:
            tag_name = (row.get("tag") or {}).get("name") or ""
        result.add(
            (
                round(float(row["amount"]), 2),
                row["type"],
                category_name,
                tag_name,
                row["consume_time"],
                row.get("note") or "",
            )
        )
    return result


async def test_2_4_own_export_reimports_without_any_unknown_format_message(
    auth_client: AsyncClient,
) -> None:
    """§2.4：`export_csv` 的**真实带 BOM 字节**直接喂 preview + confirm ——
    条数一致、金额/日期/分类名逐条一致，且全流程响应里**不出现**「无法识别」文案。

    旧实现：`export_csv` 写 BOM、`detect_and_decode` 用 `utf-8` 解码 → BOM 粘上首列表头
    成 `\\ufeffamount`（`\\ufeff`.isspace() 为 False、`strip()` 去不掉）→
    自家导出回导必报「无法识别的 CSV 格式」（需求 D 的成因，§0.4-2）。
    """
    food_id = await new_category(auth_client, "外食")
    salary_id = await new_category(auth_client, "工资")
    tag_id = (
        await auth_client.post("/api/tags", json={"name": "火锅", "category_id": food_id})
    ).json()["data"]["id"]

    originals = [
        {"amount": 120.5, "type": "expense", "category_id": food_id, "tag_id": tag_id, "consume_time": "2024-07-01 19:00", "note": "麻辣锅底"},
        {"amount": 88.0, "type": "expense", "category_id": food_id, "tag_id": None, "consume_time": "2024-07-15 09:30", "note": "便利店便当"},
        {"amount": 5000.0, "type": "income", "category_id": salary_id, "tag_id": None, "consume_time": "2024-07-20 10:00", "note": "七月月薪"},
    ]
    for payload in originals:
        resp = await auth_client.post("/api/records", json=payload)
        assert resp.status_code == 200, resp.text

    exported = await auth_client.get("/api/export/csv")
    assert exported.status_code == 200
    raw = exported.content
    assert raw[:3] == b"\xef\xbb\xbf", "真实产物：UTF-8 BOM 在场（需求 D 的成因）"
    assert "无法识别" not in exported.text

    exported_rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    assert len(exported_rows) == 3

    preview_resp = await preview_raw(auth_client, raw, "money_export.csv")
    assert "无法识别" not in preview_resp.text
    data = preview_resp.json()["data"]
    assert data["format"] == "native", "带 BOM 的自家导出必须判回 native"
    assert data["encoding"] == "utf-8-sig"
    assert data["container"] == "csv"
    assert data["row_count"] == len(exported_rows)

    before = {r["id"] for r in await records(auth_client)}
    confirm_resp = await auth_client.post(
        "/api/import/csv",
        json={
            "cache_id": data["cache_id"],
            "format": "native",
            # D18 的另一半：显式发 null 也必须接得住（旧前端根本不发这三个字段）
            "columns": None,
            "type_source": None,
            "fallback_category": None,
            "category_mapping": {"外食": {"action": "create"}, "工资": {"action": "create"}},
            "tag_mapping": {"火锅": {"action": "create", "category_id": None}},
        },
    )
    assert "无法识别" not in confirm_resp.text
    body = confirm_resp.json()
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == len(exported_rows), "导出几行就导回几行"
    assert body["data"]["skipped_count"] == 0

    names = {c["id"]: c["name"] for c in await categories_of(auth_client)}
    fresh = [r for r in await records(auth_client) if r["id"] not in before]
    assert len(fresh) == len(exported_rows)
    assert row_signature(fresh, names) == row_signature(exported_rows, names), (
        "金额 / 日期 / 分类名 / 标签 / 备注逐条一致"
    )


# ══════════════════════════════════════════════════════════════════
#  §2.5 三态收支净效果（微信 CSV 合成夹具）
# ══════════════════════════════════════════════════════════════════


async def test_2_5_type_column_three_states_skip_counts_match_fixture(auth_client: AsyncClient) -> None:
    """§2.5：`不计收支` / `中性交易` / **一手实测的 `/`**（D31）三种中性行都不入库、
    且**全部**计入 `type_ignored`；`支出` / `收入` 各归位。

    `/` 不得落进 `type_unresolved`——结果同为跳过，但原因标签失真是 D31 要防的
    （一手真实文件的 `收/支` 取值分布为 支出 / 收入 / `/`，且 `/` 的笔数与该文件自述的
    「中性交易：N 笔」逐一对齐）。本用例数据行为**合成**。
    """
    cat_id = await new_category(auth_client, "账单归入")
    raw = as_bytes(
        WECHAT_HEADER + "\n"
        "2024-08-01 09:00:00,零钱支付,甲店,早餐,支出,¥12.50,零钱,支付成功,W0001,/,/\n"
        "2024-08-02 10:00:00,零钱支付,乙店,退款,收入,¥6.60,零钱,已退款,W0002,/,/\n"
        "2024-08-03 11:00:00,信用卡还款,某平台,还款,不计收支,¥300.00,零钱,成功,W0003,/,/\n"
        "2024-08-04 12:00:00,中性交易,丙店,转账,/,¥0.00,零钱,已到账,W0004,/,/\n"
        "2024-08-05 13:00:00,零钱提现,丁店,提现,中性交易,¥50.00,零钱,成功,W0005,/,/"
    )
    assert data_row_count_of(str(raw.decode())) == 5
    body = await preview_and_confirm(
        auth_client, raw, "wechat", fallback_category={"action": "map", "target_id": cat_id}
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2
    assert body["data"]["skipped_count"] == 3, "三条中性行 = 夹具里的三行"
    reasons = body["data"]["skipped_reasons"]
    assert set(reasons) == SKIPPED_REASON_KEYS
    assert reasons["type_ignored"] == 3, "不计收支 + 中性交易 + `/` 全归 type_ignored（D11/D31）"
    assert reasons["type_unresolved"] == 0, "`/` 不得被当成「无法判定」"

    rows = {r["note"]: r for r in await records(auth_client)}
    assert set(rows) == {"甲店·早餐", "乙店·退款"}, "V2：备注 = `交易对方` · `商品`"
    assert (rows["甲店·早餐"]["amount"], rows["甲店·早餐"]["type"]) == (12.5, "expense")
    assert (rows["乙店·退款"]["amount"], rows["乙店·退款"]["type"]) == (6.6, "income")


# ── v1.4.4 V1：斜杠日的端到端净效果（从读取侧看，不重复 §4.x 的纯函数断言）────


async def test_v1_4_4_unambiguous_slash_dates_import_and_ambiguous_still_skip(
    auth_client: AsyncClient,
) -> None:
    """V1 端到端：`09/24/2026`、`24/09/2026 15:30` 入库，`05/06/2026` 仍计 `invalid_date`。

    用户翻案的正是「这类斜杠日期要能识别」，但**真歧义**（月/日两读皆合法）照旧不猜；
    入库形态仍是 §2.3.4 那一条 16 字符规范（月份过滤能读回即证明归一真的发生）。
    """
    cat_id = await new_category(auth_client, "日期翻案归入")
    raw = as_bytes(
        WECHAT_HEADER + "\n"
        "09/24/2026,零钱支付,甲店,无歧义美式,支出,¥1.00,零钱,成功,S1,/,/\n"
        "24/09/2026 15:30,零钱支付,乙店,无歧义欧式带时间,支出,¥2.00,零钱,成功,S2,/,/\n"
        "05/06/2026,零钱支付,丙店,真歧义不猜,支出,¥3.00,零钱,成功,S3,/,/\n"
        "02/30/2026,零钱支付,丁店,双非法日历日,支出,¥4.00,零钱,成功,S4,/,/"
    )
    data = await preview_data(auth_client, raw)
    assert data["format"] == "wechat"

    body = await confirm(
        auth_client,
        data["cache_id"],
        "wechat",
        fallback_category={"action": "map", "target_id": cat_id},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2
    assert body["data"]["skipped_reasons"]["invalid_date"] == 2, "真歧义 + 双非法各一条"

    rows = {r["note"]: r for r in await records(auth_client)}
    assert rows["甲店·无歧义美式"]["consume_time"] == "2026-09-24 00:00"
    assert rows["乙店·无歧义欧式带时间"]["consume_time"] == "2026-09-24 15:30"
    hits = await records(auth_client, start_date="2026-09-01", end_date="2026-09-30")
    assert len(hits) == 2, "归一后的斜杠日落在 2026-09 的字符串区间里（读取侧证据）"
    assert all(re.fullmatch(CONSUME_TIME_PATTERN, r["consume_time"]) for r in hits), hits


# ══════════════════════════════════════════════════════════════════
#  §2.6 标签净效果（同名多行只建一行 + 真实模板两行各建一标签）
# ══════════════════════════════════════════════════════════════════


def template_bytes_with_rows(*rows: str) -> bytes:
    """真实模板的**表头行**（运行时从 §1.1 夹具读，不重抄）+ **合成**数据行。

    任务 §2.6 明示：真实模板只有两行且 Title 各异，不能直接用来验「同名两行只建一个
    标签」→ 沿用其 6 列表头、把两行 `Title` 写成同一个值。
    """
    header_line = CASHEW_TEMPLATE_FIXTURE.read_bytes().decode("utf-8-sig").splitlines()[0]
    assert header_line == "Date,Amount,Category,Title,Note,Account"
    return as_bytes("\n".join([header_line, *rows]))


async def test_2_6_same_title_rows_create_exactly_one_tag(auth_client: AsyncClient) -> None:
    """§2.6 前段：合成同 `Title` 两行 → `tags` 表**仅新增一行**、两条记录共享同一 `tag_id`。

    §0.4-6 登记的既有缺陷：`tags` 无唯一约束、CSV 的 create 分支不查重 →
    同名两行会建两行。M3 补齐先查后插，这里是它的端到端证据。
    """
    raw = template_bytes_with_rows(
        "2026-09-25 09:00:00.000001,-18.00,Groceries,同名标签测试,买菜付款,",
        "2026-09-25 18:00:00.000002,20.00,Bills & Fees,同名标签测试,,",
    )
    assert await tag_names(auth_client) == []
    body = await preview_and_confirm(
        auth_client,
        raw,
        "cashew_template",
        category_mapping={"Groceries": {"action": "create"}, "Bills & Fees": {"action": "create"}},
        tag_mapping={"同名标签测试": {"action": "create", "category_id": None}},
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2

    same_name = [t for t in await tags_of(auth_client) if t["name"] == "同名标签测试"]
    assert len(same_name) == 1, "同名两行不得建两行标签"
    rows = await records(auth_client)
    assert {tag_id_of(r) for r in rows} == {same_name[0]["id"]}, "两条记录共享同一 tag_id"


async def test_2_6_real_template_fixture_two_titles_create_two_distinct_tags(auth_client: AsyncClient) -> None:
    """§2.6 后段：**真实模板逐字副本**的两行 Title 各建一个标签（Fruits / Monthly Income）。"""
    body = await preview_and_confirm(
        auth_client,
        CASHEW_TEMPLATE_FIXTURE.read_bytes(),
        "cashew_template",
        category_mapping={"Groceries": {"action": "create"}, "Bills & Fees": {"action": "create"}},
        tag_mapping={
            "Fruits and Vegetables": {"action": "create", "category_id": None},
            "Monthly Income": {"action": "create", "category_id": None},
        },
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == 2
    assert await tag_names(auth_client) == ["Fruits and Vegetables", "Monthly Income"]

    rows = sorted(await records(auth_client), key=lambda r: r["amount"])
    tags = {t["name"]: t["id"] for t in await tags_of(auth_client)}
    assert tag_id_of(rows[0]) == tags["Fruits and Vegetables"]
    assert tag_id_of(rows[1]) == tags["Monthly Income"]


# ══════════════════════════════════════════════════════════════════
#  §2.7 幂等边界登记（D20 不修，防后来者误判为 bug）
# ══════════════════════════════════════════════════════════════════


async def test_2_7_second_import_of_same_file_duplicates_records_is_known_boundary(
    auth_client: AsyncClient,
) -> None:
    """§2.7：**同一文件二次导入 → 记录翻倍**，这是本批登记后**不修**的现状（D20）。

    微信 / 支付宝的 `交易单号` / `商户单号` 技术上是天然幂等键，但启用去重需新增列或
    新表，违反 D19（零 DB 变更）→ 本期不启用。用例断言的正是「翻倍」这个事实：
    后来者若实现了去重，本用例会红并把他引到 D20 的裁定上，而不是误判成 bug。
    """
    cat_id = await new_category(auth_client, "重复导入归入")
    raw = as_bytes(
        WECHAT_HEADER + "\n"
        "2024-08-10 09:00:00,零钱支付,甲店,早餐,支出,¥12.50,零钱,支付成功,W0010,/,/\n"
        "2024-08-11 10:00:00,零钱支付,乙店,午餐,支出,¥28.16,零钱,支付成功,W0011,/,"
    )
    for round_no in range(2):
        body = await preview_and_confirm(
            auth_client, raw, "wechat", fallback_category={"action": "map", "target_id": cat_id}
        )
        assert body["code"] == Code.SUCCESS, body["message"]
        assert body["data"]["imported_count"] == 2, round_no

    assert len(await records(auth_client)) == 4, "已知边界（D20）：重复导入不去重"


# ══════════════════════════════════════════════════════════════════
#  §2.8 + §2.9.5 范围护栏（零 DB 触碰 / 只做 HTTP，不重复纯函数）
# ══════════════════════════════════════════════════════════════════

PURE_FUNCTIONS_BANNED_HERE = {
    # M1 识别层
    "normalize_header",
    "locate_header_rows",
    "match_dialect",
    "resolve_columns",
    "detect_csv_format",
    "csv_rows",
    "_to_rows",
    # M2 清洗层
    "parse_amount",
    "parse_time",
    "resolve_type",
    # M6 容器层
    "xlsx_rows",
    "detect_container",
    "excel_serial_to_text",
}
"""§2.9.5：这三层的纯函数一旦被本文件直调，就是在重复别的模块的断言。"""

DB_BYPASS_IMPORTS = {"sqlite3", "sqlalchemy", "sqlmodel"}
"""§2.8：本文件的 DB 访问只能经由 `auth_client` 走 conftest 的内存引擎。"""


def _module_level_import_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _called_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _string_literals(tree: ast.Module) -> list[str]:
    return [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]


SAMPLE_DIR_TOKEN = "example" + "/"
LIVE_DB_TOKEN = "money" + ".db"
"""两个被禁字面量写成**相邻字面量拼接**：运行时仍是完整串，但源码 AST 里不存在连续
字面量——否则本用例的断言字符串会把自己抓出来（同 M6 `_forbidden_excel_libs` 手法）。"""


def test_2_8_and_2_9_5_this_file_touches_no_live_db_and_no_pure_functions() -> None:
    """§2.8 零 DB 触碰 + §2.9.5 不重复纯函数断言——**对本文件源码取证**（`ast`，不受注释文案影响）。

    另钉红线 11：源码里不得出现未跟踪现场样例目录的路径字面量（D21 的可 grep 口径）。
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))

    assert _module_level_import_roots(tree).isdisjoint(DB_BYPASS_IMPORTS), (
        "§2.8：绕过 conftest 引擎直连数据库即破坏现场库只读纪律"
    )
    called = _called_names(tree)
    assert called.isdisjoint(PURE_FUNCTIONS_BANNED_HERE), (
        f"§2.9.5：本文件只走 HTTP，直调纯函数即重复 M1/M2/M6 的断言：{sorted(called & PURE_FUNCTIONS_BANNED_HERE)}"
    )
    for literal in _string_literals(tree):
        assert SAMPLE_DIR_TOKEN not in literal, "红线 11：不得引用本机未跟踪的现场样例目录"
        assert LIVE_DB_TOKEN not in literal, "§2.8：现场库文件不得出现在本文件的任何字符串里"


# ══════════════════════════════════════════════════════════════════
#  §2.9 需求 E：Excel（.xlsx）容器端到端
# ══════════════════════════════════════════════════════════════════

XLSX_FILENAME = "wechat_bill.xlsx"

# 中文失败文案（D27 / 设计 §6.4），**逐字**对照；本文件只复读、不改后端。
MSG_XLS_UNSUPPORTED = "暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv"
MSG_NOT_VALID_XLSX = "文件不是有效的 Excel(.xlsx)"
MSG_XLSX_TOO_LARGE = "Excel 文件过大或格式异常"
MSG_XLSX_EMPTY = "Excel 文件为空"

MIRROR_HEADER_ROW_INDEX = 16
"""M6 交接口径：镜像夹具的**第 16 行在 XML 里整体缺失**（无 `<row r="16">`），
而行矩阵「按出现顺序编号、不按 `r` 补空行」（D26）→ `locate_header_rows` 给 **16**。
「文件里前导 17 行」这一**含缺失行的行号口径**由 §2.9.1b 的 `extra_preamble=1` 变体
同时钉住（M6 §4.10 的两口径并测；主 Agent 裁定一手事实优先）。"""

FORBIDDEN_INTERNAL_TOKENS = (
    "new-line character",
    "_csv.Error",
    "BadZipFile",
    "UnicodeDecodeError",
    "ParseError",
    "Traceback",
)
"""§2.9.4 反向护栏：这些英文内部异常串一旦出现在响应里，就是 §0.4-14 的缺陷复发。"""


async def test_2_9_1_wechat_xlsx_preview_and_confirm_end_to_end(auth_client: AsyncClient) -> None:
    """§2.9.1：M6 合成镜像 `.xlsx` → 预览 `container=xlsx` + `format=wechat` → 确认入库。

    `encoding == "xlsx"` 是设计**定死的哨兵值**（该通道无字符编码可言，§1.2.5），
    不是错值。期望值**从预览响应的 `sample_rows` 推导**——既不 import 构造器内部形态、
    也不重算 D13/D24（§2.9.5）。
    """
    data = await preview_data(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)
    assert data["container"] == "xlsx", "容器由 magic 判定，不看扩展名（D22）"
    assert data["encoding"] == "xlsx", "哨兵固定值（设计 §1.2.5），不是错值"
    assert data["format"] == "wechat"
    assert data["headers"] == list(WECHAT_HEADERS)
    assert data["header_row_index"] == MIRROR_HEADER_ROW_INDEX
    assert data["row_count"] == DATA_ROW_COUNT
    assert len(data["sample_rows"]) == DATA_ROW_COUNT
    assert data["categories_in_file"] == sorted({row[1] for row in data["sample_rows"]}), \
        "v1.4.4 V2：微信的分类来源 = `交易类型` 列（按 role 定位取值）"
    assert "未识别到分类列：需指定默认分类" not in data["warnings"], "V2：微信已有分类列"

    neutral = [row for row in data["sample_rows"] if row[4] == "/"]
    payable = [row for row in data["sample_rows"] if row[4] != "/"]
    assert (len(neutral), len(payable)) == (1, DATA_ROW_COUNT - 1)

    cat_id = await new_category(auth_client, "账单归入")
    body = await confirm(
        auth_client, data["cache_id"], "wechat", fallback_category={"action": "map", "target_id": cat_id}
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    assert body["data"]["imported_count"] == len(payable), "入库条数 == 夹具数据行数 - 中性 `/` 行"
    assert body["data"]["skipped_reasons"]["type_ignored"] == len(neutral)

    def expected_note(row: list[str]) -> str:
        """V2 的备注拼接：`交易对方` · `商品`（夹具里 `/` 占位段不参与）。"""
        parts = [part for part in (row[2], row[3]) if part and part != "/"]
        return "·".join(parts)

    rows = {r["note"]: r for r in await records(auth_client)}
    assert set(rows) == {expected_note(row) for row in payable}, "商品与交易对方拼一条备注（V2）"
    for row in payable:
        stored = rows[expected_note(row)]
        assert stored["amount"] == float(row[5]), "裸数字金额 → abs 后两位小数（D13）"
        assert stored["type"] == ("expense" if row[4] == "支出" else "income")
        assert stored["category_id"] == cat_id
        assert stored["consume_time"] == row[0][:16], "serial → 容器文本 → 16 字符入库（D24/D14）"
    assert DATE_TEXT[:16] in {r["consume_time"] for r in rows.values()}


async def test_2_9_1b_header_row_index_is_sixteen_on_mirror_and_seventeen_with_drift(
    auth_client: AsyncClient,
) -> None:
    """§2.9.1 的 `header_row_index`：镜像 = **16**、`extra_preamble=1` = **17**（两条口径都在场）。

    外加前导漂移 5 行的变体——D1/D2「禁止 skiprows 写死」的端到端复现：
    前导行数变了必须仍命中同一表头、数据行数不得被多吃。
    """
    mirror = await preview_data(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)
    assert mirror["header_row_index"] == MIRROR_HEADER_ROW_INDEX == 16

    drifted = await preview_data(auth_client, wechat_xlsx_bytes(extra_preamble=1), XLSX_FILENAME)
    assert drifted["header_row_index"] == 17
    assert (drifted["container"], drifted["format"]) == ("xlsx", "wechat")
    assert drifted["row_count"] == DATA_ROW_COUNT

    more = await preview_data(auth_client, wechat_xlsx_bytes(extra_preamble=5), XLSX_FILENAME)
    assert more["header_row_index"] == 21
    assert more["row_count"] == DATA_ROW_COUNT
    assert more["warnings"][0] == f"已忽略表头前的 {more['header_row_index']} 行说明文字"


async def test_2_9_2_xlsx_serial_dates_reach_the_read_side(auth_client: AsyncClient) -> None:
    """§2.9.2：xlsx 的 serial 日期入库后，**三处读取路径**都拿到合法月份（换算真的贯通）。

    与 §2.3 同口径：只看「写进去了」不算证明，必须从 `/api/records` 的月份过滤、
    `/api/statistics/trend` 的月份键、`/api/budgets` 的 `spent` 三处读回。
    """
    data = await preview_data(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)
    month = DATE_TEXT[:7]  # 合成夹具四条数据行都在同一个月
    cat_id = await new_category(auth_client, "账单归入")
    body = await confirm(
        auth_client, data["cache_id"], "wechat", fallback_category={"action": "map", "target_id": cat_id}
    )
    assert body["code"] == Code.SUCCESS, body["message"]
    rows = await records(auth_client)
    assert rows

    # 读取路径一：月份过滤命中（未换算的裸 serial `46289.48…` 字符串比较必然出圈）
    hits = await records(auth_client, start_date=f"{month}-01", end_date=f"{month}-30")
    assert len(hits) == len(rows)
    assert await records(auth_client, start_date="2024-01-01", end_date="2024-01-31") == []
    assert {r["consume_time"] for r in hits} == {
        row[0][:16] for row in data["sample_rows"] if row[4] != "/"
    }, "月份过滤命中的正是那几条 serial 换算后的挂钟时间（D24/D14）"
    assert all(re.fullmatch(CONSUME_TIME_PATTERN, r["consume_time"]) for r in hits), hits

    # 读取路径二：趋势月份键合法且金额进桶
    trend = (
        await auth_client.get(
            "/api/statistics/trend",
            params={"group_by": "month", "start_date": f"{month}-01", "end_date": f"{month}-30"},
        )
    ).json()["data"]["items"]
    assert [item["period"] for item in trend] == [month], "不得出现 None / 裸序列号月份键"
    assert trend[0]["income"] > 0 and trend[0]["expense"] > 0

    # 读取路径三：当月预算 spent 含这些记录
    expense_cat_ids = sorted({r["category_id"] for r in rows if r["type"] == "expense"})
    created = await auth_client.post(
        "/api/budgets",
        json={
            "month": month,
            "name": "xlsx 月份预算",
            "amount": 9999.0,
            "scope_mode": "include",
            "category_ids": expense_cat_ids,
        },
    )
    assert created.json()["code"] == Code.SUCCESS, created.json()
    budgets = (await auth_client.get("/api/budgets", params={"month": month})).json()["data"]
    mine = next(b for b in budgets if b["name"] == "xlsx 月份预算")
    expected_expense = round(sum(r["amount"] for r in rows if r["type"] == "expense"), 2)
    assert mine["spent"] == expected_expense > 0, "容器层换算 → 月份桶 → 预算 spent 三段贯通"


async def test_2_9_3_xls_ole_container_gets_verbatim_chinese_param_error(auth_client: AsyncClient) -> None:
    """§2.9.3 之一：OLE `.xls`（合成 magic 前缀）→ `PARAM_ERROR` + 中文另存指引**逐字**相等。"""
    resp = await preview_raw(auth_client, xlsx_reader.XLS_MAGIC + b"\x00" * 4096, "legacy.xls")
    body = resp.json()
    assert resp.status_code == 400, "HTTP 状态码不变（红线 5）"
    assert body["code"] == Code.PARAM_ERROR
    assert body["message"] == MSG_XLS_UNSUPPORTED


async def test_2_9_3_non_zip_and_missing_worksheet_get_verbatim_chinese_messages(
    auth_client: AsyncClient,
) -> None:
    """§2.9.3 之二：`PK` 开头但不是 zip、以及**缺 worksheet entry** 的 zip → 中文文案逐字。"""
    payload = wechat_xlsx_bytes()
    cases: list[tuple[str, bytes]] = [
        ("PK 后接垃圾字节（非 zip）", b"PK\x03\x04this is not a zip archive"),
        ("截断的 zip", payload[:40]),
        ("缺 worksheet entry", _zip_write(payload, drop="xl/worksheets/sheet1.xml")),
        ("缺 workbook entry", _zip_write(payload, drop="xl/workbook.xml")),
    ]
    for label, raw in cases:
        resp = await preview_raw(auth_client, raw, XLSX_FILENAME)
        body = resp.json()
        assert resp.status_code == 400, label
        assert body["code"] == Code.PARAM_ERROR, (label, body)
        assert body["message"] == MSG_NOT_VALID_XLSX, label


async def test_2_9_3_oversized_entry_gets_verbatim_chinese_message(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§2.9.3 之三：超限 → `Excel 文件过大或格式异常`（`monkeypatch` 调小上限，
    **不改生产常量、不真造 50 MB 文件**，任务 §2.9.3）。"""
    monkeypatch.setattr(xlsx_reader, "MAX_ENTRY_BYTES", 1024)
    body = (await preview_raw(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)).json()
    assert body["code"] == Code.PARAM_ERROR
    assert body["message"] == MSG_XLSX_TOO_LARGE

    monkeypatch.setattr(xlsx_reader, "MAX_ENTRY_BYTES", 50 * 1024 * 1024)
    monkeypatch.setattr(xlsx_reader, "MAX_TOTAL_BYTES", 2048)
    total = (await preview_raw(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)).json()
    assert total["message"] == MSG_XLSX_TOO_LARGE, "单 entry 未超但解压总量超限同样拒绝（D27）"

    monkeypatch.undo()
    ok = await preview_raw(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)
    assert ok.json()["code"] == Code.SUCCESS, "上限是模块属性、非常量固化：恢复后即通"


async def test_2_9_3_empty_xlsx_gets_verbatim_chinese_message(auth_client: AsyncClient) -> None:
    """§2.9.3 之四：空表 → `Excel 文件为空`（xlsx 通道文案独立，CSV 侧 `CSV 文件为空` 不变）。"""
    body = (await preview_raw(auth_client, build_xlsx([]), XLSX_FILENAME)).json()
    assert body["code"] == Code.PARAM_ERROR
    assert body["message"] == MSG_XLSX_EMPTY

    # 「只有前导说明行、无合格表头行」按设计 §6.4 走**两条通道同一处置**：
    # M1 的退化判据（非空单元格 ≥2）落空后抛共享的空表文案——该文案由 M1 §4.5 定死为
    # `CSV 文件为空`（既有测试锁定、红线 4 零放宽），xlsx 容器只在**行矩阵本身为空**时
    # 才给 `Excel 文件为空`。故此处只断「中文 + PARAM_ERROR + 无英文内部串」，
    # 差异登记进 M5 完成报告（不自行改实现）。
    only_preamble = build_xlsx([["微信支付账单明细"], ["----微信支付账单明细列表----"]])
    drifted = (await preview_raw(auth_client, only_preamble, XLSX_FILENAME)).json()
    assert drifted["code"] == Code.PARAM_ERROR
    assert drifted["message"] in {MSG_XLSX_EMPTY, "CSV 文件为空"}, drifted["message"]
    assert not any(token in drifted["message"] for token in FORBIDDEN_INTERNAL_TOKENS)

    csv_empty = (await preview_raw(auth_client, b"", "empty.csv")).json()
    assert csv_empty["code"] == Code.PARAM_ERROR
    assert "Excel" not in csv_empty["message"], "CSV 通道不得拿到 xlsx 文案（红线 4 既有措辞保留）"


async def test_2_9_4_no_english_internals_leak_in_any_import_response(auth_client: AsyncClient) -> None:
    """§2.9.4 **反向护栏**：成功与失败的全部导入响应里都不得出现英文内部异常串。

    这是设计 §0.4-14 那条缺陷（把 xlsx 喂进 CSV 通道 → `_csv.Error` 裸冒到
    `SERVER_ERROR` 并透出 `new-line character seen in unquoted field…`）的收口证据。
    """
    payloads: list[tuple[str, str, bytes]] = [
        ("csv 正常", "ok.csv", as_bytes(WECHAT_HEADER + "\n2024-08-20 09:00:00,零钱支付,甲店,早餐,支出,¥1.00,零钱,成功,X1,/,")),
        ("xlsx 正常", XLSX_FILENAME, wechat_xlsx_bytes()),
        ("xls（OLE）", "legacy.xls", xlsx_reader.XLS_MAGIC + b"\x00" * 2048),
        ("假 zip", "fake.xlsx", b"PK\x03\x04\x00\x00\x00garbage"),
        ("空 xlsx", "empty.xlsx", build_xlsx([])),
        ("二进制垃圾当 csv", "junk.csv", bytes(range(256))),
        ("BOM + zip magic", "bompk.csv", b"\xef\xbb\xbfPK\x03\x04" + b"\x00" * 64),
        ("分隔符噪声", "noise.csv", b";;;,,,\n,,,;;;\n"),
        ("未闭合引号的换行", "newline.csv", b'amount,note\n12.0,"unterminated\n'),
    ]
    for label, filename, raw in payloads:
        resp = await preview_raw(auth_client, raw, filename)
        assert resp.status_code in (200, 400), (label, resp.status_code)
        assert resp.status_code != 500, f"{label}：不得落到 SERVER_ERROR"
        for token in FORBIDDEN_INTERNAL_TOKENS:
            assert token not in resp.text, f"{label}：响应透出英文内部异常 {token!r}"
        body = resp.json()
        if body["code"] != Code.SUCCESS:
            assert re.search(r"[一-鿿]", body["message"]), (label, body["message"])

    xlsx_body = (await preview_raw(auth_client, wechat_xlsx_bytes(), XLSX_FILENAME)).json()
    assert xlsx_body["code"] == Code.SUCCESS
    confirmed = await confirm(auth_client, xlsx_body["data"]["cache_id"], "wechat")
    assert confirmed["code"] == Code.SUCCESS, confirmed["message"]  # 无分类列 → 可解释跳过
    for token in FORBIDDEN_INTERNAL_TOKENS:
        assert token not in str(confirmed), token


# ══════════════════════════════════════════════════════════════════
#  §2.10 前后端契约一致性（P3 终验兜底：防 mock 与真实载荷漂移）
# ══════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_VUE = REPO_ROOT / "frontend/src/pages/SettingsImportExportPage.vue"
DIALOG_VUE = REPO_ROOT / "frontend/src/components/common/CsvMappingDialog.vue"
API_JS = REPO_ROOT / "frontend/src/api/export.js"

NEW_BOOT3_FIELDS = ("columns", "type_source", "fallback_category")
"""本批新增的三个字段：两侧必须**逐字同名**（D18）。"""


def frontend_source(path: Path) -> str:
    """**只读**前端源码；读不到即显式 fail（**禁止 skip 蒙过这条护栏**）。"""
    assert path.is_file(), f"前端源码不可读：{path} —— §2.10 的契约护栏必须真实在场，不得跳过"
    return path.read_text(encoding="utf-8")


def balanced_block(source: str, open_at: int) -> str:
    """从 `open_at`（指向开括号）起的**配平**片段（含首尾括号）。

    只做括号计数、不解析 JS：本批被读的四处字面量里字符串字面量均不含括号，计数即够；
    结构一旦变化，取不到键会由调用方**显式 fail**，不会静默通过。
    """
    opener = source[open_at]
    closer = {"{": "}", "[": "]"}[opener]
    depth = 0
    for pos in range(open_at, len(source)):
        char = source[pos]
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return source[open_at : pos + 1]
    raise AssertionError(f"从位置 {open_at} 起的字面量括号不配平：前端结构已变，本护栏需重审")


def block_after(source: str, anchor: str, opener: str = "{") -> str:
    """anchor 之后第一个配平字面量块。"""
    start = source.find(anchor)
    assert start >= 0, f"前端源码里找不到锚点 {anchor!r}：契约漂移或组件被重命名（红线 12）"
    open_at = source.find(opener, start)
    assert open_at >= 0, f"锚点 {anchor!r} 之后找不到 {opener} 字面量"
    return balanced_block(source, open_at)


def function_body(source: str, function_name: str) -> str:
    """`[async] function <name>(...) { ... }` 的函数体。"""
    match = re.search(rf"(?:async\s+)?function\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{", source)
    assert match, f"前端找不到函数 {function_name}：被重命名即违反红线 12，本护栏必须红"
    return balanced_block(source, match.end() - 1)


def object_keys(block: str) -> set[str]:
    """对象字面量**顶层**的 `key:` 名集合（被读的四处均无嵌套对象）。"""
    keys = set(re.findall(r"(?:^|[{,])\s*([A-Za-z_]\w*)\s*:", block[1:-1], re.M))
    assert keys, "字面量里提取不到任何键：正则失效等于这条护栏不存在"
    return keys


def assigned_names(block: str, target: str) -> set[str]:
    """函数体内 `target.<name> = ...` 的动态字段名。"""
    found = set(re.findall(rf"{re.escape(target)}\.([A-Za-z_]\w*)\s*=", block))
    assert found, f"{target}.x = 赋值提不到：载荷组装方式已变"
    return found


def option_values(block: str) -> set[str]:
    """数组字面量里 `{ value: 'xxx' }` 的取值集合。"""
    found = set(re.findall(r"value:\s*'([^']+)'", block))
    assert found, "提不到 value 字面量"
    return found


async def test_2_10_page_confirm_payload_keys_are_a_subset_of_the_backend_model(
    auth_client: AsyncClient,
) -> None:
    """§2.10：前端 `handleCsvImport` 实际发出的键 ⊆ `ImportCsvRequest.model_fields`，
    且本批三个新字段 `columns` / `type_source` / `fallback_category` **两侧逐字同名**。

    手法：`Path.read_text` 读前端源码 + 正则提取字面量（不引前端依赖、不改前端文件；
    仓库根由 `__file__` 推导——pytest 的 cwd 是 `backend`，写相对路径必错）。
    这条防的是「vitest 里 mock 的载荷与真实前端发的载荷漂移」。
    """
    del auth_client  # 纯源码对照用例
    page_source = frontend_source(PAGE_VUE)
    dialog_source = frontend_source(DIALOG_VUE)

    page_keys = object_keys(block_after(function_body(page_source, "handleCsvImport"), "const payload ="))
    assert page_keys == {"cache_id", "format", "category_mapping", "tag_mapping", *NEW_BOOT3_FIELDS}, page_keys

    backend_fields = set(ImportCsvRequest.model_fields)
    assert page_keys <= backend_fields, f"前端发出了后端模型没有的键：{page_keys - backend_fields}"
    for field in NEW_BOOT3_FIELDS:
        assert field in page_keys, f"前端不再发送 {field}（§2.10 三字段之一消失）"
        assert field in backend_fields, f"后端模型缺 {field}（本批新增字段被改名？）"

    # 向导 emit 的三字段名 == 页面读的三字段名（页面只透传、不重命名）
    confirm_body = function_body(dialog_source, "handleConfirm")
    assert set(NEW_BOOT3_FIELDS) <= assigned_names(confirm_body, "payload"), "向导不再 emit 这三字段"
    assert {"category_mapping", "tag_mapping"} <= object_keys(block_after(confirm_body, "const payload ="))

    # `importCsv` 整体透传（api 层不重新拼字段）→ 上面提取的键集 == 真实 HTTP body 的键集
    assert "request.post('/import/csv', data)" in frontend_source(API_JS), (
        "api 层不再透传载荷 → 本用例需按新转发逻辑重审"
    )

    # 后端模型必须**接受**前端真实形状的载荷（同形终证，不看 FastAPI 422 文案）
    shaped = {
        "cache_id": "e2e-cache-id",
        "format": "wechat",
        "category_mapping": {"餐饮": {"action": "map", "target_id": 1}},
        "tag_mapping": {"某店": {"action": "create", "category_id": None}},
        "columns": {"consume_time": 0, "amount": 5, "type": 4, "tag": 2, "note": 3},
        "type_source": "column",
        "fallback_category": {"action": "map", "target_id": 1},
    }
    assert set(shaped) == page_keys, "本用例的载荷形状必须与前端真实键集逐字一致"
    try:
        parsed = ImportCsvRequest(**shaped)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"后端模型不接受前端真实形状的载荷：{exc}") from exc
    assert parsed.columns == shaped["columns"]
    assert parsed.type_source == "column"
    assert parsed.fallback_category is not None


async def test_2_10_columns_payload_shape_matches_backend_preview_response(
    auth_client: AsyncClient,
) -> None:
    """§2.10 的「同形」半区：前端读的 `columns` 项字段 == 后端实际下发的字段；
    前端手选用的角色名 == 后端 `ROLES` 六值封闭集；列索引恒为 int。"""
    dialog_source = frontend_source(DIALOG_VUE)
    frontend_col_fields = set(re.findall(r"\bcol\??\.([A-Za-z_]\w+)", dialog_source))
    assert frontend_col_fields, "前端不再按字段名读 columns[].x → 提取为空即护栏不存在"

    data = await preview_data(
        auth_client,
        as_bytes(WECHAT_HEADER + "\n2024-08-21 09:00:00,零钱支付,甲店,早餐,支出,¥1.00,零钱,成功,Y1,/,"),
    )
    assert [set(row) for row in data["columns"]][0] == {"index", "header", "role", "sample"}, data["columns"][0]
    assert frontend_col_fields <= set(data["columns"][0]), "前端读了后端没发的字段"

    frontend_roles = object_keys(block_after(dialog_source, "const ROLE_LABELS ="))
    assert frontend_roles == set(ROLES), f"前端 {sorted(frontend_roles)} / 后端 {sorted(ROLES)}（D3 封闭集）"
    emitted = {row["role"] for row in data["columns"]}
    assert emitted <= frontend_roles | {None}, emitted
    assert all(isinstance(row["index"], int) for row in data["columns"]), "columns 的值必须是列索引 int"

    # 前端把「角色 → 列索引」整体回传（`columns: dict[str, int]`）
    handpicked = {row["role"]: row["index"] for row in data["columns"] if row["role"]}
    assert set(handpicked) <= frontend_roles
    assert ImportCsvRequest(cache_id="x", format="wechat", columns=handpicked).columns == handpicked


def test_2_10_type_source_and_format_enums_match_the_schema_patterns() -> None:
    """§2.10 的封闭集半区：前端可选的 `type_source` 四态与 `format` 六值，
    必须与后端 `ImportCsvRequest` 的 pattern **逐字同集**（D10 / D18）。"""
    dialog_source = frontend_source(DIALOG_VUE)

    frontend_type_sources = option_values(block_after(dialog_source, "const TYPE_SOURCE_OPTIONS =", opener="["))
    schema_type_sources = pattern_enum(schema_pattern(ImportCsvRequest, "type_source"))
    assert frontend_type_sources == schema_type_sources, (frontend_type_sources, schema_type_sources)
    assert frontend_type_sources == {"column", "sign", "all_expense", "all_income"}

    frontend_formats = object_keys(block_after(dialog_source, "const FORMAT_LABELS ="))
    schema_formats = pattern_enum(schema_pattern(ImportCsvRequest, "format"))
    assert frontend_formats == schema_formats, (frontend_formats, schema_formats)
    assert len(frontend_formats) == 6, "format 六值封闭集（D18）不得扩缩"
