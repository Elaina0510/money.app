# 模块 2：设置页 - 标签管理增强

> 需求编号：#7, #8
> 优先级：中
> 影响范围：前端 SettingsPage.vue、useCategoriesStore.js，后端 Tag model、tag_service

---

## 任务列表

### 2.1 后端 - 标签软删除

- [ ] Tag model 增加 `deleted_at` 字段
- [ ] 执行数据库迁移：`ALTER TABLE tags ADD COLUMN deleted_at TEXT DEFAULT NULL;`
- [ ] 修改 `delete_tag` 为软删除（设置 `deleted_at`）
- [ ] 修改 `get_tags` 过滤已删除标签（`deleted_at IS NULL`）

### 2.2 后端 - 账单记录保留已删除标签

- [ ] `record_service.py` 的 `_enrich_record` 获取标签时不检查 `deleted_at`
- [ ] 确保已删除标签的账单仍能显示标签名称

### 2.3 前端 - 标签新增时分类必填

- [ ] 标签新增对话框增加分类选择器（`v-select`）
- [ ] 分类设为必填项，添加验证规则
- [ ] 未选择分类时，保存按钮 disabled 或显示提示
- [ ] 提交数据包含 `category_id`

### 2.4 前端 - 标签删除适配

- [ ] `removeTag` 调用 DELETE API（后端软删除）
- [ ] 删除后重新 `fetchTags()` 刷新列表

---

## 验收标准

- [ ] 新增标签不选分类时提示"请选择分类"，无法保存
- [ ] 新增标签选择分类后创建成功
- [ ] 删除标签后标签从列表消失
- [ ] 删除标签后查看关联账单，账单详情仍显示标签名称
- [ ] 新建账单时标签选择列表不包含已删除标签
