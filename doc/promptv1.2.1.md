# Money App v1.2.1 — VibeCoding Prompt

> 本文件是 v1.2.1 版本的 VibeCoding 起始 Prompt。
> 目标：自动完成 14 个独立模块的开发、测试和质量检查，无需人工干预。

---

## 一、项目上下文

### 项目概述

Money App 是一个全栈个人记账应用：

- **后端**：Python 3.12 + FastAPI + SQLModel（async） + SQLite（aiosqlite）
- **前端**：Vue 3（Composition API） + Vuetify 3 + Pinia + Vue Router 4 + Chart.js
- **项目结构**：`backend/`（后端）、`frontend/`（前端）、`doc/`（文档）

### 后端架构

三层架构：Router → Service → Model

```
backend/app/
  models/       # SQLModel 表定义（User, Record, Category, Tag, Budget, Attachment）
  schemas/      # Pydantic 请求/响应模型
  routers/      # FastAPI 路由（/api/...），统一返回 success_response/error_response
  services/     # 业务逻辑层，async 函数
  utils/        # auth.py（JWT/bcrypt）、response.py（统一响应/错误码）、file_utils.py
  database.py   # async SQLAlchemy 引擎 + get_session()
  config.py     # 环境变量配置
  main.py       # FastAPI 入口，CORS、lifespan、路由注册
```

### 前端架构

```
frontend/src/
  pages/        # 页面组件（RecordFormPage, RecordListPage, SettingsPage 等）
  components/   # 布局（AppLayout）+ 通用组件（ConfirmDialog, EmptyState 等）
  stores/       # Pinia stores（useAppStore, useRecordsStore, useCategoriesStore, useStatisticsStore）
  api/          # Axios 封装（request.js + 各模块 API）
  utils/        # format.js（格式化）、constants.js（常量）
  styles/       # global.scss、variables.scss
  router/       # Vue Router（hash 模式）
```

### 数据隔离模式

支持匿名和登录两种模式。登录用户的数据通过 `user_id` FK 隔离：
- 查询时按 `user_id` 过滤（登录用户看自己的，匿名用户看 `user_id IS NULL` 的）
- 写操作（update/delete）**当前缺少所有权校验**（模块 10 修复）

### 错误码定义（`backend/app/utils/response.py`）

```python
class Code:
    SUCCESS = 0
    PARAM_ERROR = 40001
    NOT_FOUND = 40002
    CONFLICT = 40003
    FILE_INVALID = 40004
    # FORBIDDEN 需新增（模块 10）
    SERVER_ERROR = 50001
```

### 统一响应格式

```json
{ "code": 0, "message": "success", "data": { ... } }
```

### 测试基础设施

- 框架：pytest + pytest-asyncio（`asyncio_mode = "auto"`）
- 数据库：内存 SQLite（每个测试函数独立建表/删表）
- Fixtures：`client`（匿名）、`auth_client`（JWT 认证）、`setup_database`（autouse）
- 测试文件：`backend/tests/test_*.py`
- 运行：`cd backend && pytest tests/ -v`

### 质量检查命令

```bash
cd backend && mypy app --strict
cd backend && ruff check app
cd backend && ruff format --check app
```

---

## 二、v1.2.1 总体目标

修复 13 个 Bug + 补全 4 个功能（去重后 14 个独立模块）。

### 模块与文件映射

| 模块 | 简述 | 修改文件 | 优先级 |
|:---:|------|----------|:------:|
| 1 | 竖屏侧边栏缩窄 | `AppLayout.vue` | P1 |
| 2 | 快速记账时间保留 | `RecordFormPage.vue` | P0 |
| 3 | 账单页月份切换横条 | `RecordListPage.vue` | P2 |
| 4 | 快速记账显示标签名 | `RecordFormPage.vue` | P2 |
| 5 | 标签删除确认问题 | `SettingsPage.vue` | P0 |
| 6 | 预设分类支持删除 | `category_service.py` `categories.py` `SettingsPage.vue` | P1 |
| 7 | 登录后边栏刷新 | `AppLayout.vue` `LoginPage.vue` | P0 |
| 8 | 深色模式滚动条 | `global.scss` | P1 |
| 9 | 深色模式文字颜色 | `global.scss` | P1 |
| 10 | 数据隔离所有权校验 | `record_service.py` `category_service.py` `tag_service.py` `records.py` `categories.py` `tags.py` `response.py` | P0 |
| 11 | 统计页饼图改柱状图 | `statistics_service.py` `StatisticsPage.vue` | P1 |
| 12 | 支出/收入按钮等宽 | `RecordFormPage.vue` | P1 |
| 13 | 设置页分类列表不显示 | `SettingsPage.vue` `useCategoriesStore.js` | P0 |
| 14 | 预算页支持编辑 | `BudgetPage.vue` | P0 |

---

## 三、执行策略

### 主 Agent 职责

1. 按文件分组创建子 Agent（见下方分组），每组一个子 Agent
2. 跟踪所有子 Agent 的执行进度
3. 子 Agent 全部完成后，运行全局验证：
   - `cd backend && pytest tests/ -v`（全部通过）
   - `cd backend && mypy app --strict`（无错误）
   - `cd backend && ruff check app`（无错误）
   - `cd backend && ruff format --check app`（无错误）
4. 如有失败，生成修复子 Agent 重试
5. 输出最终完成报告

### 子 Agent 分组

共 **10 个子 Agent**，按修改文件分组：

| 子 Agent | 文件/模块 | 类型 | 测试要求 |
|----------|----------|------|----------|
| Agent-1 | Backend: 数据隔离校验（模块 10） | 后端 | pytest |
| Agent-2 | Backend: 分类级联删除 + 统计 type 字段（模块 6 后端 + 模块 11 后端） | 后端 | pytest |
| Agent-3 | Frontend: RecordFormPage（模块 2、4、12） | 前端 | 无 |
| Agent-4 | Frontend: SettingsPage + useCategoriesStore（模块 5、6 前端、13） | 前端 | 无 |
| Agent-5 | Frontend: AppLayout + LoginPage（模块 1、7） | 前端 | 无 |
| Agent-6 | Frontend: global.scss（模块 8、9） | 前端 | 无 |
| Agent-7 | Frontend: RecordListPage（模块 3） | 前端 | 无 |
| Agent-8 | Frontend: StatisticsPage（模块 11 前端） | 前端 | 无 |
| Agent-9 | Frontend: BudgetPage（模块 14） | 前端 | 无 |

### 执行顺序

所有子 Agent 可并行启动（模块间无依赖）。但同一文件的修改需注意冲突：
- Agent-1 和 Agent-2 都修改 `category_service.py` 和 `categories.py`，需协调（建议 Agent-1 先完成，Agent-2 在其基础上追加）
- 其余 Agent 独立，可完全并行

建议顺序：
1. **第一批（并行）**：Agent-1、Agent-3、Agent-4、Agent-5、Agent-6、Agent-7、Agent-8、Agent-9
2. **第二批**：Agent-2（在 Agent-1 完成后）

---

## 四、子 Agent 详细指令

---

### Agent-1：Backend — 数据隔离所有权校验（模块 10）

**目标**：在 update/delete 操作中增加所有权校验，用户只能操作自己的数据。

**修改文件**：

1. `backend/app/utils/response.py` — 新增 `FORBIDDEN` 错误码
   ```python
   FORBIDDEN = 40005  # 不与现有码冲突
   ```

2. `backend/app/services/record_service.py`
   - `update_record()` 增加 `current_user: User | None = None` 参数
   - `delete_record()` 增加 `current_user: User | None = None` 参数
   - `batch_delete_records()` 增加 `current_user: User | None = None` 参数
   - 每个方法在操作前校验 `record.user_id` 与 `current_user.id` 是否匹配
   - 不匹配时 `raise PermissionError("无权操作")`
   - 匿名用户（`current_user is None`）操作有 `user_id` 的数据也拒绝

3. `backend/app/services/tag_service.py`
   - `update_tag()` 增加 `current_user` 参数，校验所有权
   - `delete_tag()` 增加 `current_user` 参数，校验所有权
   - 不匹配返回 `{"code": Code.FORBIDDEN, "message": "无权操作"}`

4. `backend/app/routers/records.py`
   - `update_record`、`delete_record`、`batch_delete` 路由增加 `current_user: User | None = Depends(get_current_user)` 依赖
   - 将 `current_user` 传入 service 调用
   - 捕获 `PermissionError` 返回 `error_response(Code.FORBIDDEN, str(e))`

5. `backend/app/routers/tags.py`
   - `update_tag`、`delete_tag` 路由增加 `current_user` 依赖并传入 service

**测试要求**：

修改或新增 `backend/tests/test_data_isolation.py`，覆盖以下场景：

```python
# 记录相关
# 1. 用户 A 创建记录，用户 B 更新 → 403
# 2. 用户 A 创建记录，用户 B 删除 → 403
# 3. 用户 A 创建记录，用户 B 批量删除 → 403

# 分类相关
# 4. 用户 A 创建自定义分类，用户 B 更新 → 403
# 5. 用户 A 创建自定义分类，用户 B 删除 → 403
# 6. 预设分类：所有用户可编辑/删除（不受所有权限制）

# 标签相关
# 7. 用户 A 创建标签，用户 B 更新 → 403
# 8. 用户 A 创建标签，用户 B 删除 → 403

# 正常操作
# 9. 用户操作自己的数据 → 正常（200）
# 10. 匿名用户操作有 user_id 的数据 → 403
```

测试需使用双用户 fixture（`auth_client_a` 和 `auth_client_b`），参考现有 `conftest.py` 中的 `auth_client` 模式。

**验收标准**：
- 所有新增测试通过
- `mypy app --strict` 无错误
- `ruff check app` 无错误
- 现有测试不受影响

---

### Agent-2：Backend — 分类级联删除 + 统计 type 字段（模块 6 后端 + 模块 11 后端）

**前置条件**：Agent-1 已完成（`Code.FORBIDDEN` 已定义，`category_service.py` 的 `delete_category` 已有 `current_user` 参数）

**目标 A：分类级联删除（模块 6 后端）**

修改 `backend/app/services/category_service.py` 的 `delete_category()`：
- 移除"有关联账单则拒绝删除"的逻辑
- 新增级联删除：删除分类时，同时删除该分类下的所有关联记录（Record）和预算（Budget）
- 返回 `{"deleted_records": record_count}` 供前端提示
- 所有权校验：预设分类所有人可删，自定义分类仅创建者可删（已在 Agent-1 中添加）

修改 `backend/app/routers/categories.py`：

1. `delete_category` 路由：
   - 传入 `current_user`
   - 捕获 `PermissionError` 返回 403
   - 返回删除成功消息，有关联账单时提示删除数量

2. `update_category` 路由：
   - 增加 `current_user: User | None = Depends(get_current_user)` 依赖
   - 将 `current_user` 传入 `category_service.update_category()`
   - 捕获 `PermissionError` 返回 `error_response(Code.FORBIDDEN, str(e))`

**目标 B：统计 type 字段（模块 11 后端）**

修改 `backend/app/services/statistics_service.py` 的 `get_category_stats()`：
- 在返回的每项数据中增加 `"type": type_filter` 字段
- 这是一个向后兼容的新增字段

**测试要求**：

1. 扩展 `backend/tests/test_categories.py`：
   ```python
   # 1. 删除无关联账单的分类 → 成功，返回 deleted_records=0
   # 2. 删除有关联账单的分类 → 成功，返回 deleted_records=N，账单被级联删除
   # 3. 删除有关联预算的分类 → 成功，预算被级联删除
   # 4. 删除不存在的分类 → 404
   # 5. 用户 B 删除用户 A 的自定义分类 → 403
   # 6. 任何用户删除预设分类 → 成功（预设分类不受所有权限制）
   # 7. 级联删除后，查询记录列表确认关联记录已删除
   ```

2. 扩展 `backend/tests/test_statistics.py`：
   ```python
   # 1. get_category_stats 返回的数据包含 type 字段
   # 2. type 字段值与查询的 type_filter 参数一致
   ```

**验收标准**：
- 所有新增测试通过
- `mypy app --strict` 无错误
- `ruff check app` 无错误
- 现有测试不受影响

---

### Agent-3：Frontend — RecordFormPage（模块 2、4、12）

**修改文件**：`frontend/src/pages/RecordFormPage.vue`

**模块 2：快速记账时间保留**

修改 `fillTemplate()` 函数，将时间重置为当前时间（而非模板的历史时间）：

```javascript
function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  // 时间重置为当前时间
  consumeDate.value = dayjs().format('YYYY-MM-DD')
  consumeTime.value = dayjs().format('HH:mm')
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

**模块 4：快速记账显示标签名**

修改模板中快速记账 chip 的显示文字（约第 200 行）：

```html
<!-- 修改前 -->
{{ tpl.category_name }} · ¥{{ tpl.amount }}

<!-- 修改后 -->
{{ tpl.tag?.name || tpl.category_name }} · ¥{{ tpl.amount }}
```

**模块 12：支出/收入按钮等宽**

移除两个按钮的 `block` 属性，改用 `flex-grow-1`：

```html
<!-- 修改前 -->
<v-btn ... block size="large" rounded="xl" class="type-btn expense-btn" ...>

<!-- 修改后 -->
<v-btn ... size="large" rounded="xl" class="type-btn expense-btn flex-grow-1" ...>
```

两个按钮（expense 和 income）都做同样修改。

**验收标准**：
- 点击快速记账模板，时间重置为当前时间
- 快速记账 chip 优先显示标签名，无标签时显示分类名
- 支出/收入按钮等宽并排，各占 50%

---

### Agent-4：Frontend — SettingsPage + useCategoriesStore（模块 5、6 前端、13）

**修改文件**：`frontend/src/pages/SettingsPage.vue`、`frontend/src/stores/useCategoriesStore.js`

**模块 5：标签删除确认问题**

移除 `v-chip` 的 `closable` 属性，改为独立删除图标：

```html
<!-- 修改前 -->
<v-chip v-for="tag in tags" :key="tag.id" closable size="small" variant="tonal" class="mb-1"
  @click:close="confirmDeleteTag(tag)">
  <v-icon start size="x-small">mdi-tag</v-icon>
  {{ tag.name }}
</v-chip>

<!-- 修改后 -->
<v-chip v-for="tag in tags" :key="tag.id" size="small" variant="tonal" class="mb-1">
  <v-icon start size="x-small">mdi-tag</v-icon>
  {{ tag.name }}
  <template v-slot:append>
    <v-icon size="x-small" class="ml-1 tag-delete-icon" @click.stop="confirmDeleteTag(tag)">
      mdi-close
    </v-icon>
  </template>
</v-chip>
```

新增样式：
```css
.tag-delete-icon {
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.15s ease;
}
.tag-delete-icon:hover {
  opacity: 1;
  color: rgb(var(--v-theme-error));
}
```

**模块 6 前端：预设分类支持删除**

1. 移除删除按钮的 `v-if="!cat.is_preset"` 条件（支出分类和收入分类两处都改）

2. 修改 `confirmDeleteCategory()` 查询关联账单数量：
```javascript
const deleteCategoryMessage = ref('')

async function confirmDeleteCategory(cat) {
  deletingCategory.value = cat
  try {
    const result = await getRecords({ category_id: cat.id, page_size: 1 })
    const count = result.total || 0
    if (count > 0) {
      deleteCategoryMessage.value = `「${cat.name}」下有 ${count} 条账单记录，删除分类将同时删除所有关联账单，确认删除？`
    } else {
      deleteCategoryMessage.value = `确定要删除「${cat.name}」吗？`
    }
  } catch {
    deleteCategoryMessage.value = `确定要删除「${cat.name}」吗？`
  }
  showDeleteCategoryDialog.value = true
}
```

3. 确认对话框使用动态消息：
```html
<ConfirmDialog
  v-model="showDeleteCategoryDialog"
  title="删除分类"
  :message="deleteCategoryMessage"
  confirm-text="删除"
  @confirm="handleDeleteCategory"
/>
```

**模块 13：设置页分类列表不显示**

按数据流逐层排查：后端 API → 前端 API 模块 → Pinia Store → SettingsPage 渲染。

排查步骤：

1. **验证后端 API**：`GET /api/categories` 返回 `{ code: 0, data: [...] }` 格式，data 为分类数组
2. **检查前端 API 解包**：`request.js` 响应拦截器在 `code === 0` 时返回 `res.data`，确认 `getCategories()` 返回的是数组
3. **检查 Store 处理**：`useCategoriesStore.js` 的 `fetchCategories()` 中 `categories.value = await getCategories()` 应赋值为数组
4. **检查 SettingsPage 调用**：`loadCategories()` 中 `categories.value = await categoriesStore.fetchCategories()` — 注意 `fetchCategories()` 无显式返回值（返回 `undefined`），导致本地 ref 被赋值为 `undefined`

修复方案：

`SettingsPage.vue` — 改用 Store 的响应式引用（推荐）：
```javascript
// 修改前
const categories = ref([])
async function loadCategories() {
  categories.value = await categoriesStore.fetchCategories() || []
}

// 修改后：直接使用 Store 的响应式引用
const categories = categoriesStore.categories
// 删除 loadCategories() 调用（Store 已在初始化时加载）
```

`useCategoriesStore.js` — 确保 `fetchCategories()` 有正确的行为：
```javascript
async function fetchCategories() {
  try {
    categories.value = await getCategories()
    loaded.value = true
  } catch (e) {
    console.error('Failed to fetch categories:', e)
  }
}
```

如排查发现后端返回格式问题，也需修复 `category_service.py` 或 `categories.py`。

**验收标准**：
- 标签删除：点击删除图标 → 弹出确认框 → 确认后才删除 → 取消则不删除
- 预设分类：显示删除按钮，有关联账单时提示数量
- 分类列表：正常显示所有分类（预设 + 自定义）

---

### Agent-5：Frontend — AppLayout + LoginPage（模块 1、7）

**修改文件**：`frontend/src/components/layout/AppLayout.vue`、`frontend/src/pages/LoginPage.vue`

**模块 1：竖屏侧边栏缩窄**

1. 修改 `v-navigation-drawer` 的 `:width`：`72` → `56`
2. 竖屏隐藏文字标题：添加 `:class="{ 'd-none': !display.mdAndUp }"`
3. 侧边栏头部文字竖屏隐藏：`v-show="display.mdAndUp"`

**模块 7：登录后边栏刷新**

AppLayout.vue 新增 `auth:login` 事件监听：
```javascript
function handleAuthLogin() {
  checkLogin()
}

onMounted(() => {
  checkLogin()
  authLogoutHandler = () => handleAuthLogout()
  authLoginHandler = () => handleAuthLogin()
  window.addEventListener('auth:logout', authLogoutHandler)
  window.addEventListener('auth:login', authLoginHandler)
})

onUnmounted(() => {
  window.removeEventListener('auth:logout', authLogoutHandler)
  window.removeEventListener('auth:login', authLoginHandler)
})
```

LoginPage.vue 在 `handleLogin()` 和 `handleRegister()` 成功后，写入 localStorage 之后、路由跳转之前：
```javascript
window.dispatchEvent(new Event('auth:login'))
```

**验收标准**：
- 竖屏侧边栏宽度 56px，仅显示图标
- 宽屏侧边栏 240px，正常显示图标+文字
- 登录/注册后边栏立即显示用户名，无需刷新

---

### Agent-6：Frontend — global.scss（模块 8、9）

**修改文件**：`frontend/src/styles/global.scss`

**模块 8：深色模式滚动条**

```scss
.v-theme--dark ::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
}

.v-theme--dark ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
}
```

**模块 9：深色模式文字颜色**

```scss
.v-theme--dark {
  color: #E0E0E0;
}

.v-theme--dark .text-body-1,
.v-theme--dark .text-body-2,
.v-theme--dark .text-caption {
  color: #E0E0E0 !important;
}

.v-theme--dark .text-grey {
  color: #B0B0B0 !important;
}

.v-theme--dark .text-h5,
.v-theme--dark .text-h6,
.v-theme--dark .text-subtitle-1,
.v-theme--dark .text-subtitle-2,
.v-theme--dark .font-weight-bold {
  color: #FFFFFF !important;
}
```

**验收标准**：
- 深色模式滚动条轨道 `rgba(255,255,255,0.1)`，滑块 `rgba(255,255,255,0.3)`
- 深色模式正文文字 `#E0E0E0`，标题 `#FFFFFF`，辅助文字 `#B0B0B0`
- 浅色模式不受影响

---

### Agent-7：Frontend — RecordListPage（模块 3）

**修改文件**：`frontend/src/pages/RecordListPage.vue`

**模块 3：账单页月份切换横条**

在筛选栏下方添加横向可滑动月份切换条：

脚本新增：
```javascript
import dayjs from 'dayjs'

const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())
const currentYear = new Date().getFullYear()

function selectMonth(month) {
  selectedMonth.value = month
  const start = `${selectedYear.value}-${String(month).padStart(2, '0')}-01`
  const endDate = new Date(selectedYear.value, month, 0)
  const end = `${selectedYear.value}-${String(month).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`
  filters.start_date = start
  filters.end_date = end
  search()
}

function prevYear() { selectedYear.value-- }
function nextYear() { if (selectedYear.value < currentYear) selectedYear.value++ }
```

模板新增（Filter Bar 与 Batch Actions Bar 之间）：
```html
<v-card class="pa-2 mb-3" rounded="xl">
  <div class="d-flex align-center">
    <v-btn v-if="selectedYear !== currentYear - 5" icon variant="text" size="x-small"
      class="d-none d-md-flex" @click="prevYear">
      <v-icon size="small">mdi-chevron-left</v-icon>
    </v-btn>
    <div class="d-flex ga-1 overflow-x-auto flex-grow-1 pb-1" style="scrollbar-width: none;">
      <div v-for="m in 12" :key="m" class="text-center flex-shrink-0" style="min-width: 48px;">
        <v-chip
          :color="selectedMonth === m && selectedYear === currentYear ? 'primary' : ''"
          :variant="selectedMonth === m ? 'flat' : 'text'"
          size="small" rounded="xl" @click="selectMonth(m)">
          {{ m }}月
        </v-chip>
        <div v-if="selectedYear !== currentYear"
          class="text-caption text-grey" style="font-size: 10px; line-height: 1; margin-top: 2px;">
          {{ selectedYear }}
        </div>
      </div>
    </div>
    <v-btn v-if="selectedYear < currentYear" icon variant="text" size="x-small"
      class="d-none d-md-flex" @click="nextYear">
      <v-icon size="small">mdi-chevron-right</v-icon>
    </v-btn>
  </div>
</v-card>
```

`onMounted` 中初始化：`selectMonth(new Date().getMonth() + 1)`

**验收标准**：
- 默认选中当前月份，显示当月账单
- 点击其他月份自动刷新
- 当前年份不显示年份标注，切换到过去年份时显示
- 竖屏可横向滚动，宽屏有年份切换箭头

---

### Agent-8：Frontend — StatisticsPage（模块 11 前端）

**修改文件**：`frontend/src/pages/StatisticsPage.vue`

**模块 11：饼图改柱状图**

1. 导入替换：`Pie` → `Bar`，注册 `BarElement` + `BarController`
2. 模板替换：`<Pie>` → `<Bar>`
3. 移除前端 `type` 过滤（后端已返回 `type` 字段）：`categoryStats.value = c?.items || []`
4. 新增柱状图数据和配置：

```javascript
const categoryBarData = computed(() => ({
  labels: categoryStats.value.map((c) => c.category_name),
  datasets: [{
    label: '金额',
    data: categoryStats.value.map((c) => c.total),
    backgroundColor: chartColors.slice(0, categoryStats.value.length),
    borderRadius: 6,
    borderSkipped: false,
  }],
}))

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: { label: (ctx) => `¥${Number(ctx.raw).toLocaleString()}` },
    },
  },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 10 } } },
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

**验收标准**：
- 统计页显示柱状图，横轴分类名称，纵轴金额
- 不同分类使用不同颜色
- 切换收支类型正确更新
- 无数据时显示"暂无数据"

---

### Agent-9：Frontend — BudgetPage（模块 14）

**修改文件**：`frontend/src/pages/BudgetPage.vue`

**模块 14：预算页支持编辑**

重写数据加载和保存逻辑：

1. 从后端 API 加载预算数据：`getBudgets({ month: currentMonth })`
2. 从后端 API 加载分类列表：`getCategories()`
3. 总预算 = 各分类预算之和（`computed`）
4. 支持编辑：点击编辑图标 → 出现金额输入框 → 回车/确认保存 → Escape/取消放弃
5. 保存调用 `batchSetBudgets()` API
6. 新增预算：点击"设置"按钮 → 选择分类 → 输入金额 → 保存

关键逻辑：
```javascript
const budgets = ref([])
const categories = ref([])
const currentMonth = dayjs().format('YYYY-MM')
const editingBudget = ref(null)
const editAmount = ref(0)

const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))

async function loadBudgets() {
  budgets.value = await getBudgets({ month: currentMonth }) || []
}

function startEdit(item) {
  editingBudget.value = item.category_id
  editAmount.value = item.amount
}

async function saveEdit(item) {
  if (editAmount.value <= 0) return
  await batchSetBudgets({ month: currentMonth, budgets: [{ category_id: item.category_id, amount: editAmount.value }] })
  editingBudget.value = null
  await loadBudgets()
}
```

**验收标准**：
- 预算页从后端加载数据，不再硬编码
- 总预算 = 各分类预算之和
- 点击编辑图标可修改金额，保存后持久化
- 新增分类预算功能正常
- 已消费金额和进度条正确显示

---

## 五、全局验证清单

所有子 Agent 完成后，主 Agent 执行以下验证：

### 后端质量检查

```bash
# 1. 全部测试通过
cd backend && pytest tests/ -v

# 2. 类型检查通过
cd backend && mypy app --strict

# 3. 代码规范检查通过
cd backend && ruff check app

# 4. 格式检查通过
cd backend && ruff format --check app
```

### 前端构建检查

```bash
# 5. 前端构建成功
cd frontend && npm run build
```

### 修复策略

如任何验证失败：
1. 分析失败原因
2. 生成修复子 Agent
3. 修复后重新验证
4. 最多重试 3 轮

---

## 六、注意事项

1. **模块 6 + 10 的交互**：`delete_category` 同时涉及级联删除和所有权校验，确保两个逻辑在同一函数中正确协作
2. **模块 6 + 10 事务完整性**：级联删除时需确保分类、账单、预算在同一事务中删除，避免部分删除
3. **模块 13 排查优先**：此为 P0 Bug，需先用 DevTools/日志排查数据断点，不能盲目改代码
4. **错误码不冲突**：新增 `Code.FORBIDDEN = 40005`，不与现有 `40003`（CONFLICT）冲突
5. **向后兼容**：`statistics_service` 新增 `type` 字段为纯新增，不影响现有前端
6. **级联删除不可逆**：删除分类会同时删除关联账单和预算，确认对话框必须清晰提示
7. **模块 14 预算 API 已就绪**：后端已有完整的预算 CRUD 接口，前端 `budgets.js` 也已封装好，只需重写页面逻辑
8. **模块 1 竖屏宽度**：56px 较窄，需确保图标不被裁切，触摸区域足够
9. **模块 12 按钮布局**：移除 `block` 后需验证在不同屏幕尺寸下按钮仍等宽，Vuetify 的 `flex-grow-1` 类可保证等分
10. **前端无自动化测试**：前端变更通过构建成功 + 验收标准人工验证
11. **ruff format**：后端代码修改后需运行 `ruff format app` 确保格式一致
12. **mypy 类型注解**：所有新增函数参数和返回值必须有类型注解（strict 模式）

---

> 📌 本 Prompt 为 v1.2.1 版本的完整自动化开发指令。主 Agent 按此调度子 Agent，子 Agent 按各自指令完成开发和测试，最终通过全局验证确保质量。
