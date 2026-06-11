# REQ-004 首页标题栏调整

> **优先级**: P1 · **涉及文件**: DashboardPage.vue, router/index.js

## 任务清单

### 1. 删除页面内重复标题
- [x] 移除 `DashboardPage.vue` 模板中的 `<h1 class="page-title">首页</h1>` 及其外层 wrapper div（`d-none d-md-block mb-4`）

### 2. 调整内容起始位置
- [x] 确认删除标题后，第一个内容元素（月度 Hero Card）的顶部 margin 适当
- [x] 确保不与 AppLayout 顶部栏重叠

### 3. 确认路由 meta 配置
- [x] 确认 `/` 路由的 `meta.title` 为 `'首页'`

### 4. 测试验收
- [ ] 首页只有一个标题（顶部栏），无重复
- [ ] 滚动页面时顶部标题栏始终可见
- [ ] 标题栏不遮挡下方第一个卡片
- [ ] 切换其他页面，标题栏位置保持一致
