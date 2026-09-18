# M6 - 预算管理迁移至统计页

> 对应需求五：预算管理从设置页完全移除，迁移到统计页；决策 D2：跟随统计页周期选择器（月视图管理所选月，年视图逐月概览 + 下钻）。
> 迁移原则：设置页整块移除（含弹窗与脚本），统计页等价重建；数据结构与 budgets CRUD 接口不变，新增一个只读年汇总聚合接口。
> 涉及文件：`backend/app/services/budget_service.py`、`backend/app/routers/budgets.py`、`backend/tests/test_budgets.py`、`frontend/src/api/budgets.js`、`frontend/src/pages/StatisticsPage.vue`、`frontend/src/pages/SettingsPage.vue`
> 依赖：无功能依赖。SettingsPage 与 M7 同文件，按 M6 → M7 串行（避免删除行号漂移）。

---

## 1. 后端：年汇总接口 `GET /api/budgets/year-summary?year=YYYY`

### 1.1 Service（budget_service.py）

- [x] 新增 `async def get_year_summary(db: AsyncSession, year: int, current_user: User | None = None) -> dict[str, Any]`
- [x] 查询：`Budget.month >= f"{year}-01"` 且 `<= f"{year}-12"`；user_id 隔离与 `get_budgets` 相同写法（有 current_user 则 `== current_user.id`，否则 `is_(None)`）
- [x] 固定输出 12 个月：`months` 数组 01→12，无预算的月份 `budgets` 为空数组、total 为 0
- [x] 每月 `total_amount/total_spent` = 该月 enriched 行求和，用 `round_money`
- [x] 行结构复用现有 `_enrich_budget(db, b, b.month)`——**易错点 7**：spent 计算传各 budget 自身 `month`，勿传查询年
- [x] 每月 `budgets` 按 `category_id` 升序（写法自选，测试可断言）

### 1.2 Router（budgets.py）

- [x] 新增 `@router.get("/year-summary")`：`year: int = Query(..., ge=2000, le=2100)`，依赖 `get_session` + `require_auth`
- [x] 返回 `success_response(data=...)`（结构：`{ year, months: [{ month, total_amount, total_spent, budgets }] }`）
- [x] 声明在文件内 `/{budget_id}` 路由之前（防御未来 GET 冲突）

### 1.3 后端测试（pytest，test_budgets.py 沿用内存库 fixture）

- [x] 用例 1：固定返回 12 个月、顺序 01→12
- [x] 用例 2：各月 total 等于该月 budgets 求和；`spent` 与按月 `GET /api/budgets` 一致（口径回归）
- [x] 用例 3：数据隔离——跨用户不可见
- [x] 用例 4：`year` 缺失/非法 → 422；未认证 → 401
- [x] 用例 5：无任何预算 → 12 个空月份，不报错

## 2. 前端：API 层

- [x] `frontend/src/api/budgets.js` 新增 `getBudgetYearSummary(params)`：`request.get('/budgets/year-summary', { params })`

## 3. 前端：StatisticsPage.vue 预算区块

### 3.1 周期联动状态

- [x] 新增 computed：`budgetMonth`（`dayjs().add(periodOffset, 'month').format('YYYY-MM')`）、`budgetYear`（`dayjs().add(periodOffset, 'year').format('YYYY')`）
- [x] 新增 computed：`budgetMonthLabel`（`budgetMonth` 按 `YYYY年M月` 格式化，供概览卡文案使用）
- [x] 新增 refs：`budgets`（月视图明细）、`yearMonths`（年视图 12 月概览）、`budgetLoading`
- [x] 新增 `loadBudgets()`：monthly → `getBudgets({ month: budgetMonth })`；否则 → `getBudgetYearSummary({ year: budgetYear })` 取 `months`；try/catch/finally 按设计 §6.2.1
- [x] `loadData()`（现 :294-309）扩展并发加载预算；`prevPeriod/nextPeriod/switchPeriod` 触发时随周期一起刷新

### 3.2 月视图 UI（等价迁移 + 跟随所选月）

- [x] 区块位置：收支趋势卡片（现 :108-122）之后、页面最后一个 `v-card`；外壳 `v-card pa-4 mb-3 settings-card rounded="xl"` + `mdi-piggy-bank-outline` 紫色头像
- [x] 头部：标题"预算管理" + 「设置」按钮（`openBudgetAddDialog`）
- [x] **易错点 6**：新增预算写入月份 = `budgetMonth.value`（当前所选月），非系统当前月——`saveBudget`/`saveBudgetEdit` 的 `month` 参数同步替换
- [x] 概览卡（等价 SettingsPage :335-351）：文案 `{{ budgetMonthLabel }} 预算`（`YYYY年M月`），数值取迁移来的 `totalBudget/totalSpent/budgetUsagePercent` computed 组（:782-795）
- [x] 分类预算列表（等价 :353-420）：行内编辑（笔/勾/叉 + `updateBudget`/`batchSetBudgets`）、删除入口、进度条阈值配色（>80% error / >50% warning / 其余 success|primary）原样搬运
- [x] 随块迁移函数：`startBudgetEdit/cancelBudgetEdit/saveBudgetEdit/getBudgetColor/availableBudgetCategories`（分类来自 `useCategoriesStore`，type==='expense' 排除已有预算项）、`BUDGET_COLORS` 常量
- [x] Budget Add Dialog（:423-451）整体搬到 StatisticsPage 模板尾部，`budgetForm.month` 取 `budgetMonth.value`

### 3.3 年视图 UI（逐月展开概览，决策 D2）

- [x] 头部摘要：`{年} · 预算 ¥Σtotal_amount · 已用 ¥Σtotal_spent`；无「设置」按钮
- [x] 月份行：`M月` + 迷你进度条（`total_spent/total_amount`，阈值配色同月视图）+ `¥total_spent / ¥total_amount`
- [x] `total_amount === 0` 的月显示"暂无预算"弱文本行
- [x] 行点击下钻：`periodType='monthly'`、`periodOffset = dayjs(month + '-01').diff(dayjs().startOf('month'), 'month')`、`loadData()`
- [x] 年视图不提供新增/编辑/删除（数据模型以月为粒度）
- [x] 全部月份无预算：一行空态文案"该年暂无预算设置"

## 4. 前端：SettingsPage.vue 移除清单（设计 §6.3）

- [x] 删预算管理卡片（概览+列表+编辑，:319-421）
- [x] 删 Budget Add Dialog（:423-451）
- [x] 删脚本 refs：`budgets/showBudgetAddDialog/savingBudget/editingBudget/editBudgetAmount/budgetForm`（:760-766）、`currentMonth`（:767）
- [x] 删 computed：`totalBudget/totalSpent/budgetUsagePercent/enrichedBudgets/availableBudgetCategories`（:782-800）
- [x] 删函数：`getBudgetColor/loadBudgets/startBudgetEdit/cancelBudgetEdit/saveBudgetEdit/openBudgetAddDialog/saveBudget`（:970-1031）
- [x] `onMounted` 的 `Promise.all`（:1090）移除 `loadBudgets()` 调用
- [x] 移除 `import { getBudgets, batchSetBudgets } from '@/api/budgets'`
- [x] 移除 `import { formatAmount } from '@/utils/format'`（grep 核实 :337/:348/:400/:401 四处使用全在预算区块后再删）
- [x] 移除 `BUDGET_COLORS` 常量（已随块迁至 StatisticsPage）
- [x] grep 校验：SettingsPage 内无 `budget|Budget` 残留，**设置页不留任何预算入口**（需求验收 1）

## 5. 测试（vitest，新增 StatisticsPage 用例）

- [x] 用例 1：默认月视图 → `getBudgets` 以当前年月被调用，渲染概览 + 列表
- [x] 用例 2：`prevPeriod` 到上一年 12 月 → `getBudgets` 参数随 `budgetMonth` 变化
- [x] 用例 3：切「年」→ 调用 `getBudgetYearSummary`；行点击切回月视图且 offset 指向该月
- [x] 用例 4：进度条阈值配色分支（>80/>50/其他）断言

## 6. 手工验收（竖屏 375px + 宽屏 1280px）

- [ ] 设置页不再出现任何预算相关内容
- [ ] 统计页预算区块：查看、新增、编辑、删除全流程可用，功能与迁移前等价
- [ ] 进度条配色与迁移前一致（>80% 红、>50% 黄、其余绿）
- [ ] 月视图翻到 2025-03 再新增预算 → 写入 2025-03（不是系统当前月）
- [ ] 年视图逐月概览正确；点击月份行下钻到对应月视图
- [ ] 无预算用户：月视图空态、年视图"该年暂无预算设置"正常显示

## 7. 质量门槛

- [x] `cd backend && python -m pytest tests/test_budgets.py -v` 通过；全量 `pytest tests/` 回归
- [x] mypy + ruff 通过
- [x] `cd frontend && npm test && npm run lint && npm run build` 通过
