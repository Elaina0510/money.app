# M8 - 分类模型重构：收支共用统一分类（需求八）★重构 + 迁移

> 对应需求八（设计 §八）。分类不再区分收入/支出，成为收支共用统一标签：模型约束改 `(name, user_id)`（D2 保留 type 列、废弃语义）、预设合并为 14 条单套、「其他支出/其他收入」合并为「其他」（`mdi-cash-minus` 置末）、存量数据迁移（`migrate_to_v1.4.3.py` 阶段 A）、前后端全部消费方去 type 依赖。
> 涉及文件（后端）：`models/category.py`、`schemas/category.py`、`services/category_service.py`、`routers/categories.py`、`main.py`、`services/record_service.py`、`services/import_service.py`、`services/export_service.py`、新增 `backend/migrate_to_v1.4.3.py`。
> 涉及文件（前端）：`SettingsCategoriesPage.vue`（重写列表+弹窗）、`RecordFormPage.vue`、`SettingsPage.vue`（分类摘要）、`CsvMappingDialog.vue`、`useCategoriesStore.js`。
> 涉及文件（测试）：`test_categories.py`、`test_categories_reorder.py`、新增 `test_migration_v143.py`、`test_csv_import_export.py`/`test_sql_import_export.py`（适配）、`SettingsSubPages.test.js` 分类块、`RecordFormPage.test.js`。
> 依赖：无（被 M9/M12 依赖，须先行）。**红线：M8 不动 `StatisticsPage.vue`**（`availableBudgetCategories` type 过滤随 M12 重写自然消失，登记于依赖表避免同触）。分类页样式由 M8 一次落到 M6 口径。

---

## 1. 后端：模型与 schema（设计 §8.2.1/§8.2.2）

- [x] 1.1 `models/category.py`：`__table_args__` 改 `UniqueConstraint("name", "user_id", name="idx_categories_name_user")`
- [x] 1.2 `type` 列保留（D2）：`type: str = Field(default="expense", nullable=False)`；新增常量 `LEGACY_CATEGORY_TYPE = "expense"` 供新行占位写入；列与原值保留供事后排查
- [x] 1.3 认知登记：SQLModel `UniqueConstraint` 不生成命名索引对象（真库仅 `sqlite_autoindex_categories_N`），新库 `create_all` 直接产表级内嵌 `UNIQUE (name, user_id)`；旧库换形靠迁移整表重建，**不可用 DROP INDEX**
- [x] 1.4 `schemas/category.py`：`CategoryCreate` 删 `type` 必填（多余字段 pydantic 默认忽略）；`CategoryReorder = { ids: list[int] }`（去 type）；`CategoryResponse` 保留 `type` 字段（列原值，前端不再读取）

## 2. 后端：服务层规则单点（设计 §8.2.3）

- [x] 2.1 `category_service.py`：常量 `OTHER_CATEGORY_NAME = "其他"` 为唯一真源（原 `OTHER_CATEGORY_NAMES` dict 删除）；`_is_other_category(cat)` 仅判 `cat.name == '其他'`；`_is_other_row(name)` 同步改签名（原 :16-26 name+type 双判废弃）
- [x] 2.2 `_visible_categories`：CoW 排除子查询改**仅按 name** 匹配（用户同名自定义行遮蔽预设行，无论列上残留 type 值，D11）
- [x] 2.3 `get_categories`：`type` 参数保留签名、一律忽略，响应全量单列表
- [x] 2.4 `_next_sort_order` 单列表版：非「其他」行 `max(sort)+1`，且钳制小于「其他」行的 sort（沿用 v1.4.2 钳制算法，作用域组内→全列表）
- [x] 2.5 `create_category`：查重改仅 `name + user_id`（跨原收支语义同名亦拒）；写入 `LEGACY_CATEGORY_TYPE`
- [x] 2.6 `reorder_categories(db, ids, user)`：作用于全量可见集合——ids 须为全量、「其他」强制归一化末位、预设行改序落 CoW 副本（v1.4.2 算法平移）；缺「其他」报 PARAM_ERROR（v1.4.2 语义平移）
- [x] 2.7 `update_category`：「其他」改名拒绝文案改「"其他"分类名称不可修改」；其余逻辑不变（本就不收 type/sort_order）
- [x] 2.8 `restore-defaults`（:332-394）：预设复位改按新预设集 **name** 匹配（原按 (name,type)）

## 3. 后端：预设集（设计 §8.2.4，`main.py:44-82`）

- [x] 3.1 15 条双套改 **14 条单套**：餐饮(1) 出行(2) 购物(3) 娱乐(4) 医疗(5) 居住(6) 通讯(7) 工作(8) 旅行(9) 账单与费用(10) → 工资(11) 红包(12) 理财(13)（图标不变）→ 其他(14) `mdi-cash-minus`
- [x] 3.2 全部预设行 type 列写 `'expense'` 占位；原「其他收入」预设行随迁移删除
- [x] 3.3 `init_preset_data` 改按 name 幂等 seed

## 4. 后端：路由与其他服务适配

- [x] 4.1 `routers/categories.py`：GET `type` 查询参数保留签名透传但服务层忽略；POST 不再收 type；reorder 调用去 type（:19、:64）
- [x] 4.2 `record_service.py:429-434`（D9）：手动快速记账模板 `type` 派生改「该标签最近一笔流水的交易 type」（records 按 `consume_time` desc 取第一行），无流水兜底 `'expense'`；`quick_templates.type` 列语义不变（交易语义）
- [x] 4.3 `import_service.py:200`：CSV 导入新建分类携带 `type` 改恒 `'expense'` 占位（实测现状新建分类未设 sort_order、默认 0，未经 `_next_sort_order`——本期仅改 type 语义，排序行为维持现状不扩范围，登记之）
- [x] 4.4 SQL 导出/导入（`export_service.py:92-110`）：导出列保留原值；导入匹配改按 name、type 忽略；旧文件同名 income/expense 两分类在新库撞 name 唯一 → 「已存在同名即映射」消解（设计 §8.3）
- [x] 4.5 `budget_service.py:34-40` **不动**（按分类 type 过滤随 M12 重写整体消失，不双改）

## 5. 前端：分类管理页重写（设计 §8.2.5）

- [x] 5.1 模板改**单一 Draggable 列表**（一组 `dragList: ref([])`，快照/回滚单份）；删除收入/支出分组标题、双列表与「支出分类/收入分类」表头（原 :227-228 双 computed）
- [x] 5.2 行图标统一 `.entry-avatar` primary 10% 底 + primary 图标（替换现 :56-58、:112-114 红/绿双色底），消除同页收支色暗示
- [x] 5.3 弹窗删「类型」`v-select`（:158-165）与 `categoryForm.type`；保存载荷仅 `{name, icon}`
- [x] 5.4 `isOther = cat.name === '其他'`；置尾/锁定/归一化逻辑作用域从"分组内"改"全列表内"（「其他」无把手不可拖、恒末位）
- [x] 5.5 间距直接按 M6 口径落 `section-title`/`section-block` 与全局规则（M6 不再触碰本文件，一次落地）

## 6. 前端：其余消费方适配

- [x] 6.1 `RecordFormPage.vue`：`currentCategories`（:253-255）去过滤返回全量；`watch(recordType)` 的"选中项出组重置"逻辑删除（:431-436、:455-458）；`onMounted` 默认分类改取全列表首个非「其他」项；分类九宫格图标/选中色继续按**交易** type 着色（交易语义不变）
- [x] 6.2 `SettingsPage.vue`：分类摘要「支出 x / 收入 y」→「{{ categories.length }} 个分类」（:50-52；删 :287-288 两个 computed）
- [x] 6.3 `CsvMappingDialog.vue:99`：`categoryOptions` label 去「(支出/收入)」后缀；create action 不再发送 `type` 字段
- [x] 6.4 `useCategoriesStore.js`：删 `expenseCategories/incomeCategories` computed（:12-18，全库确认无其他消费方后）；`reorderCategories` 改签名 `(ids)`（:68-79 去 type）
- [x] 6.5 **红线**：不动 `StatisticsPage.vue`、不动 `BudgetPage.vue`（死文件）

## 7. 迁移脚本阶段 A：`backend/migrate_to_v1.4.3.py`（设计 §8.2.6，D1）

- [x] 7.1 骨架：v1.4/v1.4.2 同款范式（SQLAlchemy 原生 SQL + 探测判据 + `[OK]/[SKIP]` 输出 + 头部用法/幂等说明）；`cd backend && python migrate_to_v1.4.3.py [db路径]`；**全程单事务**（`engine.begin()`，任何一步失败整体回滚）；文件预留阶段 B 挂点（M12 续写，分类在前、预算在后）
- [x] 7.2 幂等判据：读 `sqlite_master` 中 categories 的 **CREATE TABLE 文本**已含 `UNIQUE (name, user_id)` → 整体 SKIP；**不可用 `PRAGMA index_list` 判名**；识别 `UNIQUE (name, type)` 与 `UNIQUE (name, type, user_id)` 两代旧形；表不存在（新库）输出 `[SKIP]`
- [x] 7.3 同名合并：按 `user_id` 分桶（NULL=预设桶），桶内按 name 分组——同名两行保留 expense 行（图标天然取支出侧）、income 行为 loser；仅 income 行保留原位待追加
- [x] 7.4 loser 引用重定向：`records.category_id`、`tags.category_id`、`quick_templates.category_id` 改指 kept id（`operation_history` 快照文本不追改，属历史审计）；重定向后 DELETE loser 行；内存记录 `merge_map[loser] = kept`（供阶段 B 使用，同事务同进程）
- [x] 7.5 「其他」归一三分支：桶内「其他支出」改名「其他」（icon 非 `mdi-cash-minus` 一并纠正）；「其他收入」按 7.3/7.4 作 loser 并入；仅收入侧「其他收入」桶 → 原行改名且 icon 置 `mdi-cash-minus`；桶内**已有自建「其他」** → 被改名行作 loser 重定向并入。全库结束后任一桶内「其他」唯一且置末
- [x] 7.6 排序重排：桶内序 =（非其他·原 type=expense 按原 sort,id）→（仅收入侧行 按原 sort,id）→（其他）；`sort_order` 重写 1..n 无空洞（合并前 99 等旧预设位一并消除）
- [x] 7.7 预设桶按 §3 清单校准：14 条逐条以 name 定位，纠 icon/sort；删除多余预设行（仅「其他收入」）
- [x] 7.8 **categories 整表重建**（约束换形唯一路径）：`CREATE TABLE categories_new(..., CONSTRAINT idx_categories_name_user UNIQUE (name, user_id))` → 最终行 INSERT SELECT → `DROP TABLE categories` → RENAME → 末尾 `PRAGMA foreign_key_check` 零违规（连接未启用 `PRAGMA foreign_keys`，DROP/RENAME 不被阻断；7.4 已消灭全部 loser 悬挂）
- [x] 7.9 输出 `[OK] 合并 x 组同名分类 / 重定向 y 条账单 / …`
- [x] 7.10 回滚说明写入脚本头注释：不提供 downgrade 代码路径——回滚 = 恢复发布流程中的 db 备份（沿 v1.4.2 口径）；发布步骤（停服→备份→跑脚本→起新服）与开发库旧形制登记（附录 A 第 5 条：money.db budgets 为 `UNIQUE(category_id, month)`、quick_templates 无 kind 列，**不假设库必处于 v1.4.2 后标准态**）

## 8. 边界自检（设计 §8.3）

- [x] 8.1 用户曾把收入预设 CoW 改名（如「红包」→「退款」）：按 name 匹配不受影响，「退款」为仅收入侧行追加段保留
- [x] 8.2 交易 type 与分类无关联校验：收入交易挂任意分类/支出挂任意分类均允许（后端只校验 `Record.type ∈ {income,expense}`）
- [x] 8.3 SQL 导出→跨版本导入旧文件：按 name 匹配、匹配不上走映射新建（type 忽略）、同名即映射
- [x] 8.4 用户桶缺「其他」不补（预设桶恒有，与 v1.4.2 可见集合行为一致）
- [x] 8.5 reorder ids 缺「其他」→ PARAM_ERROR（v1.4.2 语义平移）

## 9. 测试：后端（设计 §8.4）

- [x] 9.1 `test_categories.py` 重写：去 type 后 CRUD；跨原收支语义同名查重拒绝；「其他」改名 400；CoW 仅按 name（用户「工资」副本遮蔽预设）；GET 带 `type=expense` → 200 且返回全量（忽略断言）
- [x] 9.2 `test_categories_reorder.py` 重写：`{ids}` 单列表全量重排、「其他」强制置末、缺项/多项 400、预设行改序落副本
- [x] 9.3 新增 `test_migration_v143.py`（阶段 A 部分；M12 续阶段 B 断言）：sqlite 临时库 fixture **手写旧形 CREATE TABLE**（至少覆盖 `UNIQUE(name,type)` 与 `UNIQUE(name,type,user_id)` 两代——conftest `create_all` 会直接产新形，不可依赖）造 v1.4.2 态数据：15 预设 + 用户 A 双套同名「餐饮」+ 仅收入「报销」+ 各自账单 + 「其他收入」CoW 副本 + 引用 loser 分类的 tag/模板。断言：
  - [x] ① 合并后无同名重复、loser 行删除、records/tags/quick_templates 重定向
  - [x] ② 「其他」唯一、icon=`mdi-cash-minus`、置末
  - [x] ③ sort_order 连续 1..n 且顺序 = 支出组→仅收入→其他
  - [x] ④ `sqlite_master` categories 建表文本含 `UNIQUE (name, user_id)` 且不含 `(name, type, user_id)`
  - [x] ⑤ **迁移前后按月 group by type 的收支合计逐分不差**
  - [x] ⑥ 二次运行 SKIP（幂等）
  - [x] ⑦ 阶段 B 未跑前 budgets 数据原样不损
- [x] 9.3a **审查修订（conftest 陷阱登记）**：实测 `backend/tests/conftest.py:34-42` 自带**过期 7 条预设副本**（无「其他支出」、旅行图标 `mdi-airplane` ≠ `app/main.py` 的 `mdi-bag-suitcase`，且不 import 真源）——迁移/预设相关断言**禁止依赖 conftest 预设**（import `app.main.PRESET_CATEGORIES` 真源或在 fixture 内手写），避免假绿/假红
- [x] 9.4 `test_csv_import_export.py`、`test_sql_import_export.py` 适配：新建分类无 type 语义、name 匹配兼容
- [x] 9.5 回归不动项：`test_statistics.py`、`test_records.py`、`test_history.py`（交易 type 语义未变）全量保持通过
- [x] 9.6 mypy 基线零新增 + ruff 通过

## 10. 测试：前端（`SettingsSubPages.test.js` 分类块重写等）

- [x] 10.1 单列表渲染：无「支出分类/收入分类」标题；「其他」行无把手
- [x] 10.2 弹窗无「类型」下拉；保存载荷 `{name, icon}`（mock store 断言调用参数）
- [x] 10.3 `store.reorderCategories(ids)` 以纯 ids 调用 mock api
- [x] 10.4 `RecordFormPage.test.js`：income/expense 切换后分类九宫格数量不变（全量）；选中的原收入分类在支出模式下保持选中
- [x] 10.5 `CsvMappingDialog` 用例：选项 label 无「(支出/收入)」
- [x] 10.6 设置页摘要断言改「N 个分类」

## 11. 验收与质量门槛

- [x] 11.1 `cd backend && python -m pytest`（全量）全绿；mypy 基线零新增；ruff 通过
- [x] 11.2 `cd frontend && npm test` 全绿；`npm run lint` 通过
- [ ] 11.3 手工升级回归（本模块验收主体）：真实 v1.4.2 备份库跑脚本 → 全页面巡检账单/统计/模板显示正常；记账选"支出"可见并选中任意分类（含原收入类）、选"收入"同理；设置页分类管理单列表可添加/改名/换图标/拖拽、「其他」唯一置底；迁移前后月度收支合计数字不变
- [ ] 11.4 明暗主题、竖/宽屏自查；`frontend/dist` 不随本模块提交
