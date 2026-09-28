# M0 - 软删标签读链路收口（后端热修，REQ-001/002 验收前提）

> 对应设计 §一（决策 D2，§0.4-2/3/4 三处缺陷登记）。目标：软删标签对用户「不存在」——账单列表 `tag:null`、统计标签分布排除、CSV 导出 `tag_name:""` 三处读链路一并收口；SQL 导出保持备份语义**不改**。
> 涉及文件：改 `backend/app/services/record_service.py`、`backend/app/services/statistics_service.py`、`backend/app/services/export_service.py`；新增 `backend/tests/test_soft_deleted_tags.py`。**前端零改动（仅回归）**。
> 依赖：无。**必须先于 M1 合入**（M1 验收断言「软删后 `GET /api/records` 该行 `tag=null`」依赖本模块口径）。除 `main.py` 外与其他模块零文件交叉。
> 行号为设计快照（2026-09-27）参考位，开工以 grep 定位为准。

---

## 1. 收口点一：账单富化（`record_service._enrich_record`，约 :529-537）

- [x] 1.1 `tag = await db.get(Tag, record.tag_id)` 后条件收紧为 `if tag and tag.deleted_at is None:` 才构造 `tag_info`，否则保持 `tag_info = None`
- [x] 1.2 确认列表/详情/编辑回填/历史富化均经此单函数（一处收口，不另找他处）；`record.tag_id` 为 None 的行为不变（`tag_info=None`）；悬空 `tag_id`（行不存在）现行为已是 None，不变

## 2. 收口点二：统计标签分布（`statistics_service.get_tag_stats`，约 :139-152）

- [x] 2.1 `.where(...)` 追加 `Tag.deleted_at.is_(None)`；响应结构零变化
- [x] 2.2 自查副作用：软删行不再成组；NULL-tag 行本就被 `Record.tag_id.isnot(None)` 排除，无新增跳过面

## 3. 收口点三：CSV 导出（`export_service.py` 标签查找 SQL，约 :39-43）

- [x] 3.1 原生 SQL 追加 `AND deleted_at IS NULL`，目标形态：`SELECT id, name FROM tags WHERE (user_id = :uid OR user_id IS NULL) AND deleted_at IS NULL`
- [x] 3.2 **`OR` 两段必须加括号**（防优先级错——此为本模块最易错点，测试 §4.3 钉住）；软删标签的账单行 `tag_name` 自然落 `""`
- [x] 3.3 SQL 导出（文本 dump）**一字不改**：行连同 `deleted_at` 原样导出（备份语义，D2 明确范围）

## 4. 测试（新文件 `backend/tests/test_soft_deleted_tags.py`，设计 §1.3 五组 Given/Then 逐条对号）

- [x] 4.1 账单挂标签 T → 软删 T → `GET /api/records` 该行 `tag === null`、`GET /api/records/{id}` 同（对应 §1.3-1）
- [x] 4.2 `GET /api/statistics/tags` 不含 T 分组；**未删标签 U 的分组数值逐字不变**（防过度过滤回归锚，§1.3-2）
- [x] 4.3 CSV 导出：T 的账单行第 4 列 `tag_name` 为 `""`；U 的行不变；**含全局预设标签（`user_id IS NULL`）的行仍正常出名字**（括号优先级证据，§1.3-3）
- [x] 4.4 SQL 导出：文本仍含 T 行且 `deleted_at` 值保留（§1.3-4）
- [x] 4.5 走既有单删接口 `DELETE /tags/{id}` 软删后，上述三处表现同 4.1–4.3（即本模块同时修复既有单删口径，§1.3-5）

## 5. 验收门槛（合入前逐项实测）

- [x] 5.1 新测试全绿；`pytest tests/ -q` 全量绿（含既有 records/statistics/export 用例零修改零放宽——如需改既有断言即为过度收口信号，回炉）
- [x] 5.2 `mypy backend/app` 基线零新增；`ruff check` clean
- [x] 5.3 六命令之后端四项即可（M0 零前端改动，vitest/eslint 由 M1 起接力跑全量，主 Agent 终验兜底）
- [x] 5.4 pathspec 精确提交：三个 service 文件 + `backend/tests/test_soft_deleted_tags.py` + 本任务文件；**不 push、不建分支、不 `git add -A`**
- [x] 5.5 `notes` 登记：改动行号快照 vs 实际落点差异、有无第四处读链路命中（grep `deleted_at` 全仓复核 `Tag` 相关读点）

**验收标准（REQ-001 前提 / 设计 D2）**：软删标签在账单、统计、CSV 三处对用户不可见；SQL 导出备份语义不变；`frontend/dist` 不随本模块提交。
