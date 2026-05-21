# 记账程序 — 详细设计文档 (Detailed Design)

> 版本：v1.0  
> 基于需求文档：doc/proposal.md  
> 技术选型：FastAPI + SQLModel + Vue.js 3 + SQLite  
> 目标版本：V1.0（MVP）

---

## 目录

1. [架构设计](#1-架构设计)
2. [模块划分](#2-模块划分)
3. [模块一：记账管理模块](#3-模块一记账管理模块)
4. [模块二：分类标签管理模块](#4-模块二分类标签管理模块)
5. [模块三：附件管理模块](#5-模块三附件管理模块)
6. [模块四：统计模块](#6-模块四统计模块)
7. [模块五：前端 UI 模块](#7-模块五前端-ui-模块)
8. [模块六：安卓 WebView 封装模块](#8-模块六安卓-webview-封装模块)
9. [数据库设计](#9-数据库设计)
10. [API 接口设计](#10-api-接口设计)
11. [前端项目结构](#11-前端项目结构)
12. [项目目录结构](#12-项目目录结构)
13. [部署与运行](#13-部署与运行)

---

## 1. 架构设计

> **设计决策记录**
> - amount 字段：统一存储正数，由 type 字段（income/expense）区分收入或支出，避免正负数混淆。
> - 标签（tags）：自由输入文本标签，每次记账可输入新内容，不强制复用，同时承担备注功能，无需独立的 note 字段。

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    客户端层 (Client Layer)                     │
│                                                             │
│  ┌───────────────────┐     ┌───────────────────────────┐   │
│  │  浏览器 (PC/手机)  │     │  安卓 App (WebView 封装)   │   │
│  │  Vue.js 3 SPA     │     │  Android WebView + 桥接   │   │
│  └────────┬──────────┘     └──────────┬────────────────┘   │
└───────────┼───────────────────────────┼────────────────────┘
            │           HTTP            │
┌───────────▼───────────────────────────▼────────────────────┐
│                  网关层 (API Gateway)                        │
│          FastAPI 后端 (Python 3.10+)                        │
│  ┌────────────┬────────────┬─────────────┬──────────────┐  │
│  │  记账管理   │ 分类标签管理 │  附件管理    │   统计服务    │  │
│  │  路由      │  路由      │  路由       │   路由       │  │
│  └────────────┴────────────┴─────────────┴──────────────┘  │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│                   数据层 (Data Layer)                        │
│                                                             │
│  ┌────────────────────┐     ┌──────────────────────────┐   │
│  │  SQLite 数据库      │     │  附件文件存储             │   │
│  │  (money.db)        │     │  (uploads/ 目录)         │   │
│  └────────────────────┘     └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术选型明细

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 后端框架 | FastAPI | ≥0.110 | 异步支持，自动生成 API 文档 |
| ORM | SQLModel | ≥0.14 | 基于 SQLAlchemy + Pydantic，与 FastAPI 深度集成 |
| 数据库 | SQLite | 内置 | 文件即数据库，零配置 |
| 数据库驱动 | aiosqlite | ≥0.20 | 异步 SQLite 驱动 |
| 数据验证 | Pydantic | ≥2.0 | FastAPI/SQLModel 内置 |
| 前端框架 | Vue.js 3 | ≥3.4 | Composition API + script setup |
| 前端构建 | Vite | ≥5.0 | 快速开发服务器和构建 |
| 前端路由 | Vue Router | ≥4.0 | SPA 路由 |
| 前端状态管理 | Pinia | ≥2.0 | Vue 3 官方推荐状态管理 |
| UI 组件库 | Vuetify 3 | ≥3.5 | 基于 Material Design 3 的 Vue 组件库 |
| 图表库 | Chart.js | ≥4.0 | 轻量图表，配合 vue-chartjs |
| HTTP 客户端 | Axios | ≥1.6 | 前端请求后端 API |
| 文件上传 | python-multipart | ≥0.0.9 | FastAPI 文件上传支持 |
| 安卓封装 | Android WebView | API 26+ | 原生 WebView 壳 |

> 为什么选 Vuetify 3？
> - 原生 Material Design 3 支持（Material You 风格）
> - Vue 3 原生支持（Composition API）
> - 丰富的组件库（表单、卡片、导航等）
> - 响应式设计，移动端友好

### 1.3 数据流

```
用户操作 → Vue Router 路由 → Vue 页面组件 → Pinia Store（状态管理）
  → Axios HTTP 请求 → FastAPI 路由处理函数 → SQLModel 模型
  → SQLite 数据库 / 文件系统 → JSON 响应 → Vue 渲染 → 用户看到结果
```

---

## 2. 模块划分

### 2.1 模块总览

V1.0 共划分为 **6 个模块**，模块间通过 API 接口交互，保持相互独立：

| 编号 | 模块名称 | 包含功能 | 可独立测试 |
|------|---------|---------|-----------|
| M1 | 记账管理模块 | 记账 CRUD、快速记账、批量删除、筛选查询 | ✅ |
| M2 | 分类标签管理模块 | 分类/标签的增删改查、系统预设数据 | ✅ |
| M3 | 附件管理模块 | 图片上传、查看、删除 | ✅ |
| M4 | 统计模块 | 收支统计、分类统计、趋势数据 | ✅（依赖 M1 数据） |
| M5 | 前端 UI 模块 | 页面组件、路由、状态管理、响应式布局 | ✅ |
| M6 | 安卓 WebView 封装模块 | Android 壳应用、相机调用桥接 | ✅ |

### 2.2 模块依赖关系

```
M2（分类标签管理）←── M1（记账管理）──→ M3（附件管理）
                          ↓
                     M4（统计模块）
                          ↓
                     M5（前端 UI 模块）──→ M6（安卓 WebView 封装）
```

- M2 为 M1 提供分类和标签的数据源
- M1 为 M4 提供记账基础数据
- M5 依赖所有后端 API
- M6 依赖 M5 构建的前端产物

---

## 3. 模块一：记账管理模块 (M1)

### 3.1 概述

记账管理是系统的核心模块，负责账目记录的增删改查、筛选搜索、快速记账等功能。

### 3.2 数据模型

见 [9.1 数据库表设计](#91-数据表一览)。

### 3.3 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/records | 新增记账记录 |
| GET | /api/records | 获取记录列表（支持分页、筛选、排序） |
| GET | /api/records/{id} | 获取单条记录详情（含附件信息） |
| PUT | /api/records/{id} | 编辑单条记录 |
| DELETE | /api/records/{id} | 删除单条记录 |
| POST | /api/records/batch-delete | 批量删除记录 |
| POST | /api/records/quick-add | 快速记账（基于历史记录复用） |

### 3.4 筛选与查询

**查询参数（GET /api/records）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |
| start_date | str | 否 | 开始日期，格式 YYYY-MM-DD |
| end_date | str | 否 | 结束日期，格式 YYYY-MM-DD |
| category_id | int | 否 | 分类 ID 筛选 |
| type | str | 否 | 收入/支出筛选：income / expense |
| tag | str | 否 | 标签关键词筛选 |
| keyword | str | 否 | 全文搜索关键词（搜索标签/分类名等） |
| sort_by | str | 否 | 排序字段：date / amount / created_at |
| sort_order | str | 否 | 排序方向：asc / desc，默认 desc |


**返回结构：**

```json
{
  "items": [
    {
      "id": 1,
      "amount": 25.50,
      "type": "expense",
      "category_id": 3,
      "category_name": "餐饮",
      "tags": ["奶茶", "下午茶"],
      "date": "2026-05-16",
      "attachment_ids": [1, 2],
      "created_at": "2026-05-16T12:30:00"
    }
  ],
  "total": 128,
  "page": 1,
  "page_size": 20,
  "total_pages": 7
}
```

### 3.5 快速记账逻辑

1. 用户点击"快速记账"按钮
2. 后端查询当前用户最近 10 条记录
3. 返回给前端展示为快捷卡片
4. 用户点击某条快捷卡片，自动填充表单
5. 用户确认后提交，创建新记录（日期默认为当天）

### 3.6 边界与错误处理

| 场景 | 处理方式 |
|------|---------|
| 金额为 0 | 拒绝保存，提示"金额不能为 0" |
| 金额超过 99999999.99 | 拒绝保存，提示金额过大 |
| 日期格式错误 | 返回 422 验证错误 |
| 分类 ID 不存在 | 返回 404，提示分类不存在 |
| 批量删除传入空列表 | 返回 400，提示至少选择一条记录 |
| 删除不存在的记录 | 返回 404 |

### 3.7 可独立测试性

测试时可构造 Mock 数据直接调用记账管理模块的路由，不依赖其他模块。测试用例包括：
- 增删改查 CRUD 基本流程
- 各筛选参数的组合查询
- 金额、日期等字段的边界值测试
- 批量删除的正确性验证
- 快速记账的返回结果验证

---

## 4. 模块二：分类标签管理模块 (M2)

### 4.1 概述

提供收入和支出的分类管理以及标签管理。V1.0 中标签仅作为记录的辅助信息，不做统计分析。

### 4.2 系统预设数据

**预设分类：**

| ID | 名称 | 类型 | 图标 | 排序 |
|----|------|------|------|------|
| 1 | 餐饮 | expense | mdi-food | 1 |
| 2 | 交通 | expense | mdi-bus | 2 |
| 3 | 购物 | expense | mdi-cart | 3 |
| 4 | 娱乐 | expense | mdi-gamepad | 4 |
| 5 | 医疗 | expense | mdi-hospital-box | 5 |
| 6 | 居住 | expense | mdi-home | 6 |
| 7 | 通讯 | expense | mdi-cellphone | 7 |
| 8 | 教育 | expense | mdi-school | 8 |
| 9 | 其他支出 | expense | mdi-cash-minus | 99 |
| 10 | 工资 | income | mdi-wallet | 1 |
| 11 | 兼职 | income | mdi-briefcase | 2 |
| 12 | 红包 | income | mdi-gift | 3 |
| 13 | 理财 | income | mdi-finance | 4 |
| 14 | 其他收入 | income | mdi-cash-plus | 99 |

### 4.3 数据模型

见 [9.1 数据库表设计](#91-数据表一览)。

### 4.4 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/categories | 获取所有分类（支持按类型筛选） |
| POST | /api/categories | 新增自定义分类 |
| PUT | /api/categories/{id} | 编辑分类 |
| DELETE | /api/categories/{id} | 删除分类 |
| GET | /api/tags | 获取所有已使用的标签列表 |
| POST | /api/tags | 新增标签 |
| PUT | /api/tags/{id} | 编辑标签名称 |
| DELETE | /api/tags/{id} | 删除标签 |

**获取分筛选参数（GET /api/categories）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | str | 否 | 筛选类型：income / expense，不传则返回全部 |

### 4.5 删除分类的保护逻辑

- 删除分类前检查是否有记账记录关联
- 有关联记录时，返回错误并提示"该分类下有 X 条记录，无法删除"
- 建议用户先修改这些记录的分类

### 4.6 可独立测试性

可直接构造 Mock 数据测试分类标签的增删改查。测试用例：
- 预设数据在首次启动时是否正确初始化
- 分类 CRUD 基本流程
- 删除有关联记录的分类时是否被拒绝
- 标签的自由输入和查询

---

## 5. 模块三：附件管理模块 (M3)

### 5.1 概述

负责记账记录关联的图片附件的上传、查看、删除。图片存储在文件系统中，数据库记录文件路径。

### 5.2 存储设计

- **存储根目录**：项目根目录下的 `uploads/`
- **目录结构**：`uploads/{year}/{month}/{day}/{uuid}.{ext}`
  - 示例：`uploads/2026/05/16/a1b2c3d4.jpg`
- **文件名**：使用 UUID 生成唯一文件名，避免重名冲突
- **支持的格式**：jpg、jpeg、png、gif、webp
- **大小限制**：单文件最大 10MB
- **访问方式**：通过静态文件路由 `/uploads/{path}` 直接访问

### 5.3 数据模型

见 [9.1 数据库表设计](#91-数据表一览)。

### 5.4 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/attachments/upload | 上传附件（返回附件 ID 和 URL） |
| GET | /api/attachments/{id} | 获取附件信息 |
| DELETE | /api/attachments/{id} | 删除附件（同时删除文件） |
| GET | /api/records/{record_id}/attachments | 获取某条记录的所有附件 |

### 5.5 上传流程

```
客户端选择图片 → 调用 POST /api/attachments/upload (multipart/form-data)
  → 后端验证文件类型和大小
  → 生成 UUID 文件名
  → 按日期创建目录
  → 保存文件到 uploads/{date_path}/{uuid}.{ext}
  → 写入附件记录到数据库
  → 返回 { id, filename, url, size, created_at }
```

### 5.6 删除逻辑

- 删除附件时，同时删除物理文件和数据库记录
- 如果记录被删除，其关联的附件也级联删除（后端代码层面处理，SQLite 外键级联可选）

### 5.7 可独立测试性

测试用例：
- 上传合法图片文件，验证返回信息正确
- 上传不支持的格式（如 .exe），验证被拒绝
- 上传超过大小限制的文件，验证被拒绝
- 删除附件后验证文件是否被物理删除
- 不传文件时的错误处理

---

## 6. 模块四：统计模块 (M4)

### 6.1 概述

基于记账数据提供各种统计分析功能，包括收支概览、分类统计、趋势数据等。V1.0 只提供基础统计数据（不含复杂图表）。

### 6.2 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/statistics/summary | 获取收支概览（按日/周/月/年） |
| GET | /api/statistics/by-category | 按分类统计支出 |
| GET | /api/statistics/by-tag | 按标签文本统计（标签为自由输入，故仅做简单计数，供参考） |
| GET | /api/statistics/trend | 收支趋势数据（月度/年度） |

### 6.3 接口详细说明

#### GET /api/statistics/summary

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | str | ✅ | 统计周期：day / week / month / year |
| start_date | str | ✅ | 开始日期 YYYY-MM-DD |
| end_date | str | ✅ | 结束日期 YYYY-MM-DD |

**响应：**

```json
{
  "total_income": 15000.00,
  "total_expense": 8500.50,
  "balance": 6499.50,
  "transaction_count": 42,
  "period": "month",
  "start_date": "2026-05-01",
  "end_date": "2026-05-31"
}
```

#### GET /api/statistics/by-category

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | str | ✅ | expense（仅支出分类统计） |
| start_date | str | ✅ | 开始日期 |
| end_date | str | ✅ | 结束日期 |

**响应：**

```json
{
  "items": [
    { "category_id": 1, "category_name": "餐饮", "icon": "mdi-food", "total": 3200.00, "percentage": 37.6, "count": 45 },
    { "category_id": 2, "category_name": "交通", "icon": "mdi-bus", "total": 800.50, "percentage": 9.4, "count": 12 }
  ],
  "total_expense": 8500.50
}
```

#### GET /api/statistics/by-tag

标签为自由输入文本，此接口对标签按文本内容做分组聚合统计。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | str | ✅ | 开始日期 |
| end_date | str | ✅ | 结束日期 |

**响应：**

```json
{
  "items": [
    { "tag_name": "奶茶", "total": 320.00, "count": 12 },
    { "tag_name": "共享单车", "total": 45.50, "count": 8 }
  ]
}
```

#### GET /api/statistics/trend

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| group_by | str | ✅ | month / year |
| start_date | str | ✅ | 开始日期 |
| end_date | str | ✅ | 结束日期 |

**响应：**

```json
{
  "items": [
    { "period": "2026-01", "income": 12000.00, "expense": 6500.00, "balance": 5500.00 },
    { "period": "2026-02", "income": 15000.00, "expense": 7200.00, "balance": 7800.00 }
  ]
}
```

### 6.4 可独立测试性

测试时需预先构造记账数据（可通过 M1 接口或直接写入数据库）。测试用例：
- 各周期类型的收支汇总计算正确性
- 分类统计百分比计算正确性（总和应为 100%）
- 空数据区间的正确处理（返回 0 而非报错）
- 跨年统计的正确性

---

## 7. 模块五：前端 UI 模块 (M5)

### 7.1 概述

前端是基于 Vue.js 3 + Vuetify 3 的单页应用（SPA），使用 Vite 构建。

**标签输入说明：** 标签采用自由文本输入方式，用户可在记账表单的"标签"输入框中输入任意文本，多个标签用逗号或回车分隔。标签同时承担备注功能，用户可在标签中输入描述性文字（如"公司聚餐、AA制"）。

### 7.2 页面路由设计

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 首页/仪表盘 | 今日概览、最近记录、月度统计卡片 |
| `/add` | 新增记账 | 记账表单 |
| `/edit/:id` | 编辑记账 | 预填表单 |
| `/records` | 账单列表 | 可按日期、分类、标签筛选 |
| `/statistics` | 统计页 | 图表展示 |
| `/settings` | 设置页 | 分类管理、标签管理、数据管理 |

### 7.3 底部导航栏

页面结构采用底部导航（Bottom Navigation），适用于移动端：

| 图标 | 标签 | 路由 |
|------|------|------|
| mdi-home | 首页 | `/` |
| mdi-plus-circle-outline | 记账 | `/add` |
| mdi-format-list-bulleted | 账单 | `/records` |
| mdi-chart-bar | 统计 | `/statistics` |
| mdi-cog | 设置 | `/settings` |

### 7.4 核心组件树

```
App.vue
├── AppLayout.vue (整体布局)
│   ├── TopAppBar.vue (顶部应用栏)
│   ├── BottomNavigation.vue (底部导航)
│   └── <router-view> (路由视图)
│
├── pages/
│   ├── DashboardPage.vue (仪表盘)
│   │   ├── TodaySummaryCard.vue (今日概览卡片)
│   │   ├── MonthlySummaryCard.vue (月度统计卡片)
│   │   └── RecentRecordsList.vue (最近记录列表)
│   │
│   ├── RecordFormPage.vue (记账表单页)
│   │   ├── AmountInput.vue (金额输入)
│   │   ├── CategorySelector.vue (分类选择器)
│   │   ├── TagInput.vue (标签输入，自由输入文本，同时承担备注功能)
│   │   ├── DatePicker.vue (日期选择)
│   │   └── AttachmentUploader.vue (附件上传)
│   │
│   ├── RecordListPage.vue (账单列表)
│   │   ├── RecordFilterBar.vue (筛选栏)
│   │   ├── RecordCard.vue (账单卡片项)
│   │   └── BatchActionBar.vue (批量操作栏)
│   │
│   ├── StatisticsPage.vue (统计页)
│   │   ├── SummaryCards.vue (概览卡片组)
│   │   ├── CategoryPieChart.vue (分类占比饼图)
│   │   └── TrendLineChart.vue (趋势折线图)
│   │
│   └── SettingsPage.vue (设置页)
│       ├── CategoryManager.vue (分类管理)
│       ├── TagManager.vue (标签管理)
│       └── DataManager.vue (数据管理)
│
├── components/common/
│   ├── EmptyState.vue (空状态组件)
│   ├── LoadingSpinner.vue (加载动画)
│   ├── ConfirmDialog.vue (确认对话框)
│   └── ToastNotification.vue (提示通知)
│
└── stores/
    ├── useRecordsStore.js (记账数据状态)
    ├── useCategoriesStore.js (分类标签状态)
    ├── useStatisticsStore.js (统计状态)
    └── useAppStore.js (应用全局状态)
```

### 7.5 状态管理（Pinia Store）

**useRecordsStore：**
- `records` - 当前列表数据
- `currentRecord` - 当前编辑的记录
- `filters` - 当前筛选条件
- `pagination` - 分页信息
- actions: `fetchRecords()`, `createRecord()`, `updateRecord()`, `deleteRecord()`, `batchDelete()`

**useCategoriesStore：**
- `categories` - 所有分类列表
- `tags` - 所有标签列表
- actions: `fetchCategories()`, `fetchTags()`, `createCategory()`, `deleteCategory()`

**useStatisticsStore：**
- `summary` - 收支概览数据
- `categoryStats` - 分类统计数据
- `trendData` - 趋势数据
- actions: `fetchSummary()`, `fetchCategoryStats()`, `fetchTrend()`

**useAppStore：**
- `darkMode` - 深色模式开关
- `loading` - 全局加载状态
- `toast` - 全局提示

### 7.6 响应式设计要点

- 使用 Vuetify 的 Grid 系统（v-row / v-col）实现自适应布局
- 移动端（< 600px）：单列布局，底部导航栏
- 平板端（600~960px）：双列布局，侧边导航或底部导航
- 桌面端（> 960px）：三列布局，侧边导航栏

### 7.7 可独立测试性

前端模块可通过以下方式独立测试：
- 使用 `vite` 开发服务器独立运行，Mock API 数据
- 使用 Vue Test Utils + Vitest 进行组件单元测试
- 使用 Cypress 进行 E2E 测试

---

## 8. 模块六：安卓 WebView 封装模块 (M6)

### 8.1 概述

使用 Android 原生 WebView 将前端网页封装为安卓 App。提供基本的原生功能桥接，如调用相机拍照上传。

### 8.2 项目结构

```
android/
├── app/
│   ├── build.gradle.kts
│   ├── src/
│   │   ├── main/
│   │   │   ├── AndroidManifest.xml
│   │   │   ├── java/com/example/moneyapp/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── WebViewActivity.kt
│   │   │   │   ├── WebAppInterface.kt (JS 桥接接口)
│   │   │   │   └── CameraHelper.kt (相机拍照辅助)
│   │   │   └── res/
│   │   │       ├── layout/activity_main.xml
│   │   │       ├── values/strings.xml
│   │   │       ├── values/themes.xml (Material You 主题)
│   │   │       └── mipmap-*/ (应用图标)
│   │   └── test/
│   └── proguard-rules.pro
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

### 8.3 WebView 配置

```kotlin
// WebViewActivity.kt 关键配置
webView.settings.apply {
    javaScriptEnabled = true
    domStorageEnabled = true
    loadWithOverviewMode = true
    useWideViewPort = true
    builtInZoomControls = false
    displayZoomControls = false
    setSupportZoom(false)
    allowFileAccess = true
    allowContentAccess = true
}

// 加载本地打包的前端资源（优先）或远程地址
webView.loadUrl("file:///android_asset/www/index.html")
// 或开发时加载：webView.loadUrl("http://10.0.2.2:5173")
```

### 8.4 JS 桥接接口（WebAppInterface）

| 方法名 | 前端调用方式 | 说明 |
|--------|-------------|------|
| `takePhoto()` | `window.Android.takePhoto()` | 调用系统相机拍照，返回图片 Base64 |
| `pickFromGallery()` | `window.Android.pickFromGallery()` | 从相册选择图片，返回图片 Base64 |
| `showToast(msg)` | `window.Android.showToast(msg)` | 显示原生 Toast |
| `getAppVersion()` | `window.Android.getAppVersion()` | 获取 App 版本号 |
| `vibrate(ms)` | `window.Android.vibrate(ms)` | 触觉反馈震动 |

### 8.5 相机拍照流程

```
用户点击"拍照"按钮
  → 前端调用 window.Android.takePhoto()
  → 原生启动相机 Intent
  → 拍照完成后返回图片数据（Base64 编码）
  → 前端接收 Base64 数据，创建 FormData
  → 调用 POST /api/attachments/upload 上传
  → 返回附件信息并显示在页面上
```

### 8.6 AndroidManifest 关键权限

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
    android:maxSdkVersion="28" />
```

### 8.7 打包与发布

- 使用 Android Studio 构建 APK
- 前端构建产物（`dist/` 目录）复制到 `app/src/main/assets/www/`
- 支持 debug 模式（加载远程开发服务器地址）和 release 模式（加载本地 assets）

### 8.8 可独立测试性

- 使用 Android Emulator 或真机进行测试
- 无需后端参与，可直接加载任意 URL 测试 WebView 配置
- 相机拍照功能需要在真机或模拟器（带相机模拟）上测试

---

## 9. 数据库设计

### 9.1 数据表一览

| 表名 | 说明 | 模块归属 |
|------|------|---------|
| `records` | 记账记录主表 | M1 |
| `categories` | 分类表 | M2 |
| `tags` | 标签表 | M2 |
| `record_tags` | 记账与标签关联表（多对多） | M1 |
| `attachments` | 附件表 | M3 |

### 9.2 表结构详细设计

#### 9.2.1 categories（分类表）

```sql
CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,              -- 分类名称
    type        TEXT NOT NULL CHECK(type IN ('income', 'expense')),  -- 分类类型
    icon        TEXT NOT NULL DEFAULT 'mdi-cash',  -- Material Design 图标名
    sort_order  INTEGER NOT NULL DEFAULT 0, -- 排序序号
    is_preset   INTEGER NOT NULL DEFAULT 0, -- 是否为系统预设（1=预设，0=自定义）
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE UNIQUE INDEX idx_categories_name_type ON categories(name, type);
```

#### 9.2.2 tags（标签表）

标签为自由输入的文本，每次记账可输入新的标签内容，不强制复用。标签同时承担备注功能，用户可在标签中输入描述性文字（如"公司聚餐、AA制、剩了50"）。

```sql
CREATE TABLE tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,               -- 标签内容（自由输入，不做唯一约束）
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_tags_name ON tags(name);
```

#### 9.2.3 records（记账记录主表）

amount 统一存储正数，由 type 字段（income / expense）区分收入或支出。标签承担备注功能，无需独立的 note 字段。日期 date 为账单日期（YYYY-MM-DD），创建时间 created_at 为用户录入时间（用户可手动修改）。

```sql
CREATE TABLE records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    amount      REAL NOT NULL CHECK(amount > 0),  -- 金额（统一存正数，由 type 区分收入/支出）
    type        TEXT NOT NULL CHECK(type IN ('income', 'expense')),  -- 类型
    category_id INTEGER NOT NULL,           -- 分类 ID
    date        TEXT NOT NULL,              -- 账单日期 YYYY-MM-DD
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),  -- 录入时间（用户可手动修改）
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE INDEX idx_records_date ON records(date);
CREATE INDEX idx_records_category ON records(category_id);
CREATE INDEX idx_records_type ON records(type);
```

#### 9.2.4 record_tags（记账与标签关联表）

```sql
CREATE TABLE record_tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id   INTEGER NOT NULL,
    tag_id      INTEGER NOT NULL,
    FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(record_id, tag_id)
);

CREATE INDEX idx_record_tags_record ON record_tags(record_id);
CREATE INDEX idx_record_tags_tag ON record_tags(tag_id);
```

#### 9.2.5 attachments（附件表）

```sql
CREATE TABLE attachments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id   INTEGER,                    -- 关联的记账记录 ID（可为空，上传时未关联）
    filename    TEXT NOT NULL,              -- 原始文件名
    stored_path TEXT NOT NULL,              -- 存储路径（相对于 uploads/ 目录）
    file_size   INTEGER NOT NULL,           -- 文件大小（字节）
    mime_type   TEXT NOT NULL,              -- MIME 类型
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE SET NULL
);

CREATE INDEX idx_attachments_record ON attachments(record_id);
```

### 9.3 数据库初始化

应用首次启动时自动创建数据库和表结构，并插入预设分类数据。使用 SQLModel 的 `create_all()` 机制。

预设分类数据插入见 [4.2 系统预设数据](#42-系统预设数据)。

---

## 10. API 接口设计

### 10.1 统一规范

- **基础路径**：`/api`
- **请求格式**：JSON（文件上传除外）
- **响应格式**：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

**错误响应：**

```json
{
  "code": 40001,
  "message": "金额不能为 0",
  "data": null
}
```

**错误码规划：**

| 错误码 | 含义 |
|--------|------|
| 0 | 成功 |
| 40001 | 参数验证错误 |
| 40002 | 资源不存在 |
| 40003 | 操作冲突（如删除有关联记录的分类） |
| 40004 | 文件过大或不支持的类型 |
| 50001 | 服务器内部错误 |

### 10.2 API 接口汇总

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| M1 | POST | /api/records | 新增记录 |
| M1 | GET | /api/records | 获取记录列表（分页筛选） |
| M1 | GET | /api/records/{id} | 获取单条记录详情 |
| M1 | PUT | /api/records/{id} | 更新记录 |
| M1 | DELETE | /api/records/{id} | 删除记录 |
| M1 | POST | /api/records/batch-delete | 批量删除 |
| M1 | GET | /api/records/quick-templates | 获取快速记账模板 |
| M2 | GET | /api/categories | 获取分类列表 |
| M2 | POST | /api/categories | 新增分类 |
| M2 | PUT | /api/categories/{id} | 编辑分类 |
| M2 | DELETE | /api/categories/{id} | 删除分类 |
| M2 | GET | /api/tags | 获取标签列表 |
| M2 | POST | /api/tags | 新增标签 |
| M2 | PUT | /api/tags/{id} | 编辑标签 |
| M2 | DELETE | /api/tags/{id} | 删除标签 |
| M3 | POST | /api/attachments/upload | 上传附件 |
| M3 | GET | /api/attachments/{id} | 获取附件信息 |
| M3 | DELETE | /api/attachments/{id} | 删除附件 |
| M3 | GET | /api/records/{id}/attachments | 获取记录的附件列表 |
| M4 | GET | /api/statistics/summary | 收支概览 |
| M4 | GET | /api/statistics/by-category | 分类统计 |
| M4 | GET | /api/statistics/by-tag | 标签统计（按标签文本分组汇总，由于标签为自由输入，此接口仅做简单计数统计） |
| M4 | GET | /api/statistics/trend | 收支趋势（月度/年度） |




---

## 11. 前端项目结构

### 11.1 前端目录结构

```
frontend/
├── index.html                     # HTML 入口
├── vite.config.js                 # Vite 构建配置
├── package.json                   # 依赖管理
├── .env.development               # 开发环境变量
├── .env.production                # 生产环境变量
├── public/
│   ├── favicon.ico
│   └── manifest.json              # PWA 配置
├── src/
│   ├── main.js                    # Vue 应用入口
│   ├── App.vue                    # 根组件
│   ├── router/
│   │   └── index.js               # Vue Router 路由配置
│   ├── stores/
│   │   ├── useRecordsStore.js     # 记账数据状态
│   │   ├── useCategoriesStore.js  # 分类标签状态
│   │   ├── useStatisticsStore.js  # 统计状态
│   │   └── useAppStore.js         # 应用全局状态
│   ├── api/
│   │   ├── request.js             # Axios 实例（基础配置、拦截器）
│   │   ├── records.js             # 记账相关 API 封装
│   │   ├── categories.js          # 分类相关 API 封装
│   │   ├── tags.js                # 标签相关 API 封装
│   │   ├── attachments.js         # 附件相关 API 封装
│   │   └── statistics.js          # 统计相关 API 封装
│   ├── components/
│   │   ├── common/                # 公共组件
│   │   │   ├── EmptyState.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   ├── ConfirmDialog.vue
│   │   │   └── ToastNotification.vue
│   │   ├── layout/
│   │   │   ├── AppLayout.vue
│   │   │   ├── TopAppBar.vue
│   │   │   └── BottomNavigation.vue
│   │   └── ...
│   ├── pages/
│   │   ├── DashboardPage.vue
│   │   ├── RecordFormPage.vue
│   │   ├── RecordListPage.vue
│   │   ├── StatisticsPage.vue
│   │   └── SettingsPage.vue
│   ├── composables/
│   │   ├── useTheme.js
│   │   └── useCamera.js
│   ├── utils/
│   │   ├── format.js
│   │   └── constants.js
│   └── styles/
│       ├── variables.scss
│       └── global.scss
└── dist/
```

### 11.2 Vite 配置要点

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
  plugins: [vue(), vuetify()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true }
    }
  },
  build: { outDir: 'dist' }
})
```

### 11.3 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| VITE_API_BASE_URL | API 基础路径 | /api |
| VITE_APP_TITLE | 应用标题 | 记账本 |
| VITE_ANDROID_MODE | 是否在安卓 WebView 中运行 | false |

### 11.4 Mock API 方案

开发前端时如果后端未就绪，采用以下方式 Mock：

1. **Pinia Store 预设数据**：在 Store 初始状态中硬编码演示数据（推荐 V1.0 使用）
2. **vite-plugin-mock**：在 Vite 开发服务器中拦截 API 请求
3. **MSW (Mock Service Worker)**：在浏览器端拦截请求

---

## 12. 项目目录结构（完整项目）

### 12.1 根目录结构

```
money-app/
├── backend/                       # Python 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI 应用入口
│   │   ├── config.py              # 配置
│   │   ├── database.py            # 数据库引擎和会话管理
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── record.py
│   │   │   ├── category.py
│   │   │   ├── tag.py
│   │   │   └── attachment.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── record.py
│   │   │   ├── category.py
│   │   │   ├── tag.py
│   │   │   ├── attachment.py
│   │   │   └── statistics.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── records.py
│   │   │   ├── categories.py
│   │   │   ├── tags.py
│   │   │   ├── attachments.py
│   │   │   └── statistics.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── record_service.py
│   │   │   ├── category_service.py
│   │   │   ├── tag_service.py
│   │   │   ├── attachment_service.py
│   │   │   └── statistics_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_utils.py
│   │       └── response.py
│   ├── uploads/
│   ├── money.db
│   ├── requirements.txt
│   └── .env
├── frontend/                      # Vue.js 前端
├── android/                       # 安卓 WebView 壳
├── docs/
│   ├── proposal.md
│   └── detailed-design.md
├── .gitignore
└── README.md
```

### 12.2 代码分层说明

| 层 | 目录 | 职责 |
|----|------|------|
| 路由层 | routers/ | HTTP 路由定义，参数解析，调用 service |
| 业务层 | services/ | 核心业务逻辑，数据库操作封装 |
| 数据模型 | models/ | SQLModel ORM 模型 |
| 数据模式 | schemas/ | Pydantic 请求/响应模型 |
| 工具层 | utils/ | 通用工具函数 |

### 12.3 分层调用规则

```
router -> service -> model -> database
```

- router 层不直接操作数据库
- service 层不直接处理 HTTP 请求
- 各 service 之间可通过依赖注入相互调用

---

## 13. 部署与运行

### 13.1 开发环境

**后端启动：**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API 文档自动生成于 http://localhost:8000/docs 。

**前端启动：**
```bash
cd frontend
npm install
npm run dev
```
前端开发服务器运行于 http://localhost:5173，API 通过 Vite proxy 代理到后端。

### 13.2 生产环境部署

采用前后端合并部署：将前端构建产物放到 FastAPI 静态文件目录，由 FastAPI 统一提供。

**步骤：**
```bash
cd frontend && npm run build
cp -r frontend/dist/* backend/app/static/
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**FastAPI 配置：**
```python
app.mount('/', StaticFiles(directory='app/static', html=True), name='static')
```

### 13.3 安卓 WebView

- 调试模式：webView.loadUrl('http://<PC_IP>:5173')
- 发布模式：webView.loadUrl('file:///android_asset/www/index.html')
- 构建时将 frontend/dist/ 复制到 android/app/src/main/assets/www/

### 13.4 数据存储位置

| 数据 | 存储位置 |
|------|---------|
| 数据库 | backend/money.db |
| 附件图片 | backend/uploads/ |
| 前端产物 | backend/app/static/ |

### 13.5 备份与迁移

- 备份：直接复制 money.db 和 uploads/ 目录
- 迁移：拷贝数据库和附件目录到新设备
- 恢复：替换对应文件后重启应用

### 13.6 启动脚本

**Windows (start.bat)：**
```batch
@echo off
cd /d %~dp0backend
start uvicorn app.main:app --host 0.0.0.0 --port 8000
start http://localhost:8000
```

**macOS/Linux (start.sh)：**
```bash
#!/bin/bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
open http://localhost:8000
```
