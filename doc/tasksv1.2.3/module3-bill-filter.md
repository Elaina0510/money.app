# 模块 3：账单页 - 筛选功能修复与优化

> 需求编号：#3, #4, #6 | 优先级：高 | 文件：`frontend/src/pages/RecordListPage.vue`

## 目标

修复三个关联问题：类型筛选不生效、切换页面后筛选状态丢失、分类标签未按类型联动。

## 任务清单

### #4 筛选状态持久化

- [ ] **3.1** 将页面级 `filters` reactive 对象替换为 Pinia store `useRecordsStore` 中的 `filters`（结构兼容：`start_date, end_date, type, category_id`）
- [ ] **3.2** 验证：筛选后切换到统计页再切回账单页，筛选条件保持，筛选框正确显示

### #6 分类按类型联动

- [ ] **3.3** 修改 `categoryOptions` computed：当 `filters.type` 有值时，按 `c.type === filters.type` 过滤分类列表
- [ ] **3.4** 新增 watch 监听 `filters.type` 变化时，自动清空 `filters.category_id`
- [ ] **3.5** 验证：选择"支出"后，分类下拉只显示支出分类（餐饮、交通等）
- [ ] **3.6** 验证：选择"收入"后，分类下拉只显示收入分类（工资、兼职等）
- [ ] **3.7** 验证：切换类型时，已选分类自动清空

### #3 类型筛选生效

- [ ] **3.8** 确认 `v-select` 的 `v-model` 正确绑定 `filters.type`，确认 `search()` 中 `type_filter` 参数传递正确
- [ ] **3.9** 如前端逻辑无误但筛选仍不生效，检查后端 `record_service.get_records()` 的 `type_filter` 处理
- [ ] **3.10** 验证：选择"收入"，列表只显示收入类型账单
- [ ] **3.11** 验证：选择"支出"，列表只显示支出类型账单
- [ ] **3.12** 验证：选择"全部"，列表显示所有账单
- [ ] **3.13** 验证：筛选结果实时更新，无需手动刷新
