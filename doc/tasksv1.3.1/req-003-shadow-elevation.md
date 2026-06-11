# REQ-003 全局阴影与层级设计

> **优先级**: P2 · **涉及文件**: global.scss

## 任务清单

### 1. CSS 变量定义（`:root`）
- [x] 新增 `--shadow-level-1: 0 1px 3px rgba(0, 0, 0, 0.08)`
- [x] 新增 `--shadow-level-2: 0 2px 6px rgba(0, 0, 0, 0.1)`
- [x] 新增 `--shadow-level-3: 0 8px 24px rgba(0, 0, 0, 0.15)`
- [x] 新增 `--shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.12)`

### 2. 卡片静态阴影
- [x] `.v-card` 应用 `box-shadow: var(--shadow-level-1)`
- [x] `.v-card:hover` 应用 `box-shadow: var(--shadow-hover)`
- [x] 保留已有的深色模式 `.v-theme--dark .v-card` border-color

### 3. 交互元素阴影
- [x] `.v-btn:not(.v-btn--icon)` 应用 `var(--shadow-level-2)`
- [x] `.v-chip` 应用 `0 1px 2px rgba(0, 0, 0, 0.06)`
- [x] 确认 outlined variant 输入框不加静态阴影

### 4. 浮层阴影
- [x] `.v-dialog > .v-card` 应用 `var(--shadow-level-3)`
- [x] `.v-menu > .v-overlay__content` 应用 `var(--shadow-level-3)`
- [x] `.v-bottom-navigation` 应用 `0 -2px 12px rgba(0, 0, 0, 0.1)`

### 5. 深色模式阴影覆盖
- [x] `.v-theme--dark` 下重新定义四个 CSS 变量（更深的阴影值）

### 6. 测试验收
- [ ] 所有卡片在非 hover 状态下有轻微阴影
- [ ] 各类按钮（tonal、elevated、flat）阴影符合层级
- [ ] v-dialog 弹出时阴影明显重于普通卡片
- [ ] 深色模式下阴影可见且不突兀
- [ ] 阴影不改变元素尺寸和点击热区
