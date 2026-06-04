# Money App v1.2.2 — VibeCoding Prompt

> 本文件是 v1.2.2 全量开发的起始 Prompt，供主 Agent 自动执行，无需人工干预。

---

## 一、项目背景

Money App 是一个个人记账应用，技术栈：

- **前端**：Vue 3 + Vuetify 3 + Pinia（Composition API `<script setup>`）
- **后端**：FastAPI + SQLModel + SQLite（async service 层）
- **测试**：pytest（async mode），mypy strict，ruff lint

本次 v1.2.2 共 **9 个模块**，涵盖设置页增强、移动端适配、深色模式优化等。

---

## 二、主 Agent 指令

你是主 Agent，负责协调整个 v1.2.2 的开发。你的职责：

### 2.1 总体流程

```
1. 读取 doc/detailed-designv1.2.2.md 和 doc/tasksv1.2.2/ 了解全部模块
2. 按批次生成子 Agent 执行各模块（见 2.2 批次规划）
3. 每个子 Agent 完成后，验证其结果（运行测试、mypy、ruff）
4. 更新 doc/tasksv1.2.2/progress.md 进度
5. 全部模块完成后，运行全量回归测试
6. 输出最终报告
```

### 2.2 批次规划（按依赖关系）

**第一批（5 个独立模块，并行执行）：**
- 模块 1：设置页 - 分类管理增强
- 模块 2：设置页 - 标签管理增强
- 模块 6：账单页 - 按钮位置修正
- 模块 7：账单页 - 分类筛选优化
- 模块 8：深色模式 - 字体可读性优化

**第二批（依赖模块 2）：**
- 模块 5：记账页 - 标签搜索联想

**第三批（复杂模块，并行执行）：**
- 模块 3：预算管理整合
- 模块 4：快速记账优化
- 模块 9：移动端底部导航栏

### 2.3 子 Agent 调度规则

- 每个模块生成一个独立子 Agent
- 子 Agent 必须在自己的 git worktree 中工作，避免文件冲突
- **分支策略**：每模块一个分支，从 main 创建 `feature/v1.2.2-module-N` 分支，完成后合并回 main
- 子 Agent 完成后，主 Agent 合并代码并运行验证
- 如果验证失败，主 Agent 生成修复子 Agent 重新处理

### 2.4 质量门禁（每个模块必须通过）

```bash
# 后端测试
cd backend && python -m pytest tests/ -v

# 类型检查
cd backend && python -m mypy app/ --strict

# 代码风格
cd backend && python -m ruff check app/ tests/
cd backend && python -m ruff format --check app/ tests/
```

---

## 三、子 Agent 通用指令

每个子 Agent 执行一个模块时，必须遵循以下规范：

### 3.1 开发流程

```
1. 阅读模块对应的详细设计（doc/detailed-designv1.2.2.md 中的对应章节）
2. 阅读模块任务列表（doc/tasksv1.2.2/module-N-xxx.md）
3. 阅读现有代码，理解上下文
4. 按任务列表逐项实现
5. 编写完整的 pytest 单元测试
6. 运行测试、mypy、ruff，确保全部通过
7. 更新模块任务列表，勾选已完成项
```

### 3.2 代码规范

- **后端**：
  - 所有函数必须有类型注解（mypy strict 模式）
  - 使用 async/await，不要用同步阻塞调用
  - SQLModel 定义在 `backend/app/models/` 下
  - 业务逻辑在 `backend/app/services/` 下
  - API 路由在 `backend/app/routers/` 下
  - 不引入新的外部依赖

- **前端**：
  - 使用 Composition API `<script setup>` 语法
  - 状态管理使用 Pinia stores（`frontend/src/stores/`）
  - 页面组件在 `frontend/src/pages/` 下
  - 使用 Vuetify 3 组件，不引入新依赖
  - 保持响应式设计（桌面端 + 移动端）

### 3.3 测试规范

- **后端测试**必须覆盖：
  - 正常路径（happy path）
  - 边界条件（空数据、无效输入、权限检查）
  - 数据隔离（不同用户的数据互不可见）
  - 每个 API 端点至少 3 个测试用例

- **测试文件命名**：`backend/tests/test_<module>.py`
- **使用 conftest.py 中的 fixtures**：`client`、`db_session`、`test_user` 等
- **测试必须独立**：每个测试用例之间不共享状态

### 3.4 数据库迁移

如果模块涉及数据库变更（新增表、新增字段），必须：
1. 在 SQLModel 中定义新字段/新表
2. 编写迁移 SQL 并在测试 setup 中执行
3. 确保现有测试不受影响

---

## 四、模块详细指令

### 模块 1：设置页 - 分类管理增强

**目标**：在分类列表中增加上移/下移排序按钮

**关键文件**：
- `frontend/src/pages/SettingsPage.vue` — 增加排序按钮 UI
- `frontend/src/stores/useCategoriesStore.js` — 使用现有 `editCategory` 方法

**实现要点**：
- 每个分类项 append 区域增加上移（`mdi-chevron-up`）/下移（`mdi-chevron-down`）按钮
- 首项隐藏上移按钮，末项隐藏下移按钮
- 点击时与相邻项交换 `sort_order`，调用 `editCategory` 保存
- 支出/收入分类各自独立排序

**后端改动**：无。现有 `PUT /api/categories/{id}` 已支持 `sort_order` 更新。

**测试**：前端功能测试，无需新增后端测试。

---

### 模块 2：设置页 - 标签管理增强

**目标**：标签新增时分类必填；标签删除改为软删除

**关键文件**：
- `backend/app/models/tag.py` — 增加 `deleted_at` 字段
- `backend/app/services/tag_service.py` — 软删除逻辑 + 过滤已删除
- `backend/app/services/record_service.py` — `_enrich_record` 不过滤已删除标签
- `backend/app/routers/tags.py` — DELETE 改为软删除
- `frontend/src/pages/SettingsPage.vue` — 标签对话框增加分类选择器
- `frontend/src/stores/useCategoriesStore.js` — `addTag` 传递 `category_id`

**后端测试要求**：
- 测试标签软删除（DELETE 后 GET 不返回，但数据库中仍存在）
- 测试已删除标签的账单仍显示标签名称
- 测试 `get_tags` 过滤已删除标签
- 测试新增标签必须有 `category_id`

---

### 模块 3：预算管理整合

**目标**：移除预算独立页面导航，预算管理嵌入设置页

**关键文件**：
- `frontend/src/components/layout/AppLayout.vue` — 移除预算导航项
- `frontend/src/pages/SettingsPage.vue` — 嵌入预算管理 section
- `frontend/src/router/index.js` — `/budget` 重定向到 `/settings`

**实现要点**：
- 从 `navItems` 数组移除预算项
- 在设置页增加预算管理卡片，复用 BudgetPage 的核心逻辑
- `/budget` 路由保留但重定向到 `/settings`

**测试**：前端功能测试，无需新增后端测试。

---

### 模块 4：快速记账优化

**目标**：快速记账模板改为出现 >= 2 次才纳入；设置页增加快速记账管理

**方案**：采用方案 A — 新建 `quick_templates` 独立表存储手动模板，自动模板从 records 表实时聚合，API 合并返回。

**关键文件**：
- `backend/app/models/quick_template.py` — 新建 QuickTemplate model（独立表）
- `backend/app/services/record_service.py` — 重写 `get_quick_templates`（聚合 + 合并逻辑）
- `backend/app/routers/records.py` — 新增快速模板 CRUD API（GET/POST/DELETE）
- `frontend/src/pages/RecordFormPage.vue` — 适配新数据结构
- `frontend/src/pages/SettingsPage.vue` — 快速记账管理 section

**数据流**：
```
records 表 → 按 (tag_id, type, amount) 聚合，HAVING count >= 2 → 自动模板
quick_templates 表 → 手动添加的模板
                ↓ 合并去重，按最近使用排序
           GET /api/quick-templates 返回
```

**后端测试要求**：
- 测试首次记录不进入快速记账
- 测试第 2 次相同记录后出现快速记账
- 测试手动添加模板 API（POST /api/quick-templates）
- 测试删除模板 API（DELETE /api/quick-templates/{id}）
- 测试已删除标签的模板不显示
- 测试自动模板与手动模板合并去重
- 测试删除手动模板不影响 records 表数据

---

### 模块 5：记账页 - 标签搜索联想

**目标**：标签输入改为搜索联想模式，选择后自动填入分类

**依赖**：模块 2（需要标签带分类信息的 API）

**关键文件**：
- `backend/app/routers/tags.py` — 增加 `q` 查询参数
- `backend/app/services/tag_service.py` — 支持 `search` 参数
- `frontend/src/pages/RecordFormPage.vue` — `v-combobox` 改为 `v-autocomplete`

**后端测试要求**：
- 测试搜索关键词匹配
- 测试搜索结果限制 20 条
- 测试不传 `q` 参数返回全部标签
- 测试搜索不返回已删除标签

---

### 模块 6：账单页 - 按钮位置修正

**目标**：编辑和删除按钮居中显示，风格统一

**关键文件**：
- `frontend/src/pages/RecordDetailPage.vue` — 修改按钮布局

**实现要点**：
- 移除 `block` 属性，添加 `justify-center`
- 使用 `flex-grow-1` + `max-width: 200px`
- 按钮使用 `rounded="xl"` `variant="tonal"` `size="large"`

**测试**：前端功能测试，无需新增后端测试。

---

### 模块 7：账单页 - 分类筛选优化

**目标**：选择分类后立即触发筛选，移除搜索按钮

**关键文件**：
- `frontend/src/pages/RecordListPage.vue` — 移除搜索按钮，添加 watch

**实现要点**：
- 删除搜索按钮 HTML
- 添加 `watch` 监听 `filters.type` 和 `filters.category_id`
- 使用 300ms 防抖

**测试**：前端功能测试，无需新增后端测试。

---

### 模块 8：深色模式 - 字体可读性优化

**目标**：深色模式下副标题文字更清晰

**关键文件**：
- `frontend/src/styles/global.scss` — 增强深色模式文字颜色
- `frontend/src/pages/*.vue` — 移除内联颜色硬编码

**实现要点**：
- 在 global.scss 增强 `.v-theme--dark` 文字颜色覆盖
- 定义 `.page-subtitle` 全局类
- 移除各页面的 `.page-subtitle` 内联颜色和 inline style

**测试**：前端功能测试，无需新增后端测试。

---

### 模块 9：移动端底部导航栏

**目标**：竖屏模式下用底部导航栏替代侧边栏

**关键文件**：
- `frontend/src/components/layout/AppLayout.vue` — 条件渲染侧边栏/底部导航

**实现要点**：
- 移动端（< 960px）隐藏侧边栏，显示 `v-bottom-navigation`
- 底部导航包含 4 个图标：主页、账单、统计、设置
- FAB 按钮上移避开底部导航栏
- 移动端隐藏汉堡按钮
- 深色模式下边框颜色适配

**测试**：前端功能测试，无需新增后端测试。

---

## 五、数据库变更

| 变更 | SQL | 模块 |
|------|-----|------|
| tags 表增加 deleted_at 列 | `ALTER TABLE tags ADD COLUMN deleted_at TEXT DEFAULT NULL;` | 模块 2 |
| quick_templates 表（新建） | 见模块 4 详细设计 | 模块 4 |

---

## 六、API 变更

| 方法 | 路径 | 变更类型 | 说明 | 模块 |
|------|------|----------|------|------|
| GET | `/api/tags` | 修改 | 增加 `q` 查询参数；过滤 `deleted_at` | 2, 5 |
| DELETE | `/api/tags/{id}` | 修改 | 改为软删除 | 2 |
| GET | `/api/quick-templates` | 修改 | 聚合逻辑（>= 2 次） | 4 |
| POST | `/api/quick-templates` | 新增 | 手动添加模板 | 4 |
| DELETE | `/api/quick-templates/{id}` | 新增 | 删除模板 | 4 |

---

## 七、验收标准汇总

每个模块完成后，必须满足其对应的验收标准（见各模块详细设计）。全部模块完成后：

1. 所有后端 pytest 测试通过
2. mypy --strict 无错误
3. ruff check 无警告
4. ruff format --check 无格式问题
5. 前端功能在桌面端和移动端均正常
6. 深色模式和浅色模式均正常
7. doc/tasksv1.2.2/progress.md 中所有模块标记为已完成

---

## 八、最终交付

主 Agent 在所有模块完成后：

1. 运行全量后端测试：`cd backend && python -m pytest tests/ -v`
2. 运行 mypy：`cd backend && python -m mypy app/ --strict`
3. 运行 ruff：`cd backend && python -m ruff check app/ tests/`
4. 更新 `doc/tasksv1.2.2/progress.md`
5. 输出最终报告，包含：
   - 各模块完成状态
   - 测试通过数量
   - 发现并修复的问题列表
   - 未完成项（如有）
