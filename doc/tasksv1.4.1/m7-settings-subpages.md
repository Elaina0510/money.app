# M7 - 设置页三个管理区块改二级页面

> 对应需求六：分类管理/标签管理/快速记账管理改为摘要卡片 + 独立二级页面，操作全量下沉。
> 迁移原则（易错点 8）：**搬移优先于重写**——逻辑自 SettingsPage 原样迁移（含 ConfirmDialog/restore 弹窗），行为与 v1.4 完全一致。
> 涉及文件：`frontend/src/router/index.js`、`frontend/src/pages/SettingsPage.vue`、新增 `SettingsCategoriesPage.vue`/`SettingsTagsPage.vue`/`SettingsQuickTemplatesPage.vue`
> 依赖：排在 M6 之后（同文件 SettingsPage，避免删除行号漂移）。

---

## 1. 路由（router/index.js）

- [x] 新增三条懒加载路由（置于 `/settings` 之后）：
  - [x] `/settings/categories` → `SettingsCategories` → `@/pages/SettingsCategoriesPage.vue`，`meta: { title: '分类管理' }`
  - [x] `/settings/tags` → `SettingsTags` → `@/pages/SettingsTagsPage.vue`，`meta: { title: '标签管理' }`
  - [x] `/settings/quick-templates` → `SettingsQuickTemplates` → `@/pages/SettingsQuickTemplatesPage.vue`，`meta: { title: '快速记账' }`
- [x] 确认守卫自动要求 token（现有 beforeEach 非 public 即校验，无需改动）
- [x] 确认 `AppLayout.currentRoute` 的 `path.startsWith('/settings')` 分支（:276-283）使二级页底栏「设置」高亮（现有逻辑，不改动）
- [x] 二级页底栏/FAB 显示行为与其他内页一致，本次不改动（需求 4 条）

## 2. 新建 SettingsCategoriesPage.vue（分类管理二级页）

- [x] 公共头部：返回按钮（`$router.back()`，`mdi-arrow-left`，与 HistoryPage.vue:3-15 形式一致）
- [x] 从 SettingsPage **整体搬移**模板：支出/收入分类列表（:41-171 列表区，含上移/下移/编辑/删除）、Category Dialog（:173-217）、Delete Category Confirm（:219-226）、Restore Defaults Dialog（:228-248）
- [x] 头部右侧动作区保留「恢复默认」「新增」两按钮（`d-flex ga-2`，现 :50-59）——「恢复默认」自设置页下沉至此
- [x] 搬移脚本：`expenseCategories/incomeCategories` computed、`showCategoryDialog/categoryForm/typeOptions/editingCategory/savingCategory`、`moveCategory/editCategory/saveCategory/resetCategoryForm/confirmDeleteCategory/handleDeleteCategory/handleRestoreDefaults/restoring/showRestoreConfirm`、删除确认三态 refs
- [x] 数据来源：`useCategoriesStore`，`onMounted` 调 `categoriesStore.fetchCategories()` 刷新共享状态

## 3. 新建 SettingsTagsPage.vue（标签管理二级页）

- [x] 公共头部：返回按钮 + 副标题
- [x] 搬移模板：标签 chip 云（:265-277，chip 上 × 删除；竖屏 `flex-wrap` 自然换行）、Tag Dialog（:280-308，所属分类下拉取 categories store）、Delete Tag Confirm（:310-317）
- [x] 搬移脚本：`tagForm/savingTag/showTagDialog/confirmDeleteTag`、`saveTag/handleDeleteTag`
- [x] 数据全部走共享 `useCategoriesStore`：`tags` 经 `storeToRefs` 直读、新增 `categoriesStore.addTag(...)`、删除 `categoriesStore.removeTag(id)`、`onMounted` 调 `fetchTags()`
- [x] `categories`（storeToRefs）供弹窗下拉

## 4. 新建 SettingsQuickTemplatesPage.vue（快速记账二级页）

- [x] 公共头部：返回按钮 + 副标题
- [x] 搬移模板：模板列表（:468-501，含来源展示 `category_name · 使用 N 次`、删除按钮）、Quick Template Add Dialog（:504-536）
- [x] 搬移脚本：`quickTemplates/showQuickTemplateDialog/quickTemplateForm/savingQuickTemplate/loadQuickTemplates/removeQuickTemplate/saveQuickTemplate`
- [x] CRUD 走 `@/api/records` 的 `getQuickTemplates/addQuickTemplate/deleteQuickTemplate`
- [x] 弹窗"选择标签"下拉数据来自 `useCategoriesStore`（`storeToRefs` 的 `tags` + `fetchTags()`）

## 5. SettingsPage.vue：三区块改摘要卡

### 5.1 摘要卡片（三块统一结构）

- [x] 沿用外壳 `v-card class="mb-3 settings-card" rounded="xl"` + `v-list-item :to="..."`（prepend 图标 + 标题 + 数量 subtitle + append `mdi-chevron-right`）
- [x] 保持顺序：分类管理 → 标签管理 → 快速记账（外观设置下方）
- [x] 分类管理：图标 `mdi-shape` primary，摘要 `支出 {n} / 收入 {m}`
- [x] 标签管理：图标 `mdi-tag-multiple` info，摘要 `{n} 个`
- [x] 快速记账：图标 `mdi-lightning-bolt` teal，摘要 `{n} 个模板`
- [x] 卡片上**不展示任何详细条目、不保留新增按钮**（需求 2 条）

### 5.2 数量来源

- [x] `categories`/`tags` 经 `storeToRefs(useCategoriesStore())` 直读（响应式，二级页操作返回即时更新）
- [x] `loadQuickTemplates()` 降级保留：`getQuickTemplates` 仅取条目数
- [x] 保留 `loadCategories`（store 触发）与 `expenseCategories/incomeCategories` computed（摘要用）

### 5.3 移除清单（设计 §7.4）

- [x] 删模板：:41-317（分类卡+Category Dialog+Delete Confirm+Restore Dialog+标签卡+Tag Dialog+Delete Confirm）、:453-536（快速记账卡+Add Dialog）
- [x] 删脚本：三块 CRUD 函数与弹窗状态（:841-1071 中 `moveCategory/editCategory/saveCategory/resetCategoryForm/confirmDeleteCategory/handleDeleteCategory/handleRestoreDefaults/saveTag/confirmDeleteTag/handleDeleteTag/removeQuickTemplate/saveQuickTemplate` 及相关 refs）
- [x] 删本地 `tags` ref 与 `loadTags()`（摘要改走 storeToRefs 直读）
- [x] 删 import：`addQuickTemplate/deleteQuickTemplate`（`getQuickTemplates` 保留供数量）、`ConfirmDialog`（grep 核实 :220/:311 两处已随块移走）
- [x] 保留：`CsvMappingDialog`、`getRecords` import（CSV/SQL 预览如仍使用）、外观设置/导入导出/数据回溯/账号区块
- [x] 逐项 grep 校验无残留：`showCategoryDialog|tagForm|quickTemplateForm|handleRestoreDefaults` 等

## 6. 测试（vitest）

- [x] SettingsPage：渲染三个摘要卡；卡片文本含数量、**不含**任何列表条目和新增按钮；`v-list-item` 的 `to` 指向正确路由
- [x] 三个新页面：返回按钮点击触发 `router.back()`；分类页渲染支出/收入两组；标签页空态文案；模板页删除按钮调用 `deleteQuickTemplate`
- [x] 路由表快照：三条新路由存在、懒加载、`meta.title` 正确

## 7. 手工验收（竖屏 + 宽屏各一遍）

- [ ] 设置页三卡片仅显示摘要与箭头，数量正确
- [ ] 进入分类二级页：列表、新增、编辑、删除、上移/下移、恢复默认全部可用且与 v1.4 行为一致
- [ ] 进入标签二级页：chip 云、新增、删除可用；竖屏换行正常
- [ ] 进入快速记账二级页：模板列表（含来源展示）、新增、删除可用
- [ ] 各二级页操作后返回设置页：摘要数量即时更新
- [ ] 二级页底栏「设置」保持高亮；底栏/FAB 行为同数据回溯页
- [ ] 刷新应用直达 `/settings/tags` 等二级路由：登录守卫生效、页面正常

## 8. 质量门槛

- [x] `cd frontend && npm test && npm run lint && npm run build` 通过
