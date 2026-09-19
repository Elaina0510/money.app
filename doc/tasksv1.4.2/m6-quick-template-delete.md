# M6 - 快速记账删除模板修复（自动模板按签名忽略）

> 对应需求六（设计 §六，决策 D4/D9）。自动模板删除失效修复：新增 `quick_templates.kind` 忽略机制 + `DELETE /quick-templates/auto` 按签名抑制；手动/自动删除均加确认弹窗与 toast。
> 涉及文件：`backend/app/models/quick_template.py`、新增 `backend/migrate_to_v1.4.2.py`、`record_service.py`、`routers/records.py`、`frontend/src/api/records.js`、`SettingsQuickTemplatesPage.vue`、`test_records.py`、`SettingsSubPages.test.js`。
> 依赖：无（独立穿插）。与 M4 共享 SettingsQuickTemplatesPage.vue，按 M4 → M6 合并（M4 加外层卡壳，本模块改删除流程/key/弹窗）。

---

## 1. 数据层：`quick_templates.kind`（决策 D4）

- [x] 1.1 `models/quick_template.py` 新增 `kind: str = Field(default="manual", max_length=20, nullable=False)`（manual / auto_ignored）
- [x] 1.2 忽略记录约定：仅签名三要素有效（tag_id/type/amount），`category_id=None`（分类由标签推导可变，不纳入签名）
- [x] 1.3 新建 `backend/migrate_to_v1.4.2.py`（沿 `migrate_to_v1.4.py` 手法）：`PRAGMA table_info(quick_templates)` 检查列缺失 → `ALTER TABLE ... ADD COLUMN kind VARCHAR NOT NULL DEFAULT 'manual'`；幂等可重跑（已存在输出 SKIP 不报错）
- [x] 1.4 隔离性核查：全库 grep `QuickTemplate` 仅 `get_quick_templates`/add/delete 三处消费，逐一确认加 kind 过滤，`auto_ignored` 行不得混入任何查询出口

## 2. 后端：聚合过滤（`get_quick_templates`）

- [x] 2.1 查忽略签名集合：`select(tag_id, type, amount).where(user_id==uid, kind=="auto_ignored")` → `ignored = {(tag_id, type, int(round(amount*100)))}`
- [x] 2.2 auto 聚合循环内：`(row.tag_id, row.type, int(round(row.amount*100))) in ignored` → continue
- [x] 2.3 过滤发生在 `.limit` 之后的 Python 循环（现状聚合直觉保持），被忽略组合彻底消失、不重排补位
- [x] 2.4 手动项去重键 `seen_keys` 升级为分单位整数签名同口径——消除手动/自动浮点表示差异导致的重复展示
- [x] 2.5 金额全程 `int(round(元×100))` 分单位整数比较，禁止浮点 `==`（决策 D9，易错点 3）；amount 列**仍存元**，勿改列语义

## 3. 后端：忽略服务 `ignore_auto_quick_template`

- [x] 3.1 签名 `(db, tag_id, type_, amount_cents, current_user=None) -> bool`
- [x] 3.2 tag 不存在或已软删 → return False（路由层 → 404）
- [x] 3.3 **禁 SQL 浮点相等**（易错点 14）：SQL 只按 `user_id+tag_id+type` 收窄候选；Python 内 `int(round(r.amount*100)) == amount_cents` 筛同签名
- [x] 3.4 幂等：同签名已有 `auto_ignored` 行 → 直接 True 不重复插入
- [x] 3.5 同签名手动模板行一并删除（需求：删除后条目即时消失）
- [x] 3.6 插入忽略行：`user_id=uid, tag_id, category_id=None, type, amount=round(cents/100,2), kind="auto_ignored"`；commit

## 4. 后端：路由（`routers/records.py`）

- [x] 4.1 `@router.delete("/quick-templates/auto")`，Query 参数：`tag_id(gt=0)`、`type(pattern=r"^(income|expense)$")`、`amount_cents(gt=0, 单位分)`
- [x] 4.2 服务返回 False → `error_response(Code.NOT_FOUND, "标签不存在")`；成功 → `success_response(message="自动模板已忽略")`
- [x] 4.3 **路由顺序强约束**：声明在 `DELETE /quick-templates/{template_id}`（现 :97）**之前**，否则 "auto" 被 int 抢匹配 422（易错点 1）
- [x] 4.4 现有 `DELETE /{template_id}` 行为不变（需求 2 条）

## 5. 前端：API

- [x] 5.1 `api/records.js` 新增 `ignoreAutoQuickTemplate({tag_id, type, amount_cents})` → `request.delete('/records/quick-templates/auto', { params })`

## 6. 前端：删除流程（`SettingsQuickTemplatesPage.vue`）

### 6.1 确认弹窗 + 反馈

- [x] 6.1.1 新增 `showDeleteDialog`/`deletingTemplate`/`deleting` refs 与 `deleteMessage` computed（文案区分：自动「…该组合今后不再自动出现」/ 手动普通文案）
- [x] 6.1.2 引入 `ConfirmDialog`：title「删除模板」、`:loading="deleting"`、confirm-text「删除」、`@confirm="handleDelete"`
- [x] 6.1.3 `removeQuickTemplate(tpl)` 改为只设 `deletingTemplate` + 开弹窗（点 × 不再直接删）
- [x] 6.1.4 `handleDelete()`：`tpl.id` 存在 → `deleteQuickTemplate(tpl.id)`；否则 → `ignoreAutoQuickTemplate({tag_id, type, amount_cents: Math.round(Number(tpl.amount)*100)})`
- [x] 6.1.5 成功：本地 `filter(x => x !== tpl)` 即时移除 → toast「模板已删除」→ 后台静默 `loadQuickTemplates()` 对齐
- [x] 6.1.6 失败：toast「删除失败」(error)，列表保持原状（本地未动过）；finally 复位三个状态

### 6.2 列表 key 稳定化

- [x] 6.2.1 `:key` 改 `` `${tpl.source}-${tpl.tag_id}-${Math.round(Number(tpl.amount)*100)}` ``（:29）

## 7. 测试

### 7.1 后端迁移脚本

- [x] 7.1.1 临时 SQLite 造旧表结构跑一次 `migrate_to_v1.4.2.py` → kind 列存在、旧行全 'manual'；重跑输出 SKIP 不报错

### 7.2 后端 pytest（`test_records.py` 新增用例组）

- [x] 7.2.1 `DELETE /quick-templates/auto?tag_id&type&amount_cents` → 200；GET 列表不含该自动项；追加同签名账单后再 GET 仍不出现（永久抑制）
- [x] 7.2.2 小数/整元金额签名匹配（12.34 与 25 整两类，覆盖 SQLite REAL/INTEGER 存储差异）；同 tag+type 不同金额不牵连
- [x] 7.2.3 同签名手动模板随行删除；其他签名手动/自动项不受影响
- [x] 7.2.4 幂等：连删两次同签名 → 均 200、库中忽略行仅一行
- [x] 7.2.5 路由顺序回归：`/quick-templates/auto` 200 非 422；原 `DELETE /{id}` 行为不变
- [x] 7.2.6 未认证 401；跨用户签名隔离（A 的忽略不影响 B 同签名自动项）

### 7.3 vitest（用例 4 **反转改写**，易错点 10）

- [x] 7.3.1 自动模板点删除 → 弹确认；确认后 `ignoreAutoQuickTemplate` 以 `{tag_id, type, amount_cents: 2500}` 恰调一次、`deleteQuickTemplate` 未调、条目立即消失、成功 toast 一次（旧「无 id 不请求只刷新」口径作废）
- [x] 7.3.2 手动模板确认后 `deleteQuickTemplate(21)` 一次；点取消 → 两接口均未调
- [x] 7.3.3 mock reject → 错误 toast、列表保持原状
- [x] 7.3.4 `vi.mock('@/api/records')` 工厂补 `ignoreAutoQuickTemplate` 导出

## 8. 验收与质量门槛

- [x] 8.1 后端 pytest + mypy 基线零新增 + ruff 通过；`npm test`、`npm run lint` 通过
- [ ] 8.2 手工验收：删自动模板确认后条目立即消失，刷新/重进不出现，继续记同标签同金额账单也不复活；金额不同的新组合正常自动生成；删手动模板确认后消失且后端已删；删除失败有错误 toast 且列表原状
- [ ] 8.3 部署备忘：老库需执行 `python migrate_to_v1.4.2.py`（幂等），写入发布备忘
