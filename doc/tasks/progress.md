# 项目总体进度

> **项目名称**：个人记账程序  
> **目标版本**：V1.0（MVP）  
> **更新日期**：2026年

---

## 模块完成进度

### M0 — 后端基础搭建 ✅ / ❌

- [ ] 项目目录结构初始化
- [ ] 应用入口、配置文件、数据库引擎
- [ ] 统一响应格式与错误码
- [ ] 预设数据初始化

### M1 — 记账管理模块 (CRUD)

- [ ] 数据模型（Record, RecordTag）
- [ ] Pydantic Schema
- [ ] 业务逻辑层（record_service）
- [ ] 路由层（7 个接口）
- [ ] 错误处理与边界校验
- [ ] Swagger 测试通过

### M2 — 分类标签管理模块

- [ ] 数据模型（Category, Tag）
- [ ] Pydantic Schema
- [ ] 预设数据初始化（14 条分类）
- [ ] 业务逻辑层（category_service, tag_service）
- [ ] 路由层（8 个接口）
- [ ] 删除保护逻辑（有关联记录时拒绝删除）
- [ ] Swagger 测试通过

### M3 — 附件管理模块

- [ ] 数据模型（Attachment）
- [ ] Pydantic Schema
- [ ] 文件存储工具（路径生成、类型/大小校验、物理删除）
- [ ] 业务逻辑层（attachment_service）
- [ ] 路由层（4 个接口）
- [ ] 静态文件路由配置
- [ ] 错误处理（格式/大小校验）
- [ ] Swagger 测试通过

### M4 — 统计模块

- [ ] Pydantic Schema（4 种响应结构）
- [ ] 业务逻辑层（statistics_service）
  - [ ] 收支概览（summary）
  - [ ] 分类统计（by-category）
  - [ ] 标签统计（by-tag）
  - [ ] 收支趋势（trend）
- [ ] 路由层（4 个接口）
- [ ] 参数验证与空数据处理
- [ ] Swagger 测试通过

### M5 — 前端 UI 模块

- [ ] 项目初始化（Vite + Vue 3 + Vuetify 3）
- [ ] 基础架构（Router, Axios, Pinia Store）
- [ ] 公共组件（EmptyState, LoadingSpinner, ConfirmDialog, Toast）
- [ ] 布局组件（AppLayout, TopAppBar, BottomNavigation）
- [ ] 首页/仪表盘（DashboardPage）
- [ ] 记账表单页（RecordFormPage）
- [ ] 账单列表页（RecordListPage）
- [ ] 统计页（StatisticsPage）
- [ ] 设置页（SettingsPage）
- [ ] 响应式适配（移动端/平板/桌面）
- [ ] 样式与工具函数
- [ ] 深色模式支持
- [ ] 与后端 API 联调通过

### M6 — 安卓 WebView 封装模块

- [ ] 安卓项目初始化
- [ ] AndroidManifest 配置与权限声明
- [ ] WebView 核心配置
- [ ] JS 桥接接口（相机、相册、Toast、震动）
- [ ] 相机拍照功能实现
- [ ] 前端构建产物集成（dist/ → assets/www/）
- [ ] Material You 主题配置
- [ ] APK 构建与安装验证

---

## 版本里程碑

### V1.0（MVP）

| 里程碑 | 预计完成 | 实际完成 | 说明 |
|--------|---------|---------|------|
| M0 后端基础搭建 | — | — | 基础设施 |
| M2 分类标签管理 | — | — | 基础数据准备 |
| M1 记账 CRUD | — | — | 核心功能 |
| M3 附件管理 | — | — | 核心功能 |
| M4 统计模块 | — | — | 核心功能 |
| M5 前端 UI 模块 | — | — | 用户界面 |
| M6 安卓 WebView | — | — | 安卓封装 |
| 全功能联调测试 | — | — | 全面验证 |

---

## 模块依赖关系

```
M2（分类标签管理） ←── M1（记账管理） ──→ M3（附件管理）
                           ↓
                      M4（统计模块）
                           ↓
                      M5（前端 UI 模块）──→ M6（安卓 WebView 封装）
```

> **开发顺序建议**：
> 1. M0 → M2（先搭好基础框架和基础数据）
> 2. M1（核心记账功能，同时可配合 M2）
> 3. M3（附件功能，可独立开发）
> 4. M4（统计功能，依赖 M1 的数据）
> 5. M5（前端 UI，可先 Mock 数据后与后端联调）
> 6. M6（安卓封装，依赖 M5 构建产物）
