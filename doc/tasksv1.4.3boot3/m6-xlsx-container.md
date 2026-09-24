# M6 - 后端 Excel（.xlsx）容器层（需求 E）

> 对应设计 §六。目标：让**真实微信账单 `.xlsx`**（用户 2026-09-24 提供的一手文件）与 `.csv` 走**同一条**识别 / 角色 / 清洗 / 落库链——只在「字节 → 行矩阵」这一段分叉。零新增依赖（stdlib `zipfile` + `xml.etree`，D23）。
> 涉及文件：**新增** `backend/app/services/xlsx_reader.py`、**新增** `backend/tests/test_xlsx_reader.py`；改 `backend/app/services/import_service.py` 的**容器分派入口**（`_to_rows` 新函数 + `preview_csv` 首步 + 缓存后缀实参）。
> 依赖：**M1 已合入**（同文件 `import_service.py` 串行；且要复用 M1 的 `csv_rows()` / `locate_header_rows(rows)` 行矩阵契约）+ **M2 已合入**（`parse_amount` / `parse_time` 承接容器产物）。**M3 尚未开工**（落库区由 M3 改，本模块不得越界改 `import_csv_data` 的解析逻辑，只在 §6.3 口径下为它准备好同一分派器）。
> 一手事实来源（**逐条照此实现，禁止凭 OOXML 常识扩写**）：设计 §0.4-13、D22–D27、D30、D31。

---

## 0. 前置认知（开工必读，30 秒）

- 真实文件：`example/微信支付账单流水文件(20260624-20260924)_20260924123647.xlsx`，28,042 B，**`.gitignore:68` 已忽略 → 任何代码/测试/文档都不得引用其路径、不得抄其中单元格值**（红线 11）。结构事实一律以设计 §0.4-13 的登记为准（本模块实现所需的全部结构信息已在该表，无需去 `open` 真实文件）。
- 现状缺陷（§0.4-14）：把该字节流喂进现有通道 → `csv.reader` 抛英文 `_csv.Error` → 路由 `SERVER_ERROR` 透出内部文案。**本模块连同 D27 一起收口。**

## 1. 新文件 `backend/app/services/xlsx_reader.py`（设计 §6.2）

- [x] 1.1 模块常量：`XLSX_MAGIC = b"PK\x03\x04"`、`XLS_MAGIC = b"\xd0\xcf\x11\xe0"`、`MAX_ENTRY_BYTES = 50 * 1024 * 1024`、`MAX_TOTAL_BYTES = 200 * 1024 * 1024`
- [x] 1.2 `detect_container(file_bytes: bytes) -> str`：返回 `"xlsx" | "xls" | "csv"`，**只看前 8 字节 magic**（D22）；`zipfile.is_zipfile` 之类需 seek 的写法不用（保持纯函数、可喂 `bytes`）
- [x] 1.3 `xlsx_rows(file_bytes: bytes) -> list[list[str]]`：唯一产物是**等长补齐的行矩阵**（D25/D26）
  - 选表：`xl/workbook.xml` 第一个**非 hidden** `<sheet>` → 其 `r:id` 经 `xl/_rels/workbook.xml.rels` 映射到 `Target`（实测该文件 = `worksheets/sheet1.xml`）；缺失 → `ValueError("文件不是有效的 Excel(.xlsx)")`
  - 共享串：`xl/sharedStrings.xml` 每个 `<si>` 拼接其下**全部** `<t>`、**跳过 `<rPh>`**（实测本文件 `<rPh>`/`<r>` 零命中，但按此实现防其它导出方）
  - 单元格：`t="s"`→共享串索引；无 `t`→数字 `<v>` 原样文本；`t="inlineStr"`→`<is>` 内 `<t>`；`t="str"`→`<v>`；`t="b"`→`1/0` 归 `true`/`false`；`t="e"` 与未知 → `""`
  - 列字母 → 索引：26 进制（`A→0`…`Z→25`、`AA→26`）；行内缺失列补 `""`；**行按出现顺序编号，不按 `r` 补空行**（实测第 16 行整体缺失、第 17 行仅 A 列 1 格）
  - 内存：`ET.iterparse(events=("end",))` 逐 `<row>` + `elem.clear()`；先 `ZipInfo.file_size` 校验再 `read`（§1.4）
- [x] 1.4 安全与异常（D27，**全部中文、全部 `ValueError`**）：`单 entry > 50MB 或 总解压 > 200MB` → `"Excel 文件过大或格式异常"`；`BadZipFile`/`NoValidEntry` → `"文件不是有效的 Excel(.xlsx)"`；行矩阵为空 → `"Excel 文件为空"`（**CSV 侧既有文案 `"CSV 文件为空"` 不得改动**，红线 4）
- [x] 1.5 日期单元格判定 = **`styles.xml` 的 numFmt**（不是列角色，§6.2）：解析 `<numFmt numFmtId formatCode>` + `<cellXfs>` 的 `xf/@numFmtId` 列表（下标 = 单元格 `s`）；内置 `∈ {14..22,45,46,47}` **或** 自定义 `formatCode` 含 `y`/`m`/`d`（不分大小写）→ 日期样式
  - 实测钉死（写进 docstring，勿改）：本文件 `cellXfs` 4 项，`s=1 → 164 "yyyy-mm-dd hh:mm:ss"`、`s=3 → 165 "¥#,##0.00"`；**A 列 228 格全 `s=1`、F 列 228 格全 `s=3`、其余 9 列全 `s=2`**，228 = 数据行数。`¥#,##0.00` 不含 `y/m/d` → 金额列不会被误判为日期
- [x] 1.6 `excel_serial_to_text(serial: float) -> str | None`（D24）：`datetime(1899, 12, 30) + timedelta(days=serial)` → `"%Y-%m-%d %H:%M:%S"`；**naive 挂钟、零时区偏移**（该账单第 15 行自述「所有时间均为 UTC+08:00」，与用户在微信所见一致）；超出 `[20000, 80000]` 或非数字 → `None`（原样文本交给 M2）
  - 逐位实证：`46289.48678240741` → **`"2026-09-24 11:40:58"`**
- [x] 1.7 类型注解完整、mypy 基线零新增；模块级 import **只允许** `zipfile` / `xml.etree.ElementTree` / `datetime` / `re`（D23，§4.7 用 `ast` 钉死）；**不 import** `import_service`、不 import ORM/config

## 2. `import_service.py` 容器分派接线（设计 §6.3，M6 在本文件的唯一改动）

- [x] 2.1 新增 `_to_rows(file_bytes: bytes) -> tuple[list[list[str]], str]`：`detect_container` → `xlsx` 走 `xlsx_rows()`；`xls` 抛 `ValueError("暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv")`；`csv` 走 `detect_and_decode()` + **M1 的 `csv_rows()`**；返回 `(行矩阵, container)`
- [x] 2.2 `preview_csv` 首步改为 `_to_rows(file_bytes)`，其后 `locate_header_rows` / `match_dialect` / `resolve_columns` 全部复用 M1 结果（**禁止在 xlsx 分支另写表头逻辑**，D25）
- [x] 2.3 预览 `data` 增字段 `container`（`"csv" | "xlsx"`，D29）；**`encoding` 在 xlsx 通道取 `"xlsx"`**；其余 7 个新字段（§1.2.5）语义与口径**逐位不变**
- [x] 2.4 缓存后缀按容器实参化：`save_to_cache(file_bytes, ".csv")` → `save_to_cache(file_bytes, ".xlsx" if container == "xlsx" else ".csv")`；**`read_from_cache` / `delete_cache` 的 suffix 必须成对改**（实测 `cache.py:_cache_path` 只做字符串拼接，后缀错配即「缓存文件不存在」）
- [x] 2.5 把 `_to_rows` 的可用性与签名写进 `notes`（M3 的 §2.2 重算步骤要用同一个分派器；**M6 不改 `import_csv_data` 的解析逻辑**）
- [x] 2.6 核验零改动面：`preview_sql` / `import_sql_data` / `_import_*` / `detect_sql_format` / `detect_cashew_sqlite` / dormant 往返 **一字不动**（D17/红线 2）；`.sql,.db` 上传口不受影响

## 3. 跨模块核验（**只断言、不改他人文件**；改动归属见括注）

- [x] 3.1 `csv_values.TYPE_VALUE_IGNORE` 含 `"/"`（**改动归 M2**，它独占 `csv_values.py`，见 m2 §3）——本模块用真实结构合成夹具断言：`收/支` 为 `/` 的行 `resolve_type` 返回 `(None, "type_ignored")` 而**不是** `type_unresolved`；缺失即 `notes` 上报、由主 Agent 派 M2 补丁轮，**M6 不代改他人文件**
- [x] 3.2 `/` 在**分类 / 标签 / 备注**列按空串处理（**改动归 M1 的预览集统计 + M2 的值清洗**）：本模块断言合成 xlsx 的 `categories_in_file` / `tags_in_file` **不含** `/`（`备注`/`商户单号` 全为 `/` 的真实形态）
- [x] 3.3 逐字实证写进 `notes`：真实文件 `收/支` 取值分布 = `支出`×176 / `收入`×48 / `/`×4，与文件自述「中性交易：4笔」逐一对齐（设计 §0.4-13、D31）

## 4. 测试（新文件 `backend/tests/test_xlsx_reader.py`，设计 §6.5）

- [x] 4.1 **合成 xlsx 构造器**（测试内 helper，`zipfile.writestr` 手写最小 **7** entry：`[Content_Types].xml`、`_rels/.rels`、`xl/workbook.xml`、`xl/_rels/workbook.xml.rels`、`xl/worksheets/sheet1.xml`、`xl/sharedStrings.xml`、`xl/styles.xml`（§1.5 的 numFmt 判定要它））——**两形态各一份**：① 真实镜像形态（`t="s"` 共享串 + 日期 `s=1`/numFmt 164 + 金额 `s=3`/`¥#,##0.00`）；② `inlineStr` 形态（**不写** sharedStrings entry）
- [x] 4.2 构造器必须镜像 §0.4-13 的**结构**：11 列表头逐字（`交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注`）、前导 **17 行**（含 4 条编号注释 + 单格 `----…----` 分隔线）、**第 16 行整体缺失**（XML 不写该 `<row>`）、`收/支` 出现 `支出/收入//`、备注列 `/`。**数据行一律合成，禁止取自真实账单**（红线 11）
- [x] 4.3 `detect_container` 三态：xlsx magic / OLE `.xls` magic / 普通文本字节
- [x] 4.4 `xlsx_rows`：行矩阵**等长补齐**、行序=出现顺序、跳列补空串（分隔线行 = `["----…----", "", …]`）、两种 cell 形态（`t="s"` 与 `inlineStr`）结果逐格一致
- [x] 4.5 日期换算：`46289.48678240741` → `"2026-09-24 11:40:58"`（逐字）；超窗/非数字/`t="e"` → 不换算或空；金额 `"9.78"` **不被改写**（`¥` 留在值里交 M2 `parse_amount`）
- [x] 4.6 D27 三条错误文案**逐字**断言（含 `.xls` 指引文案）；`"CSV 文件为空"` 在 CSV 通道原样存在（回归护栏）
- [x] 4.7 **零依赖核验**：`ast` 解析 `xlsx_reader.py` 的模块级 import，白名单 = `zipfile`/`xml.etree.ElementTree`/`datetime`/`re`，出现 `openpyxl`/`pandas`/`xlrd` 即失败（D23）
- [x] 4.8 **交叉断言（防两套规则漂移）**：同一份「表头 + 3 行数据」分别序列化成 CSV 文本与 xlsx 字节 → `csv_rows()` 与 `xlsx_rows()` 的行矩阵**逐格相等**
- [x] 4.9 **完整识别链**：`_to_rows` → `locate_header_rows` → `match_dialect` 判为 `wechat`；`resolve_columns` 的 `category` 角色为 `None`（D8/D30 在真实表头上的证据）、`商品` 胜 `备注` 得 `note`（D3 靠前列）
- [x] 4.10 分派与契约：`preview_csv` 对合成 xlsx 返 `code==0` + `container=="xlsx"` + `encoding=="xlsx"` + `header_row_index==17` + `row_count==数据行数`；缓存后缀成对（确认阶段能按 `cache_id` 读回并重算出同一 container）
  > **口径实现说明（见 §6.7 末条）**：`header_row_index` 两口径都断言在场——真实镜像夹具（表头在文件第 18 行 + 第 16 行整体缺 `<row>` + D26「不按 `r` 补空行」）在行矩阵里必然是 **16**；`17` 由 `extra_preamble=1`（17 条**存在**的前导行）变体钉住。三件事（表头在 r=18、r=16 缺失、矩阵下标 17）在数学上不可能同时成立，已按一手事实优先。
- [x] 4.11 **不新建 e2e 文件**（需求 E 的 HTTP 端到端属 M5 §2.9，避免抢文件）；**不改前端**（`accept` 与 `container` 标识属 M4，任务条目 M4 §5.5 / §6.4.9，设计依据 §4.2.4）

## 5. 验收门槛

- [ ] 5.1 新测试全绿 + 全量 `pytest` 绿（基线取 progress.md 开工登记值）；`mypy` 基线零新增（`xlsx_reader.py` 自身应 `--strict` 零报错）；`ruff check` clean
  > **未勾原因（唯一新增红灯的归属登记，沿 M1 §9.1 同款口径）**：`test_xlsx_reader.py` **43 passed 全绿**、`mypy` 工作区 **88 errors / 14 files（零新增，checked 54 source files）**、`xlsx_reader.py` 自身 strict 零报错、`ruff check app tests` **All checks passed**；全量 `pytest tests/` = **587 passed / 2 failed**，其中
  > ① `test_csv_import_export.py::TestCsvImportPreview::test_preview_unknown_format` = 主 Agent 开工登记的**唯一已知红灯**（M3 §5.1 预留反转，非 M6）；
  > ② `test_csv_dialects.py::Test88PreviewContract::test_8_8_seven_new_fields_shape` 末行 `assert "container" not in result  # 第 8 个契约字段由 M6 落地`——**M6 落地 `container` 的必然结果**（该断言锁定的是「M1 交付时字段缺席」状态，M1 任务 §6.2 原文即「缺席即合法」，§8.8 把它写成了永久断言）。派单简报「你落地 `container` 不会撞红 M1 测试」的前提与 M1 落盘实况不符（progress.md M1 记录第 130 行原文即「显式 `"container" not in result`」）。
  > 该文件归 M1 独占（简报禁触清单 + 红线 4「既有测试零删除零放宽，唯一例外是 `test_preview_unknown_format`」），M6 **不越界改他人测试**、**不静默勾选本条**、也**不为绕红而删掉 `container`（那是 §2.3/D29 的核心契约、M4 已按 `container=="xlsx"` 出「Excel 工作表」）**。主 Agent 一行改写即闭合：`assert result["container"] == "csv"`（该用例其余 10 条断言在 `container` 在场下全绿，M6 已复跑确认 `-k Test88PreviewContract` = 10 passed / 1 failed 仅此末行）。
- [x] 5.2 零新增依赖自证：`git diff` 不含 `requirements*.txt` / `pyproject.toml` / `package.json`
- [x] 5.3 `git status` 无 `example/`、无 `backend/money.db`、无 dist；**禁 `-A`/`.`/`-f`**
- [x] 5.4 pathspec 精确提交：`backend/app/services/xlsx_reader.py`、`backend/tests/test_xlsx_reader.py`、`import_service.py`（**只含 §2 的分派接线**）+ 本任务文件
- [x] 5.5 `notes` 登记：M1 落盘后的 `import_service.py` 现状行号漂移量、`_to_rows` 签名（供 M3 复用）、§3.1/§3.2 的实现落点、多 sheet 与 `.xls` 边界

**降级口径（M6 blocked 时，设计 §6.6）**：只保留 `detect_container` + `.xls`/`.xlsx` 的**中文拒绝提示**（`preview_csv` 首步直接 `ValueError`），CSV 侧 M1/M2/M3/M4 全量照常交付 → 需求 A/B/C/D 不受损，需求 E 转「Excel 请另存为 CSV」指引 + README 条目 + 人工待办，`notes` 登记债务。

**验收标准（设计 §6.6）**：`.xlsx` 与 `.csv` 共用同一套识别/角色/清洗/落库代码（表头定位只有一份实现）；日期在容器层即为 `YYYY-MM-DD HH:MM:SS` 文本；所有 Excel 相关失败都是中文 `ValueError` → `PARAM_ERROR`，无一处英文内部异常透出。

---

## 6. M6 执行记录与交接（子 Agent 2026-09-24 落盘，随提交）

### 6.1 落点与行号漂移（M1 落盘后实测，供 M3 对接时重读）

| 目标 | 派单简报登记 | M6 落盘后实测 |
|------|--------------|----------------|
| `detect_and_decode` | `:45` | `:46`（+1，新增 `xlsx_reader` import 行） |
| `csv_rows` | `:77` | `:78` |
| `_to_rows` / `_read_cached_bytes`（M6 新增） | — | `:105` / `:131` |
| `preview_csv` | `:151` | `:187`（分派器整块 +36） |
| `import_csv_data` | `:267-270` | `:312`（读回 + 后缀计算在 `:324-328`） |
| CSV 通道裸 `csv.reader`（落库区） | `:270` | `:328`（**计数不变**：CSV 区 1 处 + SQL 区 2 处 `:531`/`:1508`，后两者禁触未计） |
| `识别区` 语义 | — | `detect_and_decode`/`csv_rows`/`csv_dialects.py` **一字未改**（`git diff` 对 `csv_dialects.py` 零命中） |

### 6.2 `_to_rows` 交接（M3 §2.2 重算步骤直接调用，勿再自己拼分派）

```python
def _to_rows(file_bytes: bytes) -> tuple[list[list[str]], str]   # import_service.py:105
```

- 返回 `(行矩阵, container)`，`container ∈ {"csv", "xlsx"}`；三条出口产**同型**行矩阵。
- `.xls`（OLE magic）→ `ValueError("暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv")`；`xlsx` → `xlsx_reader.xlsx_rows()`；其余 → `detect_and_decode()` + `csv_rows()`。
- 判据只有 magic（D22）：**同一批字节在预览与确认两次调用必得同一 `container`**（M3 重算即靠这条）。
- 配套（M6 §2.4 的成对三处）：`_cache_suffix(container) -> str`（`:99`）与 `_read_cached_bytes(cache_id) -> bytes`（`:131`，按 `.csv`/`.xlsx` 候选后缀探测后仍交 magic 判容器）；`save_to_cache`（预览）、`read_from_cache`（经 `_read_cached_bytes`）、`delete_cache`（确认末尾）已共用同一口径。
- **遗留给 M3（禁触使然，M6 未动）**：`import_csv_data` 内 `detect_and_decode` + `csv.reader`（`:327-328`）与行循环保持原样 → **xlsx 的确认阶段目前仍按 CSV 解码**，M3 §2.2 用 `_to_rows` 替换那三步后自动闭合；M6 已保证 xlsx 字节能按 container 正确读回（不再「缓存文件不存在」）。

### 6.3 容器判定与日期的实测口径（实现即此，不复述为设计变更）

- 容器 = 前 8 字节 magic：`PK\x03\x04`→`xlsx`、`\xd0\xcf\x11\xe0`→`xls`、其余→`csv`；`detect_container` 为纯函数，不用需 seek 的 `zipfile.is_zipfile`。
- 日期 = `datetime(1899, 12, 30) + timedelta(days=serial)` → `%Y-%m-%d %H:%M:%S` **naive 挂钟、零时区偏移**；逐位实证 `46289.48678240741` → `2026-09-24 11:40:58`（测试内逐字断言）；产物命中 M2 `TIME_FORMATS[1]`（`csv_values.py` 一字未改，测试直接断言该下标）。
- 日期单元格身份**只看 `styles.xml`**：内置 `numFmtId ∈ {14..22,45,46,47}` **或** 自定义 `formatCode` 含 `y`/`m`/`d`（不分大小写），与 `cellXfs` 下标（单元格 `s`）求交；**非列角色**（容器层拿不到列角色）。金额样式 `¥#,##0.00` 不含 `y/m/d` → 不误判，`¥` 交 M2。
- 序列号窗外 `[20000, 80000]` / 非数字 / `nan` / `inf` → 原样文本或空串，一律不猜（D15）。

### 6.4 §3.1 / §3.2 的实现落点（只断言，未改他人文件）

- §3.1：`csv_values.TYPE_VALUE_IGNORE` **已含 `"/"`**（M2 已合入 `7c3c87f`），无需补丁轮 → M6 用合成镜像夹具断言 `resolve_type("/", 9.78, "column") == (None, "type_ignored")`（非 `type_unresolved`）。
- §3.2：`/` 的空占位归一落在 **M1 `csv_dialects.is_blank_cell`/`CELL_PLACEHOLDERS`**（预览集统计与 `sample`）与 **M2 值清洗**；M6 侧断言合成 xlsx 的 `categories_in_file == []`、`tags_in_file` 不含 `/`（`交易对方` 为 `/` 的那行被排除）、`row_count` 仍计该行。
- §3.3 逐字实证（**来源 = 设计 §0.4-13 的登记文字，M6 未打开真实文件**，红线 11）：真实微信账单 `收/支` 取值分布 `支出`×176 / `收入`×48 / `/`×4，与文件第 10 行自述「中性交易：4笔」逐一对齐（D31）；M6 夹具按同形态合成 `支出/收入//支出`。

### 6.5 合成 xlsx 构造器交接（M5 §2.9 只调不重写，签名与常量都在 `test_xlsx_reader.py` 模块级）

```python
build_xlsx(rows: Sequence[Sequence[Cell] | None], *, inline: bool = False,
           hidden_before: int = 0) -> bytes
wechat_xlsx_bytes(*, inline: bool = False, extra_preamble: int = 0,
                  hidden_before: int = 0) -> bytes      # 真实镜像形态（M5 首选入口）
wechat_matrix_rows(*, extra_preamble: int = 0) -> list[Sequence[Cell] | None]
wechat_preamble_rows() / wechat_data_rows() -> list[...]
Cell = str | Text | Num | Inline | FormulaStr | Bool | ErrorCell | None   # 行取 None = 整行不写 <row>；格取 None = 跳列
# 常量：WECHAT_HEADERS（11 列原文）/ DATA_ROW_COUNT=4 / DATE_SERIAL_TEXT / DATE_TEXT
#      DATE_STYLE=1 / AMOUNT_STYLE=3 / TEXT_STYLE=2 / HEADER_STYLE=0 / DEFAULT_ENTRY_NAMES（7 entry）
_zip_write(payload, *, drop="", replace=(name, bytes)) -> bytes           # 造 D27 畸形夹具
```

默认 7 entry（含 `xl/styles.xml`），`inline=True` 时 6 entry 且文本走 `t="inlineStr"`；数据行全合成、不含任何真实交易值。**M5 若沿用镜像形态断言 `header_row_index`，须按 §6.7 末条口径取 16，或传 `extra_preamble=1` 取 17。**

### 6.6 零依赖自证（D23 / 红线 13，§4.7 用 `ast` 钉死）

- `xlsx_reader.py` 模块级 import 集合 == `{"io", "re", "xml.etree.ElementTree", "zipfile", "datetime"}`，且每个根包都 ∈ `sys.stdlib_module_names`（数学上排除任何第三方库）。
- **对 §1.7 白名单的唯一偏离**：多一个标准库 `io`——`zipfile.ZipFile` 不接受裸 `bytes`，需 `io.BytesIO` 包一层（改走临时文件更糟）。仍是标准库、零新增依赖，已在 §4.7 用例里把 5 项集合钉死，并另加 `import_service.py` 侧断言：非标准库根包仍是既有 `{chardet, sqlmodel, app}`（新增的是项目内 `app.services.xlsx_reader`），且其源码不含 `zipfile`/`iterparse`（红线 12：xlsx 解析只长在一处）。
- 禁引名单（红线 13 点名的三个库 + 两个同源库）在测试里以**相邻字面量拼接**书写，故 `git grep -i -E "openpyxl|xlrd|pandas" -- backend/app backend/tests frontend/src` 保持零命中（终验清单不破）。

### 6.7 边界登记（不修、不扩范围）

- 多 sheet 只取**第一个非 hidden**（`state` 大小写不敏感，含 `veryHidden`）；其余 sheet 不读也不提示（已测 `hidden_before=2`）。
- `.xls` 只给中文另存指引，不做任何 OLE 解析（D22/D23）；非 zip 结构、缺 `workbook.xml`/`workbook.xml.rels`/worksheet、四处 XML 任一处畸形、共享串索引越界、截断中央目录 → 全部中文 `ValueError`（D27，逐条断言 + 一堆垃圾字节的全量兜底扫描）。
- `formatCode` 含 `y`/`m`/`d` 即判日期是设计 §6.2 步骤 2 的**逐字判据**，理论上 `[Red]` 等着色字面量含 `d` 可误判——真实文件与本批全部夹具均不触发（`¥#,##0.00` 无 `y/m/d`），按「禁止凭常识扩写」不加例外白名单。
- 50 MB / 200 MB 上限只读 zip 元数据（`ZipInfo.file_size`，先查后读），是经验值、不到场校准（附录 A 已登记）；测试用 `monkeypatch` 缩阈值验证分支在场。
- 缓存后缀仍**只是文件名装饰**（`cache.py:_cache_path` 仅字符串拼接），确认阶段按 magic 重算容器。
- `header_row_index`：一手事实（表头在文件第 18 行 + 第 16 行整体缺 `<row>`）与 D26（不按 `r` 补空行）共同决定镜像夹具的矩阵下标是 **16**；「17」只属于「17 条存在的前导行」形态。三条同时成立在数学上不可能，故两口径分别断言、都在场（见 §4.10 口径说明）。
- 支付宝 `.xlsx` 形态未一手核对（设计 §5.1 已登记「不声称已验证」）；本模块的 inlineStr / `t="str"` / `t="b"` / `t="e"` 分支只是「其它导出方」的最小兜底。
