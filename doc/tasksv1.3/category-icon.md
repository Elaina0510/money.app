# 模块 4：分类图标替代收支图标

> **优先级：** 低 | **复杂度：** 低 | **涉及文件：** `RecordListPage.vue`

## 子任务

- [ ] 4.1 将 `v-slot:prepend` 中的 `mdi-arrow-down` / `mdi-arrow-up` 替换为 `record.category_icon || 'mdi-circle'`
- [ ] 4.2 将 prepend 图标 size 从 18 调整为 20
- [ ] 4.3 背景色保持不变（`#FFE8E8` / `#E8FFF3`），仍通过颜色区分收支类型
- [ ] 4.4 移除 `v-list-item-title` 中重复的小号分类图标（`v-avatar size="24"` 那段）
- [ ] 4.5 保留文字部分：`{{ record.tag?.name || record.category_name || '未分类' }}`

## 验收测试

- [ ] 账单列表中各条目显示对应分类的图标
- [ ] 无分类图标时显示 `mdi-circle` 兜底
- [ ] 收入/支出仍通过背景色和金额正负号区分
