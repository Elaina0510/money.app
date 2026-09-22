# Money App v1.4.3-boot2 总体进度

> v1.4.3-boot 后的跟进批次，三项用户实测反馈：① 分类管理拖拽排序完全失效（把手按压无反应）→ 任何数据态永远可拖；② 现场库仍并存「其他 / 其他支出 / 其他收入」→ 数据归并为单一「其他」；③ 新增预算「包含模式至少需 1 个分类」限制去除 → 不选=动态全部分类，分类删光转休眠保留。
> 需求原文即详细设计三章（无独立需求文档）　详细设计：`doc/detailed-designv1.4.3boot2.md`
> 任务拆解：每模块一个文件（见模块清单链接），子任务以 checklist 表示完成状态。

---

## 模块清单（3 个，与需求三节一对一）

- [ ] [M1 - 分类拖拽排序永远可用](m1-category-drag-always-on.md) —— 需求一（前端去禁用 + 后端 reorder 家族置尾归一 + 根因复核）
- [ ] [M2 - 「其他支出 / 其他收入」归并入「其他」](m2-merge-other-categories.md) —— 需求二（一次性迁移脚本，幂等，零运行期代码）
- [ ] [M3 - 预算「不选=全部」+ 删光转休眠](m3-budget-dynamic-all-dormant.md) —— 需求三（Budget.dormant + 校验放开 + 级联改向 + 前端置灰）

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
| M1 | 前端 + 后端（category_service） | ⬜ 待开始 | | |
| M2 | 后端（迁移脚本 + 测试） | ⬜ 待开始 | | |
| M3 | 后端（模型/服务/路由/脚本）+ 前端（统计页） | ⬜ 待开始 | | |

## 模块执行记录

（执行阶段落盘）

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
