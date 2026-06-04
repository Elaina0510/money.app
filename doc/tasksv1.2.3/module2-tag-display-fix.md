# 模块 2：快速记账页 - 标签显示异常修复

> 需求编号：#2 | 优先级：高 | 文件：`frontend/src/pages/RecordFormPage.vue`

## 目标

修复输入标签后点击空白处，标签显示为数字 ID 而非名称的问题。确保 `tagSearchResults` 始终包含当前已选中的标签项。

## 任务清单

- [ ] **2.1** 修改 `onTagSearch` 函数：当搜索清空时（`query` 为空），保留当前已选中的标签在 `tagSearchResults` 中（从现有结果中找到 `selectedTagId` 对应项，保留为单元素数组）
- [ ] **2.2** 修改 `onCreateTagFromSearch` 函数：新标签确认后，将临时标签对象 `{ id: -1, name, category_id }` 加入 `tagSearchResults`，并设置 `selectedTagId = -1`
- [ ] **2.3** 修改 `submit()` 函数：将标签 ID 判断条件从 `!tagId` 改为 `!tagId || tagId === -1`，以处理临时 ID
- [ ] **2.4** 验证：输入新标签名按回车，点击空白处，输入框显示标签名称（非数字）
- [ ] **2.5** 验证：选择已有标签，点击空白处，输入框显示标签名称
- [ ] **2.6** 验证：输入新标签名按回车，保存账单，账单正确关联新创建的标签
- [ ] **2.7** 验证：账单页回看标签，显示标签名称与记账页一致
