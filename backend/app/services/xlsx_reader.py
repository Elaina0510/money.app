"""Excel（``.xlsx``）容器读取层（v1.4.3-boot3 M6，设计 §6.2，需求 E）。

职责**只有一段**：把上传的**字节**归一为**行矩阵** ``list[list[str]]``，交给 M1 的
识别链（``locate_header_rows`` / ``match_dialect`` / ``resolve_columns``）。
本模块**不做**表头定位、不判列角色、不清洗值、不碰数据库、不 import
``import_service``（D25/D28：表头定位全仓只有一份实现，xlsx 解析只在本文件）。

零新增依赖（D23）：只用标准库 ``zipfile`` + ``xml.etree.ElementTree``（iterparse）
+ ``datetime`` + ``re``（``io.BytesIO`` 仅为把 ``bytes`` 交给 ``zipfile.ZipFile``——
``ZipFile`` 不接受裸 bytes，这是 §1.7 白名单的唯一必要补充，仍是标准库、
零第三方依赖；``tests/test_xlsx_reader.py`` §4.7 用 ``ast`` 把 import 集合钉死）。

一手事实来源（设计 §0.4-13 的**结构**登记，禁止凭 OOXML 常识扩写）：真实微信账单
`.xlsx` = 单 sheet、11 列、表头在文件第 18 行（前导说明含 4 条编号注释与单格分隔线）、
**第 16 行在 XML 里整体缺 ``<row r="16">``**、`时间列是数字序列号 + numFmt
`yyyy-mm-dd hh:mm:ss`、金额列是裸数字 + numFmt `¥#,##0.00`、单元格仅 `t="s"` 与无
`t` 数字两类。本模块对上述每个环节都留了最小兜底分支（`inlineStr` / `str` / `b` / `e`），
以便「其它导出方」的文件不产生新的英文内部异常。
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta

# ── 常量（M6 §1.1） ─────────────────────────────────────────────────

XLSX_MAGIC: bytes = b"PK\x03\x04"
"""zip 本地文件头 magic（xlsx / xlsm / ods 共用）——容器判定的**唯一**依据（D22）。"""

XLS_MAGIC: bytes = b"\xd0\xcf\x11\xe0"
"""老 OLE 复合文档 magic（`.xls`）→ 明确不支持，给中文另存指引（D22/§6.4）。"""

MAX_ENTRY_BYTES: int = 50 * 1024 * 1024
"""单 entry 解压后上限（D27）。"""

MAX_TOTAL_BYTES: int = 200 * 1024 * 1024
"""全部 entry 解压后合计上限（D27）。"""

EXCEL_EPOCH = datetime(1899, 12, 30)
"""Excel 序列号基准日（D24）：`1900-01-01` 记为 1、并含 1900 闰年缺陷 → 基准落在 1899-12-30。"""

SERIAL_MIN: float = 20000.0
SERIAL_MAX: float = 80000.0
"""序列号合理窗口（约 1954–2119 年）。窗外**不换算不猜**（D24/D15），原样文本交给 M2。"""

DATE_OUTPUT_FORMAT = "%Y-%m-%d %H:%M:%S"
"""日期单元格的产物形态：**naive 挂钟文本**（零时区偏移），命中 M2 `TIME_FORMATS` 第 2 位。"""

BUILTIN_DATE_NUM_FORMATS: frozenset[int] = frozenset(
    {14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47}
)
"""OOXML 内置日期/时间 numFmtId 表（§6.2 步骤 2）。"""

ERROR_INVALID_XLSX = "文件不是有效的 Excel(.xlsx)"
ERROR_TOO_LARGE = "Excel 文件过大或格式异常"
ERROR_EMPTY_XLSX = "Excel 文件为空"
ERROR_XLS_UNSUPPORTED = "暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv"
"""四条中文失败文案（D27）：全部以 `ValueError` 抛出 → 路由 `PARAM_ERROR`，
绝不把 `BadZipFile` / `ParseError` / `KeyError` 的英文内部文案透给用户。"""

WORKBOOK_ENTRY = "xl/workbook.xml"
WORKBOOK_RELS_ENTRY = "xl/_rels/workbook.xml.rels"
SHARED_STRINGS_ENTRY = "xl/sharedStrings.xml"
STYLES_ENTRY = "xl/styles.xml"

_HIDDEN_STATES = frozenset({"hidden", "veryhidden"})
_LOCAL_PART_RE = re.compile(r"^.*\}")
_COLUMN_LETTERS_RE = re.compile(r"^([A-Za-z]+)")


# ── 容器判定（D22） ─────────────────────────────────────────────────


def detect_container(file_bytes: bytes) -> str:
    """字节 → `"xlsx" | "xls" | "csv"`：**只看前 8 字节 magic**，不信扩展名、
    不信缓存文件名后缀（D22：用户改名、后端缓存后缀都只是观感）。

    纯函数、直接吃 `bytes`（不用 `zipfile.is_zipfile` 之类需要 seek 的写法）。
    """
    head = file_bytes[:8]
    if head.startswith(XLSX_MAGIC):
        return "xlsx"
    if head.startswith(XLS_MAGIC):
        return "xls"
    return "csv"


# ── 对外主函数（M6 §1.3） ───────────────────────────────────────────


def xlsx_rows(file_bytes: bytes) -> list[list[str]]:
    """``.xlsx`` 字节 → **等长补齐的行矩阵**（D25/D26），唯一产物。

    步骤：zip 限额自检 → 选第一个非 hidden sheet → `styles.xml` 的 numFmt 日期样式集
    → `sharedStrings.xml` → 逐 `<row>` 流式读单元格（列字母 26 进制定位、缺失列补空串、
    **行按出现顺序**编号，不按 `r` 补空行）。

    Raises:
        ValueError: 中文文案 `ERROR_INVALID_XLSX` / `ERROR_TOO_LARGE` / `ERROR_EMPTY_XLSX`。
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(file_bytes))
    except (zipfile.BadZipFile, OSError, EOFError) as exc:  # 截断 / 非 zip / 中央目录损坏
        raise ValueError(ERROR_INVALID_XLSX) from exc

    with archive:
        _guard_zip_limits(archive)
        sheet_entry = _first_visible_sheet(archive)
        date_styles = _date_style_indexes(archive)
        shared = _shared_strings(archive)
        rows = _sheet_rows(archive, sheet_entry, date_styles, shared)

    if not rows or all(_is_blank_row(row) for row in rows):
        raise ValueError(ERROR_EMPTY_XLSX)

    width = max(len(row) for row in rows)
    return [*(_pad(row, width) for row in rows)]


def excel_serial_to_text(serial: float) -> str | None:
    """Excel 日期序列号 → `YYYY-MM-DD HH:MM:SS` **文本**（D24）。

    `datetime(1899, 12, 30) + timedelta(days=serial)`，**naive 挂钟、零时区偏移**——
    真实账单第 15 行自述「所有时间均为 UTC+08:00」，与用户在微信 App 所见逐位一致，
    故容器层不做任何时区换算。产物文本正好落在 M2 `TIME_FORMATS` 白名单第 2 位
    → M2/M3 对 xlsx 零特殊分支。

    窗外（`[20000, 80000]` 之外）、`nan`/`inf`、换算溢出 → `None`（**不猜**，D15），
    由调用方把原样文本交给 M2。逐位实证：`46289.48678240741` → `2026-09-24 11:40:58`。
    """
    if not SERIAL_MIN <= serial <= SERIAL_MAX:  # nan 与 inf 在此一并落 None
        return None
    try:
        moment = EXCEL_EPOCH + timedelta(days=serial)
    except (OverflowError, ValueError):
        return None
    return moment.strftime(DATE_OUTPUT_FORMAT)


# ── zip 限额与 entry 读取（D27） ────────────────────────────────────


def _guard_zip_limits(archive: zipfile.ZipFile) -> None:
    """逐 entry **先查 `ZipInfo.file_size`（解压后体积）再读**，防 zip 炸弹（D27）。

    阈值是设计登记的经验值（50 MB / 200 MB），只查元数据、不解压，故对正常文件零成本。
    """
    total = 0
    for info in archive.infolist():
        if info.file_size > MAX_ENTRY_BYTES:
            raise ValueError(ERROR_TOO_LARGE)
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise ValueError(ERROR_TOO_LARGE)


def _read_entry(
    archive: zipfile.ZipFile, name: str, *, required: bool = True
) -> bytes | None:
    """取一个 entry 的字节；缺失且 `required=False` 返回 `None`（`sharedStrings.xml` /
    `styles.xml` 合法缺席），其余异常一律收口成中文 `ValueError`。"""
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        if not required:
            return None
        raise ValueError(ERROR_INVALID_XLSX) from exc
    if info.file_size > MAX_ENTRY_BYTES:
        raise ValueError(ERROR_TOO_LARGE)
    try:
        return archive.read(name)
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as exc:
        # 含「加密 entry / 未知压缩算法」——zipfile 对这些抛 RuntimeError 而非 ValueError
        raise ValueError(ERROR_INVALID_XLSX) from exc


def _parse_xml(data: bytes) -> ET.Element:
    """`bytes` → Element；XML 自身畸形即「不是有效的 xlsx」（D27，禁 `ParseError` 裸冒）。"""
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(ERROR_INVALID_XLSX) from exc


# ── 选表（§1.3：第一个非 hidden sheet） ─────────────────────────────


def _first_visible_sheet(archive: zipfile.ZipFile) -> str:
    """`xl/workbook.xml` 第一个**非 hidden** `<sheet>` → 其 `r:id` 经 rels 映射到 entry 路径。

    多 sheet 只取第一张可见的——**不猜用户要哪张**（设计 §6.2 登记的边界）。
    """
    workbook = _read_entry(archive, WORKBOOK_ENTRY)
    if workbook is None:  # `required=True` 已在缺失时抛，此分支只为满足类型收窄
        raise ValueError(ERROR_INVALID_XLSX)
    root = _parse_xml(workbook)
    targets = _sheet_targets(archive)

    for sheet in root.iter():
        if _local(sheet.tag) != "sheet":
            continue
        if (sheet.get("state") or "").strip().lower() in _HIDDEN_STATES:
            continue
        relation = _attr(sheet, "id")
        target = targets.get(relation) if relation else None
        if target:
            return _resolve_entry_path(archive, target)
    raise ValueError(ERROR_INVALID_XLSX)


def _sheet_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    """`xl/_rels/workbook.xml.rels` → `{Relationship/@Id: Target}`（rels 缺席即空表）。"""
    raw = _read_entry(archive, WORKBOOK_RELS_ENTRY, required=False)
    if raw is None:
        return {}
    mapping: dict[str, str] = {}
    for node in _parse_xml(raw).iter():
        if _local(node.tag) != "Relationship":
            continue
        relation_id = node.get("Id")
        target = node.get("Target")
        if relation_id and target:
            mapping[relation_id] = target
    return mapping


def _resolve_entry_path(archive: zipfile.ZipFile, target: str) -> str:
    """`Target` 归一成 zip 内路径：rels 里的 `worksheets/sheet1.xml` 相对 `xl/` 目录。"""
    cleaned = target.replace("\\", "/").lstrip("/")
    candidates = [cleaned] if cleaned.startswith("xl/") else [cleaned, f"xl/{cleaned}"]
    names = set(archive.namelist())
    for candidate in candidates:
        if candidate in names:
            return candidate
    raise ValueError(ERROR_INVALID_XLSX)


# ── 日期样式（§1.5：numFmt 判定，不是列角色） ───────────────────────


def _date_style_indexes(archive: zipfile.ZipFile) -> frozenset[int]:
    """`xl/styles.xml` → **日期样式的下标集**（下标 = 单元格的 `s` 属性）。

    实测钉死（同一真实文件，写死勿改）：`cellXfs` 共 4 项，`s=0/2 → numFmtId=0`、
    **`s=1 → 164 = "yyyy-mm-dd hh:mm:ss"`**、**`s=3 → 165 = "¥#,##0.00"`**；按列分布 =
    **A 列 228 格全 `s=1`（日期）**、**F 列 228 格全 `s=3`（金额）**、其余 9 列全 `s=2`，
    228 = 数据行数。`¥#,##0.00` 不含 `y/m/d` → **金额列不会被误判为日期**，
    `¥` 前缀仍由 M2 `parse_amount` 处理、容器层不动它。

    判据（设计 §6.2 步骤 2，逐字实现）：内置 `numFmtId ∈ {14..22, 45, 46, 47}`
    **或** 自定义 `formatCode` 含 `y`/`m`/`d`（大小写不敏感）。日期身份**只看样式**，
    容器层拿不到列角色，故不按列猜（D24）。
    """
    raw = _read_entry(archive, STYLES_ENTRY, required=False)
    if raw is None:
        return frozenset()
    root = _parse_xml(raw)

    custom: dict[int, str] = {}
    for node in root.iter():
        if _local(node.tag) != "numFmt":
            continue
        format_id = _to_int(node.get("numFmtId"))
        if format_id is not None:
            custom[format_id] = node.get("formatCode") or ""

    indexes: set[int] = set()
    for cell_xfs in root.iter():
        if _local(cell_xfs.tag) != "cellXfs":
            continue
        for position, xf in enumerate(cell_xfs):
            if _local(xf.tag) != "xf":
                continue
            format_id = _to_int(xf.get("numFmtId")) or 0
            if _is_date_format(format_id, custom):
                indexes.add(position)
    return frozenset(indexes)


def _is_date_format(num_fmt_id: int, custom: dict[int, str]) -> bool:
    """一个 `numFmtId` 是否日期样式（内置表命中 **或** 自定义 formatCode 含 y/m/d）。"""
    if num_fmt_id in BUILTIN_DATE_NUM_FORMATS:
        return True
    code = custom.get(num_fmt_id)
    if not code:
        return False
    lowered = code.lower()
    return any(marker in lowered for marker in ("y", "m", "d"))


# ── 共享字符串 ──────────────────────────────────────────────────────


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """`xl/sharedStrings.xml`：每个 `<si>` 拼接其下**全部** `<t>`、**跳过 `<rPh>`**。

    真实文件 `<rPh>` / 富文本 `<r>` 零命中，此处按设计口径实现以兜住其它导出方；
    entry 合法缺席（全数字表）→ 空表。
    """
    raw = _read_entry(archive, SHARED_STRINGS_ENTRY, required=False)
    if raw is None:
        return []
    root = _parse_xml(raw)
    return [
        "".join(_t_texts(si)) for si in root if _local(si.tag) == "si"
    ]


def _t_texts(elem: ET.Element) -> list[str]:
    """递归收集 `<t>` 文本，跳过 `<rPh>`（注音）子树。"""
    parts: list[str] = []
    for child in elem:
        name = _local(child.tag)
        if name == "rPh":
            continue
        if name == "t" and child.text:
            parts.append(child.text)
        parts.extend(_t_texts(child))
    return parts


# ── worksheet 逐行读取（D26 稀疏行列） ──────────────────────────────


def _sheet_rows(
    archive: zipfile.ZipFile,
    entry: str,
    date_styles: frozenset[int],
    shared: list[str],
) -> list[list[str]]:
    """`iterparse` 逐 `<row>` + `elem.clear()`（大表不驻留整棵树），行按**出现顺序**入矩阵。

    实测第 16 行整体缺 `<row r="16">`、第 17 行分隔线只有 1 格——两者都**原样反映**在
    行矩阵里（不按 `r` 补空行、也不丢弃），与 Excel 所见行序一致（D26）。
    """
    rows: list[list[str]] = []
    try:
        with archive.open(entry) as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if _local(element.tag) != "row":
                    continue
                rows.append(_row_cells(element, date_styles, shared))
                element.clear()
    except (
        zipfile.BadZipFile,
        OSError,
        RuntimeError,
        NotImplementedError,
        ET.ParseError,
    ) as exc:
        raise ValueError(ERROR_INVALID_XLSX) from exc
    return rows


def _row_cells(
    row_element: ET.Element, date_styles: frozenset[int], shared: list[str]
) -> list[str]:
    """一行 → 单元格列表：列字母定列位、行内缺失列补空串。"""
    cells: list[str] = []
    next_index = 0
    for cell in row_element:
        if _local(cell.tag) != "c":
            continue
        position = _column_index(cell.get("r"))
        if position is None:  # 极少数导出方省略 `r` → 顺延上一格
            position = next_index
        while len(cells) <= position:
            cells.append("")
        cells[position] = _cell_text(cell, date_styles, shared)
        next_index = position + 1
    return cells


def _cell_text(
    cell: ET.Element, date_styles: frozenset[int], shared: list[str]
) -> str:
    """一个 `<c>` → 文本（§1.3 的单元格分支表，逐条照抄，不扩写）。"""
    cell_type = (cell.get("t") or "").strip()
    if cell_type == "e":  # 错误值（`#DIV/0!` 等）→ 空串，不把错误码当业务值
        return ""
    if cell_type == "inlineStr":
        return "".join(_t_texts(cell))

    value = _child_text(cell, "v")
    if cell_type == "s":
        position = _to_int(value)
        if position is None or not 0 <= position < len(shared):
            return ""  # 索引越界即坏文件，但**不抛 KeyError**（D27）
        return shared[position]
    if cell_type == "b":
        return "true" if (value or "0").strip() not in ("", "0") else "false"
    if cell_type == "str":
        return value or ""

    # 无 `t` = 数字。日期样式命中且落在合理窗口 → 换算为挂钟文本（D24）
    if cell_type == "" and value and _style_of(cell) in date_styles:
        serial = _to_float(value)
        if serial is not None:
            converted = excel_serial_to_text(serial)
            if converted is not None:
                return converted
    return value or ""


def _style_of(cell: ET.Element) -> int | None:
    """单元格的样式下标 `s`（缺省 = 0 号样式）。"""
    return _to_int(cell.get("s"), default=0)


# ── 小工具 ──────────────────────────────────────────────────────────


def _local(tag: str) -> str:
    """去掉 `{namespace}` 前缀取局部名：命名空间前缀随导出方而异，按局部名匹配最稳。"""
    return _LOCAL_PART_RE.sub("", tag)


def _attr(elem: ET.Element, name: str) -> str | None:
    """按**局部名**取属性（`r:id` 与裸 `id` 两种写法都吃）。"""
    direct = elem.get(name)
    if direct is not None:
        return direct
    for key, value in elem.attrib.items():
        if _local(key) == name:
            return value
    return None


def _child_text(elem: ET.Element, name: str) -> str | None:
    """第一个同名子元素的文本（`None` = 无该子元素）。"""
    for child in elem:
        if _local(child.tag) == name:
            return child.text or ""
    return None


def _column_index(reference: str | None) -> int | None:
    """列字母 → 0-based 列下标，26 进制（`A→0`…`Z→25`、`AA→26`，D26）。"""
    if not reference:
        return None
    match = _COLUMN_LETTERS_RE.match(reference.strip())
    if match is None:
        return None
    index = 0
    for char in match.group(1).upper():
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _to_int(raw: str | None, default: int | None = None) -> int | None:
    """宽松取整数：失败返回 `default`（样式下标、共享串索引、`numFmtId` 共用）。"""
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _to_float(raw: str) -> float | None:
    """`<v>` 文本 → float；非数字返回 `None`（交给 M2，不猜，D15）。"""
    try:
        return float(raw.strip())
    except ValueError:
        return None


def _is_blank_row(row: list[str]) -> bool:
    """整行皆空（含全空白）——与 `import_service._is_blank_row` 同口径的本地副本，
    只为不回依赖 `import_service`（§1.7 禁反向 import）而保留最小实现。"""
    return not row or all(cell.strip() == "" for cell in row)


def _pad(row: list[str], width: int) -> list[str]:
    """行矩阵等长补齐（D25/D26：下游按列下标取值不必再判越界）。"""
    if len(row) >= width:
        return row
    return [*row, *([""] * (width - len(row)))]
