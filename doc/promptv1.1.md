# 💰 Money App v1.1 - 预算管理 + 图片附件 + 体验优化

## 一、Prompt 概述

### 1.1 目标版本
**V1.1** — 在 V1.0 基础上新增预算管理、图片附件、数据统计优化三大模块。

### 1.2 技术栈
- **后端**：FastAPI + SQLModel + SQLite (aiosqlite) + Python 3.12
- **前端**：Vue.js 3 (Composition API) + Vuetify 3 + Pinia + Vue Router 4
- **测试**：pytest + pytest-asyncio + httpx
- **代码质量**：mypy (严格模式) + ruff (零警告)

### 1.3 现有项目结构

```
backend/
├── app/
│   ├── main.py                  # FastAPI 主入口
│   ├── database.py              # 数据库引擎与会话管理
│   ├── config.py                # 配置（DATABASE_URL, UPLOAD_DIR 等）
│   ├── models/                  # SQLModel 数据模型
│   │   ├── record.py            # 记录模型
│   │   ├── category.py          # 分类模型
│   │   ├── tag.py               # 标签模型
│   │   ├── record_tag.py        # 记录-标签关联表
│   │   ├── attachment.py        # 附件模型
│   │   └── __init__.py
│   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── record.py
│   │   ├── category.py
│   │   ├── tag.py
│   │   ├── statistics.py
│   │   ├── attachment.py
│   │   └── __init__.py
│   ├── services/                # 业务逻辑层
│   │   ├── record_service.py
│   │   ├── category_service.py
│   │   ├── tag_service.py
│   │   ├── attachment_service.py
│   │   ├── statistics_service.py
│   │   └── __init__.py
│   ├── routers/                 # API 路由
│   │   ├── records.py
│   │   ├── categories.py
│   │   ├── tags.py
│   │   ├── attachments.py
│   │   ├── statistics.py
│   │   └── __init__.py
│   └── utils/
│       ├── response.py          # 统一响应格式
│       ├── file_utils.py        # 文件工具
│       └── __init__.py
├── tests/
│   ├── conftest.py              # 测试配置（SQLite 内存数据库）
│   ├── test_records.py
│   ├── test_categories.py
│   ├── test_tags.py
│   ├── test_statistics.py
│   ├── test_attachments.py
│   └── __init__.py
├── pyproject.toml               # pytest 配置
├── requirements.txt
└── money.db                     # 现有 SQLite 数据库文件

frontend/
├── src/
│   ├── main.js                  # Vue 入口
│   ├── App.vue
│   ├── router/index.js          # 路由定义
│   ├── api/                     # API 请求封装
│   │   ├── request.js           # Axios 实例（拦截器处理统一响应）
│   │   ├── records.js
│   │   ├── categories.js
│   │   ├── tags.js
│   │   ├── attachments.js
│   │   └── statistics.js
│   ├── stores/                  # Pinia 状态管理
│   │   ├── useAppStore.js
│   │   ├── useRecordsStore.js
│   │   ├── useCategoriesStore.js
│   │   └── useStatisticsStore.js
│   ├── pages/                   # 页面组件
│   │   ├── DashboardPage.vue    # 首页
│   │   ├── RecordListPage.vue   # 账单列表
│   │   ├── RecordFormPage.vue   # 记账表单
│   │   ├── StatisticsPage.vue   # 统计页面
│   │   ├── BudgetPage.vue       # 预算页面（空壳）
│   │   └── SettingsPage.vue     # 设置页面
│   ├── components/
│   │   ├── layout/AppLayout.vue # 主布局（导航、FAB）
│   │   ├── common/ConfirmDialog.vue
│   │   ├── common/EmptyState.vue
│   │   ├── common/LoadingSpinner.vue
│   │   └── common/ToastNotification.vue
│   ├── styles/
│   │   ├── variables.scss
│   │   └── global.scss
│   └── utils/
│       ├── constants.js
│       └── format.js            # formatAmount, formatDate 等工具
├── package.json
└── vite.config.js
```

### 1.4 版本管理说明

**现有分支**：`master`（v1.0 已发布代码）
**新分支**：基于 master 创建 `feature-v1.1` 分支

### 1.5 关于现有数据库

项目中存在 `backend/money.db`（现有 SQLite 数据文件）。  
V1.1 新增的 `budgets` 表需要通过**自动化迁移脚本**创建。  
**方案**：在 `app/database.py` 中扩展 `create_all_tables()`，利用 SQLModel 的 `SQLModel.metadata.create_all` 会自动创建不存在的表，既有的表不会受影响。

---

## 二、主 Agent 工作流（Master Agent Orchestration）

### 2.1 主 Agent 职责

1. **创建 feature-v1.1 分支**：基于 master 创建
2. **分解任务并分配子 Agent**：按模块分为 5 个子 Agent
3. **协调子 Agent 通信**：确保模块间接口一致
4. **集成验证**：合并所有子任务后运行完整测试套件
5. **质量把关**：确保 pytest 通过、mypy 严格模式通过、ruff 零警告

### 2.2 任务分解结构

```
主 Agent（Master Agent）
│
├── 阶段 0：环境准备与数据库迁移
│   ├── 创建 feature-v1.1 分支
│   ├── 配置 mypy（pyproject.toml 添加 mypy 配置）
│   ├── 配置 ruff（pyproject.toml 添加 ruff 配置）
│   └── 数据库迁移准备
│
├── 阶段 1：子 Agent #1 — 后端预算管理模块（M0 Budget）
│   ├── 创建 models/budget.py（预算数据模型）
│   ├── 创建 schemas/budget.py（预算请求/响应 Schema）
│   ├── 创建 services/budget_service.py（预算业务逻辑）
│   ├── 创建 routers/budgets.py（预算 API 路由）
│   ├── 修改 routers/statistics.py（收支对比接口）
│   └── 创建 tests/test_budgets.py（单元测试）
│
├── 阶段 2：子 Agent #2 — 后端图片附件增强（M0 Attachment Enhancement）
│   ├── 修改 services/attachment_service.py
│   ├── 修改 routers/attachments.py
│   └── 修改 tests/test_attachments.py
│
├── 阶段 3：子 Agent #3 — 后端数据统计扩展（M0 Statistics Enhancement）
│   ├── 修改 services/statistics_service.py
│   ├── 修改 routers/statistics.py
│   └── 修改 tests/test_statistics.py
│
├── 阶段 4：子 Agent #4 — 前端预算页面（M5 Budget UI）
│   ├── 修改 BudgetPage.vue（从空壳到完整页面）
│   ├── 修改 api/statistics.js（新增预算相关 API 调用）
│   ├── 修改 stores/useStatisticsStore.js（新增预算状态管理）
│   └── 修改 router/index.js（如有需要）
│
├── 阶段 5：子 Agent #5 — 前端体验优化（M5 UX Enhancement）
│   ├── 修改 RecordFormPage.vue（图片上传功能）
│   ├── 修改 RecordListPage.vue（图片缩略图显示）
│   ├── 修改 RecordDetailPage.vue（新建详情页）
│   ├── 修改 DashboardPage.vue（预算概览卡片）
│   ├── 修改 StatisticsPage.vue（日/周粒度和预算对比）
│   └── 新增组件（图片预览、详情弹窗等）
│
└── 阶段 6：集成验证
    ├── 运行 pytest backend/tests/ -v（全部通过）
    ├── 运行 mypy backend/app/ --strict（无错误）
    ├── 运行 ruff check backend/app/（无警告）
    └── 人工验收 checklist
```

### 2.3 质量要求

| 工具 | 要求 | 命令 |
|------|------|------|
| **pytest** | 每个模块必须有完整单元测试，覆盖率 > 90% | `pytest backend/tests/ -v` |
| **mypy** | 严格模式通过 | `mypy backend/app/ --strict` |
| **ruff** | 零警告通过 | `ruff check backend/app/` |

### 2.4 子 Agent 协作规则

1. **接口契约**：子 Agent 必须遵循本文档定义的接口规范
2. **错误处理**：子 Agent 生成的代码有 bug → 主 Agent 指出具体错误并要求修复
3. **测试失败**：→ 要求子 Agent 修复直到通过
4. **mypy/ruff 不通过**：→ 要求子 Agent 修复类型注释和代码风格
5. **模块间接口不一致**：→ 主 Agent 协调两个子 Agent 统一接口
6. **偏离设计**：→ 主 Agent 引用本详细设计文档纠正

---

## 三、详细设计文档

### 模块 M0 — 预算管理（Budget）

#### 3.1 数据模型

**表名**：`budgets`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 主键 |
| category_id | INTEGER | FK → categories.id, NOT NULL | 关联分类 |
| month | TEXT | NOT NULL, 格式 YYYY-MM | 预算月份 |
| amount | REAL | NOT NULL, > 0, ≤ 99999999.99 | 预算金额 |
| created_at | TEXT | NOT NULL, 默认当前时间 | 创建时间 |
| updated_at | TEXT | NOT NULL, 默认当前时间 | 更新时间 |

**唯一约束**：`(category_id, month)` 联合唯一

#### 3.2 API 接口

##### 3.2.1 预算 CRUD

**GET /api/budgets** — 获取预算列表

Query 参数：
- `month` (string, 格式 YYYY-MM, 必填) — 查询月份
- `type` (string, 可选: income/expense) — 按类型筛选

Response：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "category_id": 3,
      "category_name": "餐饮",
      "type": "expense",
      "month": "2026-06",
      "amount": 2000.00,
      "spent": 1250.50,
      "remaining": 749.50,
      "percentage": 62.5,
      "created_at": "2026-06-01 00:00:00",
      "updated_at": "2026-06-01 00:00:00"
    }
  ]
}
```

**POST /api/budgets** — 创建/更新预算

Request body：
```json
{
  "category_id": 3,
  "month": "2026-06",
  "amount": 2000.00
}
```
- 如果同一 `(category_id, month)` 已存在，则更新金额（upsert 语义）

**PUT /api/budgets/{id}** — 更新预算

**DELETE /api/budgets/{id}** — 删除预算

**POST /api/budgets/batch** — 批量设置预算

Request body：
```json
{
  "month": "2026-06",
  "budgets": [
    { "category_id": 3, "amount": 2000.00 },
    { "category_id": 6, "amount": 3000.00 }
  ]
}
```
- 批量 upsert 语义

##### 3.2.2 预算概览

**GET /api/statistics/budget-overview** — 获取月度预算概览

Query 参数：
- `month` (string, 格式 YYYY-MM, 必填)

Response：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "month": "2026-06",
    "total_budget": 5000.00,
    "total_spent": 3250.50,
    "total_remaining": 1749.50,
    "overall_percentage": 65.0,
    "categories": [
      {
        "category_id": 3,
        "category_name": "餐饮",
        "icon": "mdi-food",
        "budget": 2000.00,
        "spent": 1250.50,
        "remaining": 749.50,
        "percentage": 62.5,
        "status": "normal"  // normal / warning(>80%) / exceeded(>100%)
      }
    ]
  }
}
```

#### 3.3 业务逻辑要点

1. **Upsert 逻辑**：创建预算时检查 `(category_id, month)` 是否已存在，存在则更新金额
2. **已花费金额**：从 `records` 表按月和分类汇总 `expense` 类型记录
3. **状态计算**：percentage < 80% → normal, 80%-100% → warning, > 100% → exceeded
4. **分类筛选**：只有 expense 类型的分类可以设置预算
5. **迁移兼容**：`create_all_tables()` 会自动检测并创建 budgets 表，旧数据不受影响

---

### 模块 M0 — 图片附件增强

#### 3.4 现有附件功能

V1.0 已有：
- `Attachment` 模型（id, record_id, filename, stored_path, file_size, mime_type, created_at）
- 图片上传 API：`POST /api/attachments/upload`
- 图片删除 API：`DELETE /api/attachments/{id}`

#### 3.5 新增/修改功能

##### 3.5.1 获取记录的附件列表

**GET /api/attachments/by-record/{record_id}**

Response：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "filename": "lunch.jpg",
      "stored_path": "2026/06/01/xxx.jpg",
      "file_size": 102400,
      "mime_type": "image/jpeg",
      "created_at": "2026-06-01 12:00:00"
    }
  ]
}
```

##### 3.5.2 获取单个附件信息

**GET /api/attachments/{id}**

##### 3.5.3 记录详情中包含附件信息

在记录的 enriched 数据中，`attachment_ids` 保持保留，同时增加 `attachments` 字段：
```json
{
  "id": 1,
  "amount": 25.50,
  "type": "expense",
  "category_id": 3,
  "category_name": "餐饮",
  "tags": ["午餐"],
  "attachment_ids": [1, 2],
  "attachments": [
    {
      "id": 1,
      "filename": "lunch.jpg",
      "stored_path": "2026/06/01/xxx.jpg",
      "file_size": 102400,
      "mime_type": "image/jpeg",
      "created_at": "2026-06-01 12:00:00"
    }
  ],
  "date": "2026-06-01",
  "created_at": "2026-06-01 12:00:00",
  "updated_at": "2026-06-01 12:00:00"
}
```

##### 3.5.4 图片缩略图支持（可选增强）

在 upload 目录下创建 thumbnails 子目录，上传时自动生成 200px 宽度的缩略图。

---

### 模块 M0 — 数据统计扩展

#### 3.6 新增/修改统计接口

##### 3.6.1 日/周粒度趋势

**GET /api/statistics/trend** — 扩展 group_by 参数

新增支持 `group_by=day`：

| group_by | 说明 | period 格式 |
|----------|------|------------|
| day | 按天分组 | YYYY-MM-DD |
| month | 按月分组（已有） | YYYY-MM |
| year | 按年分组（已有） | YYYY |

##### 3.6.2 分类统计支持收入类型

**GET /api/statistics/by-category** — 扩展 type 参数

当前只支持 `type=expense`，扩展支持 `type=income`：
- 去除对 type 的限制检查
- 返回的收入分类统计数据

##### 3.6.3 同比/环比对比（可选）

**GET /api/statistics/compare** — 两个时段对比

Query 参数：
- `start_date_1`, `end_date_1` — 时段1
- `start_date_2`, `end_date_2` — 时段2

Response：
```json
{
  "period_1": { "total_income": 5000, "total_expense": 2000 },
  "period_2": { "total_income": 5500, "total_expense": 1800 },
  "income_change": 10.0,
  "expense_change": -10.0
}
```

---

### 模块 M5 — 前端预算页面

#### 3.7 BudgetPage.vue 完整实现

从现在的空壳页面改造成完整的预算管理页面。

**页面布局**：

```
┌─────────────────────────────────┐
│ 预算管理 (页面标题)              │
│ 掌握每月开支                     │
├─────────────────────────────────┤
│ [← 2026年06月 →]  月/年切换     │
├─────────────────────────────────┤
│ ┌───────────┬───────────┐       │
│ │ 总预算     │ 已使用     │       │
│ │ ¥5000     │ ¥3250     │       │
│ │           │ 65%       │       │
│ └───────────┴───────────┘       │
├─────────────────────────────────┤
│ 分类预算列表                      │
│ ┌─────────────────────────┐     │
│ │ 🍔 餐饮    ¥2000       │     │
│ │ ████████████░░░░ 62%   │     │
│ │ 已用 ¥1250 / 剩余 ¥750 │     │
│ ├─────────────────────────┤     │
│ │ 🏠 居住    ¥3000       │     │
│ │ ██████████████████ 100%│     │
│ │ ⚠️ 已用 ¥3000          │     │
│ ├─────────────────────────┤     │
│ │ 🚗 交通    ¥500        │     │
│ │ ████████████████████░ 120%│   │
│ │ 🔴 超支 ¥100           │     │
│ └─────────────────────────┘     │
├─────────────────────────────────┤
│ [+ 添加预算]                     │
└─────────────────────────────────┘
```

**交互需求**：
1. 月份切换（左右箭头）
2. 点击分类可编辑预算金额
3. 添加预算弹窗：选择分类 + 输入金额
4. 删除预算（滑动手势或长按菜单）
5. 进度条颜色：正常(#6750A4) / 警告(#FFD43B) / 超支(#FF6B6B)

#### 3.8 API 集成

前端需要新增/修改的 API 调用：

```javascript
// api/budgets.js（新建）
export function getBudgets(params)      // GET /api/budgets
export function createBudget(data)      // POST /api/budgets
export function updateBudget(id, data)  // PUT /api/budgets/{id}
export function deleteBudget(id)        // DELETE /api/budgets/{id}
export function batchSetBudgets(data)   // POST /api/budgets/batch

// api/statistics.js（新增）
export function getBudgetOverview(params)  // GET /api/statistics/budget-overview
```

#### 3.9 状态管理

新建 `useBudgetsStore.js`（或在 `useStatisticsStore.js` 中扩展）：

```javascript
// stores/useBudgetsStore.js
state: {
  budgets: [],        // 当前月份预算列表
  overview: null,     // 预算概览
  currentMonth: '',   // 当前查看月份 YYYY-MM
}
actions: {
  fetchBudgets(month),
  setBudget(categoryId, month, amount),
  removeBudget(id),
  batchSetBudgets(month, budgets),
  fetchOverview(month),
}
```

---

### 模块 M5 — 前端体验优化

#### 3.10 记账表单增加图片上传

在 RecordFormPage.vue 中新增功能：

**图片上传区域**（在标签输入下方）：
```
┌─────────────────────────┐
│ 图片附件                  │
│ ┌────┐ ┌────┐ ┌────┐    │
│ │ 🖼 │ │ 🖼 │ │ ➕ │    │
│ └────┘ └────┘ └────┘    │
│ 最多9张，每张最大10MB     │
└─────────────────────────┘
```

**交互细节**：
1. 点击 ➕ 触发文件选择器（accept="image/*"）
2. 选择后立即上传，上传中显示 loading 动画
3. 上传成功显示缩略图，失败显示错误提示
4. 点击图片可预览大图
5. 右上角 ✕ 按钮可删除
6. 编辑记录时回显已上传的图片

#### 3.11 账单列表显示图片缩略图

在 RecordListPage.vue 中，如果有附件，在记录项右侧显示小缩略图：
```
┌────────────────────────────────┐
│ 🡇 餐饮           -¥25.50     │
│    06/01 · 午餐   [🖼️]       │
└────────────────────────────────┘
```

#### 3.12 记录详情页（新建）

新建 `RecordDetailPage.vue`，路由 `/record/:id`。

**页面布局**：
```
┌─────────────────────────────────┐
│ ← 返回                          │
├─────────────────────────────────┤
│ 类型图标 + 分类名称              │
│ ¥25.50                          │
│ 2026年6月1日 星期三              │
├─────────────────────────────────┤
│ 标签: [午餐] [外卖]              │
├─────────────────────────────────┤
│ 图片画廊 (左右滑动)              │
│ ┌────┐ ┌────┐ ┌────┐           │
│ │ 🖼 │ │ 🖼 │ │ 🖼 │           │
│ └────┘ └────┘ └────┘           │
├─────────────────────────────────┤
│ 创建时间: 2026-06-01 12:30      │
│ 更新时间: 2026-06-01 12:30      │
├─────────────────────────────────┤
│ [编辑] [删除]                    │
└─────────────────────────────────┘
```

#### 3.13 首页增加预算概览卡片

在 DashboardPage.vue 中，当月度总支出卡片下方增加一行：
```
┌─────────────────────────────────┐
│ 本月预算     ¥3,250 / ¥5,000    │
│ ██████████████░░░░░░░░  65%     │
│ 已用 ¥3,250  剩余 ¥1,750        │
└─────────────────────────────────┘
```
- 点击跳转到预算页面
- 如果没有设置预算，显示"去设置预算"按钮

#### 3.14 统计页面增加预算对比

在 StatisticsPage.vue 中，分类统计卡片下方增加"预算对比"区域：
- 显示有预算的分类实际支出 vs 预算金额
- 使用水平柱状图对比

#### 3.15 统计页面增加日/周趋势

在 StatisticsPage.vue 的趋势图表中，增加日/周/月/年的切换：
```
[日] [周] [月] [年]
```
- 日视图：显示当月每天的收支
- 周视图：显示当月的周汇总（或按自然周）
- 月视图：已有
- 年视图：已有

#### 3.16 图片预览组件

新建 `ImagePreview.vue` 组件：
- 全屏模式下显示大图
- 左右滑动切换多图
- 捏合缩放（移动端）
- 点击遮罩关闭

---

## 四、具体实现指引

### 4.1 后端实现通用规则

1. **模型定义**：使用 SQLModel，所有模型放在 `app/models/` 下
2. **Schema 定义**：使用 Pydantic v2 BaseModel，放在 `app/schemas/` 下
3. **Service 层**：业务逻辑放在 `app/services/` 下，使用类型注解
4. **Router 层**：API 路由放在 `app/routers/` 下，通过 Depends(get_session) 注入数据库会话
5. **统一响应**：使用 `app/utils/response.py` 中的 `success_response()` 和 `error_response()`
6. **数据库迁移**：无需手动迁移脚本，SQLModel 的 `create_all` 会自动创建新表

### 4.2 前端实现通用规则

1. **样式风格**：遵循 Vuetify 3 + 现有 SCSS 变量
2. **响应式设计**：移动端优先，桌面端适配
3. **状态管理**：使用 Pinia stores
4. **API 请求**：通过 `src/api/` 下的模块封装，使用 Axios 拦截器处理响应
5. **日期处理**：使用 dayjs（已安装）
6. **图标**：使用 MDI 图标（@mdi/font，已安装）
7. **数据格式化**：使用 `src/utils/format.js` 中的工具函数
8. **组件事件**：Toast 通知通过 `useAppStore().showToast()` 触发

### 4.3 测试编写规范

1. 使用 `conftest.py` 中的现有 fixture（`client`, `db_session`, `setup_database`）
2. 每个测试文件都使用 `pytest.mark.asyncio`
3. 测试使用 SQLite 内存数据库
4. 测试覆盖：正常流程、边界条件、错误情况
5. 测试文件命名：`test_<module>.py`

### 4.4 现有代码关键细节

#### 统一响应格式

后端所有 API 返回格式：
```json
{
  "code": 0,        // 0=成功
  "message": "success",
  "data": { ... }   // 实际数据
}
```

错误响应：
```json
{
  "code": 40001,    // 错误码
  "message": "参数验证错误",
  "data": null
}
```

#### 现有错误码

```python
class Code:
    SUCCESS = 0
    PARAM_ERROR = 40001
    NOT_FOUND = 40002
    CONFLICT = 40003
    FILE_INVALID = 40004
    SERVER_ERROR = 50001
```

#### 前端 Axios 拦截器行为

```javascript
// success_response → 返回 res.data（data 字段的内容）
// error_response → 抛出 Error(res.message)
// 422 → 抛出 Error('参数错误')
// 500 → 抛出 Error('服务器错误')
```

#### 现有数据库配置

```python
DATABASE_URL = "sqlite+aiosqlite:///backend/money.db"  # 从 .env 读取
```

#### 测试数据库

```python
TEST_DATABASE_URL = "sqlite+aiosqlite://"  # 内存数据库
```

---

## 五、主 Agent 执行流程

### 5.1 阶段 0：环境准备

1. 创建 feature-v1.1 分支
2. 在 `pyproject.toml` 中添加 mypy 和 ruff 配置

```toml
[tool.mypy]
strict = true
python_version = "3.12"
ignore_missing_imports = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_any_unimported = false

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.format]
quote-style = "double"
```

3. 验证当前代码在 feature-v1.1 分支上能正常运行

### 5.2 阶段 1-5：子 Agent 执行

每个子 Agent 按以下模板执行：

```
你是一个专注于 [模块名称] 的全栈开发者。

需要实现的功能：
[简要描述]

需要创建/修改的文件：
[文件列表]

详细设计参考：
[引用详细设计文档对应章节]

现有代码参考：
[关键文件内容或接口定义]

质量要求：
1. 后端代码必须通过 mypy --strict 检查
2. 后端代码必须通过 ruff check（零警告）
3. 测试必须全部通过
4. 前端代码兼容 Vue 3 Composition API + Vuetify 3

完成标准：
- 功能代码编写完成
- 单元测试编写完成
- 本地运行 pytest 通过
```

### 5.3 阶段 6：集成验证

1. **后端测试**：`pytest backend/tests/ -v`
2. **类型检查**：`mypy backend/app/ --strict`
3. **代码风格**：`ruff check backend/app/`
4. **启动测试**：`uvicorn app.main:app --reload` 查看 /docs
5. **前端构建**：`npm run build` 确认无错误
6. **功能验收**：按 6.2 节 checklist 逐项确认

---

## 六、验收标准

### 6.1 质量门禁

| 检查项 | 命令 | 通过标准 |
|--------|------|----------|
| 单元测试 | `pytest backend/tests/ -v` | 全部通过 |
| 类型检查 | `mypy backend/app/ --strict` | 零错误 |
| 代码风格 | `ruff check backend/app/` | 零警告 |
| 前端构建 | `cd frontend && npm run build` | 无错误 |

### 6.2 功能验收清单

#### 预算管理
- [ ] 可以创建分类预算（设置金额和月份）
- [ ] 同一分类同月份重复设置自动更新（upsert）
- [ ] 可以批量设置预算
- [ ] 预算列表显示已花费金额和剩余金额
- [ ] 进度条颜色按比例变化（正常/警告/超支）
- [ ] 可以编辑和删除预算
- [ ] 预算概览接口返回总预算、总花费、总剩余

#### 图片附件
- [ ] 记账表单可以上传图片
- [ ] 上传图片显示缩略图
- [ ] 可以预览大图
- [ ] 可以删除已上传图片
- [ ] 编辑记录时回显已有图片
- [ ] 记录详情中显示图片列表
- [ ] 账单列表有附件的记录显示缩略图标记

#### 统计增强
- [ ] 趋势图支持按日查看
- [ ] 趋势图支持按周查看
- [ ] 分类统计支持收入类型
- [ ] 统计页面显示预算对比
- [ ] 首页显示预算概览卡片

#### 前端体验
- [ ] 所有页面在移动端显示正常
- [ ] 所有页面在桌面端显示正常
- [ ] 深色模式兼容
- [ ] 页面切换动画流畅
- [ ] Toast 通知正常

### 6.3 数据库兼容性

- [ ] 原有 `money.db` 数据不受影响
- [ ] `budgets` 表自动创建
- [ ] 已有 API 接口返回格式不变

---

## 七、附录

### A. 现有关键文件内容摘要

#### app/database.py
```python
engine = create_async_engine(DATABASE_URL, echo=False)

async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

#### app/utils/response.py
```python
class Code:
    SUCCESS = 0
    PARAM_ERROR = 40001
    NOT_FOUND = 40002
    CONFLICT = 40003
    FILE_INVALID = 40004
    SERVER_ERROR = 50001

def success_response(data=None, message=None) -> JSONResponse
def error_response(code, message=None, data=None, status_code=400) -> JSONResponse
```

#### frontend/src/api/request.js
```javascript
const request = axios.create({ baseURL: '/api', timeout: 15000 })
// 响应拦截器：code===0 → return res.data，其他 → Promise.reject
```

#### Record 响应格式（现有 enrich 结果）
```python
{
    "id": int,
    "amount": float,
    "type": "income" | "expense",
    "category_id": int,
    "category_name": str,
    "tags": list[str],
    "attachment_ids": list[int],
    "date": str,  # YYYY-MM-DD
    "created_at": str,  # YYYY-MM-DD HH:mm:ss
    "updated_at": str,  # YYYY-MM-DD HH:mm:ss
}
```

### B. 现有测试 conftest.py 关键 fixture

```python
# 使用内存 SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite://"

@pytest_asyncio.fixture(autouse=True)
async def setup_database():  # 每次测试前创建表并 seed 预设分类

@pytest_asyncio.fixture
async def client():  # 提供 AsyncClient，覆盖 get_session 依赖

@pytest_asyncio.fixture
async def db_session():  # 提供测试数据库会话
```

### C. 依赖说明

已在 requirements.txt 中的依赖：
- fastapi>=0.110, sqlmodel>=0.0.14, aiosqlite>=0.20
- uvicorn[standard], python-multipart>=0.0.9, python-dotenv
- pytest>=7.0, pytest-asyncio>=0.21, httpx>=0.27, mypy>=1.0, ruff>=0.1

前端 package.json 现有依赖：
- vue@3, vue-router@4, pinia
- vuetify@3, @mdi/font
- axios, dayjs, chart.js, vue