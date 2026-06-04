# 模块 1：快速记账页 - 标签保存时机优化

> 需求编号：#1 | 优先级：高 | 文件：`frontend/src/pages/RecordFormPage.vue`

## 目标

按回车仅在界面上确认标签（设置本地状态），不调用 API。标签的实际创建推迟到 `submit()` 中与账单一起保存。

## 任务清单

- [ ] **1.1** 修改 `onCreateTagFromSearch` 函数：移除 `createTagData` 调用，改为仅设置 `selectedTagId=null` 和 `selectedTagName=tagSearchQuery`
- [ ] **1.2** 确认 `submit()` 函数中已有处理新标签的逻辑（`selectedTagName` 有值但 `selectedTagId` 为空时创建标签），无需修改
- [ ] **1.3** 验证：输入新标签按回车后，数据库 tags 表无新增记录
- [ ] **1.4** 验证：输入新标签按回车后填写其他信息，点击保存，账单和标签一起保存到数据库
- [ ] **1.5** 验证：输入新标签按回车后不保存直接离开，数据库中无残留标签
- [ ] **1.6** 验证：选择已有标签按回车，正常选中（selectedTagId 赋值为已有 ID）
- [ ] **1.7** 验证：保存后查看账单详情，标签显示正确
