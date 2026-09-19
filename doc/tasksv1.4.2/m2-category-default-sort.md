# M2 - 新增分类默认排序 +「其他」固定置尾

> 对应需求二（设计 §二）。分类表单删除「排序」字段；新增分类由后端自动追加到分组末尾（「其他」之前）；「其他」名称禁改、sort 恒置尾。
> 涉及文件：`backend/app/services/category_service.py`、`backend/app/schemas/category.py`、`backend/app/routers/categories.py`、`frontend/src/pages/SettingsCategoriesPage.vue`、`frontend/src/stores/useCategoriesStore.js`、`test_categories.py`、`SettingsSubPages.test.js`。
> 依赖：前端排在 M1 之后（同弹窗文件，M1 已改图标字段区）；后端可提前并行。M3 复用本模块的「其他」判定助手。

---

## 1. 后端：「其他」判定助手（M2/M3 共用，服务层唯一真源）

- [x] 1.1 `category_service.py` 新增常量 `OTHER_CATEGORY_NAMES: dict[str, str] = {"expense": "其他支出", "income": "其他收入"}`
- [x] 1.2 新增 `_is_other_category(cat: Category) -> bool`：`cat.name == OTHER_CATEGORY_NAMES.get(cat.type)`（预设行与其 CoW 用户副本同名一并命中，决策 D3）
- [x] 1.3 新增 `_is_other_row(type_: str, name: str) -> bool`
- [x] 1.4 红线：create/update/reorder 三处禁止散落「其他」字面量，一律经这两个助手（易错点 2）

## 2. 后端：`create_category` 排序服务端计算

- [x] 2.1 抽取「该用户+类型可见分类集合」查询为 `_visible_categories(db, type, user)`（与 `get_categories` 同一逻辑，M3 复用）
- [x] 2.2 `CategoryCreate.sort_order` 改 `int | None = Field(default=None, ge=0)`（`schemas/category.py:12`）
- [x] 2.3 `sort_order=None` 时按设计 §2.2.2 计算：
  - [x] `base = max(非「其他」行 sort_order, default=0)`
  - [x] 组内存在「其他」且 `other.sort_order <= base` → `base = other.sort_order - 1`（异常数据自愈）
  - [x] 组内无「其他」→ 直接 `max+1`
  - [x] 结果 `sort_order = base + 1`，恒严格小于「其他」的 sort
- [x] 2.4 入参显式携带 `sort_order` → 维持现行为原样写入（向后兼容）

## 3. 后端：`update_category` 两条约束

- [x] 3.1 禁改「其他」名（决策 D3）：校验置于更新与 CoW 两条路径**之前**——目标为「其他」（预设或副本）且 `data.name` 非空且 ≠ 标准名 → `raise ValueError('「其他」分类名称不可修改')`
- [x] 3.2 `update_data` 一律 `pop("sort_order")`：单个分类 PUT 不再接受排序修改
- [x] 3.3 `CategoryUpdate.sort_order`（`schemas/category.py:20`）字段定义保留（避免 422 语义变化），服务层忽略
- [x] 3.4 CoW 副本分支（:120-131）确认：sort_order 被剔除后副本恒继承预设自身 sort（编辑预设不拽离原位），无需特殊处理
- [x] 3.5 `routers/categories.py` 的 `update_category` 补 `except ValueError → error_response(Code.PARAM_ERROR, str(e))`（现该端点无 ValueError 分支）

## 4. 前端：表单删「排序」字段

- [x] 4.1 删除「排序」`v-text-field`（`SettingsCategoriesPage.vue:162-169`）
- [x] 4.2 `categoryForm` 去掉 `sort_order` 字段（:236）；`editCategory` 回填与 `resetCategoryForm` 同步清理
- [x] 4.3 `saveCategory` 载荷：
  - [x] 新增：`{ name, type, icon }`（不再出现 sort_order）
  - [x] 编辑：`{ name, icon }`（不含 type——编辑不改类型；不含 sort_order）

## 5. 前端：store CoW 副本适配

- [x] 5.1 `useCategoriesStore.editCategory`（:50-62）：响应 `cat.id !== id`（预设 CoW 生成副本）时**跳过原地替换**（旧 id 已不在可见集合，原地替换会双份），交由调用方 `loadCategories()` 重拉对齐

## 6. 测试

### 6.1 后端 pytest（`test_categories.py` 新增用例组）

- [x] 6.1.1 不传 sort_order 创建 → 落位 = max(非其他)+1，GET 列表位于「其他」之前；连续创建依次后移
- [x] 6.1.2 收入分组独立计算
- [x] 6.1.3 显式传 sort_order → 按传入值写入（兼容回归）
- [x] 6.1.4 PUT 载荷携带 sort_order → 值不变（被忽略）
- [x] 6.1.5 PUT 改「其他」（预设/副本）名 → 400；改图标 → 200 且副本 sort 继承 99
- [x] 6.1.6 未认证 401；跨用户隔离（用户 A 的分组不影响 B 的 max 计算）

### 6.2 vitest（`SettingsSubPages.test.js` 用例 2c 改写，排序部分）

- [x] 6.2.1 `createCategory` 断言载荷 `{name, type, icon}`（无 sort_order）
- [x] 6.2.2 `updateCategory` 断言载荷 `{name, icon}`
- [x] 6.2.3 源码断言：表单不再渲染「排序」输入（不含 `label="排序"`）

## 7. 验收与质量门槛

- [x] 7.1 `cd backend && python -m pytest tests/test_categories.py -v` 全绿；`mypy`（基线零新增口径）+ `ruff` 通过
- [x] 7.2 `cd frontend && npm test`、`npm run lint` 通过
- [ ] 7.3 手工验收：新建「宠物」（支出）排在该分组最后、「其他」之前；再建一个继续往后；收入分组独立；任何操作后「其他」仍在分组末尾；编辑已有分类不改位
