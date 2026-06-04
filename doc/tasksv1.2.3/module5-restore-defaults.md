# 模块 5：设置页 - 恢复默认分类功能

> 需求编号：#7 | 优先级：高 | 涉及文件：前端 SettingsPage.vue、useCategoriesStore.js、api/categories.js；后端 category_service.py、categories.py

## 目标

在设置页分类管理栏添加"恢复默认"按钮，点击后二次确认，确认后删除所有自定义分类、重置预设分类排序。

## 任务清单

### 后端

- [ ] **5.1** 在 `category_service.py` 新增 `restore_default_categories(db, current_user)` 函数：删除 `is_preset=0` 的用户自定义分类，关联记录 `category_id` 设为 NULL，关联预算删除，重置预设分类 `sort_order`
- [ ] **5.2** 在 `categories.py` 新增 `POST /api/categories/restore-defaults` 端点，调用 service 函数并返回结果

### 前端 API

- [ ] **5.3** 在 `api/categories.js` 新增 `restoreDefaultCategories()` 函数，调用 `POST /categories/restore-defaults`

### 前端 Store

- [ ] **5.4** 在 `useCategoriesStore.js` 新增 `restoreDefaults` action：调用 API 后重新 `fetchCategories()`

### 前端 UI

- [ ] **5.5** 在 `SettingsPage.vue` 分类管理卡片标题栏添加"恢复默认"按钮（警告色 tonal 样式）
- [ ] **5.6** 添加二次确认对话框：显示操作说明（删除自定义分类、记录保留但失去关联、重置预设排序）和"此操作不可撤销"警告
- [ ] **5.7** 实现 `handleRestoreDefaults` 函数：调用 store action，显示 toast，重新加载分类列表
- [ ] **5.8** 验证：点击"恢复默认"弹出确认对话框
- [ ] **5.9** 验证：点击"取消"关闭对话框，无变化
- [ ] **5.10** 验证：点击"确认恢复"后，自定义分类被删除，预设分类重置
- [ ] **5.11** 验证：恢复后账单记录仍在但无分类关联
- [ ] **5.12** 验证：恢复后自定义分类下的预算被删除
- [ ] **5.13** 验证：恢复后预设分类排序重置为默认
- [ ] **5.14** 验证：无自定义分类时恢复，预设排序重置，无报错
