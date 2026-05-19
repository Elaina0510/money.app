# 模块一：记账管理模块 (M1) — 任务分解

> **对应需求**：2.1 记账管理  
> **前置依赖**：M0 后端基础搭建完成，M2 分类标签管理 API 就绪  
> **预估工时**：3-4小时

## 任务清单

### 1. 数据模型

- [ ] 创建 `app/models/record.py` — `Record` 模型（id, amount, type, category_id, date, created_at, updated_at）
- [ ] 创建 `app/models/record_tag.py` — `RecordTag` 关联模型（record_id, tag_id）
- [ ] 验证建表：启动后端后确认 `records` 表和 `record_tags` 表已创建

### 2. Pydantic Schema

- [ ] 创建 `app/schemas/record.py` — 包含：
  - `RecordCreate`：新增记录请求体（amount, type, category_id, tags: list[str], date, created_at 可选）
  - `RecordUpdate`：更新记录请求体（所有字段可选）
  - `RecordResponse`：响应模型（含 category_name, tags: list[str], attachment_ids: list[int]）
  - `RecordListResponse`：分页列表响应（items, total, page, page_size, total_pages）
- [ ] 创建 `app/schemas/statistics.py` — 快速记账模板响应

### 3. 业务逻辑层 (Service)

- [ ] 创建 `app/services/record_service.py`，实现以下方法：
  - [ ] `create_record(db, data)` — 创建记录并处理标签关联
  - [ ] `get_records(db, filters, pagination)` — 分页查询及多条件筛选（start_date, end_date, category_id, type, tag, keyword, sort）
  - [ ] `get_record(db, id)` — 获取单条记录详情（含标签和附件信息）
  - [ ] `update_record(db, id, data)` — 更新记录（含标签更新）
  - [ ] `delete_record(db, id)` — 删除单条记录（级联删除关联标签和附件？按设计附件设为 NULL）
  - [ ] `batch_delete(db, ids)` — 批量删除
  - [ ] `get_quick_templates(db)` — 获取最近 10 条记录作为快速记账模板
- [ ] 确保金额校验（> 0 且不超过 99999999.99）
- [ ] 确保分类 ID 存在性校验

### 4. 路由层 (Router)

- [ ] 创建 `app/routers/records.py`，注册路由：
  - [ ] `POST /api/records` — 新增记录
  - [ ] `GET /api/records` — 获取记录列表（解析 query params: page, page_size, start_date, end_date, category_id, type, tag, keyword, sort_by, sort_order）
  - [ ] `GET /api/records/{id}` — 获取单条记录
  - [ ] `PUT /api/records/{id}` — 编辑记录
  - [ ] `DELETE /api/records/{id}` — 删除记录
  - [ ] `POST /api/records/batch-delete` — 批量删除
  - [ ] `GET /api/records/quick-templates` — 获取快速记账模板（更新：原设计 POST /quick-add 改为 GET /quick-templates）

### 5. 错误处理

- [ ] 金额为 0 时返回 400 错误
- [ ] 金额超过上限时返回 400 错误
- [ ] 分类 ID 不存在时返回 404
- [ ] 批量删除传入空列表时返回 400
- [ ] 删除不存在的记录时返回 404

### 6. 验证与测试

- [ ] 通过 Swagger `/docs` 测试所有 CRUD 接口
- [ ] 测试各筛选参数的组合查询
- [ ] 测试金额边界值（0, 99999999.99, 负数）
- [ ] 测试快速记账模板接口返回最近 10 条数据
- [ ] 测试批量删除的正确性
