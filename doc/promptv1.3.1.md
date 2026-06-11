# Money App v1.3.1 VibeCoding Prompt

> 自动生成，用于指导 AI Agent 完成 v1.3.1 版本的全部开发工作

---

## 项目概述

**项目名称：** Money App v1.3.1
**项目类型：** 前端 Vue 3 单页应用
**目标：** 实现 8 个 UI/UX 优化模块，包含动画修复、视觉增强、交互优化和主题自动切换
**工作目录：** `h:\code\money.app`

### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5.34 | 前端框架（Composition API + `<script setup>`） |
| Vuetify | 3.12.6 | Material Design 组件库（含 v-time-picker） |
| Vite | 8 | 构建工具 |
| Pinia | 3 | 状态管理 |
| dayjs | - | 日期处理 |
| Chart.js / vue-chartjs | - | 图表 |
| @mdi/font | 7.4 | Material Design Icons |

### 代码规范

- **语言：** 纯 JavaScript（非 TypeScript），所有文件后缀为 `.js` / `.vue`
- **测试框架：** Vitest（前端）
- **代码检测：** ESLint + Prettier
- **所有新增和修改的代码必须：**
  1. 含 JS 逻辑的代码有 Vitest 单元测试覆盖（CSS-only 模块如 REQ-003 通过视觉验证）
  2. 通过 ESLint 检测（零 warning，零 error）
  3. 通过 Prettier 格式化检查

### 设计原则

1. **模块独立：** 每个 REQ 模块可独立开发和测试，不相互依赖
2. **最小侵入：** 优先复用现有组件和 store，减少新增文件
3. **Vuetify 原生优先：** 尽量使用 Vuetify 3 原生组件和指令，减少自定义样式
4. **主题感知：** 所有新增样式必须同时适配深色/浅色模式

---

## 开发任务清单

### 建议开发顺序：8 → 3 → 4 → 1 → 2 → 5 → 6+7

| 序号 | 模块 | 优先级 | 复杂度 | 涉及文件 |
|------|------|--------|--------|----------|
| 8 | 深色/浅色模式自动切换 | P1 | 中 | `useAppStore.js`、`AppLayout.vue`、`SettingsPage.vue` |
| 3 | 全局阴影与层级设计 | P2 | 低 | `global.scss` |
| 4 | 首页标题栏调整 | P1 | 低 | `DashboardPage.vue`、`router/index.js`（确认） |
| 1 | 账单详情页展开动画 | P1 | 中 | `AppLayout.vue` |
| 2 | 账单页筛选列表UI优化 | P2 | 低 | `RecordListPage.vue` |
| 5 | 图标水波纹涟漪动效 | P2 | 低 | `AppLayout.vue`、`DashboardPage.vue`、`RecordListPage.vue`、`SettingsPage.vue` |
| 6+7 | 日期时间布局 + 时间选择器 | P2 | 中 | `DatePickerPopover.vue` |

---

## 模块详细需求

### 模块 REQ-008：深色/浅色模式自动切换（P1）

**需求：** 在设置页新增"自动"模式选项，跟随系统 `prefers-color-scheme` 自动切换深色/浅色模式。

**实现要点：**

1. **修改 `useAppStore.js`：**
   - 定义 `THEME_KEY = 'money-app-theme-mode'`
   - 新增 `themeMode` ref，从 localStorage 读取初始值，默认 `'auto'`
   - 新增 `resolveDarkMode()` 函数：`auto` 时读取 `window.matchMedia('(prefers-color-scheme: dark)').matches`，否则按 `themeMode` 判断
   - 新增 `setThemeMode(mode)` action：更新 `themeMode`，写入 localStorage，更新 `darkMode`
   - 新增 `initThemeListener()` 函数：初始化 `darkMode`，监听 `matchMedia` 的 `change` 事件，仅在 `themeMode === 'auto'` 时响应系统变化
   - 修改 `toggleDarkMode()`：如果当前是 `auto`，切换为与当前状态相反的固定模式
   - return 中新增 `themeMode`、`setThemeMode`、`initThemeListener`

2. **修改 `AppLayout.vue`：**
   - 删除**第二个** `onMounted` 钩子中的 `appStore.setDarkMode(false)`（第 349-352 行，强制 light mode）
   - 将该 `onMounted` 改为调用 `appStore.initThemeListener()`
   - 侧边栏底部的 `v-switch` 深色模式切换保持不变，`toggleDarkMode()` 在 `auto` 模式下会切换为固定模式

3. **修改 `SettingsPage.vue`：**
   - `useAppStore` 已导入（第 547 行），无需重复导入
   - 新增外观设置卡片作为**第一个**设置项（插入在 `page-header` 之后、`分类管理` 卡片之前）
   - 使用 `v-btn-toggle` 实现三态切换：自动 / 浅色 / 深色
   - 绑定 `v-model="appStore.themeMode"`，`@update:model-value="appStore.setThemeMode"`
   - 每个按钮带 `v-icon`：`mdi-brightness-auto` / `mdi-weather-sunny` / `mdi-weather-night`
   - 卡片样式与现有设置卡片一致：`v-card class="pa-4 mb-3 settings-card" rounded="xl"`

**验收标准：**
- 选择"自动"后，切换系统深色/浅色，应用跟随变化
- 选择"深色"/"浅色"后，切换系统设置，应用不变
- 刷新页面后，上次选择的模式保持（localStorage 持久化）
- 系统主题变化时，应用实时切换无需刷新
- 侧边栏/顶部栏的快速切换按钮仍可使用

**参考文档：** `doc/tasksv1.3.1/req-008-theme-auto.md`、`doc/detailed-designv1.3.1.md` REQ-008 章节

---

### 模块 REQ-003：全局阴影与层级设计（P2）

**需求：** 为全应用元素建立 Material You Z 轴阴影层级体系，增强视觉层次感。

**实现要点：**

1. **修改 `global.scss`：**
   - 在 `:root` 中新增 CSS 变量：
     - `--shadow-level-1: 0 1px 3px rgba(0, 0, 0, 0.08)` — 静态卡片
     - `--shadow-level-2: 0 2px 6px rgba(0, 0, 0, 0.1)` — 交互元素（按钮、输入框、chip）
     - `--shadow-level-3: 0 8px 24px rgba(0, 0, 0, 0.15)` — 浮层（弹窗、下拉菜单）
     - `--shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.12)` — 卡片 hover 态
   - 卡片静态阴影：`.v-card` 使用 `var(--shadow-level-1)`
   - 卡片 hover 阴影：`.v-card:hover` 使用 `var(--shadow-hover)`
   - 交互元素阴影：`.v-btn:not(.v-btn--icon)` 使用 `var(--shadow-level-2)`
   - Chip 阴影：`.v-chip` 使用 `0 1px 2px rgba(0, 0, 0, 0.06)`
   - 浮层阴影：`.v-dialog > .v-card` 和 `.v-menu > .v-overlay__content` 使用 `var(--shadow-level-3)`
   - 底部导航阴影：`.v-bottom-navigation` 使用 `0 -2px 12px rgba(0, 0, 0, 0.1)`
   - 深色模式覆盖：`.v-theme--dark` 下重新定义四个 CSS 变量：
     - `--shadow-level-1: 0 1px 3px rgba(0, 0, 0, 0.3)`
     - `--shadow-level-2: 0 2px 6px rgba(0, 0, 0, 0.35)`
     - `--shadow-level-3: 0 8px 24px rgba(0, 0, 0, 0.5)`
     - `--shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.4)`
   - 保留已有的深色模式 `.v-theme--dark .v-card` border-color

**验收标准：**
- 所有卡片在非 hover 状态下有轻微阴影
- 各类按钮阴影符合层级
- 弹窗阴影明显重于普通卡片
- 深色模式下阴影可见且不突兀
- 阴影不改变元素尺寸和点击热区

**参考文档：** `doc/tasksv1.3.1/req-003-shadow-elevation.md`、`doc/detailed-designv1.3.1.md` REQ-003 章节

---

### 模块 REQ-004：首页标题栏调整（P1）

**需求：** 移除 DashboardPage 中的页面标题（AppLayout 顶部栏已通过 `route.meta.title` 显示固定标题，无需页面内再显示）。

**现状：** DashboardPage.vue 第 4-11 行有一个 `<h1 class="page-title">首页</h1>`（桌面端可见，`d-none d-md-block`），与 AppLayout 顶部 sticky 标题栏重复。

**实现要点：**

1. **修改 `DashboardPage.vue`：**
   - 移除模板中的整个 `page-header` div（第 4-11 行），包含 `<h1 class="page-title">首页</h1>` 和 `<p class="page-subtitle">` 及其外层 wrapper
   - 确认删除标题后，第一个内容元素（月度 Hero Card `<v-card class="monthly-overview-card">`）的顶部 margin 适当，不与 AppLayout 顶部栏重叠

2. **确认 `router/index.js`：**
   - `/` 路由的 `meta.title` 已为 `'首页'`（已确认，无需修改）

**验收标准：**
- 首页只有 AppLayout 顶部栏的标题，无页面内重复标题
- 滚动页面时顶部标题栏始终可见
- 标题栏不遮挡下方第一个卡片（月度 Hero Card）
- 切换其他页面，标题栏位置保持一致

**参考文档：** `doc/tasksv1.3.1/req-004-dashboard-title.md`、`doc/detailed-designv1.3.1.md` REQ-004 章节

---

### 模块 REQ-001：账单详情页展开动画（P1）

**需求：** 修复从账单列表点击进入详情页时的展开动画。动画从点击坐标开始，以 scale 变换扩展至全屏。

**实现要点：**

1. **修改 `AppLayout.vue` 的 `onBeforeEnter` 钩子（第 301-308 行）：**
   - 当前代码设置 `scale(0)`，需改为 `scale(0.1)`（从极小而非不可见开始，避免闪烁）
   - `transformOrigin` 映射逻辑保持不变

2. **修改 `AppLayout.vue` 的 `onEnter` 钩子（第 310-325 行）：**
   - 读取 `appStore.transitionOrigin` 获取点击坐标
   - 将视口坐标映射到 el 的相对坐标（百分比）：`x = ((origin.x - rect.left) / rect.width) * 100`
   - 设置 `transformOrigin` 为映射后的坐标
   - 初始状态：`scale(0.1)`, `opacity(0)`, `transition: none`
   - `requestAnimationFrame` 中设置过渡：`transform 250ms cubic-bezier(0.4, 0, 0.2, 1), opacity 250ms ease`
   - 目标状态：`scale(1)`, `opacity(1)`
   - 监听 `transitionend` 事件调用 `done`（`{ once: true }`）

3. **修改 `AppLayout.vue` 的 `onLeave` 钩子（第 327-347 行）：**
   - 离开动画：`scale(1) → scale(0.95)`, `opacity(1) → 0`, `duration 200ms ease`
   - 确保 `transformOrigin` 与 enter 一致

4. **确认已有逻辑无需改动：**
   - `RecordListPage.goToDetail()` 已正确写入 `transitionOrigin`
   - `RecordDetailPage.handleBack()` 已清除 `transitionOrigin`
   - `useAppStore.js` 的 `transitionOrigin` getter/setter 满足需求

**验收标准：**
- 在列表不同位置点击，动画起始点跟随点击位置
- 快速连续点击不同条目，无残影或闪烁
- 375px / 768px / 1440px 宽度下动画表现一致
- 从详情页返回时有反向收束效果

**参考文档：** `doc/tasksv1.3.1/req-001-expand-animation.md`、`doc/detailed-designv1.3.1.md` REQ-001 章节

---

### 模块 REQ-002：账单页筛选列表UI优化（P2）

**需求：** 美化账单页筛选栏的样式，使其符合 Material You 设计风格，交互形式保持不变。

**实现要点：**

1. **修改 `RecordListPage.vue`：**
   - 筛选栏卡片添加 `variant="flat"` 或 `elevation="0"`（配合 REQ-003 全局阴影系统）
   - 添加内部 padding `pa-4`
   - 使用 `v-row` + `v-col` 实现响应式排列：移动端 `cols="6"`（每行 2 个），桌面端 `sm="3"`（一行 4 个）
   - v-select 样式微调：确保 `rounded="lg"`、`bg-color="surface"`
   - 类型筛选添加 `prepend-inner-icon="mdi-swap-vertical"`
   - 分类筛选添加 `prepend-inner-icon="mdi-shape-outline"`

**验收标准：**
- 筛选组件使用 Vuetify 3 原生组件或符合 Material You 风格
- 筛选组件样式与整体UI风格协调
- 筛选功能保持不变
- 支持深色/浅色模式下的样式适配
- 375px / 768px / 1440px 下布局正确

**参考文档：** `doc/tasksv1.3.1/req-002-filter-ui.md`、`doc/detailed-designv1.3.1.md` REQ-002 章节

---

### 模块 REQ-005：图标水波纹涟漪动效（P2）

**需求：** 为可点击图标添加 Vuetify `v-ripple` 水波纹效果，涟漪从精确点击位置扩散至图标边框。

**实现要点：**

1. **确认全局 `v-ripple` 指令已注册：** `main.js` 中 `vuetify/directives` 已包含 ripple

2. **修改 `AppLayout.vue`：**
   - 移除侧边栏 `v-list-item` 上的 `:ripple="false"` 属性，启用默认 ripple
   - 确认 FAB `v-btn` 已有 ripple（Vuetify 默认启用）

3. **修改 `DashboardPage.vue`：**
   - 检查记录条目是否已被 `v-list-item` 包裹（自带 ripple）
   - 若无，为 category avatar 添加 `v-ripple` 和 `class="cursor-pointer"`

4. **修改 `RecordListPage.vue`：**
   - 同上，检查是否已有 `v-list-item` 包裹
   - 若无，为 avatar 添加 `v-ripple` 和 `class="cursor-pointer"`

5. **修改 `SettingsPage.vue`：**
   - 确认分类列表项的 edit/delete `v-btn` 已有 ripple
   - 确认标签 close 按钮已有 ripple

**验收标准：**
- 点击各页面可点击图标，产生涟漪效果
- 涟漪从精确点击位置开始扩散
- 涟漪在碰到图标边框时停止
- 涟漪动画自然流畅，不影响点击响应速度
- hover 效果保持现状不变

**参考文档：** `doc/tasksv1.3.1/req-005-ripple-effect.md`、`doc/detailed-designv1.3.1.md` REQ-005 章节

---

### 模块 REQ-006 + REQ-007：日期时间布局调整 + 时间选择器UI优化（P2）

**需求：** 将快速记账页的日期和时间选择调整为同一行显示，时间靠右对齐；将时间选择器从原生 `input[type=time]` 替换为 Vuetify 的 `v-time-picker` 时钟样式组件。

> 注意：REQ-006 和 REQ-007 共享 `DatePickerPopover.vue` 组件，必须一起实施。

**实现要点：**

1. **修改 `DatePickerPopover.vue` — activator 区域布局（REQ-006）：**
   - 当前结构：activator `#activator` 插槽内只有一个日期 `v-text-field`，时间 `v-text-field type="time"` 在弹窗卡片内部（第 30-39 行）
   - 目标结构：将 activator 区域改为 `d-flex align-center ga-2` 横向 div，包裹日期字段和时间字段
   - 日期字段使用 `flex-grow-1` 占据剩余空间
   - 时间字段添加 `class="time-field"` 限制最大宽度（`max-width: 140px`），设为 `readonly`，不使用 `type="time"`

2. **修改 `DatePickerPopover.vue` — 移除弹窗内的时间选择器（REQ-006）：**
   - 删除弹窗卡片内的 `v-text-field type="time"`（第 30-39 行）
   - 时间选择改为在 activator 区域独立显示（与日期同行）

3. **修改 `DatePickerPopover.vue` — 新增独立时间选择弹窗（REQ-007）：**
   - 确认 `v-time-picker` 从 `vuetify/components` 主包导出（Vuetify v3.12.6 已非 Labs 组件）
   - 添加 `showTimePicker` ref 状态
   - 使用 `v-dialog` + `v-card` 包裹 `v-time-picker`
   - `v-time-picker` 设置 `format="24hr"`, `color="primary"`, `width="100%"`
   - 弹窗标题："选择时间"，底部添加"取消"和"确定"按钮
   - 新增 `openTimePicker()`、`onTimeSelected(time)`、`confirmTime()` 交互逻辑
   - 时间字段添加 `@click.stop="openTimePicker"`

4. **样式适配：**
   - `:deep(.v-text-field)` 添加 `border-radius: 12px`
   - `v-time-picker` 添加 `border-radius: 16px`（与日历组件一致）
   - 确认深色/浅色模式下弹窗样式正常

5. **确认 `RecordFormPage.vue` 无需改动** — `DatePickerPopover` 的 props 接口保持不变

**验收标准：**
- 记账页日期和时间在同一行显示
- 时间选择器右对齐，始终可见，无需额外操作
- 点击时间字段弹出圆形时钟面板
- 时钟面板与日历组件圆角、配色一致
- 切换深色/浅色主题后面板样式正常
- 选择日期和时间后正确回显

**参考文档：** `doc/tasksv1.3.1/req-006-datetime-layout.md`、`doc/tasksv1.3.1/req-007-time-picker.md`、`doc/detailed-designv1.3.1.md` REQ-006 和 REQ-007 章节

---

## 关键文件现状与跨模块注意事项

> 多个模块修改同一文件时，后执行的 Agent 必须保留前序 Agent 的改动。

### AppLayout.vue（被 REQ-001、REQ-005、REQ-008 修改）

- **第 40 行、第 62 行：** `v-list-item` 上有 `:ripple="false"`（REQ-005 删除）
- **第 134-150 行：** `<router-view>` 的 expand transition 区域（REQ-001 修改 `onEnter`/`onLeave` 钩子）
- **第 301-347 行：** `onBeforeEnter`、`onEnter`、`onLeave` 三个 JS 钩子函数（REQ-001 修改）
- **第 349-352 行：** 第二个 `onMounted`，调用 `appStore.setDarkMode(false)`（REQ-008 改为 `initThemeListener()`）
- **执行顺序：** REQ-008 先改 `onMounted` → REQ-001 改 transition 钩子 → REQ-005 改 `:ripple="false"`，互不冲突

### DashboardPage.vue（被 REQ-004、REQ-005 修改）

- **第 4-11 行：** `page-header` div 含 `<h1>首页</h1>`（REQ-004 删除整个 div）
- REQ-005 需检查记录条目是否有 `v-list-item` 包裹，若无则添加 `v-ripple`
- **执行顺序：** REQ-004 先删标题 → REQ-005 检查 ripple，互不冲突

### RecordListPage.vue（被 REQ-002、REQ-005 修改）

- REQ-002 修改筛选栏样式（`v-row`/`v-col` 布局、`prepend-inner-icon` 等）
- REQ-005 检查列表条目 avatar 的 ripple
- **执行顺序：** REQ-002 先改筛选栏 → REQ-005 检查 ripple，区域不重叠

### SettingsPage.vue（被 REQ-008、REQ-005 修改）

- REQ-008 新增外观设置卡片（第一个设置项）
- REQ-005 确认按钮已有 ripple（Vuetify 默认，通常无需代码改动）
- **执行顺序：** REQ-008 先新增卡片 → REQ-005 确认 ripple

### useAppStore.js（被 REQ-008 修改）

- 当前 `darkMode` 为简单 boolean ref，无持久化
- 当前 `toggleDarkMode()` 直接取反 `darkMode`
- REQ-008 新增 `themeMode`、`resolveDarkMode()`、`setThemeMode()`、`initThemeListener()`

### DatePickerPopover.vue（被 REQ-006+007 修改）

- 当前 activator `#activator` 插槽内只有一个日期 `v-text-field`
- 时间 `v-text-field type="time"` 在弹窗卡片内部（第 30-39 行）
- REQ-006+007 将时间移到 activator 区域并替换为 `v-time-picker` 弹窗

---

## Agent 架构

### 主 Agent（Orchestrator）

**职责：**
1. 跟踪整体开发进度
2. 按顺序调度子 Agent 执行各模块
3. 确保模块间的依赖关系正确处理（REQ-006 和 REQ-007 必须由同一子 Agent 一起实施）
4. 汇总各模块的测试结果
5. 最终验证所有代码通过 ESLint + Prettier 检查

**工作流程：**
```
1. 确认项目环境就绪（Vitest、ESLint、Prettier 已安装且可执行）
2. 按顺序 8 → 3 → 4 → 1 → 2 → 5 → 6+7 调度子 Agent
3. 每个模块完成后：
   - 运行该模块涉及文件的 Vitest 测试
   - 运行 ESLint 检查（涉及的 .js 和 .vue 文件）
   - 运行 Prettier 检查（涉及的 .js 和 .vue 文件）
   - 记录完成状态到 doc/tasksv1.3.1/progress.md
4. 所有模块完成后，运行全量 Vitest 测试
5. 运行全量 ESLint + Prettier 检查
6. 生成最终报告
```

### 子 Agent（Module Implementer）

**每个子 Agent 职责：**
1. 阅读模块详细设计文档（`doc/tasksv1.3.1/` 目录下对应文件）和详细设计文档（`doc/detailed-designv1.3.1.md` 对应章节）
2. 实现模块功能代码
3. 编写完整的 Vitest 单元测试（新建或更新对应的 `.test.js` 文件）
4. 确保代码通过 ESLint + Prettier 检测
5. 更新 `doc/tasksv1.3.1/progress.md` 中的完成状态

**子 Agent 列表：**

| Agent | 负责模块 | 输入文件 | 涉及源文件 |
|-------|----------|----------|------------|
| agent-008 | 深色/浅色自动切换 | `req-008-theme-auto.md` | `useAppStore.js`、`AppLayout.vue`、`SettingsPage.vue` |
| agent-003 | 全局阴影与层级 | `req-003-shadow-elevation.md` | `global.scss` |
| agent-004 | 首页标题栏调整 | `req-004-dashboard-title.md` | `DashboardPage.vue` |
| agent-001 | 展开动画修复 | `req-001-expand-animation.md` | `AppLayout.vue` |
| agent-002 | 筛选栏UI优化 | `req-002-filter-ui.md` | `RecordListPage.vue` |
| agent-005 | 涟漪动效 | `req-005-ripple-effect.md` | `AppLayout.vue`、`DashboardPage.vue`、`RecordListPage.vue`、`SettingsPage.vue` |
| agent-006+007 | 日期时间布局+时间选择器 | `req-006-datetime-layout.md`、`req-007-time-picker.md` | `DatePickerPopover.vue` |

---

## 测试要求

### Vitest 单元测试规范

1. **测试文件位置：** 与被测文件同目录，命名为 `*.test.js` 或 `*.spec.js`

   **目录结构：**
   ```
   frontend/src/
   ├── pages/
   │   ├── DashboardPage.vue
   │   ├── DashboardPage.test.js       # 新增（REQ-004、REQ-005）
   │   ├── SettingsPage.vue
   │   ├── SettingsPage.test.js        # 新增（REQ-008、REQ-005）
   │   └── RecordListPage.vue
   │   └── RecordListPage.test.js      # 已有，需更新（REQ-002、REQ-005）
   ├── components/
   │   ├── common/
   │   │   ├── DatePickerPopover.vue
   │   │   └── DatePickerPopover.test.js   # 已有，需更新（REQ-006、REQ-007）
   │   └── layout/
   │       ├── AppLayout.vue
   │       └── AppLayout.test.js           # 已有，需更新（REQ-001、REQ-008、REQ-005）
   ├── stores/
   │   ├── useAppStore.js
   │   └── useAppStore.test.js             # 已有，需更新（REQ-008）
   └── styles/
       └── global.scss                      # CSS-only（REQ-003），无需 Vitest 测试
   ```

   > 注：`RecordFormPage.vue`、`RecordDetailPage.vue` 在 v1.3.1 中无需修改，其已有测试文件保持不变。

2. **测试覆盖率要求：** 核心逻辑覆盖率 ≥ 80%
3. **测试内容必须包括：**
   - 组件渲染测试
   - 用户交互测试（点击、输入、切换等）
   - 状态变更测试（Pinia store 的 state/action 变化）
   - 边界条件测试
   - 深色/浅色模式切换测试（REQ-008）

4. **测试示例结构：**
```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ComponentName from './ComponentName.vue'

describe('ComponentName', () => {
  beforeEach(() => {
    // 初始化设置
  })

  it('should render correctly', () => {
    const wrapper = mount(ComponentName)
    expect(wrapper.exists()).toBe(true)
  })

  it('should handle user interaction', async () => {
    // 交互测试
  })
})
```

5. **Mock 策略：**
   - Vue Router：使用 `vi.mock('vue-router')`
   - Pinia Store：使用 `vi.mock('@/stores/xxx')` 或 `createTestingPinia()`
   - Vuetify 组件：使用 `shallowMount` 或 mock 子组件
   - `window.matchMedia`：在 REQ-008 测试中需 mock `matchMedia` 以模拟系统主题变化
   - `localStorage`：在 REQ-008 测试中需 mock localStorage 验证持久化
   - `getBoundingClientRect`：在 REQ-001 测试中需 mock 坐标计算

### ESLint 配置要求

项目已配置 ESLint（`frontend/eslint.config.js`），规则包括：
- `eslint-plugin-vue` flat/recommended
- `eslint-config-prettier` 避免与 Prettier 冲突
- 零 warning，零 error

### Prettier 配置要求

项目已配置 `.prettierrc`：
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

---

## 环境确认

主 Agent 在开始开发前，需确认以下环境就绪：

### 确认清单

- [ ] `frontend/node_modules` 已安装（`npm install` 已执行）
- [ ] `npm run test` 可执行
- [ ] `npm run lint` 可执行
- [ ] `npm run format` 可执行
- [ ] 现有 7 个测试文件全部通过（基线测试）

> 注：v1.3 已完成环境初始化（Vitest、ESLint、Prettier 已安装并配置），v1.3.1 无需重复安装。

---

## 完成标准

每个模块完成必须满足：

1. ✅ 功能代码实现完成
2. ✅ Vitest 单元测试全部通过（新建或更新的测试文件）
3. ✅ ESLint 检测零 warning 零 error
4. ✅ Prettier 格式化检查通过
5. ✅ `doc/tasksv1.3.1/progress.md` 中对应模块标记为已完成

整体完成标准：

1. ✅ 所有 8 个模块开发完成
2. ✅ 全量 Vitest 测试通过（包括已有测试 + 新增测试）
3. ✅ 全量 ESLint + Prettier 检查通过
4. ✅ `doc/tasksv1.3.1/progress.md` 中所有模块标记为已完成
5. ✅ `frontend/` 目录下 `npm run build` 构建成功

---

## 参考文档

- **需求文档：** `doc/proposalv1.3.1.md`
- **详细设计：** `doc/detailed-designv1.3.1.md`
- **任务清单：** `doc/tasksv1.3.1/` 目录下各模块文件
- **总进度：** `doc/tasksv1.3.1/progress.md`

---

## 主 Agent 验证清单

主 Agent 在调度子 Agent 前后，需逐项验证：

### 环境确认验证

- [ ] `npm run test` 可执行，现有测试全部通过
- [ ] `npm run lint` 可执行
- [ ] `npm run format` 可执行

### 每个模块完成后的验证

- [ ] 功能代码已实现
- [ ] 测试文件已创建或更新（`*.test.js`）
- [ ] `npm run test` 涉及的测试全部通过
- [ ] `npm run lint` 零 warning 零 error
- [ ] `npm run format` 检查通过
- [ ] `doc/tasksv1.3.1/progress.md` 中对应模块已标记为已完成

### 最终验证

- [ ] 所有 8 个模块已完成
- [ ] `npm run test` 全量测试通过
- [ ] `npm run lint` 全量检查通过
- [ ] `npm run format` 全量检查通过
- [ ] `npm run build` 构建成功
- [ ] `doc/tasksv1.3.1/progress.md` 所有模块标记为已完成

---

## 注意事项

1. **项目语言为纯 JavaScript**，不要使用 TypeScript 语法
2. **所有 `.vue` 文件使用 `<script setup>` 语法**
3. **Vuetify 3 原生优先**：使用 Vuetify 原生组件和指令（如 `v-ripple`），减少自定义样式
4. **深色/浅色模式适配**：所有新增样式必须同时适配两种主题模式
5. **REQ-006 和 REQ-007 必须一起实施**，它们共享 `DatePickerPopover.vue` 组件
6. **REQ-001 的动画参数需要仔细调试**：`scale(0.1)→scale(1)`、250ms、cubic-bezier(0.4, 0, 0.2, 1)
7. **REQ-003 的阴影使用 `!important`**：确保覆盖 Vuetify 默认阴影
8. **REQ-008 需要 mock `matchMedia` 和 `localStorage`**：测试中无法真正控制系统主题，需使用 `vi.fn()` 模拟
9. **AppLayout.vue 被 3 个模块修改**（REQ-001、REQ-005、REQ-008），后执行的 Agent 必须保留前序 Agent 的改动
10. **提交前必须运行测试和检测**，确保代码质量
11. **不要修改后端代码**，v1.3.1 仅涉及前端改动
12. **`global.scss`（REQ-003）为纯 CSS**，无需 Vitest 测试，通过视觉验证确认效果
