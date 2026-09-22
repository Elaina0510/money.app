# M3 - 预算统计范围放开：不选=动态全部 + 删光转休眠（需求三）

> 对应需求三（设计 §三）。① 去除「include 空集」前后端校验——不选即统计**全部分类支出**（动态口径，后续新增分类自动计入，D3）；② 关联分类被删光的 include 预算**不再删除**，置 `dormant=1` 休眠（保留记录、置灰展示、编辑保存即唤醒，D4）；③ 汇总口径全面剔除休眠预算（D10）。
> 涉及文件：`backend/app/models/budget.py`、`backend/app/schemas/budget.py`、`backend/app/routers/budgets.py`、`backend/app/routers/categories.py`（文案）、`backend/app/services/budget_service.py`、`backend/app/services/category_service.py`（:278-328 级联区，M1 之后串行提交）、新增 `backend/migrate_to_v1.4.3boot2_dormant.py`、`frontend/src/pages/StatisticsPage.vue`、`backend/tests/test_budgets.py`、`frontend/src/pages/StatisticsPage.test.js`。
> 依赖：与 M1 共享 `category_service.py` 但函数区域无交叉（§0.2），**M1 合入后再提交 M3**；与 M2 无耦合（M2 重定向保住预算关联 → 反而不进休眠，语义自然衔接）。

---

## 1. 数据模型 + 迁移脚本（设计 §3.2.4）

- [x] 1.1 `models/budget.py`（:22-42）新增列 `dormant: Mapped[int]`（`Integer NOT NULL DEFAULT 0`，注释「1=关联分类被删光的休眠预算」）
- [x] 1.2 新增 `backend/migrate_to_v1.4.3boot2_dormant.py`：`PRAGMA table_info(budgets)` 探测列存在则整体 no-op；缺列 `ALTER TABLE budgets ADD COLUMN dormant INTEGER NOT NULL DEFAULT 0`（SQLite 带默认值单语句加列安全）
- [x] 1.3 backfill：`scope_mode='include' 且无任何 budget_categories 关联` 的存量预算 → `dormant=1`（旧校验下理论命中 0，真正命中者=删分类未级联干净的异常行）；统计输出 `backfilled_dormant`
- [x] 1.4 脚本幂等（重复执行列在即 no-op）、单事务；**执行窗口硬约定（D11）**写进脚本头注释：必须先于新版后端服务启动执行，违反顺序的处置=前端编辑重新保存即清（D9），不写反悔脚本
- [x] 1.5 `routers/budgets.py` 文档字符串随 `schemas/budget.py` 口径同步（见 §2.2）

## 2. 后端校验放开 + 求和分支（设计 §3.2.1 / §3.2.2）

- [x] 2.1 `budget_service._validate_budget_fields`（:110-111）：**删除** `include 且空集 → ValueError`
- [x] 2.2 `create_budget`/`update_budget` docstring 与 `schemas/budget.py:11-25` 注释同步新口径：「include 空集 = 动态全部分类（dormant=0 时）」
- [x] 2.3 `_build_detail` 求和分支改造（:269-282，纯函数）：
  - `snap.dormant` → `spent_raw, detail_pairs = 0.0, []`（覆盖文案由前端按 dormant 渲染）
  - `INCLUDE 且 category_ids 空`（非休眠）→ `spent_raw = month_total`（与 exclude 空排除集**完全同口径**，含 category_id NULL/失效极端数据，D5）；`detail_pairs` = 花费>0 且非未分类桶的全部类目（复用 exclude 分支同款过滤，excluded=∅）
  - 显式所选 INCLUDE / exclude 两分支现状不变
- [x] 2.4 响应 `BudgetDetail` schema 增加 `dormant: bool`；`_BudgetSnapshot.from_budget` 携带该列

## 3. 分类删除级联改向（设计 §3.2.3）

- [x] 3.1 `category_service._cascade_budgets_for_deleted_category`（:278-328）更名 `_dormant_budgets_for_deleted_category`；`still_linked` 为空的 include 预算：**`budget.dormant = 1` 替代 `db.delete(budget)`**；关联行删除、flush、剩余关联查询逻辑不变
- [x] 3.2 exclude 预算行为不变（移出排除集=覆盖扩大，无休眠概念）——核验原分支
- [x] 3.3 返回计数键 `deleted_budgets` → **`dormant_budgets`**；`delete_category` / `restore_default_categories` 两处调用点的返回结构同步
- [x] 3.4 `routers/categories.py:114-128` 文案：`"分类删除成功，同时删除了 N 条关联账单" + "，M 条预算因不再覆盖任何分类被保留为休眠"`（M=0 时不提）
- [x] 3.5 唤醒（D9）：`update_budget` 成功路径统一 `budget.dormant = 0`；`create_budget` 恒 0；**无独立唤醒接口**（核验不新增）

## 4. 汇总剔除（设计 §3.2.5 / D10）

- [x] 4.1 `get_budget_overview`（:540-，**审查勘误：原书 `get_month_summary` :557-593 函数不存在**）：快照构建跳过 dormant 行
- [x] 4.2 `get_year_summary`（:407-408）：`total_amount/total_spent` 同样剔除 dormant
- [x] 4.3 预算列表接口（月视图卡片数据源）**保留返回** dormant 行（置灰展示需要它）——核验未被误过滤

## 5. 前端：表单放开（设计 §3.2.1）

- [x] 5.1 `StatisticsPage.vue`：删 `budgetIncludeEmpty` → `budgetFormValid` 的牵连（:637-639）；删 `budgetScopeError` 红字（:645-647）及其渲染节点（:372-374）
- [x] 5.2 多选框 label（:361）与提示 `budgetScopeTip`（:640-644）改文案：include → 「仅计入所选分类；一个都不选即统计全部分类支出」
- [x] 5.3 编辑回填核验（`openBudgetEditDialog` :766-769）：dormant 预算打开即普通 include 空选，重选或不选皆可保存、后端清 dormant——前端零特殊逻辑（核验）

## 6. 前端：休眠卡片置灰 + 概览剔除（设计 §3.2.5）

- [x] 6.1 `isDormant(budget)` 单点判定
- [x] 6.2 预算卡（:174-234）dormant 态：根节点加 `budget-card--dormant`（`opacity: .55` 一档，明暗通用，**不引新色值**）；scope chip 文本改「保留」；`scopeSummary` 返回固定 `"分类已删除，预算保留"`；`scopeHint` 返回 `"编辑并保存此预算可重新启用"`；进度条恒 0；明细折叠钮隐藏（details 恒空数组自然隐藏，无额外分支）
- [x] 6.3 `budgetPercent/budgetBarColor` 对 dormant 直接 0/`grey`（防御性：spent=0 天然 0%，复用现函数不强改）
- [x] 6.4 概览剔除：`totalBudget/totalSpent`（:613-618）改 `filter(b => !b.dormant)` 后求和

## 7. 边界与异常（设计 §3.3，代码走查 + 用例覆盖）

- [x] 7.1 include 不选建预算后又新建分类 → 新分类自动计入（动态语义，月度数字随账单变化属预期）
- [x] 7.2 动态全部（空集 dormant=0）vs exclude 空集：花费同值（全额），仅标签/明细语义不同，非矛盾
- [x] 7.3 休眠预算月份/年份汇总全面剔除（月概览、年视图、`get_budget_overview`——审查勘误：即原书「get_month_summary」）
- [x] 7.4 用户删除休眠预算 → 既有 DELETE 接口零改动（核验）
- [x] 7.5 「其他」custom 副本被删 → 走同一级联：挂它的 include 预算转休眠（不再连删预算）
- [x] 7.6 dormant=1 被 PUT 改 scope_mode=exclude → dormant=0（D9），exclude 无休眠语义一致
- [x] 7.7 旧版前端缓存包提交 include 空集 → 后端已放开直接落库=动态全部，无需兼容层（核验）
- [x] 7.8 SQLite 写串行（项目单写者口径），分类删除 vs 预算保存无新增交错面（核验）

## 8. 测试（设计 §3.4 + 附录 B）

**后端 pytest（`test_budgets.py` 增改 + dormant 迁移用例新组/新文件）：**
- [x] 8.1 校验放开：「include 空集 → 400」原用例**改写**为 200 + 动态全部求和断言（附录 B）
- [x] 8.2 `_build_detail`：include 空集非休眠 = 全额 + 明细同 exclude 空集组（未分类桶计入 spent 不列名，D5）；dormant → spent=0、details=[]、响应 `dormant:true`；显式所选 include 现状回归
- [x] 8.3 级联改向：「include 预算失去最后关联 → 预算删除」原用例**改写**为「仍在列表 + 已休眠」+ 响应键 `dormant_budgets`（附录 B）；exclude 移出排除集回归；`restore_default_categories` 路径同改
- [x] 8.4 唤醒：dormant 预算 PUT 保存 → dormant=0 恢复统计
- [x] 8.5 汇总剔除：`get_budget_overview`/`get_year_summary` 对 dormant 不计 total；月列表接口仍返回 dormant 行（审查勘误：原书「get_month_summary」不存在）
- [x] 8.6 迁移脚本用例：缺列库 → 加列 + backfill 命中构造的异常空集行、正常行不动、二次执行 no-op、已含列库直接 no-op
- [x] 8.12 **审查补入（原书未点名的口径反转用例）**：`test_migrated_orphan_budget_is_read_only`（:290-343，钉死 v1.4.3「include 空集=只读态、spent 恒 0、PUT 被 400 拦、删除是唯一出口」旧裁定，与 M3 新语义逐条冲突）——改写为「空集非休眠 → spent=当月全额；PUT 200 保存即唤醒（dormant=0）」，删除出口断言随新语义调整；归 M3b 半区

**前端 vitest（`StatisticsPage.test.js`）：**
- [x] 8.7 `budgetFormValid`：include 空选 → 可保存（**改写**原禁用断言组）；`budgetScopeError` 渲染节点删除断言（附录 B）
- [x] 8.8 置灰：`budget-card--dormant` 类、chip 文本「保留」、覆盖/提示文案（`?raw` 断言）
- [x] 8.9 概览求和剔除 dormant（纯函数/computed 用例；原 Σ 用例补分支，附录 B）
- [x] 8.10 `scopeSummary`/`scopeHint`：dormant 与 include 空集两分支
- [x] 8.11 label/提示文案更新的既有用例随改（:361/:640-644 现文案断言）

## 9. 验收门槛

- [x] 9.1 `pytest` / `npm test` 相关组全绿；mypy/ruff 基线零新增
- [ ] 9.2 人工·主链路：新增预算不选分类保存 → 卡片显示全部分类语义、花费=当月总支出；新建分类并记账 → 该预算数字自动跟上；删除该预算唯一关联分类 → 卡片置灰「分类已删除，预算保留」、月概览不含它；编辑重选分类 → 恢复计入
- [ ] 9.3 人工·明暗主题 × 竖/宽屏自查（置灰一档可读、不引新色值）
- [ ] 9.4 不回退核验：v1.4.3 M12 预算两泳道互斥校验（scope_mode 切换时的多选行为）只放宽空集限制，泳道互斥本身不变

**验收标准（设计 §3.4）**：① 包含模式零分类可直接保存；② 不选的分类预算覆盖后续新增分类；③ 分类删光的 include 预算不再消失，置灰、花费 0、不参与汇总、可编辑恢复。
