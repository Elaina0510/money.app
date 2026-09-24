"""CSV 方言与列角色识别（v1.4.3-boot3 M1，设计 §1.2.1）。

**纯数据 + 纯函数模块**：零 ORM、零 DB、不 import 项目内任何其他模块（M1 §1.6 禁反向依赖）。
职责链：列名归一 → 表头行定位 → 方言匹配 → 逐列角色建议。
**不做任何单元格值解析**（金额/日期/收支三态属 M2 清洗层），**不碰数据库**（落库属 M3）。

行矩阵契约（D25，交接 M6）：
    「字节 → 文本 → 行矩阵」由 `import_service` 负责（`detect_and_decode` + `csv_rows`）；
    本模块的 `locate_header_rows` **只吃行矩阵**（`list[list[str]]`），不吃文本、不吃字节，
    因此 CSV 与 xlsx（M6 的 `xlsx_rows()`）**共用同一套**定位 / 评分 / 角色算法，
    任何一侧都不得另写第二份表头逻辑。
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

# ── 角色常量（D3 封闭集，六值；禁止实现期扩键） ─────────────────────

ROLES: tuple[str, ...] = ("consume_time", "amount", "type", "category", "tag", "note")

REQUIRED_ROLES: tuple[str, ...] = ("consume_time", "amount")
"""导入必需的角色（M1 §1.1）。唯一消费方在 M3 §2.4 的显式校验；本模块只定义并导出。"""

ROLE_LABELS: dict[str, str] = {
    "consume_time": "交易时间",
    "amount": "金额",
    "type": "收/支",
    "category": "分类",
    "tag": "标签",
    "note": "备注",
}
"""角色 → 中文展示名，仅用于 `warnings` 文案（用户可见处不出现 `consume_time` 之类内部术语）。"""

CELL_PLACEHOLDERS: frozenset[str] = frozenset({"/"})
"""空占位符集合（D31，一手实测：真实微信账单的 `备注`/`商户单号` 大量为 `/`）。

`resolve_columns` 的 `sample`、预览的 `categories_in_file`/`tags_in_file` 一律按空串处理。
**收支列的 `/` 判为中性交易属 M2 `TYPE_VALUE_IGNORE`**，本模块不判值语义。
"""

# ── 列名别名表（B 需求的内置别名；逐键钉死，禁止凭印象扩键） ─────────

COLUMN_ALIASES: dict[str, str] = {
    # amount
    "amount": "amount",
    "金额": "amount",
    # consume_time
    "consume_time": "consume_time",
    "date": "consume_time",
    "交易时间": "consume_time",
    "日期": "consume_time",
    "时间": "consume_time",
    # type
    "type": "type",
    "income": "type",
    "收/支": "type",
    "收支": "type",
    # category
    "category_name": "category",
    "category": "category",
    "交易分类": "category",
    # tag
    "tag_name": "tag",
    "title": "tag",
    "交易对方": "tag",
    # note
    "note": "note",
    "备注": "note",
    "商品": "note",
    "商品说明": "note",
}
"""归一化列名 → 角色。

- `金额(元)` 经 `normalize_header` 落 `金额` 键，故**不重复登记**带单位形态（D4 防死键）。
- `交易类型`（微信的资金渠道列）**故意不在表内**（D9：它不是分类，登记即污染）。
- 空列名归一为 `""` 且不落任何键 → 天然 `role=None`（M1 §2.2）。
"""

# ── 列名归一化（D4 五步，顺序不可换） ──────────────────────────────

_UNIT_CHARS = "元角分块厘￥¥$美金美元人民币円cnyusdgbpeurjpykrahkdamount单位:：.0123456789"
# 步骤 4：只剥**结尾**的「括号单位」，且一次剥完整条单位链（`(元)(元)` 一次剥净）——
# 单遍只剥一组时 `收入(含税)(元)` 的第二次调用会再剥 `(含税)`，破坏幂等（M1 §2.3）。
# 非单位的结尾括号（`商品(说明)`、`收入(含税)`）一律保留，中间括号更不可能被误伤。
_TRAILING_UNIT_RE = re.compile(
    r"(?:\s*[(（\[【][" + _UNIT_CHARS + r"]*[)）\]】])+\s*$",
    re.IGNORECASE,
)
_INTERNAL_WS_RE = re.compile(r"\s+")


def normalize_header(header: str) -> str:
    """列名归一化：剥 BOM → NFKC → 两端 strip → 剥结尾括号单位 → 折叠内部空白 → lower。

    五步顺序即语义（D4）：**NFKC 必须在剥括号之前**，否则全角 `金额（元）` 剥不掉。
    结尾括号正则**只锚定末尾**且只认「单位」（`金额(元)`→`金额`、`收入(含税)(元)`→`收入(含税)`）。
    折叠内部连续空白为**单**空格，故 `category name` 的空格得以保留（M1 §2.2）。
    幂等：`normalize_header(normalize_header(h)) == normalize_header(h)`（M1 §2.3）。
    """
    text = header.replace("\ufeff", "")
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    text = _TRAILING_UNIT_RE.sub("", text)
    text = _INTERNAL_WS_RE.sub(" ", text)
    return text.strip().lower()


# ── 方言数据表（D5/D6/D9，只内置五个） ─────────────────────────────


@dataclass(frozen=True)
class Dialect:
    """一个内置 CSV 方言：判定所需列集 + 逐列角色预设 + 收支判定预设。"""

    key: str
    label: str
    required: frozenset[str]
    roles: dict[str, str]
    type_source: str


NATIVE = Dialect(
    key="native",
    label="本系统格式",
    # 严格集合相等（见 match_dialect），保持现状 :53-55 语义不破回归（D5）
    required=frozenset(
        {"amount", "type", "category_name", "tag_name", "consume_time", "note"}
    ),
    roles={
        "amount": "amount",
        "type": "type",
        "category_name": "category",
        "tag_name": "tag",
        "consume_time": "consume_time",
        "note": "note",
    },
    type_source="column",
)

CASHEW = Dialect(
    key="cashew",
    label="Cashew 全量导出",
    required=frozenset({"title", "category name"}),
    # 由现存死常量 `CASHEW_COLUMN_MAP` 逐条平移（D16 激活）；
    # `CASHEW_IGNORED_COLUMNS`（subcategory name/account/currency/wallet）
    # 平移为「不在 roles 即无角色」的自然结果（无消费方的丢弃即默认行为）。
    roles={
        "title": "tag",
        "category name": "category",
        "amount": "amount",
        "income": "type",
        "note": "note",
        "date": "consume_time",
    },
    type_source="column",
)

CASHEW_TEMPLATE = Dialect(
    key="cashew_template",
    label="Cashew 导入模板",
    required=frozenset({"date", "amount", "category", "title"}),
    # `account` 无角色（roles 未登记即丢弃）
    roles={
        "date": "consume_time",
        "amount": "amount",
        "category": "category",
        "title": "tag",
        "note": "note",
    },
    type_source="sign",
)

ALIPAY = Dialect(
    key="alipay",
    label="支付宝账单",
    required=frozenset({"交易时间", "交易分类", "金额", "收/支"}),
    # 丢弃列：对方账号 / 收/付款方式 / 交易状态 / 交易订单号 / 商家订单号 / 备注（D9）
    roles={
        "交易时间": "consume_time",
        "交易分类": "category",
        "金额": "amount",
        "收/支": "type",
        "交易对方": "tag",
        "商品说明": "note",
    },
    type_source="column",
)

WECHAT = Dialect(
    key="wechat",
    label="微信账单",
    required=frozenset({"交易时间", "金额", "收/支"}),
    # `金额(元)` 经归一化落 `金额` 键（D4）。
    # 丢弃列：交易类型（资金渠道，非分类）/ 支付方式 / 当前状态 / 交易单号 /
    #         商户单号 / 备注（D9：`商品` 信息量高于常为 `/` 的 `备注`）。
    roles={
        "交易时间": "consume_time",
        "金额": "amount",
        "收/支": "type",
        "交易对方": "tag",
        "商品": "note",
    },
    type_source="column",
)

DIALECTS: dict[str, Dialect] = {
    dialect.key: dialect
    for dialect in (NATIVE, CASHEW, CASHEW_TEMPLATE, ALIPAY, WECHAT)
}

DIALECT_ORDER: tuple[str, ...] = ("native", "cashew", "cashew_template", "alipay", "wechat")
"""方言匹配顺序，**顺序即正确性**（D5）。

`alipay` **必须先于** `wechat`：支付宝的必要列集 `{交易时间, 交易分类, 金额, 收/支}`
是微信必要列集 `{交易时间, 金额, 收/支}` 的**超集**，一旦倒序，支付宝表头会先命中
微信的宽松判据 → 被判成 `wechat` → `交易分类` 不在微信 roles 里 → **分类列被丢掉**，
用户只能看到「无分类列」。倒序的后果由 `test_csv_dialects.py` §8.4 显式取证。
"""


def dialects_in_order(order: Sequence[str] = DIALECT_ORDER) -> tuple[Dialect, ...]:
    """按 key 顺序取方言实例；未知 key 直接报错（防止 `DIALECT_ORDER` 与数据表漂移）。"""
    return tuple(DIALECTS[key] for key in order)


# ── 单元格与表头定位 ───────────────────────────────────────────────


def is_blank_cell(value: str) -> bool:
    """空占位判定（M1 §5.5/D31）：`""`、纯空白与 `/` 都算空。"""
    stripped = value.strip()
    return stripped == "" or stripped in CELL_PLACEHOLDERS


def header_score(row: Sequence[str]) -> int:
    """一行作为表头的评分 = 「归一化后命中 `COLUMN_ALIASES` 的**非空**单元格数」（D2）。

    **逐格精确匹配（归一后全等），禁止子串匹配**——前导说明行（`微信昵称：[xxx]`、
    `----分隔线----`、`收入：48笔 0.35元`）都是单非空格，评分必然为 0。
    """
    return sum(
        1
        for cell in row
        if not is_blank_cell(cell) and normalize_header(cell) in COLUMN_ALIASES
    )


def locate_header_rows(
    rows: Sequence[Sequence[str]],
    max_scan: int = 50,
) -> tuple[int, list[str], list[list[str]]]:
    """在**行矩阵**里按内容定位表头行（D1/D2/D25）。

    Args:
        rows: 行矩阵 `list[list[str]]`（CSV 由 `import_service.csv_rows()` 产出、
            xlsx 由 M6 `xlsx_rows()` 产出）。**不是文本、不是字节**。
        max_scan: 只扫前 `max_scan` 行；禁止任何 `skiprows=固定值`（前导行数必然
            漂移：一手真实微信 xlsx 实测 17 行、调研微信 CSV 16 行、支付宝 24 行）。

    Returns:
        `(表头行下标, 归一化表头, 表头之后的全部数据行)`。
        - 评分最高者胜出，**同分取靠前行**；
        - 全部行评分为 0 → 退化为「第一个非空单元格数 ≥ 2 的行」（全手动场景）；
        - 数据行含空行，由下游既有的「全空行跳过」逻辑消化；**前导行整体丢弃、
          不计入 `row_count`**。

    Raises:
        ValueError: 无表头 / 仅空行 → `ValueError("CSV 文件为空")`（既有文案不改，U3）。
    """
    matrix: list[list[str]] = [list(row) for row in rows]
    limit = max(0, min(len(matrix), max_scan))
    best_index = -1
    best_score = 0
    fallback_index = -1

    for index in range(limit):
        cells = matrix[index]
        score = header_score(cells)
        if score > best_score:  # 严格大于 → 同分保留靠前行
            best_score = score
            best_index = index
        if fallback_index < 0 and sum(1 for cell in cells if not is_blank_cell(cell)) >= 2:
            fallback_index = index

    header_index = best_index if best_score > 0 else fallback_index
    if header_index < 0:
        raise ValueError("CSV 文件为空")

    headers = [normalize_header(cell) for cell in matrix[header_index]]
    data_rows = [list(row) for row in matrix[header_index + 1:]]
    return header_index, headers, data_rows


# ── 方言匹配与逐列角色 ─────────────────────────────────────────────


@dataclass(frozen=True)
class ColumnHint:
    """一列的识别建议：原样列名 + 角色 + 样例值。

    `conflict` 记录「本列被同角色更靠前列挤掉」（D3），仅供 `preview_csv` 生成
    `warnings`；**不进响应契约**（`columns` 项只有 index/header/role/sample 四键）。
    """

    index: int
    header: str
    role: str | None
    sample: str
    conflict: bool = False


def match_dialect(
    headers: Sequence[str],
    order: Sequence[str] = DIALECT_ORDER,
) -> Dialect | None:
    """按 `DIALECT_ORDER` 取第一个满足必要列的方言（D5）。

    判定强度与现状 :53-57 一致：`native` 用**严格集合相等**（多列/少列/改名即不判
    native），其余方言用**超集包含**。

    Args:
        headers: 表头单元格（原样或已归一皆可，内部再归一一次，幂等）。
        order: 匹配顺序，默认生产 `DIALECT_ORDER`；仅测试为取证 D5 顺序陷阱而传乱序。
    """
    seen = {normalize_header(cell) for cell in headers}
    for dialect in dialects_in_order(order):
        if dialect.key == "native":
            if seen == dialect.required:
                return dialect
        elif dialect.required <= seen:
            return dialect
    return None


def resolve_columns(
    headers: Sequence[str],
    dialect: Dialect | None,
    data_rows: Sequence[Sequence[str]] = (),
) -> list[ColumnHint]:
    """逐列给出角色建议（D3/D9）。

    - 有方言 → 取 `dialect.roles`；无方言（`custom`）→ 取通用 `COLUMN_ALIASES`。
    - **每角色最多一列**：两列抢同一角色时靠前列得角色，后者 `role=None` 并置
      `conflict=True`（D3）。
    - `header` 为原样列名（**仅两端去空白**，保留大小写与中文）；`role` 查表用的是
      `normalize_header` 后的键，故空列名（支付宝表头末尾多一个逗号）天然 `None`。
    - `sample` 取该列**第一个非空**数据值（`/` 按空占位跳过，D31），无则 `""`。

    Raises:
        ValueError: 表头为空 → `ValueError("CSV 文件为空")`。
    """
    if not headers:
        raise ValueError("CSV 文件为空")

    alias_map: dict[str, str] = dialect.roles if dialect is not None else COLUMN_ALIASES
    taken: set[str] = set()
    hints: list[ColumnHint] = []

    for index, raw_header in enumerate(headers):
        key = normalize_header(raw_header)
        candidate = alias_map.get(key) if key else None
        role: str | None = candidate
        conflict = False
        if candidate is None:
            pass
        elif candidate in taken:
            role = None
            conflict = True
        else:
            taken.add(candidate)
        hints.append(
            ColumnHint(
                index=index,
                header=raw_header.strip(),
                role=role,
                sample=_column_sample(data_rows, index),
                conflict=conflict,
            )
        )
    return hints


def _column_sample(data_rows: Sequence[Sequence[str]], index: int) -> str:
    """该列第一个非空、且非空占位（`/`）的数据值；找不到返回 `""`。"""
    for row in data_rows:
        if index >= len(row):
            continue
        value = row[index].strip()
        if value and not is_blank_cell(value):
            return value
    return ""
