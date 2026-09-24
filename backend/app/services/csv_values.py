"""CSV/Excel 值清洗层（v1.4.3-boot3 M2，设计 §二 / 需求 C）。

三个**纯函数**：``parse_amount`` / ``parse_time`` / ``resolve_type``，外加两个
模块级常量契约 ``TIME_FORMATS``（日期格式白名单）与 ``TYPE_VALUE_*``（收支三集合）。

设计约束（实现期不得发散）：
  * **零 IO、零 DB、零 ORM、零配置**：本模块只 import 标准库 ``re`` / ``unicodedata``
    / ``datetime``；**不 import** ``csv_dialects``（识别层，M3 才单向依赖两者）、
    **不 import** ``import_service``——反向 import 即循环依赖（设计 §2.2）。
  * **只归一、不接线**：``import_service.py`` 的调用点属 M3；本模块的完成判据是
    单测全绿 + 可被 M3 import。
  * **绝不静默产 0 或产脏字符串**：任何无法安全归一的值一律返回 ``None``，由 M3
    跳过并计入 ``skipped_reasons``（D12）。

``"/"`` 的来由（D31，一手实测的**结构事实**，不含任何真实交易内容）：
  微信账单的 ``收/支`` 列在「中性交易」行上填的是**单个** ``/``（该文件的取值分布为
  ``支出`` / ``收入`` / ``/`` 三类，且 ``/`` 的笔数与该文件自述的「中性交易：N 笔」
  逐一对齐）。缺它这些行会被记成 ``type_unresolved`` 而非 ``type_ignored``——结果同样
  是跳过，但**跳过原因失真**。``/`` 同时是分类/标签/备注列的空占位（归一化层按空串
  处理，属 M1/M3）。三集合的匹配是**全等**而非子串：``/`` 只有单字符全等才命中，
  ``充值/提现`` 这类含斜杠的组合值不得被判为 IGNORE，``不计收支`` 也不得因末字
  「支」正好是 expense 集成员而被拆成 expense。

``借/贷``（以及 ``是/否``、``true/false``）属于**值映射**而不是列名别名（D6）：银行
列名不内置进识别层，但用户手选该列后，列里的值在本模块仍可判。

已知边界（D15/D17，登记不修、不扩范围）：歧义日期序（``09/24/2026`` 美式、
``24/09/2026`` 欧式）不支持；CSV 侧不做 Unix 时间戳（时区不可知；SQLite 导入路径的
既有换算不属本模块）。
"""

import re
import unicodedata
from datetime import datetime
from math import isfinite

# ── 常量契约（§2 / §3，逐字抄自任务文件，禁止增删；§4.3 逐位钉死）────────────

TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y年%m月%d日 %H:%M:%S",
    "%Y年%m月%d日 %H:%M",
    "%Y年%m月%d日",
)

TYPE_VALUE_EXPENSE = {"支出", "支", "expense", "out", "debit", "借", "否", "false", "0"}
TYPE_VALUE_INCOME = {"收入", "入", "income", "in", "credit", "贷", "是", "true", "1"}
TYPE_VALUE_IGNORE = {"不计收支", "不计", "中性交易", "neutral", "ignore", "/"}

# 归一输出目标（设计 D14：年在前、补零、16 字符；库内 TEXT 靠字典序 + strftime 读取）
OUTPUT_FORMAT = "%Y-%m-%d %H:%M"

# 粗判前置正则（D15 歧义序的**唯一**防线）：年份必须在最前且紧跟分隔符，
# 故 `09/24/2026`、`24/09/2026`、`1727147274`、裸 Excel 序列号统统不进白名单。
_TIME_PREFIX_RE = re.compile(r"^\s*(19|20)\d{2}\s*[-/年]")

_WHITESPACE_RE = re.compile(r"\s+")
_CURRENCY_CHARS = ("¥", "￥", "$")
_PAREN_RE = re.compile(r"^\((.*)\)$")

__all__ = [
    "TIME_FORMATS",
    "TYPE_VALUE_EXPENSE",
    "TYPE_VALUE_INCOME",
    "TYPE_VALUE_IGNORE",
    "OUTPUT_FORMAT",
    "parse_amount",
    "parse_time",
    "resolve_type",
]

# ── 纯函数 ──────────────────────────────────────────────────────────────────


def parse_amount(raw: str | None) -> float | None:
    """金额清洗（D13）：返回**保留符号**的浮点数，不可解析 → ``None``。

    处理序：``None`` → ``None``；NFKC（全角数字/句点/括号转半角）→ 剥 ``¥ ￥ $``
    与全部空白与千分位逗号 → 剥首尾 ``元`` → 括号形态 ``(12.00)`` 判为负 →
    ``float()``；任何失败返回 ``None``（**不抛异常**）。

    ``0.0`` 是合法值，故返回类型用 ``float | None`` 区分「零金额」与「失败」；
    绝对化（``abs()`` + ``round_money``）在 M3 入库时做，**本函数不得抹掉符号**，
    因为 ``source="sign"`` 的收支判定要看符号（D10）。
    """
    if raw is None:
        return None

    text = unicodedata.normalize("NFKC", raw)
    text = _WHITESPACE_RE.sub("", text)
    for char in _CURRENCY_CHARS:
        text = text.replace(char, "")
    text = text.replace(",", "").strip("元")
    if not text:
        return None

    negative = False
    matched = _PAREN_RE.match(text)
    if matched:
        # 会计式括号 = 负数；取括号内数值后取负
        negative = True
        text = matched.group(1)
        if not text:
            return None

    try:
        value = float(text)
    except ValueError:
        return None
    # `nan` / `inf` / `Infinity` 是 float() 能接受但绝不是合法账单金额的形态，
    # 放行即「静默产脏值」，故一并归 None（验收标准 §2.4）。
    if not isfinite(value):
        return None
    return -value if negative else value


def parse_time(raw: str | None) -> str | None:
    """日期清洗（D14）：归一为唯一目标 ``YYYY-MM-DD HH:MM``，否则 ``None``。

    处理序：粗判前置正则（挡住歧义序与纯数字时间戳，D15）→ ``~`` 时间区间取前段
    → 按 ``TIME_FORMATS`` **顺序**逐个 ``strptime`` → 命中后 ``strftime`` 输出。
    无时间成分的形态由 ``strftime`` 自然补 ``00:00``；``strptime`` 容忍非补零输入
    （``2026/9/24``、``8:30``），输出侧恒为 16 字符、补零、24 小时制。

    **禁止按 ``.`` 截断**：微秒位数不固定（模板 6 位、全量导出 3 位），必须走 ``%f``
    （其本身支持 1~6 位）。xlsx 通道不改本函数（D24）——容器层已把日期单元格换算成
    ``"%Y-%m-%d %H:%M:%S"`` 文本，白名单成员与顺序一字不改。
    """
    if raw is None:
        return None
    if not _TIME_PREFIX_RE.match(raw):
        return None

    text = raw.strip()
    # 时间区间 `2026-09-24 11:07:54~2026-09-24 11:08:00` → 取前段
    if "~" in text:
        text = text.split("~", 1)[0].strip()
    if not text:
        return None

    for fmt in TIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.strftime(OUTPUT_FORMAT)
    return None


def resolve_type(
    raw: str | None, amount: float | None, source: str
) -> tuple[str | None, str | None]:
    """收支三态判定（D10/D11）：返回 ``(type, skip_reason)``。

    * ``type`` ∈ ``{"income", "expense", None}``
    * ``skip_reason`` ∈ ``{None, "type_ignored", "type_unresolved", "invalid_amount"}``
      （与 M3 的 ``skipped_reasons`` 键同名，D12）

    ``source == "column"``：按三集合**全等**判（判前 ``strip().lower()``）；值为空或
    不可判 → ``(None, "type_unresolved")``，**绝不回落到 sign**（D10：回落会让整表
    静默变支/收）。``source == "sign"``：金额为 ``None`` → ``(None,
    "invalid_amount")``；负 → expense、正 → income、**0 归支出**。
    ``all_expense`` / ``all_income``：常量返回。其它 ``source`` → ``(None,
    "type_unresolved")``（不猜）。
    """
    if source == "column":
        return _resolve_from_column(raw)
    if source == "sign":
        if amount is None:
            return None, "invalid_amount"
        if amount > 0:
            return "income", None
        return "expense", None  # 负数与 0 同为支出（D10「0 归支出」）
    if source == "all_expense":
        return "expense", None
    if source == "all_income":
        return "income", None
    return None, "type_unresolved"


def _resolve_from_column(raw: str | None) -> tuple[str | None, str | None]:
    """收支列值判定：忽略集优先，其余**全等**匹配（非子串）。"""
    if raw is None:
        return None, "type_unresolved"
    key = raw.strip().lower()
    if not key:
        return None, "type_unresolved"
    if key in TYPE_VALUE_IGNORE:
        return None, "type_ignored"
    if key in TYPE_VALUE_EXPENSE:
        return "expense", None
    if key in TYPE_VALUE_INCOME:
        return "income", None
    return None, "type_unresolved"
