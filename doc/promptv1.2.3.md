# Money App v1.2.3 — VibeCoding Prompt

> 本文件是 v1.2.3 全量开发的起始 Prompt，供主 Agent 自动执行，无需人工干预。

---

## 一、项目背景

Money App 是一个个人记账应用，技术栈：

- **前端**：Vue 3 + Vuetify 3 + Pinia（Composition API `<script setup>`，纯 JavaScript，无 TypeScript）
- **后端**：FastAPI + SQLModel + SQLite（async service 层，Python 3.12）
- **测试**：pytest（async mode，仅后端），mypy strict，ruff lint（仅后端）
- **前端无自动化测试**，无 ESLint 配置

本次 v1.2.3 共 **5 个模块**，修复 7 个 Bug，优化快速记账、账单筛选、登录提示等功能。所有模块相互独立，无依赖关系。

---

## 二、主 Agent 指令

你是主 Agent，负责协调整个 v1.2.3 的开发。你的职责：

### 2.1 总体流程

```
1. 读取 doc/detailed-designv1.2.3.md 和 doc/tasksv1.2.3/ 了解全部模块
2. 按批次生成子 Agent 执行各模块（见 2.2 批次规划）
3. 每个子 Agent 完成后，验证其结果（运行测试、mypy、ruff）
4. 更新 doc/tasksv1.2.3/progress.md 进度
5. 全部模块完成后，运行全量回归测试
6. 输出最终报告
```

### 2.2 批次规划（按文件冲突分析）

**第一批（3 个子 Agent 并行执行）：**
- 子 Agent A：模块 1 + 模块 2（共享文件 `RecordFormPage.vue`，合并处理）
- 子 Agent B：模块 3（`RecordListPage.vue`）
- 子 Agent C：模块 4（`api/request.js`）

**第二批（1 个子 Agent，前后端都涉及，工作量最大）：**
- 子 Agent D：模块 5（前端 `SettingsPage.vue` + 后端 `category_service.py` + `categories.py`）

### 2.3 子 Agent 调度规则

- 每个子 Agent 使用独立的 git worktree（`feature/v1.2.3-agent-X` 分支），避免文件冲突
- 子 Agent 完成后，主 Agent 合并代码并运行验证
- 如果验证失败，主 Agent 生成修复子 Agent 重新处理
- 所有子 Agent 合并完成后，主 Agent 运行全量回归测试

### 2.4 质量门禁

**后端（每个涉及后端改动的模块必须通过）：**

```bash
cd backend && python -m pytest tests/ -v
cd backend && python -m mypy app/ --strict
cd backend && python -m ruff check app/ tests/
cd backend && python -m ruff format --check app/ tests/
```

**前端（无自动化测试，但需确认）：**
- 子 Agent 完成后，主 Agent 确认前端改动不引入语法错误（检查 `npm run build` 是否通过）

---

## 三、子 Agent 通用指令

每个子 Agent 执行一个模块时，必须遵循以下规范：

### 3.1 开发流程

```
1. 阅读模块对应的详细设计（doc/detailed-designv1.2.3.md 中的对应章节）
2. 阅读模块任务列表（doc/tasksv1.2.3/module-N-xxx.md）
3. 阅读现有代码，理解上下文
4. 按任务列表逐项实现
5. 如果涉及后端改动：编写完整的 pytest 单元测试
6. 运行测试、mypy、ruff，确保全部通过
7. 更新模块任务列表，勾选已完成项
8. 更新 doc/tasksv1.2.3/progress.md
```

### 3.2 代码规范

- **后端**：
  - 所有函数必须有类型注解（mypy strict 模式）
  - 使用 async/await，不要用同步阻塞调用
  - SQLModel 定义在 `backend/app/models/` 下
  - 业务逻辑在 `backend/app/services/` 下
  - API 路由在 `backend/app/routers/` 下
  - 统一响应格式：`success_response()` / `error_response()`（来自 `app/utils/response.py`）
  - 不引入新的外部依赖

- **前端**：
  - 使用 Composition API `<script setup>` 语法
  - 状态管理使用 Pinia stores（`frontend/src/stores/`）
  - 页面组件在 `frontend/src/pages/` 下
  - API 调用在 `frontend/src/api/` 下
  - 使用 Vuetify 3 组件，不引入新依赖
  - 保持现有代码风格和命名规范

### 3.3 测试规范（仅后端）

- **后端测试**必须覆盖：
  - 正常路径（happy path）
  - 边界条件（空数据、无效输入、权限检查）
  - 数据隔离（不同用户的数据互不可见）
  - 每个新增/修改的 API 端点至少 3 个测试用例

- **测试文件命名**：`backend/tests/test_<module>.py`
- **使用 conftest.py 中的 fixtures**：`client`、`auth_client`、`auth_client_a`、`auth_client_b`、`db_session`、`setup_database`（autouse）
- **测试必须独立**：每个测试用例之间不共享状态（setup_database fixture 会自动重建表）
- **所有测试使用 async def + @pytest.mark.asyncio**（conftest.py 已设置 pytestmark）

---

## 四、模块详细指令

### 模块 1 + 模块 2：标签保存时机优化 + 标签显示异常修复

**需求编号**：#1、#2
**目标**：修复快速记账页标签的两个问题——(1) 按回车不应立即保存标签到数据库，(2) 点击空白处标签显示为数字 ID 而非名称。
**关键文件**：`frontend/src/pages/RecordFormPage.vue`

**模块 1 实现要点**：

修改 `onCreateTagFromSearch` 函数，将按回车时的行为从"创建标签并保存到数据库"改为"仅在界面上确认标签"：

```javascript
async function onCreateTagFromSearch() {
  if (!tagSearchQuery.value || tagSearchQuery.value.length < 1) return

  // 精确匹配已有标签
  const exactMatch = tagSearchResults.value.find(t => t.name === tagSearchQuery.value)
  if (exactMatch) {
    selectedTagId.value = exactMatch.id
    selectedTagName.value = exactMatch.name
    if (exactMatch.category_id) {
      categoryId.value = exactMatch.category_id
    }
    return
  }

  // 新标签：仅在界面上确认，不保存到数据库
  selectedTagId.value = null
  selectedTagName.value = tagSearchQuery.value.trim()
}
```

`submit()` 函数已有处理新标签的逻辑（`selectedTagName` 有值但 `selectedTagId` 为空时创建标签），无需修改。

**模块 2 实现要点**：

问题根因：`v-autocomplete` 的 `v-model` 绑定 `selectedTagId`，当搜索结果清空时无法从空 items 中匹配名称，回退显示数字 ID。

修复方案（三处改动）：

1. `onTagSearch`：搜索清空时保留当前已选中的标签在 `tagSearchResults` 中：
```javascript
async function onTagSearch(query) {
  if (!query || query.length < 1) {
    if (selectedTagId.value) {
      const currentItem = tagSearchResults.value.find(t => t.id === selectedTagId.value)
      tagSearchResults.value = currentItem ? [currentItem] : []
    } else {
      tagSearchResults.value = []
    }
    return
  }
  // ... 防抖搜索逻辑不变
}
```

2. `onCreateTagFromSearch`：新标签确认后，加入临时项使 `v-autocomplete` 能显示：
```javascript
// 新标签确认后（接模块 1 的改动）
selectedTagId.value = null
selectedTagName.value = tagSearchQuery.value.trim()
const tempTag = { id: -1, name: selectedTagName.value, category_id: categoryId.value }
tagSearchResults.value = [tempTag]
selectedTagId.value = -1  // 临时 ID
```

3. `submit()`：处理临时 ID（-1）：
```javascript
let tagId = selectedTagId.value
if (selectedTagName.value && (!tagId || tagId === -1)) {
  const newTag = await createTagData({ name: selectedTagName.value.trim(), category_id: categoryId.value })
  tagId = newTag.id
}
```

**验收标准**：
- [ ] 按回车只确认标签，不保存到数据库
- [ ] 点击空白处标签显示名称而非数字 ID
- [ ] 保存后账单和标签一起入库
- [ ] 不保存直接离开，无残留标签
- [ ] 已有标签按回车正常选中
- [ ] 账单页回看标签显示正确

**后端改动**：无。无需新增后端测试。

---

### 模块 3：账单页 - 筛选功能修复与优化

**需求编号**：#3、#4、#6
**目标**：修复三个关联问题——类型筛选不生效、切换页面后筛选状态丢失、分类标签未按类型联动。
**关键文件**：`frontend/src/pages/RecordListPage.vue`

**#4 筛选状态持久化**：

将页面级 `filters` reactive 对象替换为 Pinia store `useRecordsStore` 中的 `filters`（结构兼容：`start_date, end_date, type, category_id`）。页面离开时 filters 保留在 store 中，切换回来时自动恢复。

```javascript
import { useRecordsStore } from '@/stores/useRecordsStore'
const recordsStore = useRecordsStore()
const filters = recordsStore.filters
```

**#6 分类按类型联动**：

修改 `categoryOptions` computed，根据当前选中类型过滤分类：

```javascript
const categoryOptions = computed(() => {
  const list = [{ name: '全部分类', id: null }]
  if (filters.type) {
    const filtered = categories.value.filter(c => c.type === filters.type)
    return list.concat(filtered)
  }
  return list.concat(categories.value)
})
```

新增 watch 监听 `filters.type` 变化时自动清空 `filters.category_id`。

**#3 类型筛选生效**：

确认 `v-select` 的 `v-model` 正确绑定 `filters.type`，确认 `search()` 中 `type_filter` 参数传递正确。如前端逻辑无误但筛选仍不生效，检查后端 `record_service.get_records()` 的 `type_filter` 处理。

**验收标准**：
- [ ] 选择"收入"只显示收入账单
- [ ] 选择"支出"只显示支出账单
- [ ] 选择"全部"显示所有账单
- [ ] 分类下拉按类型联动过滤
- [ ] 切换类型时自动清空已选分类
- [ ] 筛选结果实时更新
- [ ] 切换页面后筛选条件保持，筛选框正确显示

**后端改动**：无。无需新增后端测试。

---

### 模块 4：登录页 - 错误提示优化

**需求编号**：#5
**目标**：登录失败时显示后端返回的"用户名或密码错误"，而非通用的"登录已过期，请重新登录"。
**关键文件**：`frontend/src/api/request.js`

**实现要点**：

修改响应拦截器的错误处理器，对 401 状态码优先从 `error.response.data.message` 读取后端返回的错误信息：

```javascript
(error) => {
  if (error.response) {
    const { status, data } = error.response
    let msg = '请求失败'

    if (status === 401) {
      if (data && data.message) {
        // 优先使用后端返回的错误信息（如"用户名或密码错误"）
        msg = data.message
      } else {
        // 无后端信息（token 过期的真实 401）
        msg = '登录已过期，请重新登录'
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.removeItem('userId')
        window.dispatchEvent(new CustomEvent('auth:logout'))
      }
    } else if (status === 422) {
      msg = (data && data.message) || '参数错误'
    } else if (status === 500) {
      msg = (data && data.message) || '服务器错误'
    }

    return Promise.reject(new Error(msg))
  }
  if (error.code === 'ECONNABORTED') {
    return Promise.reject(new Error('请求超时'))
  }
  return Promise.reject(new Error('网络异常'))
}
```

**设计说明**：后端登录接口返回 401 时一定有 `data.message`（如"用户名或密码错误"），而 token 过期的真实 401 通常由网关返回，`data` 为空或无 `message` 字段。因此优先读取 `data.message` 即可区分两种场景，无需硬编码接口路径。

**验收标准**：
- [ ] 输入错误密码显示"用户名或密码错误"
- [ ] 输入不存在用户名显示"用户名或密码错误"
- [ ] 不泄露具体错误类型
- [ ] Token 过期显示"登录已过期，请重新登录"
- [ ] 网络异常显示"网络异常"
- [ ] 超时显示"请求超时"

**后端改动**：无。无需新增后端测试。

---

### 模块 5：设置页 - 恢复默认分类功能

**需求编号**：#7
**目标**：在设置页分类管理栏添加"恢复默认"按钮，二次确认后删除所有自定义分类、重置预设分类排序。关联账单记录保留但失去分类关联，关联预算删除。
**涉及文件**：
- 后端：`backend/app/services/category_service.py`、`backend/app/routers/categories.py`
- 前端：`frontend/src/pages/SettingsPage.vue`、`frontend/src/api/categories.js`、`frontend/src/stores/useCategoriesStore.js`

#### 后端实现

**5.1 新增 `restore_default_categories` 函数**（`category_service.py`）：

```python
async def restore_default_categories(
    db: AsyncSession, current_user: User | None = None
) -> dict[str, int]:
    """恢复默认分类：删除用户自定义分类，重置预设分类属性。

    - 删除所有 is_preset=0 的用户自定义分类
    - 关联的账单记录保留，category_id 设为 NULL
    - 关联的预算删除
    - 重置预设分类的 sort_order 和 icon 为默认值

    返回：{"deleted_categories": N, "affected_records": M}
    """
    from app.main import PRESET_CATEGORIES

    user_id = current_user.id if current_user else None

    # Step 1: 删除用户自定义分类（is_preset=0）
    custom_query = select(Category).where(
        Category.is_preset == 0,
        Category.user_id == user_id,
    )
    custom_result = await db.exec(custom_query)
    custom_categories = list(custom_result.all())

    deleted_count = 0
    affected_records = 0

    for cat in custom_categories:
        # 统计关联记录数
        count_stmt = select(func.count(Record.id)).where(Record.category_id == cat.id)
        count_result = await db.exec(count_stmt)
        record_count = count_result.one() or 0
        affected_records += record_count

        # 将关联记录的 category_id 设为 NULL（保留记录）
        record_stmt = select(Record).where(Record.category_id == cat.id)
        record_result = await db.exec(record_stmt)
        for record in record_result.all():
            record.category_id = None

        # 删除关联预算
        budget_stmt = select(Budget).where(Budget.category_id == cat.id)
        budget_result = await db.exec(budget_stmt)
        for budget in budget_result.all():
            await db.delete(budget)

        # 删除分类
        await db.delete(cat)
        deleted_count += 1

    # Step 2: 重置预设分类的 sort_order 和 icon
    for preset in PRESET_CATEGORIES:
        stmt = select(Category).where(
            Category.name == preset["name"],
            Category.type == preset["type"],
            Category.is_preset == 1,
        )
        result = await db.exec(stmt)
        category = result.first()
        if category:
            category.sort_order = preset["sort_order"]
            category.icon = preset["icon"]

    await db.commit()
    return {"deleted_categories": deleted_count, "affected_records": affected_records}
```

**5.2 新增 API 端点**（`categories.py`）：

```python
@router.post("/restore-defaults")
async def restore_defaults(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """恢复默认分类设置。"""
    result = await category_service.restore_default_categories(db, current_user)
    return success_response(
        data=result,
        message=f"已恢复默认分类，删除 {result['deleted_categories']} 个自定义分类，"
                f"{result['affected_records']} 条记录已解除分类关联",
    )
```

注意：此端点使用 `require_auth`（而非 `get_current_user`），因为恢复默认是破坏性操作，必须登录。

#### 前端实现

**5.3 新增 API 函数**（`api/categories.js`）：

```javascript
export function restoreDefaultCategories() {
  return request.post('/categories/restore-defaults')
}
```

**5.4 新增 Store action**（`useCategoriesStore.js`）：

```javascript
async function restoreDefaults() {
  const result = await restoreDefaultCategoriesAPI()
  await fetchCategories()
  return result
}
```

**5.5 设置页 UI**（`SettingsPage.vue`）：

在分类管理卡片标题栏添加"恢复默认"按钮（警告色 tonal 样式），添加二次确认对话框（显示操作说明和"此操作不可撤销"警告），实现 `handleRestoreDefaults` 函数。

**验收标准**：
- [ ] 分类管理栏显示"恢复默认"按钮
- [ ] 点击按钮弹出确认对话框
- [ ] 点击"取消"关闭对话框，无变化
- [ ] 点击"确认恢复"后自定义分类被删除，预设分类重置
- [ ] 恢复后账单记录仍在但无分类关联
- [ ] 恢复后自定义分类下的预算被删除
- [ ] 恢复后预设分类排序重置为默认
- [ ] 无自定义分类时恢复不报错
- [ ] 未登录时调用返回 401

**后端测试要求**：
- 测试恢复默认分类成功（创建自定义分类 + 记录 + 预算后恢复，验证结果）
- 测试恢复后自定义分类被删除
- 测试恢复后关联记录的 category_id 为 NULL
- 测试恢复后关联预算被删除
- 测试恢复后预设分类 sort_order 重置
- 测试无自定义分类时恢复不报错
- 测试未登录调用返回 401
- 测试不同用户数据隔离（用户 A 恢复不影响用户 B 的自定义分类）

---

## 五、数据库变更

| 变更 | SQL | 模块 |
|------|-----|------|
| 无新增表或列 | — | — |

模块 5 的恢复默认功能通过后端逻辑实现，不涉及数据库结构变更。`Record.category_id` 字段已允许 NULL（`ondelete="SET NULL"`）。

---

## 六、API 变更

| 方法 | 路径 | 变更类型 | 说明 | 模块 |
|------|------|----------|------|------|
| POST | `/api/categories/restore-defaults` | 新增 | 恢复默认分类设置 | 5 |

---

## 七、修改文件汇总

| 文件 | 变更类型 | 涉及模块 |
|------|----------|----------|
| `frontend/src/pages/RecordFormPage.vue` | 修改 | 1, 2 |
| `frontend/src/pages/RecordListPage.vue` | 修改 | 3 |
| `frontend/src/api/request.js` | 修改 | 4 |
| `frontend/src/pages/SettingsPage.vue` | 修改 | 5 |
| `frontend/src/api/categories.js` | 修改 | 5 |
| `frontend/src/stores/useCategoriesStore.js` | 修改 | 5 |
| `backend/app/services/category_service.py` | 修改 | 5 |
| `backend/app/routers/categories.py` | 修改 | 5 |
| `backend/tests/test_restore_defaults.py` | 新增 | 5 |

---

## 八、验收标准汇总

每个模块完成后，必须满足其对应的验收标准（见各模块详细设计）。全部模块完成后：

1. 所有后端 pytest 测试通过（`cd backend && python -m pytest tests/ -v`）
2. mypy --strict 无错误（`cd backend && python -m mypy app/ --strict`）
3. ruff check 无警告（`cd backend && python -m ruff check app/ tests/`）
4. ruff format --check 无格式问题（`cd backend && python -m ruff format --check app/ tests/`）
5. 前端 build 通过（`cd frontend && npm run build`）
6. doc/tasksv1.2.3/progress.md 中所有模块标记为已完成

---

## 九、最终交付

主 Agent 在所有模块完成后：

1. 运行全量后端测试：`cd backend && python -m pytest tests/ -v`
2. 运行 mypy：`cd backend && python -m mypy app/ --strict`
3. 运行 ruff：`cd backend && python -m ruff check app/ tests/ && python -m ruff format --check app/ tests/`
4. 运行前端 build：`cd frontend && npm run build`
5. 更新 `doc/tasksv1.2.3/progress.md`
6. 输出最终报告，包含：
   - 各模块完成状态
   - 后端测试通过数量
   - 发现并修复的问题列表
   - 未完成项（如有）
