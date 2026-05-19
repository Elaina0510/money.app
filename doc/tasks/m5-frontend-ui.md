# 模块五：前端 UI 模块 (M5) — 任务分解

> **对应需求**：全部前端页面  
> **前置依赖**：后端 API 全部或部分就绪（可用 Mock 数据替代）  
> **预估工时**：8-12小时

## 任务清单

### 1. 项目初始化

- [ ] 使用 Vite 创建 Vue 3 项目 `frontend/`
- [ ] 安装依赖：`vue-router`, `pinia`, `vuetify`, `axios`, `chart.js`, `vue-chartjs`, `@mdi/font`
- [ ] 配置 `vite.config.js`（端口 5173，代理 `/api` 和 `/uploads` 到后端）
- [ ] 配置 `.env.development` 和 `.env.production`
- [ ] 创建 `src/main.js` — 注册 Vue App、Router、Pinia、Vuetify

### 2. 基础架构

- [ ] 创建 `src/router/index.js` — 路由配置（/, /add, /edit/:id, /records, /statistics, /settings）
- [ ] 创建 `src/api/request.js` — Axios 实例（基础 URL、响应拦截器、统一错误处理）
- [ ] 创建 `src/api/records.js` — 记账 API 封装
- [ ] 创建 `src/api/categories.js` — 分类 API 封装
- [ ] 创建 `src/api/tags.js` — 标签 API 封装
- [ ] 创建 `src/api/attachments.js` — 附件 API 封装
- [ ] 创建 `src/api/statistics.js` — 统计 API 封装

### 3. Pinia Store

- [ ] 创建 `src/stores/useRecordsStore.js`（records, currentRecord, filters, pagination, actions）
- [ ] 创建 `src/stores/useCategoriesStore.js`（categories, tags, actions）
- [ ] 创建 `src/stores/useStatisticsStore.js`（summary, categoryStats, trendData, actions）
- [ ] 创建 `src/stores/useAppStore.js`（darkMode, loading, toast）

### 4. 公共组件

- [ ] 创建 `src/components/common/EmptyState.vue` — 空状态组件（含 Material You 风格插画提示）
- [ ] 创建 `src/components/common/LoadingSpinner.vue` — 加载动画
- [ ] 创建 `src/components/common/ConfirmDialog.vue` — 确认对话框（删除/清空数据等二次确认）
- [ ] 创建 `src/components/common/ToastNotification.vue` — 提示通知组件

### 5. 布局组件

- [ ] 创建 `src/components/layout/AppLayout.vue` — 整体布局容器
- [ ] 创建 `src/components/layout/TopAppBar.vue` — 顶部应用栏（标题 + 深色模式切换）
- [ ] 创建 `src/components/layout/BottomNavigation.vue` — 底部导航栏（首页、记账、账单、统计、设置）

### 6. 首页/仪表盘 (DashboardPage)

- [ ] 创建 `src/pages/DashboardPage.vue`
- [ ] 创建 `TodaySummaryCard.vue` — 今日收支概览卡片
- [ ] 创建 `MonthlySummaryCard.vue` — 月度统计卡片
- [ ] 创建 `RecentRecordsList.vue` — 最近 5 条记录列表
- [ ] 集成数据：调取统计接口和记账列表接口

### 7. 记账表单页 (RecordFormPage)

- [ ] 创建 `src/pages/RecordFormPage.vue`（同时兼容新增和编辑模式 `/add` 和 `/edit/:id`）
- [ ] 创建 `AmountInput.vue` — 金额输入组件（数字键盘友好，两位小数）
- [ ] 创建 `CategorySelector.vue` — 分类选择器（区分收入/支出 tab，图标展示）
- [ ] 创建 `TagInput.vue` — 标签输入组件（自由文本输入，逗号/回车分隔，同时承担备注功能）
- [ ] 创建 `DatePicker.vue` — 日期选择组件（默认当天）
- [ ] 创建 `AttachmentUploader.vue` — 附件上传组件（上传预览、删除）
- [ ] 集成快速记账功能：显示最近模板供一键填充

### 8. 账单列表页 (RecordListPage)

- [ ] 创建 `src/pages/RecordListPage.vue`
- [ ] 创建 `RecordFilterBar.vue` — 筛选栏（日期范围、分类、类型、关键词搜索）
- [ ] 创建 `RecordCard.vue` — 账单卡片项（金额、分类图标、标签、日期）
- [ ] 创建 `BatchActionBar.vue` — 批量操作栏（全选、批量删除）
- [ ] 实现分页加载（滚动加载或点击"加载更多"）

### 9. 统计页 (StatisticsPage)

- [ ] 创建 `src/pages/StatisticsPage.vue`
- [ ] 创建 `SummaryCards.vue` — 概览卡片组（总收入、总支出、结余）
- [ ] 创建 `CategoryPieChart.vue` — 分类占比饼图（使用 Chart.js）
- [ ] 创建 `TrendLineChart.vue` — 收支趋势折线图
- [ ] 实现时间周期切换（月/年）

### 10. 设置页 (SettingsPage)

- [ ] 创建 `src/pages/SettingsPage.vue`
- [ ] 创建 `CategoryManager.vue` — 分类管理（列表展示、新增、编辑、删除，预设分类不可删）
- [ ] 创建 `TagManager.vue` — 标签管理（列表展示、编辑、删除）
- [ ] 创建 `DataManager.vue` — 数据管理（导出 CSV/Excel、备份恢复、一键清空（二次确认））

### 11. 样式与工具

- [ ] 创建 `src/styles/variables.scss` — Vuetify 主题变量覆盖（Material You 配色）
- [ ] 创建 `src/styles/global.scss` — 全局样式（圆角、阴影、过渡动画）
- [ ] 创建 `src/utils/format.js` — 格式化工具（金额格式化、日期格式化、文件大小格式化）
- [ ] 创建 `src/utils/constants.js` — 常量定义（分类预设图标映射、错误码映射）

### 12. 响应式适配

- [ ] 移动端（< 600px）：单列布局 + 底部导航
- [ ] 平板端（600~960px）：双列布局
- [ ] 桌面端（> 960px）：侧边栏导航或更大的布局
- [ ] 触摸友好的输入控件（大按钮、大输入框）

### 13. Mock 数据（可选，用于后端未就绪时独立开发前端）

- [ ] 在 Pinia Store 中预设演示数据
- [ ] 或配置 vite-plugin-mock 拦截请求
- [ ] 或使用 MSW 浏览器端拦截

### 14. 验证与测试

- [ ] 启动前端开发服务器 `npm run dev`，确认页面正常渲染
- [ ] 测试所有页面路由可正常访问
- [ ] 测试记账表单的创建和编辑流程
- [ ] 测试账单列表的筛选和搜索
- [ ] 测试统计页面图表渲染
- [ ] 测试响应式布局在不同屏幕尺寸下的表现
- [ ] 测试深色模式切换
