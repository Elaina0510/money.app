# Money App v1.2.3 详细设计文档

> 版本：v1.0
> 日期：2026-06-04
> 状态：待评审
> 对应需求：`doc/proposalv1.2.3.md`

---

## 架构概览

本版本涉及前端 5 个模块的改动，后端 2 个模块的改动。模块之间相互独立，可按任意顺序开发和测试。

### 模块依赖关系

```
模块 1（标签保存时机优化）  ── 独立
模块 2（标签显示异常修复）  ── 独立
模块 3（账单筛选功能修复）  ── 独立
模块 4（登录错误提示优化）  ── 独立
模块 5（恢复默认分类功能）  ── 独立
```

### 技术约束

- 前端：Vue 3 + Vuetify 3 + Pinia，不引入新依赖
- 后端：FastAPI + SQLModel + SQLite，不引入新依赖
- 保持现有代码风格（Composition API `<script setup>`，async service 层）

---

## 模块 1：快速记账页 - 标签保存时机优化

**需求编号：** #1
**优先级：** 高
**影响范围：** 前端 RecordFormPage.vue

### 1.1 现状分析

当前 [RecordFormPage.vue](frontend/src/pages/RecordFormPage.vue) 中，标签在**两个时机**被保存到数据库：

1. **按回车时**（[onCreateTagFromSearch 第 312-313 行](frontend/src/pages/RecordFormPage.vue#L312-L313)）：调用 `createTagData({ name, category_id })` 立即写入数据库
2. **点击保存按钮时**（[submit 第 340-342 行](frontend/src/pages/RecordFormPage.vue#L340-L342)）：如果 `selectedTagName` 有值但 `selectedTagId` 为空，再次调用 `createTagData`

这导致标签和账单的保存时机不一致——标签可能在用户未最终确认时就已入库。

### 1.2 设计方案

**核心思路：** 按回车仅在界面上确认标签（设置本地状态），不调用 API。标签的实际创建推迟到 `submit()` 中与账单一起保存。

**文件：** `frontend/src/pages/RecordFormPage.vue`

#### 1.2.1 修改 `onCreateTagFromSearch` 函数

将按回车时的行为从"创建标签并保存到数据库"改为"仅在界面上确认标签"：

```javascript
async function onCreateTagFromSearch() {
  if (!tagSearchQuery.value || tagSearchQuery.value.length < 1) return

  // 如果搜索结果中有精确匹配，直接选中（与现有逻辑一致）
  const exactMatch = tagSearchResults.value.find(t => t.name === tagSearchQuery.value)
  if (exactMatch) {
    selectedTagId.value = exactMatch.id
    selectedTagName.value = exactMatch.name
    if (exactMatch.category_id) {
      categoryId.value = exactMatch.category_id
    }
    return
  }

  // 新标签：仅在界面上确认，不保存到数据库
  selectedTagId.value = null  // 标记为新标签（无 ID）
  selectedTagName.value = tagSearchQuery.value.trim()
  // 注意：不调用 createTagData，不写入数据库
}
```

#### 1.2.2 确认 `submit()` 函数逻辑正确

现有 `submit()` 函数（第 334-366 行）已有处理新标签的逻辑：

```javascript
async function submit() {
  // ...
  let tagId = selectedTagId.value
  if (selectedTagName.value && !tagId) {
    // selectedTagName 有值但无 ID → 是新标签，在此处创建
    const newTag = await createTagData({
      name: selectedTagName.value.trim(),
      category_id: categoryId.value
    })
    tagId = newTag.id
  }
  // ... 使用 tagId 创建账单
}
```

这段逻辑无需修改，它会在保存账单时统一创建标签。

#### 1.2.3 离开页面时的行为

用户未点击保存就离开页面时，由于标签从未调用 API 创建，不会残留无主标签。无需额外处理。

### 1.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 输入新标签名，按回车 | 标签名在输入框中正确显示 |
| 按回车后检查数据库 | tags 表中无新增记录 |
| 按回车后填写其他信息，点击保存 | 账单和标签一起保存到数据库 |
| 输入新标签名，按回车，不保存直接离开 | 数据库中无新增标签 |
| 选择已有标签，按回车 | 正常选中（selectedTagId 赋值为已有 ID） |
| 保存后查看账单详情 | 标签显示正确 |

---

## 模块 2：快速记账页 - 标签显示异常修复

**需求编号：** #2
**优先级：** 高
**影响范围：** 前端 RecordFormPage.vue

### 2.1 现状分析

当前 `v-autocomplete` 组件的 `v-model` 绑定的是 `selectedTagId`（标签 ID），`item-title` 为 `name`。当用户输入标签名后点击空白处，组件的 `v-model:search`（`tagSearchQuery`）会被清空，导致 `tagSearchResults` 清空。此时 `v-autocomplete` 无法从空的 items 列表中找到匹配项来显示名称，回退显示原始的 `v-model` 值——即数字 ID。

同时，`selectedTagName` ref 已经存储了正确的标签名，但 `v-autocomplete` 不使用它来显示。

### 2.2 设计方案

**核心思路：** 确保 `tagSearchResults` 始终包含当前已选中的标签项，使 `v-autocomplete` 能正确显示名称。

**文件：** `frontend/src/pages/RecordFormPage.vue`

#### 2.2.1 修改 `onTagSearch` 函数

在搜索结果清空时（如点击空白处触发 `search=""`），保留当前已选中的标签：

```javascript
async function onTagSearch(query) {
  if (!query || query.length < 1) {
    // 清空搜索结果时，保留当前已选中的标签
    if (selectedTagId.value) {
      // 从现有结果中找到当前选中项，保留它
      const currentItem = tagSearchResults.value.find(t => t.id === selectedTagId.value)
      tagSearchResults.value = currentItem ? [currentItem] : []
    } else {
      tagSearchResults.value = []
    }
    return
  }
  // ... 防抖搜索逻辑不变
}
```

#### 2.2.2 修改 `onCreateTagFromSearch` 函数

用户输入新标签名按回车后（结合模块 1 的改动，此时不保存到数据库），将新标签信息加入搜索结果列表，使 `v-autocomplete` 能正确显示：

```javascript
async function onCreateTagFromSearch() {
  // ... 精确匹配逻辑不变

  // 新标签：仅在界面上确认
  selectedTagId.value = null
  selectedTagName.value = tagSearchQuery.value.trim()

  // 将新标签作为临时项加入搜索结果，使 v-autocomplete 能显示
  // 注意：这是一个假 ID（-1），仅用于前端显示
  const tempTag = {
    id: -1,  // 临时 ID，表示尚未保存
    name: selectedTagName.value,
    category_id: categoryId.value,
  }
  tagSearchResults.value = [tempTag]
  selectedTagId.value = -1  // 临时选中
}
```

#### 2.2.3 修改 `submit()` 函数中的标签 ID 判断

需要处理临时 ID（-1）的情况：

```javascript
async function submit() {
  // ...
  let tagId = selectedTagId.value
  // -1 表示新标签（未保存），需要创建
  if (selectedTagName.value && (!tagId || tagId === -1)) {
    const newTag = await createTagData({
      name: selectedTagName.value.trim(),
      category_id: categoryId.value
    })
    tagId = newTag.id
  }
  // ...
}
```

### 2.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 输入新标签名，按回车，点击空白处 | 输入框显示标签名称（非数字） |
| 选择已有标签，点击空白处 | 输入框显示标签名称 |
| 输入新标签名，按回车，保存账单 | 账单正确关联新创建的标签 |
| 输入新标签名，不按回车，直接保存 | 账单正确关联新创建的标签 |
| 账单页回看标签 | 显示标签名称，与记账页一致 |

---

## 模块 3：账单页 - 筛选功能修复与优化

**需求编号：** #3, #4, #6
**优先级：** 高
**影响范围：** 前端 RecordListPage.vue

本模块合并处理三个相关需求：
- **#3**：类型筛选不生效
- **#4**：切换页面后筛选状态丢失
- **#6**：分类标签未按类型联动

### 3.1 现状分析

**#3 类型筛选不生效：**

当前 [RecordListPage.vue](frontend/src/pages/RecordListPage.vue) 的 `search()` 函数（第 241-258 行）使用 `filters.type` 映射到 `type_filter` 参数。已有 `watch` 监听 `filters.type` 变化并触发搜索（第 264-272 行）。但需确认 `v-select` 的 `v-model` 绑定是否正确。

查看模板代码：`v-select` 的 `v-model` 绑定 `filters.type`，`item-value="value"`，选项值为 `''`/`'expense'`/`'income'`。`search()` 中 `if (filters.type) params.type_filter = filters.type`——当值为 `''` 时不传 `type_filter`（显示全部），值为 `'expense'`/`'income'` 时传对应值。逻辑上应能正常工作。

**可能的问题：** `watch` 监听的 `filters.type` 变化可能未正确触发，或者后端参数名不匹配。需要实际调试确认。

**#4 筛选状态丢失：**

`filters` 是页面级 `reactive` 对象（第 202-207 行），不存储在 Pinia store 中。用户导航到其他页面再返回时，组件重新创建，`filters` 被重置为初始值。

Pinia store `useRecordsStore` 已有 `filters` ref 和 `setFilters`/`resetFilters` 方法，但 `RecordListPage` 未使用它们。

**#6 分类未按类型联动：**

`categoryOptions` computed（第 215-218 行）直接拼接全量 `categories`，未根据 `filters.type` 过滤：

```javascript
const categoryOptions = computed(() => {
  const list = [{ name: '全部分类', id: null }]
  return list.concat(categories.value)  // 未按 type 过滤
})
```

### 3.2 设计方案

**文件：** `frontend/src/pages/RecordListPage.vue`

#### 3.2.1 使用 Pinia store 持久化筛选状态（#4）

将筛选状态从页面级 `reactive` 迁移到 `useRecordsStore`：

```javascript
import { useRecordsStore } from '@/stores/useRecordsStore'

const recordsStore = useRecordsStore()

// 使用 store 的 filters 替代本地 reactive
// store.filters 的结构与现有 filters 一致：{ start_date, end_date, type, category_id }
const filters = recordsStore.filters
```

**页面进入时：** store 中的 filters 保留上次的值，无需重新初始化。

**页面离开时：** filters 保留在 store 中，切换回来时自动恢复。

**注意：** 需要检查 `useRecordsStore.filters` 的结构是否与页面使用的字段一致。store 中的 filters 有 `start_date`、`end_date`、`category_id`、`type`、`tag_id`、`keyword`，页面使用 `start_date`、`end_date`、`type`、`category_id`，完全兼容。

#### 3.2.2 分类按类型联动（#6）

修改 `categoryOptions` computed，根据当前选中的类型过滤分类：

```javascript
const categoryOptions = computed(() => {
  const list = [{ name: '全部分类', id: null }]
  if (filters.type) {
    // 按选中类型过滤分类
    const filtered = categories.value.filter(c => c.type === filters.type)
    return list.concat(filtered)
  }
  // 未选类型时显示全部分类
  return list.concat(categories.value)
})
```

**切换类型时清空已选分类：**

在现有的 `watch` 中增加清空分类的逻辑：

```javascript
watch(
  () => [filters.type, filters.category_id],
  () => {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = setTimeout(() => { search() }, 300)
  }
)

// 新增：监听类型变化，清空已选分类
watch(
  () => filters.type,
  () => {
    filters.category_id = null
  }
)
```

#### 3.2.3 确认类型筛选生效（#3）

现有 `search()` 函数的映射逻辑：

```javascript
if (filters.type) params.type_filter = filters.type
```

当 `filters.type` 为 `'expense'` 时，`params.type_filter = 'expense'`。后端 `get_records` 使用 `type_filter` 参数过滤。

**需确认：** `v-select` 的 `v-model` 绑定是否正确。检查模板中是否有 `v-model="filters.type"` 绑定。如果绑定正确，筛选应能生效。

如果经过调试确认前端逻辑无误但筛选仍不生效，需检查后端 `record_service.get_records()` 的 `type_filter` 处理逻辑。

### 3.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 选择"收入" | 列表只显示收入类型账单 |
| 选择"支出" | 列表只显示支出类型账单 |
| 选择"全部" | 列表显示所有账单 |
| 选择"支出"后，分类下拉只显示支出分类 | 餐饮、交通等支出分类可见，工资等收入分类不可见 |
| 切换类型 | 已选分类自动清空 |
| 筛选后切换到统计页，再切回账单页 | 筛选条件保持，筛选框正确显示 |
| 筛选后切换页面再切回 | 筛选结果与筛选框显示一致 |
| 筛选结果实时更新 | 无需手动刷新 |

---

## 模块 4：登录页 - 错误提示优化

**需求编号：** #5
**优先级：** 高
**影响范围：** 前端 api/request.js

### 4.1 现状分析

**后端行为：**

[auth.py 第 100-101 行](backend/app/routers/auth.py#L100-L101)：登录失败时返回 HTTP 401 状态码 + 统一格式 JSON：

```python
return error_response(Code.PARAM_ERROR, "用户名或密码错误", status_code=401)
```

响应体：`{"code": 40001, "message": "用户名或密码错误", "data": null}`，HTTP 状态码：401

**前端拦截器行为：**

[request.js](frontend/src/api/request.js) 的响应拦截器有两个处理器：

1. **成功处理器**（第 24-34 行）：处理 HTTP 2xx 响应，检查 `res.code`，非 0 时 reject
2. **错误处理器**（第 36-59 行）：处理 HTTP 4xx/5xx 响应，对 401 返回"登录已过期，请重新登录"

**问题所在：**

当后端返回 HTTP 401 时，Axios **不走成功处理器**，直接进入错误处理器。错误处理器检查 `error.response.status === 401`，返回 `Promise.reject(new Error('登录已过期，请重新登录'))`。

这意味着登录失败时，用户看到的是"登录已过期，请重新登录"而非"用户名或密码错误"。

### 4.2 设计方案

**文件：** `frontend/src/api/request.js`

#### 4.2.1 修改错误处理器

在错误处理器中，优先从响应体中读取后端返回的错误信息：

```javascript
(error) => {
  if (error.response) {
    const { status, data } = error.response
    let msg = '请求失败'

    if (status === 401) {
      // 优先使用后端返回的错误信息（如"用户名或密码错误"）
      if (data && data.message) {
        msg = data.message
      } else {
        msg = '登录已过期，请重新登录'
        // 清除过期的 token
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.removeItem('userId')
        window.dispatchEvent(new CustomEvent('auth:logout'))
      }
    } else if (status === 422) {
      msg = (data && data.message) || '参数错误'
    } else if (status === 500) {
      msg = (data && data.message) || '服务器错误'
    }

    return Promise.reject(new Error(msg))
  }
  if (error.code === 'ECONNABORTED') {
    return Promise.reject(new Error('请求超时'))
  }
  return Promise.reject(new Error('网络异常'))
}
```

**关键改动：**

- 401 状态码时，先检查 `data.message` 是否存在
- 如果后端返回了具体错误信息（如"用户名或密码错误"），直接使用
- 如果没有后端信息（如 token 过期的真实 401），才显示"登录已过期"并清除 token
- 同样优化 422 和 500 的错误信息读取

#### 4.2.2 区分登录 401 和 token 过期 401

**问题：** 登录接口的 401（密码错误）和业务接口的 401（token 过期）使用相同的 HTTP 状态码。

**区分方式：** 检查请求 URL 是否为登录接口 `/api/auth/login`：

```javascript
if (status === 401) {
  const isLoginRequest = error.config?.url?.includes('/auth/login')
  if (isLoginRequest && data && data.message) {
    // 登录接口的 401：使用后端消息
    msg = data.message
  } else {
    // 其他接口的 401：token 过期
    msg = '登录已过期，请重新登录'
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('userId')
    window.dispatchEvent(new CustomEvent('auth:logout'))
  }
}
```

**推荐方案：** 采用 4.2.1 的方案（优先读取 `data.message`），因为后端登录接口返回的 401 一定有 `data.message`，而 token 过期的真实 401 通常由 Nginx/网关返回，`data` 为空或无 `message` 字段。这样不需要硬编码接口路径。

### 4.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 输入错误密码 | 显示"用户名或密码错误" |
| 输入不存在的用户名 | 显示"用户名或密码错误" |
| 不泄露具体错误类型 | 不会提示"用户不存在"或"密码错误" |
| Token 过期访问业务接口 | 显示"登录已过期，请重新登录"并跳转登录页 |
| 网络异常 | 显示"网络异常" |
| 请求超时 | 显示"请求超时" |

---

## 模块 5：设置页 - 恢复默认分类功能

**需求编号：** #7
**优先级：** 高
**影响范围：** 前端 SettingsPage.vue、useCategoriesStore.js，后端 category_service.py、categories.py

### 5.1 现状分析

- 默认分类定义在后端 [main.py 第 23-57 行](backend/app/main.py#L23-L57) 的 `PRESET_CATEGORIES` 常量中
- 分类管理已有增删改查功能，删除分类时级联删除关联的记录和预算（[category_service.py 第 86-125 行](backend/app/services/category_service.py#L86-L125)）
- 用户自定义分类的 `is_preset=0`，预设分类的 `is_preset=1`

**需求要求：**
- 恢复默认时删除所有用户自定义分类
- 自定义分类下的账单记录**保留**，但清除其 `category_id` 关联（设为 NULL）
- 恢复预设分类的原始排序和属性
- 操作不可撤销，需二次确认

### 5.2 设计方案

#### 5.2.1 后端：新增恢复默认分类 API

**文件：** `backend/app/services/category_service.py`

新增 `restore_default_categories` 函数：

```python
async def restore_default_categories(
    db: AsyncSession, current_user: User | None = None
) -> dict[str, int]:
    """恢复默认分类：删除用户自定义分类，重置预设分类属性。

    - 删除所有 is_preset=0 的用户自定义分类
    - 关联的账单记录保留，category_id 设为 NULL
    - 关联的预算删除
    - 重置预设分类的 sort_order 为默认值

    返回：{"deleted_categories": N, "affected_records": M}
    """
    from app.main import PRESET_CATEGORIES

    user_id = current_user.id if current_user else None

    # Step 1: 删除用户自定义分类（is_preset=0）
    custom_query = select(Category).where(
        Category.is_preset == 0,
        Category.user_id == user_id,
    )
    custom_result = await db.exec(custom_query)
    custom_categories = list(custom_result.all())

    deleted_count = 0
    affected_records = 0

    for cat in custom_categories:
        # 统计关联记录数
        count_stmt = select(func.count(Record.id)).where(Record.category_id == cat.id)
        count_result = await db.exec(count_stmt)
        record_count = count_result.one() or 0
        affected_records += record_count

        # 将关联记录的 category_id 设为 NULL（保留记录）
        record_stmt = select(Record).where(Record.category_id == cat.id)
        record_result = await db.exec(record_stmt)
        for record in record_result.all():
            record.category_id = None

        # 删除关联预算
        budget_stmt = select(Budget).where(Budget.category_id == cat.id)
        budget_result = await db.exec(budget_stmt)
        for budget in budget_result.all():
            await db.delete(budget)

        # 删除分类
        await db.delete(cat)
        deleted_count += 1

    # Step 2: 重置预设分类的 sort_order
    for preset in PRESET_CATEGORIES:
        stmt = select(Category).where(
            Category.name == preset["name"],
            Category.type == preset["type"],
            Category.is_preset == 1,
        )
        result = await db.exec(stmt)
        category = result.first()
        if category:
            category.sort_order = preset["sort_order"]
            category.icon = preset["icon"]

    await db.commit()
    return {"deleted_categories": deleted_count, "affected_records": affected_records}
```

**文件：** `backend/app/routers/categories.py`

新增 API 端点：

```python
@router.post("/restore-defaults")
async def restore_defaults(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """恢复默认分类设置。"""
    result = await category_service.restore_default_categories(db, current_user)
    return success_response(
        data=result,
        message=f"已恢复默认分类，删除 {result['deleted_categories']} 个自定义分类，"
                f"{result['affected_records']} 条记录已解除分类关联",
    )
```

#### 5.2.2 前端：API 调用

**文件：** `frontend/src/api/categories.js`

新增 API 函数：

```javascript
export function restoreDefaultCategories() {
  return request.post('/categories/restore-defaults')
}
```

#### 5.2.3 前端：设置页 UI

**文件：** `frontend/src/pages/SettingsPage.vue`

在分类管理卡片的标题栏右侧添加"恢复默认"按钮：

```html
<v-card class="pa-4 mb-3 settings-card" rounded="xl">
  <div class="d-flex justify-space-between align-center mb-3">
    <div class="d-flex align-center">
      <v-avatar size="36" color="rgba(33, 150, 243, 0.1)" class="mr-2">
        <v-icon color="blue" size="20">mdi-shape-outline</v-icon>
      </v-avatar>
      <span class="text-subtitle-2 font-weight-bold">分类管理</span>
    </div>
    <v-btn
      size="small"
      color="warning"
      variant="tonal"
      @click="showRestoreConfirm = true"
    >
      <v-icon start size="small">mdi-restore</v-icon>
      恢复默认
    </v-btn>
  </div>
  <!-- ... 现有分类列表 ... -->
</v-card>
```

**二次确认对话框：**

```html
<v-dialog v-model="showRestoreConfirm" max-width="400">
  <v-card class="pa-4" rounded="xl">
    <v-card-title class="text-h6 pa-0 mb-2">恢复默认分类</v-card-title>
    <v-card-text class="pa-0 mb-4">
      <v-alert type="warning" variant="tonal" class="mb-3">
        此操作不可撤销！
      </v-alert>
      <p class="text-body-2">
        恢复默认分类将：
      </p>
      <ul class="text-body-2 text-medium-emphasis">
        <li>删除所有自定义分类</li>
        <li>自定义分类下的账单记录将被保留，但失去分类关联</li>
        <li>重置预设分类为默认排序</li>
      </ul>
    </v-card-text>
    <div class="d-flex justify-end ga-2">
      <v-btn variant="text" @click="showRestoreConfirm = false">取消</v-btn>
      <v-btn color="warning" @click="handleRestoreDefaults" :loading="restoring">
        确认恢复
      </v-btn>
    </div>
  </v-card>
</v-dialog>
```

**处理函数：**

```javascript
const showRestoreConfirm = ref(false)
const restoring = ref(false)

async function handleRestoreDefaults() {
  restoring.value = true
  try {
    const result = await restoreDefaultCategories()
    appStore.showToast(result.message || '已恢复默认分类')
    showRestoreConfirm.value = false
    // 重新加载分类列表
    await loadCategories()
  } catch (e) {
    appStore.showToast(e.message || '恢复失败', 'error')
  } finally {
    restoring.value = false
  }
}
```

#### 5.2.4 Store 更新

**文件：** `frontend/src/stores/useCategoriesStore.js`

新增 `restoreDefaults` action：

```javascript
async function restoreDefaults() {
  const result = await restoreDefaultCategoriesAPI()
  await fetchCategories()  // 重新获取分类列表
  return result
}
```

### 5.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 分类管理栏显示"恢复默认"按钮 | 按钮可见，样式为警告色 |
| 点击按钮弹出确认对话框 | 对话框显示操作说明和警告 |
| 点击"取消" | 对话框关闭，无任何变化 |
| 点击"确认恢复" | 自定义分类被删除，预设分类重置 |
| 恢复后查看账单记录 | 自定义分类下的记录仍在，但无分类关联 |
| 恢复后查看预算 | 自定义分类下的预算被删除 |
| 恢复后预设分类排序 | 重置为默认排序（餐饮 1、交通 2 ...） |
| 恢复后自定义分类 | 全部消失 |
| 无自定义分类时恢复 | 预设分类排序重置，无报错 |
| 恢复操作不可撤销 | 对话框明确提示"此操作不可撤销" |

---

## 数据库变更汇总

| 变更 | SQL | 影响模块 |
|------|-----|----------|
| 无新增表或列 | — | — |

**注意：** 模块 5 的恢复默认功能通过后端逻辑实现，不涉及数据库结构变更。`Record.category_id` 字段已允许 NULL（`ondelete="SET NULL"`），可直接将记录的 `category_id` 设为 NULL。

---

## API 变更汇总

| 方法 | 路径 | 变更类型 | 说明 | 影响模块 |
|------|------|----------|------|----------|
| POST | `/api/categories/restore-defaults` | 新增 | 恢复默认分类设置 | 模块 5 |

---

## 修改文件汇总

| 文件 | 变更类型 | 涉及模块 |
|------|----------|----------|
| `frontend/src/pages/RecordFormPage.vue` | 修改 | 模块 1, 2 |
| `frontend/src/pages/RecordListPage.vue` | 修改 | 模块 3 |
| `frontend/src/api/request.js` | 修改 | 模块 4 |
| `frontend/src/pages/SettingsPage.vue` | 修改 | 模块 5 |
| `frontend/src/api/categories.js` | 修改 | 模块 5 |
| `frontend/src/stores/useCategoriesStore.js` | 修改 | 模块 5 |
| `backend/app/services/category_service.py` | 修改 | 模块 5 |
| `backend/app/routers/categories.py` | 修改 | 模块 5 |
