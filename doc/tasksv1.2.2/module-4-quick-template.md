# 模块 4：快速记账优化

> 需求编号：#9, #10
> 优先级：中
> 影响范围：后端 record_service.py，前端 RecordFormPage.vue、SettingsPage.vue

---

## 任务列表

### 4.1 后端 - 快速记账模板逻辑优化

- [ ] 新建 `quick_templates` 表（model）
- [ ] 执行数据库迁移创建表
- [ ] 重写 `get_quick_templates` 函数：按 `(tag_id, type, amount)` 分组
- [ ] 筛选 `HAVING count >= 2` 的组合
- [ ] 排除已删除标签（`tag.deleted_at IS NULL`）
- [ ] 按最近使用时间降序排列

### 4.2 后端 - 快速记账模板 API

- [ ] `GET /api/quick-templates` — 获取模板（合并自动 + 手动）
- [ ] `POST /api/quick-templates` — 手动添加模板
- [ ] `DELETE /api/quick-templates/{id}` — 删除模板

### 4.3 前端 - 快速模板适配新数据结构

- [ ] 修改 `fillTemplate` 函数适配新字段
- [ ] 模板 chip 显示调整：`{{ tpl.tag_name }} · ¥{{ tpl.amount }}`

### 4.4 前端 - 设置页快速记账管理

- [ ] 新增快速记账管理卡片 section
- [ ] 显示快速记账模板列表
- [ ] 实现删除快速记账项功能
- [ ] 实现手动添加快速记账项对话框
- [ ] 添加时需选择标签和输入金额

---

## 验收标准

- [ ] 首次记录"午餐 25 元"不出现在快速记账
- [ ] 第 2 次记录"午餐 25 元"后出现在快速记账
- [ ] 设置页可查看快速记账列表
- [ ] 设置页可删除快速记账项
- [ ] 设置页可手动添加快速记账项
