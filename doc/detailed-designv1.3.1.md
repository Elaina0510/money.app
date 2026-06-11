# Money App v1.3.1 详细设计文档

## 版本信息

| 项目 | 内容 |
|------|------|
| 基线版本 | v1.3 |
| 目标版本 | v1.3.1 |
| 技术栈 | Vue 3 + Vite + Vuetify 3 + Pinia |
| 文档日期 | 2026-06-07 |
| 需求文档 | doc/proposalv1.3.1.md |

---

## 设计原则

1. **模块独立**：每个 REQ 模块可独立开发和测试，不相互依赖
2. **最小侵入**：优先复用现有组件和 store，减少新增文件
3. **Vuetify 原生优先**：尽量使用 Vuetify 3 原生组件和指令，减少自定义样式
4. **主题感知**：所有新增样式必须同时适配深色/浅色模式

---

## 模块总览

| 编号 | 模块 | 涉及文件 | 新增依赖 |
|------|------|----------|----------|
| REQ-001 | 账单详情页展开动画 | AppLayout.vue, RecordListPage.vue, RecordDetailPage.vue, useAppStore.js | 无 |
| REQ-002 | 账单页筛选列表UI优化 | RecordListPage.vue, global.scss | 无 |
| REQ-003 | 全局阴影与层级设计 | global.scss, 各页面 scoped style | 无 |
| REQ-004 | 首页标题栏调整 | DashboardPage.vue | 无 |
| REQ-005 | 图标水波纹涟漪动效 | AppLayout.vue, DashboardPage.vue, RecordListPage.vue, SettingsPage.vue | 无 |
| REQ-006 | 快速记账页日期时间栏布局调整 | DatePickerPopover.vue, RecordFormPage.vue | 无 |
| REQ-007 | 时间选择器UI优化 | DatePickerPopover.vue | 无（v-time-picker 已包含在 vuetify/components 中） |
| REQ-008 | 深色/浅色模式自动切换 | useAppStore.js, AppLayout.vue, SettingsPage.vue | 无 |

---

## REQ-001 账单详情页展开动画

### 概述

修复从账单列表点击进入详情页时的展开动画。动画从点击坐标开始，以 scale 变换扩展至 content area 范围。

### 现状分析

- `RecordListPage.goToDetail()` 已捕获点击坐标并写入 `appStore.transitionOrigin`
- `AppLayout.vue` 已有 expand transition 机制，通过 JS hooks 驱动 `transform: scale` 动画
- `RecordDetailPage.vue` 未参与动画过程——它是被 transition 包裹的目标组件
- **问题根因**：AppLayout 中 expand transition 的 `onEnter` 使用 `transform: scale(0) -> scale(1)` 起始值为 0，导致内容从不可见状态出现而非从点击位置"展开"。且 `onLeave` 动画 `scale(0.9)` 与 enter 不匹配，可能造成视觉断裂

### 设计方案

#### 动画流程

```
用户点击账单条目 (x, y)
  → RecordListPage 设置 transitionOrigin
  → router.push('/detail/:id')
  → AppLayout expand transition 触发
    → onBeforeEnter: 元素 scale(0), opacity(0), transformOrigin = (x, y)
    → onEnter: 250ms ease → scale(1), opacity(1)
    → 页面完全显示
```

#### 修改点

**文件：`AppLayout.vue`**

修改 `onEnter` 钩子，确保：
1. `transformOrigin` 基于 `transitionOrigin` 的视口坐标，映射到 content area 内的相对位置
2. 进入动画：`scale(0.1) → scale(1)`，opacity `0 → 1`，duration 250ms ease
3. 离开动画：`scale(1) → scale(0.95)`，opacity `1 → 0`，duration 200ms ease（反向收束感）

```javascript
// onEnter 伪代码
function onEnter(el, done) {
  const origin = appStore.transitionOrigin
  // 将视口坐标映射到 el 的相对坐标
  const rect = el.getBoundingClientRect()
  const x = ((origin.x - rect.left) / rect.width) * 100
  const y = ((origin.y - rect.top) / rect.height) * 100

  el.style.transformOrigin = `${x}% ${y}%`
  el.style.transform = 'scale(0.1)'
  el.style.opacity = '0'
  el.style.transition = 'none'

  requestAnimationFrame(() => {
    el.style.transition = 'transform 250ms cubic-bezier(0.4, 0, 0.2, 1), opacity 250ms ease'
    el.style.transform = 'scale(1)'
    el.style.opacity = '1'
    el.addEventListener('transitionend', done, { once: true })
  })
}
```

**文件：`RecordListPage.vue`**

`goToDetail()` 方法无需修改——已正确捕获坐标并写入 store。

**文件：`RecordDetailPage.vue`**

`handleBack()` 方法中清除 `transitionOrigin` 的逻辑保持不变。

**文件：`useAppStore.js`**

无需修改——`transitionOrigin` 的 getter/setter 已满足需求。

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 动画从点击位置开始 | 在列表不同位置点击，观察动画起始点是否跟随 |
| 过渡自然无闪烁 | 快速连续点击不同条目，观察是否有残影或闪烁 |
| 多设备尺寸一致 | 在 375px / 768px / 1440px 宽度下测试动画表现 |
| 返回动画反向 | 从详情页返回时，动画应有反向收束效果 |

---

## REQ-002 账单页筛选列表UI优化

### 概述

美化账单页筛选栏的样式，使其符合 Material You 设计风格，交互形式保持不变。

### 现状分析

- 筛选栏使用 `<v-card rounded="xl">` 包裹，内含两个 `DatePickerPopover` 和两个 `v-select`
- `v-select` 使用 Vuetify 全局默认配置：`variant: 'outlined'`, `density: 'compact'`
- 样式较为朴素，缺乏 Material You 的层次感和圆润感

### 设计方案

#### 修改点

**文件：`RecordListPage.vue`**

1. **筛选栏卡片样式增强**：
   - 添加 `variant="flat"` 或 `elevation="0"`，配合全局阴影系统（REQ-003）统一管理
   - 添加内部 padding `pa-4`
   - 筛选项之间使用 `v-divider` 或 `ga-3` gap 分隔

2. **v-select 样式微调**：
   - 将 `variant="outlined"` 改为 `variant="solo-filled"` 或保持 `outlined` 但调整 `bg-color="surface"`
   - 确保 `rounded="lg"` 与整体风格一致
   - 添加 `prepend-inner-icon` 增强可识别性（如类型用 `mdi-swap-vertical`，分类用 `mdi-shape-outline`）

3. **筛选栏布局优化**：
   - 使用 `v-row` + `v-col` 实现响应式排列
   - 日期筛选和类型/分类筛选分两行
   - 移动端：每行 2 个筛选项；桌面端：一行 4 个

```html
<!-- 目标结构示意 -->
<v-card rounded="xl" class="filter-card pa-4">
  <v-row dense>
    <v-col cols="6" sm="3">
      <DatePickerPopover ... />
    </v-col>
    <v-col cols="6" sm="3">
      <DatePickerPopover ... />
    </v-col>
    <v-col cols="6" sm="3">
      <v-select
        v-model="recordsStore.filters.type"
        :items="typeOptions"
        item-title="text"
        item-value="value"
        label="类型"
        prepend-inner-icon="mdi-swap-vertical"
        variant="outlined"
        density="compact"
        rounded="lg"
        bg-color="surface"
      />
    </v-col>
    <v-col cols="6" sm="3">
      <v-select ... />
    </v-col>
  </v-row>
</v-card>
```

**文件：`global.scss`**

无需修改——筛选组件使用 Vuetify 原生样式，通过 props 控制外观。

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 样式符合 Material You | 视觉审查：圆角、间距、颜色与整体一致 |
| 深色/浅色模式适配 | 切换主题后筛选栏样式正常 |
| 筛选功能不变 | 使用各筛选组合验证数据过滤正确 |
| 响应式布局 | 375px / 768px / 1440px 下布局正确 |

---

## REQ-003 全局阴影与层级设计

### 概述

为全应用元素建立 Material You Z 轴阴影层级体系，增强视觉层次感。

### 现状分析

- `global.scss` 中 `.v-card:hover` 使用 `box-shadow: 0 2px 8px rgba(0,0,0,0.06)`
- 各页面卡片无静态阴影，仅 hover 时出现
- 深色模式下 `.v-theme--dark .v-card` 仅设置了 border-color，无阴影处理
- 按钮、输入框、弹窗等无自定义阴影

### 设计方案

#### Z 轴层级定义

| 层级 | 用途 | 浅色模式阴影 | 深色模式阴影 |
|------|------|-------------|-------------|
| Level 0 | 背景/底层 | none | none |
| Level 1 | 静态卡片 | `0 1px 3px rgba(0,0,0,0.08)` | `0 1px 3px rgba(0,0,0,0.3)` |
| Level 2 | 交互元素（按钮、输入框、chip） | `0 2px 6px rgba(0,0,0,0.1)` | `0 2px 6px rgba(0,0,0,0.35)` |
| Level 3 | 浮层（弹窗、下拉菜单、toast） | `0 8px 24px rgba(0,0,0,0.15)` | `0 8px 24px rgba(0,0,0,0.5)` |
| Hover | 卡片 hover 态 | `0 4px 12px rgba(0,0,0,0.12)` | `0 4px 12px rgba(0,0,0,0.4)` |

#### 修改点

**文件：`global.scss`**

1. **CSS 变量定义**（在 `:root` 中新增）：

```scss
:root {
  // 已有
  --app-max-width: 640px;
  // 新增阴影层级
  --shadow-level-1: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-level-2: 0 2px 6px rgba(0, 0, 0, 0.1);
  --shadow-level-3: 0 8px 24px rgba(0, 0, 0, 0.15);
  --shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.12);
}
```

2. **卡片静态阴影**：

```scss
.v-card {
  box-shadow: var(--shadow-level-1) !important;
}

.v-card:hover {
  box-shadow: var(--shadow-hover) !important;
}
```

3. **交互元素阴影**：

```scss
.v-btn:not(.v-btn--icon) {
  box-shadow: var(--shadow-level-2) !important;
}

.v-text-field,
.v-select,
.v-autocomplete {
  // outlined variant 不加静态阴影，保持简洁
  // solo/filled variant 加 level-2 阴影
}

.v-chip {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
```

4. **浮层阴影**：

```scss
.v-dialog > .v-card {
  box-shadow: var(--shadow-level-3) !important;
}

.v-menu > .v-overlay__content {
  box-shadow: var(--shadow-level-3) !important;
}

.v-bottom-navigation {
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.1);
}
```

5. **深色模式阴影覆盖**：

```scss
.v-theme--dark {
  --shadow-level-1: 0 1px 3px rgba(0, 0, 0, 0.3);
  --shadow-level-2: 0 2px 6px rgba(0, 0, 0, 0.35);
  --shadow-level-3: 0 8px 24px rgba(0, 0, 0, 0.5);
  --shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.4);
}
```

6. **深色模式卡片 border 保持**（已有，不删除）：

```scss
.v-theme--dark .v-card {
  border-color: rgba(255, 255, 255, 0.06) !important;
}
```

**各页面 scoped style**

无需修改——阴影通过全局 CSS 变量统一管理，各页面的 `.v-card`、`.v-btn` 自动继承。

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 卡片有静态阴影 | 所有卡片在非 hover 状态下有轻微阴影 |
| 按钮有适当阴影 | 各类按钮（tonal、elevated、flat）阴影符合层级 |
| 弹窗阴影更重 | v-dialog 弹出时阴影明显重于普通卡片 |
| 深色模式自然 | 深色模式下阴影可见且不突兀 |
| 可点击区域不受影响 | 阴影不改变元素尺寸和点击热区 |

---

## REQ-004 首页标题栏调整

### 概述

移除首页内容区中部的重复标题，保留 AppLayout 顶部固定标题栏。

### 现状分析

- `AppLayout.vue` 顶部栏已有 sticky 标题，从 `route.meta.title` 读取
- `DashboardPage.vue` 模板顶部有一个 `<h1 class="page-title">首页</h1>` 标题区域（桌面端可见，`d-none d-md-block`）
- 这两个标题同时存在造成视觉重复

### 设计方案

#### 修改点

**文件：`DashboardPage.vue`**

1. **删除页面内标题区域**：移除模板中的 `<h1 class="page-title">首页</h1>` 及其外层 wrapper div
2. **确保内容起始位置正确**：删除标题后，第一个内容元素（月度 Hero Card）的顶部 margin 需适当调整，避免与 AppLayout 顶部栏重叠
3. **router meta 确认**：确保 `/` 路由的 `meta.title` 为 `'首页'`，以便 AppLayout 顶部栏正确显示

```html
<!-- 删除前 -->
<template>
  <div>
    <div class="d-none d-md-block mb-4">
      <h1 class="page-title">首页</h1>
    </div>
    <!-- 月度 Hero Card ... -->
  </div>
</template>

<!-- 删除后 -->
<template>
  <div>
    <!-- 月度 Hero Card 直接作为第一个元素 -->
    <v-card ...> ... </v-card>
  </div>
</template>
```

**文件：`router/index.js`**

确认路由配置：

```javascript
{
  path: '/',
  component: DashboardPage,
  meta: { title: '首页' }
}
```

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 无重复标题 | 首页只有一个标题（顶部栏） |
| 标题固定 | 滚动页面时顶部标题栏始终可见 |
| 不遮挡内容 | 标题栏不遮挡下方第一个卡片 |
| 所有页面一致 | 切换其他页面，标题栏位置保持一致 |

---

## REQ-005 图标水波纹涟漪动效

### 概述

为可点击图标添加 Vuetify `v-ripple` 水波纹效果，涟漪从精确点击位置扩散至图标边框。

### 现状分析

- 应用使用 `@mdi/font` 图标
- 图标点击无视觉反馈（无 ripple、无 scale 变化，仅 hover 有轻微效果）
- Vuetify 3 内置 `v-ripple` 指令，可直接使用

### 设计方案

#### 适用范围

以下位置的可点击图标需要添加 ripple 效果：

| 位置 | 组件 | 当前实现 |
|------|------|----------|
| 底部导航栏图标 | `v-bottom-navigation` 的 `v-btn` | 已由 Vuetify 内置支持 |
| 侧边栏导航图标 | `v-navigation-drawer` 的 `v-list-item` | 当前显式设置 `:ripple="false"`，需移除以启用 |
| 首页记录条目头像 | `DashboardPage` 的 category avatar | 需添加 |
| 账单列表条目头像 | `RecordListPage` 的 category avatar | 需添加 |
| 设置页操作按钮 | `SettingsPage` 的各类 icon btn | 需添加 |
| FAB 按钮 | `AppLayout` 的 `v-btn` FAB | 需确认 |

#### 修改点

**文件：`DashboardPage.vue`**

对记录条目的 category avatar 添加 `v-ripple`：

```html
<!-- 修改前 -->
<v-avatar :color="..." size="36">
  <v-icon size="18">mdi-xxx</v-icon>
</v-avatar>

<!-- 修改后 -->
<v-avatar :color="..." size="36" v-ripple class="cursor-pointer">
  <v-icon size="18">mdi-xxx</v-icon>
</v-avatar>
```

注意：`v-ripple` 需要元素有 `position: relative` 才能正确渲染涟漪。`v-avatar` 默认为 `relative`，无需额外处理。若 avatar 外层已有 `v-list-item`，则 ripple 已由 `v-list-item` 提供，无需重复添加。

**文件：`RecordListPage.vue`**

同上，对记录条目的 avatar 添加 `v-ripple`。若记录条目使用 `v-list-item` 包裹，则 `v-list-item` 自带 ripple，仅需确认其已启用。

**文件：`SettingsPage.vue`**

对分类列表项的 edit/delete 按钮、标签的 close 按钮等，确认 `v-btn` 已有 ripple（Vuetify `v-btn` 默认启用 ripple）。

**文件：`AppLayout.vue`**

1. **侧边栏导航项**：当前侧边栏 `v-list-item` 显式设置了 `:ripple="false"`（AppLayout.vue 约第 40、62 行）。需移除此属性以启用默认 ripple 效果：

```html
<!-- 修改前 -->
<v-list-item :to="item.to" :ripple="false" ...>

<!-- 修改后 -->
<v-list-item :to="item.to" ...>
```

2. **FAB 按钮**：使用 `v-btn`，Vuetify 默认启用 ripple。若未生效，添加 `v-ripple` 显式指令。

#### 全局确认

检查 `main.js` 中是否注册了 `v-ripple` 指令。当前使用 `import * as directives from 'vuetify/directives'` 并 `...directives` 展开，已包含 ripple。

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 点击图标有涟漪 | 点击各页面可点击图标，观察涟漪效果 |
| 涟漪从点击位置散开 | 在图标不同位置点击，涟漪起始点跟随 |
| 涟漪在边框停止 | 涟漪不超出图标/按钮边界 |
| 动画流畅 | 涟漪动画不影响点击响应速度 |
| hover 行为不变 | hover 效果保持现状不变 |

---

## REQ-006 快速记账页日期时间栏布局调整

### 概述

将快速记账页的日期和时间选择调整为同一行显示，时间靠右对齐，不再折叠。

### 现状分析

- `RecordFormPage.vue` 使用 `DatePickerPopover` 组件，传入 `:show-time="true"`
- `DatePickerPopover.vue` 在日期选择器下方显示一个 `v-text-field type="time"` 作为时间输入
- 时间选择器在弹窗内部，与日期在同一弹窗中但上下排列
- 日期栏边框为默认 `outlined` variant 的较细边框

### 设计方案

#### 修改点

**文件：`DatePickerPopover.vue`**

1. **移除弹窗内的时间选择器**：当 `showTime` 为 true 时，不再在弹窗内显示时间输入
2. **在 activator 区域增加时间显示**：将日期和时间并排显示在触发区域

```html
<!-- 目标结构 -->
<template #activator="activatorProps">
  <div v-bind="activatorProps" @click="openPicker" class="d-flex align-center ga-2">
    <slot name="activator">
      <v-text-field
        :model-value="displayValue"
        :label="label"
        readonly
        hide-details
        variant="outlined"
        density="compact"
        prepend-inner-icon="mdi-calendar"
        class="flex-grow-1"
      />
    </slot>
    <v-text-field
      v-if="showTime"
      :model-value="selectedTime"
      readonly
      label="时间"
      hide-details
      variant="outlined"
      density="compact"
      prepend-inner-icon="mdi-clock-outline"
      class="time-field"
      @click.stop="openTimePicker"
    />
  </div>
</template>
```

注意：时间字段为 `readonly`，不使用 `type="time"`，时间选择通过 REQ-007 的 `v-time-picker` 弹窗完成。

3. **时间选择器弹窗**：点击时间字段时，打开独立的时间选择弹窗（见 REQ-007 设计，函数名为 `openTimePicker`）

4. **Props 调整**：新增 `modelValueTime` 的双向绑定保持不变

**文件：`RecordFormPage.vue`**

无需修改——`DatePickerPopover` 的 props 接口保持不变。

#### 日期栏边框增强

**文件：`DatePickerPopover.vue`**

```scss
<style scoped>
:deep(.v-text-field) {
  border-radius: 12px;
}

.time-field {
  max-width: 140px;
}
</style>
```

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 日期时间同行 | 记账页日期和时间在同一行显示 |
| 时间靠右 | 时间选择器右对齐 |
| 时间不折叠 | 时间始终可见，无需额外操作 |
| 功能正常 | 选择日期和时间后正确回显 |

---

## REQ-007 时间选择器UI优化

### 概述

将时间选择器从原生 `input[type=time]` 替换为 Vuetify 的 `v-time-picker` 时钟样式组件，与日历组件风格统一。

### 现状分析

- `DatePickerPopover.vue` 使用 `<v-text-field type="time">` 显示时间选择
- 原生时间输入在各浏览器样式不一致，与 Vuetify Material You 风格不协调
- 日历部分已使用 `v-date-picker`，风格统一

### 设计方案

#### 依赖确认

在当前项目使用的 Vuetify 版本（v3.12.6）中，`v-time-picker` 已从 `vuetify/components` 主包导出（位于 `node_modules/vuetify/lib/components/VTimePicker/`），不属于 Labs 组件。项目在 `main.js` 中已通过 `import * as components from 'vuetify/components'` 全量注册所有组件，因此 `v-time-picker` 已可用，无需额外安装依赖或导入 Labs 包。

#### 修改点

**文件：`DatePickerPopover.vue`**

1. **替换时间输入为弹出式时钟选择器**：

```html
<template>
  <ExpandTransition v-model="showPicker" :origin="origin" :max-width="400">
    <template #activator="activatorProps">
      <div v-bind="activatorProps" @click="openPicker" class="d-flex align-center ga-2">
        <slot name="activator">
          <v-text-field
            :model-value="displayValue"
            :label="label"
            readonly
            hide-details
            variant="outlined"
            density="compact"
            prepend-inner-icon="mdi-calendar"
            class="flex-grow-1"
          />
        </slot>
        <!-- 时间选择触发器 -->
        <v-text-field
          v-if="showTime"
          :model-value="selectedTime"
          readonly
          label="时间"
          hide-details
          variant="outlined"
          density="compact"
          prepend-inner-icon="mdi-clock-outline"
          class="time-field"
          @click.stop="openTimePicker"
        />
      </div>
    </template>

    <v-card rounded="xl">
      <v-card-text class="pa-0">
        <v-date-picker
          v-model="selectedDate"
          :show-adjacent-months="false"
          color="primary"
          width="100%"
          @update:model-value="onDateSelected"
        />
      </v-card-text>
    </v-card>
  </ExpandTransition>

  <!-- 独立的时间选择弹窗 -->
  <v-dialog v-model="showTimePicker" max-width="320">
    <v-card rounded="xl">
      <v-card-title class="text-subtitle-1 font-weight-bold pa-4 pb-2">
        选择时间
      </v-card-title>
      <v-card-text class="pa-4 pt-0">
        <v-time-picker
          v-model="selectedTime"
          color="primary"
          format="24hr"
          width="100%"
          @update:model-value="onTimeSelected"
        />
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" @click="showTimePicker = false">取消</v-btn>
        <v-btn variant="tonal" color="primary" @click="confirmTime">确定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
```

2. **Script 新增逻辑**：

```javascript
const showTimePicker = ref(false)

function openTimePicker() {
  showTimePicker.value = true
}

function onTimeSelected(time) {
  selectedTime.value = time
}

function confirmTime() {
  emit('update:modelValueTime', selectedTime.value)
  showTimePicker.value = false
}
```

3. **弹窗交互说明**：

   - 日期选择继续使用现有的 `ExpandTransition` 组件（基于 `v-dialog`，从点击位置展开）
   - 时间选择使用独立的 `v-dialog`，两者互不干扰
   - 当日期弹窗打开时点击时间字段，`@click.stop` 阻止事件冒泡，不会触发日期弹窗
   - 两个弹窗不会同时打开：日期弹窗通过 `ExpandTransition` 的 `v-model` 控制，时间弹窗通过 `showTimePicker` 控制

4. **样式**：

```scss
<style scoped>
:deep(.v-date-picker),
:deep(.v-time-picker) {
  border-radius: 16px;
}

.time-field {
  max-width: 140px;
}
</style>
```

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 时钟样式 | 点击时间字段弹出圆形时钟面板 |
| 风格统一 | 时钟面板与日历组件圆角、配色一致 |
| 深色/浅色适配 | 切换主题后面板样式正常 |
| 时间回显 | 选择时间后正确显示在输入框 |

---

## REQ-008 深色/浅色模式自动切换功能

### 概述

在设置页新增"自动"模式选项，跟随系统 `prefers-color-scheme` 自动切换深色/浅色模式，用户选择持久化到 localStorage。

### 现状分析

- `useAppStore.js`：`darkMode` 为简单 boolean ref，无持久化
- `AppLayout.vue`：`onMounted` 中强制 `appStore.setDarkMode(false)`，覆盖任何已有状态
- `SettingsPage.vue`：无深色模式切换 UI（切换在 AppLayout 侧边栏和顶部栏）
- `main.js`：定义了 `light` 和 `dark` 两个主题，`defaultTheme: 'light'`

### 设计方案

#### 状态模型

```
themeMode: 'auto' | 'dark' | 'light'  // 用户选择，持久化到 localStorage
darkMode: boolean                       // 实际生效的主题状态，由 themeMode 派生
```

#### 修改点

**文件：`useAppStore.js`**

1. **新增 `themeMode` state**：

```javascript
const THEME_KEY = 'money-app-theme-mode'

// 从 localStorage 读取初始值，默认 'auto'
const themeMode = ref(localStorage.getItem(THEME_KEY) || 'auto')
const darkMode = ref(false)
```

2. **新增 `resolvedDarkMode` 计算逻辑**：

```javascript
function resolveDarkMode() {
  if (themeMode.value === 'auto') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  return themeMode.value === 'dark'
}
```

3. **新增 `setThemeMode` action**：

```javascript
function setThemeMode(mode) {
  themeMode.value = mode
  localStorage.setItem(THEME_KEY, mode)
  darkMode.value = resolveDarkMode()
}
```

4. **新增系统主题监听**：

```javascript
function initThemeListener() {
  // 初始化
  darkMode.value = resolveDarkMode()

  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', (e) => {
    if (themeMode.value === 'auto') {
      darkMode.value = e.matches
    }
  })
}
```

5. **保留 `toggleDarkMode` 用于向后兼容**（侧边栏和顶部栏的快速切换按钮）：

```javascript
function toggleDarkMode() {
  // 快速切换：如果当前是 auto，切换为与当前相反的固定模式
  if (themeMode.value === 'auto') {
    setThemeMode(darkMode.value ? 'light' : 'dark')
  } else {
    setThemeMode(darkMode.value ? 'light' : 'dark')
  }
}
```

6. **暴露新属性**：

```javascript
return {
  // 已有
  darkMode, loading, toast, transitionOrigin,
  // 新增
  themeMode,
  // 已有 actions
  toggleDarkMode, setDarkMode, setLoading, showToast, hideToast, setTransitionOrigin,
  // 新增 actions
  setThemeMode, initThemeListener,
}
```

**文件：`AppLayout.vue`**

1. **移除强制 light mode**：删除 `onMounted` 中的 `appStore.setDarkMode(false)`

2. **初始化主题监听**：在现有的 `onMounted` 钩子中调用 `appStore.initThemeListener()`。注意：AppLayout.vue 当前已有两个 `onMounted` 调用（Composition API 允许多个），将 `initThemeListener()` 添加到其中一个即可，无需新增第三个钩子

3. **顶部栏主题切换按钮改为三态**（可选，或保留在设置页）：

```html
<!-- 保持现有快速切换按钮不变，仅用于 auto 模式下的手动覆盖 -->
<v-btn icon @click="appStore.toggleDarkMode()">
  <v-icon>{{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}</v-icon>
</v-btn>
```

**文件：`SettingsPage.vue`**

1. **新增主题模式选择卡片**（放在设置页顶部，作为第一个设置项）：

```html
<v-card rounded="xl" class="settings-card mb-4">
  <v-card-title class="d-flex align-center ga-2">
    <v-avatar color="primary" size="36" rounded="lg">
      <v-icon size="18">mdi-brightness-6</v-icon>
    </v-avatar>
    <span class="text-subtitle-1 font-weight-bold">外观设置</span>
  </v-card-title>

  <v-card-text>
    <v-btn-toggle
      v-model="appStore.themeMode"
      mandatory
      rounded="xl"
      density="compact"
      color="primary"
      class="w-100"
      @update:model-value="appStore.setThemeMode"
    >
      <v-btn value="auto" class="flex-grow-1">
        <v-icon start>mdi-brightness-auto</v-icon>
        自动
      </v-btn>
      <v-btn value="light" class="flex-grow-1">
        <v-icon start>mdi-weather-sunny</v-icon>
        浅色
      </v-btn>
      <v-btn value="dark" class="flex-grow-1">
        <v-icon start>mdi-weather-night</v-icon>
        深色
      </v-btn>
    </v-btn-toggle>
  </v-card-text>
</v-card>
```

2. **Script 导入 useAppStore**（如果尚未导入）：

```javascript
import { useAppStore } from '@/stores/useAppStore'
const appStore = useAppStore()
```

### 状态流转

```
用户选择 'auto' → localStorage 保存 'auto'
  → darkMode = matchMedia('(prefers-color-scheme: dark)').matches
  → 系统切换时自动跟随

用户选择 'dark' → localStorage 保存 'dark'
  → darkMode = true
  → 不响应系统变化

用户选择 'light' → localStorage 保存 'light'
  → darkMode = false
  → 不响应系统变化

应用启动 → 读取 localStorage → 恢复 themeMode → resolveDarkMode()
```

### 验收测试

| 测试项 | 验证方法 |
|--------|----------|
| 自动模式跟随系统 | 选择自动后，切换系统深色/浅色，应用跟随变化 |
| 手动模式不跟随 | 选择深色/浅色后，切换系统设置，应用不变 |
| 持久化保存 | 刷新页面后，上次选择的模式保持 |
| 无需刷新生效 | 系统主题变化时，应用实时切换 |
| 手动切换不受影响 | 侧边栏/顶部栏的快速切换按钮仍可使用 |

---

## 文件修改清单

| 文件 | REQ | 修改类型 | 说明 |
|------|-----|----------|------|
| `frontend/src/stores/useAppStore.js` | 001, 008 | 修改 | 新增 themeMode、initThemeListener；transitionOrigin 已有无需改 |
| `frontend/src/components/layout/AppLayout.vue` | 001, 005, 008 | 修改 | 修复 expand transition；移除强制 light mode；初始化主题监听 |
| `frontend/src/pages/RecordListPage.vue` | 001, 002, 005 | 修改 | 筛选栏样式优化；确认 ripple |
| `frontend/src/pages/RecordDetailPage.vue` | 001 | 确认 | 确认 handleBack 逻辑无需改动 |
| `frontend/src/pages/DashboardPage.vue` | 004, 005 | 修改 | 删除重复标题；添加 ripple |
| `frontend/src/pages/SettingsPage.vue` | 005, 008 | 修改 | 新增外观设置卡片；确认按钮 ripple |
| `frontend/src/pages/RecordFormPage.vue` | 006 | 确认 | 无需修改，由 DatePickerPopover 改动生效 |
| `frontend/src/components/common/DatePickerPopover.vue` | 006, 007 | 修改 | 日期时间同行布局；引入 v-time-picker |
| `frontend/src/styles/global.scss` | 003 | 修改 | 新增阴影层级 CSS 变量和规则 |
| `frontend/src/router/index.js` | 004 | 确认 | 确认路由 meta.title 配置 |

---

## 实施顺序建议

按依赖关系和优先级排序：

1. **REQ-008**（P1，深色/浅色自动切换）—— 独立模块，影响全局主题基础
2. **REQ-003**（P2，全局阴影）—— 独立模块，影响所有页面视觉
3. **REQ-004**（P1，首页标题栏）—— 独立模块，改动最小
4. **REQ-001**（P1，展开动画）—— 独立模块，需仔细调试动画参数
5. **REQ-002**（P2，筛选栏UI）—— 独立模块，视觉优化
6. **REQ-005**（P2，涟漪动效）—— 独立模块，影响多个页面
7. **REQ-006 + REQ-007**（P2，日期时间布局 + 时间选择器）—— 共享 DatePickerPopover 组件，建议一起实施
