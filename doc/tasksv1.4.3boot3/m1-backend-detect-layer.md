# M1 - 后端识别层：字节解码 + 表头行定位 + 方言与列角色（需求 A、B、D）

> 对应设计 §一。目标：让**任意** CSV 都能进预览并拿到「每列建议角色」，未知表头不再整文件拒绝（A/D）；内置五方言别名与逐列预设（B）；修掉自家导出 CSV 带 BOM 回导必失败的缺陷（D）。
> 涉及文件：新增 `backend/app/services/csv_dialects.py`、新增 `backend/tests/test_csv_dialects.py`；改 `backend/app/services/import_service.py` 的**识别区**（`detect_and_decode` :36-47、`detect_csv_format` :50-58、`CASHEW_COLUMN_MAP`/`CASHEW_IGNORED_COLUMNS` :61-72、`preview_csv` :93-144）、**新增 `csv_rows(text) -> list[list[str]]`**（`csv.reader` 包一层 + `_csv.Error` 收口成中文 `ValueError`，D27 的 CSV 半边，设计 §1.2.3）。
> 依赖：无。**与 M2 零文件交叉可并行**；`import_service.py` 的**落库区**属 M3，本模块禁触。
> **串行链已因需求 E 扩为 `M1 → M6 → M3`**（设计 §六）：本模块**必须交付「行矩阵」契约**给 M6 复用——`locate_header_rows(rows: Sequence[Sequence[str]], max_scan=50)`（**入参不再是文本**，§4.1），xlsx 与 CSV 共用同一套定位/评分/角色算法（D25，禁止让 M6 另写一份）。

---

## 1. 新文件 `backend/app/services/csv_dialects.py`：常量与数据表

- [x] 1.1 角色常量：`ROLES = ("consume_time", "amount", "type", "category", "tag", "note")`、`REQUIRED_ROLES = ("consume_time", "amount")`（设计 D3；`REQUIRED_ROLES` 的唯一消费方在 M3，本模块只定义并导出）
- [x] 1.2 `COLUMN_ALIASES: dict[str, str]` **逐键抄录下表，禁止实现期自造或扩键**：

  | 角色 | 键（`normalize_header` 之后） |
  |------|------|
  | `amount` | `amount`、`金额` |
  | `consume_time` | `consume_time`、`date`、`交易时间`、`日期`、`时间` |
  | `type` | `type`、`income`、`收/支`、`收支` |
  | `category` | `category_name`、`category`、`交易分类` |
  | `tag` | `tag_name`、`title`、`交易对方` |
  | `note` | `note`、`备注`、`商品`、`商品说明` |

  > **`交易类型` 故意不在表内**（微信该列是资金渠道，不是分类；设计 D9）。`金额(元)` 经归一化落 `金额` 键，**不得重复登记**带单位形态（设计 D4 防死键）。
- [x] 1.3 `@dataclass(frozen=True) class Dialect`：字段 `key / label / required(frozenset[str]) / roles(dict[str,str]) / type_source(str)`
- [x] 1.4 五个方言实例，`roles` 逐列按下表**全量钉死**（`label` 为中文展示名，供前端直接用）：

  | key | label | 判定 `required`（对归一化表头） | `roles`（归一化列名 → 角色） | `type_source` |
  |-----|-------|------|------|------|
  | `native` | 本系统格式 | **集合严格相等** `{amount,type,category_name,tag_name,consume_time,note}`（保持现状语义，设计 D5） | 六列同名：`amount→amount`、`type→type`、`category_name→category`、`tag_name→tag`、`consume_time→consume_time`、`note→note` | `column` |
  | `cashew` | Cashew 全量导出 | ⊇ `{title, category name}` | **由现存 `CASHEW_COLUMN_MAP` 逐条平移**：`title→tag`、`category name→category`、`amount→amount`、`income→type`、`note→note`、`date→consume_time` | `column` |
  | `cashew_template` | Cashew 导入模板 | ⊇ `{date, amount, category, title}` | `date→consume_time`、`amount→amount`、`category→category`、`title→tag`、`note→note`；`account` 无角色 | **`sign`** |
  | `alipay` | 支付宝账单 | ⊇ `{交易时间, 交易分类, 金额, 收/支}` | `交易时间→consume_time`、`交易分类→category`、`金额→amount`、`收/支→type`、`交易对方→tag`、`商品说明→note`；`对方账号/收/付款方式/交易状态/交易订单号/商家订单号/备注` 无角色 | `column` |
  | `wechat` | 微信账单 | ⊇ `{交易时间, 金额, 收/支}` | `交易时间→consume_time`、`金额→amount`（覆盖 `金额(元)` 归一形态）、`收/支→type`、`交易对方→tag`、`商品→note`；`交易类型/支付方式/当前状态/交易单号/商户单号/备注` 无角色 | `column` |

  > 支付宝/微信的 `备注` 列被丢弃是 D9 的显式结果（一角色一列、不拼接；`商品(说明)` 信息量高于常为 `/` 的 `备注`）；用户可在前端手选把 `备注` 改为 note。
  > `CASHEW_IGNORED_COLUMNS`（`subcategory name/account/currency/wallet`）**并入** cashew 的「无角色」事实（其定义删除，设计 D16 死代码激活）。
- [x] 1.5 `DIALECT_ORDER = ("native", "cashew", "cashew_template", "alipay", "wechat")`，并在 docstring 写明 **`alipay` 必须先于 `wechat`**（支付宝必要列集是微信超集，倒序即误判并丢分类列，设计 D5）
- [x] 1.6 类型注解完整（mypy 基线零新增口径）；模块内**不 import** `import_service`、**不 import** DB/ORM（零反向依赖）

## 2. 列名归一化 `normalize_header`（设计 D4）

- [x] 2.1 五步按序实现：剥 `\ufeff` → `unicodedata.normalize("NFKC", h)` → `strip()` 两端空白（含全角空格 `\u3000`、TAB）→ 剥**结尾**括号单位（正则仅锚定末尾，`金额(元)`→`金额`；中间括号不得误伤）→ 折叠内部连续空白为单空格 → `.lower()`
- [x] 2.2 保 `category name` 的单空格（折叠不得吃掉它）；空列名归一为 `""` 且**在别名表与所有 `roles` 中都不落键** → 天然 `role=None`
- [x] 2.3 幂等：`normalize_header(normalize_header(h)) == normalize_header(h)`（全角/半角混合形态下亦成立）

## 3. 解码改造 `detect_and_decode`（设计 D7，需求 D 主体）

- [x] 3.1 签名改为 `detect_and_decode(file_bytes: bytes) -> tuple[str, str]`，返回 `(文本, 编码标签)`
- [x] 3.2 尝试序：`utf-8-sig` → `utf-8` → `chardet.detect` 探测结果 → `gb18030`（`errors="replace"`）兜底。**`gb18030` 替换现有 `gbk`**（GBK 超集，覆盖中文账单生僻字）
- [x] 3.3 返回前统一 `text.lstrip("\ufeff")` 兜一层（防 chardet 报非 sig 编码时 BOM 残留）
- [x] 3.4 **不留旧签名的兼容转发壳**（不留 `detect_and_decode_str` 之类半死封装）；两处调用点 `preview_csv`(:97) 与 `import_csv_data`(:180) 同批更新——`:180` 处仅改解包、不改落库逻辑（落库改造属 M3）
- [x] 3.5 核验：`export_csv` 产出的 BOM 字节流经本函数后首列表头为 `amount`（非 `\ufeffamount`）

## 4. 表头行定位 `locate_header_rows`（设计 D1/D2）

- [x] 4.1 签名 `locate_header_rows(rows: Sequence[Sequence[str]], max_scan: int = 50) -> tuple[int, list[str], list[list[str]]]`，返回 `(表头行下标, 归一化表头, 表头之后的全部数据行)`。**入参是行矩阵而非文本**（D25：CSV 与 xlsx 共用；M6 的 `xlsx_rows()` 也喂同一函数）
- [x] 4.2 **新增 `csv_rows(text: str) -> list[list[str]]`**（在 `import_service.py`）：`csv.reader(io.StringIO(text))` 逐行读并物化为行矩阵；**捕获 `_csv.Error` → `raise ValueError("CSV 文件内容为空或格式不正确")`**（D27 的 CSV 半边；现状实测：非 CSV 二进制会让 `csv.reader` 抛英文 `new-line character seen in unquoted field` 并经 `SERVER_ERROR` 透出，设计 §0.4-14）。**禁止任何 `skiprows=固定值`**——前导行数必然漂移：真实微信 **xlsx 实测 17 行**、调研微信 CSV 16 行、支付宝 24 行（§0.4-10/13）
- [x] 4.3 评分 = 该行「`normalize_header` 后命中 `COLUMN_ALIASES` 的**非空**单元格数」；取最高分行，**同分取靠前行**；只扫前 `max_scan` 行
- [x] 4.4 全部行评分为 0 时退化为「第一个非空单元格数 ≥ 2 的行」作表头（全手动场景）
- [x] 4.5 无表头/仅空行 → `raise ValueError("CSV 文件为空")`（既有文案不改，设计 U3）
- [x] 4.6 数据行 = 表头行之后的全部行（含空行，由下游既有「全空行跳过」逻辑消化）；前导行**整体丢弃、不计入 `row_count`**

## 5. 方言匹配与列角色 `match_dialect` / `detect_csv_format` / `resolve_columns`

- [x] 5.1 `match_dialect(headers) -> Dialect | None`：按 `DIALECT_ORDER` 取第一个满足 `required` 者；`native` 用**严格集合相等**、其余用**超集包含**（与现状 :53-57 判定强度一致）
- [x] 5.2 `detect_csv_format(headers) -> str`：**保留函数名**，返回值改为「方言 key 或 `custom`」；未命中**不抛异常、不返回 `unknown`**（需求 A/D 的核心落点）
- [x] 5.3 `resolve_columns(headers, dialect) -> list[ColumnHint]`：`ColumnHint` 含 `index / header(原样，仅两端去空白) / role / sample`；有方言取 `dialect.roles`、无方言取 `COLUMN_ALIASES`
- [x] 5.4 同角色冲突按 D3 处置：靠前列得角色、后者置 `None`；`sample` 取该列**第一个非空**数据值（无则 `""`）
- [x] 5.5 未使用参数与守卫：`resolve_columns` 内 `headers` 为空即 `ValueError("CSV 文件为空")`；不改 `preview_csv(db, ...)` 的 `db` 形参（现状未使用，登记 `notes`，无消费方不做清理）
- [x] 5.6 **`/` 按空占位处理**（D31，一手实测：真实微信账单的 `备注`、`商户单号` 大量为 `/`）：`resolve_columns` 的 `sample` 与 `preview_csv` 的 `categories_in_file` / `tags_in_file` 统计一律把 `"/"`（`strip()` 后全等）**视作空串**跳过 → 不产生「`/` 分类」「`/` 标签」。（收支列的 `/` 判为中性交易由 M2 `TYPE_VALUE_IGNORE` 负责，本模块不判值语义）

## 6. `preview_csv` 响应扩展（设计 §1.2.5，M4 契约冻结依据）

- [x] 6.1 保留既有 5 字段：`format`（值改为六枚举之一）、`row_count`、`categories_in_file`、`tags_in_file`、`cache_id`
- [x] 6.2 新增 7 字段：`headers`、`header_row_index`、`columns`、`suggested_type_source`、`encoding`、`sample_rows`、`warnings`（字段名逐字，前端 M4 依此断言）。**第 8 个契约字段 `container` 由 M6 落地**（§1.2.5/D29）——M1 交付时该字段**缺席即合法**，前端按「不存在则不显示」容错；**M1 不得预留空值或假值**
- [x] 6.3 `row_count` 口径改为「表头行之后的非空行数」；`categories_in_file`/`tags_in_file` 改为**按 role 定位列**取值（native/cashew 下结果与现状**逐位一致**，不得因改造而变序或变集）
- [x] 6.4 `warnings` 只生成 3 类：`header_row_index > 0` → 前导行丢弃；无 `category` 角色列 → 需指定默认分类；`REQUIRED_ROLES` 未全覆盖 → 缺必需列（文案中文，不含内部术语）
- [x] 6.5 `sample_rows` 取表头后前 5 行原始单元格；`encoding` 取 §3 返回的标签
- [x] 6.6 缓存写入不变（`save_to_cache(file_bytes, ".csv")`），确认阶段仍靠 `cache_id` 读回原字节（**不新增缓存字段、不在内存存定位结果**）。**注**：该后缀实参由 M6 按容器参数化（m6 §2.4），故 M1 **不得在任何测试里断言 `".csv"` 字面量**，否则 M6 必撞红

## 7. 边界与异常（设计 §1.3 逐条落地）

- [x] 7.1 重复列名（两列 `金额`）→ 靠前列得角色 + `warnings`
- [x] 7.2 支付宝表头**末尾多一个逗号**（第 13 个空列）→ 该列 `role=None`、`headers` 保留空串、不计入任何集
- [x] 7.3 全角 `金额（元）` / `ＤＡＴＥ` 型列名 → NFKC 后正常命中
- [x] 7.4 真实微信前导形态（一手实测 §0.4-13）：`注：` + **4 条编号注释** + `----微信支付账单明细列表----` 单格分隔线 + 单格汇总行（`共228笔记录`、`收入：48笔 …`）→ 全部**评分 0 且不合格化退化**（双判据均排除，「非空单元格 ≥2」不满足），表头落在其后那个 11 列行
- [x] 7.5 仅表头无数据行 → 正常返回、`row_count == 0`，不抛异常
- [x] 7.6 `1,2,3` / `col1,col2,col3` 型无表头文件 → 退化取表头、`format == "custom"`、全列 `role=None`
- [x] 7.7 GB18030 字节流（中文表头）→ 解码后命中 `alipay`/`wechat`

## 8. 测试（新文件 `backend/tests/test_csv_dialects.py`，纯函数级、零 DB）

- [x] 8.1 **BOM 闭环（需求 D 的钉子）**：直接调 `export_service.export_csv` 产出真实 BOM 字节 → `detect_and_decode` → `detect_csv_format` 判为 `native`（若成本过高，退化为「手写 `b"\xef\xbb\xbfamount,type,..."` 断言判 `native`」+ 在 `notes` 登记；**不得**用手写无 BOM 串代替，那等于没测）
- [x] 8.2 `normalize_header` 逐形态：BOM、全角数字/括号、TAB 与全角空格两端、`金额(元)`→`金额`、中间括号不误伤、`category name` 空格保留、幂等
- [x] 8.3 `locate_header_rows`（**入参是行矩阵**，§4.1）：微信 **16 行与 17 行两形态**前导夹具（一手实测漂移，§0.4-10/13）、支付宝 24 行前导夹具、**再插 2 行说明仍命中正确表头**、退化分支（全 0 分）、空行/仅空行入参
- [x] 8.3b `csv_rows`（D27 CSV 半边）：正常多行文本 → 行矩阵逐位一致；**含裸换行/畸形引号的内容不得抛出英文 `_csv.Error`**，必须转成 `ValueError("CSV 文件内容为空或格式不正确")`（用现状实测的那类字节作反例）
- [x] 8.4 `detect_csv_format`：五方言逐一击中 + `custom`；**D5 顺序陷阱显式断言**——支付宝表头必须判 `alipay`，并断言「若 `wechat` 排在前面则结果为 `wechat` 且丢 `category` 列」（用测试内局部乱序表实现，不改生产常量）
- [x] 8.5 native 严格集合相等不破：少一列 / 多一列 / 改名列 → 不再判 `native`（且改为 `custom`，**不再是拒绝**）
- [x] 8.6 `resolve_columns`：微信 11 列、支付宝 13 列（含空尾列）**全列角色逐位断言**，含丢弃列断言 `role is None`；同角色冲突取靠前列
- [x] 8.7 GB18030 中文表头字节流解码命中；`encoding` 标签正确
- [x] 8.8 `preview_csv` 契约：既有 5 字段在新分类目下**逐位回归**（native/cashew 各一组，断言 `row_count`/`categories_in_file`/`tags_in_file` 与改造前一致）+ 新 7 字段形状与 `warnings` 三类文案

## 9. 验收门槛

- [ ] 9.1 新测试文件全绿 + `test_csv_import_export.py` 既有用例**零改动零删除**全绿（本模块不得碰该文件；`test_preview_unknown_format` 的反转属 **M3 §5.1**，若因本模块提前变红，**必须回退本模块改动而非改测试**）
  > **M1 红灯归属登记（未勾原因）**：`test_csv_dialects.py` 87 passed 全绿；`test_csv_import_export.py` 17 passed / **1 failed**，唯一红灯 = `TestCsvImportPreview::test_preview_unknown_format`（`col1,col2,col3` 断言 `code != 0`）。该用例的失败**不是缺陷**，而是需求 A 的落地证据：本模块 §7.6 与设计 §1.3 明确要求该输入「退化取表头 → `format == custom` → 全列 `role=None`」并照常返回预览，M1 验收标准亦为「任意 CSV 都能进预览」。断言反转**唯一授权落点是 M3 §5.1**（设计附录 B、红线 4 的唯一例外），且 M3 §5.1 的新断言（`code == 0` + `format == custom` + `headers == ["col1","col2","col3"]`）需要 M1 这套服务侧行为已就位——**M1 无法同时满足本条与本模块 §7.6/§8.4/验收标准**，故选择保留设计口径、不静默勾选、不越界改他人测试文件。
- [ ] 9.2 `pytest` 全量绿；`mypy backend/app --strict` 基线零新增（新增两文件自身应零报错）；`ruff check` clean
  > **M1 门槛实测**：`mypy app` = **88 errors / 14 files**（开工登记基线 89 → 零新增且 -1，因 chardet 标签已收型；`csv_dialects.py` 自身 strict **零报错**）；`ruff check app tests` = **All checks passed**；`pytest tests/` = **545 passed / 1 failed**（唯一红灯归属同上条），0 skipped。
- [x] 9.3 `notes` 登记：`preview_csv` 的 `db` 形参未使用、GB18030 replace 生僻字不抛、逐行 flush 性能不在本模块处理；**并显式写明「`locate_header_rows` 已改为行矩阵入参 + `csv_rows()` 已交付」给 M6 复用**（D25 的契约交接，M6 据此不得另写表头逻辑）
- [x] 9.4 pathspec 精确提交（禁 `-A`/`.`）：`backend/app/services/csv_dialects.py`、`backend/app/services/import_service.py`、`backend/tests/test_csv_dialects.py`

**验收标准（设计 §1.4）**：任意 CSV（含未知表头、含前导说明的中文账单、含 BOM 的自家导出）都能进预览并拿到逐列角色建议；五方言自动命中且预设映射逐位正确；解码不再被 BOM/GBK 卡住；`export → import` 闭环在识别层成立。
