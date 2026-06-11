# Money App v1.3.1 总体进度

> 按建议实施顺序排列，优先级 P1 在前

## 模块完成状态

- [x] [REQ-008 深色/浅色模式自动切换](req-008-theme-auto.md) — P1 · 独立模块，影响全局主题基础
- [x] [REQ-004 首页标题栏调整](req-004-dashboard-title.md) — P1 · 独立模块，改动最小
- [x] [REQ-001 账单详情页展开动画](req-001-expand-animation.md) — P1 · 独立模块，需仔细调试动画参数
- [x] [REQ-003 全局阴影与层级设计](req-003-shadow-elevation.md) — P2 · 独立模块，影响所有页面视觉
- [x] [REQ-002 账单页筛选列表UI优化](req-002-filter-ui.md) — P2 · 独立模块，视觉优化
- [x] [REQ-005 图标水波纹涟漪动效](req-005-ripple-effect.md) — P2 · 独立模块，影响多个页面
- [x] [REQ-006 日期时间栏布局调整](req-006-datetime-layout.md) — P2 · 与 REQ-007 共享组件，建议一起实施
- [x] [REQ-007 时间选择器UI优化](req-007-time-picker.md) — P2 · 与 REQ-006 共享组件，建议一起实施

## 统计

| 状态 | 数量 |
|------|------|
| 未开始 | 0 |
| 进行中 | 0 |
| 已完成 | 8 |

## 修改文件索引

| 文件 | 涉及 REQ |
|------|----------|
| `frontend/src/stores/useAppStore.js` | 001, 008 |
| `frontend/src/components/layout/AppLayout.vue` | 001, 005, 008 |
| `frontend/src/pages/RecordListPage.vue` | 001, 002, 005 |
| `frontend/src/pages/RecordDetailPage.vue` | 001 |
| `frontend/src/pages/DashboardPage.vue` | 004, 005 |
| `frontend/src/pages/SettingsPage.vue` | 005, 008 |
| `frontend/src/pages/RecordFormPage.vue` | 006 |
| `frontend/src/components/common/DatePickerPopover.vue` | 006, 007 |
| `frontend/src/styles/global.scss` | 003 |
| `frontend/src/router/index.js` | 004 |
