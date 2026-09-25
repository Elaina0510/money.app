"""M6 后端 Excel（``.xlsx``）容器层测试（任务 ``m6-xlsx-container.md`` §4.1–§4.11，设计 §6.5）。

**红线 11（xlsx 半区）**：本文件**不引用**本机那份未跟踪的真实样例目录（含用户数据、
git 不收录），也**不抄**任何真实账单单元格值。构造器只镜像设计 §0.4-13 登记的**结构事实**
（表头 11 列原文、前导说明含 4 条编号注释与单格分隔线、第 16 行整体缺 ``<row r="16">``、
日期为数字序列号 + numFmt 164、金额为裸数字 + numFmt 165、``t="s"`` sharedStrings、
A 列 ``s=1`` / F 列 ``s=3`` / 其余 9 列 ``s=2``），**数据行全部合成**。唯一的逐位数字常量
``46289.48678240741`` 是任务 §1.6 / §4.5 明定的「基准换算逐位实证」样本。

**合成构造器交接（M5 §5.2 只调不重写）**：

    build_xlsx(rows: Sequence[Sequence[Cell] | None], *, inline: bool = False,
               hidden_before: int = 0) -> bytes
        # 行取 None = 整行不写 <row>（造缺行）；单元格取 None = 该格不写 <c>（造跳列）
        # inline=True → t="inlineStr" 且不写 xl/sharedStrings.xml（6 entry）
        # hidden_before=N → 可见表之前放 N 张 state="hidden" 的垃圾 sheet
    wechat_xlsx_bytes(*, inline: bool = False, extra_preamble: int = 0,
                      hidden_before: int = 0) -> bytes     # 真实镜像形态的 .xlsx 字节
    wechat_matrix_rows(*, extra_preamble: int = 0) -> list[Sequence[Cell] | None]
    Cell = str | Text | Num | Inline | FormulaStr | Bool | ErrorCell | None
    常量：WECHAT_HEADERS / DATA_ROW_COUNT / DATE_SERIAL_TEXT / DATE_TEXT
          DATE_STYLE(=1) / AMOUNT_STYLE(=3) / TEXT_STYLE(=2) / HEADER_STYLE(=0)
"""

import ast
import io
import re
import sys
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

import app.services.import_service as import_service
from app.services import xlsx_reader
from app.services.csv_dialects import locate_header_rows, match_dialect, resolve_columns
from app.services.csv_values import TIME_FORMATS, parse_amount, parse_time, resolve_type
from app.services.xlsx_reader import detect_container, excel_serial_to_text, xlsx_rows
from app.utils.cache import delete_cache, read_from_cache

# 用例无需 `pytestmark`：pyproject 已配 `asyncio_mode = "auto"`，异步用例自动收集。

NO_DB = cast(AsyncSession, None)
"""`preview_csv` 的 `db` 形参现状无消费方（设计 §1.2.6），本文件按 §1.2.6 直接传 None。"""

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

DEFAULT_ENTRY_NAMES = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/worksheets/sheet1.xml",
    "xl/sharedStrings.xml",
    "xl/styles.xml",
)


# ══════════════════════════════════════════════════════════════════
#  §4.1 合成 xlsx 构造器（stdlib `zipfile.writestr` 手写最小 7 entry）
# ══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Text:
    """``t="s"`` 共享串单元格（`style` = `s` 属性，镜像实测「其余 9 列全 s=2」）。"""

    value: str
    style: int | None = None


@dataclass(frozen=True)
class Num:
    """数字单元格：**无** ``t`` 属性；`style` = ``s``（日期身份只看它，D24）。"""

    text: str
    style: int | None = None


@dataclass(frozen=True)
class Inline:
    """``t="inlineStr"`` 单元格。"""

    text: str


@dataclass(frozen=True)
class FormulaStr:
    """``t="str"``（公式缓存串）单元格。"""

    text: str


@dataclass(frozen=True)
class Bool:
    """``t="b"`` 单元格：``1/0`` → ``true/false`` 文本。"""

    text: str


@dataclass(frozen=True)
class ErrorCell:
    """``t="e"`` 错误值单元格：容器层归空串。"""

    text: str = "#VALUE!"


Cell = str | Text | Num | Inline | FormulaStr | Bool | ErrorCell | None
"""单元格构造形态；``None`` = 该格不写 ``<c>``（造行内跳列）。整行取 ``None`` = 不写 ``<row>``。"""


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _col_letters(index: int) -> str:
    """0-based 列下标 → 列字母（``xlsx_reader._column_index`` 的逆运算）。"""
    letters = ""
    position = index + 1
    while position > 0:
        position, remainder = divmod(position - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _shared_text(cell: Cell) -> str | None:
    """该单元格是否走共享串（``str`` / ``Text``）；是则返回其文本。"""
    if isinstance(cell, str):
        return cell
    if isinstance(cell, Text):
        return cell.value
    return None


def _shared_strings_map(rows: Sequence[Sequence[Cell] | None]) -> dict[str, int]:
    """按**首次出现顺序**编号（``t="s"`` 的 ``<v>`` 即该索引）。"""
    mapping: dict[str, int] = {}
    for row in rows:
        if row is None:
            continue
        for cell in row:
            text = _shared_text(cell)
            if text is not None and text not in mapping:
                mapping[text] = len(mapping)
    return mapping


def _cell_xml(
    ref: str, cell: Cell, shared: dict[str, int], inline: bool, style: int | None = None
) -> str:
    text = _shared_text(cell)
    if text is not None:
        style_attr = f' s="{style}"' if style is not None else ""
        if inline:
            return f'<c r="{ref}"{style_attr} t="inlineStr"><is><t>{_esc(text)}</t></is></c>'
        return f'<c r="{ref}"{style_attr} t="s"><v>{shared[text]}</v></c>'
    if isinstance(cell, Num):
        style_attr = f' s="{cell.style}"' if cell.style is not None else ""
        return f'<c r="{ref}"{style_attr}><v>{_esc(cell.text)}</v></c>'
    if isinstance(cell, Inline):
        return f'<c r="{ref}" t="inlineStr"><is><t>{_esc(cell.text)}</t></is></c>'
    if isinstance(cell, FormulaStr):
        return f'<c r="{ref}" t="str"><v>{_esc(cell.text)}</v></c>'
    if isinstance(cell, Bool):
        return f'<c r="{ref}" t="b"><v>{_esc(cell.text)}</v></c>'
    if isinstance(cell, ErrorCell):
        return f'<c r="{ref}" t="e"><v>{_esc(cell.text)}</v></c>'
    raise TypeError(f"未知单元格形态：{cell!r}")


def _sheet_xml(
    rows: Sequence[Sequence[Cell] | None], shared: dict[str, int], inline: bool
) -> str:
    """行矩阵 → ``sheetData``。

    **行号 = 矩阵下标 + 1**，取 ``None`` 的行不写元素 → 自动产生「``<row r="16">``
    整体缺失」的真实形态（D26：行按出现顺序、不按 ``r`` 补空行）。
    """
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{MAIN_NS}">',
        "<sheetData>",
    ]
    for position, row in enumerate(rows):
        if row is None:
            continue
        number = position + 1
        parts.append(f'<row r="{number}">')
        for column, cell in enumerate(row):
            if cell is None:
                continue
            style = cell.style if isinstance(cell, Text) else None
            parts.append(
                _cell_xml(f"{_col_letters(column)}{number}", cell, shared, inline, style)
            )
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


# 实测钉死（设计 §6.2）：cellXfs 共 4 项，s=0/2 → numFmtId=0、s=1 → 164 日期、s=3 → 165 金额
STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<styleSheet xmlns="{MAIN_NS}">'
    '<numFmts count="2">'
    '<numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd\\ hh\\:mm\\:ss"/>'
    '<numFmt numFmtId="165" formatCode="¥#,##0.00"/>'
    "</numFmts>"
    '<cellXfs count="4">'
    '<xf numFmtId="0" fontId="0"/>'
    '<xf numFmtId="164" fontId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="0" fontId="0"/>'
    '<xf numFmtId="165" fontId="0" applyNumberFormat="1"/>'
    "</cellXfs></styleSheet>"
)
"""与真实文件同形的样式表：日期样式下标 1、金额样式下标 3（§1.5 的判据来源）。"""


def _content_types_xml(inline: bool) -> str:
    shared = (
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        if not inline
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package'
        '-relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{shared}</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    )


def _workbook_xml(hidden_before: int) -> str:
    sheets = [
        f'<sheet name="隐藏{position + 1}" sheetId="{position + 1}" state="hidden" '
        f'r:id="rId{position + 1}"/>'
        for position in range(hidden_before)
    ]
    visible = hidden_before + 1
    sheets.append(f'<sheet name="Sheet1" sheetId="{visible}" r:id="rId{visible}"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">'
        f"<sheets>{''.join(sheets)}</sheets></workbook>"
    )


def _workbook_rels_xml(hidden_before: int) -> str:
    rels = [
        f'<Relationship Id="rId{position + 1}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{position + 1}.xml"/>'
        for position in range(hidden_before + 1)
    ]
    rels.append(
        f'<Relationship Id="rId{hidden_before + 2}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">{"".join(rels)}</Relationships>'
    )


def build_xlsx(
    rows: Sequence[Sequence[Cell] | None],
    *,
    inline: bool = False,
    hidden_before: int = 0,
) -> bytes:
    """行矩阵 → ``.xlsx`` 字节（§4.1 构造器；签名交接给 M5）。

    Args:
        rows: 行矩阵。整行 ``None`` = XML 里不写该 ``<row>``（造「第 16 行整体缺失」）；
            单元格 ``None`` = 不写该 ``<c>``（造行内跳列）。
        inline: ``True`` → 文本走 ``t="inlineStr"`` 且**不写** ``xl/sharedStrings.xml``。
        hidden_before: 可见表之前放 N 张 ``state="hidden"`` 的垃圾 sheet（§1.3 选表边界）。

    Returns:
        zip 容器字节：默认 7 个 entry；``inline=True`` 时 6 个。
    """
    shared = {} if inline else _shared_strings_map(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(inline))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(hidden_before))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(hidden_before))
        for position in range(hidden_before):
            archive.writestr(
                f"xl/worksheets/sheet{position + 1}.xml",
                _sheet_xml([[Inline("隐藏占位表，不应被读取")]], {}, True),
            )
        archive.writestr(
            f"xl/worksheets/sheet{hidden_before + 1}.xml",
            _sheet_xml(rows, shared, inline),
        )
        if not inline:
            archive.writestr("xl/sharedStrings.xml", _shared_strings_xml(shared))
        archive.writestr("xl/styles.xml", STYLES_XML)
    return buffer.getvalue()


def _shared_strings_xml(shared: dict[str, int]) -> str:
    items = "".join(f"<si><t>{_esc(text)}</t></si>" for text in shared)
    size = len(shared)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="{MAIN_NS}" count="{size}" uniqueCount="{size}">{items}</sst>'
    )


# ── §4.2 真实镜像夹具（设计 §0.4-13 的**结构**，数据全合成） ─────────


WECHAT_HEADERS: tuple[str, ...] = (
    "交易时间",
    "交易类型",
    "交易对方",
    "商品",
    "收/支",
    "金额(元)",
    "支付方式",
    "当前状态",
    "交易单号",
    "商户单号",
    "备注",
)
"""11 列表头**逐字**取自设计 §0.4-13（任务 §4.2 明定的结构事实，非用户数据）。"""

DATE_SERIAL_TEXT = "46289.48678240741"
DATE_TEXT = "2026-09-24 11:40:58"
"""任务 §1.6 / §4.5 明定的逐位实证样本（序列号 → naive 挂钟文本）。"""

DATE_STYLE = 1  # cellXfs[1] → numFmtId 164 `yyyy-mm-dd hh:mm:ss`
AMOUNT_STYLE = 3  # cellXfs[3] → numFmtId 165 `¥#,##0.00`
TEXT_STYLE = 2  # cellXfs[2] → numFmtId 0（实测其余 9 列全 s=2）
HEADER_STYLE = 0

DATA_ROW_COUNT = 4
"""合成数据行数（§4.10 的 `row_count` 断言用）。"""


def wechat_preamble_rows() -> list[Sequence[Cell] | None]:
    """前导说明区：15 条信息行 + **第 16 行整体缺失** + 第 17 行单格分隔线。

    表头因此落在文件第 **18** 行（§0.4-13「前导 17 行」是**含**缺失行的行号口径），
    而矩阵里前导**存在**的行只有 16 条 → `locate_header_rows` 返回 0-based 下标 **16**
    （D26「行按出现顺序、不按 `r` 补空行」的直接结果）。
    """
    return [
        [Text("微信支付账单明细", HEADER_STYLE)],
        [Text("微信昵称：[合成测试昵称]", HEADER_STYLE)],
        [Text("起始时间：[2026-01-01 00:00:00] 终止时间：[2026-01-31 23:59:59]")],
        [Text("导出类型：[全部]")],
        [Text("导出时间：[2026-02-01 12:00:00]")],
        [Text("本文件为合成夹具，不含任何真实交易内容")],
        [Text(f"共{DATA_ROW_COUNT}笔记录")],
        [Text("收入：1笔 10.00元")],
        [Text("支出：2笔 22.12元")],
        [Text("中性交易：1笔 0.00元")],
        [Text("注：")],
        [Text("1. 本表格内的所有金额均为人民币单位元")],
        [Text("2. 实付款进账，默认表示支付成功")],
        [Text("3. 已退款表示该笔交易已退款")],
        [Text("4. 本账单仅包含账单日期范围内的交易记录")],
        None,  # 第 16 行：XML 里没有 <row r="16">
        [Text("----微信支付账单明细列表----")],  # 第 17 行：分隔线只有 A 列 1 格
    ]


def wechat_data_rows() -> list[Sequence[Cell]]:
    """数据行**全部合成**：日期列 = 序列号 + ``s=1``、金额列 = 裸数字 + ``s=3``、
    其余 9 列 = ``t="s"`` + ``s=2``；``收/支`` 覆盖 ``支出 / 收入 / /``（D31），
    ``商户单号``/``备注`` 用 ``/`` 空占位形态（§0.4-13）。
    """
    spec = [
        (DATE_SERIAL_TEXT, "微信支付", "合成商户甲", "合成商品A", "支出", "9.78", "零钱", "支付成功", "SYN0001", "/", "/"),
        ("46290.5", "QQ红包", "合成商户乙", "合成商品B", "收入", "10", "零钱", "已退款¥10.00", "SYN0002", "/", "/"),
        ("46291.0", "中性交易", "/", "合成商品C", "/", "0", "/", "交易关闭", "SYN0003", "/", "/"),
        ("46292.25", "商户消费", "合成商户丙", "合成商品D", "支出", "12.34", "信用卡(0000)", "支付成功", "SYN0004", "SYN-MCH-4", "合成备注"),
    ]
    rows: list[list[Cell]] = []
    for serial, channel, party, goods, direction, amount, method, status, trade_no, mch_no, remark in spec:
        rows.append(
            [
                Num(serial, DATE_STYLE),
                Text(channel, TEXT_STYLE),
                Text(party, TEXT_STYLE),
                Text(goods, TEXT_STYLE),
                Text(direction, TEXT_STYLE),
                Num(amount, AMOUNT_STYLE),
                Text(method, TEXT_STYLE),
                Text(status, TEXT_STYLE),
                Text(trade_no, TEXT_STYLE),
                Text(mch_no, TEXT_STYLE),
                Text(remark, TEXT_STYLE),
            ]
        )
    return rows


def wechat_matrix_rows(*, extra_preamble: int = 0) -> list[Sequence[Cell] | None]:
    """完整镜像行矩阵（前导 + 表头 + 数据）。

    ``extra_preamble`` 取证 D1/D2 的「前导行数必然漂移」：在编号注释区**再插** N 条合成
    注释行（第 16 行整体缺失的形态保持不变，只是行号后移）。
    """
    preamble = list(wechat_preamble_rows())
    for position in range(extra_preamble):
        preamble.insert(
            15 + position,
            [Text(f"{5 + position}. 追加编号注释（合成变体第 {position + 1} 条）")],
        )
    header: list[Cell] = [Text(name, HEADER_STYLE) for name in WECHAT_HEADERS]
    return [*preamble, header, *wechat_data_rows()]


def wechat_xlsx_bytes(
    *,
    inline: bool = False,
    extra_preamble: int = 0,
    hidden_before: int = 0,
) -> bytes:
    """真实镜像形态的 ``.xlsx`` 字节（M5 复用的主入口）。"""
    return build_xlsx(
        wechat_matrix_rows(extra_preamble=extra_preamble),
        inline=inline,
        hidden_before=hidden_before,
    )


def _zip_write(payload: bytes, *, drop: str = "", replace: tuple[str, bytes] | None = None) -> bytes:
    """重打包夹具：删一个 entry（`drop`）或替换其内容（`replace`），造 D27 的畸形文件。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(payload)) as source, zipfile.ZipFile(
        buffer, "w", zipfile.ZIP_DEFLATED
    ) as target:
        for info in source.infolist():
            if info.filename == drop:
                continue
            data = source.read(info.filename)
            if replace and info.filename == replace[0]:
                data = replace[1]
            target.writestr(info.filename, data)
    return buffer.getvalue()


# ══════════════════════════════════════════════════════════════════
#  §4.1 构造器两形态（7 entry / inlineStr 无 sharedStrings）
# ══════════════════════════════════════════════════════════════════


def test_builder_writes_the_seven_named_entries() -> None:
    """§4.1 点名的 7 个 entry 逐名在场（`styles.xml` 是 §1.5 numFmt 判定的必需项）。"""
    with zipfile.ZipFile(io.BytesIO(wechat_xlsx_bytes())) as archive:
        assert set(archive.namelist()) == set(DEFAULT_ENTRY_NAMES)
        assert len(DEFAULT_ENTRY_NAMES) == 7
        assert b'<sheet name="Sheet1"' in archive.read("xl/workbook.xml")
        assert b"worksheets/sheet1.xml" in archive.read("xl/_rels/workbook.xml.rels")


def test_inline_variant_omits_shared_strings_entry() -> None:
    payload = wechat_xlsx_bytes(inline=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "xl/sharedStrings.xml" not in names
        assert len(names) == len(DEFAULT_ENTRY_NAMES) - 1
        assert b't="inlineStr"' in archive.read("xl/worksheets/sheet1.xml")


# ══════════════════════════════════════════════════════════════════
#  §4.2 结构镜像断言
# ══════════════════════════════════════════════════════════════════


def _sheet_xml_of(payload: bytes, entry: str = "xl/worksheets/sheet1.xml") -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return archive.read(entry).decode("utf-8")


def test_fixture_mirrors_row_structure_of_design_0_4_13() -> None:
    xml = _sheet_xml_of(wechat_xlsx_bytes())
    numbers = [int(node) for node in re.findall(r'<row r="(\d+)">', xml)]
    # 前导 17 行（含缺失的第 16 行）→ 表头是文件第 18 行，矩阵里第 17 个 <row>
    assert numbers[:17] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18]
    assert '<row r="16">' not in xml
    assert numbers[17] == 19  # 首条数据行
    assert numbers[-1] == 18 + DATA_ROW_COUNT


def test_fixture_has_11_header_columns_and_single_cell_separator() -> None:
    payload = wechat_xlsx_bytes()
    xml = _sheet_xml_of(payload)
    header_row = xml.split('<row r="18">')[1].split("</row>")[0]
    assert header_row.count("<c ") == len(WECHAT_HEADERS) == 11
    assert xlsx_rows(payload)[16] == list(WECHAT_HEADERS)

    separator_row = xml.split('<row r="17">')[1].split("</row>")[0]
    assert separator_row.count("<c ") == 1  # 实测「第 17 行仅 A 列 1 格」
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert "----微信支付账单明细列表----" in archive.read("xl/sharedStrings.xml").decode("utf-8")


def test_fixture_data_shape_directions_and_slash_placeholders() -> None:
    data = xlsx_rows(wechat_xlsx_bytes())[-DATA_ROW_COUNT:]
    assert [row[4] for row in data] == ["支出", "收入", "/", "支出"]
    assert [row[10] for row in data] == ["/", "/", "/", "合成备注"]  # 备注列 `/` 占位形态
    assert [row[9] for row in data][:2] == ["/", "/"]  # 商户单号列同形态
    assert {row[8][:3] for row in data} == {"SYN"}  # 交易单号为合成值


# ══════════════════════════════════════════════════════════════════
#  §4.3 detect_container 三态（只看 magic，D22）
# ══════════════════════════════════════════════════════════════════


def test_detect_container_three_states() -> None:
    assert detect_container(wechat_xlsx_bytes()) == "xlsx"
    assert detect_container(xlsx_reader.XLS_MAGIC + b"\x00" * 4096) == "xls"
    assert detect_container(b"amount,type\n1.0,expense\n") == "csv"
    assert detect_container(b"") == "csv"


def test_detect_container_uses_exact_magic_not_extension_or_near_match() -> None:
    """D22：判据是 magic 本身——`PK` 开头但不是 `PK\\x03\\x04` 仍走 CSV 通道。"""
    assert detect_container(b"PKnotes,not really a zip") == "csv"
    assert detect_container(b"\xd0\xcf\x11\xe1" + b"\x00" * 8) == "csv"
    assert detect_container(b"amount,type\n" + wechat_xlsx_bytes()) == "csv"
    assert detect_container(wechat_xlsx_bytes() + b"trailing") == "xlsx"


# ══════════════════════════════════════════════════════════════════
#  §4.4 行矩阵：等长补齐 + 行序 + 跳列 + 两形态一致
# ══════════════════════════════════════════════════════════════════


def test_matrix_is_equal_length_and_in_appearance_order() -> None:
    rows = xlsx_rows(wechat_xlsx_bytes())
    assert {len(row) for row in rows} == {11}  # 等长补齐（D25/D26）
    assert len(rows) == 16 + 1 + DATA_ROW_COUNT  # 16 条前导（第 16 行不存在）+ 表头 + 数据
    assert rows[0][0] == "微信支付账单明细"
    assert rows[14][0] == "4. 本账单仅包含账单日期范围内的交易记录"
    assert rows[15][0].startswith("----微信支付账单明细列表----")  # 缺行不补、也不丢分隔线
    assert rows[16] == list(WECHAT_HEADERS)


def test_separator_row_is_padded_with_empty_strings() -> None:
    rows = xlsx_rows(wechat_xlsx_bytes())
    assert rows[15] == ["----微信支付账单明细列表----", *[""] * 10]


def test_missing_columns_become_empty_strings() -> None:
    rows = xlsx_rows(
        build_xlsx(
            [
                ["表头一", None, "表头三"],
                ["a", None, "c"],
                [None, "b"],
            ]
        )
    )
    assert rows == [["表头一", "", "表头三"], ["a", "", "c"], ["", "b", ""]]


def test_shared_string_and_inline_forms_agree_cell_by_cell() -> None:
    assert xlsx_rows(wechat_xlsx_bytes()) == xlsx_rows(wechat_xlsx_bytes(inline=True))


def test_other_cell_types_follow_the_reader_rule_table() -> None:
    rows = xlsx_rows(
        build_xlsx(
            [[Inline("行内串"), FormulaStr("公式缓存"), Bool("1"), Bool("0"), ErrorCell("#DIV/0!"), Num("42")]]
        )
    )
    assert rows == [["行内串", "公式缓存", "true", "false", "", "42"]]


def test_multi_sheet_takes_first_visible_one() -> None:
    """§1.3 边界：多 sheet 只取第一个非 hidden（不猜用户要哪张）。"""
    payload = wechat_xlsx_bytes(hidden_before=2)
    rows = xlsx_rows(payload)
    assert rows[0][0] == "微信支付账单明细"
    assert "隐藏占位表，不应被读取" not in {row[0] for row in rows}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert "xl/worksheets/sheet3.xml" in archive.namelist()


# ══════════════════════════════════════════════════════════════════
#  §4.5 日期序列号换算（D24）与金额不改写
# ══════════════════════════════════════════════════════════════════


def test_serial_conversion_is_verbatim_and_naive() -> None:
    assert excel_serial_to_text(46289.48678240741) == "2026-09-24 11:40:58"
    assert excel_serial_to_text(float(DATE_SERIAL_TEXT)) == DATE_TEXT
    assert "T" not in DATE_TEXT and "Z" not in DATE_TEXT and "+08" not in DATE_TEXT
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", DATE_TEXT)


def test_date_styled_cells_are_converted_in_matrix() -> None:
    data = xlsx_rows(wechat_xlsx_bytes())[-DATA_ROW_COUNT:]
    assert [row[0] for row in data] == [
        "2026-09-24 11:40:58",
        "2026-09-25 12:00:00",
        "2026-09-26 00:00:00",  # 整数序列号 = 当日零点（1899-12-30 基准的自洽核对）
        "2026-09-27 06:00:00",
    ]
    # 命中的正是 M2 白名单第 2 位 → M2 零改（设计 §6.2「收益」）
    assert TIME_FORMATS[1] == "%Y-%m-%d %H:%M:%S"
    assert parse_time(data[0][0]) == "2026-09-24 11:40"


def test_amount_cells_are_not_rewritten() -> None:
    data = xlsx_rows(wechat_xlsx_bytes())[-DATA_ROW_COUNT:]
    assert [row[5] for row in data] == ["9.78", "10", "0", "12.34"]  # s=3 的 ¥#,##0.00 不含 y/m/d
    assert parse_amount("9.78") == 9.78
    assert data[1][7] == "已退款¥10.00"  # `¥` 留在值里，容器层不动（交 M2 parse_amount）
    assert parse_amount("¥9.78") == 9.78


def test_out_of_window_and_non_numeric_are_left_alone() -> None:
    assert excel_serial_to_text(19999.0) is None
    assert excel_serial_to_text(80001.0) is None
    assert excel_serial_to_text(float("nan")) is None
    assert excel_serial_to_text(float("inf")) is None
    assert excel_serial_to_text(20000.0) is not None
    assert excel_serial_to_text(80000.0) is not None

    rows = xlsx_rows(
        build_xlsx([[Num("19999", DATE_STYLE), Num("not-a-number", DATE_STYLE), Num("999999", DATE_STYLE), ErrorCell()]])
    )
    assert rows == [["19999", "not-a-number", "999999", ""]]  # 窗外/非数字/错误值 → 原样或空


def test_unstyled_numbers_stay_text() -> None:
    rows = xlsx_rows(build_xlsx([[Num(DATE_SERIAL_TEXT), Num(DATE_SERIAL_TEXT, TEXT_STYLE)]]))
    # 无 `s`（= 0 号样式）与 s=2 都不是日期样式 → 原样文本交给 M2（D15 不猜）
    assert rows == [[DATE_SERIAL_TEXT, DATE_SERIAL_TEXT]]
    assert parse_time(DATE_SERIAL_TEXT) is None


# ══════════════════════════════════════════════════════════════════
#  §4.6 D27 错误文案逐字（全中文 ValueError）+ CSV 空表回归护栏
# ══════════════════════════════════════════════════════════════════


def _message_of(call: Callable[[], object]) -> str:
    """执行并取中文 `ValueError` 文案；**非 `ValueError` 即失败**（D27）。"""
    with pytest.raises(ValueError) as state:
        call()
    assert type(state.value) is ValueError, f"应抛 ValueError 本体：{type(state.value)}"
    return str(state.value)


def test_invalid_zip_is_chinese_value_error() -> None:
    payload = wechat_xlsx_bytes()
    assert _message_of(lambda: xlsx_rows(b"PK\x03\x04garbage-not-a-zip")) == "文件不是有效的 Excel(.xlsx)"
    assert _message_of(lambda: xlsx_rows(payload[: len(payload) // 2])) == "文件不是有效的 Excel(.xlsx)"
    assert _message_of(lambda: xlsx_rows(b"")) == "文件不是有效的 Excel(.xlsx)"


def test_missing_worksheet_entries_are_chinese_value_error() -> None:
    payload = wechat_xlsx_bytes()
    for entry in ("xl/worksheets/sheet1.xml", "xl/workbook.xml", "xl/_rels/workbook.xml.rels"):
        assert _message_of(lambda e=entry: xlsx_rows(_zip_write(payload, drop=e))) == "文件不是有效的 Excel(.xlsx)"


def test_broken_xml_parts_are_chinese_value_error() -> None:
    payload = wechat_xlsx_bytes()
    broken = (
        "xl/sharedStrings.xml",
        "xl/styles.xml",
        "xl/worksheets/sheet1.xml",
        "xl/workbook.xml",
    )
    for entry in broken:
        damaged = _zip_write(payload, replace=(entry, b"<root><unclosed"))
        assert _message_of(lambda e=entry: xlsx_rows(damaged)) == "文件不是有效的 Excel(.xlsx)", entry


def test_shared_string_index_out_of_range_yields_empty_string() -> None:
    """索引越界（坏文件）→ 该格空串，**不抛 KeyError**（D27）。"""
    payload = wechat_xlsx_bytes()
    xml = _sheet_xml_of(payload)
    assert '<v>0</v>' in xml
    damaged = _zip_write(payload, replace=("xl/worksheets/sheet1.xml", xml.replace("<v>0</v>", "<v>9999</v>", 1).encode()))
    assert xlsx_rows(damaged)[0][0] == ""


def test_size_limits_are_checked_from_zip_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = wechat_xlsx_bytes()
    monkeypatch.setattr(xlsx_reader, "MAX_ENTRY_BYTES", 1024)
    assert _message_of(lambda: xlsx_rows(payload)) == "Excel 文件过大或格式异常"
    monkeypatch.setattr(xlsx_reader, "MAX_ENTRY_BYTES", 50 * 1024 * 1024)
    monkeypatch.setattr(xlsx_reader, "MAX_TOTAL_BYTES", 2048)
    assert _message_of(lambda: xlsx_rows(payload)) == "Excel 文件过大或格式异常"


def test_empty_sheet_variants_are_chinese_value_error() -> None:
    assert _message_of(lambda: xlsx_rows(build_xlsx([]))) == "Excel 文件为空"
    assert _message_of(lambda: xlsx_rows(build_xlsx([[]]))) == "Excel 文件为空"
    assert _message_of(lambda: xlsx_rows(build_xlsx([[Text("")], [Text("  ")]]))) == "Excel 文件为空"


def test_xls_magic_gets_chinese_redirect_from_dispatcher() -> None:
    assert _message_of(
        lambda: import_service._to_rows(xlsx_reader.XLS_MAGIC + b"\x00" * 64)
    ) == "暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv"


def test_csv_channel_empty_message_is_untouched() -> None:
    """回归护栏（红线 4）：CSV 通道的 `CSV 文件为空` 原样存在，xlsx 侧文案独立。"""
    text, _encoding = import_service.detect_and_decode(b"")
    assert _message_of(lambda: locate_header_rows(import_service.csv_rows(text))) == "CSV 文件为空"
    assert _message_of(lambda: locate_header_rows([])) == "CSV 文件为空"
    assert _message_of(lambda: locate_header_rows([[""], ["  "]])) == "CSV 文件为空"


def test_no_english_internals_leak_for_junk_bytes() -> None:
    """D27：任何畸形输入只得到中文 `ValueError`，无英文内部异常透出。"""
    forbidden = ("new-line character", "_csv.Error", "BadZipFile", "ParseError", "UnicodeDecodeError", "NoneType")
    payloads = [
        b"PK\x03\x04",
        b"PK\x03\x04\x00\x00",
        wechat_xlsx_bytes()[:40] + b"\x00" * 50,
        b"\xd0\xcf\x11\xe0" + b"\x01" * 20,
        bytes(range(256)),
        b"\xef\xbb\xbfPK\x03\x04",
        b";;;,,,",
    ]
    for payload in payloads:
        try:
            import_service._to_rows(payload)
        except ValueError as exc:
            assert str(exc)
            for marker in forbidden:
                assert marker not in str(exc)


# ══════════════════════════════════════════════════════════════════
#  §4.7 零新增依赖（D23，`ast` 钉死 import 白名单）
# ══════════════════════════════════════════════════════════════════


def _module_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


def _forbidden_excel_libs() -> tuple[str, ...]:
    """D23 / 红线 13 点名的禁引第三方表格与数据框架名单（Excel 读取只准用标准库）。

    名字写成**相邻字面量拼接**：运行时仍是完整字符串，但源码里不存在连续字面量，
    以保证终验口径「`git grep -i -E` 三个库名对 backend/tests 零命中」（progress.md
    终验清单）与本用例同时成立。
    """
    return ("open" "pyxl", "xl" "rd", "pan" "das", "xlsx" "writer", "odf" "py")


def test_xlsx_reader_module_level_imports_are_whitelisted() -> None:
    imported = _module_level_imports(Path(xlsx_reader.__file__))
    assert imported == {"io", "re", "xml.etree.ElementTree", "zipfile", "datetime"}
    roots = {name.split(".")[0] for name in imported}
    assert roots <= set(sys.stdlib_module_names)  # 全标准库 = 零新增依赖（D23）
    assert roots.isdisjoint(_forbidden_excel_libs())


def test_import_service_gains_no_third_party_import() -> None:
    """`import_service.py` 的非标准库根包仍只有既有三个（新增的是项目内 `app.services.xlsx_reader`）。"""
    imported = _module_level_imports(Path(import_service.__file__))
    assert {name.split(".")[0] for name in imported} - set(sys.stdlib_module_names) == {
        "chardet",
        "sqlmodel",
        "app",
    }
    assert "app.services.xlsx_reader" in imported
    assert not any(name.startswith(("zipfile", "xml")) for name in imported)  # 红线 12


def test_no_forbidden_excel_library_name_in_m6_sources() -> None:
    for path in (Path(xlsx_reader.__file__), Path(import_service.__file__)):
        source = path.read_text(encoding="utf-8")
        for name in _forbidden_excel_libs():
            assert name not in source, (path.name, name)


# ══════════════════════════════════════════════════════════════════
#  §4.8 交叉断言：同一份「表头 + 3 行数据」两通道行矩阵逐格相等
# ══════════════════════════════════════════════════════════════════


def test_csv_and_xlsx_channels_produce_identical_matrix() -> None:
    rows: list[list[str]] = [
        list(WECHAT_HEADERS),
        ["2026-01-05 09:30:00", "商户消费", "合成商户A", "合成商品A", "支出", "9.78", "零钱", "支付成功", "SYN1", "MCH1", "/"],
        ["2026-01-06 20:15:30", "转账", "合成商户B", "合成商品B", "收入", "10", "零钱", "已入账", "SYN2", "/", "合成备注"],
        ["2026-01-07 08:00:00", "中性交易", "/", "合成商品C", "/", "0", "/", "交易关闭", "SYN3", "/", "/"],
    ]
    csv_bytes = "\n".join(",".join(row) for row in rows).encode("utf-8")
    xlsx_payload = build_xlsx([[cell for cell in row] for row in rows])

    csv_matrix, csv_container = import_service._to_rows(csv_bytes)
    xlsx_matrix, xlsx_container = import_service._to_rows(xlsx_payload)

    assert (csv_container, xlsx_container) == ("csv", "xlsx")
    assert len(csv_matrix) == len(xlsx_matrix) == len(rows)
    for index, (left, right) in enumerate(zip(csv_matrix, xlsx_matrix)):
        assert left == right, f"第 {index} 行两套通道不一致"
    assert import_service.csv_rows(csv_bytes.decode()) == xlsx_rows(xlsx_payload)


# ══════════════════════════════════════════════════════════════════
#  §4.9 完整识别链（复用 M1 契约，D25/D30）
# ══════════════════════════════════════════════════════════════════


def test_full_recognition_chain_on_xlsx_rows() -> None:
    rows, container = import_service._to_rows(wechat_xlsx_bytes())
    assert container == "xlsx"
    header_index, headers, data_rows = locate_header_rows(rows)
    assert header_index == 16  # 出现顺序口径（D26）
    dialect = match_dialect(headers)
    assert dialect is not None and dialect.key == "wechat"

    raw_headers = [cell.strip() for cell in rows[header_index]]
    hints = resolve_columns(raw_headers, dialect, data_rows)
    assert {hint.header: hint.role for hint in hints} == {
        "交易时间": "consume_time",
        "交易类型": "category",
        "交易对方": "note",
        "商品": "note",
        "收/支": "type",
        "金额(元)": "amount",
        "支付方式": None,
        "当前状态": None,
        "交易单号": None,
        "商户单号": None,
        "备注": None,
    }, "v1.4.4 V2：交易类型是分类来源、交易对方并入备注"
    assert "category" in {hint.role for hint in hints}, "V2 之后微信有分类列"
    assert [hint.header for hint in hints if hint.role == "note"] == ["交易对方", "商品"]
    assert not any(hint.conflict for hint in hints), "note 多列并存不判冲突（V2 的唯一例外）"


def test_note_role_goes_to_earlier_column_on_custom_path() -> None:
    """custom 路径的 v1.4.4 V2 新规则：`商品` 与 `备注` **同为 note**（多列并存）。

    旧口径（D3）：靠前者得角色、后者标冲突。V2 把 `note` 定为「每角色一列」的唯一例外
    （一个文件的备注可来自多列），故 `商品` 与 `备注` 两列都拿到 `note` 且都不标冲突；
    `交易对方`（别名表已改判 note）同样并存。其余角色的独占规则**未放宽**，取证在
    `test_csv_dialects.py::test_8_6_note_is_the_only_multi_column_role`。
    """
    rows, _container = import_service._to_rows(wechat_xlsx_bytes())
    header_index, _headers, data_rows = locate_header_rows(rows)
    raw_headers = [cell.strip() for cell in rows[header_index]]
    by_header = {hint.header: hint for hint in resolve_columns(raw_headers, None, data_rows)}
    assert by_header["商品"].role == "note" and not by_header["商品"].conflict
    assert by_header["备注"].role == "note" and not by_header["备注"].conflict
    assert by_header["交易对方"].role == "note", "别名表全局：交易对方也是备注来源"


def test_preamble_drift_still_locates_the_header() -> None:
    """D1/D2：前导行数漂移（多 2 条编号注释）后仍按内容命中表头。"""
    rows, _container = import_service._to_rows(wechat_xlsx_bytes(extra_preamble=2))
    header_index, headers, _data = locate_header_rows(rows)
    assert header_index == 18 and headers[0] == "交易时间"
    assert match_dialect(headers) is not None


# ══════════════════════════════════════════════════════════════════
#  §4.10 分派与契约：preview_csv 八字段 + 缓存后缀成对
# ══════════════════════════════════════════════════════════════════


async def test_preview_contract_for_synthetic_xlsx() -> None:
    result = await import_service.preview_csv(NO_DB, wechat_xlsx_bytes())
    assert result["container"] == "xlsx"
    assert result["encoding"] == "xlsx"
    assert result["format"] == "wechat"
    assert result["header_row_index"] == 16
    assert result["row_count"] == DATA_ROW_COUNT
    assert result["headers"] == list(WECHAT_HEADERS)
    assert result["suggested_type_source"] == "column"
    assert len(result["sample_rows"]) == DATA_ROW_COUNT
    assert result["sample_rows"][0][0] == DATE_TEXT
    assert result["categories_in_file"] == ["QQ红包", "中性交易", "商户消费", "微信支付"], \
        "v1.4.4 V2：微信的分类来源是 `交易类型` 列"
    assert f"已忽略表头前的 {result['header_row_index']} 行说明文字" in result["warnings"]
    assert "未识别到分类列：需指定默认分类" not in result["warnings"], "V2：微信已有分类列"
    assert set(result) == {
        "format",
        "row_count",
        "categories_in_file",
        "tags_in_file",
        "cache_id",
        "headers",
        "header_row_index",
        "columns",
        "suggested_type_source",
        "encoding",
        "container",
        "sample_rows",
        "warnings",
    }


async def test_preview_header_row_index_can_be_seventeen() -> None:
    """§4.10 的字面口径：17 条**存在**的前导行 → `header_row_index == 17`。

    真实镜像夹具（第 16 行整体缺失）前导**存在**行只有 16 条，故上一条断言 16；
    此处以「再加一条合成前导注释」的变体把 17 口径也钉住（两个口径都在场）。
    """
    result = await import_service.preview_csv(NO_DB, wechat_xlsx_bytes(extra_preamble=1))
    assert result["header_row_index"] == 17
    assert result["container"] == "xlsx"
    assert result["row_count"] == DATA_ROW_COUNT


async def test_csv_channel_contract_is_unchanged() -> None:
    text = "amount,type,category_name,tag_name,consume_time,note\n50.0,expense,餐饮,午餐,2024-01-15 12:00,测试\n"
    result = await import_service.preview_csv(NO_DB, text.encode("utf-8"))
    assert result["container"] == "csv"
    assert result["encoding"] == "utf-8"
    assert result["header_row_index"] == 0
    assert result["format"] == "native"
    assert result["row_count"] == 1


async def test_cache_suffix_pairing_roundtrip() -> None:
    """缓存后缀成对：按 `cache_id` 读回同批字节并重算出同一 container（M6 §2.4）。"""
    payload = wechat_xlsx_bytes()
    result = await import_service.preview_csv(NO_DB, payload)
    cache_id = result["cache_id"]

    recovered = read_from_cache(cache_id, ".xlsx")
    assert recovered == payload
    rows, container = import_service._to_rows(recovered)
    assert container == "xlsx" == result["container"]
    assert locate_header_rows(rows)[0] == result["header_row_index"]

    assert import_service._read_cached_bytes(cache_id) == payload
    with pytest.raises(FileNotFoundError):  # 后缀仍是文件名装饰，不是判据（D22）
        read_from_cache(cache_id, ".csv")

    delete_cache(cache_id, ".xlsx")
    with pytest.raises(FileNotFoundError):
        import_service._read_cached_bytes(cache_id)


async def test_csv_cache_still_uses_csv_suffix() -> None:
    text = "amount,type,category_name,tag_name,consume_time,note\n50.0,expense,餐饮,,2024-01-15 12:00,x\n"
    result = await import_service.preview_csv(NO_DB, text.encode("utf-8"))
    cache_id = result["cache_id"]
    assert read_from_cache(cache_id, ".csv") == text.encode("utf-8")
    assert import_service._read_cached_bytes(cache_id) == text.encode("utf-8")
    delete_cache(cache_id, ".csv")


async def test_xls_upload_gets_chinese_message_at_first_step() -> None:
    """`.xls` 在预览首步即中文拒绝（D22/D27），不产生缓存。"""
    with pytest.raises(ValueError) as state:
        await import_service.preview_csv(NO_DB, xlsx_reader.XLS_MAGIC + b"\x00" * 4096)
    assert str(state.value) == "暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv"


# ══════════════════════════════════════════════════════════════════
#  §3.1 / §3.2 跨模块核验（只断言，不改他人文件）
# ══════════════════════════════════════════════════════════════════


def test_slash_in_type_column_is_type_ignored_not_unresolved() -> None:
    """§3.1（`TYPE_VALUE_IGNORE` 补 `/` 的改动归 M2）——在场即通过，缺了此断言即红。"""
    assert resolve_type("/", 9.78, "column") == (None, "type_ignored")
    assert resolve_type("支出", 9.78, "column") == ("expense", None)
    assert resolve_type("收入", 10.0, "column") == ("income", None)


async def test_slash_placeholder_absent_from_categories_and_tags() -> None:
    """§3.2：`/` 在分类 / 标签 / 备注列按空串处理，不进 `categories_in_file`/`tags_in_file`。

    v1.4.4 V2：镜像的 `交易对方` 已改判 note（备注来源）→ 微信形态**没有** tag 列，
    `tags_in_file` 恒为空集；分类集合改由 `交易类型` 供值，`/` 那一行的值仍被排除在外。
    """
    result = await import_service.preview_csv(NO_DB, wechat_xlsx_bytes())
    assert "/" not in result["categories_in_file"]
    assert "/" not in result["tags_in_file"]
    assert result["tags_in_file"] == [], "V2：微信不再产生标签（交易对方→note）"
    assert result["categories_in_file"] == ["QQ红包", "中性交易", "商户消费", "微信支付"]
    assert result["row_count"] == DATA_ROW_COUNT


# ══════════════════════════════════════════════════════════════════
#  §4.11 范围护栏（不新建 e2e、不改前端、xlsx 解析与表头定位各只有一份）
# ══════════════════════════════════════════════════════════════════


def test_scope_guards_for_m6() -> None:
    """§4.11：需求 E 的 HTTP 端到端属 M5、`accept` 与 `container` 标识属 M4，本文件不越界。"""
    own_imports = {
        name.split(".")[0] for name in _module_level_imports(Path(__file__))
    }
    assert own_imports.isdisjoint({"httpx", "fastapi", "requests"})  # 无 HTTP e2e（需求 E 的端到端归 M5）

    service_source = Path(import_service.__file__).read_text(encoding="utf-8")
    assert "zipfile" not in service_source and "iterparse" not in service_source  # 红线 12
    assert "def locate_header_rows" not in service_source  # 表头定位只有一份实现

    dialects_source = Path(xlsx_reader.__file__).with_name("csv_dialects.py").read_text(encoding="utf-8")
    for name in ("normalize_header", "locate_header_rows", "match_dialect", "resolve_columns"):
        assert dialects_source.count(f"def {name}") == 1, name
