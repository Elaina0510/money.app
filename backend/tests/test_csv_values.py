"""Tests for M2（v1.4.3-boot3）：后端清洗层纯函数 `app/services/csv_values.py`。

用例编号 §4.1–§4.8 与任务文件 `doc/tasksv1.4.3boot3/m2-csv-value-normalization.md`
的 checklist 一一对应；本文件**不接线** `import_service.py`（接线属 M3）。
"""

import ast
import re
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.record import RecordCreate
from app.services import csv_values
from app.services.csv_values import (
    TIME_FORMATS,
    TYPE_VALUE_EXPENSE,
    TYPE_VALUE_IGNORE,
    TYPE_VALUE_INCOME,
    parse_amount,
    parse_time,
    resolve_type,
)

# 斜杠日期形态用变量拼，避免与 ISO 短横形态在源码里视觉混淆
S = "/"

# ── §4.1 parse_amount：符号 / 千分位 / 括号负数 / 占位符 ──────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("¥1,234.50", 1234.5),  # 货币符号 + 千分位
        ("(12.00)", -12.0),  # 会计式括号 → 负
        ("１２．５", 12.5),  # 全角数字与全角句点（NFKC）
        ("12.00元", 12.0),  # 结尾单位
        ("-19.9", -19.9),  # 显式负号（绝对化在 M3，D13）
        ("0", 0.0),  # 0 是合法值，不得与失败混淆
        ("￥1,000", 1000.0),  # 全角符号 + 千分位
        ("  -50  ", -50.0),  # 两端空白
        ("1,234", 1234.0),
        ("$3.5", 3.5),
    ],
)
def test_4_1_parse_amount_normalizes_signed_value(raw: str, expected: float) -> None:
    """§4.1 可归一形态：返回值**保留符号**（不 abs、不 round）。"""
    result = parse_amount(raw)
    assert result is not None
    assert result == pytest.approx(expected)
    assert (result < 0) == (expected < 0)


@pytest.mark.parametrize(
    "raw",
    ["/", "-", "--", "", "   ", None, "abc", "元", "1.2.3", "12-34", "()"],
)
def test_4_1_parse_amount_returns_none_for_unsafe(raw: str | None) -> None:
    """§4.1 占位符与脏值 → `None`（不抛异常、不静默产 0）。"""
    assert parse_amount(raw) is None


def test_4_1_parse_amount_zero_is_not_failure() -> None:
    """§4.1 `0` → `0.0`，与失败的 `None` 可区分。"""
    zero = parse_amount("0")
    assert zero == 0.0
    assert zero is not None
    assert parse_amount("/") is None


def test_4_1_parse_amount_rejects_non_finite() -> None:
    """§4.1 补强：`float()` 能吞下但绝不是合法账单金额的 `inf`/`nan` → `None`。"""
    for raw in ("inf", "-inf", "nan", "Infinity", "1e999"):
        assert parse_amount(raw) is None, raw


# ── §4.2 三集合互斥 + 全等匹配（`不计收支` 不被拆走） ─────────────────────────


def test_4_2_three_sets_are_pairwise_disjoint() -> None:
    """§4.2 expense / income / ignore 三集合两两互斥。"""
    assert TYPE_VALUE_EXPENSE & TYPE_VALUE_INCOME == set()
    assert TYPE_VALUE_EXPENSE & TYPE_VALUE_IGNORE == set()
    assert TYPE_VALUE_INCOME & TYPE_VALUE_IGNORE == set()


def test_4_2_match_is_exact_not_substring() -> None:
    """§4.2 `不计收支` 命中 IGNORE，**不得**因含「支」子串被拆成 expense。

    子串实现必然翻车的证据：`"支" in "不计收支"` 为真，而 `"支"` 正是 expense 集成员。
    """
    assert "支" in "不计收支"
    assert resolve_type("不计收支", -1.0, "column") == (None, "type_ignored")
    assert resolve_type("不计", -1.0, "column") == (None, "type_ignored")
    assert resolve_type("中性交易", -1.0, "column") == (None, "type_ignored")
    # 组合值同样不得被拆走：`/` 只有单字符全等才命中
    assert resolve_type("充值" + S + "提现", -1.0, "column") == (
        None,
        "type_unresolved",
    )
    assert resolve_type("支出" + S, -1.0, "column") == (None, "type_unresolved")
    # 含集成员子串的长值一律不可判（全等匹配的另一侧证据）
    assert resolve_type("本月支出", -1.0, "column") == (None, "type_unresolved")
    assert resolve_type("income_tax", 1.0, "column") == (None, "type_unresolved")


def test_4_2_slash_placeholder_is_ignored() -> None:
    """§4.2 / D31：单个 `/` 全等才命中 IGNORE（中性交易占位）。"""
    assert resolve_type("/", -1.0, "column") == (None, "type_ignored")
    assert resolve_type(" " + S + " ", -1.0, "column") == (None, "type_ignored")


# ── §4.3 TIME_FORMATS 与任务文件 §2 常量逐位一致 ─────────────────────────────

# 任务文件 §2 的白名单原文（顺序即匹配优先级，禁止增删）
SPEC_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%Y" + S + "%m" + S + "%d %H:%M:%S",
    "%Y" + S + "%m" + S + "%d %H:%M",
    "%Y" + S + "%m" + S + "%d",
    "%Y年%m月%d日 %H:%M:%S",
    "%Y年%m月%d日 %H:%M",
    "%Y年%m月%d日",
)

# 任务文件 §3 的三集合原文（逐值抄录）
SPEC_TYPE_VALUE_EXPENSE = {
    "支出", "支", "expense", "out", "debit", "借", "否", "false", "0",
}
SPEC_TYPE_VALUE_INCOME = {
    "收入", "入", "income", "in", "credit", "贷", "是", "true", "1",
}
SPEC_TYPE_VALUE_IGNORE = {"不计收支", "不计", "中性交易", "neutral", "ignore", "/"}


def test_4_3_time_formats_are_position_by_position_identical() -> None:
    """§4.3 白名单成员与顺序逐位钉死（防实现期漂移）。"""
    assert len(TIME_FORMATS) == len(SPEC_TIME_FORMATS) == 13
    for index, (actual, spec) in enumerate(zip(TIME_FORMATS, SPEC_TIME_FORMATS)):
        assert actual == spec, f"TIME_FORMATS[{index}] 漂移"
    assert TIME_FORMATS == SPEC_TIME_FORMATS


def test_4_2_three_sets_are_verbatim_copy_of_spec() -> None:
    """§3 / §4.2 三集合逐值钉死（含 D31 一手实测补入的 `/`）。"""
    assert TYPE_VALUE_EXPENSE == SPEC_TYPE_VALUE_EXPENSE
    assert TYPE_VALUE_INCOME == SPEC_TYPE_VALUE_INCOME
    assert TYPE_VALUE_IGNORE == SPEC_TYPE_VALUE_IGNORE
    assert (len(TYPE_VALUE_EXPENSE), len(TYPE_VALUE_INCOME), len(TYPE_VALUE_IGNORE)) == (
        9,
        9,
        6,
    )


# ── §4.4 parse_time 逐形态 ───────────────────────────────────────────────────

TIME_CASES: list[tuple[str, str]] = [
    ("2026-09-24 11:07:54.617083", "2026-09-24 11:07"),  # 模板 6 位微秒
    ("2026-06-04 10:58:23.000", "2026-06-04 10:58"),  # 全量导出 3 位微秒
    ("2026-09-24T11:07:54", "2026-09-24 11:07"),  # ISO T 分隔
    ("2026-09-24T11:07:54.617083", "2026-09-24 11:07"),  # T + 微秒
    ("2026" + S + "9" + S + "24", "2026-09-24 00:00"),  # 斜杠 + 非补零月日
    ("2026" + S + "09" + S + "24 11:07:54", "2026-09-24 11:07"),  # 斜杠 + 时间
    ("2026" + S + "09" + S + "24 11:07", "2026-09-24 11:07"),  # 斜杠 + 分
    ("2026-9-24", "2026-09-24 00:00"),  # 短横 + 非补零（任务 §4.4 原文）
    ("2026-09-24", "2026-09-24 00:00"),  # 已是目标日期形态（无时间成分）
    ("2026年9月24日 8:30", "2026-09-24 08:30"),  # 中文日期 + 非补零时
    ("2026年9月24日 8:30:00", "2026-09-24 08:30"),  # 中文日期 + 秒
    ("2026年9月24日", "2026-09-24 00:00"),  # 中文日期无时间
    ("2026-09-24 11:07", "2026-09-24 11:07"),  # 分钟精度原样收敛
    ("2026-09-24 11:07:54~2026-09-24 11:08:00", "2026-09-24 11:07"),  # 区间取前段
    ("2026-09-24 11:40:58", "2026-09-24 11:40"),  # M6 容器层换算后的文本（D24）
]


@pytest.mark.parametrize(("raw", "expected"), TIME_CASES)
def test_4_4_parse_time_normalizes_each_form(raw: str, expected: str) -> None:
    """§4.4 白名单内形态全部收敛到 `YYYY-MM-DD HH:MM`。"""
    assert parse_time(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), TIME_CASES)
def test_4_4_output_is_padded_16_chars(raw: str, expected: str) -> None:
    """§2.2 / §4.4 输出恒 16 字符、补零、24 小时制、无残留分隔符。"""
    result = parse_time(raw)
    assert result is not None
    assert len(result) == 16
    assert result == expected
    for junk in (".", S, "年", "月", "日", "T", "~"):
        assert junk not in result


def test_4_4_no_truncation_on_dot() -> None:
    """§1.2 **禁止按 `.` 截断**：微秒 1~6 位都由 `%f` 吃掉。"""
    for digits in range(1, 7):
        raw = "2026-09-24 11:07:54." + "6" * digits
        assert parse_time(raw) == "2026-09-24 11:07", raw
    assert parse_time("2026-06-04 10:58:23.000") == "2026-06-04 10:58"


# ── §4.5 不猜形态 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        "09" + S + "24" + S + "2026",  # 美式月/日 → 歧义序（D15）
        "24" + S + "09" + S + "2026",  # 欧式日/月 → 歧义序（D15）
        "1727147274",  # 纯数字 Unix 时间戳（时区不可知，D15/D17）
        "46289.48678240741",  # 裸 Excel 序列号（另存 CSV 后的形态，D15）
        "2026-13-01",  # 非法月份
        "2026-09-31",  # 非法日
        "garbage",
        "",
        "   ",
        None,
        "2026.09.24",  # 点分隔不在白名单
        "24 Sep 2026",  # 年不在最前
        "2026-09-24T11:07:54+08:00",  # 带时区偏移不猜
        "9月24日",  # 无年份
        "~2026-09-24",  # 区间前段为空
    ],
)
def test_4_5_parse_time_never_guesses(raw: str | None) -> None:
    """§4.5 粗判正则与白名单之外的形态一律 `None`，交 M3 计 `invalid_date`。"""
    assert parse_time(raw) is None


def test_4_5_coarse_prefix_regex_is_the_ambiguity_defence() -> None:
    """§1.2 粗判前置：年份不在最前并紧跟分隔符即不进白名单（歧义序唯一防线）。"""
    prefix = csv_values._TIME_PREFIX_RE
    assert prefix.match("2026-09-24")
    assert prefix.match("2026" + S + "9" + S + "24")
    assert prefix.match("  2026-09-24")
    assert prefix.match("2026年9月24日")
    assert prefix.match("1999-01-01")
    for not_year_first in (
        "09" + S + "24" + S + "2026",
        "24" + S + "09" + S + "2026",
        "1727147274",
        "46289.48",
        "9月24日",
        "2026Sep24",
        "20260924",
        "2026.09.24",
    ):
        assert not prefix.match(not_year_first), not_year_first


# ── §4.6 与记录 API 契约交叉断言（import 正则，不重新抄写） ────────────────────


def _schema_consume_time_pattern() -> str:
    """取 `app/schemas/record.py` 里 `consume_time` 的 pattern 原文（不重抄）。"""
    field = RecordCreate.model_fields["consume_time"]
    for meta in field.metadata:
        constraint: Any = getattr(meta, "pattern", None)
        if constraint is not None:
            if isinstance(constraint, re.Pattern):
                return str(constraint.pattern)
            return str(constraint)
    raise AssertionError("未取到 consume_time 的 pattern：交叉断言已失效")


def test_4_6_pattern_really_comes_from_record_schema() -> None:
    """§4.6 前置：正则确实取自 `schemas/record.py` 且该约束真实生效。"""
    pattern = _schema_consume_time_pattern()
    assert pattern
    assert re.compile(pattern).pattern == pattern
    # 脏形态必须被 schema 拒，否则本交叉断言是空断言
    with pytest.raises(ValidationError):
        RecordCreate(
            amount=1.0,
            type="expense",
            category_id=1,
            consume_time="2026" + S + "9" + S + "24",
        )


@pytest.mark.parametrize(("raw", "expected"), TIME_CASES)
def test_4_6_parse_time_output_matches_record_api(raw: str, expected: str) -> None:
    """§4.6 清洗产物必须被记录 API 的 `consume_time` 正则 fullmatch。"""
    pattern = _schema_consume_time_pattern()
    result = parse_time(raw)
    assert result == expected
    assert re.fullmatch(pattern, result), f"{result!r} 不被 {pattern!r} 接受"


def test_4_6_record_schema_accepts_cleaned_time() -> None:
    """§4.6 交叉断言第二半：Pydantic 校验同样放行清洗产物。"""
    cleaned = parse_time("2026年9月24日 8:30")
    assert cleaned is not None
    record = RecordCreate(
        amount=1.0, type="expense", category_id=1, consume_time=cleaned
    )
    assert record.consume_time == cleaned


# ── §4.7 resolve_type 四态 × 三集 × 边界 ─────────────────────────────────────


@pytest.mark.parametrize("value", sorted(SPEC_TYPE_VALUE_EXPENSE))
def test_4_7_column_source_expense_set(value: str) -> None:
    """§4.7 列值命中 expense 集 → expense（含 `借`/`否`/`false`/`0`）。"""
    assert resolve_type(value, 12.0, "column") == ("expense", None)


@pytest.mark.parametrize("value", sorted(SPEC_TYPE_VALUE_INCOME))
def test_4_7_column_source_income_set(value: str) -> None:
    """§4.7 列值命中 income 集 → income（含 `贷`/`是`/`true`/`1`）。"""
    assert resolve_type(value, -12.0, "column") == ("income", None)


@pytest.mark.parametrize("value", sorted(SPEC_TYPE_VALUE_IGNORE))
def test_4_7_column_source_ignore_set(value: str) -> None:
    """§4.7 列值命中 ignore 集 → 跳过并计 `type_ignored`（D11/D31）。"""
    assert resolve_type(value, 12.0, "column") == (None, "type_ignored")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("TRUE", "income"),
        ("False", "expense"),
        ("  支出  ", "expense"),
        ("Income", "income"),
        ("CREDIT", "income"),
        ("Debit", "expense"),
        ("不计收支 ", None),
    ],
)
def test_4_7_column_source_normalizes_cell(value: str, expected: str | None) -> None:
    """§3.1 判前 `strip().lower()`：大小写与两端空白不影响判定。"""
    kind, reason = resolve_type(value, 1.0, "column")
    assert kind == expected
    assert (reason is None) == (expected is not None)
    if expected is None:
        assert reason == "type_ignored"  # 不失真成 type_unresolved


@pytest.mark.parametrize("raw", ["", "   ", None, "转账", "未知", "收", "0.5", "中性"])
def test_4_7_column_source_unjudgable_never_falls_back_to_sign(
    raw: str | None,
) -> None:
    """§1.3 / D10：`column` 下空值与不可判 → `type_unresolved`，**绝不回落 sign**。

    回落会让整表静默变支/收；故金额为负、为正、甚至清洗失败都不改变结论。
    """
    assert resolve_type(raw, -99.0, "column") == (None, "type_unresolved")
    assert resolve_type(raw, 99.0, "column") == (None, "type_unresolved")
    assert resolve_type(raw, None, "column") == (None, "type_unresolved")


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (-19.9, "expense"),
        (0.0, "expense"),
        (-0.0, "expense"),
        (0.01, "income"),
        (250.0, "income"),
    ],
)
def test_4_7_sign_source(amount: float, expected: str) -> None:
    """§4.7 / D10：符号法负→支出、正→收入、**0 归支出**。"""
    assert resolve_type(None, amount, "sign") == (expected, None)


@pytest.mark.parametrize("raw", ["支出", "", None, "/"])
def test_4_7_sign_source_ignores_column_value(raw: str | None) -> None:
    """§4.7 符号法不看列值（列值只在 `column` 源下参与判定）。"""
    assert resolve_type(raw, -1.0, "sign") == ("expense", None)
    assert resolve_type(raw, 1.0, "sign") == ("income", None)


def test_4_7_sign_source_without_amount_is_invalid_amount() -> None:
    """§4.7 / D12：符号法遇到金额清洗失败 → `invalid_amount`（不猜方向）。"""
    assert resolve_type("支出", None, "sign") == (None, "invalid_amount")


@pytest.mark.parametrize("raw", [None, "", "/", "收入", "不计收支"])
def test_4_7_all_expense_and_all_income_are_constants(raw: str | None) -> None:
    """§4.7 常量源：列值与金额都不参与判定。"""
    for amount in (None, 0.0, -1.0, 1.0):
        assert resolve_type(raw, amount, "all_expense") == ("expense", None)
        assert resolve_type(raw, amount, "all_income") == ("income", None)


@pytest.mark.parametrize(
    "source", ["", "COLUMN", "Sign", "unknown", "auto", "fallback", "column "]
)
def test_4_7_unknown_source_is_not_guessed(source: str) -> None:
    """§1.3：四态之外的 `source` → `type_unresolved`（不猜）。"""
    assert resolve_type("支出", -1.0, source) == (None, "type_unresolved")
    assert resolve_type(None, None, source) == (None, "type_unresolved")


def test_4_7_return_vocabulary_is_closed() -> None:
    """§4.7 返回值封闭集：`type` 与 `skip_reason` 不冒出第三种字面量。"""
    allowed_types = {"income", "expense", None}
    allowed_reasons = {None, "type_ignored", "type_unresolved", "invalid_amount"}
    cells = ["支出", "收入", "/", "", "不计收支", "abc", None, "TRUE", "0"]
    for source in ("column", "sign", "all_expense", "all_income", "junk"):
        for cell in cells:
            for amount in (None, 0.0, 3.3, -3.3):
                kind, reason = resolve_type(cell, amount, source)
                assert kind in allowed_types, (source, cell, amount, kind)
                assert reason in allowed_reasons, (source, cell, amount, reason)
                assert (kind is None) == (reason is not None)


def test_4_7_skip_reasons_are_d12_key_subset() -> None:
    """§1.3 / D12：本模块产出的 reason 字面量是 M3 `skipped_reasons` 键的子集。"""
    d12_keys = {
        "invalid_amount",
        "invalid_date",
        "type_ignored",
        "type_unresolved",
        "category_unresolved",
    }
    produced: set[str] = set()
    for source in ("column", "sign", "all_expense", "all_income", "junk"):
        for cell in ("支出", "", None, "/"):
            for amount in (None, 0.0, -1.0, 1.0):
                reason = resolve_type(cell, amount, source)[1]
                if reason is not None:
                    produced.add(reason)
    assert produced and produced <= d12_keys


# ── §4.8 纯函数无副作用 / 无时间与外部状态依赖 ────────────────────────────────

_AMOUNT_INPUTS = ["¥1,234.50", "(12.00)", "１２．５", "12.00元", "-19.9", "0", "/", None]
_TIME_INPUTS = [raw for raw, _ in TIME_CASES] + [
    "09" + S + "24" + S + "2026",
    "1727147274",
    None,
]
_TYPE_INPUTS: list[tuple[str | None, float | None, str]] = [
    (cell, amount, source)
    for source in ("column", "sign", "all_expense", "all_income", "junk")
    for cell in ("支出", "收入", "/", "", None)
    for amount in (None, 0.0, 5.0, -5.0)
]


def _module_source() -> str:
    assert csv_values.__file__ is not None
    with open(csv_values.__file__, encoding="utf-8") as handle:
        return handle.read()


def test_4_8_repeated_calls_are_identical() -> None:
    """§4.8 同一入参重复调用结果逐位一致（无内部缓存 / 累加状态）。"""
    amount_rounds = [[parse_amount(raw) for raw in _AMOUNT_INPUTS] for _ in range(5)]
    assert all(round_ == amount_rounds[0] for round_ in amount_rounds)
    time_rounds = [[parse_time(raw) for raw in _TIME_INPUTS] for _ in range(5)]
    assert all(round_ == time_rounds[0] for round_ in time_rounds)
    type_rounds = [[resolve_type(*args) for args in _TYPE_INPUTS] for _ in range(5)]
    assert all(round_ == type_rounds[0] for round_ in type_rounds)


def test_4_8_call_order_does_not_matter() -> None:
    """§4.8 乱序 / 交错调用与单独调用结果一致（无跨入参残留）。"""
    single = [parse_time(raw) for raw in _TIME_INPUTS]
    assert list(reversed([parse_time(raw) for raw in reversed(_TIME_INPUTS)])) == single

    interleaved: dict[int, str | None] = {}
    for index, raw in enumerate(reversed(_TIME_INPUTS)):
        parse_amount("¥1,234.50")
        resolve_type("支出", -1.0, "column")
        interleaved[len(_TIME_INPUTS) - 1 - index] = parse_time(raw)
    assert [interleaved[i] for i in range(len(_TIME_INPUTS))] == single


def test_4_8_module_has_no_clock_or_external_state_dependency() -> None:
    """§4.8 / §1.4 源码级证据：只 import 标准库，不取当前时间、不读环境/locale。"""
    source = _module_source()
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # 零新增依赖 + 零 ORM/config + 不反向 import 识别层（M3 才单向依赖两者）
    assert imported <= {"re", "unicodedata", "datetime", "math", "__future__"}, imported

    for banned in (".now(", ".today(", ".utcnow(", ".fromtimestamp(", "getenv"):
        assert banned not in source, f"纯函数不应依赖当前时间/环境：{banned!r}"


def test_4_8_constants_are_not_mutated_by_calling() -> None:
    """§4.8 调用不改动模块级常量（三集合与白名单原地不变）。"""
    snapshot = (
        set(TYPE_VALUE_EXPENSE),
        set(TYPE_VALUE_INCOME),
        set(TYPE_VALUE_IGNORE),
        tuple(TIME_FORMATS),
    )
    for raw in _AMOUNT_INPUTS:
        parse_amount(raw)
    for raw in _TIME_INPUTS:
        parse_time(raw)
    for args in _TYPE_INPUTS:
        resolve_type(*args)
    assert snapshot == (
        set(TYPE_VALUE_EXPENSE),
        set(TYPE_VALUE_INCOME),
        set(TYPE_VALUE_IGNORE),
        tuple(TIME_FORMATS),
    )
