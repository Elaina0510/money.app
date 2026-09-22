# Money App v1.4.3-boot2 总体进度

> v1.4.3-boot 后的跟进批次，三项用户实测反馈：① 分类管理拖拽排序完全失效（把手按压无反应）→ 任何数据态永远可拖；② 现场库仍并存「其他 / 其他支出 / 其他收入」→ 数据归并为单一「其他」；③ 新增预算「包含模式至少需 1 个分类」限制去除 → 不选=动态全部分类，分类删光转休眠保留。
> 需求原文即详细设计三章（无独立需求文档）　详细设计：`doc/detailed-designv1.4.3boot2.md`
> 任务拆解：每模块一个文件（见模块清单链接），子任务以 checklist 表示完成状态。

---

## 模块清单（3 个，与需求三节一对一）

- [x] [M1 - 分类拖拽排序永远可用](m1-category-drag-always-on.md) —— 需求一（前端去禁用 + 后端 reorder 家族置尾归一 + 根因复核）✅ `045dc45`
- [x] [M2 - 「其他支出 / 其他收入」归并入「其他」](m2-merge-other-categories.md) —— 需求二（一次性迁移脚本，幂等，零运行期代码）✅ `3692f20`
- [x] [M3 - 预算「不选=全部」+ 删光转休眠](m3-budget-dynamic-all-dormant.md) —— 需求三（Budget.dormant + 校验放开 + 级联改向 + 前端置灰）✅ `ddc68f3`（M3b 后端半区 + M3f 前端半区，整模块一次性提交）

## 开发顺序（设计附录 A）

```
M1 → M2 → M3
```
- 每模块独立提交、独立测试全绿后进入下一模块。
- M1/M2 无功能依赖但同「家族」字面常量：先 M1 定表、M2 脚本侧钉一致性断言。
- M3 与 M1 共享 `category_service.py`（不同函数区域）：串行避开冲突。

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `backend/app/services/category_service.py` | M1、M3 | M1 改 `_is_other_category`/`_next_sort_order`/`reorder_categories`；M3 改 `_cascade_budgets_for_deleted_category`（→`_dormant_...`）及两处调用返回字段；区域无交叉，**串行 M1 → M3** |
| `backend/tests/test_categories_reorder.py` | M1 | 独占 |
| `backend/tests/test_budgets.py` | M3 | 独占 |
| `frontend/src/pages/SettingsCategoriesPage.vue` | M1 | 独占 |
| `frontend/src/pages/SettingsSubPages.test.js` | M1 | 独占 |
| `frontend/src/pages/StatisticsPage.vue` | M3 | 独占 |
| `frontend/src/pages/StatisticsPage.test.js` | M3 | 独占 |
| `backend/migrate_to_v1.4.3boot2_categories.py`（新增） | M2 | 独占 |
| `backend/migrate_to_v1.4.3boot2_dormant.py`（新增） | M3 | 独占 |
| `backend/app/models/budget.py`、`schemas/budget.py`、`routers/budgets.py`、`routers/categories.py`、`budget_service.py` | M3 | 整文件级独占 |

## 已确认设计决策（实现约束，设计 §0.3）

**用户已裁定（2026-09-22）：**

| # | 决策 | 落点 |
|---|------|------|
| D1 | 症状=拖拽把手完全无反应；修复=任何数据态永远可拖、「其他」前后端归一化强制置尾，删「非末位即整体禁用」锁定 | M1 |
| D2 | 需求二=新一次性迁移脚本 + 运行期兼容；M1 判据临时兼容旧名，保证迁移执行前也不卡死 | M1/M2 |
| D3 | 需求三「不选=全部」=动态全部 + 休眠标记；`budgets` 新增 `dormant` 列区分两空集 | M3 |
| D4 | 休眠处置=保留记录、置灰展示、可恢复；不再沿用「最后关联删除→预算删除」级联 | M3 |

**设计裁定（实现不得发散）：**

| # | 决策 | 落点 |
|---|------|------|
| D5 | 动态全部花费口径=与 exclude 空排除集完全同口径（当月全部支出不扣除，含未分类桶）；不另立第二口径 | M3 |
| D6 | 家族={其他支出,其他收入,其他}；置尾时家族整体移末尾、内部固定名次 其他支出<其他收入<其他；前后端同规则 | M1 |
| D7 | 仅「其他」无把手占位；旧名两行照常给把手可拖（迁移前过渡态，不特判） | M1 |
| D8 | 删除后端 reorder「必须有其他行」硬校验（防漏位已由 ids 全量匹配覆盖） | M1 |
| D9 | `dormant` 只由分类删除级联置 1；create/update 任何成功保存一律落 0（主动保存=唤醒，无独立唤醒接口） | M3 |
| D10 | 月/年汇总一律剔除 dormant；预算列表接口仍返回 dormant 行（供置灰） | M3 |
| D11 | 两脚本各自幂等、可单独执行、互不依赖；**dormant 脚本必须先于新版后端启动**；现场库未跑 v1.4.3 迁移仍可直接执行 | M2/M3 |
| D12 | mypy/ruff 基线零新增；`frontend/dist` 不随模块提交、终验统一重建；明暗 × 竖/宽屏逐模块自查 | 全批 |

## 全局红线（各模块共同遵守，设计 §0.6）

- **先隔离复现再碰真实数据**：M1/M2 涉及现场库取证一律用副本沙盒；迁移执行前置检查 + 备份要求写入发布备忘。
- 不回退已验收项：v1.4.3 M8 分类收支共用单列表、§8.2「其他」置尾恒等式、v1.4.3 M12 预算两泳道互斥校验、boot M9 拖拽动画参数——本批只放宽，不改正常态表现。
- 前端单测沿用 `?raw` 源码断言手法；`appStore.showToast` 为唯一 toast 通道。
- 迁移脚本三件套惯例：幂等可重入、执行前后输出统计摘要、单测在临时库副本上跑「现场形态」夹具。
- 零新增依赖（前后端）；不触碰 vuedraggable/sortablejs 既有参数。

## 发布备忘 · 发布窗口操作序（现场库，设计附录 A）

- [ ] 1. **备份现场库文件**（项目红线，操作前必做）
- [ ] 2. 停服 → 执行 `migrate_to_v1.4.3boot2_dormant.py`（**必须先于新代码启动**，D11）→ 执行 `migrate_to_v1.4.3boot2_categories.py`（两者顺序可换、可单独重跑）
- [ ] 3. 部署新前后端（`frontend/dist` 终验统一重建，D12）
- [ ] 4. 冒烟：分类拖一次排序、看「其他」单行末位；建一条不选分类的预算
- [ ] 5. 登记遗留：`migrate_to_v1.4.3.py` 仍未执行（UNIQUE 换形/重排阶段与本期脚本互不冲突，§2.2.3），继续留原发布备忘跟踪

## 终验清单（质量门，设计附录 A）

- [ ] `pytest` 全绿（新增 M2 迁移组 + M1/M3 改写用例，只增不减）
- [ ] `vitest` 全绿（M1 SettingsSubPages / M3 StatisticsPage 组改写 + 既有回归）
- [ ] `mypy`（基线零新增口径）+ `ruff` 全绿
- [ ] 前端 `npm run build` 成功 + `frontend/dist` 统一重建（gzip 与 v1.4.3-boot 对比，本批预期增量小）
- [ ] 明暗两主题 × 竖/宽屏两形态逐模块人工自查（各模块 §验收门槛 人工项）

## 进度统计

| 模块 | 层 | 状态 | 完成 commit | 备注 |
|------|----|------|-------------|------|
| M1 | 前端 + 后端（category_service） | ✅ 完成 | `045dc45` | 守门先行；pytest 252+1skip / vitest 390 / mypy 基线零新增 / ruff·eslint 绿；主 Agent 复跑核验通过 |
| M2 | 后端（迁移脚本 + 测试） | ✅ 完成 | `3692f20` | 泳道1；pytest 294+0skip / mypy 基线零新增 / ruff 绿；P3 断言自动转绿（未编辑 test_categories_reorder.py）；主 Agent 复跑核验通过 |
| M3 | 后端（模型/服务/路由/脚本）+ 前端（统计页） | ✅ 完成 | `ddc68f3` | 泳道2；M3b 后端半区 + M3f 前端半区整模块一次性提交；pytest 294 / vitest 397 / mypy 90 基线 / ruff·eslint 绿；主 Agent 复跑 + P4 实测核验通过 |

## 模块执行记录

### M1（done · `045dc45` · fixed_rounds 0 · 32/35 勾选，余 3 项人工/发布窗口）
- **P2 副本取证**：现场库 SHA256 复制前后一致（`f8e0c5de…`，原件未动、只读连接、未回写），副本形态与分支 A 逐条一致：「其他」id=34 sort=14，旧名「其他支出」id=9 /「其他收入」id=14 均 sort=99 压后 → 「其他」非末位 → 旧 `isOtherLocked` 恒真整列表禁用（user1/user3 可见集同形）。无需走 B/C 分支。
- **改动**：前端删 `isOtherLocked` + `:disabled`，把手条件收口 `cat.name !== OTHER_CATEGORY_NAME`（D7），`onDragEnd`→`normalizeTail`（D6 与后端逐位一致）；后端家族常量定表 + `_is_other_category`/`_is_other_row` 判据放宽三名、`reorder` 删「缺其他→ValueError」（D8）改家族名次稳定置尾、`_next_sort_order` 钳家族最小 sort + 0 下钳、`update_category` 禁改名收窄「其他」本名；回滚链路与 store 零改动。
- **附录 B 改写**：`test_categories_reorder.py`（含反转组、三名乱序尾段固定、三态钳制、旧名可改名/「其他」仍锁、M2 常量一致性占位）、`SettingsSubPages.test.js`（把手 ?raw 红线 + disabled undefined、isOtherFamily/isOther 真值表、normalizeTail、现场形态夹具）。全部替换断言新口径，零删除零放宽。
- **主 Agent 核验增补**：本模块额外改 `backend/tests/test_categories.py`（5 例，任务涉及文件未点名）——经复核为 M1 `_next_sort_order` 家族钳制对夹具旧名行的**合法行为涟漪适配**（断言转严、加无家族态前置、仅调 sort 绝对值维度、注释同步），非放宽；沙盒仅内存库、未碰真实 money.db。
- **5.4 占位手法**：M1 用「探测脚本文件存在即 skip、存在则按路径加载做双侧常量实断言」替代 importorskip（后者对含点号文件名抛 SyntaxError 不生效）；M2 落文件后**自动**转实断言，P3 闭环终验核验。
- M9 flip 组（3 例含 :1763 零闪回）整组复跑通过；vuedraggable/sortablejs 参数一字未动。

### M2（done · `3692f20` · fixed_rounds 1 · 19/21 勾选，余 4.2/4.3 人工）
- 新增 `backend/migrate_to_v1.4.3boot2_categories.py`（433 行）+ `test_migration_v143boot2_categories.py`（18 用例，tmp 文件库现场形态夹具）。分桶归一 keeper 优先级 `其他>其他支出>其他收入`、先删 loser 再改名、重定向 `records/quick_templates/budget_categories`（+去重 `deduped_references`）逐表探测缺表跳过、置尾幂等、单事务失败回滚、统计 `merged_rows/redirected_references/tail_fixed`。零运行期代码、`app/main.py`/`category_service`/前端 `constants.js` 零改动。
- **P3 闭环**：脚本落地后 `test_categories_reorder.py::test_other_family_rank_matches_m2_script_constants` **自动 skip→实断言通过**，M2 **未编辑该他模块文件**（提交仅 3 文件）；双向 ⊇/⊆ 常量钉 + KEEPER_PRIORITY + icon 对齐落在 M2 自己的新测试文件。
- 幂等（二次统计全 0 + snapshot 一字不差）、环境变体两组（旧 UNIQUE 形 / 缺 budget_categories 表）、顺序收敛双向（v1.4.3↔boot2 真跑 tmp 库均收敛）全覆盖。
- 主 Agent 复跑：全量 pytest 294 passed / **0 skipped**（P3 转实断言的硬证）、mypy 90 基线、ruff clean。money.db SHA256 复核不变。

### M3b（后端半区 · 工作区未提交，待 M3f 整模块提交 · fixed_rounds 1 · 32/32 后端勾选）
- 落盘 7 改（`models/budget.py` dormant 列 / `schemas/budget.py` / `routers/budgets.py` / `routers/categories.py` 休眠文案 / `budget_service.py` 校验删+`_build_detail` 四分支+响应 `dormant`+月概览 `get_budget_overview`+年汇总 `get_year_summary` 剔除+create/update 落 0 / `category_service.py` **仅级联区**更名 `_dormant_budgets_for_deleted_category`+`dormant=1`+返回键 `dormant_budgets`）+ 2 新（`migrate_to_v1.4.3boot2_dormant.py` 缺列 ALTER+backfill+D11 头注释、其测试 10 用例四态）+ 改 `test_budgets.py`（40→53 用例，零删除，含 8.1/8.3/8.12 口径反转）。
- 主 Agent 复跑核验：全量 294 passed、M3 组 63 passed、mypy 90 基线（M3b 报「92」系观测 M2 编辑瞬时，终态净 90）、ruff clean；工作树仅 7 改+2 新，**零前端文件**（M3f 领地正确留白）。`_build_detail` 分支序 dormant→INCLUDE空→INCLUDE显式→exclude 逐行核对，D5（INCLUDE空集 spent=month_total 与 exclude 空排除集同值）实证。
- **M3b 合理偏离（记录，属行号/标识符定位与新语义）**：① `dormant` 用本文件 SQLModel `Field(sa_column=Column(Integer,NOT NULL DEFAULT 0))` 而非 `Mapped[int]`（全文无 Mapped 惯例，列形等同）；② 仓内无 `BudgetDetail` pydantic 类，响应契约为 `_build_detail` dict，故 dormant 落该 dict（不新建类、不扩面）；③ SQLite DDL 即时提交 → §1.4「单事务」如实改为「失败终态=列已加未回填（良性漏标，动态全部渲染、编辑保存归位）」+ 只读 `_warn_if_unbackfilled`（绝不改写）、无回滚开关；④ backfill 加只读探测（无 scope_mode 列 / 缺 budget_categories 表 → 加列但 backfilled=0 记 `skipped_reason`）；⑤ 现场库副本实测正是该极旧形（budgets 8 列无 scope_mode，6 行）→ 演练加列 1 / backfilled 0 / 二次 no-op / integrity ok。
- **⚠️ 登记关注（M3b 上报，越出 M3 涉及文件清单，本期不扩围修）**：`app/services/export_service.py:182-201` budgets 导出列集合硬编码 8 列、**不含 `dormant`** → 备份→还原后休眠行会以 `dormant=0`（动态全部）回归。现有导出/导入往返用例全绿、不影响本期门槛。列入交付报告「遗留关注」，是否补列留人工/后续批次裁定。

### M3f（done · 整模块 `ddc68f3` · fixed_rounds 1 · 前端 13 项勾选）
- 前端 `StatisticsPage.vue`：删 `budgetIncludeEmpty`→`budgetFormValid` 牵连 + `budgetScopeError` 红字/渲染节点（include 空选可保存）；label/`budgetScopeTip` 新文案「一个都不选即统计全部分类支出」；`isDormant` 单点、`budget-card--dormant` 仅 `opacity:.55` 一档（明暗通用、零新色值）、chip「保留」、`scopeSummary`/`scopeHint` 前端自出、进度条恒 0、明细钮靠空数组自然隐藏；`totalBudget/totalSpent` 求和前 `filter(!isDormant)`；`openBudgetEditDialog` 零特殊回填。`StatisticsPage.test.js` +7 用例（390→397）。
- 对接确认：严格以响应 `dormant` 键判休眠（不由 include 空集自推）；全仓无 `deleted_budgets` 前端引用；未改一行 M3b 后端。
- **合理偏离（记录）**：`scopeSummary`/`scopeHint` 的 **include 空集非休眠** 分支由旧「未知分类」只读态改为「全部分类 / 统计全部分类支出（含后续新增分类）」，与后端 8.12 同向——否则 9.2 出现「花费=当月全额、覆盖却写未知分类」自相矛盾。

## 终验记录（§6.2，主 Agent 亲执，基线 HEAD `a90e102`）

**六命令全绿（终验提交前）：**
| 命令 | 结果 | 对照 |
|------|------|------|
| `npm test` | 397 passed (15 files) | 基线 389，只增不减 |
| `npm run lint` | 0 errors / 2 warnings | 基线同形（CsvMappingDialog） |
| `npm run build` | 成功 | dist 重建 535,537 B gzip，**+127 B / +0.12 KB**（预期增量小 ✅） |
| `pytest tests/` | 294 passed, 0 skipped | 基线 245+… ，P3 §5.4 由 skip 转实断言（0 skipped 硬证） |
| `mypy app/` | 90 errors / 14 files | 基线零新增 |
| `ruff check app/ tests/` | All checks passed | 基线 clean |

**跨模块闭环核验：** ✅ `test_categories_reorder.py::test_other_family_rank_matches_m2_script_constants` 为实断言（pytest 0 skipped）；✅ `migrate_to_v1.4.3boot2_dormant.py` 头含 D11 执行窗口注释；✅ `routers/categories.py` 文案含 `dormant_count>0` 休眠分支（M=0 不提）。

**money.db 原库保护复核：** 终验全程后 SHA256 仍 `f8e0c5de303c46f4…`，与开工登记逐字一致（未动、未 `git add -f`、`.p4sandbox` 内 *.db 被 `*.db` ignore、演练后已删）。

**P4 浏览器实测（副本演练 + 三链路）——环境受限，如实登记：**
- 本会话 in-app browser **无可见视口**（viewport 0×0，`visibilityState=hidden`）→ `take_screenshot` 与 pointer 类动作（click/**真实指针拖拽**）被系统拒绝。故**未能产出 `screenshots/v1.4.3-boot2/` 截图，也未做真实指针拖拽**；此两项连同明暗×竖/宽屏观感一并留**人工真机终判**。未以 DOM 绿虚构「拖拽已真机验证」。
- **已取得的运行态实证（browser DOM 快照 + 副本/新库 HTTP 端到端）：**
  - **M1**：现场副本经两脚本后，前端分类页实渲 14 行、**13 个 `.drag-handle` + 1 个 `.drag-handle-placeholder`（仅「其他」）、拖拽列表无 disabled 属性**（锁已去，D7 把手规则成立）；HTTP reorder 把「其他」放中部提交 → 200 且落库「其他」归一到末位、非家族保持提交序。
  - **M2**：现场库**副本**发布窗口序演练——dormant（加列/backfill 探测跳过，因库为 pre-v1.4.3 无 scope_mode）→ categories（三家族行归并为单「其他」keeper id=34、其他支出/收入计数=0、records 重定向至 keeper、`foreign_key_check` 违规数与原库同为 70 即**新增 0**）；浏览器分类页确认单「其他」置尾、无旧名行。
  - **M3**：当前 schema 新库 HTTP 端到端——D5 dynamic-all(include 空) spent==exclude(空)当月总额 100.0；7.1 新建分类并记账后 dynamic-all **免重存自动计入**（100→150）；删唯一关联分类 → 响应 `dormant_budgets≥1`、预算**仍在列表** + `dormant=true` + spent=0 + details=[]；年汇总 total 777→0（**D10 剔除休眠**）同时月列表仍返回该行；PUT 重保存 → dormant 清 0（**无独立唤醒接口**）。
- **现场库限制登记（重要，非本批缺陷）**：`migrate_to_v1.4.3.py` 在该现场副本上因**既有 70 条 FK 违规主动回滚**（未跑成），故现场尚未 v1.4.3 schema、新后端预算接口在其上会 500（缺 scope_mode 列）——印证「现场未跑 v1.4.3 迁移」的历史背景；M3 实时验证改在 current-schema 新库上完成。发布时 v1.4.3 迁移需先处理既有 FK 违规（属 `migrate_to_v1.4.3.py` 自身发布议题，本批不扩围）。

## 阻塞清单

（无——三模块全部 done）

## 待人工抽检清单（子 Agent 不勾选，P4 已覆盖项标「已自动化实测」）

### M1
- [ ] 1.2 发布窗口二次确认：若服务器现场库与副本形态不同，按判定树 B/C 补查（属新信息则停，不猜）——**现场库实测**，发布窗口
- [ ] 6.2 明暗主题 × 竖/宽屏真机拖拽观感（触摸长按 150ms、鼠标即拖）、保存后无跳变、toast 文案不变——**逻辑链已由 HTTP reorder（其他归末位、非家族保序）+ DOM（13 把手/1 占位/无 disabled）实证；真实指针拖拽手势 + 明暗/宽竖观感 + 截图留人工**（本会话 in-app browser 无视口，见终验 P4 登记）
- [ ] 6.3 现场库副本实测「其他」非末位态可拖——副本迁移 + DOM 已确认渲染可拖（无 disabled）；**真实指针拖拽留人工**

### M2
- [ ] 4.2 现场库**副本**演练一次：备份 → 执行 → 前端分类页三行变一行、历史账单归类正确、预算覆盖不变——副本发布窗口序演练 + 分类页 DOM「单其他置尾、无旧名」**已完成 + 已复核重定向/FK 新增 0**；截图与历史账单肉眼归类终判留人工
- [ ] 4.3 发布备忘登记：执行序（先备份、dormant 脚本先于新代码启动、本脚本与其顺序可换可单独重跑）——已落本文件发布备忘段，人工复核

### M3
- [ ] 9.2 人工·主链路：新增预算不选分类保存 → 花费=当月总支出；新建分类并记账 → 数字自动跟上；删唯一关联分类 → 置灰「分类已删除、预算保留」、月概览不含；编辑重选 → 恢复计入——**后端链路已 HTTP 端到端实证（D5 100.0、7.1 100→150、dormant 保留+summary 777→0、PUT 唤醒）；前端置灰肉眼观感 + 截图留人工**
- [ ] 9.3 人工·明暗主题 × 竖/宽屏自查（置灰一档可读、不引新色值）——人工（本会话无视口截图）
- [ ] 9.4 不回退核验：v1.4.3 M12 预算两泳道互斥校验（scope_mode 切换多选行为）只放宽空集限制，泳道互斥本身不变——M3b/M3f 口头 + `test_scope_mode_validation` 绿灯核验，真机人工终判

## 阻塞清单

（暂无）

## 开工登记（2026-09-22，基线 HEAD `a90e102`）

> **环境事实**：项目 Python 依赖不在 PATH（裸 `python -m pytest` 报 No module）。三模块质量门槛一律使用 `backend/venv/Scripts/python.exe -m <pytest|mypy|ruff>`。前端在 `frontend/` 下用 `npm`。

| 项 | 值 | 用途 |
|----|----|------|
| `backend/money.db` SHA256 | `f8e0c5de303c46f4acae01972f299b095f2b339bc004bcc647a36231f8246405` | P2 原件未动证明（终验复核） |
| pytest 基线 | 245 passed（22 warnings） | 终验对照（只增不减） |
| mypy 基线 | Found 90 errors in 14 files（checked 51 source files） | 「基线零新增」口径对照（新增/改动函数零报错，既有 90 不要求清理） |
| ruff 基线 | All checks passed（app/ + tests/ 零命中） | 终验对照 |
| vitest 基线 | 389 passed（15 test files） | 终验对照（本批只增不减） |
| eslint 基线 | 0 errors, 2 warnings（CsvMappingDialog.vue `vue/require-default-prop` ×2） | 终验对照（既有警告不新增） |
| dist 基准 | 535,410 bytes（committed dist，assets js+css gzip 合计） | 包体增量对比（终验重建后对照） |
