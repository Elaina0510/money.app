# Money App v1.2.1 详细设计文档

> 版本：v1.2.1  
> 日期：2026-05-31  
> 基于需求文档：`doc/proposalv1.2.1.md`  
> 对应需求项：13 项 Bug 修复 + 4 项功能补全

---

## 一、文档概述

本文档针对 v1.2.1 需求文档中的全部 17 项内容（去重后 14 个独立模块），逐一给出详细设计方案。每个模块独立设计，可独立开发和测试。

需求编号与模块编号映射：

| 需求编号 | 类型 | 模块编号 | 简述 |
|:---:|:---:|:---:|------|
| Bug 1 | 🐛 | 模块 1 | 竖屏侧边栏过宽 |
| Bug 2 | 🐛 | 模块 2 | 快速记账时间被重置 |
| Bug 3 / 功能 3 | 🐛/✨ | 模块 3 | 账单页月份切换横条 |
| Bug 4 / 功能 4 | 🐛/✨ | 模块 4 | 快速记账显示标签名 |
| Bug 5 | 🐛 | 模块 5 | 标签删除确认问题 |
| Bug 6 | 🐛 | 模块 6 | 预设分类支持删除 |
| Bug 7 | 🐛 | 模块 7 | 登录后边栏不刷新 |
| Bug 8 | 🐛 | 模块 8 | 深色模式滚动条 |
| Bug 9 | 🐛 | 模块 9 | 深色模式文字颜色 |
| Bug 10 | 🐛 | 模块 10 | 数据隔离所有权校验 |
| Bug 11 / 功能 2 | 🐛/✨ | 模块 11 | 统计页饼图改柱状图 |
| Bug 12 | 🐛 | 模块 12 | 记账页支出/收入按钮比例失衡 |
| Bug 13 | 🐛 | 模块 13 | 设置页分类管理不显示分类列表 |
| 功能 1 | ✨ | 模块 14 | 预算页支持编辑 |

---

## 二、模块设计

---

### 模块 1：竖屏侧边栏缩窄（Bug 1）

**问题定位**

- 文件：`frontend/src/components/layout/AppLayout.vue`（第 10 行）
- 现状：`v-navigation-drawer` 的 `:width` 在竖屏模式下为 `72px`，用户反馈仍然偏宽

**修复方案**

将竖屏侧边栏宽度从 `72px` 缩小至 `56px`，同时隐藏侧边栏文字标题（仅保留图标），使侧边栏更紧凑。

**代码变更**

文件：`frontend/src/components/layout/AppLayout.vue`

```html
<!-- 修改前（第 10 行） -->
:width="display.mdAndUp ? 240 : 72"

<!-- 修改后 -->
:width="display.mdAndUp ? 240 : 56"
```

隐藏竖屏模式下的文字标题：

```html
<!-- 修改前（第 43 行） -->
<v-list-item-title class="text-body-2 font-weight-medium">
  {{ item.title }}
</v-list-item-title>

<!-- 修改后：竖屏隐藏文字 -->
<v-list-item-title
  class="text-body-2 font-weight-medium"
  :class="{ 'd-none': !display.mdAndUp }"
>
  {{ item.title }}
</v-list-item-title>
```

侧边栏头部文字同样在竖屏隐藏：

```html
<!-- 修改前（第 19-22 行） -->
<div class="sidebar-header-text" style="min-width:0">
  <div class="text-subtitle-2 font-weight-bold text-truncate" style="line-height: 1.2">Money App</div>
  <div class="text-caption text-truncate" style="color: rgba(0,0,0,0.5)">个人记账</div>
</div>

<!-- 修改后 -->
<div class="sidebar-header-text" style="min-width:0" v-show="display.mdAndUp">
  <div class="text-subtitle-2 font-weight-bold text-truncate" style="line-height: 1.2">Money App</div>
  <div class="text-caption text-truncate" style="color: rgba(0,0,0,0.5)">个人记账</div>
</div>
```

**影响范围**

- 仅修改 `AppLayout.vue`
- 不涉及后端变更

**测试要点**

1. 竖屏（<960px）打开侧边栏，宽度为 56px，仅显示图标
2. 宽屏（≥960px）侧边栏宽度仍为 240px，正常显示图标+文字
3. 竖屏侧边栏不遮挡过多内容区域
4. 导航项点击功能正常

---

### 模块 2：快速记账时间保留（Bug 2）

**问题定位**

- 文件：`frontend/src/pages/RecordFormPage.vue`
- 函数：`fillTemplate()`（第 295-312 行）
- 原因：`fillTemplate` 中直接用模板的 `consume_time` 覆盖了用户已选时间

**修复方案**

移除 `fillTemplate()` 中对 `consumeDate` 和 `consumeTime` 的赋值逻辑。需求明确：时间应保持当前时间不变（而非保留用户已选时间）。

**代码变更**

文件：`frontend/src/pages/RecordFormPage.vue`

```javascript
// 修改前（第 295-312 行）
function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  if (tpl.consume_time) {
    consumeDate.value = tpl.consume_time.substring(0, 10)
    consumeTime.value = tpl.consume_time.substring(11, 16)
  }
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

// 修改后
function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  // 时间重置为当前时间，不使用模板的历史时间
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

**影响范围**

- 仅修改 `RecordFormPage.vue` 的 `fillTemplate()` 函数
- 不涉及后端变更

**测试要点**

1. 在记账页手动修改时间为非当前时间
2. 点击快速记账模板
3. 验证时间被重置为当前时间（而非模板的历史时间，也非用户手动修改的时间）
4. 验证其他字段（金额、分类、标签、备注）正常填充

---

### 模块 3：账单页月份切换横条（Bug 3 / 功能 3）

**问题定位**

- 文件：`frontend/src/pages/RecordListPage.vue`
- 原因：当前页面只有日期范围筛选器，缺少快速月份切换横条

**修复方案**

在筛选栏下方添加横向可滑动的月份切换条：
- 月份标签：`1月 2月 3月 ... 12月`
- 当前年份不标注年份，过去年份下方小字标注年份
- 默认选中当前月份
- 点击月份后刷新该月账单
- 竖屏可左右滑动
- 宽屏提供左右箭头切换年份

**代码变更**

文件：`frontend/src/pages/RecordListPage.vue`

**脚本新增**：

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

function prevYear() {
  selectedYear.value--
}

function nextYear() {
  if (selectedYear.value < currentYear) {
    selectedYear.value++
  }
}
```

**模板新增**（在 Filter Bar 与 Batch Actions Bar 之间）：

```html
<!-- Month Selector Bar -->
<v-card class="pa-2 mb-3" rounded="xl">
  <div class="d-flex align-center">
    <!-- 宽屏：左箭头切换年份 -->
    <v-btn
      v-if="selectedYear !== currentYear - 5"
      icon
      variant="text"
      size="x-small"
      class="d-none d-md-flex"
      @click="prevYear"
    >
      <v-icon size="small">mdi-chevron-left</v-icon>
    </v-btn>

    <!-- 月份条 -->
    <div class="d-flex ga-1 overflow-x-auto flex-grow-1 pb-1" style="scrollbar-width: none;">
      <div
        v-for="m in 12"
        :key="m"
        class="text-center flex-shrink-0"
        style="min-width: 48px;"
      >
        <v-chip
          :color="selectedMonth === m && selectedYear === currentYear ? 'primary' : ''"
          :variant="selectedMonth === m ? 'flat' : 'text'"
          size="small"
          rounded="xl"
          @click="selectMonth(m)"
        >
          {{ m }}月
        </v-chip>
        <!-- 过去年份标注年份 -->
        <div
          v-if="selectedYear !== currentYear"
          class="text-caption text-grey"
          style="font-size: 10px; line-height: 1; margin-top: 2px;"
        >
          {{ selectedYear }}
        </div>
      </div>
    </div>

    <!-- 宽屏：右箭头切换年份 -->
    <v-btn
      v-if="selectedYear < currentYear"
      icon
      variant="text"
      size="x-small"
      class="d-none d-md-flex"
      @click="nextYear"
    >
      <v-icon size="small">mdi-chevron-right</v-icon>
    </v-btn>
  </div>
</v-card>
```

**脚本修改**（`onMounted` 中初始化选中月份并自动筛选）：

```javascript
onMounted(async () => {
  try {
    categories.value = await getCategories()
    selectMonth(new Date().getMonth() + 1)
  } catch (e) {
    console.error('List load error:', e)
  }
})
```

**影响范围**

- 仅修改 `RecordListPage.vue`
- 不涉及后端变更

**测试要点**

1. 账单页默认选中当前月份，显示当前月账单
2. 点击其他月份，自动刷新为该月账单
3. 当前年份月份条不显示年份标注
4. 点击宽屏箭头切换到上一年，月份条下方显示年份
5. 竖屏月份条可横向滚动
6. 月份切换后，顶部日期筛选器的值同步更新

---

### 模块 4：快速记账显示标签名（Bug 4 / 功能 4）

**问题定位**

- 文件：`frontend/src/pages/RecordFormPage.vue`（第 200 行）
- 原因：快速记账模板 chip 显示的是 `tpl.category_name`，应改为显示标签名

**修复方案**

修改模板 chip 的显示文字，优先显示标签名，无标签时回退到分类名。

**代码变更**

文件：`frontend/src/pages/RecordFormPage.vue`

```html
<!-- 修改前（第 200 行） -->
{{ tpl.category_name }} · ¥{{ tpl.amount }}

<!-- 修改后 -->
{{ tpl.tag?.name || tpl.category_name }} · ¥{{ tpl.amount }}
```

**影响范围**

- 仅修改 `RecordFormPage.vue` 的模板显示
- 不涉及后端变更

**测试要点**

1. 有标签的快速记账模板，显示 `标签名 · ¥金额`
2. 无标签的快速记账模板，显示 `分类名 · ¥金额`
3. 点击后其他字段正常填充

---

### 模块 5：标签删除确认问题（Bug 5）

**问题定位**

- 文件：`frontend/src/pages/SettingsPage.vue`
- 需求描述：点击"删除"图标弹出确认框，但在确认之前标签已被删除
- 需核实：当前代码使用 `ConfirmDialog` 组件，`handleDeleteTag` 在 `@confirm` 回调中执行。需检查是否存在 `v-chip` 的 `closable` 属性导致视觉上提前消失的问题。

**修复方案**

检查并确保：
1. `deleteTag()` API 调用只在用户确认后才执行
2. 确认前标签在视觉上不消失

移除 `v-chip` 的 `closable` 属性，改为在 chip 内添加独立的删除图标按钮，点击后弹出确认框，确认后才调用 API。

**代码变更**

文件：`frontend/src/pages/SettingsPage.vue`

```html
<!-- 修改前（第 176-188 行） -->
<v-chip
  v-for="tag in tags"
  :key="tag.id"
  closable
  size="small"
  variant="tonal"
  class="mb-1"
  @click:close="confirmDeleteTag(tag)"
>
  <v-icon start size="x-small">mdi-tag</v-icon>
  {{ tag.name }}
</v-chip>

<!-- 修改后 -->
<v-chip
  v-for="tag in tags"
  :key="tag.id"
  size="small"
  variant="tonal"
  class="mb-1"
>
  <v-icon start size="x-small">mdi-tag</v-icon>
  {{ tag.name }}
  <template v-slot:append>
    <v-icon
      size="x-small"
      class="ml-1 tag-delete-icon"
      @click.stop="confirmDeleteTag(tag)"
    >
      mdi-close
    </v-icon>
  </template>
</v-chip>
```

**样式新增**：

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

**影响范围**

- 仅修改 `SettingsPage.vue` 的标签列表显示
- 不涉及后端变更

**测试要点**

1. 点击标签的删除图标，标签不消失，弹出确认对话框
2. 点击"取消"，标签不消失、不删除
3. 点击"删除"，确认后才调用 API，标签从列表移除
4. 确认对话框出现前，标签始终正常显示

---

### 模块 6：预设分类支持删除（Bug 6）

**问题定位**

- 前端文件：`frontend/src/pages/SettingsPage.vue`（第 49-57 行）— 删除按钮被 `v-if="!cat.is_preset"` 隐藏
- 后端文件：`backend/app/services/category_service.py`（`delete_category` 函数）— 存在关联账单时拒绝删除
- 后端路由：`backend/app/routers/categories.py`（`delete_category` 路由）— 未传入 `current_user`

**修复方案**

分前后端两部分修改：

**后端 service 修改**

文件：`backend/app/services/category_service.py`

1. `delete_category` 增加 `current_user` 参数，验证分类所有权
2. 移除"有关联账单则拒绝删除"的逻辑
3. 级联删除关联账单和预算
4. 返回被删除的账单数量

```python
async def delete_category(
    db: AsyncSession, category_id: int, current_user: User | None = None
) -> dict | None:
    """Delete a category and all related records/budgets."""
    category = await db.get(Category, category_id)
    if not category:
        return {"code": Code.NOT_FOUND, "message": "分类不存在"}

    # 所有权校验：预设分类所有人可删，自定义分类仅创建者可删
    if not category.is_preset and category.user_id and current_user and category.user_id != current_user.id:
        return {"code": Code.FORBIDDEN, "message": "无权删除此分类"}

    # 统计关联账单数量
    stmt = select(func.count(Record.id)).where(Record.category_id == category_id)
    result = await db.exec(stmt)
    record_count = result.one()

    # 级联删除关联账单
    if record_count > 0:
        records_stmt = select(Record).where(Record.category_id == category_id)
        records_result = await db.exec(records_stmt)
        for record in records_result.all():
            await db.delete(record)

    # 级联删除关联预算
    from app.models.budget import Budget
    budget_stmt = select(Budget).where(Budget.category_id == category_id)
    budget_result = await db.exec(budget_stmt)
    for budget in budget_result.all():
        await db.delete(budget)

    await db.delete(category)
    await db.commit()
    return {"deleted_records": record_count}
```

**后端路由修改**

文件：`backend/app/routers/categories.py`

```python
# 修改前
@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await category_service.delete_category(db, category_id)
    if result:
        return error_response(result["code"], result["message"])
    return success_response(message="分类删除成功")

# 修改后
@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    result = await category_service.delete_category(db, category_id, current_user)
    if result and "code" in result:
        return error_response(result["code"], result["message"])
    deleted_records = result.get("deleted_records", 0) if result else 0
    msg = "分类删除成功"
    if deleted_records > 0:
        msg = f"分类删除成功，同时删除了 {deleted_records} 条关联账单"
    return success_response(message=msg, data={"deleted_records": deleted_records})
```

**前端修改**

文件：`frontend/src/pages/SettingsPage.vue`

1. 移除删除按钮的 `v-if="!cat.is_preset"` 条件（支出分类和收入分类两处）

```html
<!-- 修改前 -->
<v-btn
  v-if="!cat.is_preset"
  icon
  variant="text"
  size="x-small"
  @click="confirmDeleteCategory(cat)"
>

<!-- 修改后 -->
<v-btn
  icon
  variant="text"
  size="x-small"
  @click="confirmDeleteCategory(cat)"
>
```

2. 修改 `confirmDeleteCategory` 函数，查询关联账单数量并更新确认消息：

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

3. 修改确认对话框使用动态消息：

```html
<ConfirmDialog
  v-model="showDeleteCategoryDialog"
  title="删除分类"
  :message="deleteCategoryMessage"
  confirm-text="删除"
  @confirm="handleDeleteCategory"
/>
```

**影响范围**

- 后端：`category_service.py`、`categories.py`
- 前端：`SettingsPage.vue`
- 需新增 `Code.FORBIDDEN` 错误码（如尚未定义）到 `backend/app/utils/response.py`
- 关联影响：删除分类后，通过 store 刷新各页面分类列表

**测试要点**

1. 预设分类显示删除按钮
2. 无关联账单的分类：直接删除，提示"删除成功"
3. 有关联账单的分类：弹出确认框，显示关联账单数量
4. 确认删除后，分类和关联账单均被删除
5. 删除后，记账页分类列表、账单页分类筛选器、统计页数据均同步更新
6. 删除有关联预算的分类时，预算也被清理

---

### 模块 7：登录后边栏刷新（Bug 7）

**问题定位**

- 文件：`frontend/src/components/layout/AppLayout.vue`（第 172-181 行）
- 原因：`AppLayout` 中的 `token` 和 `username` 是 `ref`，仅在 `onMounted` 时从 `localStorage` 读取一次。登录成功后跳转到 `/`，但 `AppLayout` 已挂载，不会重新执行 `onMounted`。

**修复方案**

需求指定方案：登录成功后通过 `window.dispatchEvent(new Event('auth:login'))` 通知 `AppLayout` 刷新登录状态。

**代码变更**

文件：`frontend/src/components/layout/AppLayout.vue`

```javascript
// 新增：监听登录事件
function handleAuthLogin() {
  checkLogin()
}

let authLoginHandler

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

文件：`frontend/src/pages/LoginPage.vue`

在 `handleLogin()` 和 `handleRegister()` 成功后，写入 localStorage 之后、路由跳转之前，派发事件：

```javascript
// handleLogin 成功后（第 187-190 行之间）
localStorage.setItem('token', result.access_token)
localStorage.setItem('username', result.username)
localStorage.setItem('userId', String(result.user_id))
window.dispatchEvent(new Event('auth:login'))  // 新增
router.replace('/')

// handleRegister 成功后（第 217-220 行之间）
localStorage.setItem('token', result.access_token)
localStorage.setItem('username', result.username)
localStorage.setItem('userId', String(result.user_id))
window.dispatchEvent(new Event('auth:login'))  // 新增
router.replace('/')
```

**影响范围**

- 修改 `AppLayout.vue`、`LoginPage.vue`
- 不涉及后端变更

**测试要点**

1. 退出登录后跳转到登录页
2. 重新登录成功后跳转到主页
3. 验证边栏立即显示用户名和头像，无需手动刷新
4. 注册成功后同样立即显示
5. 退出登录后边栏立即隐藏用户信息

---

### 模块 8：深色模式滚动条适配（Bug 8）

**问题定位**

- 文件：`frontend/src/styles/global.scss`（第 142-144 行）
- 原因：已有 `v-theme--dark ::-webkit-scrollbar-thumb` 样式，但缺少滚动条轨道（track）的深色背景

**修复方案**

按需求指定的色值补充深色模式滚动条样式：
- 轨道：`rgba(255, 255, 255, 0.1)`
- 滑块：`rgba(255, 255, 255, 0.3)`

**代码变更**

文件：`frontend/src/styles/global.scss`

```scss
// 修改前（第 142-144 行）
.v-theme--dark ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}

// 修改后
.v-theme--dark ::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
}

.v-theme--dark ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
}
```

**影响范围**

- 仅修改 `global.scss`
- 不涉及后端变更

**测试要点**

1. 切换到深色模式
2. 滚动页面，验证滚动条轨道背景为 `rgba(255,255,255,0.1)`
3. 滚动条滑块为 `rgba(255,255,255,0.3)`，可见且不突兀
4. 切换回浅色模式，滚动条恢复正常样式

---

### 模块 9：深色模式文字颜色（Bug 9）

**问题定位**

- 文件：`frontend/src/styles/global.scss`
- 原因：深色模式下正文文字颜色使用默认黑色，在深色背景上可读性差

**修复方案**

按需求指定的色值设置：
- 正文文字：`#E0E0E0`（浅灰白色）
- 标题：`#FFFFFF`（白色）

**代码变更**

文件：`frontend/src/styles/global.scss`

```scss
// 深色模式文字颜色
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

**影响范围**

- 仅修改 `global.scss`
- 不涉及后端变更

**测试要点**

1. 切换到深色模式
2. 验证正文文字为 `#E0E0E0`，清晰可读
3. 验证标题文字为 `#FFFFFF`，醒目
4. 验证灰色辅助文字为 `#B0B0B0`，与正文有层次区分
5. 切换回浅色模式，文字颜色恢复正常

---

### 模块 10：数据隔离 — 更新/删除所有权校验（Bug 10）

**问题定位**

- 后端文件：
  - `backend/app/services/record_service.py` — `update_record()`、`delete_record()`、`batch_delete_records()` 无所有权校验
  - `backend/app/services/category_service.py` — `update_category()`、`delete_category()` 无所有权校验
  - `backend/app/services/tag_service.py` — `update_tag()`、`delete_tag()` 无所有权校验
- 原因：查询操作正确过滤 `user_id`，但更新/删除操作不验证所有权，任何用户可通过 ID 修改/删除他人数据

**修复方案**

在每个 service 的 update/delete 方法中增加 `current_user` 参数，操作前验证资源的 `user_id` 是否匹配当前用户。不匹配返回 403。

**代码变更**

**record_service.py**

```python
async def update_record(
    db: AsyncSession, record_id: int, data: RecordUpdate,
    current_user: User | None = None
) -> dict[str, Any] | None:
    """Update an existing record."""
    record = await db.get(Record, record_id)
    if not record:
        return None

    # 所有权校验
    if current_user and record.user_id != current_user.id:
        raise PermissionError("无权修改此记录")
    if not current_user and record.user_id is not None:
        raise PermissionError("无权修改此记录")

    # ... 原有更新逻辑 ...


async def delete_record(db: AsyncSession, record_id: int, current_user: User | None = None) -> bool:
    """Delete a record."""
    record = await db.get(Record, record_id)
    if not record:
        return False

    # 所有权校验
    if current_user and record.user_id != current_user.id:
        raise PermissionError("无权删除此记录")
    if not current_user and record.user_id is not None:
        raise PermissionError("无权删除此记录")

    await db.delete(record)
    await db.commit()
    return True


async def batch_delete_records(
    db: AsyncSession, ids: list[int], current_user: User | None = None
) -> int:
    """Delete multiple records."""
    count = 0
    for rid in ids:
        record = await db.get(Record, rid)
        if record:
            # 所有权校验
            if current_user and record.user_id != current_user.id:
                raise PermissionError(f"无权删除记录 {rid}")
            if not current_user and record.user_id is not None:
                raise PermissionError(f"无权删除记录 {rid}")
            await db.delete(record)
            count += 1
    await db.commit()
    return count
```

**category_service.py**

```python
async def update_category(
    db: AsyncSession, category_id: int, data: CategoryUpdate,
    current_user: User | None = None
) -> Category | None:
    """Update an existing category."""
    category = await db.get(Category, category_id)
    if not category:
        return None

    # 所有权校验：预设分类所有人可编辑，自定义分类仅创建者可编辑
    if not category.is_preset and category.user_id and current_user and category.user_id != current_user.id:
        raise PermissionError("无权修改此分类")

    # ... 原有更新逻辑 ...
```

`delete_category` 的所有权校验已在模块 6 中设计。

**tag_service.py**

```python
async def update_tag(
    db: AsyncSession, tag_id: int, data: TagUpdate,
    current_user: User | None = None
) -> Tag | None:
    """Update a tag."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None

    # 所有权校验
    if current_user and tag.user_id != current_user.id:
        raise PermissionError("无权修改此标签")
    if not current_user and tag.user_id is not None:
        raise PermissionError("无权修改此标签")

    # ... 原有更新逻辑 ...


async def delete_tag(db: AsyncSession, tag_id: int, current_user: User | None = None) -> dict | None:
    """Delete a tag."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return {"code": Code.NOT_FOUND, "message": "标签不存在"}

    # 所有权校验
    if current_user and tag.user_id != current_user.id:
        return {"code": Code.FORBIDDEN, "message": "无权删除此标签"}
    if not current_user and tag.user_id is not None:
        return {"code": Code.FORBIDDEN, "message": "无权删除此标签"}

    await db.delete(tag)
    await db.commit()
    return None
```

**路由层修改**

在对应的 router 中将 `current_user` 传入 service 调用，并捕获 `PermissionError` 返回 403。

文件：`backend/app/routers/records.py`

```python
from fastapi import HTTPException

# update_record 路由增加 current_user 传入
@router.put("/{record_id}")
async def update_record(
    record_id: int,
    data: RecordUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    try:
        record = await record_service.update_record(db, record_id, data, current_user)
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e))
    # ... 原有逻辑 ...

# delete_record 路由增加 current_user 传入
@router.delete("/{record_id}")
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    try:
        deleted = await record_service.delete_record(db, record_id, current_user)
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e))
    # ... 原有逻辑 ...

# batch_delete 路由增加 current_user 传入
@router.post("/batch-delete")
async def batch_delete(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    try:
        count = await record_service.batch_delete_records(db, data.ids, current_user)
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e))
    # ... 原有逻辑 ...
```

`categories.py` 和 `tags.py` 的路由同理，将 `current_user` 传入 service。

**错误码补充**

文件：`backend/app/utils/response.py`

确认 `Code` 类中已定义 `FORBIDDEN` 错误码：

```python
class Code:
    SUCCESS = 0
    PARAM_ERROR = 40001
    NOT_FOUND = 40002
    CONFLICT = 40003
    FILE_INVALID = 40004
    FORBIDDEN = 40003  # 或新增 40005，视现有定义而定
    SERVER_ERROR = 50001
```

**影响范围**

- 后端：`record_service.py`、`category_service.py`、`tag_service.py`、`records.py`、`categories.py`、`tags.py`、`response.py`
- 前端：无需修改（已有 401 处理，403 会被统一错误处理拦截）

**测试要点**

1. 用户 A 创建的记录，用户 B 调用更新接口返回 403
2. 用户 A 创建的记录，用户 B 调用删除接口返回 403
3. 用户 A 创建的自定义分类，用户 B 调用更新/删除接口返回 403
4. 预设分类：所有用户可编辑/删除（不受所有权限制）
5. 用户 A 创建的标签，用户 B 调用更新/删除接口返回 403
6. 用户操作自己的数据正常，不受影响
7. 未登录用户操作有 user_id 的数据返回 403

---

### 模块 11：统计页分类统计柱状图（Bug 11 / 功能 2）

**问题定位**

- 前端文件：`frontend/src/pages/StatisticsPage.vue`
- 后端文件：`backend/app/services/statistics_service.py`（`get_category_stats` 函数）
- 问题 1：后端返回数据中不包含 `type` 字段，前端过滤后无数据
- 问题 2：当前使用饼图（Pie），需求要求使用柱状图（Bar）

**修复方案**

两部分修改：

**后端修改**

文件：`backend/app/services/statistics_service.py`

在 `get_category_stats()` 返回的每项数据中增加 `type` 字段：

```python
items.append({
    "category_id": category_id,
    "category_name": category_name,
    "icon": icon,
    "type": type_filter,  # 新增
    "total": total_val,
    "percentage": percentage,
    "count": count_val,
})
```

**前端修改**

文件：`frontend/src/pages/StatisticsPage.vue`

1. 导入替换：`Pie` → `Bar`，注册 `BarElement` 和 `BarController`

```javascript
// 修改前
import { Pie, Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Title, Filler,
} from 'chart.js'

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Title, Filler
)

// 修改后
import { Bar, Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  BarElement, BarController, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Title, Filler,
} from 'chart.js'

ChartJS.register(
  BarElement, BarController, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Title, Filler
)
```

2. 模板中将 `<Pie>` 替换为 `<Bar>`：

```html
<!-- 修改前（第 87 行） -->
<Pie :data="categoryChartData" :options="chartOptions" />

<!-- 修改后 -->
<Bar :data="categoryBarData" :options="barChartOptions" />
```

3. 移除前端的 `type` 过滤（后端已按 type 查询，无需前端再过滤）：

```javascript
// 修改前（第 292 行）
categoryStats.value = (c?.items || []).filter(item => item.type === 'expense')

// 修改后
categoryStats.value = c?.items || []
```

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
      callbacks: {
        label: (ctx) => `¥${Number(ctx.raw).toLocaleString()}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 10 } },
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

**影响范围**

- 后端：`statistics_service.py`
- 前端：`StatisticsPage.vue`
- 依赖：`chart.js` 已包含 `BarElement` 和 `BarController`，无需额外安装

**测试要点**

1. 有支出账单数据时，统计页显示柱状图，各分类名称在横轴，金额在纵轴
2. 不同分类使用不同颜色
3. 切换到收入类型，收入分类柱状图正确显示
4. 无账单数据时，正确显示"暂无数据"
5. 切换月份/年份后数据正确更新

---

### 模块 12：记账页支出/收入按钮比例失衡（Bug 12）

**问题定位**

- 文件：`frontend/src/pages/RecordFormPage.vue`（第 17-44 行）
- 现状：两个按钮均使用 `block` 属性（`width: 100%`），在 `d-flex` 容器中导致布局异常，支出按钮占据大部分宽度，收入按钮被挤压
- v1.1 中两个按钮等宽各占 50%

**修复方案**

移除两个按钮的 `block` 属性，改用 `flex: 1` 实现等宽布局。

**代码变更**

文件：`frontend/src/pages/RecordFormPage.vue`

```html
<!-- 修改前（第 17-44 行） -->
<div class="d-flex mb-4 ga-2">
  <v-btn
    :color="recordType === 'expense' ? '#FF6B6B' : ''"
    :variant="recordType === 'expense' ? 'flat' : 'outlined'"
    block
    size="large"
    rounded="xl"
    class="type-btn expense-btn"
    :class="{ 'active-expense': recordType === 'expense' }"
    @click="recordType = 'expense'"
  >
    <v-icon start>mdi-arrow-down</v-icon>
    支出
  </v-btn>
  <v-btn
    :color="recordType === 'income' ? '#20C997' : ''"
    :variant="recordType === 'income' ? 'flat' : 'outlined'"
    block
    size="large"
    rounded="xl"
    class="type-btn income-btn"
    :class="{ 'active-income': recordType === 'income' }"
    @click="recordType = 'income'"
  >
    <v-icon start>mdi-arrow-up</v-icon>
    收入
  </v-btn>
</div>

<!-- 修改后 -->
<div class="d-flex mb-4 ga-2">
  <v-btn
    :color="recordType === 'expense' ? '#FF6B6B' : ''"
    :variant="recordType === 'expense' ? 'flat' : 'outlined'"
    size="large"
    rounded="xl"
    class="type-btn expense-btn flex-grow-1"
    :class="{ 'active-expense': recordType === 'expense' }"
    @click="recordType = 'expense'"
  >
    <v-icon start>mdi-arrow-down</v-icon>
    支出
  </v-btn>
  <v-btn
    :color="recordType === 'income' ? '#20C997' : ''"
    :variant="recordType === 'income' ? 'flat' : 'outlined'"
    size="large"
    rounded="xl"
    class="type-btn income-btn flex-grow-1"
    :class="{ 'active-income': recordType === 'income' }"
    @click="recordType = 'income'"
  >
    <v-icon start>mdi-arrow-up</v-icon>
    收入
  </v-btn>
</div>
```

**影响范围**

- 仅修改 `RecordFormPage.vue` 的按钮布局
- 不涉及后端变更

**测试要点**

1. 竖屏和宽屏下，支出和收入按钮等宽并排，各占 50%
2. 点击按钮切换类型功能正常
3. 按钮样式（颜色、圆角、图标）无变化

---

### 模块 13：设置页分类管理不显示分类列表（Bug 13）

**问题定位**

- 文件：`frontend/src/pages/SettingsPage.vue`、`frontend/src/stores/useCategoriesStore.js`、`backend/app/services/category_service.py`、`backend/app/routers/categories.py`
- 现状：v1.1 正常显示分类，v1.2 显示"暂无分类"
- 可能原因：
  1. 后端 `get_categories()` 返回数据格式与前端期望不匹配
  2. 前端 `SettingsPage.vue` 的 `loadCategories()` 未正确处理 API 返回值
  3. Pinia Store 的 `fetchCategories()` 返回值处理有误
  4. API 响应拦截器解包后数据结构不一致

**排查方案**

按数据流逐层排查：后端 API → 前端 API 模块 → Pinia Store → SettingsPage 渲染。

**排查步骤**

**步骤 1：验证后端 API 返回格式**

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/categories
```

预期返回：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "id": 1, "name": "餐饮", "type": "expense", "icon": "mdi-food", ... },
    ...
  ]
}
```

**步骤 2：检查前端 API 模块解包**

文件：`frontend/src/api/request.js`

响应拦截器（第 24-31 行）在 `code === 0` 时返回 `res.data`。确认 `getCategories()` 返回的是分类数组而非包装对象。

**步骤 3：检查 Store 处理**

文件：`frontend/src/stores/useCategoriesStore.js`

```javascript
async function fetchCategories() {
  try {
    categories.value = await getCategories()  // 应为数组
    loaded.value = true
  } catch (e) {
    console.error('Failed to fetch categories:', e)
  }
}
```

**步骤 4：检查 SettingsPage 调用**

文件：`frontend/src/pages/SettingsPage.vue`

```javascript
async function loadCategories() {
  try {
    categories.value = await categoriesStore.fetchCategories() || []
  } catch (e) {
    console.error('Load categories error:', e)
  }
}
```

注意：`fetchCategories()` 没有显式返回值（返回 `undefined`），但 `categories.value` 在 Store 内部已被赋值。`SettingsPage` 的 `categories` 是本地 ref，与 Store 的 `categories` 是不同引用。

**修复方案**

根据排查结果，修复数据断点。最可能的问题是 SettingsPage 的 `categories` 本地 ref 未正确从 Store 获取数据。

**代码变更**

文件：`frontend/src/pages/SettingsPage.vue`

```javascript
// 修改前
async function loadCategories() {
  try {
    categories.value = await categoriesStore.fetchCategories() || []
  } catch (e) {
    console.error('Load categories error:', e)
  }
}

// 修改后：直接使用 Store 的 categories（响应式引用）
const categories = categoriesStore.categories

// 或者修改 loadCategories 为：
async function loadCategories() {
  try {
    await categoriesStore.fetchCategories()
    categories.value = categoriesStore.categories
  } catch (e) {
    console.error('Load categories error:', e)
  }
}
```

**影响范围**

- 修改文件取决于排查结果，可能涉及 `SettingsPage.vue`、`useCategoriesStore.js`
- 后端可能无需修改

**测试要点**

1. 设置页分类管理正常显示所有分类（预设 + 自定义）
2. 分类显示图标、名称、预设标签
3. 编辑和删除按钮正常显示
4. 新增分类后列表立即更新

---

### 模块 14：预算页支持编辑（功能 1）

**问题定位**

- 文件：`frontend/src/pages/BudgetPage.vue`
- 现状：
  - `budgets` 为硬编码静态数组（第 106-111 行）
  - `saveBudget()` 为空函数（第 125-133 行），未调用后端 API
  - 已有后端 API：`GET /api/budgets`、`POST /api/budgets`（upsert）、`PUT /api/budgets/{id}`、`POST /api/budgets/batch`
  - 已有前端 API：`getBudgets()`、`batchSetBudgets()`、`updateBudget()`、`deleteBudget()`

**修复方案**

重写 `BudgetPage.vue` 的数据加载和保存逻辑：
1. 从后端 API 加载预算数据（`GET /api/budgets`）
2. 从后端 API 加载已消费金额（通过预算接口返回的 `spent` 字段）
3. 实现编辑功能：点击预算项可修改金额
4. 总预算为各分类预算之和（自动计算，不可直接编辑）
5. 保存后数据持久化到后端

**代码变更**

文件：`frontend/src/pages/BudgetPage.vue`

**脚本重写**：

```javascript
import { ref, computed, onMounted } from 'vue'
import { getBudgets, batchSetBudgets } from '@/api/budgets'
import { getCategories } from '@/api/categories'
import { formatAmount } from '@/utils/format'
import { useAppStore } from '@/stores/useAppStore'
import dayjs from 'dayjs'

const appStore = useAppStore()
const showAddDialog = ref(false)
const saving = ref(false)
const categories = ref([])
const budgets = ref([])
const currentMonth = dayjs().format('YYYY-MM')

const budgetForm = ref({
  category_id: null,
  amount: 0,
})

const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
const budgetUsagePercent = computed(() => {
  if (totalBudget.value === 0) return 0
  return (totalSpent.value / totalBudget.value) * 100
})

async function loadBudgets() {
  try {
    const data = await getBudgets({ month: currentMonth })
    budgets.value = data || []
  } catch (e) {
    console.error('Load budgets error:', e)
  }
}

async function saveBudget() {
  if (!budgetForm.value.category_id || budgetForm.value.amount <= 0) return
  saving.value = true
  try {
    await batchSetBudgets({
      month: currentMonth,
      budgets: [{
        category_id: budgetForm.value.category_id,
        amount: budgetForm.value.amount,
      }],
    })
    appStore.showToast('预算设置成功')
    showAddDialog.value = false
    budgetForm.value = { category_id: null, amount: 0 }
    await loadBudgets()
  } catch (e) {
    appStore.showToast(e.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 编辑已有预算
const editingBudget = ref(null)
const editAmount = ref(0)

function startEdit(item) {
  editingBudget.value = item.category_id
  editAmount.value = item.amount
}

async function saveEdit(item) {
  if (editAmount.value <= 0) return
  try {
    await batchSetBudgets({
      month: currentMonth,
      budgets: [{
        category_id: item.category_id,
        amount: editAmount.value,
      }],
    })
    appStore.showToast('预算已更新')
    editingBudget.value = null
    await loadBudgets()
  } catch (e) {
    appStore.showToast(e.message || '更新失败', 'error')
  }
}

function cancelEdit() {
  editingBudget.value = null
}

onMounted(async () => {
  try {
    categories.value = await getCategories()
    await loadBudgets()
  } catch (e) {
    console.error('Budget page load error:', e)
  }
})
```

**模板修改**：

```html
<!-- 总预算卡片：显示实际总预算 -->
<v-card class="budget-overview-card mb-4">
  <div class="overview-content text-center pa-5">
    <div class="budget-label mb-1">本月预算</div>
    <div class="budget-amount mb-2">
      <span class="amount-number">¥{{ formatAmount(totalBudget) }}</span>
    </div>
    <v-progress-linear
      :model-value="budgetUsagePercent"
      :color="budgetUsagePercent > 80 ? 'error' : budgetUsagePercent > 50 ? 'warning' : 'success'"
      height="8"
      rounded
      class="mb-2"
    />
    <div class="budget-usage d-flex justify-space-between text-body-2">
      <span>已用 {{ formatAmount(totalSpent) }}</span>
      <span>{{ budgetUsagePercent.toFixed(0) }}%</span>
    </div>
  </div>
</v-card>

<!-- 分类预算列表：支持点击编辑 -->
<v-card class="pa-4 mb-3">
  <div class="d-flex justify-space-between align-center mb-3">
    <span class="text-subtitle-2 font-weight-bold">分类预算</span>
    <v-btn size="small" color="primary" variant="tonal" @click="showAddDialog = true">
      <v-icon start size="small">mdi-plus</v-icon>
      设置
    </v-btn>
  </div>

  <div v-if="budgets.length === 0" class="text-center pa-6 text-grey text-caption">
    暂无预算设置，点击上方按钮添加分类预算
  </div>

  <div v-for="item in budgets" :key="item.category_id" class="budget-item mb-3">
    <div class="d-flex justify-space-between align-center mb-1">
      <div class="d-flex align-center">
        <v-avatar size="32" color="rgba(var(--v-theme-primary), 0.1)" class="mr-2">
          <v-icon size="small" color="primary">{{ item.icon || 'mdi-cash' }}</v-icon>
        </v-avatar>
        <span class="text-body-2 font-weight-medium">{{ item.category_name }}</span>
      </div>
      <div class="d-flex align-center">
        <!-- 编辑模式 -->
        <template v-if="editingBudget === item.category_id">
          <v-text-field
            v-model.number="editAmount"
            type="number"
            density="compact"
            hide-details
            variant="outlined"
            style="max-width: 100px;"
            class="mr-1"
            @keydown.enter="saveEdit(item)"
            @keydown.escape="cancelEdit"
          />
          <v-btn icon variant="text" size="x-small" @click="saveEdit(item)">
            <v-icon size="small" color="success">mdi-check</v-icon>
          </v-btn>
          <v-btn icon variant="text" size="x-small" @click="cancelEdit">
            <v-icon size="small" color="grey">mdi-close</v-icon>
          </v-btn>
        </template>
        <!-- 显示模式 -->
        <template v-else>
          <span class="text-body-2 mr-2">
            <span class="font-weight-bold">{{ formatAmount(item.spent) }}</span>
            <span class="text-grey"> / {{ formatAmount(item.amount) }}</span>
          </span>
          <v-btn icon variant="text" size="x-small" @click="startEdit(item)">
            <v-icon size="small" color="grey">mdi-pencil</v-icon>
          </v-btn>
        </template>
      </div>
    </div>
    <v-progress-linear
      :model-value="item.amount > 0 ? (item.spent / item.amount) * 100 : 0"
      :color="(item.spent / item.amount) > 0.8 ? 'error' : (item.spent / item.amount) > 0.5 ? 'warning' : 'primary'"
      height="6"
      rounded
    />
  </div>
</v-card>
```

**影响范围**

- 仅修改 `BudgetPage.vue`
- 后端 API 已就绪，无需修改

**测试要点**

1. 预算页从后端加载数据，不再显示硬编码数据
2. 总预算金额为各分类预算之和
3. 点击编辑图标，出现金额输入框
4. 修改金额后按回车或点击确认，数据持久化
5. 按 Escape 或点击取消，取消编辑
6. 新增分类预算：点击"设置"按钮，选择分类并输入金额
7. 已消费金额正确显示（来自后端计算）
8. 进度条颜色随使用百分比变化

---

## 三、模块依赖关系

```
模块 1  (竖屏侧边栏)        ─── 独立
模块 2  (快速记账时间)        ─── 独立
模块 3  (月份切换)           ─── 独立
模块 4  (快速记账标签名)      ─── 独立（与模块 2 同文件，函数不同，无冲突）
模块 5  (标签删除确认)        ─── 独立
模块 6  (预设分类删除)        ─── 依赖模块 10（所有权校验）
模块 7  (登录边栏刷新)        ─── 独立
模块 8  (深色模式滚动条)      ─── 独立
模块 9  (深色模式文字)        ─── 独立（与模块 8 同文件，可合并修改）
模块 10 (数据隔离校验)        ─── 独立
模块 11 (统计页柱状图)        ─── 独立
模块 12 (支出/收入按钮)       ─── 独立
模块 13 (设置页分类列表)      ─── 独立
模块 14 (预算页编辑)          ─── 独立
```

建议开发顺序：
1. 优先 P0：模块 2、5、10、7、13、14
2. 次之 P1：模块 11、6、12、9、8、1
3. 最后 P2：模块 3、4

---

## 四、修改文件清单

| 文件 | 涉及模块 |
|------|----------|
| `frontend/src/components/layout/AppLayout.vue` | 模块 1、模块 7 |
| `frontend/src/pages/RecordFormPage.vue` | 模块 2、模块 4、模块 12 |
| `frontend/src/pages/RecordListPage.vue` | 模块 3 |
| `frontend/src/pages/SettingsPage.vue` | 模块 5、模块 6、模块 13 |
| `frontend/src/pages/LoginPage.vue` | 模块 7 |
| `frontend/src/styles/global.scss` | 模块 8、模块 9 |
| `frontend/src/pages/StatisticsPage.vue` | 模块 11 |
| `frontend/src/pages/BudgetPage.vue` | 模块 14 |
| `frontend/src/stores/useCategoriesStore.js` | 模块 13 |
| `backend/app/services/record_service.py` | 模块 10 |
| `backend/app/services/category_service.py` | 模块 6、模块 10 |
| `backend/app/services/tag_service.py` | 模块 10 |
| `backend/app/services/statistics_service.py` | 模块 11 |
| `backend/app/routers/records.py` | 模块 10 |
| `backend/app/routers/categories.py` | 模块 6、模块 10 |
| `backend/app/routers/tags.py` | 模块 10 |
| `backend/app/utils/response.py` | 模块 10（新增错误码） |

---

## 五、风险与注意事项

1. **模块 6 级联删除**：删除分类会同时删除关联账单和预算，此操作不可逆。需确保确认对话框信息清晰。
2. **模块 6 + 10 事务完整性**：级联删除时需确保分类、账单、预算在同一事务中删除，避免部分删除。
3. **模块 10 权限码**：需确认 `response.py` 中 `Code.FORBIDDEN` 的值不与现有错误码冲突。
4. **模块 11 图表兼容**：`chart.js` 已包含 `BarElement` 和 `BarController`，无需额外安装。
5. **模块 14 预算 API**：后端已有完整的预算 CRUD 接口，前端 `budgets.js` 也已封装好，只需重写页面逻辑。
6. **模块 1 竖屏宽度**：56px 较窄，需确保图标不被裁切，触摸区域足够。
7. **模块 13 排查优先**：此为 P0 Bug，需先排查数据断点再修复，不能盲目改代码。建议先用浏览器 DevTools 检查网络请求返回值。
8. **模块 12 按钮布局**：移除 `block` 后需验证在不同屏幕尺寸下按钮仍等宽，Vuetify 的 `flex-grow-1` 类可保证等分。

---

*文档结束*
