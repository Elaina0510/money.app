# 记账程序 v1.1 — 详细设计文档

> 版本：v1.1  
> 基于：v1.0 MVP + [proposalv11.md](proposalv11.md)  
> 目标：修复 v1.0 已知 Bug + 实现 UI/UX 改进和少量新功能  
> 技术栈：Python (FastAPI) + Vue.js 前端 + SQLite

---

## 目录

1. [版本概述](#1-版本概述)
2. [数据模型变更](#2-数据模型变更)
3. [Schema 层变更](#3-schema-层变更)
4. [Service 层变更](#4-service-层变更)
5. [Router 层变更](#5-router-层变更)
6. [前端组件变更](#6-前端组件变更)
7. [Bug 修复实施方案](#7-bug-修复实施方案)
8. [样式与主题变更](#8-样式与主题变更)
9. [API 接口文档（最终版）](#9-api-接口文档最终版)
10. [测试计划](#10-测试计划)

---

## 1. 版本概述

### 1.1 范围（共 11 项）

| # | 类型 | 内容 | 涉及层 | 工作量 |
|:---:|:---:|------|--------|:------:|
| 1 | 🐛 | PC 端缺少左侧边栏导航 | 前端 | S |
| 2 | 🐛 | 首页最近账单显示为空 | 前端+后端 | S |
| 3 | 🐛 | 统计金额显示为 0 | 后端 | S |
| 4 | 🐛 | 深色模式文字/背景颜色冲突 | 前端 | M |
| 5 | 🐛 | 账单详情默认勾选无法查看 | 前端+后端 | M |
| 6 | ✨ | 账单详情页（查看+编辑+删除） | 前端+后端 | M |
| 7 | ✨ | PC 端补充深色/浅色模式切换按钮 | 前端 | S |
| 8 | ✨ | 账单列表布局重构 | 前端+后端 | M |
| 9 | ✨ | 快速记账时标签自动匹配分类 | 后端+前端 | M |
| 10 | ✨ | 消费时间精确到分钟 | 后端+前端 | L |
| 11 | 🎨 | 主色调变更为灰褐色 | 前端 | S |

---

## 2. 数据模型变更

### 2.1 Tag 模型 — 新增 category_id 外键

**文件**: `backend/app/models/tag.py`

```python
"""Tag model."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    """Tag model for free-text labels on records."""

    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    # v1.1 新增：关联分类，可为 null
    category_id: int | None = Field(
        default=None,
        nullable=True,
        foreign_key="categories.id",
        ondelete="SET NULL",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
```

**变更说明**：
- 新增 `category_id`：Integer, FK → `categories.id`, nullable, ondelete="SET NULL"
- 用于快速记账时标签自动匹配分类

### 2.2 Record 模型 — 重构字段

**文件**: `backend/app/models/record.py`

```python
"""Record model."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Record(SQLModel, table=True):
    """Record model for income/expense transactions."""

    __tablename__ = "records"

    id: int | None = Field(default=None, primary_key=True)
    amount: float = Field(nullable=False)  # Always positive, type distinguishes income/expense
    type: str = Field(nullable=False)  # "income" or "expense"
    category_id: int = Field(nullable=False, foreign_key="categories.id")
    # v1.1 变更：从多标签（通过 RecordTag 多对多）改为单标签，直接存 tag_id
    tag_id: int | None = Field(
        default=None,
        nullable=True,
        foreign_key="tags.id",
        ondelete="SET NULL",
    )
    # v1.1 变更：新增 consume_time，替代原有的 date + created_at
    consume_time: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"),
        nullable=False,
    )
    note: str | None = Field(default=None, nullable=True)  # v1.1 新增：备注字段
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        nullable=False,
    )
```

**变更明细**：

| 状态 | 旧字段 | 新字段 | 说明 |
|:----:|--------|--------|------|
| ❌ 移除 | `date` (YYYY-MM-DD) | — | 合并到 consume_time |
| ✅ 新增 | — | `consume_time` (YYYY-MM-DD HH:mm) | 消费时间，默认当前时间，用户可修改 |
| ✅ 新增 | — | `note` (Text) | 备注，可为 null |
| ✅ 变更 | 多对多标签(RecordTag) | `tag_id` (单值 FK → tags.id) | 一条记录一个标签，可为 null |

### 2.3 RecordTag 模型 — 标记为废弃

**文件**: `backend/app/models/record_tag.py`

RecordTag 表在 v1.1 中不再使用，但为了兼容旧数据，暂不删除该表和表数据。代码中不再引用该模型。计划在 v1.2 中执行数据迁移并移除该表。

### 2.4 数据库迁移策略

> ⚠️ **注意**：当前项目使用 `SQLModel.metadata.create_all` 自动建表，**不支持自动迁移**。需要手动处理兼容。

**方案：保留旧表+版本化迁移**

1. 在 `backend/app/models/` 中定义模型变更
2. 手动编写迁移脚本 `backend/app/migration_v11.py`
3. 该脚本需在服务启动时检查并执行（可通过环境变量 `RUN_MIGRATION=true` 触发）
4. 迁移脚本内容：

```python
"""v1.1 数据库迁移脚本。

变更内容：
1. tags 表新增 category_id 列
2. records 表：移除 date 列，新增 consume_time、tag_id、note 列
3. record_tags 表保留（不再使用，v1.2 清理）
"""
```

---

## 3. Schema 层变更

### 3.1 Tag Schema

**文件**: `backend/app/schemas/tag.py`

```python
class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category_id: int | None = Field(default=None, gt=0)  # v1.1 新增


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category_id: int | None = Field(default=None, gt=0)  # v1.1 新增


class TagResponse(BaseModel):
    id: int
    name: str
    category_id: int | None = None  # v1.1 新增
    created_at: str
```

### 3.2 Record Schema

**文件**: `backend/app/schemas/record.py`

```python
class RecordCreate(BaseModel):
    amount: float = Field(..., gt=0, le=99999999.99)
    type: str = Field(..., pattern=r"^(income|expense)$")
    category_id: int = Field(..., gt=0)
    # v1.1 变更：从 tags: list[str] 改为 tag_id: int | None
    tag_id: int | None = Field(default=None, gt=0)
    # v1.1 变更：从 date + created_at 改为 consume_time
    consume_time: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",
    )
    # v1.1 新增
    note: str | None = Field(default=None, max_length=500)


class RecordUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0, le=99999999.99)
    type: str | None = Field(default=None, pattern=r"^(income|expense)$")
    category_id: int | None = Field(default=None, gt=0)
    tag_id: int | None = Field(default=None, gt=0)
    consume_time: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",
    )
    note: str | None = Field(default=None, max_length=500)


class RecordResponse(BaseModel):
    id: int
    amount: float
    type: str
    category_id: int
    category_name: str = ""
    category_icon: str = ""  # v1.1 新增
    tag: dict | None = None  # v1.1 变更：替换 tags: list[str]
    # { "id": 1, "name": "奶茶", "category_id": 3 }
    attachment_ids: list[int] = []
    consume_time: str  # v1.1 变更：替换 date + created_at
    note: str | None = None  # v1.1 新增
    created_at: str
    updated_at: str


class RecordListResponse(BaseModel):
    items: list[RecordResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
```

---

## 4. Service 层变更

### 4.1 tag_service.py 变更

**文件**: `backend/app/services/tag_service.py`

**变更点**：

1. `create_tag` — 接受 TagCreate 中的 `category_id`，保存到 tag
2. `update_tag` — 支持修改 `category_id` 和 `name`
3. `get_tag` (新增) — 获取单个标签详情（含关联分类信息）
4. `get_tags` — 返回数据包含 `category_id`

### 4.2 record_service.py 重大变更

**文件**: `backend/app/services/record_service.py`

**核心变更**：

1. **标签处理逻辑重写**：
   - 旧的 `tags: list[str]` + `RecordTag` 多对多 → 新的 `tag_id: int | None` 一对一
   - 创建/更新时不再操作 `RecordTag` 表，而是直接设置 `record.tag_id`
   - 保留 `tag_id` 时不做 "find or create" 操作（标签必须先存在）

2. **时间字段变更**：
   - 所有 `date` 相关过滤 → `consume_time` 过滤（仍使用 `>=` / `<=` 字符串比较）
   - 排序字段从 `date` 改为 `consume_time`

3. **_enrich_record 方法变更**：
   - 返回 `tag` 对象（含 id, name, category_id）替代 `tags: list[str]`
   - 新增 `category_icon` 字段
   - 返回 `consume_time` 替代 `date` + `created_at`
   - 返回 `note`

4. **get_records 参数变更**：
   - 移除 `tag` 参数（旧的多对多标签搜索），使用 `tag_id` 直接筛选
   - 关键词搜索改为搜索 `note` 字段（而非标签名）

### 4.3 statistics_service.py 变更

**文件**: `backend/app/services/statistics_service.py`

**Bug 修复 — 统计金额为 0**：

根因分析：
- SQLAlchemy 的 `func.sum(Record.amount)` 在 SQLite 中可能因类型问题返回空值
- `coalesce` 函数可能未正确处理

修复方案：
1. 确保 `Record.amount` 的 SQLite 存储类型为 `REAL`
2. 在 `get_summary` 中增加调试日志/备选查询
3. 修改查询逻辑，使用 `select(func.coalesce(...))` 确保非空回退

```python
# 修复后的查询
query = select(
    func.coalesce(
        func.sum(Record.amount).filter(Record.type == "income"), 0.0
    ).label("total_income"),
    func.coalesce(
        func.sum(Record.amount).filter(Record.type == "expense"), 0.0
    ).label("total_expense"),
    func.count(Record.id).label("transaction_count"),
).where(
    Record.date >= start_date,  # v1.1 改为 consume_time
    Record.date <= end_date,
)
```

**v1.1 适配**：所有 `Record.date` 引用改为 `Record.consume_time`

### 4.4 attachment_service.py

无重大变更。但需要确保：
- `upload_attachment` 中对 `record_id` 的关联仍然有效
- 删除记录时附件的清理逻辑

---

## 5. Router 层变更

### 5.1 tags.py 路由变更

**文件**: `backend/app/routers/tags.py`

```python
# 新增路由
@router.get("/{tag_id}")
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get a single tag with its associated category."""
    tag = await tag_service.get_tag(db, tag_id)
    if not tag:
        return error_response(Code.NOT_FOUND, "标签不存在")
    return success_response(data=tag)
```

### 5.2 records.py 路由变更

**文件**: `backend/app/routers/records.py`

- POST `/api/records/` — 请求体适配 v1.1 新 schema
- GET `/api/records/` — 返回数据适配 v1.1 新格式
- GET `/api/records/{id}` — 返回数据适配 v1.1 新格式（已有路由，需调整返回数据）
- PUT `/api/records/{id}` — 请求体和返回数据适配 v1.1

### 5.3 statistics.py 路由变更

**文件**: `backend/app/routers/statistics.py`

- 查询参数从 `start_date`/`end_date` → 保持名称不变但内部改为筛选 `consume_time`
- 修复统计计算 Bug（见 4.3）

---

## 6. 前端组件变更

### 6.1 新增页面：RecordDetailPage.vue

**文件**: `frontend/src/pages/RecordDetailPage.vue`

| 项目 | 说明 |
|------|------|
| 路由 | `/detail/:id` |
| 功能 | 展示单条记录的完整信息 |

**布局**：

```
┌──────────────────────────┐
│   ← 返回    账单详情       │
├──────────────────────────┤
│                          │
│    [分类图标]              │
│    餐饮                    │
│                          │
│       ¥ 35.00             │
│      支出                  │
│                          │
│  ┌────────────────────┐   │
│  │ 标签   奶茶          │   │
│  │ 时间   2026-01-15 14:30│   │
│  │ 备注   下午茶         │   │
│  │ 附件   [图片预览]     │   │
│  └────────────────────┘   │
│                          │
│  [编辑]    [删除]         │
└──────────────────────────┘
```

**交互逻辑**：
- 点击「编辑」→ 跳转 `/edit/:id`（复用 RecordFormPage）
- 点击「删除」→ 弹出 ConfirmDialog → 确认后删除并返回列表页

### 6.2 RecordListPage.vue 重构

**文件**: `frontend/src/pages/RecordListPage.vue`

**布局变更**（每行卡片）：

```
┌──────────────────────────────────────┐
│  [分类图标]  标题（标签名/分类名）       │
│              ¥金额    2026-01-15       │
└──────────────────────────────────────┘
```

**交互变更**：
- 点击卡片 → 跳转 `/detail/:id`（查看详情）
- 长按/右键 → 出现勾选框（用于批量删除）
- 移除旧的"点击即勾选"行为

**数据获取变更**：
- 使用 `consume_time` 替代 `date`
- 列表页仅显示日期 `YYYY-MM-DD`（从 `consume_time` 截取）
- 显示 `tag` 对象（单标签）替代 `tags` 数组
- 无标签时回退显示分类名

### 6.3 RecordFormPage.vue 重构

**文件**: `frontend/src/pages/RecordFormPage.vue`

**表单字段变更**：

| v1.0 | v1.1 |
|------|------|
| 金额（必填） | 金额（必填）|
| 类型（必填） | 类型（必填）|
| 分类（必填） | 分类（必填）|
| 日期（必填） | 消费时间（必填，精确到分钟）|
| 标签（多标签，输入+回车添加） | 标签（单标签，下拉选择现有标签，非必填）|
| — | 备注（可选）|

**标签选择器变更**：
- 从「输入标签名称+回车添加」改为「下拉选择已有标签」
- 标签为非必填
- 选择标签时自动匹配分类（调用标签的 `category_id`）
- 如果标签有 `category_id`，自动选中对应分类
- 如果标签无 `category_id`，分类保持用户选择

**时间选择器变更**：
- 从 `type="date"` 改为日期选择器 + 时间选择器
- 默认值为当前时间（精确到分钟）
- 用户可修改

### 6.4 DashboardPage.vue 修复

**文件**: `frontend/src/pages/DashboardPage.vue`

**Bug 修复 — 最近账单为空**：
- 检查 `getRecords` 调用参数是否正确
- v1.0 中使用了 `sort_by: 'date'` 和 `sort_order: 'desc'`，v1.1 应改为 `sort_by: 'consume_time'`
- 确保响应数据解析正确（适配 v1.1 的 RecordResponse 格式）

**数据展示适配**：
- 使用 `consume_time` 替代 `date`
- 使用 `tag` 对象替代 `tags`
- 统计卡片中的金额字段使用修复后的统计接口

### 6.5 新增路由：/detail/:id

**文件**: `frontend/src/router/index.js`

```javascript
{
  path: '/detail/:id',
  name: 'RecordDetail',
  component: () => import('@/pages/RecordDetailPage.vue'),
  meta: { title: '账单详情', icon: 'mdi-information-outline' },
}
```

### 6.6 新增 store 方法

暂无新增 store。但需要更新 `useRecordsStore` 中方法适配 v1.1 的数据格式。

### 6.7 主题色变更

**文件**: `frontend/src/plugins/vuetify.js`（或 `frontend/src/styles/` 下的变量文件）

将 Vuetify 主题色从紫色改为灰褐色：

```javascript
// 浅色模式
light: {
  primary: '#8B7E74',      // 灰褐色主色
  secondary: '#A8988E',    // 浅灰褐色
  accent: '#C4B5A8',       // 更浅的灰褐色
  surface: '#FFFFFF',
  background: '#F5F0EB',   // 米白背景
  error: '#E57373',
  info: '#64B5F6',
  success: '#81C784',
  warning: '#FFB74D',
}

// 深色模式
dark: {
  primary: '#A8988E',      // 深色模式下略亮
  secondary: '#8B7E74',
  accent: '#7A6E64',
  surface: '#2C2C2C',
  background: '#1E1E1E',
  error: '#EF5350',
  info: '#42A5F5',
  success: '#66BB6A',
  warning: '#FFA726',
}
```

---

## 7. Bug 修复实施方案

### Bug 1：PC 端缺少左侧边栏导航

**状态**: 已修复 ✅

**分析**: 在 `AppLayout.vue` 中，`v-navigation-drawer` 的 `permanent` 属性绑定 `$vuetify.display.mdAndUp`，已确保 PC 宽屏显示侧边栏。但需要确认 `drawer` 的初始值在 PC 端是否默认打开。

**当前代码** (`AppLayout.vue`):
```javascript
const drawer = ref(false)
```

**修复**：将 PC 端的 `drawer` 默认值改为 `true`，或在 `onMounted` 中根据屏幕尺寸设置。

```javascript
const drawer = ref(false)

onMounted(() => {
  // PC 端默认打开侧边栏
  if (window.innerWidth >= 960) {
    drawer.value = true
  }
})
```

### Bug 2：首页最近账单显示为空

**分析**: `DashboardPage.vue` 中调用 `getRecords` 时传递了 `sort_by: 'date'`，但该参数未在请求中正确传递到后端，或后端未正确处理。

**根因修复**：
1. `frontend/src/api/records.js` 中 `getRecords` 调用检查参数传递
2. 后端 `get_records` 中 `sort_by='date'` 在新版中应改为 `sort_by='consume_time'`

### Bug 3：统计金额显示为 0

**详见 4.3 节**。核心是修复 `statistics_service.py` 中的 SQL 查询逻辑。

### Bug 4：深色模式文字/背景颜色冲突

**方案**：调整深色模式下的 CSS 变量，确保对比度达标。涉及文件：
- `frontend/src/plugins/vuetify.js` 中的深色主题颜色
- 各 Vue 组件中的 `scoped` 样式，确保使用 CSS 变量而非硬编码颜色

### Bug 5：PC 端默认深色模式且无法切换

**分析**: `AppLayout.vue` 的 `onMounted` 中：
```javascript
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
appStore.setDarkMode(prefersDark)
```

这导致 PC 端如果系统是深色模式则默认深色。但侧边栏底部已有切换按钮，且手机端顶部也有切换按钮。

**修复方案**：
1. 将默认主题改为浅色（忽略系统偏好）
2. 确保切换按钮在 PC 端可正常工作（侧边栏底部已有，见 6.6 节）

### Bug 6：账单详情默认勾选无法查看

**通过新增详情页解决**（详见 6.1 节）。
- 点击卡片 → 跳转详情页
- 长按 → 出现勾选框（批量操作模式）

---

## 8. 样式与主题变更

### 8.1 侧边栏主题切换补充

在 `AppLayout.vue` 的侧边栏底部已有主题切换控件（太阳/月亮图标+Switch），可正常工作，无需额外修改。

需要确认的是：
- `rail` 模式下（窄侧边栏），使用图标按钮切换
- 非 `rail` 模式下，使用图标+Switch

### 8.2 FAB 按钮

当前实现中，FAB 按钮在 `AppLayout.vue` 中全局注册，在所有页面右下角显示。点击跳转 `/add`。保持现状。

### 8.3 深色模式 CSS 变量修复

需要修复的关键文件：
1. `frontend/src/components/layout/AppLayout.vue` — `.sidebar-header`, `.nav-item`, `.content-wrapper`
2. `frontend/src/pages/RecordListPage.vue` — `.record-card`, `.filter-card`
3. `frontend/src/pages/DashboardPage.vue` — `.today-card`, `.category-stat-item`
4. `frontend/src/pages/RecordFormPage.vue` — `.amount-card`, `.category-chip`

**修复原则**：
- 使用 Vuetify 内置 CSS 变量（`rgb(var(--v-theme-*))`）
- 避免硬编码的颜色值（如 `#333`、`#fff`）
- 文本颜色使用 `rgba(0,0,0,0.87)`（浅色）和 `rgba(255,255,255,0.87)`（深色）

---

## 9. API 接口文档（最终版）

### 9.1 分类管理 (Categories)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/categories?type=expense` | 获取分类列表 |
| POST | `/api/categories` | 创建分类 |
| PUT | `/api/categories/{id}` | 更新分类 |
| DELETE | `/api/categories/{id}` | 删除分类 |

> 无变更

### 9.2 标签管理 (Tags)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/tags` | 获取标签列表（含 category_id）|
| GET | `/api/tags/{id}` | 获取单个标签详情（含关联分类）|
| POST | `/api/tags` | 创建标签（支持 category_id）|
| PUT | `/api/tags/{id}` | 更新标签（支持修改 category_id）|
| DELETE | `/api/tags/{id}` | 删除标签 |

### 9.3 记账管理 (Records)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/records?page=1&page_size=20&...` | 获取记录列表（分页+筛选）|
| GET | `/api/records/{id}` | 获取单条记录详情 |
| POST | `/api/records` | 创建记录（v1.1 schema）|
| PUT | `/api/records/{id}` | 更新记录（v1.1 schema）|
| DELETE | `/api/records/{id}` | 删除单条记录 |
| POST | `/api/records/batch-delete` | 批量删除 |
| GET | `/api/records/quick-templates` | 快速记账模板 |

**GET /api/records/** 返回示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "amount": 35.00,
        "type": "expense",
        "category_id": 3,
        "category_name": "餐饮",
        "category_icon": "mdi-food",
        "tag": { "id": 5, "name": "奶茶", "category_id": 3 },
        "attachment_ids": [],
        "consume_time": "2026-01-15 14:30",
        "note": "下午茶",
        "created_at": "2026-01-15 14:30:00",
        "updated_at": "2026-01-15 14:30:00"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

### 9.4 数据统计 (Statistics)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/statistics/summary` | 收支汇总（Bug 修复）|
| GET | `/api/statistics/by-category` | 分类统计 |
| GET | `/api/statistics/by-tag` | 标签统计 |
| GET | `/api/statistics/trend` | 趋势统计 |

### 9.5 附件管理 (Attachments)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/attachments/upload` | 上传附件 |
| GET | `/api/attachments/{id}` | 获取附件信息 |
| DELETE | `/api/attachments/{id}` | 删除附件 |

> 无重大变更

---

## 10. 测试计划

### 10.1 后端测试

| 模块 | 测试内容 | 优先级 |
|------|---------|:------:|
| Tag service | 创建/更新/删除标签（含 category_id） | P1 |
| Record service | 创建/更新/查询记录（v1.1 schema） | P0 |
| Record service | 单标签关联操作 | P1 |
| Record service | consume_time 过滤/排序 | P1 |
| Statistics service | 汇总/分类统计金额正确性 | P0 |
| Statistics service | 日期范围筛选（consume_time） | P1 |
| Migration | v1.1 数据库迁移脚本 | P2 |

### 10.2 前端测试

| 页面 | 测试内容 | 优先级 |
|------|---------|:------:|
| RecordDetailPage | 详情展示、编辑跳转、删除确认 | P0 |
| RecordListPage | 点击跳转详情、长按批量模式、新布局展示 | P0 |
| RecordFormPage | 单标签选择、自动匹配分类、时间选择器 | P0 |
| DashboardPage | 最近账单显示、统计金额显示 | P0 |
| 全局 | 深色模式切换、PC端侧边栏、主题色 | P1 |

### 10.3 验收测试用例

**场景 1：完整记账流程**
1. 打开应用 → 首页显示统计卡片和最近账单
2. 点击右下角 + 号 → 进入记账页
3. 选择类型为「支出」
4. 输入金额 35
5. 选择标签「奶茶」→ 自动匹配分类「餐饮」
6. 修改消费时间为 `2026-01-15 14:30`
7. 输入备注「下午茶」
8. 提交 → 提示「记账成功」
9. 账单列表页 → 新记录显示 `[🍽️] 奶茶 -¥35.00 2026-01-15`

**场景 2：账单详情查看**
1. 在账单列表页点击一条记录
2. 进入详情页 → 显示完整信息（金额、分类图标、标签、时间 HH:mm、备注）
3. 点击「编辑」→ 跳转到编辑页
4. 修改金额后保存 → 返回列表
5. 再次点击该记录 → 点击「删除」→ 确认 → 记录消失

**场景 3：主题切换**
1. PC 浏览器打开 → 显示灰褐色浅色主题
2. 侧边栏底部 → 点击主题切换按钮 → 切换到深色模式
3. 所有页面文字清晰可读，无颜色冲突
4. 刷新页面 → 保持深色模式
5. 再次切换回浅色模式 → 刷新 → 保持浅色

**场景 4：统计展示**
1. 录入多条不同分类和标签的记录
2. 进入统计页面 → 显示正确的总收支金额
3. 按分类查看 → 各分类金额正确
4. 按标签查看 → 各标签金额正确

---

## 附录：文件变更清单

### 后端文件

| 文件路径 | 操作 | 说明 |
|---------|:----:|------|
| `backend/app/models/tag.py` | ✅ 修改 | 新增 category_id 字段 |
| `backend/app/models/record.py` | ✅ 修改 | date→consume_time, 新增 tag_id, note |
| `backend/app/models/record_tag.py` | ⏸️ 保留 | 不再使用但保留表结构 |
| `backend/app/schemas/tag.py` | ✅ 修改 | 所有 schema 适配 category_id |
| `backend/app/schemas/record.py` | ✅ 修改 | 适配 v1.1 新字段 |
| `backend/app/services/tag_service.py` | ✅ 修改 | 支持 category_id 的 CRUD + get_tag |
| `backend/app/services/record_service.py` | ✅ 修改 | 标签/时间字段重构 |
| `backend/app/services/statistics_service.py` | ✅ 修改 | 修复 Bug + consume_time 适配 |
| `backend/app/routers/tags.py` | ✅ 修改 | 新增 GET /tags/{id} |
| `backend/app/routers/records.py` | ✅ 修改 | 适配新 schema |
| `backend/app/routers/statistics.py` | ✅ 修改 | 修复统计 Bug |
| `backend/app/migration_v11.py` | ✅ 新增 | 数据库迁移脚本 |
| `backend/app/main.py` | ✅ 修改 | 引入迁移脚本 |

### 前端文件

| 文件路径 | 操作 | 说明 |
|---------|:----:|------|
| `frontend/src/pages/RecordDetailPage.vue` | ✅ 新增 | 账单详情页 |
| `frontend/src/pages/RecordListPage.vue` | ✅ 修改 | 布局重构、交互变更 |
| `frontend/src/pages/RecordFormPage.vue` | ✅ 修改 | 表单字段变更 |
| `frontend/src/pages/DashboardPage.vue` | ✅ 修改 | 修复 Bug + 数据适配 |
| `frontend/src/pages/StatisticsPage.vue` | ✅ 修改 | 适配新数据格式 |
| `frontend/src/components/layout/AppLayout.vue` | ✅ 修改 | PC 端侧边栏修复 |
| `frontend/src/router/index.js` | ✅ 修改 | 新增 /detail/:id 路由 |
| `frontend/src/plugins/vuetify.js` | ✅ 修改 | 主题色变更为灰褐色 |
| `frontend/src/stores/useRecordsStore.js` | ✅ 修改 | 适配 v1.1 数据格式 |
| `frontend/src/api/records.js` | ✅ 修改 | 无重大变更 |
| `frontend/src/api/tags.js` | ✅ 修改 | 适配 category_id |
| `frontend/src/styles/dark-fix.css` | ✅ 新增 | 深色模式对比度修复 |

---

> 📌 **本文档为 v1.1 版本详细设计定稿，对应 proposalv11.md 的需求，供开发实现参考。**
