# 记账程序 v1.2 — 详细设计文档

> 版本：v1.2  
> 基于：v1.1（commit `7bef534`）  
> 技术栈：Python (FastAPI + SQLModel) + Vue 3 (Vuetify) + SQLite  
> 绘图库：Chart.js (vue-chartjs) — 项目中已存在

---

## 目录

1. [模块划分与依赖关系](#1-模块划分与依赖关系)
2. [模块 1：数据隔离](#2-模块-1数据隔离)
3. [模块 2：设置页修复](#3-模块-2设置页修复)
4. [模块 3：UI 布局统一](#4-模块-3ui-布局统一)
5. [模块 4：账单筛选修复](#5-模块-4账单筛选修复)
6. [模块 5：快速记账改进](#6-模块-5快速记账改进)
7. [模块 6：预算编辑](#7-模块-6预算编辑)
8. [模块 7：月份切换横条](#8-模块-7月份切换横条)
9. [模块 8：统计页柱状图](#9-模块-8统计页柱状图)
10. [测试要点](#10-测试要点)

---

## 1. 模块划分与依赖关系

### 1.1 模块列表

| 编号 | 模块名称 | 类型 | 涉及 Bug/功能 | 涉及层 |
|:---:|---------|:---:|:------------:|:------:|
| M1 | 数据隔离 | Bug 修复 | Bug 9, Bug 10 | 后端 + 数据库 |
| M2 | 设置页修复 | Bug 修复 | Bug 2, Bug 3 | 前端 |
| M3 | UI 布局统一 | Bug 修复 | Bug 1, Bug 4, Bug 5, Bug 6 | 前端 |
| M4 | 账单筛选修复 | Bug 修复 | Bug 7 | 前端 + 后端 |
| M5 | 快速记账改进 | 功能完善 | Bug 8, 功能 4 | 前端 |
| M6 | 预算编辑 | 功能完善 | 功能 1 | 前端 + 后端 |
| M7 | 月份切换横条 | 功能完善 | 功能 3 | 前端 |
| M8 | 统计页柱状图 | 功能完善 | 功能 2 | 前端 |

### 1.2 模块依赖关系

- **M1** 独立（数据库 schema 变更，影响所有后端路由）
- **M2** 独立（纯前端，仅涉及 SettingsPage.vue + useCategoriesStore.js）
- **M3** 独立（纯前端 CSS/布局）
- **M4** 独立（前端传参 + 后端已有逻辑修复）
- **M5** 独立（纯前端，修改 RecordFormPage.vue）
- **M6** 独立（前端对接已有后端 API，无需后端改动）
- **M7** 独立（纯前端，RecordListPage.vue 新增组件）
- **M8** 独立（纯前端，StatisticsPage.vue 新增 Bar 组件）

所有模块可独立开发和测试。

---

## 2. 模块 1：数据隔离

### 2.1 概述

当前所有业务表（records、budgets、categories、tags）均无 `user_id` 字段，导致跨账号数据泄露。本模块在所有业务表中新增 `user_id` 外键，并在所有查询/写入路由中按当前用户过滤。

### 2.2 数据库变更

#### 2.2.1 Record 模型

文件：`backend/app/models/record.py`

新增字段：

```python
user_id: int | None = Field(
    default=None,
    nullable=True,
    foreign_key="users.id",
    ondelete="CASCADE",
)
```

> 使用 `nullable=True` 以兼容已有旧数据（注册前的记录无 user_id）。

#### 2.2.2 Budget 模型

文件：`backend/app/models/budget.py`

新增字段：

```python
user_id: int | None = Field(
    default=None,
    nullable=True,
    foreign_key="users.id",
    ondelete="CASCADE",
)
```

唯一约束 `UniqueConstraint("category_id", "month")` 变更为 `UniqueConstraint("user_id", "category_id", "month", name="idx_budgets_user_category_month")`，使预算按用户隔离。

#### 2.2.3 Category 模型

文件：`backend/app/models/category.py`

新增字段：

```python
user_id: int | None = Field(
    default=None,
    nullable=True,
    foreign_key="users.id",
    ondelete="CASCADE",
)
```

> `is_preset` 的分类 (`is_preset=1`) 保留 `user_id=NULL`，作为全局预设分类对所有用户可见。
> 用户自定义分类 (`is_preset=0`) 关联 `user_id`。

唯一约束 `UniqueConstraint("name", "type")` 变更为 `UniqueConstraint("user_id", "name", "type", name="idx_categories_user_name_type")`。

#### 2.2.4 Tag 模型

文件：`backend/app/models/tag.py`

新增字段：

```python
user_id: int | None = Field(
    default=None,
    nullable=True,
    foreign_key="users.id",
    ondelete="CASCADE",
)
```

### 2.3 后端逻辑变更

#### 2.3.1 获取当前用户

所有业务路由目前均未注入 `current_user`。统一模式：在每个业务路由的依赖中增加 `current_user: User | None = Depends(get_current_user)`，用于读取时过滤和写入时赋值。

#### 2.3.2 统一规则

| 操作 | 登录用户 | 未登录用户 |
|------|---------|-----------|
| 查询列表 | 只查自己(`user_id=current_user.id`)的数据 + `user_id IS NULL` 的公共数据(仅 category) | 只查 `user_id IS NULL` 的数据 |
| 创建 | 自动设置 `user_id=current_user.id` | 设置 `user_id=NULL` |
| 更新/删除 | 只能操作自己的数据(`user_id=current_user.id`) | 只能操作 `user_id=NULL` 的数据 |

#### 2.3.3 旧数据迁移逻辑（注册时）

在 `POST /api/auth/register` 中，注册成功后插入迁移逻辑：

```python
# 检查是否是第一个用户（注册前数据库中用户数为 0）
stmt = select(func.count(User.id))
result = await db.exec(stmt)
user_count = result.one()

if user_count == 1:  # 当前注册用户是第一个用户
    # 将所有 user_id IS NULL 的 records 分配给该用户
    stmt = select(Record).where(Record.user_id.is_(None))
    result = await db.exec(stmt)
    orphan_records = list(result.all())
    for record in orphan_records:
        record.user_id = user.id
    # 同样处理 budgets、categories(is_preset=0)、tags
    await db.commit()
```

> 注意：user_count 检查是在当前用户已插入数据库后进行的查询，所以等于 1 表示这是第一个注册用户。

#### 2.3.4 受影响的路由文件

| 路由文件 | 变更内容 |
|---------|---------|
| `routers/records.py` | 所有接口增加 `current_user` 依赖，查询按 user_id 过滤，创建设置 user_id |
| `routers/budgets.py` | 同上 |
| `routers/categories.py` | 同上，但 `is_preset=1` 的分类对所有用户可见 |
| `routers/tags.py` | 同上 |
| `routers/statistics.py` | 查询按 user_id 过滤 |
| `routers/auth.py` | 注册后执行旧数据迁移 |

#### 2.3.5 关键变更示例（record_service.py）

```python
# 创建时
record = Record(
    ...,
    user_id=current_user.id if current_user else None,
)

# 查询时 - 所有查询需增加 user_id 过滤
if current_user:
    query = query.where(Record.user_id == current_user.id)
else:
    query = query.where(Record.user_id.is_(None))
```

### 2.4 前端变更

前端无需大幅修改。API 请求已自动携带 JWT token（`request.js` 拦截器），后端通过 token 识别用户。前端只需确保：

- `getCurrentUser()` 在 app 启动时调用，维护登录状态
- 路由守卫（`router/index.js`）保持现有逻辑
- 设置页的账号区域（已实现）保持不变

### 2.5 影响范围

- **后端**：6 个路由文件 + 5 个 service 文件需要修改
- **数据库**：4 张表新增字段，需用 SQLite ALTER TABLE 迁移（生产数据库需手动或通过脚本迁移）
- **前端**：几乎无影响（API 调用方式不变）

---

## 3. 模块 2：设置页修复

### 3.1 Bug 2：分类/标签无法新增

#### 3.1.1 根因分析

在 `SettingsPage.vue` 的 `loadCategories()` 中：

```javascript
// 当前代码
categories.value = await categoriesStore.fetchCategories() || []
```

`categoriesStore.fetchCategories()` 的返回值为 `undefined`（函数内部没有 `return` 语句），导致 `categories.value` 始终为 `[]`，即使 API 返回了数据。

#### 3.1.2 修复方案

方案 A（最小改动）：修改 `useCategoriesStore.js`，让 `fetchCategories()` 返回数据：

```javascript
async function fetchCategories() {
    try {
        categories.value = await getCategories()
        loaded.value = true
        return categories.value  // 增加 return
    } catch (e) {
        console.error('Failed to fetch categories:', e)
        return []  // 失败时返回空数组
    }
}
```

方案 B（推荐）：修改 `SettingsPage.vue`，直接使用 store 中的响应式数据而非本地 ref：

```javascript
// 使用 store 的 categories，而不是本地 ref
const categories = computed(() => categoriesStore.categories)
```

推荐方案 B，因为它消除了本地 ref 与 store ref 的双源问题，数据始终一致。

#### 3.1.3 标签新增

标签的 `saveTag()` 调用 `categoriesStore.addTag({ name: tagForm.name.trim() })`，对应的 `addTag` 方法调用 `createTag(data)` API。检查确认前端 API `POST /tags` 和后端 `TagCreate` schema 均正确，仅当 `fetchCategories` 修复后，页面整体数据流恢复正常。

### 3.2 Bug 3：设置页首次打开空白

#### 3.2.1 根因分析

与 Bug 2 同一根源：`categories` 本地 ref 因 `fetchCategories()` 无返回值而始终为空数组。页面模板依赖 `expenseCategories` 和 `incomeCategories`（基于本地 `categories` 的计算属性），数据显示为空。

"第二次打开才显示"的现象：可能因为页面组件缓存（`<keep-alive>`）或第二次加载时 API 返回数据被本地 ref 意外接收到。但修复 Bug 2 后此问题自然解决。

#### 3.2.2 修复方案

同 Bug 2 方案 B：改用 `categoriesStore.categories` 作为数据源。

### 3.3 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/stores/useCategoriesStore.js` | `fetchCategories()` 增加返回值 |
| `frontend/src/pages/SettingsPage.vue` | 去掉本地 `categories`/`tags` ref，改用 store 响应式数据 |

---

## 4. 模块 3：UI 布局统一

### 4.1 Bug 1：竖屏模式侧边栏过宽

#### 4.1.1 当前状况

文件：`frontend/src/components/layout/AppLayout.vue` 第 10 行：

```javascript
:width="display.mdAndUp ? 240 : 72"
```

竖屏下 `width=72` 已经是较小的值。但侧边栏实际上展开时使用的是 Vuetify 默认宽度（~256px），因为 `:rail="false"` 固定设置。

#### 4.1.2 修复方案

当前侧边栏逻辑：
- 竖屏（mobile）：`temporary=true`，`permanent=false`，`width=72`
- 宽屏折叠：`rail=true`（通过 toggleNav），`temporary=true`
- 宽屏展开：`rail=false`，`permanent=true`

实际上竖屏 `width` 是用于临时抽屉打开时的宽度。当前 72px 似乎是 rail 状态的宽度，而非展开宽度。

修复：
- 竖屏展开宽度：设为 260px（占屏幕约 70%，但不超过 300px）
- 保持竖屏下 `temporary` 模式，展开时宽度 260px

```javascript
:width="display.mdAndUp ? 240 : 260"
```

### 4.2 Bug 4/5/6：双按钮排版（支出/收入 + 编辑/删除）

#### 4.2.1 当前状况

`RecordFormPage.vue` 中支出/收入按钮使用 `block` 属性和 `ga-2` gap，在 flex 容器中等宽。宽屏下未明确居中。

#### 4.2.2 修复方案

使用统一的 CSS 类处理双按钮布局：

```vue
<!-- 双按钮容器 -->
<div class="dual-btn-container">
  <v-btn class="dual-btn" ... />
  <v-btn class="dual-btn" ... />
</div>
```

```css
.dual-btn-container {
  display: flex;
  gap: 8px;
  justify-content: center;   /* 宽屏居中 */
}

.dual-btn-container .dual-btn {
  flex: 1;                   /* 竖屏等宽 */
  max-width: 200px;          /* 防止按钮过宽 */
}

@media (min-width: 960px) {
  .dual-btn-container .dual-btn {
    flex: 0 1 auto;          /* 宽屏自适应宽度 */
    min-width: 160px;
  }
}
```

#### 4.2.3 涉及页面

| 页面文件 | 需要调整的元素 |
|---------|--------------|
| `RecordFormPage.vue` | 顶部支出/收入切换按钮 |
| `RecordDetailPage.vue` | 底部编辑/删除按钮（如存在） |

### 4.3 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/components/layout/AppLayout.vue` | 调整竖屏侧边栏宽度 |
| `frontend/src/pages/RecordFormPage.vue` | 双按钮布局统一 |
| `frontend/src/pages/RecordDetailPage.vue` | 双按钮布局统一（如存在） |

---

## 5. 模块 4：账单筛选修复

### 5.1 问题分析

`RecordListPage.vue` 第 204 行：

```javascript
if (filters.type) params.type_filter = filters.type
```

前端传给后端的参数名为 `type_filter`，后端 `routers/records.py` 第 37 行接收：

```python
type: str | None = Query(None, description="类型: income/expense"),
```

后端接收参数名为 `type`（不是 `type_filter`），而前端传的是 `type_filter`，导致类型筛选条件未被后端接收。

### 5.2 修复方案

#### 方案：修前端

`RecordListPage.vue` 第 204 行：

```javascript
// 修改前
if (filters.type) params.type_filter = filters.type
// 修改后
if (filters.type) params.type = filters.type
```

与后端参数名 `type` 对齐。`category_id` 筛选的传参名与后端一致（都是 `category_id`），所以没有问题。

### 5.3 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/pages/RecordListPage.vue` | 第 204 行改参数名 |

---

## 6. 模块 5：快速记账改进

### 6.1 Bug 8：填入历史时间

#### 6.1.1 当前状况

`RecordFormPage.vue` 的 `fillTemplate(tpl)` 函数（第 295-312 行）：

```javascript
function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  if (tpl.consume_time) {
    consumeDate.value = tpl.consume_time.substring(0, 10)
    consumeTime.value = tpl.consume_time.substring(11, 16)
  }
  // ...
}
```

`tpl.consume_time` 覆盖了当前的日期和时间。

#### 6.1.2 修复方案

删除 `fillTemplate` 中覆盖时间的代码块：

```javascript
function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  // 不再覆盖 consumeDate/consumeTime，保持当前时间
  if (tpl.tag) {
    selectedTagId.value = tpl.tag.id
    selectedTagName.value = tpl.tag.name
    onTagInput(tpl.tag.name)
  } else {
    selectedTagId.value = null
    selectedTagName.value = null
  }
  note.value = tpl.note || ''
}
```

### 6.2 功能 4：快速记账改为标签模板

#### 6.2.1 当前状况

快速记账区域展示最近 10 条历史记录，每条显示为 `category_name · ¥amount` 的 chip。数据来源：`GET /api/records/quick-templates` → `record_service.get_quick_templates()`，按 `updated_at DESC` 取最近记录。

#### 6.2.2 需求变更

- 展示内容改为**标签**（tag）模板，而非分类模板
- 展示格式：标签名及其对应的分类名、备注
- 点击后：填入该标签对应的分类、备注，不修改时间（Bug 8 修复）

#### 6.2.3 后端变更

`record_service.py` 的 `get_quick_templates()`：改为按标签（tag）去重聚合，返回每个标签最近一次使用的信息。

```python
async def get_quick_templates(
    db: AsyncSession, limit: int = 10
) -> list[dict[str, Any]]:
    """Get tag-based quick templates from history.

    For each distinct tag, return the most recent record's info.
    """
    # 子查询：按 tag_id 分组取每个标签最新的记录
    subquery = (
        select(
            Record.tag_id,
            func.max(Record.consume_time).label("max_time"),
        )
        .where(Record.tag_id.isnot(None))
        .group_by(Record.tag_id)
        .subquery()
    )

    query = (
        select(Record)
        .join(subquery, Record.tag_id == subquery.c.tag_id)
        .where(Record.consume_time == subquery.c.max_time)
        .order_by(Record.consume_time.desc())
        .limit(limit)
    )
    result = await db.exec(query)
    records = list(result.all())
    items = []
    for record in records:
        items.append(await _enrich_record(db, record))
    return items
```

返回数据结构不变（已包含 `tag`、`category_name`、`note`、`amount`）。

#### 6.2.4 前端变更

`RecordFormPage.vue` 的模板展示：

```vue
<v-chip
  v-for="tpl in templates.slice(0, 5)"
  :key="tpl.id"
  size="small"
  variant="tonal"
  @click="fillTemplate(tpl)"
  class="template-chip"
>
  <v-avatar size="20" class="mr-1" :color="tpl.type === 'expense' ? '#FFE8E8' : '#E8FFF3'">
    <v-icon size="12" :color="tpl.type === 'expense' ? '#FF6B6B' : '#20C997'">
      {{ tpl.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
    </v-icon>
  </v-avatar>
  {{ tpl.tag?.name || tpl.category_name }} · ¥{{ tpl.amount }}
</v-chip>
```

主要变更：chip 标签文本从 `category_name · ¥amount` 改为 `tag.name · ¥amount`。

### 6.3 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/pages/RecordFormPage.vue` | `fillTemplate` 删除时间覆盖 + chip 显示改为 tag 名称 |
| `backend/app/services/record_service.py` | `get_quick_templates` 改为按标签聚合 |

---

## 7. 模块 6：预算编辑

### 7.1 概述

当前 `BudgetPage.vue` 使用硬编码示例数据（第 106-111 行），未连接后端 API。后端预算 API（`routers/budgets.py` + `services/budget_service.py`）已完整实现了 CRUD，包括 upsert 和批量设置。

本模块将前端对接后端 API。

### 7.2 前端对接

#### 7.2.1 新增 API 调用

`frontend/src/api/budgets.js` — 新增文件：

```javascript
import request from './request'

export function getBudgets(params) {
  return request.get('/budgets', { params })
}

export function createBudget(data) {
  return request.post('/budgets', data)
}

export function updateBudget(id, data) {
  return request.put(`/budgets/${id}`, data)
}

export function deleteBudget(id) {
  return request.delete(`/budgets/${id}`)
}

export function batchSetBudgets(data) {
  return request.post('/budgets/batch', data)
}

export function getBudgetOverview(params) {
  return request.get('/statistics/budget-overview', { params })
}
```

#### 7.2.2 BudgetPage.vue 重构

替换硬编码数据为 API 调用：

```javascript
const budgets = ref([])

async function loadBudgets() {
  try {
    const month = dayjs().format('YYYY-MM')
    const data = await getBudgets({ month, type: 'expense' })
    budgets.value = data || []
  } catch (e) {
    console.error('Load budgets error:', e)
  }
}
```

> 注意：`getBudgets` 返回的已是带 `spent`、`remaining`、`percentage` 的富化数据（由 `_enrich_budget` 处理后返回）。

总预算和各分类预算的数值改为从 API 返回数据计算：

```javascript
const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
```

#### 7.2.3 编辑对话框增强（用户确认方案）

基于现有的「设置分类预算」对话框增强：

- 打开对话框时，如果该分类已有预算记录，预填已有金额（编辑模式）
- 使用 `batchSetBudgets` API 一次性保存所有修改
- 对话框标题根据是否有预算显示「编辑分类预算」或「设置分类预算」

```javascript
async function saveBudget() {
  saving.value = true
  try {
    const month = dayjs().format('YYYY-MM')
    const budgetsData = [{
      category_id: budgetForm.value.category_id,
      amount: budgetForm.value.amount,
    }]
    await batchSetBudgets({ month, budgets: budgetsData })
    showAddDialog.value = false
    await loadBudgets()
  } finally {
    saving.value = false
  }
}
```

### 7.3 后端调整

后端预算 API 当前功能完整，无需增加新接口。唯一需要确认的是：当前 `_enrich_budget` 和 `get_budget_overview` 中的金额计算使用 `Record.consume_time` 做日期范围过滤，该逻辑保持正确。

### 7.4 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/api/budgets.js` | 新增文件 |
| `frontend/src/pages/BudgetPage.vue` | 对接后端 API，替换硬编码数据，增强编辑对话框 |

---

## 8. 模块 7：月份切换横条

### 8.1 概述

在账单列表页（RecordListPage）标题栏下方新增一个横向月份切换横条，用户可通过该横条按月份筛选账单列表。

### 8.2 横条设计

#### 8.2.1 月份范围

从第一条账单记录所在月份起，到当前月份止。首次加载时从 API 获取最早的月份。

#### 8.2.2 年份标注规则

- 当前年份（如 2026 年）的月份：只显示「一月」「二月」……不显示年份
- 过去年份的月份：月份名称下方用小字标注年份，例如「2025」
- 未来月份：不显示（横条截止到当前月）

#### 8.2.3 交互

- **竖屏**：横条可左右滑动（touch swipe）
- **宽屏**：横条左右两侧有 `<` `>` 箭头按钮，点击逐月切换
- 默认选中**当前月份**
- 同一时间只显示一个月份的账单

### 8.3 数据结构

月份列表由前端生成（不需要额外的 API），逻辑如下：

```javascript
// 计算从有数据的第一月到当前月的月份列表
function generateMonthRange() {
  const months = []
  const now = dayjs()
  // startMonth 从 API 获取或从第一条记录推算
  // 如果没有数据，默认从当前月开始
  let current = startMonth.clone()
  while (current.isBefore(now) || current.isSame(now, 'month')) {
    months.push({
      value: current.format('YYYY-MM'),  // "2026-01"
      label: current.format('M月'),       // "1月"
      year: current.year(),
      isCurrentYear: current.year() === now.year(),
    })
    current = current.add(1, 'month')
  }
  return months
}
```

### 8.4 组件结构

在 `RecordListPage.vue` 的 filter-bar 上方新增月份横条：

```vue
<!-- Month Switcher -->
<v-card class="pa-2 mb-3 month-bar" rounded="xl">
  <div class="d-flex align-center">
    <v-btn
      v-if="display.mdAndUp"
      variant="text"
      icon
      size="small"
      @click="prevMonth"
    >
      <v-icon>mdi-chevron-left</v-icon>
    </v-btn>
    <div
      ref="monthScrollContainer"
      class="month-scroll d-flex ga-1 overflow-x-auto flex-grow-1"
      @touchend="onMonthTouchEnd"
    >
      <v-chip
        v-for="m in monthList"
        :key="m.value"
        :color="currentMonth === m.value ? 'primary' : ''"
        variant="tonal"
        size="small"
        class="month-chip flex-shrink-0"
        @click="switchMonth(m.value)"
      >
        <div class="text-center">
          <div>{{ m.label }}</div>
          <div v-if="!m.isCurrentYear" class="text-caption" style="font-size: 9px; line-height: 1;">
            {{ m.year }}
          </div>
        </div>
      </v-chip>
    </div>
    <v-btn
      v-if="display.mdAndUp"
      variant="text"
      icon
      size="small"
      @click="nextMonth"
    >
      <v-icon>mdi-chevron-right</v-icon>
    </v-btn>
  </div>
</v-card>
```

### 8.5 月份切换逻辑

```javascript
const currentMonth = ref(dayjs().format('YYYY-MM'))
const monthList = ref([])

async function switchMonth(month) {
  currentMonth.value = month
  // 更新日期筛选
  const start = dayjs(month + '-01').format('YYYY-MM-DD')
  const end = dayjs(month + '-01').endOf('month').format('YYYY-MM-DD')
  filters.start_date = start
  filters.end_date = end
  await search()
}

function prevMonth() {
  const idx = monthList.value.findIndex(m => m.value === currentMonth.value)
  if (idx > 0) {
    switchMonth(monthList.value[idx - 1].value)
  }
}

function nextMonth() {
  const idx = monthList.value.findIndex(m => m.value === currentMonth.value)
  if (idx < monthList.value.length - 1) {
    switchMonth(monthList.value[idx + 1].value)
  }
}
```

### 8.6 获取首条记录月份（确定月份范围起点）

新增 API 调用或扩展现有 `GET /api/records` 以获取最早月份。最简单方案：在 `onMounted` 中额外调用一次：

```javascript
async function getEarliestMonth() {
  try {
    const result = await getRecords({ page: 1, page_size: 1, sort_by: 'consume_time', sort_order: 'asc' })
    if (result.items.length > 0) {
      return result.items[0].consume_time.substring(0, 7)  // "YYYY-MM"
    }
  } catch (e) { /* ignore */ }
  return dayjs().format('YYYY-MM')
}
```

### 8.7 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/pages/RecordListPage.vue` | 新增月份横条组件 + 月份切换逻辑 |
| `frontend/src/components/layout/AppLayout.vue` | 可能需要调整 content-wrapper 的 max-width 以适应月份横条 |

---

## 9. 模块 8：统计页柱状图

### 9.1 概述

在 StatisticsPage 的「分类统计」区域新增柱状图，展示各分类的支出总金额。

### 9.2 技术方案

项目已集成 Chart.js + vue-chartjs，已有 `Pie` 和 `Line` 组件的使用。新增 `Bar` 组件。

### 9.3 实现细节

#### 9.3.1 注册 Bar 组件

在 `StatisticsPage.vue` 中：

```javascript
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement,  // 新增
  Title, Filler,
} from 'chart.js'

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement,  // 注册
  Title, Filler,
)
```

#### 9.3.2 柱状图模板

```vue
<!-- Category Bar Chart -->
<v-card class="pa-4 mb-3 chart-card" rounded="xl">
  <div class="d-flex justify-space-between align-center mb-3">
    <span class="text-subtitle-2 font-weight-bold">分类支出柱状图</span>
    <v-chip size="x-small" variant="tonal" color="grey">支出</v-chip>
  </div>
  <div v-if="categoryStats.length === 0" class="text-center pa-6 text-grey text-caption">
    暂无数据
  </div>
  <div v-else style="height: 280px;">
    <Bar :data="barChartData" :options="barChartOptions" />
  </div>
</v-card>
```

#### 9.3.3 柱状图数据

```javascript
const barChartData = computed(() => ({
  labels: categoryStats.value.map((c) => c.category_name),
  datasets: [{
    label: '支出金额',
    data: categoryStats.value.map((c) => c.total),
    backgroundColor: chartColors.slice(0, categoryStats.value.length).map(c => c + 'CC'),
    borderColor: chartColors.slice(0, categoryStats.value.length),
    borderWidth: 1,
    borderRadius: 6,
    maxBarThickness: 40,
  }],
}))

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `¥${Number(ctx.raw).toLocaleString()}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 11 } },
    },
    y: {
      grid: { color: 'rgba(0,0,0,0.04)' },
      beginAtZero: true,
      ticks: {
        font: { size: 10 },
        callback: (val) => `¥${val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val}`,
      },
    },
  },
}
```

### 9.4 放置位置

在「分类统计」卡片中，替换当前 Pie 图表区域。保持卡片的下方分类列表不变（展示各分类金额和占比）。

### 9.5 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/pages/StatisticsPage.vue` | 新增 Bar 组件及相关数据/选项，替换 Pie |

---

## 10. 测试要点

### 10.1 M1 数据隔离

| 测试场景 | 预期结果 |
|---------|---------|
| 未登录时创建账单 | 账单 user_id 为 NULL |
| 注册第一个账号 | 所有 user_id NULL 的记录归属该账号 |
| 注册第二个账号 | 看不到第一个账号的数据和旧数据 |
| 登录账号 A 创建账单 → 退出 → 注册 B | B 看不到 A 的账单 |
| 未登录用户查看账单 | 只看到 user_id NULL 的记录（无数据时显示空） |

### 10.2 M2 设置页修复

| 测试场景 | 预期结果 |
|---------|---------|
| 首次进入设置页 | 分类和标签正常显示 |
| 新增分类 | 输入名称后保存，列表中即时显示 |
| 新增标签 | 输入标签名后保存，列表中即时显示 |

### 10.3 M3 UI 布局

| 测试场景 | 预期结果 |
|---------|---------|
| 竖屏打开侧边栏 | 宽度适中，不遮挡过多内容 |
| 竖屏下记账页 | 支出/收入按钮各占 50% |
| 宽屏下记账页 | 支出/收入按钮居中显示 |
| 详情页编辑/删除按钮 | 同上规则 |

### 10.4 M4 筛选修复

| 测试场景 | 预期结果 |
|---------|---------|
| 选择类型「支出」 | 列表只显示支出记录 |
| 选择类型「收入」 | 列表只显示收入记录 |
| 同时选择类型 + 分类 | 两个条件同时生效 |
| 清除筛选 | 显示所有记录 |

### 10.5 M5 快速记账

| 测试场景 | 预期结果 |
|---------|---------|
| 点击快速记账模板 | 分类、标签、备注自动填入 |
| 点击后时间字段 | 保持当前时间，不被覆盖 |
| 模板显示内容 | 标签名（而非分类名） |

### 10.6 M6 预算编辑

| 测试场景 | 预期结果 |
|---------|---------|
| 打开预算页 | 显示当前月的预算数据（非硬编码） |
| 设置分类预算 | 保存后数值更新，总预算重新计算 |
| 编辑已有预算 | 预填已有金额，修改后保存 |

### 10.7 M7 月份横条

| 测试场景 | 预期结果 |
|---------|---------|
| 横条显示 | 从首条记录月份到当前月 |
| 年份标注 | 当前年的月无年份，过去年份有年份标注 |
| 竖屏滑动 | 横条可左右滑动查看更多月份 |
| 宽屏箭头 | 左右箭头逐月切换 |
| 点击月份 | 下方列表切换为对应月份账单 |
| 默认状态 | 选中当前月份 |

### 10.8 M8 柱状图

| 测试场景 | 预期结果 |
|---------|---------|
| 有支出数据 | 柱状图正确显示各分类金额 |
| 无数据 | 显示「暂无数据」提示 |
| 切换统计周期 | 柱状图数据同步更新 |
| 不同分类颜色 | 每个分类使用不同颜色 |

---

## 附录：文件变更清单汇总

| # | 操作 | 文件路径 |
|:---:|:---:|---------|
| 1 | 修改 | `backend/app/models/record.py` |
| 2 | 修改 | `backend/app/models/budget.py` |
| 3 | 修改 | `backend/app/models/category.py` |
| 4 | 修改 | `backend/app/models/tag.py` |
| 5 | 修改 | `backend/app/routers/records.py` |
| 6 | 修改 | `backend/app/routers/budgets.py` |
| 7 | 修改 | `backend/app/routers/categories.py` |
| 8 | 修改 | `backend/app/routers/tags.py` |
| 9 | 修改 | `backend/app/routers/statistics.py` |
| 10 | 修改 | `backend/app/routers/auth.py` |
| 11 | 修改 | `backend/app/services/record_service.py` |
| 12 | 修改 | `backend/app/services/budget_service.py` |
| 13 | 修改 | `backend/app/services/category_service.py` |
| 14 | 修改 | `backend/app/services/tag_service.py` |
| 15 | 修改 | `backend/app/services/statistics_service.py` |
| 16 | 修改 | `frontend/src/pages/SettingsPage.vue` |
| 17 | 修改 | `frontend/src/stores/useCategoriesStore.js` |
| 18 | 修改 | `frontend/src/components/layout/AppLayout.vue` |
| 19 | 修改 | `frontend/src/pages/RecordFormPage.vue` |
| 20 | 修改 | `frontend/src/pages/RecordListPage.vue` |
| 21 | 修改 | `frontend/src/pages/StatisticsPage.vue` |
| 22 | 修改 | `frontend/src/pages/BudgetPage.vue` |
| 23 | 修改 | `frontend/src/pages/RecordDetailPage.vue` |
| 24 | 新增 | `frontend/src/api/budgets.js` |
