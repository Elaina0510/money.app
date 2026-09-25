"""Import service for CSV and SQL import."""

import csv
import io
import logging
import re
import sqlite3
import tempfile
import unicodedata
from collections.abc import Sequence
from datetime import datetime
from typing import Any, NamedTuple, cast

import chardet
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import (
    SCOPE_INCLUDE,
    SCOPE_MODES,
    UNKNOWN_CATEGORY_NAME,
    Budget,
    BudgetCategory,
)
from app.models.category import LEGACY_CATEGORY_TYPE, Category
from app.models.quick_template import QuickTemplate
from app.models.record import Record
from app.models.tag import Tag
from app.services.category_service import OTHER_CATEGORY_NAME
from app.services.csv_dialects import (
    DIALECTS,
    REQUIRED_ROLES,
    ROLE_LABELS,
    ROLES,
    ColumnHint,
    Dialect,
    is_blank_cell,
    locate_header_rows,
    match_dialect,
    resolve_columns,
)
from app.services.csv_values import parse_amount, parse_time, resolve_type
from app.services.xlsx_reader import detect_container, xlsx_rows
from app.utils.cache import delete_cache, read_from_cache, save_to_cache
from app.utils.history import create_history_entry
from app.utils.money import round_money

logger = logging.getLogger(__name__)

# ── CSV Import ─────────────────────────────────────────────────────


def detect_and_decode(file_bytes: bytes) -> tuple[str, str]:
    """字节 → `(文本, 编码标签)`（D7 / M1 §3，需求 D 主体）。

    解码序 `utf-8-sig` → `utf-8` → chardet 探测 → `gb18030`(`errors="replace"`) 兜底。
    `gb18030` 替换原 `gbk`（它是 GBK 超集，覆盖中文账单的生僻字）。返回前统一
    `lstrip("\ufeff")` 再兜一层：`export_csv` 写 BOM（`export_service.py:69`）而旧实现
    用 `utf-8` 解码，BOM 粘在首列表头成 `\ufeffamount`（`\ufeff`.isspace() 为 False、
    `strip()` 去不掉）→ 自家导出回导必报「无法识别」，本函数即该缺陷的修复落点。

    生僻字走 `errors="replace"` 时**不抛**（设计 §1.3 登记的已知边界，不扩范围）。
    """
    bom_present = file_bytes.startswith(b"\xef\xbb\xbf")
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            decoded = file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        # `utf-8-sig` 也能解无 BOM 字节 → 标签只在真有 BOM 时报 sig，不谎报
        label = "utf-8-sig" if (encoding == "utf-8-sig" and bom_present) else "utf-8"
        return decoded.lstrip("\ufeff"), label

    detected = chardet.detect(file_bytes)
    guess = str(detected.get("encoding") or "")
    if guess:
        try:
            return file_bytes.decode(guess).lstrip("\ufeff"), guess
        except (UnicodeDecodeError, TypeError, LookupError):
            pass

    return file_bytes.decode("gb18030", errors="replace").lstrip("\ufeff"), "gb18030"


def csv_rows(text: str) -> list[list[str]]:
    """文本 → **行矩阵** `list[list[str]]`（M1 §4.2，D27 的 CSV 半边）。

    `csv.reader` 对非 CSV 内容（如被改名上传的 xlsx / 任意二进制）会抛英文
    `_csv.Error: new-line character seen in unquoted field…`，它不是 `ValueError` →
    落到路由 `Exception` 分支变成 `SERVER_ERROR` 并把内部文案透出给用户（§0.4-14）。
    此处统一收口为中文 `ValueError`，由路由转 `PARAM_ERROR`。

    产物直接喂 `csv_dialects.locate_header_rows(rows)`；M6 的 xlsx 通道产同型行矩阵，
    两容器共用同一套表头定位算法（D25）。
    """
    try:
        return [list(row) for row in csv.reader(io.StringIO(text))]
    except csv.Error as exc:  # 收口英文内部异常（D27）
        raise ValueError("CSV 文件内容为空或格式不正确") from exc


CSV_CACHE_SUFFIX = ".csv"
XLSX_CACHE_SUFFIX = ".xlsx"
CACHE_SUFFIXES: tuple[str, ...] = (CSV_CACHE_SUFFIX, XLSX_CACHE_SUFFIX)


def _cache_suffix(container: str) -> str:
    """容器标签 → 缓存文件后缀（**只是文件名装饰**，判据永远是 magic，D22）。"""
    return XLSX_CACHE_SUFFIX if container == "xlsx" else CSV_CACHE_SUFFIX


def _to_rows(file_bytes: bytes) -> tuple[list[list[str]], str]:
    """字节 → **（行矩阵, 容器标签）**（M6 §2.1，设计 §6.3 第 1 步）。

    本文件唯一的容器分叉点：`detect_container` 只看 magic（D22，不信扩展名与缓存后缀）——
    `xlsx` → `xlsx_rows()`；`xls` → 中文 `ValueError` 指引另存；其余 → M1 的
    `detect_and_decode()` + `csv_rows()`。三条出口产**同型**行矩阵，其后
    `locate_header_rows` / `match_dialect` / `resolve_columns` 一套代码共用（D25）。

    Returns:
        `(行矩阵, container)`，`container ∈ {"csv", "xlsx"}`。

    Raises:
        ValueError: 全中文文案（D27）——`.xls` 指引、`Excel 文件为空`、
            `文件不是有效的 Excel(.xlsx)`、`Excel 文件过大或格式异常`、CSV 侧既有文案。

    M3 交接：确认阶段的重算步骤**直接调用本函数**（对同一批字节返回与预览同一 `container`）。
    """
    container = detect_container(file_bytes)
    if container == "xls":
        raise ValueError("暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv")
    if container == "xlsx":
        return xlsx_rows(file_bytes), "xlsx"
    text, _encoding = detect_and_decode(file_bytes)
    return csv_rows(text), "csv"


def _read_cached_bytes(cache_id: str) -> bytes:
    """按候选后缀取回缓存原字节（M6 §2.4 与 `save_to_cache` 成对的**另一半**）。

    `cache.py:_cache_path` 只做字符串拼接，后缀写死 `.csv` 时 xlsx 缓存必然
    「缓存文件不存在」；而按 `cache_id` 逐个探测再交给 magic 判定，才不违反
    D22「不信缓存后缀」。取回后容器仍以字节 magic 为准。
    """
    for suffix in CACHE_SUFFIXES:
        try:
            return read_from_cache(cache_id, suffix)
        except FileNotFoundError:
            continue
    raise FileNotFoundError("缓存文件不存在或已过期")


def detect_csv_format(headers: list[str]) -> str:
    """表头 → 方言 key（`native|cashew|cashew_template|alipay|wechat`）或 `custom`。

    语义从「native|cashew|unknown」扩展为六值枚举之一（M1 §5.2）：未命中内置方言
    **不抛异常、不再返回 `unknown`**——未知表头进预览由用户手选列角色（需求 A/D）。
    """
    dialect = match_dialect(headers)
    return dialect.key if dialect is not None else "custom"


# D16（v1.4.3-boot3 M3）：`convert_cashew_type` / `convert_cashew_amount` /
# `convert_cashew_date` 已物理删除、**不留转发壳**——职责由 M2 `csv_values` 的
# `resolve_type` / `parse_amount` / `parse_time` 承担（`abs()` 口径迁入下方落库半区 D13）。


def _is_blank_row(row: Sequence[str]) -> bool:
    """全空行判定（现状既有口径，逐字保留）。"""
    return not row or all(cell.strip() == "" for cell in row)


def _cell_by_index(row: Sequence[str], index: int | None) -> str:
    """按列下标取单元格：越界 / 无该角色列 / 空占位（含 `/`，D31）一律返回空串。"""
    if index is None or index >= len(row):
        return ""
    value = row[index].strip()
    return "" if is_blank_cell(value) else value


# ── 角色 → 列索引（v1.4.4 V2：`note` 可来自多列，其余角色仍是一列）──────────

RoleIndex = dict[str, int | list[int]]
"""`_authoritative_role_index` 与识别区推导共用的形状：角色 → 列索引（`note` 可为列表）。"""


def _indexes(value: int | list[int] | None) -> list[int]:
    """把某个角色的列索引形状归一为**升序**列表（`None` → 空表）。

    旧前端的 `int` 载荷与新前端的 `list[int]` 载荷在此汇流（D18 向后兼容）；
    升序即「按列索引顺序拼接备注」的口径（V2）。
    """
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    return sorted(value)


def _first_index(value: int | list[int] | None) -> int | None:
    """单列角色（consume_time/amount/type/category/tag）取**第一命中列**（任务 §C）。"""
    indexes = _indexes(value)
    return indexes[0] if indexes else None


def _role_index_from_hints(hints: Sequence[ColumnHint]) -> RoleIndex:
    """列提示 → 角色索引（识别区与落库区的**同一份**推导，D25 精神）。

    非 `note` 角色沿用「先列独占」（`resolve_columns` 已把后来的同角色列判为冲突 →
    此处天然只有一个命中列）；`note` 例外地把全部命中列收成列表（V2）。
    """
    index: RoleIndex = {}
    for hint in hints:
        if hint.role is None:
            continue
        if hint.role == "note":
            existing = index.get("note")
            if isinstance(existing, list):
                existing.append(hint.index)
            elif existing is None:
                index["note"] = [hint.index]
            else:
                index["note"] = [existing, hint.index]
            continue
        index.setdefault(hint.role, hint.index)
    return index


NOTE_JOINER = "·"
"""多列备注的拼接符（v1.4.4 V2：微信 `交易对方` + `商品` 拼成一条备注）。"""


def _join_note_parts(row: Sequence[str], indexes: Sequence[int]) -> str | None:
    """按**升序列索引**取每列备注来源并拼一条（V2）。

    每列走 `_cell_by_index`（`/` 与空白按空占位处理，D31），非空值以 `·` 连接；
    全空 → ``None``（**不产出空串、不产出 `·`**）。列序即拼接序，与前端向导的
    列顺序一致、可预期。
    """
    parts = [value for value in (_cell_by_index(row, index) for index in indexes) if value]
    return NOTE_JOINER.join(parts) or None


async def preview_csv(
    db: AsyncSession, file_bytes: bytes
) -> dict[str, Any]:
    """预览（CSV / xlsx 两容器）：magic 判容器 → 行矩阵 → 表头定位 → 方言匹配 → 逐列角色。

    响应契约见设计 §1.2.5（M4 依此冻结）：既有 5 字段全保留，新增 7 字段
    `headers`/`header_row_index`/`columns`/`suggested_type_source`/`encoding`/
    `sample_rows`/`warnings`；第 8 个契约字段 **`container`（`"csv" | "xlsx"`）由 M6
    的容器分派器给出**（D29）——老前端不读即可（D18）。xlsx 通道无字符编码可言，
    `encoding` 按设计定死取哨兵字符串 `"xlsx"`（不是错值，M4 已按「不当编码展示」处理）。

    未知表头不再整文件拒绝（需求 A/D）：`format` 落到 `custom`、全列 `role=None`，
    由用户在前端手选列角色。业务校验（必需列缺失等）只在 `warnings` 提示，
    确认阶段由 M3 显式拒绝。

    注：`db` 形参现状无消费方（设计 §1.2.6 / M1 §5.5 保留签名，路由依赖注入不动）。

    v1.4.4 V2 的两处可观察后果（后端事实，前端轮据此调整）：
      * 微信账单**有**分类列了（`交易类型` → `category`）→ `categories_in_file` 出的是
        该列取值，`warnings` 里的「未识别到分类列：需指定默认分类」对真实微信账单消失；
      * `note` 可由多列同时命中（微信 `交易对方`+`商品`、支付宝 `交易对方`+`商品说明`），
        按列索引升序拼一条备注（拼接发生在落库层）；`categories_in_file`/`tags_in_file`
        仍只按 category / tag 角色列收集，**不受 note 多列影响**。
    """
    rows, container = _to_rows(file_bytes)
    encoding = "xlsx" if container == "xlsx" else detect_and_decode(file_bytes)[1]
    header_row_index, headers, data_rows = locate_header_rows(rows)

    dialect = match_dialect(headers)
    format_type = dialect.key if dialect is not None else "custom"
    raw_headers = [cell.strip() for cell in rows[header_row_index]]
    columns = resolve_columns(raw_headers, dialect, data_rows)

    # 按**列角色**定位分类 / 标签列（取代现状「按表头名硬编码」）
    role_index: RoleIndex = _role_index_from_hints(columns)
    cat_idx: int | None = _first_index(role_index.get("category"))
    tag_idx: int | None = _first_index(role_index.get("tag"))

    categories_in_file: set[str] = set()
    tags_in_file: set[str] = set()
    row_count = 0

    for row in data_rows:
        if _is_blank_row(row):
            continue
        row_count += 1

        cat_name = _cell_by_index(row, cat_idx)
        tag_name = _cell_by_index(row, tag_idx)

        if cat_name:
            categories_in_file.add(cat_name)
        if tag_name:
            tags_in_file.add(tag_name)

    warnings: list[str] = []
    if header_row_index > 0:
        warnings.append(f"已忽略表头前的 {header_row_index} 行说明文字")
    if "category" not in role_index:
        warnings.append("未识别到分类列：需指定默认分类")
    missing_roles = [role for role in REQUIRED_ROLES if role not in role_index]
    if missing_roles:
        warnings.append(
            "缺少必需列：" + "、".join(ROLE_LABELS[role] for role in missing_roles)
        )
    dropped = [hint.header for hint in columns if hint.conflict]
    if dropped:
        warnings.append("多列对应同一角色：仅保留靠前列，未采用 " + "、".join(dropped))

    if dialect is not None:
        suggested_type_source = dialect.type_source
    else:
        # D10：custom 有收支列走列值，否则按金额正负
        suggested_type_source = "column" if "type" in role_index else "sign"

    sample_rows: list[list[str]] = [
        list(row) for row in data_rows if not _is_blank_row(row)
    ][:5]

    # Cache the file —— 后缀按容器实参化（M6 §2.4，与 `_read_cached_bytes` 成对）
    cache_id = save_to_cache(file_bytes, _cache_suffix(container))

    return {
        "format": format_type,
        "row_count": row_count,
        "categories_in_file": sorted(categories_in_file),
        "tags_in_file": sorted(tags_in_file),
        "cache_id": cache_id,
        "headers": raw_headers,
        "header_row_index": header_row_index,
        "columns": [
            {
                "index": hint.index,
                "header": hint.header,
                "role": hint.role,
                "sample": hint.sample,
            }
            for hint in columns
        ],
        "suggested_type_source": suggested_type_source,
        "encoding": encoding,
        "container": container,
        "sample_rows": sample_rows,
        "warnings": warnings,
    }


async def _resolve_or_create_category(
    db: AsyncSession, user_id: int | None, name: str
) -> int:
    """按 name 取已有分类，无则新建（v1.4.3 M8，设计 §8.3「已存在同名即映射」）。

    约束换形后 name + user_id 全库唯一：同一份 CSV 里多行映射到同一「create」分类名
    时，逐行 INSERT 会在第二行撞 UNIQUE 并让整个导入 500——故先查后建，复用同名列。
    type 一律不参与匹配，新建行写占位值（D2）。
    """
    existing = (
        await db.exec(select(Category).where(Category.name == name, Category.user_id == user_id))
    ).first()
    if existing is not None:
        assert existing.id is not None  # 已落库行必有主键
        return existing.id

    category = Category(name=name, type=LEGACY_CATEGORY_TYPE, icon="mdi-circle", user_id=user_id)
    db.add(category)
    await db.flush()
    assert category.id is not None  # flush 后由自增主键回填
    return category.id


# ── 落库区（M3）：统一按「角色 → 列索引」解析每一行 ────────────────────
#
# D16：旧的两套解析 `_parse_native_row`（按**位置** 0..5 取值、完全不看表头）与
# `_parse_cashew_row`（硬编码字面量 key）已连同 `convert_cashew_*` 一并物理删除，
# **不留转发壳**。它们造成的「预览按表头名定位、导入按位置读」错位隐患
# （列序打乱的 native 文件会静默错位入库）由本区的单一角色表消除——
# 识别与落库两条链路从此共用 `csv_dialects` 的同一份表头/角色实现（D25）。

SKIPPED_REASONS: tuple[str, ...] = (
    "invalid_amount",
    "invalid_date",
    "type_ignored",
    "type_unresolved",
    "category_unresolved",
)
"""跳过原因五键（D12）：**恒在、缺省 0**。键序与前端 `SKIPPED_REASON_LABELS` 同序
（M4 取首个非零键的中文标签拼 toast），故此处不得随意调序。

v1.4.4 V3：五键**结构一字不动**，但 `category_unresolved` 自此**不再产生**、恒为 0——
分类链改以「自动同名匹配 → 全局『其他』预设」兜底收口，任何行都能拿到一个
`category_id`（`records.category_id` 自 v1.4.3 起 NOT NULL），整行跳过的旧口径作废。
该键保留是给前端 toast 文案用的向后兼容位，不得删除。
"""


def _value_by_index(row: Sequence[str], index: int | None) -> str:
    """按列下标取**原值**（只两端去空白，**不**把 `/` 归成空串）。

    与识别区 `_cell_by_index` 的分工即 D31 的两半：`/` 是**分类 / 标签 / 备注**列的空
    占位，却是**收支列**的中性交易取值（一手实测 `支出`×176 / `收入`×48 / `/`×4）。
    收支列若走 `_cell_by_index` 会被归成空串 → 该行记为 `type_unresolved` 而非
    `type_ignored`，跳过原因失真（结果同为跳过，但用户看到的解释必须准确）。
    金额列同理把原值交给 `parse_amount`（D13：`/`、`-`、`""` 自然归 None）。
    """
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _as_int(value: Any) -> int | None:
    """把映射载荷里的 id 安全转 int；不可转 / 空值 → ``None``（交由调用方计未落位）。"""
    try:
        converted = int(value)
    except (TypeError, ValueError):
        return None
    return converted or None


def _default_type_source(
    format_type: str, dialect: Dialect | None, role_index: RoleIndex
) -> str:
    """``type_source`` 缺省值（D10 / 任务 §2.1）。

    ``format_type`` 参数保留，语义 = 方言 key，**仅用于展示与本缺省**（设计 §3.5
    「`columns` 与 `format` 矛盾」行：请求 `columns` 才是权威位）：
    按 `format` 取方言预设 → 取不到则用重算出的方言 → 再退化为 `custom` 推导
    （有 type 列走 `column`，否则按金额正负）。
    """
    source_dialect = DIALECTS.get(format_type) or dialect
    if source_dialect is not None:
        return source_dialect.type_source
    return "column" if "type" in role_index else "sign"


def _validated_column_indexes(value: object, column_count: int) -> int | list[int]:
    """校验单个角色的列索引载荷并**原形返回**（int 仍是 int、list 仍是 list）。

    v1.4.4 V2：`note` 可发 `list[int]`（多列备注），其余角色仍发 `int`。
    `list` 载荷**逐元素**做同一套越界判定（空列表按「无该角色列」处理，不当越界拒绝，
    与前端把某列改成「不导入」的既有语义一致）。文案与 `PARAM_ERROR` 口径不变（§0.4-8）。

    Raises:
        ValueError: 非整数 / 布尔 / 负数 / ≥ 列数 / 列表含非法元素 → `列索引超出范围`。
    """
    if isinstance(value, bool):
        raise ValueError("列索引超出范围")
    if isinstance(value, int):
        if value < 0 or value >= column_count:
            raise ValueError("列索引超出范围")
        return value
    if isinstance(value, list):
        checked: list[int] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError("列索引超出范围")
            if item < 0 or item >= column_count:
                raise ValueError("列索引超出范围")
            checked.append(item)
        return checked
    raise ValueError("列索引超出范围")


def _authoritative_role_index(
    derived: RoleIndex, requested: RoleIndex | None, column_count: int
) -> RoleIndex:
    """列角色定稿（任务 §2.3/§2.4 + v1.4.4 V2）：请求 ``columns`` 是**权威位**。

    - 未发 `columns`（旧前端，D18）→ 用 §2.2 的重算推导值。
    - 发了 → **整体替换**推导值：前端载荷恒为「用户最终选择的全量角色 → 列索引」
      （`CsvMappingDialog.roleColumns`），缺席即代表用户把该列改成了「不导入」，
      此时再补推导值等于违背手选。
    - 只认 `ROLES` 六角色封闭集（D3）：未知键不参与解析（等价于该角色不导入），
      最终由 `REQUIRED_ROLES` 的校验兜住。
    - 值形状 `int | list[int]`（V2 只有 `note` 用得到列表）；**旧 `int` 载荷继续可用**。

    Raises:
        ValueError: 索引非整数 / 为负 / ≥ 列数 → `列索引超出范围`（转 `PARAM_ERROR`，
            **不依赖 FastAPI 422**，§0.4-8）。
    """
    if requested is None:
        return dict(derived)

    resolved: RoleIndex = {}
    for role, index in requested.items():
        if role not in ROLES:
            continue
        resolved[role] = _validated_column_indexes(index, column_count)
    return resolved


async def _apply_category_action(
    db: AsyncSession, user_id: int | None, name: str, action: Any, target_id: Any
) -> int | None:
    """把一个 `CategoryMappingItem` 形状的载荷落成 category_id；落不了 → ``None``。"""
    if action == "create":
        if not name:
            # fallback_category 只能沿用行内的分类名；空名（含 `/`，D31）不猜、
            # 不建出名为 `/` 的分类。落空后由调用方继续走 V3 链（自动匹配 → 「其他」），
            # 不再整行跳过。
            return None
        # v1.4.3 M8：type 恒写占位值（分类收支共用，映射载荷不再携带 type）；
        # 同名即复用（见 _resolve_or_create_category）。现状登记：此处不设
        # sort_order（默认 0）、未经 _next_sort_order——本期不扩范围。
        return await _resolve_or_create_category(db, user_id, name)
    return _as_int(target_id)


# ── v1.4.4 V3：分类兜底链（映射落空 / 值为空或 `/` / 用户没选，一律不再整行跳过）──

CATEGORY_SYNONYMS: dict[str, str] = {"饮食": "餐饮"}
"""自动匹配的**同义词表**（本轮只登记用户裁定的这一对，禁止凭印象扩表）。

键与值都是**归一后**的形态（`_normalize_category_name` 的产物），查找按**双向**做：
账单里的「饮食」能落到已有分类「餐饮」，反向亦然。
"""

_NAME_WS_RE = re.compile(r"\s+")


def _normalize_category_name(name: str) -> str:
    """分类名归一（V3 比对用）：NFKC → 两端去空白 → 内部连续空白折成单空格 → lower。

    与识别层 `normalize_header`（列名用，还要剥括号单位）**刻意分开**：分类名里的
    `(含税)` 之类后缀不是单位、剥了就换词了。
    """
    folded = _NAME_WS_RE.sub(" ", unicodedata.normalize("NFKC", name))
    return folded.strip().lower()


class _CategoryCandidate(NamedTuple):
    """一条可参与自动匹配的分类候选（只取必要列，不装载 ORM 实体的其余字段）。"""

    id: int
    name: str
    owned: bool  # True = 用户自有行；False = 全局预设（user_id IS NULL）


async def _category_candidates(db: AsyncSession, user_id: int | None) -> list[_CategoryCandidate]:
    """V3 自动匹配的候选集 = **用户自有分类 + 全局预设**（他人的自定义行一律排除）。

    排序口径：用户自有在前、其后按 id 升序——同名多条时「自己的」先被选中，
    与 `_resolve_import_category_by_name`（SQL 区）的既有优先级一致。
    """
    stmt = select(Category.id, Category.name, Category.user_id).where(
        or_(Category.user_id == user_id, cast("Any", Category.user_id).is_(None))
    )
    result = await db.exec(stmt)
    candidates: list[_CategoryCandidate] = []
    for row in result.all():
        category_id, name, owner_id = cast("tuple[int | None, str, int | None]", row)
        if category_id is None:  # 理论不可达：已落库行必有主键
            continue
        candidates.append(
            _CategoryCandidate(id=int(category_id), name=name, owned=owner_id == user_id)
        )
    candidates.sort(key=lambda item: (not item.owned, item.id))
    return candidates


def _auto_match_rank(value: str, name: str) -> int | None:
    """一行账单分类值与一个候选分类名的匹配档位；``None`` = 不匹配。

    档位越小越优先（V3 裁定的三档）：
      * ``0`` 归一后**相等**（同名即同一分类，M8 口径的自然延伸）；
      * ``1`` **双向包含**且两侧长度都 ≥ 2（「餐饮美食」⊇「餐饮」；单字不参与，
        否则一个「衣」字就能把整表并进别的分类）；
      * ``2`` **同义词表**命中（`CATEGORY_SYNONYMS`，双向查）。
    """
    left = _normalize_category_name(value)
    right = _normalize_category_name(name)
    if not left or not right:
        return None
    if left == right:
        return 0
    if len(left) >= 2 and len(right) >= 2 and (left in right or right in left):
        return 1
    if CATEGORY_SYNONYMS.get(left) == right or CATEGORY_SYNONYMS.get(right) == left:
        return 2
    return None


async def _match_category_auto(
    db: AsyncSession, user_id: int | None, cat_name: str
) -> int | None:
    """自动同名匹配（V3 第三档兜底）：账单分类值 → 已有分类 id；匹配不到 → ``None``。

    只在**映射与 `fallback_category` 都落空后**才跑（用户显式改道永远优先）。
    候选集每次取一次（同一次导入内由 `_resolve_row_category` 的 memo 复用到行值粒度），
    按档位最小、同级「用户自有优先、id 升序」取第一条。
    """
    if not cat_name:
        return None
    best: tuple[int, int, int] | None = None  # (档位, 自有排, id) —— 越小越优
    for order, candidate in enumerate(await _category_candidates(db, user_id)):
        rank = _auto_match_rank(cat_name, candidate.name)
        if rank is None:
            continue
        key = (rank, order, candidate.id)
        if best is None or key < best:
            best = key
    return best[2] if best is not None else None


async def _resolve_other_category_id(db: AsyncSession, user_id: int | None) -> int:
    """V3 的最后一环：全局「其他」预设分类，**恒有结果**（链在此收口，不再产 None）。

    取序：用户自有「其他」 → 全局预设「其他」（`user_id IS NULL`） → 建一个名为
    「其他」的用户分类兜底（现场库缺预设行的极端形态下仍能入库，绝不悬空）。
    """
    owned = (
        await db.exec(
            select(Category.id).where(
                Category.name == OTHER_CATEGORY_NAME, Category.user_id == user_id
            )
        )
    ).first()
    if owned is not None:
        return int(owned)
    preset = (
        await db.exec(
            select(Category.id).where(
                Category.name == OTHER_CATEGORY_NAME,
                cast("Any", Category.user_id).is_(None),
            )
        )
    ).first()
    if preset is not None:
        return int(preset)
    return await _resolve_or_create_category(db, user_id, OTHER_CATEGORY_NAME)


async def _resolve_row_category(
    db: AsyncSession,
    user_id: int | None,
    cat_name: str,
    category_mapping: dict[str, Any],
    fallback_category: dict[str, Any] | None,
    memo: dict[str, int] | None = None,
) -> int:
    """分类落位链（v1.4.4 V3）：
    ``行值 → category_mapping → fallback_category → 自动同名匹配 → 「其他」``。

    * `cat_name` 已由 `_cell_by_index` 把空串与 `/`（D31）归一为空，故「值为空或 `/`」
      与「映射落空」同样往下走链，**不再整行跳过**；
    * 行值空时跳过「自动匹配」那一环（没有可比对的名字），直接挂「其他」；
    * `create` 分支的空名（含 `/`）也归此路径 → 挂「其他」，绝不建出名为 `/` 的分类；
    * 返回值**恒不为 ``None``**（`records.category_id` NOT NULL），故
      `category_unresolved` 自本版本起不再产生（键仍在 `skipped_reasons` 里、恒为 0）。

    ``memo`` 是**单次导入内**按行值缓存结果的字典（同值不重复查库）；调用方不传即
    每次实查，语义不变。
    """
    if memo is not None and cat_name in memo:
        return memo[cat_name]

    category_id: int | None = None
    if cat_name:
        mapped = category_mapping.get(cat_name)
        if mapped:
            category_id = await _apply_category_action(
                db, user_id, cat_name, mapped.get("action"), mapped.get("target_id")
            )
    if category_id is None and fallback_category:
        category_id = await _apply_category_action(
            db,
            user_id,
            cat_name,
            fallback_category.get("action"),
            fallback_category.get("target_id"),
        )
    if category_id is None and cat_name:
        category_id = await _match_category_auto(db, user_id, cat_name)
    if category_id is None:
        category_id = await _resolve_other_category_id(db, user_id)

    if memo is not None:
        memo[cat_name] = category_id
    return category_id


async def _resolve_row_tag(
    db: AsyncSession, user_id: int | None, tag_name: str, tag_mapping: dict[str, Any]
) -> int | None:
    """标签落位（任务 §2.10）：`create` 分支补**先查后插**。

    修的是 §0.4-6 登记的既有缺陷：`tags` 表没有唯一约束，旧 CSV 分支不查重 →
    同一文件同名标签出现两次即建两行。手法对齐 SQL 路径的既有同名复用
    （`select(Tag).where(name, user_id).first()` 命中即复用），**改动仅限 CSV 分支，
    SQL 侧一字不动**（D17）。
    """
    if not tag_name:
        return None
    mapping = tag_mapping.get(tag_name)
    if not mapping:
        return None
    if mapping.get("action") == "create":
        existing = (
            await db.exec(
                select(Tag).where(Tag.name == tag_name, Tag.user_id == user_id)
            )
        ).first()
        if existing is not None:
            return existing.id
        tag = Tag(
            name=tag_name,
            category_id=mapping.get("category_id"),
            user_id=user_id,
        )
        db.add(tag)
        await db.flush()
        return tag.id
    return _as_int(mapping.get("target_id"))


async def import_csv_data(
    db: AsyncSession,
    user_id: int | None,
    cache_id: str,
    format_type: str,
    category_mapping: dict[str, Any],
    tag_mapping: dict[str, Any],
    columns: dict[str, int | list[int]] | None = None,
    type_source: str | None = None,
    fallback_category: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """确认阶段落库（CSV / xlsx **同一套代码**）：按角色取单元格 → 清洗 → 落位。

    流程（设计 §3.3）：
      1. 取回缓存原字节 → `_to_rows()`（M6 §2.5 交接的唯一容器分派器，**不自行
         `detect_and_decode` + `csv.reader`**，否则 xlsx 确认通道退回乱码）→
         `locate_header_rows` → `match_dialect` → `resolve_columns`。缓存只存原字节，
         预览的内存结果不可依赖（§0.4-9），故此处**全量重算**。
      2. 请求 `columns` 为权威位；`REQUIRED_ROLES` 未覆盖 / 索引越界 → 中文 `ValueError`。
      3. 逐行 `parse_amount` → `resolve_type` → `parse_time` → 分类 → 标签 → 入库。
      4. `amount` 入库 `round_money(abs(value))`（D13，方向只由 `type` 承载；旧
         `convert_cashew_amount` 的 abs 口径迁到此处）；`consume_time` 用 `parse_time`
         的 16 字符产物（D14），**替换旧「非空即入库」**。
      5. 返回 `{imported_count, skipped_count, skipped_reasons}`（D12）。

    v1.4.4 的两条落库口径：
      * **V2 备注**：`note` 角色涉及的**所有**列（按列索引升序）各取一次单元格
        （`/` 按空占位，D31），非空值以 `·` 连接成一条；全空 → `None`。
        `columns` 的 `note` 既可是 `int`（旧前端）也可是 `list[int]`（新前端）。
      * **V3 分类**：`_resolve_row_category` 恒给得出 id（「其他」兜底）→
        `category_unresolved` 不再计数，键仍随 `skipped_reasons` 返回、恒为 0。

    全空行按既有口径直接跳过、不计入 `skipped_count`（唯一空行判定 `_is_blank_row`，
    与 `preview_csv` 共用）。历史写入与 `delete_cache` 时机零改动。
    """
    # M6 §2.4：缓存后缀已按容器实参化，故取回按候选后缀探测、容器判定仍以字节 magic
    # 为准（D22）；`cache_suffix` 供末尾 `delete_cache` 成对使用。
    file_bytes = _read_cached_bytes(cache_id)
    cache_suffix = _cache_suffix(detect_container(file_bytes))

    rows, _container = _to_rows(file_bytes)
    header_row_index, _normalized_headers, data_rows = locate_header_rows(rows)
    raw_headers = [cell.strip() for cell in rows[header_row_index]]
    dialect = match_dialect(raw_headers)
    hints = resolve_columns(raw_headers, dialect, data_rows)
    role_index = _authoritative_role_index(
        _role_index_from_hints(hints),
        columns,
        len(raw_headers),
    )
    if any(role not in role_index for role in REQUIRED_ROLES):
        raise ValueError("缺少必需列：金额/交易时间")

    source = (
        type_source
        if type_source is not None
        else _default_type_source(format_type, dialect, role_index)
    )

    # 单列角色在循环外定一次（越界校验已在 `_authoritative_role_index` 做完）
    amount_idx = _first_index(role_index.get("amount"))
    type_idx = _first_index(role_index.get("type"))
    time_idx = _first_index(role_index.get("consume_time"))
    category_idx = _first_index(role_index.get("category"))
    tag_idx = _first_index(role_index.get("tag"))
    note_indexes = _indexes(role_index.get("note"))  # V2：可多列，升序拼接
    category_memo: dict[str, int] = {}

    imported_count = 0
    skipped_count = 0
    skipped_reasons: dict[str, int] = {reason: 0 for reason in SKIPPED_REASONS}
    imported_records: list[dict[str, Any]] = []

    def skip(reason: str) -> None:
        nonlocal skipped_count
        skipped_count += 1
        skipped_reasons[reason if reason in skipped_reasons else "type_unresolved"] += 1

    for row in data_rows:
        if _is_blank_row(row):
            continue

        amount_value = parse_amount(_value_by_index(row, amount_idx))
        if amount_value is None:
            skip("invalid_amount")
            continue

        type_str, type_reason = resolve_type(
            _value_by_index(row, type_idx), amount_value, source
        )
        if type_str is None:
            skip(type_reason or "type_unresolved")
            continue

        consume_time = parse_time(_cell_by_index(row, time_idx))
        if consume_time is None:
            skip("invalid_date")
            continue

        cat_name = _cell_by_index(row, category_idx)
        category_id = await _resolve_row_category(
            db, user_id, cat_name, category_mapping, fallback_category, category_memo
        )

        tag_name = _cell_by_index(row, tag_idx)
        tag_id = await _resolve_row_tag(db, user_id, tag_name, tag_mapping)

        note = _join_note_parts(row, note_indexes)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = Record(
            amount=round_money(abs(amount_value)),
            type=type_str,
            category_id=category_id,
            tag_id=tag_id,
            consume_time=consume_time,
            note=note or None,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        await db.flush()
        imported_records.append({
            "id": record.id,
            "amount": record.amount,
            "type": record.type,
            "category_id": record.category_id,
            "tag_id": record.tag_id,
            "consume_time": record.consume_time,
            "note": record.note,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        })
        imported_count += 1

    # Write history
    if imported_records:
        await create_history_entry(
            db, user_id, "csv_import",
            f"CSV 导入 {imported_count} 条账单",
            snapshot_after=imported_records,
        )

    await db.commit()
    delete_cache(cache_id, cache_suffix)

    logger.info(
        "csv_import done user=%s imported=%d skipped=%d reasons=%s",
        user_id,
        imported_count,
        skipped_count,
        ",".join(f"{key}={skipped_reasons[key]}" for key in SKIPPED_REASONS),
    )

    return {
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "skipped_reasons": skipped_reasons,
    }


# ── SQL Import ─────────────────────────────────────────────────────


def detect_sql_format(file_bytes: bytes) -> str:
    """Detect SQL format: text_sql | sqlite_binary | unknown."""
    if file_bytes[:16] == b"SQLite format 3\x00":
        return "sqlite_binary"
    # Check for text SQL markers
    try:
        text = file_bytes[:500].decode("utf-8", errors="ignore").strip().upper()
        if any(text.startswith(kw) for kw in ("CREATE", "INSERT", "--", "BEGIN", "PRAGMA")):
            return "text_sql"
    except Exception:
        pass
    return "unknown"


def detect_cashew_sqlite(conn: sqlite3.Connection) -> bool:
    """Detect if a SQLite database is from Cashew app."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "transactions" not in tables or "categories" not in tables:
        return False
    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(transactions)"
        ).fetchall()
    }
    return (
        "category_fk" in columns
        and "income" in columns
        and "date_created" in columns
    )


def strip_id_from_insert(sql_statement: str) -> str:
    """Remove id column from INSERT statement if present."""
    pattern = r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)"
    match = re.match(pattern, sql_statement, re.IGNORECASE | re.DOTALL)
    if not match:
        return sql_statement
    table, columns_str, values_str = match.groups()
    columns = [c.strip() for c in columns_str.split(",")]
    if "id" not in columns:
        return sql_statement
    id_index = columns.index("id")
    values = next(
        csv.reader(io.StringIO(values_str), skipinitialspace=True)
    )
    columns.pop(id_index)
    values.pop(id_index)
    return (
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(values)})"
    )


def parse_text_sql(file_content: str) -> dict[str, Any]:
    """Parse text SQL file and extract table data for preview."""
    tables: dict[str, dict[str, Any]] = {}
    statements: list[str] = []
    categories_in_file: list[str] = []
    tags_in_file: list[str] = []

    # Merge multi-line statements
    current_stmt = ""
    for line in file_content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current_stmt += " " + stripped
        if stripped.endswith(";"):
            stmt = current_stmt.strip()
            statements.append(stmt)
            current_stmt = ""

            # Extract table info
            upper = stmt.upper()
            if upper.startswith("INSERT"):
                m = re.match(
                    r"INSERT\s+INTO\s+(\w+)", stmt, re.IGNORECASE
                )
                if m:
                    table_name = m.group(1)
                    if table_name not in tables:
                        tables[table_name] = {"count": 0, "sample": []}
                    tables[table_name]["count"] += 1

                    # Extract category/tag names for mapping
                    values = _extract_values(stmt)
                    if table_name == "categories" and values:
                        name = _unquote(values.get("name", ""))
                        if name:
                            categories_in_file.append(name)
                    elif table_name == "tags" and values:
                        name = _unquote(values.get("name", ""))
                        if name:
                            tags_in_file.append(name)
            elif upper.startswith("CREATE TABLE"):
                m = re.match(
                    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
                    stmt,
                    re.IGNORECASE,
                )
                if m:
                    table_name = m.group(1)
                    if table_name not in tables:
                        tables[table_name] = {"count": 0, "sample": []}

    return {
        "tables": tables,
        "statements": statements,
        "categories_in_file": categories_in_file,
        "tags_in_file": tags_in_file,
    }


def parse_sqlite_file(file_bytes: bytes) -> dict[str, Any]:
    """Parse SQLite file and extract table data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        is_cashew = detect_cashew_sqlite(conn)

        tables: dict[str, dict[str, Any]] = {}
        categories_in_file: list[str] = []
        tags_in_file: list[str] = []

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table_name in table_names:
            cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]
            tables[table_name] = {"count": count, "sample": []}

            # Get sample rows
            cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 3")
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                tables[table_name]["sample"].append(
                    dict(zip(columns, row))
                )

        # Extract category and tag names for mapping
        if is_cashew:
            # Cashew: categories from 'categories' table, tags from transaction 'name'
            try:
                rows = conn.execute("SELECT name FROM categories").fetchall()
                categories_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass
            try:
                rows = conn.execute(
                    "SELECT DISTINCT name FROM transactions WHERE name != ''"
                ).fetchall()
                tags_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass
        else:
            # Standard SQLite
            try:
                rows = conn.execute("SELECT name FROM categories").fetchall()
                categories_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass
            try:
                rows = conn.execute("SELECT name FROM tags").fetchall()
                tags_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass

        conn.close()
        return {
            "tables": tables,
            "is_cashew": is_cashew,
            "categories_in_file": categories_in_file,
            "tags_in_file": tags_in_file,
        }
    finally:
        import os

        os.unlink(tmp_path)


async def preview_sql(
    db: AsyncSession, file_bytes: bytes
) -> dict[str, Any]:
    """Preview SQL import."""
    format_type = detect_sql_format(file_bytes)
    if format_type == "unknown":
        raise ValueError("不支持的文件格式")

    is_third_party = False
    categories_in_file: list[str] = []
    tags_in_file: list[str] = []

    if format_type == "text_sql":
        content = file_bytes.decode("utf-8", errors="replace")
        parsed = parse_text_sql(content)
        tables_info = parsed["tables"]
        categories_in_file = parsed.get("categories_in_file", [])
        tags_in_file = parsed.get("tags_in_file", [])
    else:  # sqlite_binary
        parsed = parse_sqlite_file(file_bytes)
        tables_info = parsed["tables"]
        is_third_party = parsed.get("is_cashew", False)
        categories_in_file = parsed.get("categories_in_file", [])
        tags_in_file = parsed.get("tags_in_file", [])

    # Cache the file
    suffix = ".sql" if format_type == "text_sql" else ".db"
    cache_id = save_to_cache(file_bytes, suffix)

    return {
        "format": format_type,
        "is_third_party": is_third_party,
        "tables": tables_info,
        "cache_id": cache_id,
        "categories_in_file": categories_in_file,
        "tags_in_file": tags_in_file,
    }


async def import_sql_data(
    db: AsyncSession,
    user_id: int | None,
    cache_id: str,
    format_type: str,
    is_third_party: bool = False,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import SQL data within a transaction."""
    suffix = ".sql" if format_type == "text_sql" else ".db"
    file_bytes = read_from_cache(cache_id, suffix)

    try:
        logger.info(
            "sql_import start user=%s format=%s third_party=%s",
            user_id, format_type, is_third_party,
        )
        if format_type == "text_sql":
            result = await _import_text_sql(
                db, user_id, file_bytes, category_mapping, tag_mapping
            )
        else:
            result = await _import_sqlite_binary(
                db, user_id, file_bytes, is_third_party,
                category_mapping, tag_mapping
            )

        # Write history
        await create_history_entry(
            db, user_id, "sql_import",
            f"SQL 导入 {result.get('records_imported', 0)} 条账单",
            snapshot_after=result.get("imported_records", []),
        )

        await db.commit()
        delete_cache(cache_id, suffix)
        logger.info(
            "sql_import done user=%s records=%d",
            user_id, result.get("records_imported", 0),
        )
        return result
    except Exception:
        await db.rollback()
        logger.exception("sql_import failed user=%s", user_id)
        raise


async def _import_text_sql(
    db: AsyncSession,
    user_id: int | None,
    file_bytes: bytes,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import from text SQL file."""
    content = file_bytes.decode("utf-8", errors="replace")
    parsed = parse_text_sql(content)
    statements = parsed["statements"]

    records_imported = 0
    imported_records: list[dict[str, Any]] = []
    category_map: dict[int, int] = {}  # old_id -> new_id
    tag_map: dict[int, int] = {}
    budget_map: dict[int, int] = {}  # old budget id -> new id（v1.4.3 M12 关联表用）

    for stmt in statements:
        upper = stmt.upper().strip()

        if upper.startswith("CREATE TABLE"):
            continue  # Skip CREATE TABLE

        if not upper.startswith("INSERT"):
            continue

        # Extract table name and old id before stripping
        m = re.match(r"INSERT\s+INTO\s+(\w+)", stmt, re.IGNORECASE)
        if not m:
            continue
        table_name = m.group(1)

        # Get old id from values if present
        values = _extract_values(stmt)
        old_id = _parse_int(values.get("id"))

        # Strip id if present
        stmt = strip_id_from_insert(stmt)

        if table_name == "categories":
            new_id = await _import_category_stmt(db, user_id, stmt)
            if new_id:
                records_imported += 1
                if old_id:
                    category_map[old_id] = new_id
        elif table_name == "tags":
            new_id = await _import_tag_stmt(db, user_id, stmt, category_map)
            if new_id:
                records_imported += 1
                if old_id:
                    tag_map[old_id] = new_id
        elif table_name == "records":
            record_data = await _import_record_stmt(
                db, user_id, stmt, category_map, tag_map
            )
            if record_data:
                imported_records.append(record_data)
                records_imported += 1
        elif table_name == "budgets":
            new_id = await _import_budget_stmt(db, user_id, stmt, category_map)
            if new_id and old_id:
                budget_map[old_id] = new_id
            records_imported += 1
        elif table_name == "budget_categories":
            await _import_budget_category_stmt(
                db, stmt, budget_map, category_map, user_id
            )
            records_imported += 1
        elif table_name == "quick_templates":
            await _import_quick_template_stmt(
                db, user_id, stmt, category_map, tag_map
            )
            records_imported += 1

    return {
        "records_imported": len(imported_records),
        "total_imported": records_imported,
        "imported_records": imported_records,
    }


async def _import_category_stmt(
    db: AsyncSession, user_id: int | None, stmt: str
) -> int | None:
    """Import a category from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return None

    # Parse category fields
    name = _unquote(values.get("name", ""))
    icon = _unquote(values.get("icon", "mdi-circle"))

    # v1.4.3 M8（设计 §8.3）：匹配仅按 name、type 一律忽略。旧文件里同名
    # income/expense 两分类在新库撞 name 唯一 → 由「已存在同名即映射」自然消解。
    existing = await db.exec(
        select(Category).where(
            Category.name == name,
            Category.user_id == user_id,
        )
    )
    existing_cat = existing.first()
    if existing_cat:
        return existing_cat.id

    category = Category(
        name=name,
        type=LEGACY_CATEGORY_TYPE,
        icon=icon,
        user_id=user_id,
    )
    db.add(category)
    await db.flush()
    return category.id


async def _import_tag_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
) -> int | None:
    """Import a tag from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return None

    name = _unquote(values.get("name", ""))
    category_id = _parse_int(values.get("category_id"))

    # Map old category ID to new ID
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)

    # Check for existing tag
    existing = await db.exec(
        select(Tag).where(
            Tag.name == name,
            Tag.user_id == user_id,
        )
    )
    existing_tag = existing.first()
    if existing_tag:
        return existing_tag.id

    tag = Tag(
        name=name,
        category_id=category_id,
        user_id=user_id,
    )
    db.add(tag)
    await db.flush()
    return tag.id


async def _import_record_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
    tag_map: dict[int, int] | None = None,
) -> dict[str, Any] | None:
    """Import a record from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return None

    amount = _parse_float(values.get("amount"))
    rec_type = _unquote(values.get("type", ""))
    category_id = _parse_int(values.get("category_id"))
    tag_id = _parse_int(values.get("tag_id"))
    consume_time = _unquote(values.get("consume_time", ""))
    note = _unquote(values.get("note", ""))
    created_at = _unquote(values.get("created_at", ""))
    updated_at = _unquote(values.get("updated_at", ""))

    # Map old IDs to new IDs
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)
    if tag_map and tag_id:
        tag_id = tag_map.get(tag_id, tag_id)

    if not amount or rec_type not in ("income", "expense"):
        return None
    if not category_id or not consume_time:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = Record(
        amount=amount,
        type=rec_type,
        category_id=category_id,
        tag_id=tag_id,
        consume_time=consume_time,
        note=note or None,
        user_id=user_id,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
    db.add(record)
    await db.flush()
    return {
        "id": record.id,
        "amount": record.amount,
        "type": record.type,
        "category_id": record.category_id,
        "tag_id": record.tag_id,
        "consume_time": record.consume_time,
        "note": record.note,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


async def _resolve_import_category_id(
    db: AsyncSession, raw_id: int | None, category_map: dict[int, int] | None
) -> int | None:
    """把备份里的 ``category_id`` 解析到本库真实存在的分类行。

    1. 优先用导入过程建立的 old_id → new_id 映射；
    2. 无映射时仅接受指向**预设行**的 id（预设 id 跨安装稳定）；
    3. 否则返回 None——绝不把自定义分类的旧 id 挂到同 id 的无关分类上。
    """
    if raw_id is None:
        return None
    mapped = category_map.get(raw_id) if category_map else None
    if mapped:
        return mapped
    row = await db.get(Category, raw_id)
    if row is not None and row.is_preset == 1:
        return raw_id
    return None


async def _resolve_import_category_by_name(
    db: AsyncSession, name: str, user_id: int | None
) -> int | None:
    """按分类**名**落位（M8 口径「同名即同一分类」）：先本人自建同名，再同名预设。

    预算关联行的分类 id 在跨库导入时几乎必然失配（categories 段不带 id、预设段
    不导出），故导出侧双写了名字；两侧都解析不到才宁可丢这一条关联。
    """
    if not name:
        return None
    rows = list((await db.exec(select(Category).where(Category.name == name))).all())
    target = next((c for c in rows if c.user_id == user_id), None) or next(
        (c for c in rows if c.is_preset == 1), None
    )
    if target is None or target.id is None:
        return None
    return int(target.id)


async def _create_budget_from_values(
    db: AsyncSession,
    user_id: int | None,
    values: dict[str, str],
    category_map: dict[int, int] | None = None,
) -> int | None:
    """按列值建预算行（文本 SQL 与 .db 文件两条导入路径共用）。

    v1.4.3 M12 起预算为「名称 + 月份 + 金额 + 范围模式」+ 关联表；
    M12 之前的旧备份行只有 ``category_id``，此处一并兼容：
    分类可解析 → 建 include 单分类预算；不可解析 → 落成与迁移阶段 B 同款的
    「未知分类」只读态（include + 空关联，可展示可删、重保存需补选分类）。
    """
    amount = _parse_float(values.get("amount"))
    month = _unquote(values.get("month", ""))
    if not amount or not _MONTH_RE.match(month):
        return None

    scope_raw = _unquote(values.get("scope_mode", SCOPE_INCLUDE)) or SCOPE_INCLUDE
    scope_mode = scope_raw if scope_raw in SCOPE_MODES else SCOPE_INCLUDE
    # v1.4.3-boot2 M3：休眠标志随 budgets 导出列往返；旧备份无该列 → 0（动态全部/未知分类态）
    dormant = 1 if _parse_int(values.get("dormant")) == 1 else 0
    name = _unquote(values.get("name", "")).strip()

    legacy_category_id: int | None = None
    if not name:
        legacy_category_id = await _resolve_import_category_id(
            db, _parse_int(values.get("category_id")), category_map
        )
        if legacy_category_id is not None:
            category = await db.get(Category, legacy_category_id)
            name = category.name if category else UNKNOWN_CATEGORY_NAME
        else:
            name = UNKNOWN_CATEGORY_NAME

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    budget = Budget(
        user_id=user_id,
        name=name[:50],
        month=month,
        amount=round_money(amount),
        scope_mode=scope_mode,
        dormant=dormant,
        created_at=now,
        updated_at=now,
    )
    db.add(budget)
    await db.flush()
    if legacy_category_id is not None and budget.id is not None:
        db.add(BudgetCategory(budget_id=budget.id, category_id=legacy_category_id))
        await db.flush()
    return budget.id


async def _import_budget_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
) -> int | None:
    """Import a budget from an INSERT statement。返回新行 id（供关联表重映射）。"""
    values = _extract_values(stmt)
    if not values:
        return None
    return await _create_budget_from_values(db, user_id, values, category_map)


async def _link_budget_category(
    db: AsyncSession, budget_id: int, category_id: int
) -> None:
    """写入一条预算关联（幂等：撞 UNIQUE (budget_id, category_id) 即跳过）。"""
    existing = await db.exec(
        select(BudgetCategory).where(
            BudgetCategory.budget_id == budget_id,
            BudgetCategory.category_id == category_id,
        )
    )
    if existing.first():
        return
    db.add(BudgetCategory(budget_id=budget_id, category_id=category_id))
    await db.flush()


async def _import_budget_category_stmt(
    db: AsyncSession,
    stmt: str,
    budget_map: dict[int, int],
    category_map: dict[int, int] | None = None,
    user_id: int | None = None,
) -> None:
    """Import a budget_categories link row（两侧 id 均需重映射）。

    分类侧解析顺序：导入过程的 id 映射 → 备份里的 **同名**分类（本人自建优先、
    其次同名预设）→ 仅指向预设行的裸 id（M12 之前的旧行无名字）。
    预算侧映射不到即跳过——宁缺不悬：留下指向他人/不存在预算的关联行会污染卡片。
    """
    values = _extract_values(stmt)
    if not values:
        return
    new_budget_id = budget_map.get(_parse_int(values.get("budget_id")) or 0)
    raw_category_id = _parse_int(values.get("category_id"))
    category_id = (category_map or {}).get(raw_category_id or 0)
    if category_id is None:
        category_id = await _resolve_import_category_by_name(
            db, _unquote(values.get("category_name", "")), user_id
        )
    if category_id is None:
        category_id = await _resolve_import_category_id(db, raw_category_id, None)
    if not new_budget_id or not category_id:
        return
    await _link_budget_category(db, new_budget_id, category_id)


async def _import_quick_template_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
    tag_map: dict[int, int] | None = None,
) -> None:
    """Import a quick template from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return

    tag_id = _parse_int(values.get("tag_id"))
    category_id = _parse_int(values.get("category_id"))
    qt_type = _unquote(values.get("type", "expense"))
    amount = _parse_float(values.get("amount"))

    # Map old IDs to new IDs
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)
    if tag_map and tag_id:
        tag_id = tag_map.get(tag_id, tag_id)

    if not amount:
        return

    qt = QuickTemplate(
        user_id=user_id,
        tag_id=tag_id,
        category_id=category_id,
        type=qt_type,
        amount=amount,
    )
    db.add(qt)
    await db.flush()


async def _import_sqlite_binary(
    db: AsyncSession,
    user_id: int | None,
    file_bytes: bytes,
    is_third_party: bool,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import from SQLite binary file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row

        records_imported = 0
        imported_records: list[dict[str, Any]] = []

        if is_third_party:
            # Cashew format
            result = await _import_cashew_sqlite(
                db, user_id, conn, category_mapping, tag_mapping
            )
            conn.close()
            return result

        # Standard SQLite import
        # Import categories
        try:
            rows = conn.execute("SELECT * FROM categories").fetchall()
            for row in rows:
                name = row["name"]
                icon = row["icon"]

                # v1.4.3 M8（任务 4.4）：匹配仅按 name、源库 type 一律忽略
                existing = await db.exec(
                    select(Category).where(
                        Category.name == name,
                        Category.user_id == user_id,
                    )
                )
                if not existing.first():
                    category = Category(
                        name=name,
                        type=LEGACY_CATEGORY_TYPE,
                        icon=icon,
                        user_id=user_id,
                    )
                    db.add(category)
                    await db.flush()
        except sqlite3.OperationalError:
            pass

        # Import tags
        try:
            rows = conn.execute("SELECT * FROM tags").fetchall()
            for row in rows:
                name = row["name"]
                category_id = row["category_id"] if "category_id" in row.keys() else None

                existing = await db.exec(
                    select(Tag).where(
                        Tag.name == name,
                        Tag.user_id == user_id,
                    )
                )
                if not existing.first():
                    tag = Tag(
                        name=name,
                        category_id=category_id,
                        user_id=user_id,
                    )
                    db.add(tag)
                    await db.flush()
        except sqlite3.OperationalError:
            pass

        # Import records
        try:
            rows = conn.execute("SELECT * FROM records").fetchall()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for row in rows:
                amount = row["amount"]
                rec_type = row["type"]
                category_id = row["category_id"]
                tag_id = row["tag_id"] if "tag_id" in row.keys() else None
                consume_time = row["consume_time"]
                note = row["note"] if "note" in row.keys() else None
                created_at = row["created_at"] if "created_at" in row.keys() else now
                updated_at = row["updated_at"] if "updated_at" in row.keys() else now

                if not amount or rec_type not in ("income", "expense"):
                    continue
                if not category_id or not consume_time:
                    continue

                record = Record(
                    amount=round_money(amount),
                    type=rec_type,
                    category_id=category_id,
                    tag_id=tag_id,
                    consume_time=consume_time,
                    note=note,
                    user_id=user_id,
                    created_at=created_at or now,
                    updated_at=updated_at or now,
                )
                db.add(record)
                await db.flush()
                imported_records.append({
                    "id": record.id,
                    "amount": record.amount,
                    "type": record.type,
                    "category_id": record.category_id,
                    "tag_id": record.tag_id,
                    "consume_time": record.consume_time,
                    "note": record.note,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                })
                records_imported += 1
        except sqlite3.OperationalError:
            pass

        # Import budgets（v1.4.3 M12：命名预算 + 关联表，列值解析与文本 SQL 路径共用）
        budget_map: dict[int, int] = {}  # 备份库原 id -> 本库新 id
        try:
            rows = conn.execute("SELECT * FROM budgets").fetchall()
            for row in rows:
                values = {k: str(row[k]) for k in row.keys() if row[k] is not None}
                old_id = _parse_int(values.get("id"))
                new_id = await _create_budget_from_values(db, user_id, values)
                if old_id and new_id:
                    budget_map[old_id] = new_id
        except sqlite3.OperationalError:
            pass

        try:
            links = conn.execute("SELECT * FROM budget_categories").fetchall()
            for link in links:
                keys = link.keys()
                if "budget_id" not in keys or "category_id" not in keys:
                    continue
                new_budget_id = budget_map.get(_parse_int(str(link["budget_id"])) or 0)
                if not new_budget_id:
                    continue
                # 本路径的分类匹配沿 M8 口径「仅按 name」（源库仍在 conn 上可读）：
                # 先取源分类名，再落到本用户同名分类，其次同名预设
                src_cat = conn.execute(
                    "SELECT name FROM categories WHERE id = ?", (link["category_id"],)
                ).fetchone()
                if src_cat is None:
                    continue
                same_name = (
                    await db.exec(select(Category).where(Category.name == str(src_cat[0])))
                ).all()
                target = next(
                    (c for c in same_name if c.user_id == user_id),
                    None,
                ) or next((c for c in same_name if c.is_preset == 1), None)
                if target is None or target.id is None:
                    continue
                await _link_budget_category(db, new_budget_id, int(target.id))
        except sqlite3.OperationalError:
            pass  # M12 之前的备份库无此表

        # Import quick templates
        try:
            rows = conn.execute("SELECT * FROM quick_templates").fetchall()
            for row in rows:
                qt = QuickTemplate(
                    user_id=user_id,
                    tag_id=row["tag_id"] if "tag_id" in row.keys() else None,
                    category_id=row["category_id"] if "category_id" in row.keys() else None,
                    type=row["type"],
                    amount=round_money(row["amount"]),
                )
                db.add(qt)
                await db.flush()
        except sqlite3.OperationalError:
            pass

        conn.close()
        return {
            "records_imported": records_imported,
            "total_imported": records_imported,
            "imported_records": imported_records,
        }
    finally:
        import os

        os.unlink(tmp_path)


async def _import_cashew_sqlite(
    db: AsyncSession,
    user_id: int | None,
    conn: sqlite3.Connection,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import from Cashew SQLite database."""
    # Build category mapping: cashew_id -> category_name
    # Cashew uses 'category_pk' as primary key
    cashew_categories: dict[str, str] = {}
    rows = conn.execute("SELECT * FROM categories").fetchall()
    for row in rows:
        pk = str(row["category_pk"])
        cashew_categories[pk] = row["name"]

    records_imported = 0
    imported_records: list[dict[str, Any]] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Import transactions
    rows = conn.execute("SELECT * FROM transactions").fetchall()
    for row in rows:
        # Map fields
        amount = round_money(abs(float(row["amount"]))) if row["amount"] else 0
        rec_type = "income" if row["income"] == 1 else "expense"
        tag_name = row["name"] if row["name"] else ""
        note = row["note"] if row["note"] else ""

        # Convert Unix timestamp (Cashew stores in seconds)
        date_created = row["date_created"]
        if isinstance(date_created, (int, float)):
            # Handle both seconds and milliseconds
            if date_created > 1e12:
                date_created = date_created / 1000
            consume_time = datetime.fromtimestamp(date_created).strftime(
                "%Y-%m-%d %H:%M"
            )
        else:
            consume_time = str(date_created)[:16]

        # Resolve category
        cashew_cat_id = str(row["category_fk"])
        cat_name = cashew_categories.get(cashew_cat_id, "")
        category_id = None

        if cat_name:
            # Check mapping first
            if category_mapping and cat_name in category_mapping:
                cat_map = category_mapping[cat_name]
                if cat_map.get("action") == "create":
                    # v1.4.3 M8：新建分类恒写占位 type（原取映射 type / 交易 rec_type），
                    # 同名即复用
                    category_id = await _resolve_or_create_category(db, user_id, cat_name)
                else:
                    category_id = cat_map.get("target_id")
            else:
                # Auto-match by name（匹配不上即按 name 新建，type 不参与匹配）
                category_id = await _resolve_or_create_category(db, user_id, cat_name)

        if not category_id:
            continue

        # Resolve tag
        tag_id = None
        if tag_name:
            # Check mapping first
            if tag_mapping and tag_name in tag_mapping:
                t_map = tag_mapping[tag_name]
                if t_map.get("action") == "create":
                    new_tag = Tag(
                        name=tag_name,
                        category_id=t_map.get("category_id", category_id),
                        user_id=user_id,
                    )
                    db.add(new_tag)
                    await db.flush()
                    tag_id = new_tag.id
                else:
                    tag_id = t_map.get("target_id")
            else:
                # Auto-match by name
                existing = await db.exec(
                    select(Tag).where(
                        Tag.name == tag_name,
                        Tag.user_id == user_id,
                    )
                )
                tag = existing.first()
                if tag:
                    tag_id = tag.id
                else:
                    new_tag = Tag(
                        name=tag_name,
                        category_id=category_id,
                        user_id=user_id,
                    )
                    db.add(new_tag)
                    await db.flush()
                    tag_id = new_tag.id

        record = Record(
            amount=amount,
            type=rec_type,
            category_id=category_id,
            tag_id=tag_id,
            consume_time=consume_time,
            note=note or None,
            user_id=user_id,
            created_at=now,
            updated_at=None,
        )
        db.add(record)
        await db.flush()
        imported_records.append({
            "id": record.id,
            "amount": record.amount,
            "type": record.type,
            "category_id": record.category_id,
            "tag_id": record.tag_id,
            "consume_time": record.consume_time,
            "note": record.note,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        })
        records_imported += 1

    conn.close()
    return {
        "records_imported": records_imported,
        "total_imported": records_imported,
        "imported_records": imported_records,
    }


def _extract_values(stmt: str) -> dict[str, str]:
    """Extract column=value pairs from an INSERT statement."""
    pattern = r"INSERT\s+INTO\s+\w+\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)"
    match = re.match(pattern, stmt, re.IGNORECASE | re.DOTALL)
    if not match:
        return {}

    columns_str, values_str = match.groups()
    columns = [c.strip() for c in columns_str.split(",")]
    values = list(csv.reader(io.StringIO(values_str), skipinitialspace=True))

    if not values:
        return {}

    result = {}
    for i, col in enumerate(columns):
        if i < len(values[0]):
            result[col] = values[0][i].strip()
    return result


def _unquote(value: str) -> str:
    """Remove surrounding single quotes from a value."""
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def _parse_int(value: str | None) -> int | None:
    """Parse an integer value, returning None for NULL."""
    if not value or value.upper() == "NULL":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_float(value: str | None) -> float | None:
    """Parse a float value, returning None for NULL."""
    if not value or value.upper() == "NULL":
        return None
    try:
        return round_money(float(value))
    except (ValueError, TypeError):
        return None
