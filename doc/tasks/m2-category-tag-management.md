# 模块二：分类标签管理模块 (M2) — 任务分解

> **对应需求**：2.1.1 记账条目字段中的分类和标签  
> **前置依赖**：M0 后端基础搭建完成  
> **预估工时**：2-3小时

## 任务清单

### 1. 数据模型

- [ ] 创建 `app/models/category.py` — `Category` 模型（id, name, type, icon, sort_order, is_preset, created_at）
  - [ ] 唯一索引 `idx_categories_name_type`（name, type 联合唯一）
- [ ] 创建 `app/models/tag.py` — `Tag` 模型（id, name, created_at）
  - [ ] 索引 `idx_tags_name`

### 2. Pydantic Schema

- [ ] 创建 `app/schemas/category.py` — `CategoryCreate`, `CategoryUpdate`, `CategoryResponse`
- [ ] 创建 `app/schemas/tag.py` — `TagCreate`, `TagUpdate`, `TagResponse`

### 3. 预设数据初始化

- [ ] 在数据库初始化逻辑中添加预设分类插入（14 条）：
  - 支出：餐饮、交通、购物、娱乐、医疗、居住、通讯、教育、其他支出
  - 收入：工资、兼职、红包、理财、其他收入
- [ ] 确保 `is_preset=1` 的预设分类不可被删除（或提示用户）
- [ ] 确保重复启动时不会重复插入预设数据

### 4. 业务逻辑层 (Service)

- [ ] 创建 `app/services/category_service.py`：
  - [ ] `get_categories(db, type_filter)` — 获取分类列表（可按类型筛选）
  - [ ] `create_category(db, data)` — 新增自定义分类
  - [ ] `update_category(db, id, data)` — 编辑分类
  - [ ] `delete_category(db, id)` — 删除分类（检查是否有关联的记录，有关联则拒绝删除）
- [ ] 创建 `app/services/tag_service.py`：
  - [ ] `get_tags(db)` — 获取所有标签列表
  - [ ] `create_tag(db, data)` — 新增标签
  - [ ] `update_tag(db, id, data)` — 编辑标签名称
  - [ ] `delete_tag(db, id)` — 删除标签

### 5. 路由层 (Router)

- [ ] 创建 `app/routers/categories.py`：
  - [ ] `GET /api/categories` — 获取分类列表（支持 `?type=income|expense` 筛选）
  - [ ] `POST /api/categories` — 新增分类
  - [ ] `PUT /api/categories/{id}` — 编辑分类
  - [ ] `DELETE /api/categories/{id}` — 删除分类
- [ ] 创建 `app/routers/tags.py`：
  - [ ] `GET /api/tags` — 获取所有标签
  - [ ] `POST /api/tags` — 新增标签
  - [ ] `PUT /api/tags/{id}` — 编辑标签
  - [ ] `DELETE /api/tags/{id}` — 删除标签

### 6. 保护逻辑

- [ ] 删除分类时检查 `records` 表中是否存在关联记录
- [ ] 存在关联记录时返回错误码 `40003` 及提示信息"该分类下有 X 条记录，无法删除"
- [ ] 预设分类（is_preset=1）删除时给出适当提示

### 7. 验证与测试

- [ ] 确认首次启动后预设分类数据已正确插入
- [ ] 测试分类 CRUD 全部接口
- [ ] 测试按类型筛选分类
- [ ] 测试删除有关联记录的分类被拒绝
- [ ] 测试标签 CRUD 全部接口
- [ ] 测试新增同名分类时唯一约束是否生效
