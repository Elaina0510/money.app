# M3 - 分类列表拖拽排序（含批量重排接口）

> 对应需求三（设计 §三）。上移/下移按钮改三横杠把手 + vuedraggable 自由拖动；新增 `PUT /api/categories/reorder` 批量原子重排 + 归一化（「其他」强制置尾）。
> 涉及文件：`frontend/package.json`、`SettingsCategoriesPage.vue`、`useCategoriesStore.js`、`api/categories.js`、`backend/app/services/category_service.py`、`backend/app/routers/categories.py`、新增 `backend/tests/test_categories_reorder.py`、`SettingsSubPages.test.js`。
> 依赖：M2（复用其 `_is_other_category`/`_visible_categories` 与创建排序逻辑）；前端列表区在 M1/M2 合入后改。

---

## 1. 依赖安装与可行性验证（决策 D2，先于编码）

- [x] 1.1 `npm i vuedraggable@next`（next 标签 = 4.1.0，Vue3 兼容线；**latest 2.24.3 是 Vue2 版，装错即全功能失效**，易错点 13）
- [x] 1.2 `npm ls sortablejs vuedraggable` 核版本（sortablejs 为传递依赖；如需顶层锁定先 `npm info vuedraggable@next dependencies` 查实范围，禁止盲写）
- [x] 1.3 最小 demo 验证 Vue 3.5 + Vite 8 下组件可用 + `npm run build` 通过；失败则回退 D2 备选「原生 pointer 事件」并重报裁定
- [x] 1.4 实施后以 `npm run build` 前后对比记录包体增量（D2 估算 gzip ≈16KB，复核）

## 2. 后端：批量重排接口

### 2.1 接口定义（`routers/categories.py`）

- [x] 2.1.1 `PUT /api/categories/reorder`，body `{ "type": "expense"|"income", "ids": [int,...] }`（该分组全量有序），响应 `success_response(data=重排后的分类列表, message="排序已保存")`
- [x] 2.1.2 **路由顺序强约束**：声明在 `@router.put("/{category_id}")`（现 :52）**之前**，否则被路径参数抢匹配 422（易错点 1）
- [x] 2.1.3 `type` 用 Pydantic Literal/正则校验 → 非法 422

### 2.2 Service `reorder_categories`（`category_service.py` 新增）

- [x] 2.2.1 取该用户+type 可见分类集合（复用 M2 的 `_visible_categories`）
- [x] 2.2.2 校验（失败 ValueError → 400）：ids 无重复；`set(ids) == 可见集合 id 全集`（全量提交防漏位）；可见集合含「其他」（缺失 → 400）
- [x] 2.2.3 归一化赋位：第 i 项（1 起）`sort_order = i`；**「其他」无论落点强制赋 n（末位）**
- [x] 2.2.4 预设行改序走 CoW：有副本 → 更新副本；无副本 → 按预设字段建副本（`is_preset=0`、新 sort）后更新；用户行直接更新；**全局预设行 sort_order 永不写脏**
- [x] 2.2.5 单事务提交；返回按新 sort_order 排序的可见列表
- [x] 2.2.6 失败响应口径：ids 不一致/重复/含他人 id → 400 PARAM_ERROR「排序列表与当前分类不一致」；未认证 → 401

## 3. 前端：Store / API 层

- [x] 3.1 `api/categories.js` 新增 `export function reorderCategories(data) { return request.put('/categories/reorder', data) }`
- [x] 3.2 `useCategoriesStore.js` 新增 `reorderCategories(type, ids)`：成功后 `fetchCategories()`；失败 `app.showToast('排序保存失败','error')` 并 rethrow（页面负责回滚）；方法内不弹「更新成功」类附加 toast

## 4. 前端：模板改造（现 :27-131 两个列表块）

- [x] 4.1 支出/收入各一个独立 Draggable 实例（天然不可跨组拖）：`:handle="'.drag-handle'"`、`:disabled="isOtherLocked(list)"`、`item-key="id"`、`:delay="150"`、`:delay-on-touch-only="true"`、`:touch-start-threshold="5"`、`ghost-class="drag-ghost"`、`drag-class="drag-float"`、`@start`/`@end`
  - 注：外层 `<v-list class="bg-transparent pa-0">` 保留（M4 卡壳合入后其位于 `.page-card` 内，不再透视到页面背景，属合法写法；M4 §2.5/§4.2 已按此口径收敛断言）
- [x] 4.2 行首渲染三横杠把手 `mdi-drag-vertical`（`size="20" color="grey"`，头像左侧）；「其他」行不渲染把手，替换为同宽占位 span（`.drag-handle-placeholder`）
- [x] 4.3 删除四处上移/下移 `v-btn`（:50-67、:103-120）与 `moveCategory`（:252-265）——整体移除，不留兼容路径（决策 D8）
- [x] 4.4 单一渲染源约束：新增 `expenseDragList`/`incomeDragList` ref（watch store computed 派生，immediate）；模板内所有列表渲染与空态判断（含页面级 :23）一律改读 dragList，computed 不再直接出现在 v-for

## 5. 前端：脚本逻辑（设计 §3.3.3）

- [x] 5.1 `isOther(cat)`：按 name+type 双判，与后端助手对齐
- [x] 5.2 `isOtherLocked(list)`：「其他」非末位（异常数据）→ 禁用本组拖动
- [x] 5.3 `onDragStart(type)`：`preDragSnapshot[type]` 记录拖前快照
- [x] 5.4 `onDragEnd(type)`：本地镜像后端「末尾占位」归一化（「其他」被拖中间 → 移回末位后提交，避免保存后跳变），再 `submitReorder`
- [x] 5.5 `submitReorder(type, list)`：成功 → 唯一一次 toast「排序已保存」；失败 → 恢复 `preDragSnapshot` 快照 + `fetchCategories()` 静默对齐后端真值
- [x] 5.6 一次拖动只发一次 `PUT /categories/reorder` 请求（原子保存）

## 6. 前端：拖拽态样式（§3.3.5）

- [x] 6.1 `.drag-handle { cursor: grab; touch-action: none; }`——**`touch-action:none` 只加把手，加整行会杀死列表滚动**（易错点 7）
- [x] 6.2 `.drag-handle-placeholder { width: 20px; flex-shrink: 0 }`
- [x] 6.3 `.drag-ghost`（插入位置指示：opacity .4 + primary 浅底）、`.drag-float`（拖起浮起：scale 1.02 + level-3 阴影）

## 7. 测试

### 7.1 后端 pytest（新增 `backend/tests/test_categories_reorder.py`）

- [x] 7.1.1 乱序全量 ids → 返回按提交序、sort_order 归一化 1..n 连续
- [x] 7.1.2 「其他」放 ids 中间提交 → 响应与库中均强制置尾（n）
- [x] 7.1.3 含预设行 → 生成/更新用户副本，全局预设行 sort_order 不变（另用新验证用户 GET 回归）
- [x] 7.1.4 ids 缺项/重复/含他人 id → 400；type 非法 → 422；未认证 → 401
- [x] 7.1.5 收入组重排不影响支出组顺序

### 7.2 vitest（`SettingsSubPages.test.js` 用例 2b 改写为拖拽+批量重排口径）

- [x] 7.2.1 行内无 `mdi-chevron-up/down`；非「其他」行有 `.drag-handle`，「其他」行有 `.drag-handle-placeholder`
- [x] 7.2.2 改 `expenseDragList` 后调 `onDragEnd('expense')` → `reorderCategories` PUT 恰一次、payload `{type:'expense', ids:[...]}`、成功 toast「排序已保存」一次（jsdom 不真实驱动 sortable，vm 直改列表手动调 onDragEnd）
- [x] 7.2.3 「其他」被拖中间 → 提交 ids 中「其他」仍末位
- [x] 7.2.4 mock reject → 本地列表恢复快照 + 错误 toast
- [x] 7.2.5 `isOtherLocked` 单测：非末位「其他」→ true

## 8. 验收与质量门槛

- [x] 8.1 后端 pytest 相关 + 全量回归、mypy 基线零新增、ruff 通过
- [x] 8.2 `npm test`、`npm run lint`、`npm run build` 通过（build 尺寸记录于 progress 备注）
- [ ] 8.3 手工验收：桌面鼠标 + 移动触摸均可拖动任意距离；松手刷新/重进顺序保持；「其他」拖不动、别人拖不到它后面；一次拖动仅一次保存请求、无成串 toast、无顺序闪回；支出/收入两组互不可拖
- [ ] 8.4 与 M4 合入时做一次卡壳 × 拖拽样式视觉回归；`bg-transparent pa-0` 断言口径以 M4 §2.5/§4.2（页面无透视，卡内 v-list 合法保留）为准，勿用整串字面量断言
