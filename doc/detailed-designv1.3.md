# Money App v1.3 详细设计文档

> 基于 `proposalv1.3.md` 需求文档，按模块拆分的详细技术设计

---

## 技术栈约束

| 项目 | 版本 | 备注 |
|------|------|------|
| Vue | 3.5.34 | Composition API + `<script setup>` |
| Vuetify | 3.12.6 | Material Design 组件库 |
| Vite | 8 | 构建工具 |
| Pinia | 3 | 状态管理 |
| dayjs | - | 日期处理 |
| Chart.js / vue-chartjs | - | 图表 |

**项目语言：** 纯 JavaScript（非 TypeScript），所有文件后缀为 `.js` / `.vue`。

---

## 模块总览

| # | 模块 | 优先级 | 复杂度 | 涉及文件 |
|---|------|--------|--------|----------|
| 1 | 记账页返回时未保存提醒 | 高 | 低 | `RecordFormPage.vue` |
| 2 | 日历组件风格升级与动画 | 中 | 中 | `RecordFormPage.vue`, `RecordListPage.vue`, 新增 `ExpandTransition.vue` |
| 3 | 账单详情展开动画 | 中 | 中 | `RecordListPage.vue`, `RecordDetailPage.vue`, `router/index.js`, 新增 `ExpandTransition.vue` |
| 4 | 分类图标替代收支图标 | 低 | 低 | `RecordListPage.vue` |
| 5 | 页面滑动模糊渐变 | 中 | 中 | `AppLayout.vue`, `global.scss`, 各页面滚动容器 |
| 6 | 宽屏适配 110% 放大 | 低 | 低 | `AppLayout.vue`, `global.scss` |

**建议开发顺序：** 1 → 4 → 6 → 2 → 3 → 5

---

## 模块 1：记账页返回时未保存提醒

### 1.1 需求摘要

用户在记账页（RecordFormPage）修改过字段后，点击返回时弹出确认对话框，提示"你确定要放弃更改吗？"。未修改时直接退出。

### 1.2 现状分析

- `RecordFormPage.vue` 使用 `<script setup>`，通过 `useRouter()` 和 `useRoute()` 管理路由
- 页面返回按钮调用 `router.back()`
- 表单字段：`recordType`, `amount`, `categoryId`, `consumeDate`, `consumeTime`, `selectedTagId`, `note`
- 编辑模式（`/edit/:id`）在 `onMounted` 中加载已有记录数据
- 已有 `ConfirmDialog.vue` 组件可复用（v-dialog + persistent 模式）

### 1.3 设计方案

#### 1.3.1 变更追踪机制

**新增 ref：**
```js
const isDirty = ref(false)       // 表单是否被修改过
const showLeaveDialog = ref(false) // 离开确认弹窗
const pendingNavigation = ref(null) // 待执行的导航回调
```

**初始快照（用于对比）：**

在 `onMounted` 加载完成后，保存一份初始状态快照：
```js
let initialSnapshot = null

function takeSnapshot() {
  return JSON.stringify({
    recordType: recordType.value,
    amount: amount.value,
    categoryId: categoryId.value,
    consumeDate: consumeDate.value,
    consumeTime: consumeTime.value,
    selectedTagId: selectedTagId.value,
    note: note.value,
  })
}
```

**变更检测：**

使用 `watch` 监听所有表单字段的深层变化，与快照对比：
```js
watch(
  [recordType, amount, categoryId, consumeDate, consumeTime, selectedTagId, note],
  () => {
    if (initialSnapshot === null) return
    isDirty.value = takeSnapshot() !== initialSnapshot
  },
  { deep: true }
)
```

> **注意：** 不能仅靠 `isDirty` 初始为 `false` 然后任何变化设为 `true` 的方式，因为编辑模式下用户可能改回原始值，此时应视为"未修改"。

#### 1.3.2 拦截返回操作

**方案：使用 Vue Router 的 `onBeforeRouteLeave` 组合式 API**

```js
import { onBeforeRouteLeave } from 'vue-router'

onBeforeRouteLeave((to, from, next) => {
  if (isDirty.value) {
    showLeaveDialog.value = true
    pendingNavigation.value = next
    return false // 阻止导航
  }
  next()
})
```

**拦截页面内的返回按钮：**

修改现有的 `@click="router.back()"` 为自定义方法：
```js
function handleBack() {
  if (isDirty.value) {
    showLeaveDialog.value = true
    pendingNavigation.value = () => router.back()
  } else {
    router.back()
  }
}
```

#### 1.3.3 确认弹窗

复用现有 `ConfirmDialog.vue` 组件：

```html
<ConfirmDialog
  v-model="showLeaveDialog"
  title="未保存的更改"
  message="你确定要放弃更改吗？"
  confirm-text="确定放弃"
  confirm-color="error"
  @confirm="confirmLeave"
  @cancel="cancelLeave"
/>
```

**处理函数：**
```js
function confirmLeave() {
  isDirty.value = false // 防止再次触发拦截
  showLeaveDialog.value = false
  if (pendingNavigation.value) {
    pendingNavigation.value()
    pendingNavigation.value = null
  }
}

function cancelLeave() {
  showLeaveDialog.value = false
  pendingNavigation.value = null
}
```

#### 1.3.4 浏览器物理返回键兼容

Vue Router 的 `onBeforeRouteLeave` 已经能拦截 hash 路由下的浏览器后退按钮（触发 `popstate` 事件后 Vue Router 会执行导航守卫）。无需额外的 `beforeunload` 或 `popstate` 监听。

#### 1.3.5 提交成功后清除脏状态

在 `submit()` 函数的 `router.push('/')` 之前，设置 `isDirty.value = false`，防止提交成功后的路由跳转触发弹窗。

#### 1.3.6 涉及文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/pages/RecordFormPage.vue` | 修改 | 新增脏状态检测、路由守卫、确认弹窗 |

### 1.4 验收标准映射

| 验收标准 | 实现方式 |
|----------|----------|
| 未修改时返回直接退出 | `isDirty` 为 `false`，`onBeforeRouteLeave` 直接 `next()` |
| 修改后返回弹出确认弹窗 | `isDirty` 为 `true` 时拦截导航，显示 `ConfirmDialog` |
| 弹窗包含"取消"和"确定放弃" | 复用 `ConfirmDialog`，配置 `confirm-text="确定放弃"` |
| 取消留当前页，确定放弃退出 | `cancel` 恢复，`confirm` 执行 `pendingNavigation` |
| 兼容浏览器物理返回键 | `onBeforeRouteLeave` 自动拦截 popstate 触发的导航 |

### 1.5 独立测试方案

- 手动测试：进入记账页 → 不做修改 → 点返回 → 应直接退出
- 手动测试：进入记账页 → 修改金额 → 点返回 → 应弹出确认框
- 手动测试：确认框点"取消" → 留在页面
- 手动测试：确认框点"确定放弃" → 退出页面
- 手动测试：编辑模式 → 改回原始值 → 点返回 → 应直接退出（快照对比）
- 手动测试：编辑模式 → 修改后点保存 → 应正常提交不弹框
- 手动测试：移动端浏览器物理返回键 → 同样触发确认框

---

## 模块 2：日历组件风格升级与动画

### 2.1 需求摘要

日历弹出组件视觉风格与 Material Design 一致，打开时从点击位置以 expand 动画展开至画面中心。

### 2.2 现状分析

- `RecordFormPage.vue`：消费时间使用 `<v-text-field type="date">` 和 `<v-text-field type="time">`，浏览器原生日期选择器
- `RecordListPage.vue`：筛选栏使用 `<v-text-field type="date">`，同样为浏览器原生
- 项目中无自定义日历组件
- Vuetify 3 提供 `v-date-picker` 组件，但其弹出容器（`v-menu` / `v-dialog`）不支持从点击坐标展开的动画

### 2.3 设计方案

#### 2.3.1 新增公共组件：`ExpandTransition.vue`

**路径：** `frontend/src/components/common/ExpandTransition.vue`

**职责：** 提供从指定坐标以 expand 动画展开/收起的过渡效果。可被日历组件、详情页等复用。

**Props：**
```js
{
  modelValue: Boolean,        // 控制显示/隐藏
  origin: { x: Number, y: Number }, // 动画起始坐标（相对于视口）
  duration: { type: Number, default: 250 }, // 动画时长 ms
}
```

**实现原理：**
1. 使用 `v-dialog` 作为容器（提供遮罩层和居中定位）
2. 自定义 Vue transition 函数，在 `onBeforeEnter` 钩子中根据 `origin` 计算 `transform-origin`
3. 动画使用 CSS `transform: scale()` + `opacity`，从 `scale(0)` 到 `scale(1)`
4. `transform-origin` 计算逻辑：将点击坐标转换为相对于对话框中心的百分比偏移

**关键 CSS：**
```css
.expand-enter-active,
.expand-leave-active {
  transition: transform var(--duration) ease, opacity var(--duration) ease;
}
.expand-enter-from {
  transform: scale(0);
  opacity: 0;
}
.expand-leave-to {
  transform: scale(0);
  opacity: 0;
}
```

**transform-origin 计算：**
```js
function calcOrigin(dialogEl, clickX, clickY) {
  const rect = dialogEl.getBoundingClientRect()
  const x = ((clickX - rect.left) / rect.width) * 100
  const y = ((clickY - rect.top) / rect.height) * 100
  return `${x}% ${y}%`
}
```

#### 2.3.2 新增日历弹出组件：`DatePickerPopover.vue`

**路径：** `frontend/src/components/common/DatePickerPopover.vue`

**职责：** 封装 Vuetify `v-date-picker`，配合 `ExpandTransition` 提供带动画的日历选择。

**Props：**
```js
{
  modelValue: String,          // 日期值 (YYYY-MM-DD)
  modelValueTime: String,      // 时间值 (HH:mm)，可选
  showTime: Boolean,           // 是否显示时间选择
}
```

**Events：**
```js
'update:modelValue'   // 日期变更
'update:modelValueTime' // 时间变更
```

**实现：**
1. 使用 `v-menu` 作为触发容器，`activator` 绑定到触发元素
2. 菜单内容使用 `ExpandTransition` 包裹 `v-date-picker`
3. 点击触发元素时，通过事件对象获取 `(clientX, clientY)` 传给 `ExpandTransition`
4. 可选附带 `v-text-field type="time"` 用于时间选择

#### 2.3.3 修改 `RecordFormPage.vue`

**替换现有日期/时间输入：**

将：
```html
<v-text-field v-model="consumeDate" type="date" ... />
<v-text-field v-model="consumeTime" type="time" ... />
```

替换为：
```html
<DatePickerPopover
  v-model="consumeDate"
  v-model:time="consumeTime"
  show-time
>
  <template #activator="{ on }">
    <v-text-field
      :model-value="consumeDate"
      readonly
      @click="on.click"
      ...
    />
  </template>
</DatePickerPopover>
```

#### 2.3.4 修改 `RecordListPage.vue`

**替换筛选栏日期输入：**

将两个 `<v-text-field type="date">` 替换为 `DatePickerPopover`，不显示时间选择。

#### 2.3.5 涉及文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/components/common/ExpandTransition.vue` | **新增** | 通用 expand 动画过渡组件 |
| `frontend/src/components/common/DatePickerPopover.vue` | **新增** | 日历弹出组件（封装 v-date-picker + ExpandTransition） |
| `frontend/src/pages/RecordFormPage.vue` | 修改 | 替换日期/时间为 DatePickerPopover |
| `frontend/src/pages/RecordListPage.vue` | 修改 | 替换筛选日期为 DatePickerPopover |

### 2.4 验收标准映射

| 验收标准 | 实现方式 |
|----------|----------|
| 日历风格与 Material Design 一致 | 使用 Vuetify `v-date-picker` 组件 |
| 从点击位置 expand 动画展开至中心 | `ExpandTransition` 根据 click 坐标计算 `transform-origin` |
| 记账页和账单页均呈现新风格 | 两处均替换为 `DatePickerPopover` |
| 动画时长 200-300ms，不卡顿 | 默认 250ms，CSS `ease` 缓动 |

### 2.5 独立测试方案

- 手动测试：记账页点击日期字段 → 日历从点击位置展开
- 手动测试：账单页点击开始/结束日期 → 同样的展开动画
- 手动测试：选择日期后日历收起，字段值正确更新
- 性能测试：动画帧率 ≥ 60fps（Chrome DevTools Performance 面板）

---

## 模块 3：账单详情展开动画

### 3.1 需求摘要

点击账单条目后，从该条目位置以 expand 动画逐渐扩大至完整的详情页画面，与日历动画风格一致。

### 3.2 现状分析

- `RecordListPage.vue` 中点击条目调用 `router.push(/detail/${id})`
- `AppLayout.vue` 中 `<router-view>` 包裹在 `<transition name="page" mode="out-in">` 中
- 当前页面过渡为 fade + translateY，所有页面共用同一个过渡效果
- `RecordDetailPage.vue` 是独立路由页面，非弹窗/覆盖层

### 3.3 设计方案

#### 3.3.1 方案概述

使用 **Vue Router 路由 meta + 动态 transition** 实现：当从账单列表跳转到详情页时，使用自定义的 expand 过渡替代默认的 `page` 过渡。

#### 3.3.2 传递点击坐标

在 `RecordListPage.vue` 的 `goToDetail` 方法中，通过路由 meta 传递点击坐标：

```js
function goToDetail(event, id) {
  const rect = event.currentTarget.getBoundingClientRect()
  const origin = {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  }
  router.push({
    path: `/detail/${id}`,
    meta: { transitionOrigin: origin },
  })
}
```

> **注意：** Vue Router 的 `meta` 是路由配置级别的，不能通过 `router.push` 动态设置。需要使用其他方式传递坐标。

**修正方案：使用全局状态或 sessionStorage 传递坐标**

在 `useAppStore.js` 中新增：
```js
// 在 useAppStore 中
const transitionOrigin = ref(null)
function setTransitionOrigin(origin) {
  transitionOrigin.value = origin
}
```

`RecordListPage.vue` 中：
```js
function goToDetail(event, id) {
  const rect = event.currentTarget.getBoundingClientRect()
  appStore.setTransitionOrigin({
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  })
  router.push(`/detail/${id}`)
}
```

#### 3.3.3 自定义路由过渡

修改 `AppLayout.vue` 中的 `<router-view>` 过渡逻辑：

```html
<router-view v-slot="{ Component, route }">
  <transition
    :name="getTransitionName(route)"
    :css="true"
    @before-enter="onBeforeEnter"
    @enter="onEnter"
    @leave="onLeave"
    mode="out-in"
  >
    <component :is="Component" />
  </transition>
</router-view>
```

**过渡名称选择逻辑：**
```js
function getTransitionName(route) {
  if (route.path.startsWith('/detail/') && appStore.transitionOrigin) {
    return 'expand'
  }
  return 'page'
}
```

**JavaScript 钩子（处理动态 transform-origin）：**
```js
function onBeforeEnter(el) {
  if (appStore.transitionOrigin) {
    const origin = appStore.transitionOrigin
    el.style.transformOrigin = `${origin.x}px ${origin.y}px`
    el.style.transform = 'scale(0)'
    el.style.opacity = '0'
  }
}

function onEnter(el, done) {
  if (appStore.transitionOrigin) {
    el.offsetHeight // 强制 reflow
    el.style.transition = 'transform 0.3s ease, opacity 0.3s ease'
    el.style.transform = 'scale(1)'
    el.style.opacity = '1'
    el.addEventListener('transitionend', done, { once: true })
  } else {
    done()
  }
}

function onLeave(el, done) {
  if (appStore.transitionOrigin) {
    el.style.transition = 'transform 0.2s ease, opacity 0.2s ease'
    el.style.transform = 'scale(0.9)'
    el.style.opacity = '0'
    el.addEventListener('transitionend', () => {
      appStore.transitionOrigin = null
      done()
    }, { once: true })
  } else {
    done()
  }
}
```

#### 3.3.4 详情页返回动画

当从详情页返回列表页时，应执行反向动画（从全屏缩回条目位置）。

在 `RecordDetailPage.vue` 的返回按钮中：
```js
function handleBack() {
  // 返回时不做 expand 动画，使用默认 page 过渡
  appStore.setTransitionOrigin(null)
  router.back()
}
```

> **简化设计：** 返回时使用默认的 `page` 过渡（fade + slide），不做反向 expand。原因是返回时原始条目可能已不在视口中（用户滚动过），反向动画的位置计算不可靠。

#### 3.3.5 涉及文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/stores/useAppStore.js` | 修改 | 新增 `transitionOrigin` 状态 |
| `frontend/src/components/layout/AppLayout.vue` | 修改 | 自定义路由过渡逻辑，支持 expand 动画 |
| `frontend/src/pages/RecordListPage.vue` | 修改 | `goToDetail` 传递点击坐标 |
| `frontend/src/pages/RecordDetailPage.vue` | 修改 | 返回时清除 `transitionOrigin` |
| `frontend/src/styles/global.scss` | 修改 | 新增 `expand` 过渡 CSS 类（备用） |

### 3.4 验收标准映射

| 验收标准 | 实现方式 |
|----------|----------|
| 动画起始位置为被点击的条目 | `getBoundingClientRect()` 获取条目中心坐标 |
| 展开至完整详情页画面 | CSS `scale(0)` → `scale(1)` + `opacity` |
| 动画风格与日历动画一致 | 同为 expand 效果，相同时长和缓动函数 |
| 建议使用 Vue Router 过渡 | 使用 `<transition>` + JavaScript 钩子 |

### 3.5 独立测试方案

- 手动测试：账单列表点击条目 → 从条目位置展开至详情页
- 手动测试：详情页点返回 → 使用默认过渡回到列表
- 手动测试：直接访问 `/detail/:id`（非从列表跳转）→ 使用默认 page 过渡
- 手动测试：动画流畅无卡顿

---

## 模块 4：分类图标替代收支图标

### 4.1 需求摘要

账单列表中每条记录的前端图标从统一的收入/支出箭头图标，改为显示该记录所属分类的图标。

### 4.2 现状分析

`RecordListPage.vue` 第 124-133 行，账单条目的 `v-slot:prepend` 区域：

```html
<v-avatar :color="record.type === 'expense' ? '#FFE8E8' : '#E8FFF3'" size="40" class="mr-2">
  <v-icon :color="record.type === 'expense' ? '#FF6B6B' : '#20C997'" size="18">
    {{ record.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
  </v-icon>
</v-avatar>
```

当前显示：统一的 `mdi-arrow-down`（支出）/ `mdi-arrow-up`（收入）图标。

同时，第 136-138 行的 `v-list-item-title` 中已经有一个分类图标：
```html
<v-avatar size="24" color="rgba(139, 126, 116, 0.12)" class="mr-1">
  <v-icon size="14" color="#8B7E74">{{ record.category_icon || 'mdi-circle' }}</v-icon>
</v-avatar>
```

**数据源确认：** API 返回的 `record` 对象包含 `category_icon` 字段（MDI 图标字符串），已在使用中。

### 4.3 设计方案

#### 4.3.1 替换 prepend 区域图标

将 `v-slot:prepend` 中的收入/支出箭头图标替换为分类图标：

```html
<template v-slot:prepend>
  <v-avatar
    :color="record.type === 'expense' ? '#FFE8E8' : '#E8FFF3'"
    size="40"
    class="mr-2"
  >
    <v-icon
      :color="record.type === 'expense' ? '#FF6B6B' : '#20C997'"
      size="20"
    >
      {{ record.category_icon || 'mdi-circle' }}
    </v-icon>
  </v-avatar>
</template>
```

**变更点：**
- 图标从 `mdi-arrow-down` / `mdi-arrow-up` 改为 `record.category_icon`
- 图标 size 从 18 调整为 20（分类图标通常比箭头需要更大显示面积）
- 背景色保持不变（`#FFE8E8` / `#E8FFF3`），仍通过颜色区分收支类型

#### 4.3.2 移除重复的小分类图标

由于 prepend 区域已显示分类图标，`v-list-item-title` 中的小号分类图标变为冗余。移除第 136-138 行：

```html
<!-- 移除此段 -->
<v-avatar size="24" color="rgba(139, 126, 116, 0.12)" class="mr-1">
  <v-icon size="14" color="#8B7E74">{{ record.category_icon || 'mdi-circle' }}</v-icon>
</v-avatar>
```

保留文字部分：`{{ record.tag?.name || record.category_name || '未分类' }}`

#### 4.3.3 涉及文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/pages/RecordListPage.vue` | 修改 | prepend 图标改为分类图标，移除重复小图标 |

### 4.4 验收标准映射

| 验收标准 | 实现方式 |
|----------|----------|
| 前端显示分类图标 | `record.category_icon` 替代箭头图标 |
| 图标来自用户设置的分类数据 | 数据源为 API 返回的 `category_icon` 字段 |
| 收支区分不再依赖图标 | 背景色（红/绿）和金额颜色（红/绿）仍区分收支 |

### 4.5 独立测试方案

- 手动测试：账单列表中各条目显示对应分类的图标
- 手动测试：无分类图标时显示 `mdi-circle` 兜底
- 手动测试：收入/支出仍通过背景色和金额正负号区分

---

## 模块 5：页面滑动模糊渐变

### 5.1 需求摘要

垂直滑动时，在固定标题栏下方和页面底部边缘添加模糊渐变效果。

### 5.2 现状分析

- `AppLayout.vue` 中 `.app-top-bar` 为 `position: sticky; top: 0; z-index: 100`
- `.content-wrapper` 为页面内容容器，`max-width: 640px; padding: 24px 20px 100px`
- 页面滚动发生在 `.main-content`（`v-main`）层级
- 各页面无独立滚动容器，统一使用浏览器窗口滚动

### 5.3 设计方案

#### 5.3.1 顶部标题栏下方模糊渐变

**实现位置：** `AppLayout.vue` 的 `.app-top-bar` 下方

**实现方式：** 在 `.app-top-bar` 底部添加一个伪元素 `::after`，使用 CSS `mask-image` 实现从不透明到透明的渐变：

```css
.app-top-bar::after {
  content: '';
  position: absolute;
  bottom: -24px;
  left: 0;
  right: 0;
  height: 24px;
  background: rgb(var(--v-theme-background));
  mask-image: linear-gradient(to bottom, black 0%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%);
  pointer-events: none;
  z-index: 99;
}
```

**效果：** 标题栏下方出现 24px 的渐变遮罩，内容从标题栏下方滑入时逐渐显现，避免硬切。

#### 5.3.2 页面底部模糊渐变

**实现位置：** `AppLayout.vue` 的 `.content-wrapper` 底部

**实现方式：** 使用 CSS `::after` 伪元素，固定在内容区域底部：

```css
.content-wrapper::after {
  content: '';
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: min(100%, 640px);
  height: 40px;
  background: linear-gradient(to bottom, transparent, rgb(var(--v-theme-background)));
  pointer-events: none;
  z-index: 50;
}
```

**效果：** 页面底部出现 40px 的渐变遮罩，提示下方还有内容。当滚动到底部时，渐变自然消失（因为下方无内容可露出）。

#### 5.3.3 响应式适配

- 移动端（<960px）：底部渐变宽度为 100%
- 桌面端（≥960px）：底部渐变宽度跟随 `content-wrapper` 的 `max-width: 640px`
- 渐变颜色跟随主题（light/dark），使用 Vuetify 的 CSS 变量 `--v-theme-background`

#### 5.3.4 涉及文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/components/layout/AppLayout.vue` | 修改 | 添加顶部和底部模糊渐变伪元素 |
| `frontend/src/styles/global.scss` | 修改 | 可选：将渐变样式提取为全局工具类 |

### 5.4 验收标准映射

| 验收标准 | 实现方式 |
|----------|----------|
| 向下滚动时标题下方出现模糊渐变 | `.app-top-bar::after` 渐变遮罩 |
| 页面底部出现模糊渐变 | `.content-wrapper::after` 固定定位渐变 |
| 使用 CSS mask-image 实现 | `mask-image: linear-gradient(...)` |
| 移动端和桌面端均生效 | 响应式宽度适配 |
| 不影响正常滚动和点击 | `pointer-events: none` |

### 5.5 独立测试方案

- 手动测试：主页向下滚动 → 标题栏下方出现模糊过渡
- 手动测试：页面底部可见模糊渐变效果
- 手动测试：切换深色模式 → 渐变颜色跟随主题
- 手动测试：移动端和桌面端均正常显示
- 手动测试：渐变区域不阻挡点击事件

---

## 模块 6：宽屏适配 110% 放大

### 6.1 需求摘要

桌面端（≥960px）使用 CSS `transform: scale(1.1)` 对整体内容放大，视觉等效于 704px。

### 6.2 现状分析

- `AppLayout.vue` 中 `.content-wrapper` 设置 `max-width: 640px`
- 桌面端断点为 960px（`isDesktop` ref）
- 侧边栏宽度 240px，与内容区域独立

### 6.3 设计方案

#### 6.3.1 CSS 放大

在 `AppLayout.vue` 的 scoped style 中添加：

```css
@media (min-width: 960px) {
  .content-wrapper {
    transform: scale(1.1);
    transform-origin: top center;
  }
}
```

#### 6.3.2 防止水平溢出

`transform: scale(1.1)` 会使内容宽度从 640px 变为 704px。需要确保父容器不会出现水平滚动条：

在 `AppLayout.vue` 的 `.main-content` 上添加：
```css
.main-content {
  overflow-x: hidden;
}
```

#### 6.3.3 底部间距补偿

放大后内容高度也会增加 10%，需要补偿底部 padding 以避免 FAB 和底部导航遮挡内容：

```css
@media (min-width: 960px) {
  .content-wrapper {
    transform: scale(1.1);
    transform-origin: top center;
    padding-bottom: calc(100px * 1.1); /* 原 100px × 1.1 */
  }
}
```

#### 6.3.4 涉及文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/components/layout/AppLayout.vue` | 修改 | 添加媒体查询下的 scale 放大和 overflow 控制 |

### 6.4 验收标准映射

| 验收标准 | 实现方式 |
|----------|----------|
| 移动端不受影响 | `@media (min-width: 960px)` 限定范围 |
| 桌面端统一放大 110% | `transform: scale(1.1)` |
| 不出现水平滚动条 | `overflow-x: hidden` |
| 不影响交互功能 | CSS transform 不影响事件坐标 |
| 侧边栏和底部导航不受影响 | scale 仅应用于 `.content-wrapper` |

### 6.5 独立测试方案

- 手动测试：移动端（<960px）→ 内容保持原始比例
- 手动测试：桌面端（≥960px）→ 内容放大 110%
- 手动测试：放大后无水平滚动条
- 手动测试：放大后点击、滚动、输入均正常
- 手动测试：侧边栏展开/折叠不受影响

---

## 公共依赖

以下组件/模块被多个模块依赖，应优先开发：

| 依赖 | 依赖方 | 说明 |
|------|--------|------|
| `ExpandTransition.vue`（新增） | 模块 2、模块 3 | 通用 expand 动画过渡组件 |
| `useAppStore.transitionOrigin`（新增） | 模块 3 | 路由过渡坐标传递 |

---

## 开发顺序与依赖关系

```
模块 1（返回提醒）── 独立，无依赖
模块 4（分类图标）── 独立，无依赖
模块 6（宽屏放大）── 独立，无依赖
模块 2（日历动画）── 依赖 ExpandTransition.vue（新增）
模块 3（详情动画）── 依赖 ExpandTransition.vue（可选）、useAppStore 扩展
模块 5（模糊渐变）── 独立，但建议最后实施（涉及全局样式）
```

---

## 注意事项

1. **所有文件为 `.js` 而非 `.ts`：** 项目为纯 JavaScript，详细设计中所有代码示例均使用 JS 语法。需求文档中提到的 `frontend/src/router/index.ts` 实际为 `frontend/src/router/index.js`。
2. **现有 ConfirmDialog 可复用：** 模块 1 的确认弹窗直接复用 `frontend/src/components/common/ConfirmDialog.vue`，无需新增组件。
3. **颜色未做集中管理：** 当前项目中 `#FF6B6B`（支出）和 `#20C997`（收入）在多处硬编码。本版本不重构此问题，保持现有风格。
4. **浏览器兼容性：** `mask-image` 需要 `-webkit-` 前缀以兼容 Safari。`transform: scale()` 在所有现代浏览器中均支持。
