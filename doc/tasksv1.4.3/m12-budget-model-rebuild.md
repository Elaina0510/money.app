# M12 - 预算模型重构：每月多条命名预算（需求十二）★重构 + 迁移

> 对应需求十二（设计 §十二）。预算改「某自然月下的具名预算」：名称/金额/范围模式（包含/排除）/关联分类列表，同月可多条；统计页预算区改预算卡片列表；旧分类预算 1:1 迁移（`migrate_to_v1.4.3.py` 阶段 B）。约束对象仍为支出。
> 涉及文件（后端）：`models/budget.py`（重写）、新增 `BudgetCategory`、`schemas/budget.py`、`services/budget_service.py`、`routers/budgets.py`、`services/category_service.py`（删除级联适配）、`migrate_to_v1.4.3.py`（阶段 B 续写）。
> 涉及文件（前端）：`StatisticsPage.vue`（预算卡区 :123-298 + 新增对话框 :301-329 + ConfirmDialog :331-338 + script 预算逻辑 :527-704 重写）、`api/budgets.js`、`StatisticsPage.test.js`、`test_budgets.py`、`test_data_isolation.py`（预算段）、`test_migration_v143.py`（阶段 B 断言并入）。
> 依赖：**依赖 M8**（分类单套 + 两阶段迁移同脚本「分类在前、预算在后」）。`BudgetPage.vue` 为死文件不参与适配（保留不动）。M14 后续只换本模块新增对话框外壳。

---

## 1. 后端：数据模型（D3，设计 §12.2.1）

- [x] 1.1 `Budget` 重写：`budgets(id, user_id FK, name str NOT NULL, month str YYYY-MM, amount float, scope_mode str, created_at, updated_at)`；name 同月不强制唯一
- [x] 1.2 新增 `BudgetCategory` 关联表：`budget_categories(id, budget_id FK→budgets.id ondelete=CASCADE, category_id FK→categories.id)`，`UniqueConstraint("budget_id","category_id",name="idx_budgetcat_budget_category")`
- [x] 1.3 服务层校验：name 1–50 必填；amount>0；`scope_mode ∈ {include, exclude}`；**include → category_ids 去重后 ≥1**；exclude 允许空列表（=全部分类，UI 同步提示该语义）

## 2. 后端：接口契约（D12，设计 §12.2.2）

- [x] 2.1 `GET /api/budgets?month=`：去 `type` 参数；返回 `BudgetDetail[]` 按 id 升序（创建序）
- [x] 2.2 `POST /api/budgets`：由 upsert 改**纯创建**（同月同多名允许）；载荷 `{month, name, amount, scope_mode, category_ids}`
- [x] 2.3 `PUT /api/budgets/{id}`：全字段编辑 `{name, amount, scope_mode, category_ids}`，**month 传入被忽略**；IDOR 403 保持
- [x] 2.4 `DELETE /api/budgets/{id}`：不变（IDOR 403）
- [x] 2.5 **删除** `POST /api/budgets/batch`（调用方仅统计页）
- [x] 2.6 `GET /api/budgets/year-summary?year=`：结构不变；`months[].total_amount/total_spent = Σ 各预算`（D4）；`budgets[]` = 该月 BudgetDetail 列表
- [x] 2.7 `BudgetDetail` 响应结构：`{id, month, name, amount, spent, remaining, percentage, scope_mode, category_ids, category_names, details:[{category_id, category_name, icon, spent}]}`

## 3. 后端：spent 计算（设计 §12.2.3，杜绝 N+1）

- [x] 3.1 `_month_expense_by_category(db, month) -> dict[int, float]`：单查询 `SELECT category_id, SUM(amount) ... WHERE type='expense' AND consume_time BETWEEN 月首月末 GROUP BY category_id`（收支口径与旧 `_enrich_budget` 同源；**审查修订（2026-09-20 用户已认可）：实测旧 :87-92 spent 查询缺 `user_id` 谓词、跨用户聚合致 spent 虚高——本重写必须补 `WHERE user_id = ?` 隔离，属对设计「谓词完全同源」的裁定性偏离**，并落 §11.2 隔离用例）
- [x] 3.2 include：`spent = Σ 选中类花费`（未出现在聚合结果的记 0）；exclude：`spent = 当月全部支出 − Σ 排除类花费`（空列表即全额）
- [x] 3.3 details：include → 选中类逐一（0 花费显示 0）；exclude → **仅列出有实际花费的未排除分类**（明细只列计入分类）
- [x] 3.4 `remaining/percentage/超额判定` 沿用现口径（`max(amt-spent,0)`、`spent/amt*100`）；进度色档实测三处同型 `>80% error / >50% warning / 其余 success(primary)`、无 100% 独立档，前端计算不变
- [x] 3.5 year-summary：全年一次聚合 `GROUP BY substr(consume_time,1,7), category_id`，Python 内按月逐预算按同规则求和——12 月 × N 预算零 N+1
- [x] 3.6 金额口径：全部经 `round_money`；聚合 float 求和后再 round（与旧逐条口径一致）

## 4. 后端：分类删除级联适配（设计 §12.2.4，`category_service.delete_category`）

- [x] 4.1 删分类时删 `budget_categories` 关联行
- [x] 4.2 **include** 模式若因此无任何分类 → 该预算一并删除（对齐现「级联删预算」语义，响应 message 提示）
- [x] 4.3 **exclude** 模式仅移出排除集（预算语义自动扩大，不删）
- [x] 4.4 restore-defaults 路径复用同一级联逻辑

## 5. 前端：统计页月视图预算卡列表（设计 §12.2.5）

- [x] 5.1 「预算管理」卡内改**预算卡片列表**：每卡显示 名称、已用/预算金额、进度条（色档沿用）、覆盖简述、展开明细、编辑（铅笔→对话框回填）/删除动作；多卡纵向堆叠，key=id
- [x] 5.2 月度总览小卡保留（:148-164），total = Σ 各预算（D4 口径）
- [x] 5.3 覆盖简述纯函数 `scopeSummary(b, categories)`：include ≤2 类全列（「餐饮、交通」）、>2 类前 2 + 计数（「餐饮、交通等 3 类」）；exclude 空列表→「全部分类」、非空→「除 工资、理财 外全部支出」；恒在卡片副行 tooltip/尾注呈现一次语义提示（exclude「选中分类不计入本预算」/ include「仅计入所选分类」）
- [x] 5.4 展开明细：`v-btn toggle + v-slide-y-transition`（M12 先以 slide-y 落地，时长 `--expand-duration` 口径，M14 收编统一展开动画）；明细行 = details 字段（仅计入分类）
- [x] 5.5 删除走 `ConfirmDialog`，message：`确定要删除「{名称}」预算吗？`；确认后 DELETE + 重拉
- [x] 5.6 script 清理：删行内编辑态（`editingBudget`/`editBudgetAmount`/`availableBudgetCategories` 等，type 依赖随之消失）

## 6. 前端：新增/编辑对话框（重写 :301-329 单分类版）

- [x] 6.1 名称 `v-text-field`（必填校验）/ 金额（>0）/ 范围模式 `v-btn-toggle`（包含/排除 + 语义提示文案）/ 分类 `v-select multiple chips`（**M8 单套分类全量**）
- [x] 6.2 校验联动：include 0 选 → 保存禁用 + 提示；exclude 允许 0 选（提示=全部分类语义）
- [x] 6.3 编辑复用同对话框回填全部字段（含 category_ids/scope_mode）

## 7. 前端：`api/budgets.js`

- [x] 7.1 删 `batchSetBudgets`（随 batch 端点下线）；新增 `createBudget(data)`（POST 纯创建）；`updateBudget(id, data)` 载荷扩为全字段；`getBudgets({month})` 保持不传 type（现状 :611 已不传）。**审查修订登记**：实测现状编辑/行内改额走 `batchSetBudgets`（StatisticsPage :637/:659），`updateBudget` 未被 import——batch 下线时编辑保存链路须重接为单条 `PUT /{id}`（随 §6.3 对话框编辑路径一并落地）

## 8. 前端：年视图

- [x] 8.1 `yearMonths` 渲染结构不变（total_amount/total_spent 后端 Σ 口径透传）；下钻逻辑不变（点行 → 月视图该月预算卡列表）

## 9. 迁移脚本阶段 B：预算（设计 §12.2.6，同脚本、阶段 A 之后、同事务）

- [x] 9.1 幂等判据：`PRAGMA table_info(budgets)` 已含 `name` 列 → SKIP
- [x] 9.2 旧表逐行 1:1 转换：`cid' = merge_map.get(old.cid, old.cid)`（阶段 A 内存映射）；`name = 保留分类行当前名`；amount/month/user_id/created_at/updated_at 原样
- [x] 9.3 分类已被彻底删除的旧预算行 → 名称「未知分类」、category_ids 置空、scope 仍 include（**迁移产出的只读态**：正常展示、spent=0、可删；仅 PUT 重保存被 include ≥1 校验拦截引导补选）
- [x] 9.4 同月多条 → 多行新记录（多张卡），**不做任何合并**
- [x] 9.5 建 `budgets_new` + `budget_categories` → 写入 → `DROP TABLE budgets` → RENAME（与阶段 A 同法整表重建、同事务）
- [x] 9.6 输出 `[OK] 转换 x 条预算（含 y 条重定向分类引用）`

## 10. 边界自检（设计 §12.3）

- [x] 10.1 include 预算引用的分类之后被删 → §4 级联行为正确
- [x] 10.2 exclude 空列表且当月零支出：spent=0、percentage=0
- [x] 10.3 同月同名两条预算：允许，卡片以 id 为 key
- [x] 10.4 旧版用户从未设预算：阶段 B 空表迁移即过，新 UI 空态引导
- [x] 10.5 年视图 Σ spent 大于当月总支出（范围重叠）：预期行为（D4），卡片区不额外解释
- [x] 10.6 开发库实测登记（附录 A.5）：money.db budgets 旧形为 `UNIQUE(category_id, month)` 无 user_id——整表重建 + 文本判据天然兼容，不假设库形制

## 11. 测试：后端（设计 §12.4）

- [x] 11.1 `test_budgets.py` 新模型全量重写：POST include/exclude/空排除集、同月多条、同月同名多条；校验（缺 name/空 name→422、amount≤0→422、include+空 ids→PARAM_ERROR、exclude+空 ids→200）；spent 精确（造 4 分类流水：include 2 类求和、exclude=总额−该类、空排除=全额、details 内容两模式）；PUT 全字段 + month 忽略 + IDOR 403 + DELETE；year-summary 逐月 Σ total_amount/total_spent（含重叠直加）+ budgets[] 结构；POST 非 upsert（同 payload 两次两条）
- [x] 11.2 `test_data_isolation.py` 预算段适配新表；**新增 spent 跨用户隔离用例**（用户 B 同分类支出不得计入用户 A 预算——锁死 §3.1 user_id 谓词修复）
- [x] 11.3 `test_migration_v143.py` 并入阶段 B 断言：1:1 转换（条数/金额/月份/名称=分类名）、被合并分类引用重定向、二次 SKIP、**单事务回滚**（构造阶段 B 失败 → 阶段 A 数据不落库）
- [x] 11.4 mypy 基线零新增 + ruff 通过

## 12. 测试：前端

- [x] 12.1 `StatisticsPage.test.js` 预算块重写：月视图渲染预算卡列表（名称/已用/预算/进度/简述各一）；`?raw` 不含 `editingBudget`
- [x] 12.2 `scopeSummary` 单测：include 1/2/3 类文案、exclude 空/非空文案
- [x] 12.3 新增对话框：include 未选分类保存禁用；提交载荷字段精确
- [x] 12.4 删除走 ConfirmDialog 且 message 含名称；确认后 DELETE 调用 + 重拉
- [x] 12.5 年视图行数字 = 后端 total_amount/total_spent 透传；下钻仍可用
- [x] 12.6 v1.4.2「M7 分类柱状图过渡动画」describe 块（:314 起）全部保留不动

## 13. 验收与质量门槛

- [x] 13.1 后端全量 pytest 绿（含 M8 联调：`migrate_to_v1.4.3.py` 两阶段一次执行）；前端 vitest 绿；lint 通过
- [ ] 13.2 手工验收场景复算：同月「日常开销 3000 包含 餐饮/交通/日用」+「学习 500 包含 教育」两卡独立进度正确；「除工资外全支出 4000」排除模式已用 = 当月支出 − 工资类支出
- [ ] 13.3 升级回归：旧数据迁移后原分类预算以单分类命名预算完整保留（金额月份一致）；年视图合计 = 当月各预算金额之和
- [ ] 13.4 明暗主题、竖/宽屏自查；`frontend/dist` 不随本模块提交
