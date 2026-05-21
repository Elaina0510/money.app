# VibeCoding 主 Agent Prompt — 个人记账程序 V1.0

> **项目名称**：个人记账程序 (Money App)  
> **目标版本**：V1.0（MVP）  
> **技术栈**：后端 FastAPI + SQLModel + SQLite，前端 Vue.js 3 + Vuetify 3  
> **输出规范**：代码必须通过 `pytest` 单元测试、`mypy` 类型检查、`ruff` 代码检查（后两者仅后端）

---

## 一、你是谁

你是一个 VibeCoding **主 Agent**。你的任务是：
1. 理解整个项目的需求和详细设计
2. **生成子 Agent** 来实现每一个模块
3. **跟踪整体进度**，确保子 Agent 按正确顺序完成工作
4. **整个过程无需人工参与**

---

## 二、项目概述

开发一个**个人记账网页应用**，支持收入/支出记录、分类标签管理、图片附件、数据统计等功能。
单人使用，本地运行，数据存储在 SQLite 中。

> 详细需求见 `doc/proposal.md`  
> 详细设计见 `doc/detailed-design.md`  
> 任务划分见 `doc/tasks/` 目录

---

## 三、项目目录结构

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
│   │   │   ├── record.py          # Record 模型
│   │   │   ├── record_tag.py      # RecordTag 关联模型
│   │   │   ├── category.py        # Category 模型
│   │   │   ├── tag.py             # Tag 模型
│   │   │   └── attachment.py      # Attachment 模型
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
│   ├── uploads/                   # 附件图片存储
│   ├── tests/                     # pytest 测试
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_records.py
│   │   ├── test_categories.py
│   │   ├── test_tags.py
│   │   ├── test_attachments.py
│   │   └── test_statistics.py
│   ├── money.db                   # SQLite 数据库文件（自动生成）
│   ├── requirements.txt
│   └── .env
├── frontend/                      # Vue.js 前端
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── public/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/index.js
│   │   ├── stores/
│   │   │   ├── useRecordsStore.js
│   │   │   ├── useCategoriesStore.js
│   │   │   ├── useStatisticsStore.js
│   │   │   └── useAppStore.js
│   │   ├── api/
│   │   │   ├── request.js
│   │   │   ├── records.js
│   │   │   ├── categories.js
│   │   │   ├── tags.js
│   │   │   ├── attachments.js
│   │   │   └── statistics.js
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── layout/
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── DashboardPage.vue
│   │   │   ├── RecordFormPage.vue
│   │   │   ├── RecordListPage.vue
│   │   │   ├── StatisticsPage.vue
│   │   │   └── SettingsPage.vue
│   │   ├── composables/
│   │   ├── utils/
│   │   └── styles/
│   └── dist/                      # 构建产物
├── doc/
│   ├── proposal.md
│   ├── detailed-design.md
│   ├── tasks/
│   │   ├── progress.md
│   │   ├── backend-setup.md
│   │   ├── m1-record-management.md
│   │   ├── m2-category-tag-management.md
│   │   ├── m3-attachment-management.md
│   │   ├── m4-statistics.md
│   │   ├── m5-frontend-ui.md
│   │   └── m6-android-webview.md
│   └── prompt.md                  # 本文件
├── .gitignore
└── README.md
```

---

## 四、模块划分与开发顺序

### 4.1 模块总览

| 编号 | 模块名称 | 描述 | 技术栈 |
|------|---------|------|--------|
| M0 | 后端基础搭建 | 项目结构、配置、数据库引擎、统一响应 | Python |
| M2 | 分类标签管理 | 分类/标签 CRUD、预设数据（M0 后第一步） | Python |
| M1 | 记账管理 | 记账 CRUD、筛选搜索、快速记账 | Python |
| M3 | 附件管理 | 图片上传/查看/删除 | Python |
| M4 | 统计模块 | 收支概览、分类统计、趋势 | Python |
| M5 | 前端 UI | Vue.js 3 SPA 全部页面 | JavaScript |
| M6 | 安卓 WebView | 安卓壳封装（仅提及，不要求实现） | Kotlin |

### 4.2 开发顺序

```
M0 → M2 → M1 → M3 → M4 → M5
```

> M6（安卓 WebView）仅作为后续补充提及，**此轮 VibeCoding 不要求生成 M6 的代码**。

### 4.3 模块依赖关系

```
M2（分类标签管理） ←── M1（记账管理） ──→ M3（附件管理）
                           ↓
                      M4（统计模块）
                           ↓
                      M5（前端 UI 模块）
```

- M2 为 M1 提供分类数据源
- M1 为 M4 提供基础记账数据
- M5 依赖所有后端 API

---

## 五、各模块详细要求

### M0 — 后端基础搭建

**目标**：搭建项目骨架，确保后端可启动。

**具体要求**：
1. 创建 `backend/` 目录及子目录结构
2. `requirements.txt` 依赖：
   - `fastapi>=0.110`
   - `sqlmodel>=0.14`
   - `aiosqlite>=0.20`
   - `uvicorn[standard]`
   - `python-multipart>=0.0.9`
   - `python-dotenv`
   - 测试相关：`pytest`, `pytest-asyncio`, `httpx`, `mypy`, `ruff`
3. `app/config.py`：从 `.env` 和默认值加载配置（数据库路径 `money.db`，上传目录 `uploads/`，最大文件 10MB）
4. `app/database.py`：SQLModel 异步引擎、`AsyncSession`、`get_session` 依赖注入
5. `app/main.py`：FastAPI 应用，注册 CORS 中间件（允许所有来源），注册各模块路由，启动事件中执行 `create_all()` 建表并插入预设分类数据
6. `app/utils/response.py`：统一响应格式 `{"code": 0, "message": "success", "data": {...}}`，错误码常量
7. 预设分类数据（14 条，详见详细设计 4.2 节），插入时检查是否已存在，避免重复插入

### M2 — 分类标签管理模块

**目标**：提供分类和标签的 CRUD API。

**具体要求**：
1. **数据模型**：
   - `Category`：id, name, type(income/expense), icon, sort_order, is_preset, created_at
   - `Tag`：id, name, created_at
   - Category 的 `(name, type)` 联合唯一索引
2. **API 接口**（8 个）：
   - `GET /api/categories` — 获取分类列表，支持 `?type=income|expense` 筛选
   - `POST /api/categories` — 新增自定义分类
   - `PUT /api/categories/{id}` — 编辑分类
   - `DELETE /api/categories/{id}` — 删除分类（检查是否有记录关联）
   - `GET /api/tags` — 获取所有标签
   - `POST /api/tags` — 新增标签
   - `PUT /api/tags/{id}` — 编辑标签
   - `DELETE /api/tags/{id}` — 删除标签
3. **保护逻辑**：删除分类时检查 `records` 表是否有引用，有则返回错误码 `40003`
4. **预设分类**（is_preset=1）删除时给出提示

### M1 — 记账管理模块

**目标**：记账记录的增删改查、筛选查询、快速记账。

**具体要求**：
1. **数据模型**：
   - `Record`：id, amount(>0), type(income/expense), category_id(FK), date, created_at, updated_at
   - `RecordTag`：record_id(FK CASCADE), tag_id(FK CASCADE), UNIQUE(record_id, tag_id)
2. **关键设计决策**：
   - `amount` 统一存正数，由 `type` 字段区分收入/支出
   - 标签（tags）为自由输入文本，每次记账可输入新内容，不强制复用，同时承担备注功能
3. **API 接口**（7 个）：
   - `POST /api/records` — 新增记录（含标签列表）
   - `GET /api/records` — 获取列表（分页+筛选，详见详细设计 3.4 节）
   - `GET /api/records/{id}` — 获取单条详情（含标签和附件信息）
   - `PUT /api/records/{id}` — 更新记录
   - `DELETE /api/records/{id}` — 删除记录
   - `POST /api/records/batch-delete` — 批量删除
   - `GET /api/records/quick-templates` — 获取最近 10 条记录作为快速记账模板
4. **筛选参数**：page, page_size, start_date, end_date, category_id, type, tag, keyword, sort_by, sort_order
5. **边界校验**：金额>0且≤99999999.99，分类ID存在性，批量删除空列表返回400

### M3 — 附件管理模块

**目标**：图片附件的上传/查看/删除。

**具体要求**：
1. **数据模型**：
   - `Attachment`：id, record_id(FK SET NULL), filename, stored_path, file_size, mime_type, created_at
2. **存储规则**：
   - 目录：`uploads/{year}/{month}/{day}/{uuid}.{ext}`
   - 支持格式：jpg/jpeg/png/gif/webp
   - 单文件最大 10MB
   - 文件名用 UUID 生成
3. **API 接口**（4 个）：
   - `POST /api/attachments/upload` — 上传（multipart/form-data）
   - `GET /api/attachments/{id}` — 获取附件信息
   - `DELETE /api/attachments/{id}` — 删除（同时删除物理文件）
   - `GET /api/records/{record_id}/attachments` — 获取记录的附件列表
4. **静态文件路由**：配置 `/uploads` 指向 `uploads/` 目录

### M4 — 统计模块

**目标**：基于记账数据的统计分析。

**具体要求**：
1. **API 接口**（4 个）：
   - `GET /api/statistics/summary` — 收支概览（period: day/week/month/year, start_date, end_date）
   - `GET /api/statistics/by-category` — 分类统计（type=expense, start_date, end_date）
   - `GET /api/statistics/by-tag` — 标签统计（start_date, end_date）
   - `GET /api/statistics/trend` — 收支趋势（group_by: month/year, start_date, end_date）
2. **空数据处理**：无数据区间返回 0 而非报错
3. 各接口详细响应结构见详细设计第 6 节

### M5 — 前端 UI 模块

**目标**：完整的 Vue.js 3 SPA。

**具体要求**：
1. **技术栈**：Vue 3 + Vite + Vuetify 3 + Vue Router + Pinia + Axios + Chart.js
2. **路由**：`/`(仪表盘), `/add`(新增), `/edit/:id`(编辑), `/records`(列表), `/statistics`(统计), `/settings`(设置)
3. **底部导航**：首页、记账、账单、统计、设置
4. **页面**：
   - 仪表盘：今日概览、月度统计、最近5条记录
   - 记账表单：金额、类型、分类选择器、标签输入（自由文本+逗号分隔）、日期选择、附件上传
   - 账单列表：筛选栏、卡片列表、分页、批量删除
   - 统计页：概览卡片、分类饼图、趋势折线图
   - 设置页：分类管理、标签管理、数据管理
5. **设计风格**：Material You（Material Design 3），支持深色模式
6. **响应式**：移动端优先，适配平板和桌面
7. **API 层**：通过 Axios 调用后端 API，开发环境通过 Vite proxy 代理到 `localhost:8000`
8. **测试**：可选，由子 Agent 自行决定是否添加

---

## 六、质量要求

### 6.1 后端质量门禁

| 工具 | 要求 | 命令 |
|------|------|------|
| **pytest** | 每个模块必须有完整的单元测试，覆盖率尽可能高 | `pytest backend/tests/ -v` |
| **mypy** | 严格模式通过 | `mypy backend/app/ --strict` |
| **ruff** | 零警告通过 | `ruff check backend/app/` |

### 6.2 测试要点（后端）

- `conftest.py` 中配置测试数据库（使用临时文件或内存数据库）
- 每个模块独立测试，构造 Mock 数据
- 测试正常流程和边界情况
- M4 统计模块测试时需预构造记账数据

### 6.3 前端质量

- 可选，由子 Agent 自行决定是否添加测试
- 代码风格尽量保持整洁一致

---

## 七、主 Agent 工作流程

### 7.1 总控流程

```
主 Agent 启动
    │
    ├── 第1步：读取所有设计文档（已完成）
    │
    ├── 第2步：生成子 Agent #1（M0 后端基础搭建）
    │   └── 等待完成 → 验证（启动后端 + 访问 /docs）
    │
    ├── 第3步：生成子 Agent #2（M2 分类标签管理）
    │   └── 等待完成 → 验证（测试 + mypy + ruff）
    │
    ├── 第4步：生成子 Agent #3（M1 记账管理）
    │   └── 等待完成 → 验证（测试 + mypy + ruff）
    │
    ├── 第5步：生成子 Agent #4（M3 附件管理）
    │   └── 等待完成 → 验证（测试 + mypy + ruff）
    │
    ├── 第6步：生成子 Agent #5（M4 统计模块）
    │   └── 等待完成 → 验证（测试 + mypy + ruff）
    │
    ├── 第7步：生成子 Agent #6（M5 前端 UI）
    │   └── 等待完成 → 验证（启动前端 + 页面渲染）
    │
    ├── 第8步：联调测试（前后端集成验证）
    │
    └── 第9步：汇总完成状态，更新 progress.md
```

### 7.2 子 Agent 生成模板

每个子 Agent 被生成时，你应该向其提供：

1. **模块编号和名称**（如 "M1 — 记账管理模块"）
2. **对应任务文件**的完整内容（来自 `doc/tasks/` 目录）
3. **详细设计文档**中该模块对应的章节
4. **相关数据模型和接口定义**
5. **质量要求**：pytest 测试、mypy、ruff
6. **该模块的输入和输出**（哪些文件需要创建/修改）

### 7.3 进度跟踪

每完成一个子 Agent，更新 `doc/tasks/progress.md` 中的对应复选框。
完成后输出汇总报告。

### 7.4 依赖处理

- M0 完成后才能开始 M2
- M2 完成后才能开始 M1（M1 依赖分类数据）
- M1 完成后才能开始 M4（M4 依赖记账数据）
- M3 可与 M1 并行开发（无依赖冲突）
- M5 可在后端 API 就绪后开始

---

## 八、关键设计决策（必须遵守）

以下决策来自详细设计文档，子 Agent 实现时必须遵守：

1. **amount 字段**：统一存储正数，由 `type` 字段（income/expense）区分收入或支出
2. **标签（tags）**：自由输入文本标签，每次记账可输入新内容，不强制复用，**同时承担备注功能**，无需独立的 note 字段
3. **统一响应格式**：`{"code": 0, "message": "success", "data": {...}}`
4. **错误码**：0=成功, 40001=参数验证错误, 40002=资源不存在, 40003=操作冲突, 40004=文件违规, 50001=服务器错误
5. **快速记账**：使用 `GET /api/records/quick-templates` 获取最近 10 条记录（而非原设计的 POST 方式）
6. **删除附件**：同时删除物理文件和数据库记录
7. **预设分类**：is_preset=1，首次启动自动插入，重复启动不重复插入

---

## 九、可能遇到的问题与处理

| 问题 | 处理方式 |
|------|---------|
| 子 Agent 生成的代码有 bug | 主 Agent 应指出具体错误，要求子 Agent 修复 |
| 测试失败 | 要求子 Agent 修复直到通过 |
| mypy/ruff 不通过 | 要求子 Agent 修复类型注释和代码风格 |
| 模块间接口不一致 | 主 Agent 协调两个子 Agent 统一接口 |
| 子 Agent 偏离设计 | 主 Agent 引用详细设计文档纠正 |

---

## 十、完成标准

所有模块完成后应满足：

1. ✅ `uvicorn app.main:app --reload` 启动成功
2. ✅ 访问 `http://localhost:8000/docs` 显示所有 API
3. ✅ `pytest backend/tests/ -v` 全部通过
4. ✅ `mypy backend/app/ --strict` 通过
5. ✅ `ruff check backend/app/` 通过
6. ✅ `npm run dev` 前端启动正常
7. ✅ 所有页面可正常访问
8. ✅ 前后端联调通过（记账→列表→统计→设置全流程）
9. ✅ `doc/tasks/progress.md` 全部勾选完成
