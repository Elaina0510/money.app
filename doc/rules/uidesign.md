# Money App UI/UX 设计规范

本文档记录当前项目遵循的 UI/UX 设计规范，供后续版本开发参考。

---

## 1. 设计基础

### 1.1 设计体系

基于 **Material You (Material Design 3)** 设计体系，使用 Vuetify 3 组件库实现。

### 1.2 技术约束

| 项目 | 规范 |
|------|------|
| 组件库 | Vuetify 3（全量注册，含 components 和 directives） |
| 图标库 | @mdi/font (Material Design Icons) |
| 样式方案 | Vuetify utility classes + scoped CSS + global.scss |
| 主题系统 | Vuetify theme（light / dark 双主题） |
| 响应式断点 | 960px（桌面端 ≥ 960px，移动端 < 960px） |

---

## 2. 色彩系统

### 2.1 主题色板

**浅色模式（Light）：**

| 角色 | 色值 | 用途 |
|------|------|------|
| primary | `#8B7E74` | 灰褐色，主操作、强调 |
| secondary | `#A8988E` | 浅灰褐色，次要操作 |
| accent | `#C4B5A8` | 更浅灰褐色，装饰 |
| background | `#F5F0EB` | 米白，页面背景 |
| surface | `#FFFFFF` | 纯白，卡片/容器背景 |
| surface-variant | `#F0EBE6` | 浅米色，替代表面 |
| on-surface | `#1C1B1F` | 深色，表面文字 |
| on-surface-variant | `#49454F` | 中灰，次要文字 |

**深色模式（Dark）：**

| 角色 | 色值 | 用途 |
|------|------|------|
| primary | `#A8988E` | 略亮灰褐色 |
| secondary | `#8B7E74` | 灰褐色 |
| accent | `#7A6E64` | 深灰褐色 |
| background | `#1E1E1E` | 深灰，页面背景 |
| surface | `#2C2C2C` | 略浅深灰，卡片背景 |
| surface-variant | `#2C2C2C` | 同 surface |
| on-surface | `#E6E1E5` | 浅灰白，表面文字 |
| on-surface-variant | `#CAC4D0` | 中灰白，次要文字 |

**语义色：**

| 角色 | 浅色模式 | 深色模式 | 用途 |
|------|----------|----------|------|
| error | `#E57373` | `#EF5350` | 错误、支出 |
| warning | `#FFB74D` | `#FFA726` | 警告 |
| success | `#81C784` | `#66BB6A` | 成功、收入 |
| info | `#64B5F6` | `#42A5F5` | 信息 |

### 2.2 业务色（硬编码）

以下颜色用于收支语义区分，**不随主题变化**：

| 用途 | 色值 | 说明 |
|------|------|------|
| 支出标识 | `#FF6B6B` | 红色，用于支出金额、趋势图标 |
| 收入标识 | `#20C997` | 绿色，用于收入金额、趋势图标 |
| 支出背景 | `#FFE8E8` | 浅红，分类头像背景 |
| 收入背景 | `#E8FFF3` | 浅绿，分类头像背景 |

### 2.3 色彩使用规则

1. **主题色通过 CSS 变量引用**：`rgb(var(--v-theme-primary))`、`rgba(var(--v-theme-surface), 0.8)` 等
2. **深色模式文字层级**：
   - 标题（h5/h6/subtitle）：`#FFFFFF`（纯白）
   - 正文（body-1/body-2）：`#E6E1E5`（浅灰白）
   - 副标题/说明（caption）：`#C8C3CE`（中灰）
   - 辅助文字（text-grey）：`#C8C3CE`
   - 占位/禁用文字：`#A0A0A0`
3. **深色模式卡片边框**：`rgba(255, 255, 255, 0.06)`
4. **浅色模式分隔线**：`rgba(0, 0, 0, 0.06)`

---

## 3. 阴影系统

### 3.1 Z 轴层级

通过 CSS 变量统一管理，深色/浅色模式独立定义：

| 层级 | 变量 | 用途 | 浅色模式 | 深色模式 |
|------|------|------|----------|----------|
| Level 0 | — | 背景/底层 | none | none |
| Level 1 | `--shadow-level-1` | 静态卡片 | `0 1px 3px rgba(0,0,0,0.08)` | `0 1px 3px rgba(0,0,0,0.3)` |
| Level 2 | `--shadow-level-2` | 交互元素（按钮、chip） | `0 2px 6px rgba(0,0,0,0.1)` | `0 2px 6px rgba(0,0,0,0.35)` |
| Level 3 | `--shadow-level-3` | 浮层（弹窗、菜单） | `0 8px 24px rgba(0,0,0,0.15)` | `0 8px 24px rgba(0,0,0,0.5)` |
| Hover | `--shadow-hover` | 卡片 hover 态 | `0 4px 12px rgba(0,0,0,0.12)` | `0 4px 12px rgba(0,0,0,0.4)` |

### 3.2 阴影应用规则

| 元素类型 | 阴影层级 | 说明 |
|----------|----------|------|
| `.v-card` | Level 1 | 静态状态 |
| `.v-card:hover` | Hover | 鼠标悬停 |
| `.v-btn:not(.v-btn--icon)` | Level 2 | 非图标按钮 |
| `.v-chip` | `0 1px 2px rgba(0,0,0,0.06)` | 轻量阴影 |
| `.v-dialog > .v-card` | Level 3 | 弹窗 |
| `.v-menu > .v-overlay__content` | Level 3 | 下拉菜单 |
| `.v-bottom-navigation` | `0 -2px 12px rgba(0,0,0,0.1)` | 底部导航（向上投射） |

### 3.3 注意事项

- 图标按钮（`v-btn--icon`）**不加** Level 2 阴影，保持轻量
- outlined variant 输入框**不加**静态阴影，保持简洁
- 阴影不改变元素尺寸和点击热区

---

## 4. 圆角系统

| 元素 | 圆角值 | 说明 |
|------|--------|------|
| `.v-card` | `16px` | 全局默认 |
| `.v-dialog > .v-card` | `20px` | 弹窗更大圆角 |
| `.v-navigation-drawer` | `0 20px 20px 0` | 侧边栏右侧圆角 |
| `.v-navigation-drawer .v-list-item` | `12px` | 导航项 |
| `.v-btn` | `xl` (Vuetify 内置) | 按钮默认 |
| `.v-select` / `.v-text-field` | `lg` | 输入框（通过 props） |
| FAB 按钮 | `16px` | 浮动操作按钮 |

**规则**：优先使用 Vuetify 的 `rounded` prop（`xs`/`sm`/`md`/`lg`/`xl`），仅在需要精确控制时使用 px 值。

---

## 5. 间距与布局

### 5.1 内容区域

| 属性 | 值 | 说明 |
|------|------|------|
| 最大宽度 | `640px` | 通过 `--app-max-width` 变量控制 |
| 居中方式 | `margin: 0 auto` | 页面内容居中 |
| 桌面缩放 | `transform: scale(1.1)` | 桌面端内容区域放大 10% |

### 5.2 卡片间距

| 场景 | 间距 | 实现方式 |
|------|------|----------|
| 卡片之间 | `mb-4` (16px) | Vuetify utility |
| 卡片内部 | `pa-4` (16px) | Vuetify utility |
| 行内元素间距 | `ga-2` (8px) | flex gap |

### 5.3 响应式策略

| 断点 | 布局 | 导航 |
|------|------|------|
| < 960px（移动端） | 单列，padding 减小 | 底部导航栏（`v-bottom-navigation`） |
| ≥ 960px（桌面端） | 居中 640px，scale 1.1 | 侧边栏（`v-navigation-drawer`） |

---

## 6. 字体系统

### 6.1 字体栈

```css
font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
```

### 6.2 字号规范

| 用途 | 字号 | 字重 | 说明 |
|------|------|------|------|
| 大金额数字 | `40px`（桌面）/ `32px`（移动端） | 700 | 月度总额 |
| 金额输入 | `2.5rem` (40px) | 700 | 记账输入框 |
| 详情金额 | `36px` | 700 | 账单详情 |
| 页面标题 | `.page-title` 自定义类：`28px`（列表/设置页）或 `24px`（表单/详情页） | bold | 各页面内容区标题 |
| 顶部栏标题 | Vuetify `text-h6` | bold | AppLayout 顶部 sticky 栏 |
| 卡片标题 | `text-subtitle-2 font-weight-bold` | bold | 设置项、卡片区块标题 |
| 正文 | `text-body-1` / `text-body-2` | regular | 列表内容 |
| 辅助文字 | `.page-subtitle` / `text-caption` / `13px` | regular | 日期、副标题 |

> **注意**：`.page-title` 字号在不同页面存在差异（28px vs 24px），属于待统一项。

### 6.3 金额格式化

- 使用千分位分隔符：`1,234.56`
- 元符号与数字间有空格
- 支出/收入通过颜色区分（红/绿），**同时使用 +/- 前缀**：支出 `-`，收入 `+`

---

## 7. 动画与过渡

### 7.1 全局过渡

```scss
// 基础交互元素平滑过渡
.v-card, .v-list-item, .v-btn {
  transition: all 0.2s ease;
}
```

### 7.2 页面过渡

| 过渡类型 | 名称 | 时长 | 缓动 | 说明 |
|----------|------|------|------|------|
| 普通页面切换 | `page` | 200ms | ease | fade + translateY(10px) |
| 展开详情 | `expand` | 250ms | cubic-bezier(0.4, 0, 0.2, 1) | 从点击位置 scale 展开 |
| 弹窗淡入 | `fade` | 150ms | ease | 纯透明度 |
| 底部弹出 | `slide-up` | 300ms | ease | translateY(100%) → 0 |
| 批量操作栏 | `slideDown` | 200ms | ease | 顶部滑入 |

### 7.3 微交互

| 元素 | 交互 | 效果 | 适用范围 |
|------|------|------|----------|
| `.v-card`（通用） | hover | 阴影变化（Level 1 → Hover） | 全局 `global.scss` |
| `.record-card` | hover | `translateX(2px)` + 边框变为 primary 色 | RecordListPage、DashboardPage |
| `.today-card` | hover | `translateY(-1px)` | DashboardPage |
| 分类 chip | hover | `scale(1.02)` | RecordFormPage |
| FAB 按钮 | hover | `scale(1.05)` + 阴影变为 `0 6px 16px rgba(0,0,0,0.2)` | AppLayout |
| 可点击图标 | click | `v-ripple` 水波纹效果 | 全局 |

> **注意**：`translateX(2px)` 和 `translateY(-11)` 仅用于特定卡片子类（`.record-card`、`.today-card`），通用 `.v-card` hover 仅变化阴影。

### 7.4 过渡时长

全局基础过渡为 `0.2s ease`，但部分 scoped 样式使用 `0.15s ease`（如 `.nav-item`、`.record-card`、`.category-chip`、`.category-list-item`、`.tag-delete-icon`）。两类时长共存，新代码优先使用 `0.2s`。

### 7.5 动画性能规则

1. 优先使用 `transform` 和 `opacity`（GPU 加速），避免动画中改变 `width`/`height`/`margin`/`padding`
2. 动画时长不超过 300ms，微交互不超过 200ms
3. 使用 `requestAnimationFrame` 触发动画，确保首帧渲染
4. 展开动画起始值建议使用 `scale(0.1)` 而非 `scale(0)`，避免内容从完全不可见状态出现（当前 `ExpandTransition` 组件使用 `scale(0)`，`AppLayout` 展开过渡使用 `scale(0.1)`，两处不一致）

---

## 8. 组件规范

### 8.1 全局组件默认值（main.js defaults）

```javascript
VBtn:              { rounded: 'xl' }
VCard:             { rounded: 'xl' }
VTextField:        { variant: 'outlined', density: 'compact' }  // 无 rounded 默认值
VSelect:           { variant: 'outlined', density: 'compact' }  // 无 rounded 默认值
VNavigationDrawer: { rounded: 'xl' }
```

> **注意**：`VTextField` 和 `VSelect` 未设置全局 `rounded` 默认值。如需圆角输入框，需在实例上通过 `rounded="lg"` 等 prop 单独设置。

### 8.2 按钮使用规范

| 场景 | variant | 示例 |
|------|---------|------|
| 主操作 | `elevated`（默认，带阴影） | 提交、保存 |
| 次要操作 | `tonal` | 编辑、删除确认 |
| 文字操作 | `text` | 取消、返回 |
| 图标操作 | `icon` | 顶部栏按钮、关闭 |
| FAB | `icon` + 固定定位 | 快速记账入口 |
| 分段选择 | `v-btn-toggle` | 主题切换、类型切换 |

### 8.3 卡片使用规范

| 场景 | variant | 圆角 | 阴影 |
|------|---------|------|------|
| 内容卡片 | 默认 | 16px | Level 1 |
| 弹窗卡片 | 默认 | 20px | Level 3 |
| 信息展示 | `tonal` | 16px | 无额外阴影 |
| 边框卡片 | `outlined` | 16px | 无阴影 |

### 8.4 输入框规范

- 默认使用 `variant="outlined"` + `density="compact"`
- 大金额输入使用 `variant="plain"` + 自定义字号
- 时间/日期选择使用 `readonly` + 点击弹窗选择
- 自动补全使用 `v-autocomplete` + `no-filter`（手动搜索模式）

### 8.5 列表规范

- 使用 `v-list` + `v-list-item`，设置 `density="compact"`
- 列表项圆角 `12px`
- 列表项默认启用 `v-ripple`（除非有特殊理由禁用）
- 分隔使用 `v-divider`

### 8.6 图标规范

- 图标库：MDI（`mdi-*`）
- 头像图标尺寸：`20px`（40px 头像内）或 `16px`（36px 头像内），根据头像大小调整
- 列表图标尺寸：`20px`
- 按钮图标：使用 `v-icon`，尺寸跟随按钮

---

## 9. 深色模式规范

### 9.1 实现方式

- 通过 Vuetify theme 系统：`<v-app :theme="darkMode ? 'dark' : 'light'">`
- 主题模式持久化到 `localStorage`（key: `money-app-theme-mode`）
- 支持三种模式：`auto`（跟随系统）、`light`、`dark`

### 9.2 适配规则

1. **优先使用 Vuetify 主题变量**：`rgb(var(--v-theme-primary))` 等自动适配
2. **阴影通过 CSS 变量切换**：深色模式下阴影 alpha 值更高
3. **深色模式文字颜色**：通过 `.v-theme--dark` 选择器覆盖（见 global.scss）
4. **硬编码颜色审查**：业务色（支出红/收入绿）保持不变，其他硬编码颜色需评估是否需要深色适配
5. **边框/分隔线**：浅色用 `rgba(0,0,0,0.06)`，深色用 `rgba(255,255,255,0.06)`

### 9.3 深色模式 Checklist

新增组件或页面时，检查以下项目：

- [ ] 文字在深色背景上对比度足够（WCAG AA）
- [ ] 阴影在深色背景上可见
- [ ] 卡片边框使用主题感知的颜色
- [ ] 硬编码的背景色/文字色有深色适配
- [ ] 图标在深色背景上清晰可见

---

## 10. 交互规范

### 10.1 反馈机制

| 交互 | 反馈方式 |
|------|----------|
| 点击按钮 | `v-ripple` 水波纹 + 状态变化 |
| 点击列表项 | `v-ripple` + hover 样式 |
| 点击卡片 | hover translateX/Y 变化 |
| 操作成功 | Toast 通知（`appStore.showToast`） |
| 操作失败 | Toast 通知（error 色） |
| 加载中 | `v-progress-circular` 或 `v-progress-linear` |
| 空状态 | `EmptyState` 组件（图标 + 文字） |
| 危险操作 | `ConfirmDialog` 二次确认 |

### 10.2 导航模式

| 场景 | 导航方式 |
|------|----------|
| 列表 → 详情 | `router.push` + expand transition |
| 详情 → 返回 | `router.back()` + 清除 transition origin |
| 新增记录 | FAB → `/add` 路由 |
| 编辑记录 | 详情页 → `/edit/:id` 路由 |
| 设置项 | 侧边栏/底部导航 → `/settings` |

### 10.3 表单规范

- 脏数据追踪：序列化表单快照，离开时对比
- 离开确认：`onBeforeRouteLeave` 拦截 + `ConfirmDialog`
- 提交按钮：禁用状态（`!canSubmit`），加载状态（`submitting`）
- 标签创建：支持 Enter 快捷创建新标签

---

## 11. 布局架构

### 11.1 页面壳（AppLayout）

```
┌─────────────────────────────────────────┐
│ v-app                                   │
│ ┌──────────┬────────────────────────────┤
│ │ 侧边栏    │ v-main                    │
│ │ (桌面端)  │ ┌────────────────────────┐│
│ │          │ │ 顶部栏 (sticky)         ││
│ │          │ ├────────────────────────┤│
│ │          │ │ 内容区 (max 640px)      ││
│ │          │ │   <router-view>        ││
│ │          │ │                        ││
│ │          │ │                        ││
│ │          │ └────────────────────────┘│
│ └──────────┴────────────────────────────┤
│                              ┌────┐     │
│                              │FAB │     │
│                              └────┘     │
│ ┌──────────────────────────────────────┐│
│ │ 底部导航 (移动端)                      ││
│ └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### 11.2 页面结构模板

每个页面遵循统一结构：

```html
<template>
  <div>
    <!-- 页面标题（可选，桌面端显示） -->
    <div class="d-none d-md-block mb-4">
      <h1 class="page-title">页面标题</h1>
      <p class="page-subtitle">副标题</p>
    </div>

    <!-- 内容区域 -->
    <v-card rounded="xl" class="mb-4">
      <!-- 卡片内容 -->
    </v-card>
  </div>
</template>
```

### 11.3 Store 架构

| Store | 职责 |
|-------|------|
| `useAppStore` | 全局状态：主题、加载、Toast、动画坐标 |
| `useRecordsStore` | 记录数据、筛选条件、批量操作 |
| `useCategoriesStore` | 分类和标签数据 |
| `useStatisticsStore` | 统计数据 |

---

## 12. 文件组织

### 12.1 目录结构

```
frontend/src/
├── api/              # API 请求封装
├── components/
│   ├── common/       # 通用组件（ConfirmDialog, DatePickerPopover, EmptyState 等）
│   └── layout/       # 布局组件（AppLayout）
├── pages/            # 页面组件（与路由一一对应）
├── stores/           # Pinia stores
├── styles/
│   └── global.scss   # 全局样式
├── utils/            # 工具函数
├── router/           # 路由配置
├── App.vue
└── main.js
```

### 12.2 样式文件职责

| 文件 | 职责 | 内容 |
|------|------|------|
| `global.scss` | 全局基础样式 | CSS 变量、阴影系统、过渡动画、深色模式覆盖、滚动条、焦点环 |
| `main.js` Vuetify config | 组件默认值 | rounded、variant、density 等 props 默认值 |
| 各组件 `<style scoped>` | 组件私有样式 | 仅影响当前组件的自定义样式 |

### 12.3 样式优先级

1. Vuetify utility classes（`d-flex`、`mb-4` 等）—— 最优先使用
2. Vuetify component props（`rounded="xl"`、`variant="outlined"` 等）
3. `global.scss` 全局规则 —— 通用基础样式
4. `<style scoped>` —— 组件私有样式，最小化使用

**原则**：能用 Vuetify utility/props 解决的，不写自定义 CSS。

---

## 13. 全局样式细节（global.scss）

### 13.1 滚动条

```scss
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.12); border-radius: 4px; }
```
深色模式：track `rgba(255,255,255,0.1)`，thumb `rgba(255,255,255,0.3)`。

### 13.2 焦点环

```scss
*:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
  border-radius: 4px;
}
```

### 13.3 文本选择高亮

```scss
::selection { background: rgba(var(--v-theme-primary), 0.2); }
```

### 13.4 分类图标圆形

`.category-icon`：`40px × 40px` 圆形，`20px` 字号，flex 居中。

### 13.5 页面副标题

`.page-subtitle`：`13px`，浅色 `rgba(0,0,0,0.45)`，深色 `#C8C3CE`。

### 13.6 金额输入

`.amount-input input`：`2.5rem` 字号，`700` 字重，居中对齐。

---

## 14. 布局壳细节（AppLayout）

### 14.1 侧边栏

- 宽度：`240px`
- 圆角：`0 20px 20px 0`（右侧圆角）
- 边框：`1px solid rgba(0,0,0,0.06)`
- 桌面端：`permanent` 模式，可切换 `rail`（折叠）
- 移动端：`display: none`，使用底部导航替代

### 14.2 顶部栏

- 位置：`sticky`，`z-index` 高于内容
- 底部渐变遮罩：`linear-gradient(transparent, rgb(var(--v-theme-background)))`，高度 `20px`
- 标题：`text-h6`，从 `route.meta.title` 读取
- 副标题：中文日期格式（如"6月7日 星期六"）

### 14.3 内容区

- 最大宽度 `640px`，居中
- 桌面端 `transform: scale(1.1)`，`transform-origin: top center`
- 底部渐变遮罩：`linear-gradient(transparent 70%, rgb(var(--v-theme-background)))`，固定定位

### 14.4 FAB 按钮

- 桌面端：`bottom: 24px; right: 24px`，`56×56px`，`border-radius: 16px`
- 移动端：`bottom: 80px; right: 16px`（避免与底部导航重叠）
- hover：`scale(1.05)`，阴影变为 `0 6px 16px rgba(0,0,0,0.2)`
- 导航目标：`/add`

### 14.5 底部导航

- 仅移动端显示（`v-if="!isDesktop"`）
- 4 个 tab：首页、账单、统计、设置
- 使用 `grow` 属性平分宽度
- 边框：`1px solid rgba(0,0,0,0.06)`（深色模式 `rgba(255,255,255,0.06)`）

---

## 15. 通用组件清单

### 15.1 ConfirmDialog

| 属性 | 值 |
|------|------|
| 最大宽度 | `360px` |
| 圆角 | 继承全局 `16px` |
| 持久化 | `persistent`（点击遮罩不关闭） |
| 用途 | 删除确认、离开确认、恢复默认确认 |

### 15.2 EmptyState

| 属性 | 默认值 |
|------|--------|
| icon | `mdi-inbox-outline` |
| title | "暂无数据" |
| subtitle | "这里还没有内容" |
| actionColor | `primary` |

### 15.3 ToastNotification

- 全局组件，在 `AppLayout` 中引入
- 通过 `appStore.showToast(message, color)` 触发
- 默认颜色 `success`，支持 `error`、`warning` 等

### 15.4 ExpandTransition

| 属性 | 默认值 | 说明 |
|------|--------|------|
| duration | `250ms` | 动画时长 |
| maxWidth | `400` | 弹窗最大宽度 |
| origin | `{ x: 0, y: 0 }` | 展开起点坐标 |

- 基于 `v-dialog` 实现
- 从点击坐标计算 `transform-origin`，`scale(0) → scale(1)` 展开

### 15.5 DatePickerPopover

| 属性 | 说明 |
|------|------|
| modelValue | 日期值（`YYYY-MM-DD`） |
| modelValueTime | 时间值（`HH:mm`） |
| showTime | 是否显示时间选择 |
| label | 输入框标签，默认"选择日期" |

- 日期选择使用 `v-date-picker`
- 弹出方式使用 `ExpandTransition`

---

## 16. 路由配置

- 使用 `createWebHashHistory()`（hash 模式）
- 路由 meta 包含 `title` 字段，用于顶部栏标题显示

---

## 17. 待统一项

以下是当前代码中存在的不一致，后续版本应考虑统一：

| 项目 | 现状 | 建议 |
|------|------|------|
| `.page-title` 字号 | 列表/设置页 28px，表单/详情页 24px | 统一为一个值 |
| 展开动画起始值 | `ExpandTransition` 用 `scale(0)`，`AppLayout` 用 `scale(0.1)` | 统一为 `scale(0.1)` |
| 过渡时长 | 全局 `0.2s`，部分 scoped `0.15s` | 新代码统一用 `0.2s` |
| 统计收入色 | `.stat-value.income` 用 `#69DB7C`，业务色用 `#20C997` | 统一为一个绿色 |
| `rounded` 默认值 | `VTextField`/`VSelect` 无全局 rounded，部分实例用 `lg` | 考虑在 main.js 设默认值 |
