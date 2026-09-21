# M3 - 标签输入免回车：保存账单即保存标签（需求三）

> 对应需求三（设计 §三）。痛点：输入新标签文字后不回车直接点保存，文字静默丢失（`submit()` 只读 `selectedTagName`，而它仅由回车/点选填充）。改造 submit 前置「待确认文字」归一（D4），无二次确认弹窗。
> 涉及文件：`RecordFormPage.vue`（submit :396-432 + 标签确认逻辑 :356-378 邻近 + onTagSelected 清除分支 :341-345）。RecordFormPage 串行：M2 → **M3** → M4。
> 与 M4 同控件：实现与提交独立，末了联合验收链路（D9）。

---

## 1. submit 前置「待确认文字」归一（设计 §3.2.1，D4）

- [x] 1.1 pending 判定：`selectedTagId === -1 || selectedTagId == null` 时取 `(tagSearchQuery || selectedTagName || '').trim()`；tagId 为真实 id 时**不采信**搜索框文字（以已选中为准，勿扩大口径为「文字优先」）
- [x] 1.2 归一①：先在现有防抖结果 `tagSearchResults` 内查精确同名（`t.id !== -1 && t.name === pending`）
- [x] 1.3 归一②兜底：未命中 → 发一次**非防抖** `searchTags(pending)`；结果 `=== null`（查询失败）→ `appStore.showToast('标签校验失败，请重试保存')` + **中止本次保存**（不建标签不落账单，finally 复位 submitting）——后端无查重、`Tag.name` 无唯一约束，校验不可用时宁可不保存也不静默造重复
- [x] 1.4 精确同名 → 直接关联既有标签 id，零创建（需求 3.2）
- [x] 1.5 无匹配 → `createTagData({ name: pending, category_id: categoryId.value })` 并关联本单；`createdTagName` 记录供 toast
- [x] 1.6 toast 合并提示：新建时「记账成功，已新建标签「x」」/「账单已更新，已新建标签「x」」，否则维持原文案；全程无二次确认（需求 3.3）
- [x] 1.7 `data` 载荷结构（现 :410-417）不变，`tag_id: tagId || null`；编辑模式同函数天然覆盖（需求 3.4），`updateRecord` 同口径

## 2. 旧路径零改动 + 清除防御（设计 §3.2.1 尾注）

- [x] 2.1 点选（`onTagSelected` :340-354）与回车（`onCreateTagFromSearch` :356-378）两条旧路径行为不回退（需求 3.5）；回车 temp(-1) 在 submit 走同段归一，语义严格不劣化
- [x] 2.2 `onTagSelected` 空值分支（:341-345）追加 `tagSearchQuery.value = ''`——✕ 清除后残留旧标签名不得被下次保存「自动确认」
- [x] 2.3 未保存即离开：归一只发生在 `submit()` 内；`tagSearchQuery` 不入快照——纯标签文字变化不置 dirty，维持现状（需求 3.5，不新增确认拦截）

## 3. 失败原子性（设计 §3.2.2）

- [x] 3.1 顺序维持「先建标签→再存账单」（现状）：建标签成功但账单保存失败 → 标签成孤儿，下次同名走精确关联自愈——既有行为，本批不扩 scope，登记边界表即可

## 4. 边界与异常（设计 §3.3，走查 + 用例覆盖）

- [x] 4.1 文字 = 已选标签名（选中后又原样输入）→ pending='' → 直接关联原标签，零创建
- [x] 4.2 已选真实标签后再改输入框文字 → 丢弃新文字、关联原标签（§2.1 判定口径的用例化）
- [x] 4.3 文字仅空白 `'  '` → trim 后空，不触发归一
- [x] 4.4 回车 temp(-1) 未动直接保存 → 同名关联否则创建（旧行为一致）
- [x] 4.5 同名判定用严格 `===`，不做大小写/全半角归一化模糊

## 5. 测试（设计 §3.4）

- [x] 5.1 vitest 主链路：输入 `'奶茶'` 不回车不点选 → results 无同名 → `createTagData` 以 `{name:'奶茶', category_id}` 调用、`createRecord` 载荷新 tag_id、toast 含「已新建标签「奶茶」」
- [x] 5.2 vitest 同名（防抖结果内）：results 含同名 → 不调 createTag、关联既有 id
- [x] 5.3 vitest 同名（防抖未回）：results 空 + `searchTags` mock 返回同名 → 不 createTag（锁死②兜底步）
- [x] 5.4 vitest：已选真实标签后 query 残留/异变 → 不归一；✕ 清除后 `tagSearchQuery === ''`
- [x] 5.5 vitest 编辑模式：同 5.1（updateRecord 断言）
- [x] 5.6 vitest 兜底查询失败中止：results 无同名 + searchTags reject → createTag/createRecord **零调用**、toast「标签校验失败」、isDirty 保持、submitting 复位
- [x] 5.7 vitest 旧路径回归：点选、回车两用例保持通过；既有「回车才建标签」口径用例表述改写为「三路径（点选/回车/直接保存）」（附录 B）
- [x] 5.8 vitest 未保存离开：仅改 tagSearchQuery → createTag 零调用
- [x] 5.9 `RecordFormPage.test.js` 只增「标签免回车」组 + 改回车口径用例，M2/M4 组不触碰

## 6. 验收门槛

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 6.2 人工：输入新标签名→不碰回车→点保存 → 账单保存成功、详情页可见该标签
- [ ] 6.3 人工：输入既有同名文字直接保存 → 关联既有标签，标签管理无重复条目
- [ ] 6.4 人工：点选/回车两条旧路径不回退
- [ ] 6.5 与 M4 联合验收链路（D9，用例见 m4 任务文件 §6）
- [ ] 6.6 人工：明暗、竖/宽屏自查
