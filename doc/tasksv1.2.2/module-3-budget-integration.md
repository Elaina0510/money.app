# 模块 3：预算管理整合

> 需求编号：#5
> 优先级：高
> 影响范围：前端 AppLayout.vue、SettingsPage.vue、router/index.js

---

## 任务列表

### 3.1 前端 - 移除预算导航入口

- [ ] 从 `AppLayout.vue` 的 `navItems` 数组中移除预算项
- [ ] 确认侧边栏不再显示"预算"入口

### 3.2 前端 - 设置页嵌入预算管理

- [ ] 在 `SettingsPage.vue` 增加预算管理卡片 section
- [ ] 嵌入月度预算概览（总额、进度条、已用百分比）
- [ ] 嵌入分类预算列表（复用 BudgetPage 逻辑）
- [ ] 嵌入添加预算按钮
- [ ] `onMounted` 中增加 `loadBudgets()` 数据加载

### 3.3 前端 - 路由重定向

- [ ] `/budget` 路由重定向到 `/settings`
- [ ] 保留路由配置，确保旧链接可访问

---

## 验收标准

- [ ] 侧边栏无"预算"入口
- [ ] 设置页显示预算管理 section
- [ ] 设置页中可添加/编辑预算
- [ ] 直接访问 `/budget` 路由时重定向到 `/settings`
- [ ] 预算数据不受影响
