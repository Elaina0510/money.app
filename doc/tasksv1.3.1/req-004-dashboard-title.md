# REQ-004 首页标题栏调整

> **优先级**: P1 · **涉及文件**: DashboardPage.vue, RecordListPage.vue, StatisticsPage.vue, SettingsPage.vue

## 任务清单

### 1. 删除页面内重复标题
- [x] 移除 `DashboardPage.vue` 中的 `<h1>` 标题及 wrapper
- [x] 移除 `RecordListPage.vue` 中的 `<h1 class="page-title">账单</h1>`，保留副标题作为辅助信息
- [x] 移除 `StatisticsPage.vue` 中的 `<h1 class="page-title">统计</h1>`，保留副标题
- [x] 移除 `SettingsPage.vue` 中的 `<h1 class="page-title">设置</h1>`，保留副标题

### 2. 调整内容起始位置
- [x] 确认删除标题后，各页面第一个内容元素的顶部 margin 适当
- [x] 确保不与 AppLayout 顶部栏重叠

### 3. 确认路由 meta 配置
- [x] 确认各路由的 `meta.title` 已正确配置（首页、账单、统计、设置）

### 4. 清理无用 CSS
- [x] 移除各页面中 `.page-header`、`.page-title` 的无用样式

### 5. 测试验收
- [x] 所有主要页面只有一个标题（顶部栏），无重复
- [x] 滚动页面时顶部标题栏始终可见
- [x] 标题栏不遮挡下方内容
- [x] 全部 65 个测试通过
