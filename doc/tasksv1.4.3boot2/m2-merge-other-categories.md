# M2 - 「其他支出 / 其他收入」数据归并入「其他」（需求二）

> 对应需求二（设计 §二）。新增一次性迁移脚本：按桶合并三个「其他」类（引用重定向后删旧行），幂等可单独执行，**不等待、不绑定** `migrate_to_v1.4.3.py`（该脚本现场库仍未执行，见 §2.1）。零运行期代码改动。
> 涉及文件：新增 `backend/migrate_to_v1.4.3boot2_categories.py`、新增 `backend/tests/test_migration_v143boot2_categories.py`。蓝本 `backend/migrate_to_v1.4.3.py`（`_normalize_other` :310-336、`_redirect_and_delete` :339-356、重排 :359-374）——**不 import、不修改它**。
> 依赖：无（与 M1 仅共享家族名字面值常量，一致性断言钉住；与 M3 脚本互不依赖）。

---

## 1. 脚本主体：`backend/migrate_to_v1.4.3boot2_categories.py`（设计 §2.2.1）

- [x] 1.1 脚本侧家族常量独立定义（`其他支出/其他收入/其他` + keeper 优先级 其他 > 其他支出 > 其他收入），命名与 `category_service` 侧可对齐 import（供 §3.2 一致性断言）
- [x] 1.2 分桶：按 `user_id`（含 `None` 预设桶）分组；同桶内家族行 >1 时合并；keeper 改名「其他」、图标刷 `mdi-cash-minus`（对齐预设固定值）
  > 实现口径：`>1 才合并` 约束的是 **loser 数（`merged_rows`）**；「改名 + 刷图标」对**每桶 keeper 无条件收敛**——桶内只有一行旧名（如仅有「其他收入」副本）时同样归一为「其他」，否则 §3.3「全库家族行仅剩各桶一个『其他』」不成立（用例 `test_3_3c_single_legacy_row_is_normalized_without_merging`，`merged_rows=0 / keepers_normalized=1`）。
- [x] 1.3 loser 处置顺序：先 `DELETE loser` 再对 keeper 改名（规避 `UNIQUE(name,user_id)` 撞形，蓝本 :313-336 同款注释保留）
- [x] 1.4 引用重定向表集合：`records.category_id`、`quick_templates.category_id`、**`budget_categories.category_id`（新增，蓝本没有）**；`tags` 如有关联表一并处理；逐表 `_table_exists` 探测，表不存在跳过（版本混跑安全）
  > 实现补充：`budget_categories` 带 `UNIQUE(budget_id, category_id)`——同一条预算**同时**挂 loser 与 keeper 时 UPDATE 会撞约束，故先把这类 loser 关联行**去重删除**再重定向其余行（该预算的覆盖本就由 keeper 行承载，覆盖不因此改变，§2.3 边界表「预算覆盖延续到『其他』」语义成立），计数单列 `deduped_references`（用例 `test_3_3` 的预算 402/403 两组形态）。`tags` 确有 `category_id` 列 → 纳入集合；`record_tags` 只关联 (record_id, tag_id)、无该列（分类引用经 records 已覆盖）→ **不**纳入，用例断言其内容一字不变。v1.4.2 旧形 `budgets.category_id` **不在** §2.2.1 集合内（旧形 `UNIQUE(category_id, month)` 下重定向同样会撞形、只能删预算让位，超出「不丢覆盖」范围），已在脚本头「已知边界」段登记，副本实测该形制下预算均未挂家族 loser。
- [x] 1.5 跨桶不合并：用户桶只有旧名副本、预设桶另有「其他」→ 各自桶内归一；用户副本改名「其他」后按 CoW 天然遮蔽预设行，**不**把用户副本重定向到预设 id
- [x] 1.6 置尾：合并完成后对每个用户可见集合（`user_id ∈ {None, X}`）把该桶 keeper `sort_order` 置为「可见存活行最大 sort + 1」；已是最大则不动（幂等）；用户副本桶同样处理
- [x] 1.7 统计输出：`merged_rows / redirected_references（分表计数） / tail_fixed`，全 0 = no-op（幂等证明）
- [x] 1.8 安全：执行前置检查只读（`PRAGMA integrity_check` 摘要 + 家族行清单打印）；全程单事务提交，失败即回滚可重跑；脚本不做备份（备份属发布窗口纪律，见 progress.md 发布备忘）
- [x] 1.9 `frontend/src/utils/constants.js` 的 `CATEGORY_ICONS` 旧名映射为死代码——**不触碰**（§0.4，不扩范围，核验）

## 2. 独立性核查（设计 §2.2.2 / §2.2.3）

- [x] 2.1 `init_preset_data`（`app/main.py` :44-68 新 14 条单套，审查勘误：原书「main.py :46-65」）按 name 幂等——跑完脚本旧名不再被种回，`app/main.py` 零改动（核验）
- [x] 2.2 `restore_default_categories` 预设复位按 name 匹配新 14 条——旧名行删除后无残留匹配问题，零改动（核验）
- [x] 2.3 对未执行 `migrate_to_v1.4.3.py` 的库：旧 UNIQUE 形 `(name,type,user_id)` 下「先删 loser 再改名」同样成立；`budget_categories` 缺表按探测跳过；两脚本任意顺序均收敛（v1.4.3 的 `_normalize_other` 见单桶单家族行自然 no-op）——代码走查确认

## 3. 测试（设计 §2.4，新文件 `test_migration_v143boot2_categories.py`，临时 SQLite 副本库）

- [x] 3.1 夹具「现场形态」：旧名预设（user_id=None）+ 用户旧名副本 + 预设「其他」+ records/quick_templates/budget_categories 引用行
- [x] 3.2 常量一致性断言：脚本家族常量 与 `category_service.OTHER_FAMILY_RANK.keys()` ⊇ 且 ⊆ 互钉（防漂移，闭合 M1 §5.4）
  > **实测闭环（M2，2026-09-22）**：脚本落文件后 `test_categories_reorder.py::test_other_family_rank_matches_m2_script_constants` 由 skip **自动转实断言并通过**（`1 passed`，非 skip；全量 pytest `0 skipped` 佐证），故 **M2 未编辑 `test_categories_reorder.py`**（M1 的「文件不存在即 skip、存在则按路径加载实断言」写法零人工升级）。脚本侧双向钉的落点 = 新文件 `test_migration_v143boot2_categories.py::test_3_2_family_constants_are_pinned_in_both_directions`（⊇/⊆ 各一条 + 名表逐位 + `KEEPER_PRIORITY` 独立钉）。
  > **实现期漂移修正**：草稿曾以「`OTHER_FAMILY_RANK` 倒序」推导 keeper 优先级，得 `其他 > 其他收入 > 其他支出`，与设计 §2.2.1/蓝本的 `其他 > 其他支出 > 其他收入` 相反（名次表是置尾排列序，非 keeper 优先级）——已改为 `KEEPER_PRIORITY = (OTHER_CATEGORY_NAME, *LEGACY_OTHER_NAMES)` 并由 `test_3_3d` 纯函数用例 + `test_3_3` 库级断言（用户 1 桶保留 id 23「其他支出」而非 22）双向钉住。
- [x] 3.3 合并断言：全库家族行仅剩各桶一个「其他」（图标 `mdi-cash-minus`、置尾）；引用重定向计数正确（**含 `budget_categories`**）；loser 行删除
- [x] 3.4 幂等：二次执行统计全 0、数据不变
- [x] 3.5 环境变体两组：旧 UNIQUE 形（未跑 v1.4.3 的库）与 `budget_categories` 缺表各一组
- [x] 3.6 顺序收敛：至少覆盖「v1.4.3 迁移跑过后 boot2 再跑 no-op」一条（同库联测成本过高时按此裁剪，设计已允许）

## 4. 验收门槛

- [x] 4.1 新 pytest 文件全绿 + 既有回归全绿；mypy/ruff 基线零新增
  > **门槛实测（M2，2026-09-22）**：`pytest` **288 passed / 0 failed / 0 skipped**（含新文件 18 例；`0 skipped` 即 §5.4 占位转实断言的全局佐证）；`mypy backend/app --strict` = **92 errors in 14 files**，其中 **+2 归对向泳道 M3b 在途**（`category_service.py:467-468`，M3b 正改其级联区）——M2 零 `app/` 运行期代码改动，故 M2 侧贡献为 0；新增两文件自身在 `--strict` 下 **零报错**、`ruff check` **All checks passed**。`backend/money.db` 全程只读（未执行任何迁移，用例一律 tmp_path 临时库）。
- [ ] 4.2 人工·现场库**副本**演练一次：备份 → 执行 → 前端分类页三行变一行、历史账单归类正确、预算覆盖不变
- [ ] 4.3 发布备忘登记：执行序（先备份、dormant 脚本先于新代码启动、本脚本与其顺序可换可单独重跑）写入 progress.md 发布备忘段

**验收标准（设计 §2.4）**：执行后分类列表只存在一个「其他」（末位）；原挂「其他支出/其他收入」的账单、模板、预算关联全部指向「其他」；重跑无副作用。
