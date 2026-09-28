# M1 - 标签批量治理（REQ-001 一键清空 / REQ-002 多选批量删除）

> 对应设计 §二（决策 D1 接口命名、D7 头部位次）。目标：`POST /api/tags/batch-delete` + `POST /api/tags/clear-all` 两批量接口（单事务原子、软删、**不写回溯**），标签管理页「清空」按钮 + 「多选」两态流。
> 涉及文件：改 `backend/app/schemas/tag.py`、`backend/app/services/tag_service.py`、`backend/app/routers/tags.py`、`backend/tests/test_tags.py`；改 `frontend/src/api/tags.js`、`frontend/src/pages/SettingsTagsPage.vue`、`frontend/src/stores/useCategoriesStore.js`、`frontend/src/pages/__tests__/SettingsSubPages.test.js`（**只增自己的 describe 块，M2 亦追加该文件——不触碰对方**）。
> 依赖：**M0 必须先合入**（验收断言「软删后 `GET /api/records` 该行 `tag=null`」用 M0 口径）。
> 行号为设计快照参考位，开工以 grep 定位为准。

---

## 1. 后端 schema（`schemas/tag.py`，本模块独占）

- [x] 1.1 新增 `TagBatchDelete(BaseModel)`：`ids: list[int] = Field(..., min_length=1)`；数量**无上限**（需求裁定 M 为数十至数百级）；docstring 沿既有 Schema 英文风格

## 2. 后端服务（`tag_service.py`，两函数均单事务原子提交）

- [x] 2.1 `batch_delete_tags(db, ids, current_user) -> int` 控制流三步（设计 §2.1）：
  - ① 一次查询 `SELECT id FROM tags WHERE user_id == current_user.id AND deleted_at IS NULL AND id IN (set(ids))`（**无 N+1**）
  - ② 命中数 ≠ `len(set(ids))` → 抛 `ValueError("部分标签不存在或已被删除，请刷新后重试")`，**整单失败、不落任何删除**
  - ③ 全命中 → 逐行置 `deleted_at = now("%Y-%m-%d %H:%M:%S")`（沿既有单删的时间格式函数），一次 `await db.commit()`，返回删除数
- [x] 2.2 归属口径：仅 `user_id == current_user.id` 可被批量接口触碰——**刻意不开 `user_id IS NULL` 全局行口子**（严于既有 `delete_tag`），跨用户/全局 id 一律计入 ②的「不存在」
- [x] 2.3 `clear_all_tags(db, current_user) -> int`：SELECT 当前用户全部未软删标签 → 置 `deleted_at` → 一次 commit → 返回条数；**0 条也成功返回 0（不抛错）**

## 3. 后端路由（`routers/tags.py`）

- [x] 3.1 两 POST 端点声明位置：`/paged` 之后、`/{tag_id}` 之前（红线序）
- [x] 3.2 `POST /api/tags/batch-delete`：成功 `{"code":0,"message":"已删除 N 个标签","data":{"deleted_count":N}}`；`ValueError` → `error_response(Code.PARAM_ERROR, str(e))`；ids 缺失/空数组/非整数由 FastAPI 默认 422 兜底（**不做特判**，前端仅在已选 ≥1 时发起）
- [x] 3.3 `POST /api/tags/clear-all`：无 body；成功 message `已清空 N 个标签`；`deleted_count=0` 时 message 为 `"标签已全部清空"`（幂等成功）；未登录沿用全局 401 口径
- [x] 3.4 不写回溯（既裁定）、不发事件、无条数上限

## 4. 前端 API 与 store

- [x] 4.1 `api/tags.js` 追加 `batchDeleteTags(ids)` → `request.post('/tags/batch-delete', { ids })`；`clearAllTags()` → `request.post('/tags/clear-all')`
- [x] 4.2 `useCategoriesStore.js` 追加（与 `removeTag` 同风格：成功就地更新 + toast，失败 toast 后 rethrow）：
  - `batchRemoveTags(ids)`：成功后 `tags.value = tags.value.filter(t => !ids.includes(t.id))`，toast「已删除 N 个标签」
  - `clearTags()`：成功后 `tags.value = []`，toast「标签已清空」

## 5. 页面交互（`SettingsTagsPage.vue`，D7 位次）

- [x] 5.1 头部右侧按钮序：`多选`（tonal 小按钮，`mdi-checkbox-marked-outline`）→ `新增`（现状不动）→ `清空`（`variant="text"` 小按钮，**不传 color 继承 foreground**——「弱色」即此口径，禁点 error/warning 彩色；`total === 0` 时 `disabled`）（2026-09-28 ui-design 审查补）
- [x] 5.2 **清空流**：点「清空」→ `ConfirmDialog`，message = `将删除全部 ${total} 个标签，账单上的标签标记同步移除，此操作不可撤销` → 确认 → `clearTags()` + `resetPaging()` 回空态；取消零请求零副作用
- [x] 5.3 **多选流·进入**：`multiSelect=true`；chip 前显勾选图标（未选 `mdi-checkbox-blank-circle` / 已选 `mdi-checkbox-marked`，**同系 filled 配对**，ui-design 0.8 图标系别一致，2026-09-28 审查补），点 chip 主体切换选中；**此态下不弹删除确认、单 chip ✕ 隐藏、「清空」按钮不渲染**（避免双入口）
- [x] 5.4 **多选流·操作条**：`selectedIds.length >= 1` 时浮出 `<Transition name="batch-bar">` 顶栏操作条（复用账单页动效类与版式，§0.4-13 范式）：`已选 M 个` chip + `删除` + `取消`；已选 0 不渲染
- [x] 5.5 **多选流·删除**：点「删除」→ `ConfirmDialog`（`确定删除已选的 M 个标签？账单上的标签标记同步移除，此操作不可撤销`）→ 确认 → `batchDeleteTags([...selectedIds])` → `resetPaging()` + 退出多选态；**失败保留选中态与模式**（可重试），toast 由 store 弹
- [x] 5.6 **多选流·退出**：点「取消」或再点「多选」→ 清空 `selectedIds`、回普通态，零请求
- [x] 5.7 选中范围 = 已加载 `displayedTags`（未「展开更多」部分不含，需求既裁定）；空标签库「多选」不禁用（无 chip 可选、操作条永不出现，不造禁用态）

## 6. 边界与异常（设计 §2.4 逐条）

- [x] 6.1 并发幽灵：他端已删 → 后端整单 400，前端弹后端中文 message，不动本地选中态（用户重试自愈）
- [x] 6.2 `ids` 含重复：后端按 `set(ids)` 判、删除数按 set 计；前端本就 Set 语义——两侧口径一致，不额外去重逻辑
- [x] 6.3 清空后再点清空：`total=0` 按钮已禁用；后端兜底 `deleted_count:0` 成功

## 7. 后端测试（追加至 `backend/tests/test_tags.py`，设计 §2.5 后端 6 条）

- [x] 7.1 批量删 3 全命中 → 200、`deleted_count=3`、三行 `deleted_at` 非空、其余标签不受影响
- [x] 7.2 ids 含一个不存在 id → 400 中文 message、**零行被软删**（原子性断言）
- [x] 7.3 ids 含他人标签 id → 同 7.2（跨用户拒绝）
- [x] 7.4 `clear-all` 有标签 → 全软删、计数正确；再点一次 → 200 `deleted_count=0`（幂等）
- [x] 7.5 `clear-all` 不触碰 `user_id IS NULL` 全局行（红线断言）
- [x] 7.6 软删后 `GET /api/records` 该行 `tag=null`（M0 联动，验 REQ-001「标记同步移除」）

## 8. 前端测试（`SettingsSubPages.test.js` 新 describe，设计 §2.5 前端 5 条）

- [x] 8.1 `total=0` 时「清空」`disabled` 为真且点击不发请求（mock api 计数 0）
- [x] 8.2 ConfirmDialog 未确认 → `clearAllTags` 调用次数 0
- [x] 8.3 多选模式：进入后 chip 勾选态类名存在；选中 M 项操作条出现、文案含「已选 M 个」；取消后 `selectedIds` 清空且 `batchDeleteTags` 调用 0 次
- [x] 8.4 多选删除提交载荷 ids 与选中集逐字一致；成功后 `multiSelect=false` 且列表刷新
- [x] 8.5 多选态下「清空」按钮与单 chip ✕ 均不渲染（模板断言）

## 9. 验收门槛

- [x] 9.1 本模块后端/前端测试全绿；全量 `pytest` / `npx vitest run` 绿（唯一红灯若出自对向泳道在途文件，notes 登记归属即可）
- [x] 9.2 mypy 基线零新增；`ruff check` clean；eslint 基线零新增
- [x] 9.3 全局红线自查：标签批量操作**不写回溯**；`user_id IS NULL` 全局行零写入；`frontend/dist` 不提交
- [x] 9.4 pathspec 精确提交：§「涉及文件」全清单 + 本任务文件；不 push

**验收标准（REQ-001/002）**：N>0 清空后列表为空、账单标签标记消失；N=0 按钮禁用；未经确认弹窗零删除；多选 M 项删除后未选标签及其账单关联不受影响；已选 0 操作条不出现；中途取消零删除。
