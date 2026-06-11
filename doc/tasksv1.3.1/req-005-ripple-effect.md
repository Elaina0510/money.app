# REQ-005 图标水波纹涟漪动效

> **优先级**: P2 · **涉及文件**: AppLayout.vue, DashboardPage.vue, RecordListPage.vue, SettingsPage.vue

## 任务清单

### 1. 确认全局 v-ripple 指令已注册
- [x] 检查 `main.js` 中 `vuetify/directives` 已包含 `v-ripple`

### 2. DashboardPage.vue — 记录条目 avatar
- [x] 记录条目已被 `v-list-item` 包裹（自带 ripple），无需额外处理

### 3. RecordListPage.vue — 账单列表条目 avatar
- [x] 已有 `v-list-item` 包裹，自带 ripple

### 4. AppLayout.vue — 侧边栏导航项
- [x] 移除侧边栏 `v-list-item` 上的 `:ripple="false"` 属性（两处：导航列表和设置项）
- [x] 确认 FAB `v-btn` 已有 ripple（Vuetify 默认启用）

### 5. SettingsPage.vue — 操作按钮
- [x] 确认分类列表项的 edit/delete `v-btn` 已有 ripple（Vuetify 默认启用）
- [x] 确认标签 close 按钮已有 ripple

### 6. 测试验收
- [ ] 点击各页面可点击图标，观察涟漪效果
- [ ] 在图标不同位置点击，涟漪起始点跟随点击位置
- [ ] 涟漪不超出图标/按钮边界
- [ ] 涟漪动画不影响点击响应速度
- [ ] hover 效果保持现状不变
