# M5 - 端到端真实样例回归 + 文档收口（需求 A/B/C/D/E 总验）

> 对应设计 §五。目标：用**真实模板的逐字副本 / 真实导出产物 / 逐字表头合成夹具（CSV 与 xlsx 两种容器）**三类样例把五条子需求一次验完，并把「哪些是实证、哪些是合成」诚实登记；README 与人工验收清单收口。
> 涉及文件：新增 `backend/tests/test_csv_import_boot3_e2e.py`、`README.md`、`doc/tasksv1.4.3boot3/progress.md`（发布备忘与人工清单段）。**只读复用** M3 §5.0 的夹具 `backend/tests/fixtures/csv/cashew_import_template.csv`（**不重复落文件、不改 M3 的 `test_csv_import_export.py`、不引用 `example/`**，D21）；xlsx 素材用 **M6 §4.1 的构造器**（本模块不新建 fixture 文件）。
> 依赖：M1 + M2 + M3 + M4 + **M6** 全部合入。**收尾模块，串行最后。**

---

## 1. 样例性质登记（写进测试文件头 docstring，禁止混淆实证与合成）

- [x] 1.1 **真实模板的逐字副本**（D21）：`backend/tests/fixtures/csv/cashew_import_template.csv`（M3 §5.0 建；源文件为本机 `example/cashew-import-template1790219274617.csv`，用户所给、6 列、符号法收支、无前导行）。**e2e 只读该夹具路径，禁止读 `example/`**（该目录 git 未跟踪，新克隆/CI 读不到）
- [x] 1.2 **真实产物**：`export_service.export_csv` 的带 BOM 字节（需求 D 的闭环验证素材）
- [x] 1.3 **合成**（表头原文真实、数据行合成）：Cashew 全量导出形态 = 17 列表头**逐字**取自设计 §0.4-10（含日期 `...10:58:23.000` 形制）+ 合成数据行。本机虽有真实文件（`example/cashew-2026-06-11-15-42-13-865.csv`），但**含用户真实数据 → 禁止入库，也不得把其内容抄进夹具**（红线 11），只作主 Agent 本机人工核验素材
- [x] 1.3b **一手实证但禁止入库**：真实微信账单 `.xlsx`（用户 2026-09-24 提供，在 `example/`，含真实交易数据）→ 自动化用例改用 **M6 §4.1/§4.2 的「结构镜像 + 数据全合成」xlsx**（11 列表头逐字、前导 17 行、第 16 行缺失、稀疏列、serial 日期、`/` 占位）；真实文件仅由主 Agent 在 P4 做一次本机对照导入。**支付宝 `.xlsx` 形态未一手核对** → 只声称「容器层通用规则覆盖」，不声称已验证
- [x] 1.4 **合成夹具**：微信 / 支付宝——表头与典型行**逐字**取自设计 §0.4-10 的一手样本（前导 16/24 行、`¥28.16`、`不计收支`、`/` 占位、支付宝 13 个空尾列均按样本复现），**非真实导出文件**
- [x] 1.5 测试文件头 docstring 显式声明 **§1.3 与 §1.4 均为合成**（表头原文取自一手样本、数据行为合成） + 调研来源清单（微信/支付宝一手样本出自 `WeChatPay_to_Notion` 仓库、`double-entry-generator` Quick Start、BeeCount wiki；Cashew 导入模板为本仓库 `example/` 实测的逐字副本，**Cashew 全量导出形态为合成**）
- [x] 1.6 显式声明**不内置来源**：随手记 / 京东金融 / 各银行流水（一手表头查证不到，设计 D6），并各留一条「走 `custom` 手选列」用例证明该路径可用

## 2. 新文件 `backend/tests/test_csv_import_boot3_e2e.py`（HTTP 端到端，不重复 M1/M2 纯函数断言）

- [x] 2.1 **需求 A**：无表头型（`1,2,3` 三列 + 数据行）→ 手选 `columns` → 成功入库；任意中文自定义表头（`日期,花费,说明`）→ 手选 `columns` → 成功入库
- [x] 2.2 **需求 B**：五方言逐一命中且入库结果符合该方言预设（native 同名映射、cashew 的 `income` 布尔 + 负数【§1.3 合成夹具，表头逐字原文】、cashew_template 的符号法【§1.1 夹具】、alipay 的 `交易分类` 自动映射、wechat 的 `fallback_category`）
- [x] 2.3 **需求 C 净效果（本模块独有价值，不得用纯函数断言替代）**：导入含脏形态的**合成行**后，**从读取侧断言**
  - [x] 2.3.1 `GET /api/records` 按 `start_date/end_date` 月份过滤能命中该记录（`record_service.py:98-105` 字符串区间比较）
  - [x] 2.3.2 `GET /api/statistics/trend?granularity=month` 的月份键为合法 `YYYY-MM` 且金额进桶（`statistics_service.py:181-207` 的 `strftime`）
  - [x] 2.3.3 `GET /api/budgets` 当月预算的 `spent` 含该记录（`budget_service.py:71-83` + `substr(...,1,7)`，:177-193）
  - [x] 2.3.4 断言库内 `consume_time` 全部满足 `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$`（脏日期入库即失败——现状 `2024/01/15` 可原样入库，本批收口）
- [x] 2.4 **需求 D**：`export_csv` → preview → confirm 闭环，断言 `imported_count == 导出行数`、金额/日期/分类名逐条一致；断言全流程响应中**不出现**「无法识别」文案
- [x] 2.5 三态收支净效果：微信夹具里 `不计收支`、**一手实测的 `/` 中性交易值**（D31）、`中性交易` 行不入库、`支出`/`收入` 各归位；`skipped_reasons.type_ignored` 计数与夹具行数吻合（`/` **不得**落进 `type_unresolved`）
- [x] 2.6 标签净效果：**合成**同 `tag_name` 多行（沿用 §1.1 模板的 6 列表头，把两行 `Title` 写成同一个值——真实模板只有两行且 Title 各异，不能直接用来验这条）→ `tags` 表**仅新增一行**、两条记录共享同一 `tag_id`（M3 §2.10 的端到端证据）；另断言真实模板的两行 Title 各建一标签（`Fruits and Vegetables` / `Monthly Income`）
- [x] 2.7 幂等边界登记：同一文件二次导入 → 记录翻倍（**现状行为，D20 不修**，用例断言该事实并注明「已知边界」，防后来者误判为 bug）
- [x] 2.8 零 DB 触碰：用例一律 tmp_path / 既有测试夹具库；`backend/money.db` 全程只读
- [x] 2.9 **需求 E（Excel 容器端到端，本模块收口 M6 的用户可见效果）**
  - [x] 2.9.1 §1.3b 的合成镜像 xlsx → `preview` 返 `code==0` + `container=="xlsx"` + `format=="wechat"` + `header_row_index==17`；`confirm` 带 `fallback_category` → 入库条数 == 夹具数据行数（中性 `/` 行除外）
  - [x] 2.9.2 **读取侧净效果**：xlsx 里的 serial 日期入库后 → `/api/records` 月份过滤命中、`/api/statistics/trend` 出现合法 `YYYY-MM` 键、`consume_time` 全量满足 §2.3.4 的正则（证明容器层换算真的贯通到读取侧，不只是写进去）
  - [x] 2.9.3 失败面三条：OLE `.xls` 字节（合成 magic 前缀即可）、`PK` 开头但缺 worksheet entry 的 zip、**超限**（用 `monkeypatch` 把 `xlsx_reader.MAX_ENTRY_BYTES` 调小覆盖，**不改生产常量、不真造 50 MB 文件**）→ 各自 `code != 0` 且 `message` **逐字等于** D27/§6.4 的中文文案
  - [x] 2.9.4 **反向护栏**：以上全部响应（含成功与失败）的 `message` 中**不得出现** `new-line character`、`_csv.Error`、`BadZipFile`、`UnicodeDecodeError` 等英文内部异常串（§0.4-14 的收口证据）
  - [x] 2.9.5 不重复 M6 §4 的纯函数断言（本模块只走 HTTP 端到端）
- [x] 2.10 **前后端契约一致性（P3 的终验兜底，防 mock 与真实载荷漂移）**：在 e2e 内**只读**前端源码 `frontend/src/pages/SettingsImportExportPage.vue`（`Path(__file__).resolve().parents[2] / "frontend/src/pages/SettingsImportExportPage.vue"` 读文本 + 正则提取 `handleCsvImport` 请求体对象的键集合——pytest 的 cwd 是 `backend`（`pyproject.toml` 只配 `testpaths=["tests"]`，无路径魔法），**仓库根必须由 `__file__` 推导，不得写相对路径**；**不引入前端依赖、不改任何前端文件**），与后端 `ImportCsvRequest.model_fields.keys()` 比对：断言前端发出的键 ⊆ 后端字段集，且本批三个新字段 `columns` / `type_source` / `fallback_category` **两侧逐字同名**；若前端文件不可读或正则提取为空 → 用例**显式 fail 并给出中文断言消息**，**禁止 skip 蒙过**（skip 等于这条护栏不存在）。编号追加在 §2.9 之后是刻意的——**不改写 §2.9**，以免打断 M6 §4.11 与 progress.md 对「M5 §2.9」的既有引用

## 3. README（`README.md`）

- [x] 3.1 Version History 表（:243 起）追加 **v1.4.3-boot3** 行，一句话概括：CSV 导入通用列映射、五方言别名、值清洗归一、**真实微信/支付宝 `.xlsx` 账单直读**、自家导出回导修复
- [x] 3.2 **按项目版本策略**：只写 Version History 一条，**不在 Features 段加版本块**
- [x] 3.3 「导入导出」相关正文补一小段中文须知（放在 Quick Start / Project Structure 之后的合适正文位置，不新增一级章节）：前导说明自动跳过、无分类列需选「账单归入」、`不计收支` **与 `收/支` 列为 `/` 的中性交易行**不导入、不支持 `09/24/2026` 型歧义日期、**重复导入不去重**、**微信/支付宝导出的 `.xlsx` 可直接上传，老 `.xls` 请先在 Excel 里另存为 `.xlsx` 或 `.csv`**
- [x] 3.4 API Overview（:177 起）不变（本批无新端点）

## 4. progress.md 收口段

- [ ] 4.1 发布备忘登记：**零迁移、零 DB 变更、回退 = 换回旧后端 + 旧 dist**；与 boot2 发布窗口的关系按设计附录 A 的 **2026-09-24 实测更新**登记（现场库已具 v1.4.3 + dormant 形制、分类已归并，`foreign_key_check` 余 52 条 tags 孤儿继续沿 boot2 条目跟踪；**成因不追查**，开工时只读复测）
- [ ] 4.2 冒烟四条：导出→导入条数一致；模板 `-50`→支出 / `250`→收入；任意中文表头手选列能入库；**合成镜像 `.xlsx` 全链路入库 + `.xls` 得到中文另存提示**
- [ ] 4.3 待人工抽检清单落表（子 Agent 不勾选）：
  - [ ] 4.3.1 **真实支付宝账单**导入一次（合成夹具无法替代；验证前导行数漂移、GBK 系编码、`/` 占位）——**本会话无该文件，不得声称已验证**
  - [ ] 4.3.1b **真实微信 `.xlsx` 本机对照导入一次**（用户 2026-09-24 已提供一手文件 → 由**主 Agent 在 P4 亲执**：预览须判 `wechat` + `container=xlsx`、必选「账单归入」、228 行中 4 笔中性交易不入库、金额与月份正确；结论与截图登记，标注「本机对照，非 CI 证据」）
  - [ ] 4.3.1c **用户自助路径验证**：在 Excel 里把该 `.xlsx` **另存为 CSV** 再导入一次，登记实际得到的日期形态（文本/序列号）与编码，确认 D14/D15 口径下不误收脏日期
  - [ ] 4.3.2 真实微信账单**CSV** 形态（若用户日后拿到 CSV 导出）：验证 `交易对方`→标签 的数量上升是否可接受、`¥` 金额
  - [ ] 4.3.3 真实浏览器文件选择 → 映射向导三区块走完 → 记录出现在账单页与月统计
  - [ ] 4.3.4 明暗 × 竖屏/宽屏观感截图（列角色表 + 样例行表格）
  - [ ] 4.3.5 Cashew App 内用官方模板实际导出一次，验证我方是否吃下其真实列集（合成依据仅调研，未一手核对官方仓库）
- [ ] 4.4 已知边界登记（不修不扩围）：D15 歧义日期、D20 无去重、微信标签数量上升、大文件逐行 flush、`preview_csv` 的 `db` 形参未使用、`CategoryMappingItem.type` 字段空转；**xlsx 侧**——多 sheet 只取第一个非 hidden、老 `.xls` 不支持（仅给另存指引）、支付宝 `.xlsx` 形态未一手核对、D27 的 50/200 MB 上限为经验值不做到场校准
- [ ] 4.5 包体增量对比（dist gzip vs boot2 基准 `+127 B`）落表，供人工裁定

## 5. 验收门槛（本模块 = 全批终验的输入）

- [x] 5.1 新 e2e 文件全绿 + 既有全量 pytest 绿；`mypy`/`ruff` 基线零新增
- [ ] 5.2 六命令全绿（`pytest` / `vitest` / `mypy` / `ruff` / `eslint` / `vite build`）由主 Agent 终验复跑，本模块只需自证 e2e 绿
- [x] 5.3 pathspec 精确提交：`backend/tests/test_csv_import_boot3_e2e.py`、`README.md`、`doc/tasksv1.4.3boot3/progress.md`

**验收标准（设计 §5.2）**：**五**条子需求各有端到端断言（E 走 §2.9 的「结构镜像 + 数据全合成」xlsx）；**且 §2.10 的前后端 `columns` 载荷一致性断言在场（P3 终验兜底）**；需求 C 的证明出现在**读取侧**（统计/列表/预算三处），而非只在写入侧；合成与实证素材的性质在测试文件与 progress.md 双处登记，后来者不会把夹具当真实账单。

---

## 执行状态说明（M5 子 Agent，2026-09-24）

**已交付**：新增 `backend/tests/test_csv_import_boot3_e2e.py`（29 例全绿：§1.6 一条 + §2.1 两条
+ §2.2 五条 + §2.3 四条 + §2.4/§2.5/§2.6×2/§2.7/§2.8+§2.9.5 护栏一条 + §2.9 十条 + §2.10 三条）；
`README.md` 只改 Version History 一行 + 「账单导入须知」一小段（Features 段未加版本块，API Overview
表未动）。全仓 `pytest tests/ -q` = **632 passed / 0 failed / 0 skipped**（基线 603 + 本文件 29）；
`mypy app` = **85 errors / 14 files**（工作区基线零新增）；`ruff check app tests` = All checks passed；
现场库 SHA256 逐字未变。

**未勾项 = 归主 Agent 的两类，逐条理由**：

1. **§4.1 / §4.2 / §4.3 / §4.4 / §4.5 全部未勾**：本批纪律「`progress.md` 仅主 Agent 读写」
   （且派单简报把 `progress.md` 列入禁触清单）→ 子 Agent 不写该文件，**§4 的内容以下列原文交接给
   主 Agent 直接落进 progress.md**：
   - **§4.1 发布备忘**：零迁移、零 DB 变更、回退 = 换回旧后端 + 旧 dist；与 boot2 发布窗口的关系按
     设计附录 A 的 2026-09-24 实测更新登记（现场库已具 v1.4.3 + dormant 形制、分类已归并，
     `foreign_key_check` 余 52 条 tags 孤儿继续沿 boot2 条目跟踪；成因不追查，开工时只读复测）。
   - **§4.2 冒烟四条**：① 导出→导入条数一致（已由 `test_2_4_own_export_reimports_without_any_unknown_format_message`
     自动化）；② 模板 `-50`→支出 / `250`→收入（`test_2_2_cashew_template_dialect_uses_sign_preset_on_real_fixture_copy`）；
     ③ 任意中文表头手选列能入库（`test_2_1_arbitrary_chinese_header_imports_after_manual_columns`）；
     ④ 合成镜像 `.xlsx` 全链路入库 + `.xls` 得到中文另存提示（`test_2_9_1_*` / `test_2_9_3_xls_*`）。
     **四条均已端到端自动覆盖**，人工冒烟可选做。
   - **§4.3 人工抽检清单**（子 Agent 不勾，P4 由主 Agent 亲执）：4.3.1 真实支付宝账单导入一次；
     4.3.1b 真实微信 `.xlsx` 本机对照导入一次（预览判 `wechat` + `container=xlsx`、必选「账单归入」、
     228 行中 4 笔中性交易不入库、金额与月份正确，结论标注「本机对照，非 CI 证据」）；
     4.3.1c Excel 另存 CSV 的用户自助路径；4.3.2 真实微信 CSV 形态；4.3.3 真实浏览器文件选择 →
     向导三区块 → 账单页与月统计；4.3.4 明暗 × 竖屏/宽屏观感截图；4.3.5 Cashew App 内用官方模板导出一次。
   - **§4.4 已知边界登记**：D15 歧义日期、D20 无去重、微信标签数量上升、大文件逐行 flush、
     `preview_csv` 的 `db` 形参未使用、`CategoryMappingItem.type` 空转；xlsx 侧多 sheet 只取第一个非
     hidden、老 `.xls` 不支持、支付宝 `.xlsx` 形态未一手核对、D27 上限为经验值。
   - **§4.5 包体增量对比**：需 `vite build` 重建 dist，归主 Agent 终验（本模块未碰前端）。
2. **§5.2 未勾**：六命令终验复跑归主 Agent；本模块自证范围 = `pytest`（新文件 + 全量）/ `mypy` / `ruff`。

**M5 执行期发现的两条口径（不改实现、不判缺陷，登记备查）**：

- **§2.3.2 的参数名**：任务写 `trend?granularity=month`，本仓库该端点的实参名是 `group_by=month`
  （`routers/statistics.py`，本批未新增端点）→ e2e 按现状端点契约断言，同一处读取路径无歧义。
- **「只有前导说明行、无合格表头行」的 xlsx 文案**：设计 §6.4 把该场景判给「两条通道同一处置」，
  实现走 M1 共享的 `locate_header_rows` → 得到的是既有 `CSV 文件为空`（该串被 M1 §4.5 与既有测试锁定，
  红线 4 零放宽），而 `Excel 文件为空` 只在**行矩阵本身为空**时出现。e2e 只断「中文 + `PARAM_ERROR`
  + 无英文内部异常串」，不锁死具体是哪一个文案。若产品口径要求 xlsx 侧必报 `Excel 文件为空`，
  属后续单点裁定（M5 不自行改实现）。
