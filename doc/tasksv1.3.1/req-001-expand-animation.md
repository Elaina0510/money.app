# REQ-001 账单详情页展开动画

> **优先级**: P1 · **涉及文件**: AppLayout.vue, RecordListPage.vue, RecordDetailPage.vue, useAppStore.js

## 任务清单

### 1. 修改 AppLayout.vue onEnter 钩子
- [x] 读取 `appStore.transitionOrigin` 获取点击坐标
- [x] 将视口坐标映射到 el 的相对坐标（百分比）
- [x] 设置 `transformOrigin` 为映射后的坐标
- [x] 初始状态：`scale(0.1)`, `opacity(0)`, `transition: none`
- [x] `requestAnimationFrame` 中设置过渡：`transform 250ms cubic-bezier(0.4, 0, 0.2, 1), opacity 250ms ease`
- [x] 目标状态：`scale(1)`, `opacity(1)`
- [x] 监听 `transitionend` 事件调用 `done`（`{ once: true }`）

### 2. 修改 AppLayout.vue onLeave 钩子
- [x] 设置离开动画：`scale(1) → scale(0.95)`, `opacity(1) → 0`, `duration 200ms ease`
- [x] 确保 `transformOrigin` 与 enter 一致

### 3. 验证已有逻辑无需改动
- [x] 确认 `RecordListPage.goToDetail()` 已正确写入 `transitionOrigin`
- [x] 确认 `RecordDetailPage.handleBack()` 已清除 `transitionOrigin`
- [x] 确认 `useAppStore.js` 的 `transitionOrigin` getter/setter 满足需求

### 4. 测试验收
- [ ] 在列表不同位置点击，动画起始点跟随点击位置
- [ ] 快速连续点击不同条目，无残影或闪烁
- [ ] 375px / 768px / 1440px 宽度下动画表现一致
- [ ] 从详情页返回时有反向收束效果
