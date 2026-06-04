# VibeCoding Prompt — Money App v1.2

> 目标：基于 v1.1 代码库，实现 9 个 Bug 修复 + 5 个功能完善（详见需求文档和详细设计）。
> 整个过程无人参与，代码生成后需通过 pytest + mypy + ruff 检测。

---

## 项目上下文

- **后端**：Python 3.12, FastAPI, SQLModel (async), SQLite (aiosqlite)
- **前端**：Vue 3 (composition API), Vuetify 3, Pinia, Vue Router, Chart.js (vue-chartjs)
- **包管理器**：后端 `uv` (pip), 前端 `npm`
- **测试**：pytest + pytest-asyncio, httpx AsyncClient, 内存 SQLite
- **后端入口**：[backend/app/main.py](backend/app/main.py)
- **前端入口**：[frontend/src/main.js](frontend/src/main.js)
- **测试 conftest**：[backend/tests/conftest.py](backend/tests/conftest.py)
- **数据库文件**：`backend/money.db`（生产）；测试使用内存 SQLite

### 已有后端模块结构

```
backend/app/
├── main.py              FastAPI app + lifespan
├── config.py            配置常量
├── database.py          数据库引擎 + get_session 依赖
├── models/              SQLModel 数据模型
│   ├── record.py, budget.py, category.py, tag.py, attachment.py, user.py
├── schemas/             Pydantic 请求/响应 schema
├── routers/             API 路由层（调用 service）
├── services/            业务逻辑层（数据库操作）
└── utils/
    ├── auth.py          get_current_user(), require_auth(), JWT, 密码哈希
    └── response.py      标准 API 响应格式
```

### 已有前端模块结构

```
frontend/src/
├── main.js, App.vue
├── pages/               Dashboard, RecordList, RecordForm, RecordDetail,
│                         Statistics, Budget, Settings, Login
├── components/layout/   AppLayout.vue (侧边栏 + 顶栏 + FAB)
├── components/common/   ConfirmDialog, EmptyState, LoadingSpinner, ToastNotification
├── stores/              useAppStore, useRecordsStore, useStatisticsStore, useCategoriesStore
├── api/                 request.js (Axios + JWT 拦截器), records, categories, tags, stats, auth
├── router/              index.js (路由守卫)
├── utils/               format.js, constants.js
└── styles/              variables.scss, global.scss
```

### 关键约定

1. **API 响应格式**：所有接口用 `success_response(data=..., message=...)` 或 `error_response(code, msg)` 包裹
2. **认证模式**：`get_current_user()` 返回 `User | None`（不强制登录），`require_auth()` 返回 `User`（强制登录抛出 401）
3. **前端请求**：`request.js` 自动附带 JWT token（`Authorization: Bearer xxx`），无需手动处理
4. **测试数据库**：`conftest.py` 用 `sqlite+aiosqlite://` 内存库，`SQLModel.metadata.create_all` 建表后 `seed_categories()` 插入 5 个预设分类
5. **测试风格**：所有测试函数 `async def`，使用 `client: AsyncClient` fixture 发请求
6. **Ruff 配置**：select = ["E", "F", "I", "N", "W", "UP"], line-length = 100
7. **Mypy 配置**：strict = true, python_version = "3.12"
8. **前端使用 `useDisplay()` 获取响应式断点**：`display.mdAndUp`（≥960px 宽屏）, `display.smAndDown`（<960px 竖屏）

---

## 实现任务

### T1: 数据隔离（Bug 9 + Bug 10）【后端 + 数据库】

#### T1.1 数据库模型变更

修改 4 个模型文件，新增 `user_id` 字段：

**`backend/app/models/record.py`**：
```python
user_id: int | None = Field(default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE")
```

**`backend/app/models/budget.py`**：
```python
user_id: int | None = Field(default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE")
```
唯一的束从 `UniqueConstraint("category_id", "month")` 改为：
```python
UniqueConstraint("user_id", "category_id", "month", name="idx_budgets_user_category_month")
```

**`backend/app/models/category.py`**：
```python
user_id: int | None = Field(default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE")
```
唯一约束从 `UniqueConstraint("name", "type")` 改为：
```python
UniqueConstraint("user_id", "name", "type", name="idx_categories_user_name_type")
```
- `is_preset=1` 的分类保留 `user_id=NULL`（全局可见）
- 用户自定义分类 `is_preset=0` 关联 `user_id`

**`backend/app/models/tag.py`**：
```python
user_id: int | None = Field(default=None, nullable=True, foreign_key="users.id", ondelete="CASCADE")
```
新增唯一约束：
```python
__table_args__ = (UniqueConstraint("user_id", "name", name="idx_tags_user_name"),)
```

#### T1.2 Service 层变更

修改 5 个 service 文件，所有数据库操作按 `current_user` 过滤：

**统一规则**：

| 操作 | 登录用户 | 未登录 |
|------|---------|--------|
| 查询/列表 | 只查 `user_id == current_user.id` | 只查 `user_id IS NULL` |
| 创建 | 自动设置 `user_id = current_user.id` | 设置 `user_id = NULL` |
| 更新/删除 | 只能操作 `user_id == current_user.id` | 只能操作 `user_id IS NULL` |
| Category 特殊 | `is_preset=1` 对所有可见 | `is_preset=1` 对所有可见 |

**具体修改**：

- `services/record_service.py`：`create_record`, `get_records`, `get_record`, `update_record`, `delete_record`, `batch_delete_records`, `get_quick_templates` 均增加 `current_user: User | None = None` 参数，按规则过滤
- `services/budget_service.py`：`get_budgets`, `create_or_update_budget`, `update_budget`, `delete_budget`, `batch_set_budgets`, `get_budget_overview` 增加 `current_user` 参数，按规则过滤；`_enrich_budget` 中的 spent 查询也需按 user_id 过滤
- `services/category_service.py`：查询时 `is_preset=1` 对所有可见，`is_preset=0` 按 user_id 过滤；创建时对登录用户设 `user_id`，`is_preset=0`
- `services/tag_service.py`：与 category 同理
- `services/statistics_service.py`：`get_summary`, `get_category_stats`, `get_tag_stats`, `get_trend`, `get_compare` 均增加 `current_user` 参数，所有 Record 查询按 user_id 过滤

#### T1.3 Router 层变更

修改 6 个 router 文件，在每个路由函数中注入 `current_user: User | None = Depends(get_current_user)` 并传递给 service：

- `routers/records.py`
- `routers/budgets.py`
- `routers/categories.py`
- `routers/tags.py`
- `routers/statistics.py`

#### T1.4 注册时旧数据迁移

在 `routers/auth.py` 的 `register` 函数中，`await db.commit()` 之后增加：

```python
# 检查是否是第一个用户
from sqlmodel import select, func
from app.models.user import User
from app.models.record import Record
from app.models.budget import Budget
from app.models.category import Category
from app.models.tag import Tag

stmt = select(func.count(User.id))
result = await db.exec(stmt)
user_count = result.one()

if user_count == 1:
    # 将所有 user_id IS NULL 的旧数据归属到第一个用户
    for model in [Record, Budget, Tag]:
        stmt = select(model).where(model.user_id.is_(None))
        result = await db.exec(stmt)
        for obj in result.all():
            obj.user_id = user.id
    # Category: 只迁移 is_preset=0 的
    stmt = select(Category).where(Category.user_id.is_(None), Category.is_preset == 0)
    result = await db.exec(stmt)
    for obj in result.all():
        obj.user_id = user.id
    await db.commit()
```

> 注意：导入语句在文件顶部追加，不要重复导入已存在的。

#### T1.5 数据库迁移脚本

新建 `backend/migrate_to_v1.2.py`，独立脚本，手动执行。逻辑：
1. 检查各表是否已有 `user_id` 列（`PRAGMA table_info`）
2. 若无则执行 `ALTER TABLE ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE`
3. 打印迁移结果

```python
"""Migration script: add user_id columns for v1.2 data isolation."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "sqlite+aiosqlite:///./backend/money.db"

TABLES = ["records", "budgets", "categories", "tags"]

async def migrate():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        for table in TABLES:
            # Check if column exists
            result = await conn.exec(text(f"PRAGMA table_info({table})"))
            columns = [row[1] for row in await result.all()]
            if "user_id" not in columns:
                await conn.exec(text(
                    f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
                ))
                print(f"  ✓ Added user_id to {table}")
            else:
                print(f"  - user_id already exists in {table}")
    await engine.dispose()
    print("Migration completed.")

if __name__ == "__main__":
    asyncio.run(migrate())
```

#### T1.6 测试

更新现有测试文件以适配 user_id 过滤逻辑：
- `conftest.py`：新增 `auth_user` fixture（创建 User 并返回 token），或直接用 `client` fixture（不登录 = user_id IS NULL）
- 所有涉及 records/budgets/categories/tags 的测试需增加：
  - 未登录用户只能看到自己的数据（user_id=NULL）
  - 登录用户只能看到自己的数据
  - 第一个注册用户继承旧数据
  - 第二个注册用户看不到旧数据

在 `conftest.py` 新增以下 fixtures：

```python
from app.models.user import User
from app.utils.auth import get_password_hash, create_access_token

@pytest_asyncio.fixture
async def auth_user():
    """Create a test user and return it."""
    async with AsyncSession(test_engine) as session:
        user = User(username="testuser", hashed_password=get_password_hash("testpass"))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
async def auth_token(auth_user):
    """Create a JWT token for the test user."""
    return create_access_token(data={"sub": str(auth_user.id), "username": auth_user.username})

@pytest_asyncio.fixture
async def auth_client(client, auth_token):
    """Return a client with auth headers."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client
```

新增 `backend/tests/test_data_isolation.py`，测试以下场景：
1. 未登录用户创建记录 → `user_id` 为 NULL，未登录查询可见
2. 登录用户创建记录 → `user_id` 等于当前用户 ID，仅该用户可见
3. 注册第一个用户 → 所有 `user_id IS NULL` 的记录归属该用户
4. 注册第二个用户 → 看不到旧数据和第一个用户的数据
5. 预设分类（`is_preset=1`）对所有用户可见
6. 自定义分类仅创建者可见

---

### T2: 设置页修复（Bug 2 + Bug 3）【前端】

#### T2.1 Bug 根因

`SettingsPage.vue` 第 267 行：
```javascript
const categories = ref([])
// ...
categories.value = await categoriesStore.fetchCategories() || []
```

`categoriesStore.fetchCategories()` 没有 `return` 语句，始终返回 `undefined`，导致 `categories.value` 始终为 `[]`。

#### T2.2 修复方案

**方案**：修改 `SettingsPage.vue`，直接使用 store 的响应式数据，去掉本地 ref。

修改 `SettingsPage.vue` `<script setup>` 部分：

```javascript
// 修改前
const categories = ref([])
const tags = ref([])
const expenseCategories = computed(() => categories.value.filter(c => c.type === 'expense'))
const incomeCategories = computed(() => categories.value.filter(c => c.type === 'income'))

// 修改后 — 直接使用 store
const expenseCategories = computed(() =>
  categoriesStore.categories.filter(c => c.type === 'expense')
)
const incomeCategories = computed(() =>
  categoriesStore.categories.filter(c => c.type === 'income')
)
```

`loadCategories` 函数简化：
```javascript
async function loadCategories() {
  try {
    await categoriesStore.fetchCategories()
  } catch (e) {
    console.error('Load categories error:', e)
  }
}
```

`loadTags` 函数简化：
```javascript
async function loadTags() {
  try {
    await categoriesStore.fetchTags()
  } catch (e) {
    console.error('Load tags error:', e)
  }
}
```

模板中的 `categories` 改为 `categoriesStore.categories`，`tags` 改为 `categoriesStore.tags`。

#### T2.3 同时修复 store

`useCategoriesStore.js` 中 `fetchCategories()` 增加 return，失败时返回 `[]`：

```javascript
async function fetchCategories() {
  try {
    categories.value = await getCategories()
    loaded.value = true
    return categories.value
  } catch (e) {
    console.error('Failed to fetch categories:', e)
    return []
  }
}
```

---

### T3: UI 布局统一（Bug 1, 4, 5, 6）【前端】

#### T3.1 侧边栏宽度（Bug 1）

`AppLayout.vue` 第 10 行：
```javascript
// 修改前
:width="display.mdAndUp ? 240 : 72"
// 修改后
:width="display.mdAndUp ? 240 : 260"
```

#### T3.2 双按钮布局统一（Bug 4, 5, 6）

**涉及 3 个页面**：
- `RecordFormPage.vue`：顶部支出/收入切换按钮（第 17 行 `.d-flex.mb-4.ga-2`）
- `RecordDetailPage.vue`：底部编辑/删除按钮（第 119 行 `.d-flex.ga-3`）

**统一方案**：使用 `.dual-btn-container` CSS 类。

在 `RecordFormPage.vue` 中，修改支出/收入按钮容器：
```vue
<!-- 修改前 -->
<div class="d-flex mb-4 ga-2">

<!-- 修改后 -->
<div class="dual-btn-container mb-4">
```

按钮去掉 `block` prop，添加 `dual-btn` class：
```vue
<v-btn
  :color="recordType === 'expense' ? '#FF6B6B' : ''"
  :variant="recordType === 'expense' ? 'flat' : 'outlined'"
  size="large"
  rounded="xl"
  class="type-btn dual-btn expense-btn"
  ...
>
```

在 `RecordDetailPage.vue` 中，修改编辑/删除按钮容器：
```vue
<!-- 修改前 -->
<div class="d-flex ga-3">

<!-- 修改后 -->
<div class="dual-btn-container">
```

两个按钮去掉 `block` prop，添加 `dual-btn` class。

**全局 CSS**：在 `frontend/src/styles/global.scss` 中新增：

```scss
.dual-btn-container {
  display: flex;
  gap: 8px;
  justify-content: center;

  .dual-btn {
    flex: 1;
    max-width: 200px;
  }
}

@media (min-width: 960px) {
  .dual-btn-container .dual-btn {
    flex: 0 1 auto;
    min-width: 160px;
  }
}
```

---

### T4: 类型筛选修复（Bug 7）【前端】

`RecordListPage.vue` 第 204 行，参数名前后端不一致：
```javascript
// 修改前
if (filters.type) params.type_filter = filters.type
// 修改后
if (filters.type) params.type = filters.type
```

后端路由 `routers/records.py` 第 37 行的参数名是 `type`（对应 `type_filter` 传入 service）。前端传 `type_filter` 导致后端收到的始终为 None。

---

### T5: 快速记账改进（Bug 8 + 功能 4）【前端 + 后端】

#### T5.1 修复时间覆盖（Bug 8）

`RecordFormPage.vue` 的 `fillTemplate` 函数（第 295-312 行），删除覆盖时间的代码：

```javascript
function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  // 删除：if (tpl.consume_time) { consumeDate.value = ...; consumeTime.value = ...; }
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

#### T5.2 改为标签模板（功能 4）

**后端**：`services/record_service.py` 的 `get_quick_templates()` 改为按标签聚合：

```python
async def get_quick_templates(
    db: AsyncSession, current_user: User | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Get tag-based quick templates from history."""
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

    # 应用 user_id 过滤
    if current_user:
        query = query.where(Record.user_id == current_user.id)
    else:
        query = query.where(Record.user_id.is_(None))

    result = await db.exec(query)
    records = list(result.all())
    items = []
    for record in records:
        items.append(await _enrich_record(db, record))
    return items
```

**前端**：`RecordFormPage.vue` 的 chip 模板文本改为显示标签名：

```vue
<!-- 修改前 -->
{{ tpl.category_name }} · ¥{{ tpl.amount }}
<!-- 修改后 -->
{{ tpl.tag?.name || tpl.category_name }} · ¥{{ tpl.amount }}
```

---

### T6: 预算编辑（功能 1）【前端】

#### T6.1 新增 API 文件

新建 `frontend/src/api/budgets.js`：

```javascript
import request from './request'

export function getBudgets(params) {
  return request.get('/budgets', { params })
}

export function batchSetBudgets(data) {
  return request.post('/budgets/batch', data)
}

export function updateBudget(id, data) {
  return request.put(`/budgets/${id}`, data)
}

export function deleteBudget(id) {
  return request.delete(`/budgets/${id}`)
}
```

#### T6.2 重构 BudgetPage.vue

删除硬编码的 `budgets` ref（第 106-111 行），改为从 API 加载：

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

`totalBudget` 和 `totalSpent` 改为从 API 数据计算：
```javascript
const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
```

> 注意：后端返回字段是 `amount`（不是 `budget`），模板中 `item.budget` 改为 `item.amount`。

#### T6.3 编辑/删除按钮

在每个分类预算项右侧增加编辑和删除按钮：
```vue
<template v-slot:append>
  <div class="d-flex ga-1">
    <v-btn icon variant="text" size="x-small" @click="editBudget(item)">
      <v-icon size="small" color="grey">mdi-pencil</v-icon>
    </v-btn>
    <v-btn icon variant="text" size="x-small" @click="confirmDeleteBudget(item)">
      <v-icon size="small" color="error">mdi-delete</v-icon>
    </v-btn>
  </div>
</template>
```

编辑：点击编辑按钮 → 弹出对话框，预填当前分类和金额 → 修改后保存。
```javascript
function editBudget(item) {
  budgetForm.value.category_id = item.category_id
  budgetForm.value.amount = item.amount
  showAddDialog.value = true
  // 对话框标题根据情况显示"编辑分类预算"
}
```

删除：点击删除按钮 → ConfirmDialog 确认 → 调用 `deleteBudget(id)` → 刷新列表。

#### T6.4 saveBudget 函数

```javascript
async function saveBudget() {
  saving.value = true
  try {
    const month = dayjs().format('YYYY-MM')
    await batchSetBudgets({
      month,
      budgets: [{
        category_id: budgetForm.value.category_id,
        amount: budgetForm.value.amount,
      }],
    })
    showAddDialog.value = false
    budgetForm.value = { category_id: null, amount: 0 }
    await loadBudgets()
  } catch (e) {
    console.error('Save budget error:', e)
  } finally {
    saving.value = false
  }
}
```

---

### T7: 月份切换横条（功能 3）【前端】

在 `RecordListPage.vue` 的 filter-bar 上方新增月份横条组件。

#### T7.1 数据结构

```javascript
import dayjs from 'dayjs'

const currentMonth = ref(dayjs().format('YYYY-MM'))
const monthList = ref([])

function generateMonthRange() {
  const months = []
  const now = dayjs()
  let current = startMonth.value.clone()
  while (current.isBefore(now) || current.isSame(now, 'month')) {
    months.push({
      value: current.format('YYYY-MM'),
      label: MONTH_NAMES[current.month()],  // 中文数字月份
      year: current.year(),
      isCurrentYear: current.year() === now.year(),
    })
    current = current.add(1, 'month')
  }
  return months
}

const MONTH_NAMES = ['一月', '二月', '三月', '四月', '五月', '六月',
                     '七月', '八月', '九月', '十月', '十一月', '十二月']
```

#### T7.2 获取首条记录月份

```javascript
const startMonth = ref(dayjs())

async function getEarliestMonth() {
  try {
    const result = await getRecords({ page: 1, page_size: 1, sort_by: 'consume_time', sort_order: 'asc' })
    if (result.items.length > 0) {
      const dateStr = result.items[0].consume_time.substring(0, 7)
      startMonth.value = dayjs(dateStr + '-01')
    }
  } catch (e) { /* ignore */ }
}
```

#### T7.3 模板

在 filter-card 上方新增：

```vue
<!-- Month Switcher -->
<v-card class="pa-2 mb-3 month-bar" rounded="xl" v-if="monthList.length > 0">
  <div class="d-flex align-center">
    <v-btn
      v-if="display.mdAndUp"
      variant="text" icon size="small"
      @click="prevMonth"
    >
      <v-icon>mdi-chevron-left</v-icon>
    </v-btn>
    <div
      ref="monthScrollContainer"
      class="month-scroll d-flex ga-1 overflow-x-auto flex-grow-1"
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
      variant="text" icon size="small"
      @click="nextMonth"
    >
      <v-icon>mdi-chevron-right</v-icon>
    </v-btn>
  </div>
</v-card>
```

#### T7.4 交互逻辑

```javascript
async function switchMonth(month) {
  currentMonth.value = month
  const start = dayjs(month + '-01').format('YYYY-MM-DD')
  const end = dayjs(month + '-01').endOf('month').format('YYYY-MM-DD')
  filters.start_date = start
  filters.end_date = end
  await search()
}

function prevMonth() {
  const idx = monthList.value.findIndex(m => m.value === currentMonth.value)
  if (idx > 0) switchMonth(monthList.value[idx - 1].value)
}

function nextMonth() {
  const idx = monthList.value.findIndex(m => m.value === currentMonth.value)
  if (idx < monthList.value.length - 1) switchMonth(monthList.value[idx + 1].value)
}
```

#### T7.5 初始化

在 `onMounted` 中增加：
```javascript
await getEarliestMonth()
monthList.value = generateMonthRange()
// 默认选中当前月份
const now = dayjs().format('YYYY-MM')
filters.start_date = dayjs().startOf('month').format('YYYY-MM-DD')
filters.end_date = dayjs().endOf('month').format('YYYY-MM-DD')
```

添加 `display` 导入：
```javascript
import { useDisplay } from 'vuetify'
const display = useDisplay()
```

#### T7.6 样式

```scss
.month-bar {
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.month-scroll {
  scrollbar-width: none;
  -ms-overflow-style: none;
  &::-webkit-scrollbar {
    display: none;
  }
}

.month-chip {
  cursor: pointer;
  transition: all 0.15s ease;
}
```

---

### T8: 统计页柱状图（功能 2）【前端】

#### T8.1 替换 Pie 为 Bar

在 `StatisticsPage.vue` 的 "分类统计" 卡片中，将现有 Pie 图表替换为 Bar 柱状图。

#### T8.2 注册 Bar 组件

```javascript
// 修改导入
import { Bar, Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement,
  Title, Filler,
} from 'chart.js'

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement,
  Title, Filler,
)
```

保留 `Pie` 导入的移除，保留 `ArcElement` 注册（其他地方可能用到）。

#### T8.3 柱状图数据

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

#### T8.4 模板

将 Pie 图表的 `<div style="height: 200px;">` 内 `<Pie :data="categoryChartData" :options="chartOptions" />` 替换为：

```vue
<div style="height: 280px;">
  <Bar :data="barChartData" :options="barChartOptions" />
</div>
```

卡片标题改为 "分类支出柱状图"。

#### T8.5 移除不再使用的代码

删除 `categoryChartData` computed 和 `chartOptions`（Pie 专用配置），如果它们仅在 Pie 图表中使用。

---

## 测试要求

### 后端测试

1. **所有新增/修改的 service 函数必须有对应的 pytest 测试**
2. 测试覆盖：
   - `test_data_isolation.py`（新文件）：6 个测试场景（见 T1.6）
   - 更新 `test_records.py`：增加 user_id 过滤相关断言
   - 更新 `test_budgets.py`：增加 user_id 过滤相关断言
   - 更新 `test_categories.py`：增加 user_id 过滤 + is_preset 相关断言
   - 更新 `test_tags.py`：增加 user_id 过滤 + 唯一约束断言
   - 更新 `test_statistics.py`：增加 user_id 过滤相关断言
3. 测试风格遵循已有模式：async def + `client` fixture + `success_response` / `error_response` 断言

### 质量检查

1. **所有后端代码通过 mypy strict 模式** (`mypy backend/app --strict`)
2. **所有后端代码通过 ruff 检查** (`ruff check backend/app && ruff format --check backend/app`)
3. **所有 pytest 测试通过** (`pytest backend/tests/ -v`)
4. 前端代码无 eslint 错误

---

## 文件变更清单

| # | 操作 | 文件路径 | 模块 |
|:---:|:---:|---------|:---:|
| 1 | 修改 | `backend/app/models/record.py` | T1 |
| 2 | 修改 | `backend/app/models/budget.py` | T1 |
| 3 | 修改 | `backend/app/models/category.py` | T1 |
| 4 | 修改 | `backend/app/models/tag.py` | T1 |
| 5 | 修改 | `backend/app/services/record_service.py` | T1, T5 |
| 6 | 修改 | `backend/app/services/budget_service.py` | T1 |
| 7 | 修改 | `backend/app/services/category_service.py` | T1 |
| 8 | 修改 | `backend/app/services/tag_service.py` | T1 |
| 9 | 修改 | `backend/app/services/statistics_service.py` | T1 |
| 10 | 修改 | `backend/app/routers/records.py` | T1 |
| 11 | 修改 | `backend/app/routers/budgets.py` | T1 |
| 12 | 修改 | `backend/app/routers/categories.py` | T1 |
| 13 | 修改 | `backend/app/routers/tags.py` | T1 |
| 14 | 修改 | `backend/app/routers/statistics.py` | T1 |
| 15 | 修改 | `backend/app/routers/auth.py` | T1 |
| 16 | 新增 | `backend/migrate_to_v1.2.py` | T1 |
| 17 | 新增 | `backend/tests/test_data_isolation.py` | T1 |
| 18 | 修改 | `backend/tests/conftest.py` | T1 |
| 19 | 修改 | `backend/tests/test_records.py` | T1 |
| 20 | 修改 | `backend/tests/test_budgets.py` | T1 |
| 21 | 修改 | `backend/tests/test_categories.py` | T1 |
| 22 | 修改 | `backend/tests/test_tags.py` | T1 |
| 23 | 修改 | `backend/tests/test_statistics.py` | T1 |
| 24 | 修改 | `frontend/src/pages/SettingsPage.vue` | T2 |
| 25 | 修改 | `frontend/src/stores/useCategoriesStore.js` | T2 |
| 26 | 修改 | `frontend/src/components/layout/AppLayout.vue` | T3 |
| 27 | 修改 | `frontend/src/pages/RecordFormPage.vue` | T3, T5 |
| 28 | 修改 | `frontend/src/pages/RecordDetailPage.vue` | T3 |
| 29 | 修改 | `frontend/src/styles/global.scss` | T3 |
| 30 | 修改 | `frontend/src/pages/RecordListPage.vue` | T4, T7 |
| 31 | 新增 | `frontend/src/api/budgets.js` | T6 |
| 32 | 修改 | `frontend/src/pages/BudgetPage.vue` | T6 |
| 33 | 修改 | `frontend/src/pages/StatisticsPage.vue` | T8 |

---

## 执行顺序建议

1. **T1**（数据隔离）：最大改动量，先完成确保其他模块在此基础上运行
2. 运行 `backend/migrate_to_v1.2.py` 迁移数据库
3. **T2-T5**（Bug 修复）：可并行，互不依赖
4. **T6-T8**（功能完善）：可并行，互不依赖
5. 运行全量测试 + mypy + ruff 检查
