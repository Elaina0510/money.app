# Money App v1.4.3-boot3 总体进度

> 唯一进度载体。仅主 Agent 读写。基线：v1.4.3-boot2（HEAD `7ae57da`；2026-09-24 实测 `origin/main` == HEAD，**已推送**）。
> 本批由**单条用户反馈**发起（「导入一份 CSV 文件提示无法识别」），经**三轮**澄清扩为**五条子需求 A/B/C/D/E**——第三轮因用户提供**真实微信账单且其为 `.xlsx`**（`example/`，含真实数据、禁止入库）而新增需求 E = Excel 直读（设计 §六）。权威设计：`doc/detailed-designv1.4.3boot3.md`。
> **零新增依赖（xlsx 只用标准库 `zipfile` + `xml.etree`；实测 venv 无 openpyxl/pandas/xlrd）、零 DB 变更、零迁移脚本。**

---

## 模块清单（6 个，划分轴心 = 层次 + 文件独占；与需求非一对一，映射见括注）

| 模块 | 名称 | 需求 | 任务文件 | 状态 | 提交 |
|------|------|------|----------|------|------|
| M1 | 后端识别层：解码 + 表头定位（**交付行矩阵契约**）+ 方言与列角色 | A、B、D | `m1-backend-detect-layer.md` | pending | — |
| M2 | 后端清洗层：金额/日期/收支三态纯函数 | C | `m2-csv-value-normalization.md` | **done** | `7c3c87f` |
| **M6** | 后端 **Excel(.xlsx) 容器层**：magic 判定 + stdlib 读表 → 行矩阵（日期序列号在容器层换算为文本） | **E** | `m6-xlsx-container.md` | pending | — |
| M3 | 后端落库层：统一列角色解析 + 契约扩展 | A、C、D | `m3-backend-import-writer.md` | pending | — |
| M4 | 前端列映射向导（+ `accept` 扩 `.xlsx` 与 Excel 标识） | A、**E** | `m4-frontend-column-mapping.md` | pending | — |
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

- **零迁移脚本、零 schema 变更** → 发布窗口只需部署新后端 + 新 `frontend/dist`，不需停库/备份演练
- 与 boot2 发布窗口的关系（**2026-09-24 对现场库只读实测后更新**）：boot2 登记的「现场库未跑 v1.4.3 迁移 + 70 条既有 FK 违规 → 预算接口 500」**已非现状**——实测 `budgets` 已含 `scope_mode`/`dormant` 列、全库仅剩一个「其他」预设（id=34、user_id NULL、sort=14）、`is_preset=1 且 user_id 非空` 异常行为 0，`PRAGMA foreign_key_check` 余 **52 条且全在 `tags`**（DB mtime 当日 11:04）。**成因不在本批追查范围**（超出本批导入识别范围）；本批仍为零迁移、零 DB 变更，开工时由主 Agent 以 `file:money.db?mode=ro` 只读复测并登记基线，余 52 条 tags 孤儿继续沿用 boot2 `progress.md` 的跟踪条目。
- 冒烟四条：① 导出 CSV 立即导入同一份文件条数一致；② 模板 `-50`→支出、`250`→收入；③ 任意中文表头手选列能入库；④ `.xlsx` 直传能出预览（`container=xlsx`），`.xls` 得到中文「请另存为 CSV/.xlsx」提示而非英文异常
- 回退：换回旧后端 + 旧 dist，零数据残留

## 终验清单（质量门，设计附录 A）

- [ ] `backend/venv/Scripts/python.exe -m pytest`（**基线 298**，2026-09-24 文档产出时点实测；boot2 记忆里登记的 296 已被其后续两条热修 `2bef12a`/`7ae57da` 的回归用例抬高，故此处取实测值 + 本批新增）全绿、`0 skipped` 复核
- [ ] `npx vitest run` 全绿（**基线 397 实测** + M4 新增）
- [ ] `mypy backend/app --strict` = 基线 **89 errors / 14 files**（2026-09-24 实测 `venv/Scripts/python.exe -m mypy app --ignore-missing-imports`；boot2 登记的 90 已随热修下降）→ **零新增**口径
- [ ] `ruff check` clean；`eslint` 0 error
- [ ] `vite build` + dist 重建单独提交 + gzip 增量对比 boot2（`+127 B` 基准）
- [ ] `backend/money.db` SHA256 与开工登记一致
- [ ] **夹具可跟踪性（D21）**：`git ls-files backend/tests/fixtures/csv/` 命中；`git grep -n "example/" -- backend frontend` 零命中（当前 HEAD 实测已零命中，须保持）；`git diff --stat <开工基线>..HEAD` 不含 `example/` 路径
- [ ] **Excel 零依赖（D23/红线 13）**：`git grep -n -i -E "openpyxl|xlrd|pandas" -- backend/app backend/tests frontend/src` 零命中（当前 HEAD 实测已零命中；范围不含 `frontend/dist` 打包产物）；M6 §4.7 的 `ast` import 白名单用例在场且通过
- [ ] **无英文内部异常透出（D27）**：M5 §2.9.4 反向护栏通过——导入相关响应 `message` 不含 `new-line character`/`_csv.Error`/`BadZipFile`/`UnicodeDecodeError`
- [ ] 浏览器实测（主 Agent 亲执，general-purpose 子 Agent 无 browser-use）：**四条**冒烟 + 向导三区块交互 + **真实微信 `.xlsx` 本机对照导入一次**（素材在 `example/`，只读、不入库）
- [ ] README Version History 条目

> **基线数字口径**：上列三项为 2026-09-24 文档产出时点（HEAD `7ae57da`）的一次性实测，**开工时须以当时 HEAD 复测并写入「开工登记」**，终验以开工登记值为准做零新增比对，不得沿用本表数字。

## 进度统计

| 项 | 数值 |
|----|------|
| 模块 done | 1 / 6（M2） |
| checklist 勾选 | 22（M2）+ 在途模块待计 |
| 待人工抽检 | 0 新增（M2 无人工项） |
| 阻塞 | 0 |

## 模块执行记录

### M1（pending）
### M2（done，`7c3c87f`，主 Agent 2026-09-24 核验通过）
- 提交 pathspec 精确（3 文件，`import_service.py` 零命中 = 「未接线」自证成立）；任务文件 22/22 勾选
- 主 Agent 复跑：`test_csv_values.py` **159 passed**；mypy 工作区 88 errors/14 files（≤ 基线 89，零新增；其中 M1 在途贡献待 M1 复测）；ruff 工作区 3 项 UP012 **全部位于 M1 在途 `test_csv_dialects.py`**（E3 归属 M1，M1 提交前须清零）
- 子 Agent 全量复跑 2 次：456/457，唯一红灯 `test_preview_unknown_format` 归属 M1 在途语义扩展（unknown→custom），其口径反转按附录 B 归 M3 —— 与简报预期一致，非缺陷
- M3 交接（三函数签名）：`parse_amount(raw: str|None)->float|None`（**带符号**，不 abs 不 round，失败→None）；`parse_time(raw: str|None)->str|None`（16 字符 `YYYY-MM-DD HH:MM`，已过 `schemas/record.py` 正则交叉断言）；`resolve_type(raw, amount, source)->(type|None, skip_reason|None)`，skip_reason ∈ {type_ignored, type_unresolved, invalid_amount}（与 D12 五键同名），column 不可判不回落 sign，sign 下 0/负→expense
- 白名单落定：`TIME_FORMATS` 13 项逐字零增删；EXPENSE/INCOME/IGNORE 三集合 9/9/6（含 `/`，D31）；`OUTPUT_FORMAT="%Y-%m-%d %H:%M"`
- 子 Agent 登记的偏离/收口（主 Agent 复核认可，不判偏离）：`math.isfinite` 兜底 inf/nan→None（验收标准「绝不静默产脏值」必要收口，有专门用例）；`元` 首尾皆剥；`(-12.00)`→+12.0（括号取负语义）；`parse_time` 不做 NFKC（全角日期不猜）；任务文件 §1.3 line25 内部矛盾按 D10+边界表实现为 `>0`→income、`<=0`→expense
- 已知边界（§5.3 登记）：歧义日期序不支持、CSV 侧无 Unix 时间戳换算、Excel 改「常规」另存的裸序列号 `46289.48…` 判 None
- 待人工抽检：M2 无新增人工项（其手工口径已被 §4.1–4.8 自动化覆盖）
### M6（pending）
### M3（pending）
### M4（pending）
### M5（pending）

## 终验记录（待主 Agent 执行）

## 阻塞清单

（空）

## 待人工抽检清单（子 Agent 不勾选）

- [ ] **真实支付宝账单**导入一次（前导行漂移、GBK 系编码、`/` 占位）——**本会话无该文件、合成夹具不可替代，不得声称已验证**
- [ ] **真实微信 `.xlsx` 本机对照导入一次**（用户 2026-09-24 已提供一手文件于 `example/`）：**主 Agent 在 P4 亲执**，断言预览判 `wechat` + `container=xlsx`、必选「账单归入」、中性交易（`/`）不入库、金额与月份正确；结论 + 截图登记并标注「本机对照，非 CI 证据」
- [ ] **用户自助路径**：在 Excel 里把该 `.xlsx` 另存为 CSV 再导一次，登记实际日期形态（文本/序列号）与编码，确认 D14/D15 不误收脏日期
- [ ] 真实浏览器：文件选择（含 `.xlsx`）→ 向导三区块 → 记录出现在账单页与月统计
- [ ] 明暗 × 竖屏/宽屏观感截图（列角色表 + 样例行表格）
- [ ] 在 Cashew App 内用官方模板实际导出一次（官方仓库模板文件已 404，模板可选列未能一手核对）；**主 Agent P4 终验时另可用本机 `example/cashew-import-template1790219274617.csv` 做一次真实文件对照导入**（只读素材，结论须标注「本机对照」，不进 CI、不作夹具）

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
