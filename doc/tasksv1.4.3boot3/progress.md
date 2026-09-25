# Money App v1.4.3-boot3 总体进度

> 唯一进度载体。仅主 Agent 读写。基线：v1.4.3-boot2（HEAD `7ae57da`；2026-09-24 实测 `origin/main` == HEAD，**已推送**）。
> 本批由**单条用户反馈**发起（「导入一份 CSV 文件提示无法识别」），经**三轮**澄清扩为**五条子需求 A/B/C/D/E**——第三轮因用户提供**真实微信账单且其为 `.xlsx`**（`example/`，含真实数据、禁止入库）而新增需求 E = Excel 直读（设计 §六）。权威设计：`doc/detailed-designv1.4.3boot3.md`。
> **零新增依赖（xlsx 只用标准库 `zipfile` + `xml.etree`；实测 venv 无 openpyxl/pandas/xlrd）、零 DB 变更、零迁移脚本。**

---

## 模块清单（6 个，划分轴心 = 层次 + 文件独占；与需求非一对一，映射见括注）

| 模块 | 名称 | 需求 | 任务文件 | 状态 | 提交 |
|------|------|------|----------|------|------|
| M1 | 后端识别层：解码 + 表头定位（**交付行矩阵契约**）+ 方言与列角色 | A、B、D | `m1-backend-detect-layer.md` | **done** | `449ff6e` |
| M2 | 后端清洗层：金额/日期/收支三态纯函数 | C | `m2-csv-value-normalization.md` | **done** | `7c3c87f` |
| **M6** | 后端 **Excel(.xlsx) 容器层**：magic 判定 + stdlib 读表 → 行矩阵（日期序列号在容器层换算为文本） | **E** | `m6-xlsx-container.md` | **done** | `1db6e54` + `d93c736` + 断言修正 `2107429`（见执行记录） |
| M3 | 后端落库层：统一列角色解析 + 契约扩展 | A、C、D | `m3-backend-import-writer.md` | **done** | `a46b0f2` |
| M4 | 前端列映射向导（+ `accept` 扩 `.xlsx` 与 Excel 标识） | A、**E** | `m4-frontend-column-mapping.md` | **done** | `158726c`（归属注记见执行记录） |
| M5 | 端到端真实样例回归 + 文档收口 | 全部总验 | `m5-e2e-and-docs.md` | pending | — |

## 开发顺序（设计附录 A）

1. **M1 ∥ M2 ∥ M4** 三线并行（M1/M2 文件零交叉；M4 靠设计 §1.2.5 + §3.2 冻结契约用 mock 驱动）
2. **M6** 串在 M1 之后（同文件 `import_service.py`；复用 M1 的 `csv_rows`/行矩阵契约，M2 已在位）
3. **M3** 串在 M6 之后（同文件链尾 = **M1 → M6 → M3**；确认阶段必须复用 M6 的 `_to_rows`）
4. **M5** 收尾（依赖 M1–M4 + M6 全部合入）
5. 主 Agent 终验（六命令 + 浏览器实测 + dist 重建 + README）

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `backend/app/services/import_service.py` | **M1（识别区）→ M6（容器分派）→ M3（落库区）** | 区域无交叉但**同文件必须按此序串行提交**；每段开工前重读上段落盘后的行号（M6 §2.5 在 notes 交接 `_to_rows` 签名） |
| `backend/app/services/csv_dialects.py`（新增） | M1 | 独占 |
| `backend/app/services/csv_values.py`（新增） | M2 | 独占 |
| `backend/app/services/xlsx_reader.py` + `backend/tests/test_xlsx_reader.py`（均新增） | **M6** | 独占（含合成 xlsx 构造器；M5 只调构造器不重写） |
| `backend/tests/test_csv_import_export.py` | M3 | M5 **不编辑**（e2e 另立新文件） |
| `backend/tests/fixtures/csv/cashew_import_template.csv`（新增） | **M3 独占创建**（§5.0） | M5 只读复用，**不重复落文件、不改内容**（D21） |
| `example/`（本机真实样例 4 个：模板 CSV、Cashew CSV/SQL 全量导出、**真实微信 `.xlsx`**） | — | git **未跟踪**（命中 `.gitignore:68`）→ 任何代码/测试**不得引用其路径**，也不得删除或 `git add -f`；**除 181 B 模板外的 3 个含真实数据 → 连单元格值都不得抄进夹具/测试/文档**；仅主 Agent 本机人工核验只读（D21 / 红线 11） |
| `backend/tests/test_csv_import_boot3_e2e.py`（新增） | M5 | 独占 |
| `frontend/src/components/common/CsvMappingDialog.vue`、`SettingsImportExportPage.vue`、`SettingsSubPages.test.js` | M4 | 独占；组件/文件**不得重命名**（M5-6 源码断言）；`SettingsImportExportPage.vue` 含 **`accept=".csv,.xlsx"`（:68，需求 E 的前端唯一 DOM 改动，M4 §5.5）** |
| `README.md` | M5 | 独占 |
| `backend/money.db` | — | **全程只读**，本批无任何写入理由 |

## 已确认设计决策（实现约束，设计 §0.3）

**用户裁定**：U1 通用列名别名 + 手动映射（否掉「只加模板方言」的最小方案）｜U2 **内置常见中文账单别名**（第二轮范围复核改判，第一轮「中文暂不需要」作废并登记）｜U3 报错文案不单独立项｜U4 收支缺列按符号法 + 弹窗可改默认｜U5 先出文档套件｜**U6（第三轮）真实微信账单是 `.xlsx` → 本批扩围直接支持 Excel 读取**（否决「只加中文提示 + 让用户另存为 CSV」的最小方案；仍守零新增依赖）。

**设计裁定 D1–D31 摘要**（逐条以设计 §0.3 为准，此处仅索引）：

- **D1/D2** 表头行按内容定位（扫前 50 行，别名命中数评分、同分取靠前，全 0 分退化为「首个非空单元格 ≥2 的行」）——**禁止 skiprows 写死**（微信调研 CSV 16 行、**一手真实 xlsx 实测 17 行**、支付宝 24 行，必然漂移）
- **D3** 六角色、一角色一列、冲突取靠前列；**D4** 列名归一五步（BOM→NFKC→strip→剥结尾括号→折叠空格→lower）
- **D5** 方言序 `native, cashew, cashew_template, alipay, wechat`——**alipay 必须先于 wechat**（超集关系）
- **D6** 只内置 5 方言；随手记/京东/银行查证不到 → **不内置**，走 custom 手选
- **D7** 解码 `utf-8-sig → utf-8 → chardet → gb18030`（替换 gbk）+ `lstrip("\ufeff")` = 需求 D 主体
- **D8/D9** 微信无分类列 → `fallback_category` **必选、不猜**；中文账单逐列角色预设（`交易对方→tag`、`商品→note`、`交易类型` 丢弃）
- **D10/D11** `type_source` 四态（column/sign/all_expense/all_income），0 归支出；`不计收支/中性交易` **与一手实测的 `/`** → 跳过并计 `type_ignored`；**列值不可判不回落到 sign**
- **D12** `skipped_reasons` 五键恒在；**D13** 金额剥 `¥￥$元`+千分位+括号负数，入库 `abs()`；**D14** 日期归一唯一目标 `YYYY-MM-DD HH:MM`（禁止按 `.` 截断）
- **D15** 歧义日期（`09/24/2026`/`24/09/2026`）与 CSV 侧 Unix 时间戳**都不猜**
- **D16** 删除 `_parse_native_row`/`_parse_cashew_row`/`convert_cashew_*`/两个 `CASHEW_*` 常量（后者激活进 dialects），**不留转发壳**
- **D17** SQL / Cashew SQLite 路径零改动；**D18** 新字段全可选，旧前端不发也能跑
- **D19** 零新增依赖、零 DB 变更；**D20** 不做重复导入去重（登记关注）
- **D21** 测试夹具必须**可跟踪**：`example/` 命中 `.gitignore:68`（实测 `git ls-files example/` 零命中）→ **任何代码与测试都不得引用其路径**；M3 §5.0 新建 `backend/tests/fixtures/csv/cashew_import_template.csv`（真实模板逐字副本，181 B / 3 行通用英文示例、无用户数据；实测该目录 `git check-ignore` **无命中** → 可正常 `git add`，禁 `-f`）；**含用户真实数据的 128 KB Cashew 全量导出禁止入库、也不得抄进夹具**，其形态改由「17 列表头原文 + 合成行」覆盖
- **D22–D31（需求 E = Excel 直读，设计 §六）**：**D22** 容器判定只看 **magic bytes**（`PK\x03\x04`=xlsx / `\xd0\xcf\x11\xe0`=老 .xls 明确中文拒绝 / 其余=CSV），**不信扩展名与缓存后缀**；**D23** 零依赖 = `zipfile` + `ET.iterparse`（实测 venv 无 openpyxl）；**D24** 日期序列号 `datetime(1899,12,30)+timedelta(days=serial)` → **naive 挂钟、零时区偏移**（账单自述 UTC+08），只在容器层、产物为文本 → M2 白名单零改；**D25** xlsx 归一为**行矩阵**后**复用 M1 全套**定位/匹配/角色（**禁止另写一份表头逻辑**）；**D26** 稀疏行列按列字母 26 进制补位、行按出现顺序；**D27** zip 上限 50/200 MB + 全部 `ValueError` 中文文案，**禁止 `_csv.Error`/`BadZipFile` 裸冒到 `SERVER_ERROR`**；**D28** `preview_csv`/`detect_and_decode` 等**一律保名**，新代码只进 `xlsx_reader.py`；**D29** 前端只改 `accept=".csv,.xlsx"` 与一行 `container` caption；**D30** **不新增方言 key/角色**（真实微信 11 列表头与调研 CSV 逐字一致，`category` 无 → D8 成立）；**D31** `TYPE_VALUE_IGNORE` 补 `/` 且 `/` 视为空占位

## 全局红线（各模块共同遵守）

> **编号与 `doc/promptv1.4.3boot3.md` §2.1 逐条同序**（该节是权威全表，本节仅摘要）；文档中所有「红线 N」引用一律按此编号解析。

1. `backend/money.db` 全程只读；开工/终验 SHA256 双对照；禁 `git add -f`
2. **SQL / Cashew SQLite 导入路径零改动**（D17）：`preview_sql`/`import_sql_data`/`_import_*`/`detect_sql_format`/`detect_cashew_sqlite`/dormant 往返（热修 `da2d011`）一字不动；`detect_and_decode` 改签名只影响 CSV 两处调用点
3. **`import_service.py` 必须 M1 → M6 → M3 串行提交**：M1 不提前改落库区；M6 只加分派器与两处入口（不改 M1 识别区语义、不碰 M3 落库区）；M3 不回退 M1/M6 已落地实现（复用现状）
4. **既有测试零删除、零放宽**——唯一例外：`test_preview_unknown_format` 的口径反转（M3 §5.1，设计附录 B 点名）
5. 不新增端点、不改 HTTP 状态码与既有错误文案（U3）；`CSV 文件为空` 措辞保留。**已裁定例外**：需求 E 的 Excel/二进制失败**必须新增中文文案**（D27——那些路径过去只有英文内部异常，属「从无到有」而非替换）
6. `format` 六值枚举与 `ROLES` 六角色为**封闭集**（D3/D18）：别名表与方言 roles **逐键抄任务文件**，不得凭印象扩键
7. **不内置随手记 / 京东金融 / 银行流水别名**（D6）：走 `custom` + 手动列角色
8. 不做去重（D20）、不做歧义序（D15）、不做 CSV 侧 Unix 时间戳、不改大文件逐行 flush
9. **零新增依赖**（前后端）；前端不引 `v-stepper`/新 Vuetify 组件；不删 `CategoryMappingItem.type` 空转字段
10. `frontend/dist` 不随模块提交、终验统一重建单独提交；README 只改 Version History；`screenshots/` 不提交
11. **禁止在代码/测试中引用 `example/` 路径**（D21）：该目录 git 未跟踪；夹具用 `backend/tests/fixtures/csv/` 或测试内合成常量，**xlsx 用 M6 §4.1/§4.2 的「结构镜像 + 数据全合成」构造器**；**含用户真实数据的文件（Cashew 全量导出、真实微信 `.xlsx`）禁止入库、也不得把其值抄进夹具/测试/文档**
12. 组件/函数**不重命名**（D28：`CsvMappingDialog.vue`、`handleCsvFileSelect`、`preview_csv`、`import_csv_data`、`detect_csv_format`、`detect_and_decode`、新增 `csv_rows` 全部保名；M5-6 的 `?raw` 字面量断言锁定；xlsx 新代码只进 `xlsx_reader.py`）
13. **Excel 边界（需求 E）**：容器判定只看 magic（不信扩展名/缓存后缀，D22）；只用标准库 `zipfile`+`xml.etree`，**禁引 openpyxl/pandas/xlrd**（D23，M6 §4.7 用 `ast` 钉）；日期序列号 **naive 挂钟零时区偏移**、超窗不猜（D24/D15）；多 sheet 只取第一个非 hidden（不猜用户要哪张）；**所有失败必须是中文 `ValueError` → `PARAM_ERROR`**，禁止 `_csv.Error`/`BadZipFile` 裸冒到 `SERVER_ERROR`（D27）；表头定位**只有一份实现**（M1 的行矩阵，M6/M3 复用，D25）

## 编排约定（仅主 Agent，不占用红线编号）

- **E1** 主 Agent 不亲自写业务代码；子 Agent 不 push、不建分支、不 `git add -A`
- **E2** 派单简报必须显式列出并发在途的禁触清单（对向泳道全部文件 + 他模块任务文件 + 本 progress.md + `backend/money.db` + `example/`）
- **E3** 并行红灯归属：全量测试若唯一红灯出自对向泳道在途文件，`notes` 登记归属 + 复跑确认非本模块引入即可提交

## 发布备忘（设计附录 A）

- **零迁移脚本、零 schema 变更、零新增依赖（含 Excel 走标准库）** → 发布窗口只需部署新后端 + 新 `frontend/dist`（终验重建 `8000489`，gzip 538,234 B，**+2,307 B** vs boot2 基准 +127 B 同口径，可接受性留人工裁定），不需停库/备份演练
- 冒烟四条**已在 P4 以 tmp 副本库全部实测通过**（① 导出 231 行→复导 231 条；② 模板 `-50`→支出、`250`→收入；③ 中文表头手选列入库；④ `.xlsx` 直传出预览 `container=xlsx`、`.xls` 得中文另存提示）——发布现场仍可照四条在真实环境复跑一遍作部署验证
- 回退：换回旧后端 + 旧 dist，零数据残留（本批未写任何 schema）
- **P4 新发现（既有行为，非本批引入，登记待后续批次）**：`export_csv` 的分类查找表只含用户自有分类，**全局预设（user_id NULL，如「餐饮」id=1）参与 join 时导出 `category_name` 落空** → 自家导出件回导时这类行全落 `category_unresolved`（P4 实测 227/229）。本批导入侧已用 `fallback_category` 兜住闭环；**导出侧修复超出 D17/红线范围，本批一字未动导出器**，登记为后续热修候选。
- boot2 现场库状态沿用上方 2026-09-24 只读实测登记（已具 v1.4.3 + dormant 形制、分类已归并，余 52 条 `tags` 孤儿沿 boot2 条目跟踪，成因不追查）；本批开工/终验 `money.db` SHA256 双对照逐字一致

## 终验清单（质量门，设计附录 A）

- [x] `pytest tests/ -q` 全绿、`0 skipped` 复核（**632 passed**，开工基线 298 + 本批新增 334）
- [x] `npx vitest run` 全绿（**408 = 基线 397 + M4 新增 11**）
- [x] mypy = **85 errors / 14 files** ≤ 开工登记基线 89 → 零新增（且 -4）
- [x] `ruff check` All checks passed；eslint 0 errors / 2 warnings（基线同值）
- [x] `vite build` + dist 重建单独提交 `8000489`；gzip 538,234 B = **+2,307 B** vs 开工基准（boot2 +127 B 口径，可接受性留人工）
- [x] `backend/money.db` SHA256 与开工登记逐字一致（终验收档复测）
- [x] **夹具可跟踪性（D21）**：`git ls-files backend/tests/fixtures/csv/` 命中；`git grep -n "example/" -- backend frontend` 零命中；`git diff --stat 7ae57da..HEAD` 不含 `example/`
- [x] **Excel 零依赖（D23/红线 13）**：`openpyxl|xlrd|pandas` 零命中；M6 §4.7 `ast` 白名单用例在场且通过
- [x] **无英文内部异常透出（D27）**：M5 §2.9.4 反向护栏通过（九载荷零 `new-line character`/`_csv.Error`/`BadZipFile`/`UnicodeDecodeError`）+ P4 `.xls` 中文实测
- [x] 浏览器实测（主 Agent P4）：四条冒烟全部实测通过（tmp 副本库 + 真实微信 `.xlsx` 本机对照）——**唯截图/指针手感因内嵌浏览器无 surface 留人工**（详见终验记录 P4 段与人工清单）
- [x] README Version History 条目（随 M5 `1256f44`）

> **基线数字口径**：上列三项为 2026-09-24 文档产出时点（HEAD `7ae57da`）的一次性实测，**开工时须以当时 HEAD 复测并写入「开工登记」**，终验以开工登记值为准做零新增比对，不得沿用本表数字。

## 进度统计

| 项 | 数值 |
|----|------|
| 模块 done | **6 / 6**（M1–M6 全部核验通过）；终验六命令全绿：pytest 632 / vitest 408 / mypy 85≤89 / ruff / eslint / build |
| checklist 勾选 | 220（M1 52 + M2 22 + M3 44 + M4 41 + M5 32 + M6 32，主 Agent 补勾已注记）；未勾仅剩 M4 §7.3 人工观感 1 条 + M5 §4.x/§5.2（全部并入终验记录闭合） |
| 待人工抽检 | M4 抄录 5 条（观感截图 / 浏览器整链 / 微信 .xlsx 对照 / 支付宝账单 / .xls 中文透出），与上方既有条目部分同源 |
| 阻塞 | 0 |

## 模块执行记录

### M1（done，`449ff6e`，主 Agent 2026-09-24 核验通过）
- 提交 pathspec 精确（4 文件：`csv_dialects.py` 新建 + `test_csv_dialects.py` 新建 + `import_service.py` 识别区 143+/54- + 任务文件）；`money.db` SHA256 逐字未变；SQL/落库区零改动（`git diff` 该区零命中）
- 主 Agent 复跑：全量 pytest **545 passed / 1 failed / 0 skipped**（唯一红灯 = `test_preview_unknown_format`，E3 归属 = M1 §7.6 合法扩展 unknown→custom，反转授权归 M3 §5.1，**非缺陷**）；`test_csv_dialects.py` 89 passed；mypy 工作区 **88 errors/14 files**（≤ 开工基线 89 且 -1，零新增；`csv_dialects.py` 自身 strict 零报错）；ruff **All checks passed**（M2 期间登记的 3 项 UP012 已由 M1 清零）
- 行矩阵契约**四函数唯一定义在 `csv_dialects.py`**（D25 grep 实证：`normalize_header`/`locate_header_rows`/`match_dialect`/`resolve_columns` 单命中）；`preview_csv` 入口已走 `csv_rows`；**CSV 通道残留裸 `csv.reader` = `import_csv_data` 内 :270（M1 仅按 §3.4 适配解包；行矩阵化归 M6 分派器 + M3 落库改造，终验闭环点 9-① 按此追踪）**；:473/:1450 属 SQL 区禁触不计
- **§9.1/§9.2 未勾 = 唯一红灯未清属预期**（子 Agent 不越界改 M3 测试），原因已在任务文件内引用块登记，符合简报「既有测试不得反向放宽」纪律；主 Agent 认可，M3 §5.1 反转后自动转绿
- **交 M6 的行矩阵契约**（M6 §2.5 据此对接，**禁止另写表头逻辑**）：`csv_rows(text)->list[list[str]]`（csv.Error→中文 ValueError）、`detect_and_decode(bytes)->(text,encoding)`（utf-8-sig→utf-8→chardet→gb18030-replace + `lstrip("\ufeff")`）、`locate_header_rows(rows, max_scan=50)->(header_idx, normalized_headers, data_rows)`（入参行矩阵，不等长/空行/空串均可直喂；空/无合格行→`ValueError("CSV 文件为空")`，xlsx 侧对应文案 `Excel 文件为空`）
- 主 Agent 复核认可的子模块内偏离（记档不判违规）：(b) 删 `CASHEW_COLUMN_MAP`/`CASHEW_IGNORED_COLUMNS` 两死常量（按任务 1.4/D16/M3 §3.5 优先于简报，全仓零引用实证；`_parse_native_row`/`_parse_cashew_row`/`convert_cashew_*` **一字未删**，D16 落库半区仍归 M3）；(c) warnings 第 4 类「多列同角色冲突」追加在 §6.4 三类之后（不违背三类逐字，主 Agent 认可保留）；(d) `resolve_columns` 可选 `data_rows` 参 + `ColumnHint.conflict` 不进响应契约（columns 项仍恰好 4 键）；(e) `match_dialect` 可选 `order` 参供 §8.4 D5 陷阱取证；(f) normalize 步骤 4 收紧为只剥括号单位白名单以保幂等；(g) encoding 标签不谎报（无 BOM 报 utf-8）
- **契约实现核对（对 M4 P3）**：§1.2.5 **7 字段**（headers/header_row_index/columns/suggested_type_source/encoding/sample_rows/warnings）逐字落地、既有 5 字段保留；**`container` 字段 M1 未预留**（显式 `"container" not in result`，属 M6）；`无法识别的 CSV 格式` 消失、`CSV 文件为空` 保留
- **⚠ 勘误（M5 须改，不判 M1 偏离）**：M1 notes(i) 发现设计 §0.4-10 **未逐字登记 Cashew 全量 17 列表头原文**（D21 声称已登记，实为 §0.4-13 只登记 xlsx 11 列结构）→ M1 改用「6 角色列 + 4 丢弃列 = 10 列」合成夹具。M5 §2 建真实 17 列 e2e 时**若无法从设计一手取得 17 列原文，沿用 M1 的 10 列合成并注明「17 列原文未一手登记」**，不得凭记忆编列名（D6 精神）、不得引用 `example/` 真实文件抄值
### M2（done，`7c3c87f`，主 Agent 2026-09-24 核验通过）
- 提交 pathspec 精确（3 文件，`import_service.py` 零命中 = 「未接线」自证成立）；任务文件 22/22 勾选
- 主 Agent 复跑：`test_csv_values.py` **159 passed**；mypy 工作区 88 errors/14 files（≤ 基线 89，零新增；其中 M1 在途贡献待 M1 复测）；ruff 工作区 3 项 UP012 **全部位于 M1 在途 `test_csv_dialects.py`**（E3 归属 M1，M1 提交前须清零）
- 子 Agent 全量复跑 2 次：456/457，唯一红灯 `test_preview_unknown_format` 归属 M1 在途语义扩展（unknown→custom），其口径反转按附录 B 归 M3 —— 与简报预期一致，非缺陷
- M3 交接（三函数签名）：`parse_amount(raw: str|None)->float|None`（**带符号**，不 abs 不 round，失败→None）；`parse_time(raw: str|None)->str|None`（16 字符 `YYYY-MM-DD HH:MM`，已过 `schemas/record.py` 正则交叉断言）；`resolve_type(raw, amount, source)->(type|None, skip_reason|None)`，skip_reason ∈ {type_ignored, type_unresolved, invalid_amount}（与 D12 五键同名），column 不可判不回落 sign，sign 下 0/负→expense
- 白名单落定：`TIME_FORMATS` 13 项逐字零增删；EXPENSE/INCOME/IGNORE 三集合 9/9/6（含 `/`，D31）；`OUTPUT_FORMAT="%Y-%m-%d %H:%M"`
- 子 Agent 登记的偏离/收口（主 Agent 复核认可，不判偏离）：`math.isfinite` 兜底 inf/nan→None（验收标准「绝不静默产脏值」必要收口，有专门用例）；`元` 首尾皆剥；`(-12.00)`→+12.0（括号取负语义）；`parse_time` 不做 NFKC（全角日期不猜）；任务文件 §1.3 line25 内部矛盾按 D10+边界表实现为 `>0`→income、`<=0`→expense
- 已知边界（§5.3 登记）：歧义日期序不支持、CSV 侧无 Unix 时间戳换算、Excel 改「常规」另存的裸序列号 `46289.48…` 判 None
- 待人工抽检：M2 无新增人工项（其手工口径已被 §4.1–4.8 自动化覆盖）
### M6（done，`1db6e54` + `d93c736` + 主 Agent 断言修正 `2107429`，2026-09-24 核验通过）
- 提交 pathspec 精确（4 文件；`d93c736` 为测试注释去 `example/` 字面量的红线自查修正）；任务文件 31/32（唯一未勾 §5.1 全量绿 = 两登记内红灯，沿 M1 §9.1 口径不静默勾选）
- **container 到期断言处置（主 Agent P3 单点）**：M1 `test_8_8` 原断言 `"container" not in result`（自带注释「属 M6」）到期 → 主 Agent 改写为 `result["container"]=="csv"`（`2107429`，改断言不改后端）。M6 不越界改 M1 独占文件、不删契约，处置正确
- 主 Agent 复跑：`test_csv_dialects.py`+`test_xlsx_reader.py` **132 passed**；全量 **588 passed / 1 failed**（唯一红灯 = `test_preview_unknown_format`，M3 §5.1 预留反转）；mypy **88 errors/14 files** 零新增（`xlsx_reader.py` 自身 strict 零报错）；ruff clean
- 红线 grep 实证：四表头函数 `def` 仍只在 `csv_dialects.py`；`openpyxl|xlrd|pandas` 零命中；`example/` 零命中；裸 `csv.reader` 现状 = `csv_rows` 内收口 1 处（合法）+ **`import_csv_data` :328 归 M3** + SQL 区 :531/:1508 禁触不计；money.db SHA256 逐字未变
- 交接 M3 的关键事实：`_to_rows(file_bytes)->(rows, container)` @ `import_service.py:105`（**M3 §2.2 确认阶段重算必须调用它**，同批字节两次调用必得同一 container）；配套 `_cache_suffix` :99 / `_read_cached_bytes` :131（后缀已成对）；**遗留禁触 = `import_csv_data` :324-328 的 `detect_and_decode`+裸 `csv.reader` 三步与行循环，M3 用 `_to_rows` 替换即闭合 xlsx 确认通道**；行号漂移：detect_and_decode :46、csv_rows :78、preview_csv :187
- 主 Agent 复核认可的偏离：① `io.BytesIO` 入依赖（`zipfile.ZipFile` 不接受裸 bytes，标准库内、零新增第三方，认可）；② §4.10 `header_row_index` 三事不可能同时成立 → 一手事实优先、两口径并测（矩阵内 16 / `extra_preamble=1` 得 17），**M5 §2.9.1 按 M6 交接口径取用**；③ numFmt `formatCode` 含 y/m/d 为设计逐字判据，`[Red]` 理论误判不扩白名单，登记 §6.7 已知边界；④ 预览 CSV 通道对同批字节二次解码取 encoding（性能可忽略，保签名稳定，认可）
- **合成构造器交接 M5（只调不重写）**：`build_xlsx(rows,*,inline=False,hidden_before=0)->bytes`、`wechat_xlsx_bytes(...)`、`wechat_matrix_rows()`/`wechat_preamble_rows()`/`wechat_data_rows()`、`_zip_write(payload,*,drop="",replace=...)`、常量 `WECHAT_HEADERS`/`DATA_ROW_COUNT`/`DATE_SERIAL_TEXT`/`DATE_TEXT`/日期样式与金额样式索引；均在 `tests/test_xlsx_reader.py` 内 import 复用
- 待人工抽检抄录：真实微信 `.xlsx` P4 对照 / `.xls` 中文透出 / 用户 Excel 另存 CSV 路径 / 真实浏览器文件选择整链——4 条均与「待人工抽检清单」既有条目（含 M4 抄录行）同源，未新增行
### M3（done，`a46b0f2`，主 Agent 2026-09-24 核验通过）
- 提交 pathspec 精确（6 文件含夹具）；任务文件 **44/44 全勾**；`money.db` SHA256 逐字未变
- 主 Agent 复跑：全量 pytest **603 passed / 0 failed / 0 skipped**（本批首次全仓绿灯，含 §5.1 反转闭合）；mypy **85 errors/14 files**（基线 89 → 零新增且 -3）；ruff clean；SQL 区与识别区分派函数在 diff 中**零命中/零删除行**实证
- D16 旧符号零残留：`def` 与调用点全域零命中，剩余命中全为注释/docstring 溯源（`import_service.py:495`、`test_csv_import_export.py:936-938` 等，合法）；`import_csv_data` 内裸 `csv.reader` 已消失（M6 遗留点闭合，xlsx 确认通道经 `_to_rows` 打通）；`detect_and_decode` 不再被 `import_csv_data` 直接调用
- 夹具可跟踪实证：`git ls-files` 命中 `cashew_import_template.csv`（工作树 181 B / blob 179 B 系 autocrlf 归一，用例只按字节流解析不断言长度——主 Agent 认可）；`example/` 字面量全域零命中延续（M3 新注释按 `d93c736` 同口径书写）
- **P3 契约差异终核（M3 notes，主 Agent 认可）：与 M4 冻结契约零差异**。关键裁定：① `columns` 权威位 = **整体替换**语义（与 M4 恒发全量角色的载荷行为天然匹配，§5.5 正反锁死）；② CSV 成功文案：后端 message 保持「成功导入 N 条记录」一字未动（U3），前端 toast「成功导入 N 条」为本地拼接不消费后端 message——**两口径不冲突，无需 M4 修正轮**（M4 台账中的该项疑虑就此销项）；③ `skipped_reasons` 键序与前端 `SKIPPED_REASON_LABELS` 逐位同序已核
- 主 Agent 复核认可的偏离：(1) 落库侧新增私有 `_value_by_index`（只 strip 不归 `/`）防 `type_ignored`/`type_unresolved` 标签失真，**未回改 M1 `_cell_by_index`**（预览语义不变）——D31 落库半区的正确收口；(2) 索引越界以表头单元格数为基准、未知角色键由 `REQUIRED_ROLES` 兜底；(3) §5.11 xlsx HTTP 端到端按任务归 M5 §2.9，M3 实走 `_to_rows` 服务层
- **M1 §9.1/§9.2 与 M6 §5.1 到期未勾项：主 Agent 已补勾**（任务文件内附引用块说明，随本批 progress 提交）
- 待人工抽检抄录：M3 手工项 6.2/6.3/6.5 均已在 HTTP/git 层自动覆盖并实证（6.2→§5.3/5.4/5.10 读 `/api/records` 回核；6.3→SHA256 双对照+工作树盘点；6.5→ls-files+show --stat），登记为「已自动化实测，人工无需复做」
### M4（done，内容全量落在 `158726c`，主 Agent 2026-09-24 核验通过）
- **提交归属注记（并行事故，内容无损）**：M4 子 Agent 按 pathspec `git add` 后其 3 次 `git commit` 均被权限层拦下（未产生独立 feat 提交）；主 Agent 提交 progress.md 时 git 默认提交整个索引，把 M4 四文件（`CsvMappingDialog.vue`/`SettingsImportExportPage.vue`/`SettingsSubPages.test.js`/其任务文件）**一并带入 `158726c`**（标题仍为 M2 落盘）。核验 `git show --name-only 158726c` = 该四文件 + progress.md，**不含 M1 在途文件**；工作树与 HEAD 对这 4 文件零差异；不 rewrite 历史（禁 amend/reset），特此登记。此后主 Agent 提交 progress.md 一律 `git commit -- <path>` 只提指定路径。
- 任务文件 41/42 勾选（唯一未勾 = §7.3 明暗×竖/宽屏观感，人工终判类，正确留人工）
- 主 Agent 复跑：**vitest 408/408**（基线 397 + 新增 11）、eslint 0 errors/2 warnings（基线同值）；`git diff 7ae57da..HEAD` 无 `package.json`/lock/requirements 命中（**零新增依赖**）；`CsvMappingDialog.vue` 零命中 `v-stepper` 且零新增 Vuetify import；`accept=".csv,.xlsx"` 在 `SettingsImportExportPage.vue:72`、SQL 侧 `accept=".sql,.db"`:79 未动
- **P3 契约核对结论（子 Agent notes，主 Agent 认可）**：§1.2.5 八字段与 §3.2 三字段**逐位一致、零差异**；`container` 双态已测（xlsx 显示「Excel 工作表」/ 缺席不渲染，§6.4.9）；`encoding=="xlsx"` 哨兵不当编码展示；SQL 复用路径三字段整体不写入 + 键集断言锁定（请求体一字不变）；同角色两列取靠前列（与 D3 同序）；存在 category 角色时不发 `fallback_category`
- 子 Agent 登记项（主 Agent 复核）：① `v-radio-group`/`v-radio` 为任务 §3.1 明定组件且弹窗 Vuetify 标签集合已被 §6.4.8 `?raw` 钉成封闭集——不判「新增组件」违规；② M5-3 成功 toast 期望改「成功导入 3 条」系任务 §5.2/设计 §4.2.3 明定文案、同测试净增 9 断言未删未放宽——合法口径修正，记入附录 B 台账（M3 落地后若后端 message 文案与此不符按 P3 以后端为准派修正轮）；③ §5.5 格式说明文案「附近无该文案 → 不新增不扩写」——符合 U3 精神；④ 分类候选异步晚到时序缺陷 = 设计 §4.3 已登记遗留，未扩围，沿设计跟踪
- 待人工抽检（抄录进下方清单区）：7.3 观感截图 / 真实浏览器文件选择整链 / 真实微信 .xlsx 对照 / 真实支付宝账单 / .xls 失败中文透出确认
### M5（done，`1256f44`，主 Agent 2026-09-24 核验通过）
- 提交 pathspec 精确（e2e + README + 任务文件 3 件，+1,631 行、零素材新建）；主 Agent 复跑全量 **632 passed / 0 failed / 0 skipped**、mypy 85 零新增、ruff clean；README diff 复核 = Version History 一行 + 导入须知小节，Features 未动（版本政策合规）
- §2.10 契约一致性断言在场（只读前端源码提取 payload 键集 ⊆ `ImportCsvRequest.model_fields`、columns 项 4 键、ROLE/TYPE_SOURCE/FORMAT 封闭集对照），无 skip 分支；§2.3 读取侧三处断言在场；§2.9 五例 + D27 反向护栏（九种垃圾载荷零英文内部串）在场
- 素材性质双登记合规：docstring + notes（模板夹具与导出字节 = 实证；微信/支付宝/Cashew 10 列/xlsx 镜像 = 合成，17 列勘误显式标注；随手记/京东/银行为自拟列名仅证 custom 路径）
- 主 Agent 裁定两项移交：① **`group_by` 勘误成立**（本仓库 statistics 端点实参为 `group_by`，设计/任务写 `granularity=month`）——按现状契约，不改实现，登记勘误；② 「仅前导行无表头的 xlsx」得到中文 `CSV 文件为空`——设计 §6.4 明写两通道同处置（共享 `locate_header_rows`），满足 D27「中文 ValueError」，**不判缺陷不补文案**，登记已知边界
- 未勾 13 条全部为主 Agent 终验项（§4.1–4.5/§5.2），已随本次终验逐条闭合（见「终验记录」）
- 待人工抽检抄录：见下方清单（M5 §4.3 系列 = P4 移交项，与既有条目同源）

## 终验记录（主 Agent，2026-09-24 执行完毕）

### 六命令（M5 后 HEAD 全量复跑）
| 命令 | 结果 | 基线对照 |
|------|------|----------|
| `pytest tests/ -q` | **632 passed / 0 failed / 0 skipped**（113.9s） | 开工 298 → +334 全为本批新增 |
| `mypy app` | **85 errors / 14 files** | 开工 89 → **零新增（-4）**；三个新 service 文件自身 strict 零报错 |
| `ruff check app tests` | **All checks passed** | 同基线 |
| `npx vitest run` | **408 passed / 408**（15 files） | 开工 397 → +11（M4） |
| `npm run lint` | **0 errors / 2 warnings** | 基线同值零新增 |
| `npm run build` | 成功（rolldown chunk-size 提示为既有非错误） | dist gzip **538,234 B** vs 开工 535,927 B = **+2,307 B**（boot2 基准 +127 B 同口径，待人工裁定可接受性） |

### 9 条跨模块闭环点（§6.2，逐项必查全部通过）
1. D16 旧符号 `def`/调用点全仓 grep **零命中**（仅注释溯源，不留转发壳）✅
2. 前端真实请求体字段与 `ImportCsvRequest` 逐位一致（M5 §2.10 断言在场 + P4 实测 HTTP 200 落库）✅
3. `DIALECT_ORDER = (native, cashew, cashew_template, alipay, wechat)`，alipay 先于 wechat，且 §8.4 测试内局部乱序陷阱用例在场（未改生产常量）✅
4. `test_preview_unknown_format` 已反转为正断言（code==0 + custom + 全列 role=None），其余既有 native/cashew 用例断言一字未改（M3 diff 仅 3 hunk 自证）✅
5. 读取侧三处：M5 §2.3 断言在场 + **P4 实测**（`/api/records` 9 月过滤 93 条、`trend?group_by=month` 月份键全合法、229 条 `consume_time` 正则零违例）✅
6. SQL 导入链路文件 `git diff 7ae57da..HEAD` **零命中**（M3 251+/108- 全落落库区，识别区/分派器零 hunk 实证）✅
7. 零新增依赖：`package.json`/lock/`requirements`/`pyproject` 在 diff 中零命中 ✅
8. 夹具可跟踪（`git ls-files` 命中）+ `git grep example/` 零命中 + `git diff --stat` 不含 `example/` ✅
9. Excel 四点：① 表头定位四函数 `def` 只在 `csv_dialects.py`、CSV 通道裸 `csv.reader` 仅剩 `csv_rows` 收口 1 处（SQL 区 :531/:1508 禁触不计）✅ ② `container` 后端产出与前端渲染逐位一致（P4 实测「Excel 工作表」caption 在场）✅ ③ `.xls`/非 zip/超限/空表全中文 `PARAM_ERROR`（P4 实测 `.xls` → `code=40001, message=暂不支持 .xls，请在 Excel 里另存为 .xlsx 或 .csv`，零英文内部异常）✅ ④ `openpyxl|xlrd|pandas` 零命中 + M6 §4.7 `ast` 用例在场 ✅

### P4 浏览器实测（主 Agent 亲执，tmp 副本库）
- **环境**：`DATABASE_URL` 指向 `backend/files/p4_money.db`（money.db 逐字节副本，SHA256 `b7974d15…c7deb3` 开工/收档一致，**原库全程零写入**）；真实素材经 `.gitignore` 的 `backend/files/` 中转，测毕已删除（`files/` 现 0 文件）
- **登录**：注册 `p4tester` + UI 登录（登录卡 → 主页跳转成功）
- **链路② Cashew 模板**（CDP 真实文件上传 `backend/tests/fixtures/csv/cashew_import_template.csv` → `input[type=file]` change → 预览请求）：向导渲染「格式：Cashew 模板 · 共 2 条记录」、编码 `utf-8`、逐列角色建议（Date→时间/Amount→金额/Category→分类/Title→标签/Note→备注/Account→不导入）、样例行表、收支三态 radio（0 归支出提示语）；「确认导入」初始禁用（分类未映射），映射后解禁 → HTTP 200 → toast **「成功导入 2 条」** → `/api/records` total=2、`-50→expense 50`、`250→income`、Category 新建 `Groceries`/`Bills & Fees` 入分类表 ✅
- **链路③ 自定义中文表头手选**（`backend/files/custom_cn.csv`，列名非别名表）：预览判「手动映射」（退化表头定位 + 全列 `role=None` 正确），手选 `花费金额→amount` 后按钮解禁；**缺分类列时 `missingRequiredCount=1` 强制「账单归入」**（D8 生效），选餐饮 → 导入 3 条、`consume_time` 全 16 字符、`备注→note` 正确、「付款方」不入库 ✅
- **链路④ 真实微信 `.xlsx`**（28,042 B 用户一手文件，本机对照、素材值不外抄）：预览判 `wechat` + `container=xlsx` + `encoding="xlsx"` 哨兵、共 **228** 条、告警「未识别到分类列：需指定默认分类」+「已忽略 15 行账单说明文字」；**11 列逐列角色与 D9 走查完全一致**（交易类型 null/支付方式 null/…，`金额(元)`→amount 剥括号）；交易时间样例 = 日期序列号换算产物（naive 挂钟）；收支四态含「按收/支列」；设归入后确认 → toast **「成功导入 224 条，跳过 4 条（不计收支）」**（4 笔 `/` 中性交易自然排除）；读取侧：total 229、9 月过滤 93、趋势月份键 `2024-03/2026-06/07/08/09` 全合法、`consume_time` 正则零违例 ✅
- **链路① 导出→导入闭环**：`GET /api/export/csv` 真实字节（15,597 B、BOM `ef bb bf`、`encoding=utf-8-sig`、判 `native`）喂 preview+confirm → 首轮 2 条闭环（227 条 `category_unresolved` = **既有导出器缺陷**，见「已知边界」新登记条）；补 `fallback_category` 后二轮 **231/231 全量闭环、skipped 五键全 0**（D20 无去重 → 462 条预期翻倍）✅
- **`.xls` 拒绝**：`code=40001` 中文另存指引、无英文异常 ✅；前端 `accept=".csv,.xlsx"` 在真实 DOM 在场（.xls 连文件选择框都被过滤）✅
- **⚠ 截图缺位（环境限制）**：Qoder 内嵌浏览器无可见 surface（viewport 0×0），`take_screenshot` 与指针点击均不可用；实测以 **CDP 文件上传 + DOM 快照 + 网络面板 + 页面内真实 fetch（携带 UI 同源 token）** 完成，证据 = 本会话快照/响应原文。**观感类（明暗 × 竖/宽屏）与人工点选手感仍留人工终判**，不得以本段替代。

### 收尾
- `frontend/dist` 终验重建单独提交 `8000489`；README 条目已随 M5 `1256f44` 入库
- money.db SHA256 收档 = 开工登记值逐字一致；工作区无测试残留（`backend/files/` 清零）

## 阻塞清单

（空）

## 待人工抽检清单（子 Agent 不勾选）

- [x] **真实支付宝账单**导入一次（前导行漂移、GBK 系编码、`/` 占位）——**2026-09-25 用户已提供一手文件（`example/支付宝交易明细(20260824-20260924).csv`，15,707 B）**，主 Agent 本机对照亲执（tmp 副本库、素材只读、值不外抄）：**编码判 `GB18030`✓（GBK 系解码打通）、表头实落第 23 行（调研样本 24 行 → 前导漂移由 D1 动态定位消化）✓、判 `alipay`、13 列含空尾列角色与 §0.4-10 逐位一致、预览 88 行 → 导入 39 / 跳过 49 全部为 `type_ignored`（`/` 中性交易占位，D31 预期口径，UI 以 skipped_reasons 提示）、`consume_time` 零格式违例、月份键 2026-08/09 合法、分类同名合流后新建 6 个、预算接口正常**。性质 = **HTTP/服务层自动化等价实测（非 CI、非真实浏览器点选；本轮为 API 级，UI 向导逻辑与微信链路同构已另行覆盖），真实浏览器内支付宝文件的手选体验仍可人工复做**。原库 SHA256 复核逐字未变
- [x] **真实微信 `.xlsx` 本机对照导入一次**（用户 2026-09-24 提供一手文件）：**主 Agent P4 已亲执**（tmp 副本库 + CDP 真实上传）——预览判 `wechat`+`container=xlsx`+`encoding=xlsx`、228 条、必选「账单归入」、4 笔 `/` 中性交易不入库（导入 224/跳过 4）、序列号日期换算、月份过滤/趋势/正则三处读取侧全绿。**性质 = 本机对照非 CI 证据；截图因内嵌浏览器无可见 surface 未能存档（环境限制），证据为本会话 DOM 快照与网络响应原文**；人工请在真实浏览器复做一遍并补 `screenshots/v1.4.3-boot3/` 截图
- [ ] **用户自助路径**：在 Excel 里把该 `.xlsx` 另存为 CSV 再导一次，登记实际日期形态（文本/序列号）与编码，确认 D14/D15 不误收脏日期（P4 无法代跑 Excel 另存动作）
- [ ] 真实浏览器：文件选择（含 `.xlsx`）→ 向导三区块 → 记录出现在账单页与月统计——**P4 已覆盖逻辑半区**（CDP 真实上传 + 向导全渲染 + 入库回核），**人工指针点击/原生文件对话框手感与观感仍待终判**（内嵌浏览器 viewport 不可用）
- [ ] 明暗 × 竖屏/宽屏观感截图（列角色表 + 样例行表格）+ M4/7.3 窄弹窗 overflow-x 实测——纯观感，人工终判
- [ ] **M4**：`.xls` / 超限 / 非法 Excel 中文 message 前端透出确认——**P4 已实测后端透出**（`code=40001` 中文文案 HTTP 200 包体），人工仅需在真实浏览器确认 toast 观感
- [ ] 在 Cashew App 内用官方模板实际导出一次（官方仓库模板文件已 404，模板可选列未能一手核对）；**主 Agent P4 另以 `example/cashew-import-template1790219274617.csv` 做过一次真实文件对照导入（链路②，本机对照性质，未入库、值不外抄）**

## 开工登记（2026-09-24 主 Agent 实测）

- [x] 基线 HEAD：`7ae57da`（`git rev-parse --short HEAD` 实测）
- [x] `backend/money.db` SHA256：`b7974d151c6edc17ec964969ef103570f0688d8ec521e05d3f58d899e6c7deb3`
- [x] 六命令开工基准（`venv/Scripts/python.exe` / npm 实测）：
  - pytest：**298 passed**（0 skipped，86.25s）
  - vitest：**397 passed / 397**（15 files）
  - mypy（`mypy app`，配置已含 strict）：**89 errors / 14 files**（checked 51 source files）→ 零新增口径对照此数
  - ruff（`ruff check app tests`）：**All checks passed**
  - eslint：**0 errors / 2 warnings**
  - build：交终验统一重建
- [x] dist gzip 基准：**535,927 B**（现有 dist，js/css/html 合计 gzip 后；终验重建后对比，boot2 增量基准 +127 B）
- [x] 现场库只读复测（`file:money.db?mode=ro`）：`budgets` 列集含 `scope_mode`+`dormant`；`categories` 全库仅一个「其他」（id=34、user_id NULL）；`PRAGMA foreign_key_check` = **52 条且全在 `tags`**（与发布备忘登记一致，本批不恶化基线）
- [x] 工作区既有未跟踪文件盘点：`doc/` 各批输入文档（含本批 prompt/设计/tasks 全套）、`screenshots/ali|baota|v1.2|v1.3|v1.3.1|v1.4.3-boot` ——**除本批点名文件外一律不触碰、不提交**

---

## 附录：v1.4.4 增补批（2026-09-25，用户三条新裁定，会话内直改非 boot 文档批）

**裁定翻案登记**（推翻本批 D8/D9/D15 局部，其余 D 决策继续有效）：**V1** 斜杠日期按「唯一合法解释」识别（`09/24/2026`/`24/09/2026` 收，`05/06/2026`、`05/05/2026` 两读皆可 → 照旧跳过计 `invalid_date`）；**V2** `交易对方`+`商品/商品说明` 双列 note 拼接（`·` 分隔、空段省略、不再建标签），`交易类型`（微信）与`交易分类`并列作分类来源（别名层全局生效）；**V3** 分类落空链 = 映射 → `fallback_category` → 自动匹配（归一相等/双向包含≥2/同义词`饮食→餐饮`）→ 全局「其他」，`category_unresolved` 恒 0（键位保留）、「账单归入」降级为可选。预览新增可选字段 `categories_suggested`（与落库共用同一 `_match_category_auto`，所见即所得）。

**提交**：后端 `328812c`（662 绿）→ 前端+preview 字段 `be13f91`（pytest 664 / vitest 411 / mypy 85=基线 / ruff / eslint 基线 / build）→ dist `+210 B` 与 README 收口 `8e7d118`。既有用例按 V 逐条改写 23+4 处（子 Agent notes 全清单在案），int 型 `columns` 旧载荷兼容有专测（D18 延续）。

**真实账单复测（tmp 副本库，原库 SHA256 全程未变）**：微信 `.xlsx` = 判 wechat、category 1 列 + note 2 列、**零映射**导入 224/跳过 4、96 条 `·` 拼备注、0 标签、时间零违例；支付宝 CSV = 判 alipay、零映射导入 39/跳过 49（`/`）、suggested 命中 2/11、3 分类复用无膨胀；斜杠日三例端到端如期（2 收 1 跳）。

**已知边界（v1.4.4 新增）**：`categories_suggested` 的自动匹配候选 = 全局预设 +（前端 name 直配链）用户自建分类——预览路由未注入 user，后端建议值对用户自建分类不覆盖（UI 直配兜住，登记备查）；导入中途并发改分类名的极端竞态未扩范围。

**v1.4.4 热修（2026-09-25，版本号不变）**：`export_csv` 分类/标签名查找扩为 `user_id = :uid OR user_id IS NULL`（全局共享行此前导出空白，P4 实测 227/229；id 全局唯一无覆盖问题，SQL/SQLite 备份路径与 dormant 区未触）。回归：新增 1 例（pytest 665 全绿、mypy 85=基线、ruff clean）；真实微信 `.xlsx` 复测「导入 224 → 导出 224 行分类名空白 0 → 原样回导 224、skipped 五键全 0」，即导出→回导分类语义已无损。提交 `2199169`。
