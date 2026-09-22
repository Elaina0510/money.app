# Money App v1.4.3-boot2 总体进度

> v1.4.3-boot 后的跟进批次，三项用户实测反馈：① 分类管理拖拽排序完全失效（把手按压无反应）→ 任何数据态永远可拖；② 现场库仍并存「其他 / 其他支出 / 其他收入」→ 数据归并为单一「其他」；③ 新增预算「包含模式至少需 1 个分类」限制去除 → 不选=动态全部分类，分类删光转休眠保留。
> 需求原文即详细设计三章（无独立需求文档）　详细设计：`doc/detailed-designv1.4.3boot2.md`
> 任务拆解：每模块一个文件（见模块清单链接），子任务以 checklist 表示完成状态。

---

## 模块清单（3 个，与需求三节一对一）

- [x] [M1 - 分类拖拽排序永远可用](m1-category-drag-always-on.md) —— 需求一（前端去禁用 + 后端 reorder 家族置尾归一 + 根因复核）✅ `045dc45`
- [x] [M2 - 「其他支出 / 其他收入」归并入「其他」](m2-merge-other-categories.md) —— 需求二（一次性迁移脚本，幂等，零运行期代码）✅ `3692f20`
- [ ] [M3 - 预算「不选=全部」+ 删光转休眠](m3-budget-dynamic-all-dormant.md) —— 需求三（Budget.dormant + 校验放开 + 级联改向 + 前端置灰）⏳ 后端半区 M3b 完成（工作区未提交），待 M3f 前端半区 + 整模块一次性提交

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
| M3 | 后端（模型/服务/路由/脚本）+ 前端（统计页） | ⬜ M3b 完成待 M3f | （M3f 提交） | 泳道2；M3b 后端半区工作区未提交，pytest 63 组全绿 + 全量 294，mypy 90 基线；M3f 待做前端半区 + 整模块一次性提交 |

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

## 待人工抽检清单（子 Agent 不勾选，P4 已覆盖项标「已自动化实测」）

### M1
- [ ] 1.2 发布窗口二次确认：若服务器现场库与副本形态不同，按判定树 B/C 补查（属新信息则停，不猜）——**现场库实测**，发布窗口
- [ ] 6.2 明暗主题 × 竖/宽屏真机拖拽观感（触摸长按 150ms、鼠标即拖）、保存后无跳变、toast 文案不变——P4 浏览器实测覆盖交互链（拖拽→保存→重进一致），观感留人工终判
- [ ] 6.3 现场库副本实测「其他」非末位态可拖——P4 副本演练覆盖，人工终判

### M2
- [ ] 4.2 现场库**副本**演练一次：备份 → 执行 → 前端分类页三行变一行、历史账单归类正确、预算覆盖不变——P4 副本演练 + 归并观察覆盖，人工终判
- [ ] 4.3 发布备忘登记：执行序（先备份、dormant 脚本先于新代码启动、本脚本与其顺序可换可单独重跑）——已落本文件发布备忘段，人工复核

### M3
- [ ] 9.2 人工·主链路：新增预算不选分类保存 → 卡片显示全部分类语义、花费=当月总支出；新建分类并记账 → 该预算数字自动跟上；删除该预算唯一关联分类 → 卡片置灰「分类已删除、预算保留」、月概览不含它；编辑重选分类 → 恢复计入——P4 浏览器实测覆盖该链路，人工终判观感
- [ ] 9.3 人工·明暗主题 × 竖/宽屏自查（置灰一档可读、不引新色值）——人工
- [ ] 9.4 不回退核验：v1.4.3 M12 预算两泳道互斥校验（scope_mode 切换多选行为）只放宽空集限制，泳道互斥本身不变——M3b 口头核验（`test_scope_mode_validation`/`test_nonexistent_category_rejected` 原样通过），真机人工终判
- [ ] ⚠️（关注，非验收项）export_service budgets 导出不含 dormant 列，还原后休眠行回退动态全部——本期不扩围修，见遗留关注

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
