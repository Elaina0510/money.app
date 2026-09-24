# M3 - 后端落库层：统一列角色解析 + 请求契约扩展（需求 A、C、D）

> 对应设计 §三。目标：确认阶段按「角色 → 列索引」解析每一行，接 M1 的识别结果与 M2 的清洗函数，让 Cashew 模板、微信/支付宝账单、手选列的任意 CSV 真正入库；输出可解释的跳过原因；删掉两套异构旧解析。**本模块对容器无感**：`.csv` 与 `.xlsx` 都已被 M6 归一为行矩阵，故 §2.2 的重算步骤**必须复用 M6 的 `_to_rows()`**，不得自行 `detect_and_decode`（否则 xlsx 通道在确认阶段退回二进制乱码）。
> 涉及文件：改 `backend/app/services/import_service.py` 的**落库区**（`import_csv_data` :170-300、`_parse_native_row` :303-311、`_parse_cashew_row` :314-329、`convert_cashew_*` :75-90）、`backend/app/schemas/import_.py`（`ImportCsvRequest` :22-28）、`backend/app/routers/import_.py`（CSV 两端点 :21-70）、`backend/tests/test_csv_import_export.py`；**新增可跟踪夹具** `backend/tests/fixtures/csv/cashew_import_template.csv`（D21）。
> 依赖：**M1 已合入**（同文件 `import_service.py` 串行链 **M1 → M6 → M3**，识别区已被 M1 改写、容器分派器 `_to_rows` 已由 M6 落地）+ **M2 已合入**（清洗函数 import）。开工前**必须重读 M6 落盘后的当前行号与 `_to_rows` 签名**（M6 §2.5 会在 notes 交接）。SQL / Cashew SQLite 路径全程禁触（设计 D17）。

---

## 1. 请求契约（设计 §3.2，D18）

- [x] 1.1 `ImportCsvRequest.format` 的 pattern 扩为 `^(native|cashew|cashew_template|alipay|wechat|custom)$`
- [x] 1.2 新增可选字段：`columns: dict[str, int] | None = None`（角色 → 列索引）、`type_source: str | None = Field(None, pattern="^(column|sign|all_expense|all_income)$")`、`fallback_category: CategoryMappingItem | None = None`
- [x] 1.3 `category_mapping` / `tag_mapping` 由**必填**改为 `= {}` 默认（微信无分类列时前端可只发 `fallback_category`）
- [x] 1.4 `CategoryMappingItem.type`（:11，服务端早已不读）**保留不动、不删**（删除属无消费方清理，越界）
- [x] 1.5 **不新增 Pydantic 校验器抛 422**：必需角色/索引越界等业务校验放 service 层抛 `ValueError`（路由转 `PARAM_ERROR`）——因前端拦截器不读 FastAPI 原生 `detail`（设计 §0.4-8）

## 2. `import_csv_data` 流程改造（设计 §3.3）

- [x] 2.1 签名扩展为接收 `columns`、`type_source`、`fallback_category`（`format_type` 参数保留，语义=方言 key，仅用于展示与 `type_source` 缺省）
- [x] 2.2 **重算识别结果**：`read_from_cache(cache_id, 后缀按容器)` → **`_to_rows(file_bytes)`（M6 的分派器，返回 `(行矩阵, container)`）** → `locate_header_rows(rows)` → `match_dialect` → `resolve_columns`（缓存只存原字节，**不得依赖 M1 预览时的内存结果**，设计 §0.4-9）。**不得**在本模块直接 `detect_and_decode` + `csv.reader`（xlsx 通道会退回乱码）；后缀须与 M6 §2.4 的 `save_to_cache` **成对一致**
- [x] 2.3 **请求 `columns` 为权威位**：带 `columns` 则覆盖推导值；未带则用推导值（`test_import_native_format` / `test_import_cashew_format` 不发 `columns`，走此路，向后兼容）
- [x] 2.4 显式校验：`columns` 的索引越界 → `ValueError("列索引超出范围")`；`REQUIRED_ROLES`（`consume_time`/`amount`）未被覆盖 → `ValueError("缺少必需列：金额/交易时间")`
- [x] 2.5 逐行按角色取单元格（单元格数不足时按空串处理）→ `parse_amount`（M2）→ `resolve_type` → `parse_time` → 分类 → 标签 → 落库；删除旧的 `if not row or all(...)` 之外的重复空行判定
- [x] 2.6 分类落位：`category_mapping.get(cat_name)` 命中则沿用（`create` 走既有 `_resolve_or_create_category`、`map` 取 `target_id`）；`cat_name` 为**空 或 `"/"`**（D31 一手实测占位符；标签列同规则）或 映射落空 → 用 `fallback_category`（同样支持 `create`/`map`）；仍无 → 跳过并计 `category_unresolved`。**禁止建出名为 `/` 的分类或标签**
- [x] 2.7 `amount` 入库 `round_money(abs(value))`（D13），方向仅由 `type` 承载；`type` 取 `resolve_type` 结果，`None` 即跳过并记对应 reason
- [x] 2.8 `consume_time` 取 `parse_time` 结果（D14）；`None` 即跳过并计 `invalid_date`——**替换现状「非空即入库」**（:216-218）
- [x] 2.9 **`skipped_reasons` 返回**（D12）：`{invalid_amount, invalid_date, type_ignored, type_unresolved, category_unresolved}`，五键恒在、缺省 0；`imported_count`/`skipped_count` 字段名与语义不变
- [x] 2.10 **标签 create 分支补查重**（设计 §0.4-6 缺陷闭环）：改为先 `select(Tag).where(name, user_id).first()` 命中即复用，手法对齐 SQL 路径 :750-758；**改动仅限 CSV 分支，SQL 侧一字不动**
- [x] 2.11 收尾不变：`imported_records` 快照 → `create_history_entry("csv_import")` → `commit` → `delete_cache` → `logger.info`（在既有日志行补 `imported/skipped` 之外再打 `skipped_reasons` 摘要，中文不参与、格式自定）
- [x] 2.12 补 `headers is None` 守卫（现状 :182-185 无守卫，M1 后由 §2.2 定位函数统一兜底 → 核验本函数不再裸取 `next(reader)`）

## 3. 删除旧解析（设计 D16，不留转发壳）

- [x] 3.1 删除 `_parse_native_row`（按位置 0..5 取值，是「预览按名、导入按位」错位隐患的根源）
- [x] 3.2 删除 `_parse_cashew_row`（硬编码字面量 key）
- [x] 3.3 删除 `convert_cashew_type` / `convert_cashew_amount` / `convert_cashew_date`（职责由 M2 `resolve_type`/`parse_amount`/`parse_time` 承担；**注意 `convert_cashew_amount` 的 `abs` 口径已迁入 D13，不得丢失**）
- [x] 3.4 全仓 grep 确认四函数与被删常量零残留引用（含 `tests`、`doc` 不进代码）；**不得保留「兼容旧调用」的空壳**
- [x] 3.5 核验 `CASHEW_COLUMN_MAP`/`CASHEW_IGNORED_COLUMNS` 已在 M1 平移进 `csv_dialects` 并从此文件删除；cashew 全量导出（`income` 布尔列 + 负数金额）经新路径解析结果与旧路径**逐位一致**

## 4. 路由（设计 §3.4）

- [x] 4.1 `routers/import_.py` CSV 预览端点：透传 M1 扩展后的 `data`（无新逻辑）
- [x] 4.2 CSV 确认端点：把 `columns`/`type_source`/`fallback_category` 透传给 service；`fallback_category` 需 `.model_dump()`（与既有 `cat_mapping`/`tag_mapping` 同款转换）
- [x] 4.3 把 `skipped_reasons` 放进 `data`；`message` 仍为 `f"成功导入 {result['imported_count']} 条记录"`（**后端文案不改**，U3；「跳过」展示在 M4 前端）
- [x] 4.4 `ValueError→PARAM_ERROR`、`Exception→SERVER_ERROR` 映射与文案零改动；SQL 两端点零改动

## 5. 测试改写与新增（`backend/tests/test_csv_import_export.py`）

- [x] 5.0 **先建可跟踪夹具**（D21，本模块其余用例的前置）：新建 `backend/tests/fixtures/csv/cashew_import_template.csv`，内容 = 本机 `example/cashew-import-template1790219274617.csv` 的**逐字字节副本**（181 B、通用英文表头、无用户数据；改名去掉时间戳，以免被误认为现场文件）。落文件后须实测：`git check-ignore -v` 对该路径**无命中**、`git ls-files` 能列出它。**任何代码与测试都不得引用 `example/` 路径**（该目录被 `.gitignore:68` 忽略、git 未跟踪，新克隆与 CI 读不到）；含用户真实数据的 128 KB Cashew 全量导出**禁止入库**，也不得把其内容抄进夹具（红线 11）
- [x] 5.1 **本批唯一口径反转**：`test_preview_unknown_format`（:164，`col1,col2,col3` 断言 `code != 0`）→ 改为 `code == 0` + `format == "custom"` + `columns` 每项 `role is None` + `headers == ["col1","col2","col3"]`。理由与影响在 `notes` 登记——「未知格式整文件拒绝」正是需求 A 要消除的行为
- [x] 5.2 既有 native/cashew 全 7 确认用例 + 预览/边界用例**断言一字不改**；若出现红灯即为真实缺陷，**禁止反向放宽**（回归护栏，设计 §3.3）
- [x] 5.3 新增 **Cashew 模板全链路**：读 §5.0 夹具 `backend/tests/fixtures/csv/cashew_import_template.csv` 的**原始字节**（不 hardcode 内容、不引用 `example/`）→ preview（`format == "cashew_template"`、`suggested_type_source == "sign"`）→ confirm（`Category` 走 `create`）→ 断言 `-50`→expense、`250`→income、`Fruits and Vegetables` 落 `tag`、日期归一为 `2026-09-24 11:07`
- [x] 5.4 新增 **导出→导入闭环（需求 D 的总验）**：先 `export_csv` 取带 BOM 的真实字节 → preview → confirm → 断言 `imported_count == 导出行数` 且记录字段一致
- [x] 5.5 新增手选列路径：`columns` 指定非默认列序（把 `Amount` 放索引 3、`Date` 放 0）→ 正确入库；`columns` 越界 → `code != 0` 且 message 含「列索引」；缺 `consume_time` 角色 → `code != 0` 且 message 含「必需列」
- [x] 5.6 新增 `fallback_category`：无分类列夹具 + 只发 `fallback_category` → 全部行归入该分类；未发 → `imported == 0` 且 `category_unresolved` 计数正确（不抛异常）
- [x] 5.7 新增 `type_source` 四态：`all_expense` / `all_income` 覆盖符号法（全正数 CSV 被正确判为全收入）；`column` 且列值不可判 → 该行 `type_unresolved`（**不回落到 sign**）
- [x] 5.8 新增 `skipped_reasons` 五键计数（各构造一条脏行，断言逐键非串扰）
- [x] 5.9 新增**标签同名多行只建一行**（§2.10 闭环）：同一文件同 `tag_name` 出现两次 → `tags` 表 1 行、两条记录同 `tag_id`
- [x] 5.10 新增中文账单合成夹具（表头逐字取设计 §0.4-10）：支付宝走 `category` 列自动映射、微信走 `fallback_category`；`不计收支` 行**与一手实测的 `/` 中性交易行**（D31）均计入 `type_ignored`；`¥28.16` 与 `6.90` 均清洗为两位小数
- [x] 5.10b `/` 不再产生分类/标签：夹具的分类列含 `/` 行 → 走 `fallback_category`，`tags` 表**无名为 `/` 的行**（§2.6 闭环）
- [x] 5.11 **不新增前端测试**（属 M4）；**不新建 e2e 文件**（属 M5，避免抢文件）；**不写 xlsx 测试**（容器层与分派归 M6 §4、端到端归 M5 §2.x）

## 6. 验收门槛

- [x] 6.1 `pytest` 全量绿（**基线 298**（2026-09-24 实测）+ 本模块新增；权威值以 progress.md 开工登记为准）；`mypy` 基线零新增；`ruff check` clean
- [x] 6.2 端到端手工核验（`httpx ASGI` 级即可，无需浏览器）：模板夹具（§5.0）+ 导出闭环 + 一份中文合成账单三条链路均能入库并在 `/api/records` 列表可见
- [x] 6.3 `backend/money.db` 全程只读（用例一律 tmp_path 临时库）；核验 `git status` 无 DB/无关文件混入
- [x] 6.4 pathspec 精确提交：`import_service.py`、`schemas/import_.py`、`routers/import_.py`、`test_csv_import_export.py`、**夹具 `backend/tests/fixtures/csv/cashew_import_template.csv`**（§5.0；**不含** `csv_dialects.py`/`csv_values.py`，已由 M1/M2 提交；**不含 `example/`**，且**禁止**对其使用 `git add -f`）
- [x] 6.5 夹具可跟踪性终核：提交后 `git ls-files backend/tests/fixtures/csv/` 列出该文件；`git show --stat HEAD` 确认工作树无 `example/` 混入

**验收标准（设计 §3.6）**：不发消息扩展即可让旧前端继续工作（D18）；四类新来源（模板 / 导出闭环 / 微信 / 支付宝）与手选列路径全部真实入库；`skipped_reasons` 能解释每一条跳过；旧两套解析函数物理消失。
