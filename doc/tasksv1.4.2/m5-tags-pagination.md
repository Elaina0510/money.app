# M5 - 标签解除 20 条上限 + 分页展开

> 对应需求五（设计 §五，决策 D1/D5）。`GET /api/tags` 去 limit(20) 保持裸数组契约；新增 `GET /api/tags/paged` 供标签页「展开更多」；设置页摘要进入即拉真实总数。
> 涉及文件：`backend/app/services/tag_service.py`、`backend/app/routers/tags.py`、`frontend/src/api/tags.js`、`SettingsTagsPage.vue`、`SettingsPage.vue`、`test_tags.py`、`SettingsSubPages.test.js`、`RecordFormPage.test.js`。
> 依赖：无（第 1 梯队可并行）。与 M8 同改 SettingsPage.vue 但区域隔离（onMounted vs 模板入口），可并行。

---

## 1. 后端：`GET /api/tags` 去上限（契约不变）

- [x] 1.1 `tag_service.get_tags`（:16-29）删除 `query.limit(20)` 一行，其余不动，响应仍裸数组
- [x] 1.2 确认既有调用方零改动即解除截断：快速记账「选择标签」下拉、记一笔页 `searchTags`（后端 `contains` 全库匹配）

## 2. 后端：新分页端点（决策 D1）

### 2.1 Service `get_tags_paged`

- [x] 2.1.1 签名 `(db, current_user=None, search=None, page=1, page_size=20) -> tuple[list[Tag], int]`，返回 (当页列表, 匹配总数)，完整类型注解（易错点 11）
- [x] 2.1.2 条件：未删 + 用户隔离；`search` 作用于 items 与 total 两处
- [x] 2.1.3 `total` 用 `select(func.count(Tag.id))`；items 按 id 排序 `offset((page-1)*page_size).limit(page_size)`

### 2.2 Router `GET /paged`（`routers/tags.py`）

- [x] 2.2.1 参数：`page: int = Query(1, ge=1)`、`page_size: int = Query(20, ge=1, le=100)`、`q: str | None`
- [x] 2.2.2 响应 `success_response(data={items, total, page, page_size})`（items 为 TagResponse dump）
- [x] 2.2.3 **路由顺序强约束**：声明在 `GET /{tag_id}` 之前，否则 "paged" 被 int 路径参数抢匹配 422（易错点 1）

## 3. 前端：API / Store

- [x] 3.1 `api/tags.js` 新增 `getTagsPaged(params)`；`getTags/searchTags` 不动
- [x] 3.2 `useCategoriesStore.fetchTags` 实现不动（内部已 try/catch 不外抛，设置页 fire-and-forget 语义安全）

## 4. 前端：设置页摘要修复（`SettingsPage.vue`）

- [x] 4.1 `onMounted`（:333-335）新增 `categoriesStore.fetchTags()`（与现有 `Promise.all([loadCategories(), loadQuickTemplates()])` 并存）
- [x] 4.2 **红线**：不得写本地 `loadTags()` 包装——用例 6b 断言 SettingsPage 源码零命中 `loadTags` 标识符，直接调 store 方法（`categoriesStore` :273 已实例化）
- [x] 4.3 摘要模板 `{{ tags.length }} 个`（:68）不变——store.tags 现为全量，即修复「显示 0」与「最多 20」

## 5. 前端：标签管理二级页分页（`SettingsTagsPage.vue`）

- [x] 5.1 数据模型改本地分页：`displayedTags`/`total`/`page`/`PAGE_SIZE=20`/`loadingMore`/`hasMore` computed
- [x] 5.2 `resetPaging()`：拉第 1 页覆盖 displayedTags 并回写 total、page=1
- [x] 5.3 `loadMore()`：拉 page+1 追加、更新 total、page 自增；finally 复位 loadingMore
- [x] 5.4 模板：chip 云渲染源改 `displayedTags`（样式与现状完全一致）；底部 `v-if="total > PAGE_SIZE"` 区——「展开更多」按钮（`v-if="hasMore"`、`:loading="loadingMore"`）+ 文案「已显示 x / 共 N 个」
- [x] 5.5 `onMounted`：`Promise.all([fetchTags(), fetchCategories(), resetPaging()])`
- [x] 5.6 新增/删除标签后：保留 `store.addTag/removeTag` 流程 → 追加 `fetchTags() + resetPaging()`
- [x] 5.7 边界：≤20 个标签时按钮与文案均不渲染（与改版前完全一致）；page 越界 items 空 → hasMore=false 隐藏按钮；「展开更多」失败 loadingMore 复位、已显示列表不变（错误 toast 由拦截器统一弹）

## 6. 测试

### 6.1 后端 pytest（`test_tags.py` 新增用例组）

- [x] 6.1.1 造 25 个标签：`GET /api/tags` 返回 25（去上限回归）；带 `q` 匹配全库而非前 20
- [x] 6.1.2 `GET /api/tags/paged` 默认 → items 20 + total 25 + page/page_size 回显；page=2 → 余 5 条、顺序与全量按 id 一致
- [x] 6.1.3 `q` + paged → 匹配总数与分页正确；page 越界 → items 空、total 不减
- [x] 6.1.4 `/paged` 不被 `/{tag_id}` 抢占（200 非 422）；软删不计入 total；数据隔离；未认证 401

### 6.2 vitest

- [x] 6.2.1 标签页：mock `getTagsPaged` 首页 20/总 30 → 渲染 20 chip + 按钮 + 「已显示 20 / 共 30 个」；点击 → 追加 10 chip、按钮消失、文案更新
- [x] 6.2.2 mock 总数 ≤20 → 按钮与文案均不渲染
- [x] 6.2.3 新增标签成功 → `resetPaging` 重查第 1 页
- [x] 6.2.4 设置页用例 1/1b 改写（口径反转，易错点 10）：mount 后 `getTags` 恰一次；修改 store.tags 后摘要即时响应不再新增请求
- [x] 6.2.5 回归：快速记账弹窗 options 长度 = mock `getTags` 全量（>20 场景）；`RecordFormPage.test.js` 中 `searchTags` mock 返回 >20 时 `tagSearchResults` 全量渲染
- [x] 6.2.6 `SettingsSubPages.test.js` 标签相关 mock 补 `getTagsPaged` 导出（vi.mock 工厂同步）

## 7. 验收与质量门槛

- [x] 7.1 后端 pytest + mypy 基线零新增 + ruff 通过
- [x] 7.2 `npm test`、`npm run lint` 通过
- [ ] 7.3 手工验收（造 30+ 标签）：设置页摘要显示真实数量（未进过任何标签页也正确）；标签页首屏 20 个 +「展开更多」增量加载并更新计数；快速记账弹窗选到第 21+ 个标签；记一笔页按名称搜出任意标签
