# Money App v1.2.2 详细设计文档

> 版本：v1.0
> 日期：2026-06-04
> 状态：待评审
> 对应需求：`doc/proposalv1.2.2.md`

---

## 架构概览

本版本涉及前端 9 个模块的改动，后端 3 个模块的改动。模块之间相互独立，可按任意顺序开发和测试。

### 模块依赖关系

```
模块 1（分类管理增强）  ── 独立
模块 2（标签管理增强）  ── 独立
模块 3（预算管理整合）  ── 独立
模块 4（快速记账优化）  ── 独立
模块 5（标签搜索联想）  ── 依赖模块 2（需要标签带分类信息的 API）
模块 6（账单按钮修正）  ── 独立
模块 7（账单筛选优化）  ── 独立
模块 8（深色模式优化）  ── 独立
模块 9（移动端底部导航）── 独立
```

### 技术约束

- 前端：Vue 3 + Vuetify 3 + Pinia，不引入新依赖
- 后端：FastAPI + SQLModel + SQLite，不引入新依赖
- 保持现有代码风格（Composition API `<script setup>`，async service 层）

---

## 模块 1：设置页 - 分类管理增强

**需求编号：** #1
**优先级：** 高
**影响范围：** 前端 SettingsPage.vue，后端 categories API（排序）

### 1.1 现状分析

当前 [SettingsPage.vue](frontend/src/pages/SettingsPage.vue) 已实现分类的增删改查，但缺少**排序调整**功能。分类列表按 `sort_order` 排序显示，但用户无法在 UI 上调整顺序。

后端 [category_service.py](backend/app/services/category_service.py) 已有 `sort_order` 字段支持，前端 store 已有 `editCategory` 方法可更新 `sort_order`。

### 1.2 设计方案

#### 前端改动

**文件：** `frontend/src/pages/SettingsPage.vue`

在每个分类列表项的 append 区域增加**上移/下移**按钮（而非拖拽，避免引入新依赖）：

```
分类列表项结构：
[图标] [名称] [预设标签] ... [上移] [下移] [编辑] [删除]
```

**交互逻辑：**

1. 每个分类项右侧增加上移（`mdi-chevron-up`）和下移（`mdi-chevron-down`）按钮
2. 列表中第一个分类不显示上移按钮，最后一个不显示下移按钮
3. 点击上移/下移时：
   - 与相邻分类交换 `sort_order` 值
   - 调用 `categoriesStore.editCategory(id, { sort_order: newOrder })` 保存
   - 刷新分类列表

**数据流：**

```
点击上移/下移
  → 计算当前项与目标项的 sort_order 互换值
  → 调用 editCategory(currentId, { sort_order: targetOrder })
  → 调用 editCategory(targetId, { sort_order: currentOrder })
  → 重新 fetchCategories()
```

**边界处理：**

- 首项不显示上移按钮，末项不显示下移按钮
- 预设分类也可以调整排序（`is_preset` 仅限制删除，不限制排序）
- 排序变更后立即生效（分类列表重新渲染）

#### 后端改动

无额外改动。现有 `PUT /api/categories/{id}` 已支持更新 `sort_order`。需确认 `sort_order` 更新时不影响其他字段。

### 1.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 新增分类后出现在列表末尾 | `sort_order` 为当前最大值 +1 |
| 点击上移，分类上移一位 | `sort_order` 与上一项互换 |
| 点击下移，分类下移一位 | `sort_order` 与下一项互换 |
| 首项无上移按钮，末项无下移按钮 | 按钮正确隐藏 |
| 排序后刷新页面 | 排序保持 |
| 支出/收入分类各自独立排序 | 互不影响 |

---

## 模块 2：设置页 - 标签管理增强

**需求编号：** #7, #8
**优先级：** 中
**影响范围：** 前端 SettingsPage.vue、useCategoriesStore.js，后端 Tag model、tag_service、record_service

### 2.1 现状分析

- 当前标签新增对话框只有名称输入，`category_id` 为可选
- 标签删除为硬删除（`DELETE /api/tags/{id}`），删除后关联的账单记录丢失标签信息
- Tag model 已有 `category_id` 字段（nullable FK）

### 2.2 设计方案

#### 2.2.1 标签新增时分类必填（需求 #7）

**前端改动：**

**文件：** `frontend/src/pages/SettingsPage.vue`

修改标签新增对话框，增加分类选择器：

```html
<!-- 标签对话框新增字段 -->
<v-select
  v-model="tagForm.category_id"
  :items="allCategories"
  item-title="name"
  item-value="id"
  label="所属分类 *"
  :rules="[v => !!v || '请选择分类']"
  hide-details="auto"
  class="mb-3"
  variant="outlined"
/>
```

**验证逻辑：**
- 分类为必填，`saveTag()` 中增加前置检查：`if (!tagForm.category_id) return`
- 未选择分类时，保存按钮 disabled 或点击后显示提示
- 提交数据改为 `{ name, category_id }`

**文件：** `frontend/src/stores/useCategoriesStore.js`

`addTag` 方法需传递 `category_id` 参数。

#### 2.2.2 标签软删除（需求 #8）

**后端改动：**

**文件：** `backend/app/models/tag.py`

给 Tag model 增加 `deleted_at` 字段：

```python
deleted_at: str | None = Field(default=None, nullable=True)
```

**数据库迁移：**

需要执行 ALTER TABLE 语句：
```sql
ALTER TABLE tags ADD COLUMN deleted_at TEXT DEFAULT NULL;
```

**文件：** `backend/app/services/tag_service.py`（新建或修改现有 tag 逻辑）

修改删除逻辑为软删除：
```python
async def delete_tag(db, tag_id, current_user):
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None
    # 权限检查
    tag.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.commit()
    return True
```

修改查询逻辑，过滤已删除标签：
```python
async def get_tags(db, current_user):
    query = select(Tag).where(Tag.deleted_at.is_(None))
    # ... 现有用户过滤逻辑
```

**文件：** `backend/app/routers/tags.py`

- `DELETE /api/tags/{id}` 改为软删除（设置 `deleted_at`）
- `GET /api/tags` 过滤 `deleted_at IS NOT NULL` 的记录

**文件：** `backend/app/services/record_service.py`

`_enrich_record` 函数中，获取标签时不检查 `deleted_at`，确保已删除标签的账单仍能显示标签名称：
```python
# 不加 deleted_at 过滤，直接通过 ID 获取
tag = await db.get(Tag, record.tag_id)
```

**前端改动：**

**文件：** `frontend/src/stores/useCategoriesStore.js`

- `fetchTags` 获取的是未删除标签（API 已过滤）
- `removeTag` 调用 DELETE API（后端软删除）
- 无需前端额外处理，删除后重新 fetch 即可

### 2.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 新增标签不选分类 | 提示"请选择分类"，无法保存 |
| 新增标签选择分类 | 标签创建成功，关联正确分类 |
| 删除标签 | 标签从列表消失 |
| 删除标签后查看关联账单 | 账单详情仍显示标签名称 |
| 新建账单时标签选择列表 | 不包含已删除标签 |
| API GET /api/tags | 不返回已删除标签 |

---

## 模块 3：预算管理整合

**需求编号：** #5
**优先级：** 高
**影响范围：** 前端 AppLayout.vue、SettingsPage.vue、router/index.js；BudgetPage.vue 保留但不再直接导航

### 3.1 现状分析

- BudgetPage.vue 是独立页面，路由 `/budget`，在侧边栏有导航入口
- 预算功能本身（API、数据、UI）正常工作
- 需求要求：移除独立导航入口，预算管理嵌入设置页

### 3.2 设计方案

#### 3.2.1 移除预算导航入口

**文件：** `frontend/src/components/layout/AppLayout.vue`

从 `navItems` 数组中移除预算项：
```javascript
const navItems = [
  { to: '/', title: '主页', icon: 'mdi-view-dashboard-outline' },
  { to: '/records', title: '账单', icon: 'mdi-format-list-bulleted' },
  { to: '/statistics', title: '统计', icon: 'mdi-chart-box-outline' },
  // 移除 { to: '/budget', ... }
]
```

#### 3.2.2 设置页嵌入预算管理

**文件：** `frontend/src/pages/SettingsPage.vue`

在设置页中增加**预算管理**卡片 section，将 BudgetPage.vue 的核心 UI 嵌入：

```html
<!-- 预算管理 Section（新增） -->
<v-card class="pa-4 mb-3 settings-card" rounded="xl">
  <div class="d-flex align-center mb-3">
    <v-avatar size="36" color="rgba(156, 39, 176, 0.1)" class="mr-2">
      <v-icon color="purple" size="20">mdi-piggy-bank-outline</v-icon>
    </v-avatar>
    <span class="text-subtitle-2 font-weight-bold">预算管理</span>
  </div>

  <!-- 月度预算概览 -->
  <v-card variant="tonal" class="pa-4 mb-3" rounded="lg">
    <div class="text-caption text-grey mb-1">本月预算</div>
    <div class="text-h5 font-weight-bold mb-2">¥{{ formatAmount(totalBudget) }}</div>
    <v-progress-linear ... />
    <div class="d-flex justify-space-between text-caption mt-1">
      <span>已用 ¥{{ formatAmount(totalSpent) }}</span>
      <span>{{ budgetUsagePercent.toFixed(0) }}%</span>
    </div>
  </v-card>

  <!-- 分类预算列表（复用 BudgetPage 逻辑） -->
  <div v-for="item in enrichedBudgets" ...>
    <!-- 与 BudgetPage.vue 相同的预算项 UI -->
  </div>

  <!-- 添加预算按钮 -->
  <v-btn ... @click="openBudgetAddDialog">设置分类预算</v-btn>
</v-card>
```

**数据加载：**

在 SettingsPage 的 `onMounted` 中增加预算数据加载：
```javascript
onMounted(async () => {
  await Promise.all([loadCategories(), loadTags(), loadBudgets()])
})
```

需要导入 `getBudgets`、`batchSetBudgets` API。

#### 3.2.3 路由保留

**文件：** `frontend/src/router/index.js`

`/budget` 路由**保留**不删除，确保旧链接/书签仍可访问。但可考虑将其重定向到 `/settings`：

```javascript
{
  path: '/budget',
  redirect: '/settings',
}
```

### 3.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 侧边栏无"预算"入口 | 导航项不显示 |
| 底部导航栏无"预算"入口 | 导航项不显示 |
| 设置页显示预算管理 section | 可看到预算概览和分类预算列表 |
| 设置页中可添加/编辑预算 | 功能正常 |
| 直接访问 /budget 路由 | 重定向到 /settings |
| 预算数据不受影响 | 原有数据完整 |

---

## 模块 4：快速记账优化

**需求编号：** #9, #10
**优先级：** 中
**影响范围：** 后端 record_service.py，前端 RecordFormPage.vue、SettingsPage.vue

### 4.1 现状分析

**需求 #9：** 当前快速记账模板取最近 10 条记录，需求要求改为"记录 2 次相同账单（标签 + 类型 + 金额均相同）后才纳入"。

**需求 #10：** 当前无快速记账管理功能，需求要求在设置页中增加查看、删除、手动添加。

### 4.2 设计方案

#### 4.2.1 快速记账模板逻辑优化（需求 #9）

**后端改动：**

**文件：** `backend/app/services/record_service.py`

重写 `get_quick_templates` 函数：

```python
async def get_quick_templates(
    db: AsyncSession, limit: int = 10, current_user: User | None = None
) -> list[dict[str, Any]]:
    """获取快速记账模板：标签+类型+金额相同且出现 >= 2 次的组合。"""
    user_filter = Record.user_id == current_user.id if current_user else Record.user_id.is_(None)

    # 按 tag_id + type + amount 分组，筛选出现次数 >= 2 的组合
    query = (
        select(
            Record.tag_id,
            Record.type,
            Record.amount,
            func.count(Record.id).label("count"),
            func.max(Record.updated_at).label("last_used"),
        )
        .where(user_filter)
        .where(Record.tag_id.isnot(None))  # 必须有标签
        .group_by(Record.tag_id, Record.type, Record.amount)
        .having(func.count(Record.id) >= 2)
        .order_by(func.max(Record.updated_at).desc())
        .limit(limit)
    )

    result = await db.exec(query)
    rows = result.all()

    # 构造模板列表
    templates = []
    for row in rows:
        tag = await db.get(Tag, row.tag_id)
        if not tag or tag.deleted_at:
            continue
        category = await db.get(Category, tag.category_id) if tag.category_id else None
        templates.append({
            "tag_id": row.tag_id,
            "tag_name": tag.name,
            "type": row.type,
            "amount": row.amount,
            "category_id": tag.category_id,
            "category_name": category.name if category else "",
            "category_icon": category.icon if category else "mdi-circle",
            "count": row.count,
        })

    return templates
```

**关键逻辑：**
- 按 `(tag_id, type, amount)` 分组
- `HAVING count >= 2`：至少出现 2 次
- 排除已删除标签（`tag.deleted_at IS NULL`）
- 按最近使用时间降序排列

**前端改动：**

**文件：** `frontend/src/pages/RecordFormPage.vue`

修改快速模板展示，适配新的数据结构：

```javascript
// 模板数据结构变化
// 旧: { id, type, amount, category_id, tag: { id, name }, ... }
// 新: { tag_id, tag_name, type, amount, category_id, category_name, category_icon, count }

function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  selectedTagId.value = tpl.tag_id
  selectedTagName.value = tpl.tag_name
  consumeDate.value = dayjs().format('YYYY-MM-DD')
  consumeTime.value = dayjs().format('HH:mm')
  note.value = ''
}
```

模板 chip 显示调整：
```html
<v-chip ...>
  {{ tpl.tag_name }} · ¥{{ tpl.amount }}
</v-chip>
```

#### 4.2.2 设置页快速记账管理（需求 #10）

**前端改动：**

**文件：** `frontend/src/pages/SettingsPage.vue`

新增**快速记账管理**卡片 section：

```html
<v-card class="pa-4 mb-3 settings-card" rounded="xl">
  <div class="d-flex justify-space-between align-center mb-3">
    <div class="d-flex align-center">
      <v-avatar size="36" color="rgba(0, 150, 136, 0.1)" class="mr-2">
        <v-icon color="teal" size="20">mdi-lightning-bolt</v-icon>
      </v-avatar>
      <span class="text-subtitle-2 font-weight-bold">快速记账</span>
    </div>
    <v-btn size="small" color="primary" variant="tonal" @click="showQuickTemplateDialog = true">
      <v-icon start size="small">mdi-plus</v-icon>
      新增
    </v-btn>
  </div>

  <!-- 快速记账模板列表 -->
  <div v-if="quickTemplates.length === 0" class="text-center pa-4 text-grey text-caption">
    暂无快速记账模板
  </div>

  <v-list v-else density="compact" class="bg-transparent pa-0">
    <v-list-item v-for="tpl in quickTemplates" :key="tpl.tag_id + '-' + tpl.amount">
      <template v-slot:prepend>
        <v-avatar size="32" :color="tpl.type === 'expense' ? '#FFE8E8' : '#E8FFF3'" class="mr-2">
          <v-icon size="16" :color="tpl.type === 'expense' ? '#FF6B6B' : '#20C997'">
            {{ tpl.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
          </v-icon>
        </v-avatar>
      </template>
      <v-list-item-title class="text-body-2">
        {{ tpl.tag_name }} · ¥{{ tpl.amount }}
      </v-list-item-title>
      <v-list-item-subtitle class="text-caption">
        {{ tpl.category_name }} · 使用 {{ tpl.count }} 次
      </v-list-item-subtitle>
      <template v-slot:append>
        <v-btn icon variant="text" size="x-small" @click="removeQuickTemplate(tpl)">
          <v-icon size="small" color="error">mdi-delete</v-icon>
        </v-btn>
      </template>
    </v-list-item>
  </v-list>
</v-card>
```

**新增模板对话框：**

```html
<v-dialog v-model="showQuickTemplateDialog" max-width="400">
  <v-card class="pa-4" rounded="xl">
    <v-card-title class="text-h6 pa-0 mb-4">新增快速记账</v-card-title>
    <v-select
      v-model="quickTemplateForm.tag_id"
      :items="availableTags"
      item-title="name"
      item-value="id"
      label="选择标签 *"
      :rules="[v => !!v || '请选择标签']"
      class="mb-3"
      @update:model-value="onQuickTemplateTagChange"
    />
    <v-text-field
      v-model.number="quickTemplateForm.amount"
      label="金额 *"
      type="number"
      prefix="¥"
      :rules="[v => v > 0 || '请输入金额']"
      class="mb-3"
    />
    <div class="d-flex justify-end ga-2">
      <v-btn variant="text" @click="showQuickTemplateDialog = false">取消</v-btn>
      <v-btn color="primary" @click="saveQuickTemplate">保存</v-btn>
    </div>
  </v-card>
</v-dialog>
```

**后端改动：**

需要新增 API 用于手动添加快速记账模板。但考虑到快速记账模板是从记录中聚合而来（非独立实体），手动添加的实现方式为：

**方案：** 手动添加 = 创建 2 条相同的记录（触发 >= 2 次的阈值），然后立即删除这两条记录，改为直接在 `quick_templates` 表中存储。

**更简洁的方案：** 新增 `quick_templates` 表，独立于 records 表管理。

**文件：** `backend/app/models/quick_template.py`（新建）

```python
class QuickTemplate(SQLModel, table=True):
    __tablename__ = "quick_templates"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(foreign_key="users.id", ondelete="CASCADE")
    tag_id: int | None = Field(foreign_key="tags.id", ondelete="SET NULL")
    category_id: int | None = Field(foreign_key="categories.id", ondelete="SET NULL")
    type: str  # "expense" / "income"
    amount: float
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
```

**文件：** `backend/app/routers/records.py`

新增 API：
- `GET /api/quick-templates` — 获取快速记账模板（合并自动 + 手动）
- `POST /api/quick-templates` — 手动添加模板
- `DELETE /api/quick-templates/{id}` — 删除模板

**合并逻辑：**
1. 从 records 表聚合出现 >= 2 次的组合（自动模板）
2. 从 quick_templates 表获取手动添加的模板
3. 去重合并，按最近使用排序

### 4.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 首次记录"午餐 25 元" | 不出现在快速记账 |
| 第 2 次记录"午餐 25 元" | 出现在快速记账 |
| 设置页查看快速记账列表 | 显示所有模板 |
| 设置页删除快速记账项 | 项消失 |
| 设置页手动添加快速记账 | 添加成功，记账页可见 |
| 已删除标签的模板不显示 | 过滤正确 |

---

## 模块 5：记账页 - 标签搜索联想

**需求编号：** #11
**优先级：** 中
**影响范围：** 前端 RecordFormPage.vue，后端 tags API

### 5.1 现状分析

当前标签输入使用 `v-combobox`，输入时从已加载的全量标签列表中过滤。需求要求改为搜索联想模式：点击不显示历史，输入 1 字符后开始搜索，选择后自动填入分类。

### 5.2 设计方案

#### 前端改动

**文件：** `frontend/src/pages/RecordFormPage.vue`

将标签输入从 `v-combobox` 改为 `v-autocomplete` + 自定义搜索逻辑：

```html
<v-autocomplete
  v-model="selectedTagId"
  v-model:search="tagSearchQuery"
  :items="tagSearchResults"
  item-title="name"
  item-value="id"
  placeholder="输入标签名称搜索"
  hide-details
  variant="outlined"
  density="compact"
  clearable
  no-filter
  :loading="tagSearching"
  @update:search="onTagSearch"
  @update:model-value="onTagSelected"
>
  <template v-slot:no-data>
    <v-list-item v-if="tagSearchQuery && tagSearchQuery.length >= 1">
      <v-list-item-title class="text-caption text-grey">
        无匹配标签，按回车创建「{{ tagSearchQuery }}」
      </v-list-item-title>
    </v-list-item>
  </template>
</v-autocomplete>
```

**搜索逻辑：**

```javascript
const tagSearchQuery = ref('')
const tagSearchResults = ref([])
const tagSearching = ref(false)
let searchDebounceTimer = null

async function onTagSearch(query) {
  if (!query || query.length < 1) {
    tagSearchResults.value = []
    return
  }
  // 防抖 200ms
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(async () => {
    tagSearching.value = true
    try {
      // 调用后端搜索 API
      const results = await searchTags(query)
      tagSearchResults.value = results
    } catch (e) {
      console.error('Tag search error:', e)
    } finally {
      tagSearching.value = false
    }
  }, 200)
}
```

**选择标签后自动填入分类：**

```javascript
function onTagSelected(tagId) {
  if (!tagId) {
    selectedTagId.value = null
    return
  }
  const tag = tagSearchResults.value.find(t => t.id === tagId)
  if (tag && tag.category_id) {
    categoryId.value = tag.category_id
  }
  selectedTagId.value = tagId
}
```

**创建新标签：**

当搜索无结果时，支持回车创建：
```javascript
// 在 v-autocomplete 上监听 @keydown.enter
async function onCreateTagFromSearch() {
  if (!tagSearchQuery.value) return
  const newTag = await createTag({
    name: tagSearchQuery.value.trim(),
    category_id: categoryId.value,  // 使用当前选中的分类
  })
  selectedTagId.value = newTag.id
  tagSearchResults.value = [newTag]
}
```

#### 后端改动

**文件：** `backend/app/routers/tags.py`

新增搜索 API（或在现有 GET /api/tags 增加 `q` 参数）：

```python
@router.get("")
async def list_tags(
    q: str | None = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
) -> JSONResponse:
    tags = await tag_service.get_tags(db, current_user, search=q)
    return success_response(data=tags)
```

**文件：** `backend/app/services/tag_service.py`

```python
async def get_tags(db, current_user, search=None):
    query = select(Tag).where(Tag.deleted_at.is_(None))
    if current_user:
        query = query.where(Tag.user_id == current_user.id)
    if search:
        query = query.where(Tag.name.contains(search))
    query = query.limit(20)  # 限制搜索结果数量
    result = await db.exec(query)
    return [serialize_tag(t) for t in result.all()]
```

### 5.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 点击标签输入框 | 不显示历史记录列表 |
| 输入"午" | 200ms 后显示包含"午"的标签 |
| 选择"午餐" | 标签填入，分类自动设为"餐饮" |
| 输入无匹配文字 | 显示"无匹配标签"提示 |
| 按回车创建新标签 | 标签创建成功并选中 |
| 输入框清空 | 分类不受影响 |

---

## 模块 6：账单页 - 按钮位置修正

**需求编号：** #2
**优先级：** 中
**影响范围：** 前端 RecordDetailPage.vue

### 6.1 现状分析

当前 [RecordDetailPage.vue](frontend/src/pages/RecordDetailPage.vue:119-142) 的操作按钮区域：

```html
<div class="d-flex ga-3">
  <v-btn ... block>编辑</v-btn>
  <v-btn ... block>删除</v-btn>
</div>
```

两个按钮使用 `block` 属性（宽度 100%），通过 `d-flex` 和 `ga-3` 排列。由于 `block` 让每个按钮占满 flex 行，实际效果是两个按钮各占约 50% 宽度，但可能因 `ga-3` 间距导致溢出或不对称。

### 6.2 设计方案

**文件：** `frontend/src/pages/RecordDetailPage.vue`

将按钮容器改为居中对齐，并保持与快速记账页的"支出/收入"按钮风格一致：

```html
<!-- Action Buttons -->
<div class="d-flex justify-center ga-3 mt-4">
  <v-btn
    color="primary"
    variant="tonal"
    size="large"
    rounded="xl"
    class="flex-grow-1"
    style="max-width: 200px;"
    @click="goToEdit"
  >
    <v-icon start>mdi-pencil</v-icon>
    编辑
  </v-btn>
  <v-btn
    color="error"
    variant="tonal"
    size="large"
    rounded="xl"
    class="flex-grow-1"
    style="max-width: 200px;"
    @click="showDeleteConfirm = true"
  >
    <v-icon start>mdi-delete</v-icon>
    删除
  </v-btn>
</div>
```

**关键改动：**
- 移除 `block` 属性（block 让按钮占满父容器宽度）
- 添加 `justify-center` 让按钮组居中
- 使用 `flex-grow-1` + `max-width: 200px` 让按钮等宽但不超过 200px
- 添加 `mt-4` 与上方内容保持间距

### 6.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 桌面端查看账单详情 | 编辑和删除按钮居中显示 |
| 移动端查看账单详情 | 按钮居中，不溢出屏幕 |
| 按钮风格 | 与快速记账页的支出/收入按钮一致（rounded-xl, tonal） |

---

## 模块 7：账单页 - 分类筛选优化

**需求编号：** #3
**优先级：** 中
**影响范围：** 前端 RecordListPage.vue

### 7.1 现状分析

当前 [RecordListPage.vue](frontend/src/pages/RecordListPage.vue:55-57) 的筛选栏有一个搜索按钮：

```html
<v-btn color="primary" variant="tonal" size="small" @click="search" class="search-btn">
  <v-icon>mdi-magnify</v-icon>
</v-btn>
```

用户需要手动点击搜索按钮才能触发筛选。需求要求选择分类后立即触发筛选。

### 7.2 设计方案

**文件：** `frontend/src/pages/RecordListPage.vue`

**改动 1：移除搜索按钮**

删除搜索按钮的 HTML：
```diff
- <v-btn color="primary" variant="tonal" size="small" @click="search" class="search-btn">
-   <v-icon>mdi-magnify</v-icon>
- </v-btn>
```

**改动 2：添加 watch 监听筛选条件变化**

```javascript
import { ref, reactive, computed, onMounted, watch } from 'vue'

// 监听筛选条件变化，自动触发搜索
watch(
  () => [filters.type, filters.category_id, filters.start_date, filters.end_date],
  () => {
    search()
  },
  { deep: true }
)
```

**改动 3：防抖处理**

为避免快速切换筛选条件时频繁请求，添加防抖：

```javascript
let searchDebounceTimer = null

function debouncedSearch() {
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    search()
  }, 300)
}

watch(
  () => [filters.type, filters.category_id],
  () => {
    debouncedSearch()
  }
)
```

**注意：** 日期筛选（`start_date`, `end_date`）由月份选择器触发，已有 `selectMonth` 函数直接调用 `search()`，无需额外 watch。

### 7.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 选择分类后 | 立即显示筛选结果（300ms 内） |
| 切换类型筛选 | 立即更新结果 |
| 搜索按钮已移除 | 筛选栏无放大镜图标 |
| 快速切换筛选条件 | 无重复请求（防抖生效） |
| 月份切换 | 筛选正常工作 |

---

## 模块 8：深色模式 - 字体可读性优化

**需求编号：** #4
**优先级：** 中
**影响范围：** 前端 main.js、global.scss

### 8.1 现状分析

当前深色模式下，`global.scss` 已有一些文字颜色覆盖（`#E0E0E0`、`#B0B0B0`），但可能存在以下问题：
- 部分页面使用内联 `style="color: rgba(0,0,0,0.45)"` 硬编码了黑色系颜色
- 副标题（`text-caption` + `text-grey`）在深色模式下对比度不足
- Vuetify 的 `text-grey` 类在深色模式下仍使用浅灰色，可能不够明显

### 8.2 设计方案

#### 8.2.1 全局深色模式文字颜色

**文件：** `frontend/src/styles/global.scss`

增强深色模式文字颜色覆盖：

```scss
/* Dark mode text colors - enhanced */
.v-theme--dark {
  color: #E6E1E5;
}

/* 主标题：纯白 */
.v-theme--dark .text-h5,
.v-theme--dark .text-h6,
.v-theme--dark .text-subtitle-1,
.v-theme--dark .text-subtitle-2,
.v-theme--dark .font-weight-bold {
  color: #FFFFFF !important;
}

/* 正文：浅灰 */
.v-theme--dark .text-body-1,
.v-theme--dark .text-body-2 {
  color: #E6E1E5 !important;
}

/* 副标题/说明文字：中灰（提高对比度） */
.v-theme--dark .text-caption {
  color: #C8C3CE !important;  /* 从 #B0B0B0 提高到更亮的灰色 */
}

/* 辅助文字：灰色 */
.v-theme--dark .text-grey {
  color: #C8C3CE !important;  /* 从 #B0B0B0 提高 */
}

/* 浅灰色文字（如"未设置标签"） */
.v-theme--dark .text-grey-lighten-1 {
  color: #A0A0A0 !important;
}
```

#### 8.2.2 修复内联颜色

需要检查各页面中使用内联 `style="color: rgba(0,0,0,0.45)"` 的地方，改为使用 Vuetify 的主题感知类。

**需检查的文件：**

| 文件 | 位置 | 当前值 | 修改为 |
|------|------|--------|--------|
| `SettingsPage.vue:463` | `.page-subtitle` | `color: rgba(0, 0, 0, 0.45)` | 使用 `text-caption text-grey` 类 |
| `RecordDetailPage.vue:225` | `.page-subtitle` | `color: rgba(0, 0, 0, 0.45)` | 同上 |
| `RecordListPage.vue:308` | `.page-subtitle` | `color: rgba(0, 0, 0, 0.45)` | 同上 |
| `RecordFormPage.vue:413` | `.page-subtitle` | `color: rgba(0, 0, 0, 0.45)` | 同上 |
| `AppLayout.vue:118` | 副标题 | `style="color: rgba(0,0,0,0.45)"` | 移除 inline style，使用类 |

**统一方案：** 在 `global.scss` 中定义 `.page-subtitle` 类：

```scss
.page-subtitle {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
  margin: 2px 0 0;
}

.v-theme--dark .page-subtitle {
  color: #C8C3CE !important;
}
```

各页面的 `.page-subtitle` 样式可以移除 inline 颜色定义，改为使用全局类。

#### 8.2.3 深色模式主题色微调

**文件：** `frontend/src/main.js`

微调深色主题的 `on-surface-variant` 颜色，提升副标题对比度：

```javascript
dark: {
  colors: {
    // ... 现有颜色
    'on-surface-variant': '#CAC4D0',  // 已有，保持
  },
},
```

此颜色已较合理，主要问题在于组件使用了硬编码颜色而非主题变量。

### 8.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 深色模式首页副标题 | 文字清晰可读，对比度 >= 4.5:1 |
| 深色模式账单页副标题 | 文字清晰可读 |
| 深色模式统计页副标题 | 文字清晰可读 |
| 深色模式预算页副标题 | 文字清晰可读 |
| 深色模式设置页 | 所有 section 标题和说明文字可读 |
| 浅色模式无影响 | 所有页面颜色不变 |

---

## 模块 9：移动端底部导航栏

**需求编号：** #6
**优先级：** 高
**影响范围：** 前端 AppLayout.vue

### 9.1 现状分析

当前移动端（< 960px）使用侧边栏抽屉（`v-navigation-drawer` temporary 模式），需要点击汉堡按钮才能展开导航。需求要求竖屏模式下显示底部导航栏替代侧边栏。

### 9.2 设计方案

**文件：** `frontend/src/components/layout/AppLayout.vue`

#### 9.2.1 条件渲染侧边栏

在移动端隐藏侧边栏：

```html
<!-- Navigation Drawer - 仅桌面端显示 -->
<v-navigation-drawer
  v-if="display.mdAndUp"
  v-model="drawer"
  :permanent="!rail"
  :rail="false"
  :width="240"
  class="app-sidebar"
  elevation="0"
>
  <!-- 现有侧边栏内容不变 -->
</v-navigation-drawer>
```

#### 9.2.2 新增底部导航栏

在 `v-app` 内、`v-main` 之后添加底部导航栏：

```html
<!-- Bottom Navigation Bar - 仅移动端显示 -->
<v-bottom-navigation
  v-if="!display.mdAndUp"
  v-model="currentRoute"
  grow
  class="bottom-nav"
>
  <v-btn :value="'/'" to="/">
    <v-icon>mdi-view-dashboard-outline</v-icon>
    <span>主页</span>
  </v-btn>
  <v-btn :value="'/records'" to="/records">
    <v-icon>mdi-format-list-bulleted</v-icon>
    <span>账单</span>
  </v-btn>
  <v-btn :value="'/statistics'" to="/statistics">
    <v-icon>mdi-chart-box-outline</v-icon>
    <span>统计</span>
  </v-btn>
  <v-btn :value="'/settings'" to="/settings">
    <v-icon>mdi-cog-outline</v-icon>
    <span>设置</span>
  </v-btn>
</v-bottom-navigation>
```

**状态管理：**

```javascript
const currentRoute = computed(() => {
  // 匹配一级路径
  const path = route.path
  if (path === '/') return '/'
  if (path.startsWith('/records') || path.startsWith('/detail')) return '/records'
  if (path.startsWith('/statistics')) return '/statistics'
  if (path.startsWith('/settings')) return '/settings'
  return '/'
})
```

#### 9.2.3 FAB 按钮上移

在移动端，FAB 按钮需要上移以避开底部导航栏：

```scss
.fab-add {
  position: fixed !important;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  // ... 现有样式
}

@media (max-width: 959px) {
  .fab-add {
    bottom: 80px;  // 上移，避开底部导航栏（高度约 56px）
    right: 16px;
  }

  .content-wrapper {
    padding: 16px 16px 100px;  // 底部 padding 增大，为底部导航栏留空间
  }
}
```

#### 9.2.4 移动端汉堡按钮

移动端不再需要汉堡按钮（侧边栏已隐藏），但可以保留用于显示设置等：

```html
<!-- Top Bar -->
<div class="app-top-bar pa-4 pb-0">
  <div class="d-flex align-center">
    <!-- 汉堡按钮 - 仅桌面端显示 -->
    <v-btn
      v-if="display.mdAndUp"
      icon
      variant="text"
      class="mr-2"
      @click="toggleNav()"
    >
      <v-icon>{{ rail ? 'mdi-menu' : 'mdi-close' }}</v-icon>
    </v-btn>
    <!-- ... -->
  </div>
</div>
```

#### 9.2.5 底部导航栏样式

```scss
.bottom-nav {
  border-top: 1px solid rgba(0, 0, 0, 0.06) !important;
}

.v-theme--dark .bottom-nav {
  border-top-color: rgba(255, 255, 255, 0.06) !important;
}
```

### 9.3 验收测试

| 测试项 | 预期结果 |
|--------|----------|
| 竖屏（< 960px）底部导航栏 | 显示 4 个图标：主页、账单、统计、设置 |
| 竖屏侧边栏 | 不显示 |
| 横屏（>= 960px）侧边栏 | 正常显示 |
| 横屏底部导航栏 | 不显示 |
| 点击底部导航项 | 正确路由跳转，高亮当前页 |
| FAB 按钮位置 | 在底部导航栏上方，不重叠 |
| FAB 功能 | 点击跳转到记账页 |
| 页面底部内容 | 不被底部导航栏遮挡 |

---

## 数据库变更汇总

| 变更 | SQL | 影响模块 |
|------|-----|----------|
| tags 表增加 deleted_at 列 | `ALTER TABLE tags ADD COLUMN deleted_at TEXT DEFAULT NULL;` | 模块 2 |
| quick_templates 表（新建） | 见模块 4.2.2 | 模块 4 |

---

## API 变更汇总

| 方法 | 路径 | 变更类型 | 说明 | 影响模块 |
|------|------|----------|------|----------|
| GET | `/api/tags` | 修改 | 增加 `q` 查询参数用于搜索；过滤 `deleted_at` | 模块 2, 5 |
| DELETE | `/api/tags/{id}` | 修改 | 改为软删除（设置 `deleted_at`） | 模块 2 |
| GET | `/api/quick-templates` | 修改 | 改为聚合逻辑（>= 2 次） | 模块 4 |
| POST | `/api/quick-templates` | 新增 | 手动添加快速记账模板 | 模块 4 |
| DELETE | `/api/quick-templates/{id}` | 新增 | 删除快速记账模板 | 模块 4 |
