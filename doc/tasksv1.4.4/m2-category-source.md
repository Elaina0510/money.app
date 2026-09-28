# M2 - 分类出身徽章 + 恢复默认连定制复原（REQ-003 / REQ-004 / REQ-005）

> 对应设计 §三（决策 D3 出身列、D6 弹窗预告数字、D8 副本不可单删）。目标：`categories.source` 新列（0=自建 1=预设派生）+ 一次性迁移脚本；徽章渲染源从 `is_preset` 改为 `source===1`；`restore_default_categories` 重写为「副本合并回全局行、账单改指不迁移、定制丢弃」；恢复默认确认弹窗预告 N/M 数字（前后端共享同一张具体整数用例表）。
> 涉及文件：改 `backend/app/models/category.py`、`backend/app/schemas/category.py`、`backend/app/services/category_service.py`、`backend/app/routers/categories.py`、`backend/app/main.py`（单行 import 替换，与 M4 对 main.py 改动正交、**M2 先合**）；新增 `backend/app/presets.py`、`backend/migrate_to_v1.4.4_source.py`、`backend/tests/test_category_source.py`（或按仓内惯例命名，下同）；改 `frontend/src/api/categories.js`、`frontend/src/pages/SettingsCategoriesPage.vue`、`frontend/src/pages/__tests__/SettingsSubPages.test.js`（只增自己的 describe 块 + 既有徽章用例改写）。
> 依赖：无（可与 M0/M1 并行）。**本模块含全批唯一 schema 变更** → 迁移脚本入发布备忘。
> **同文件串行**：§2.3 表末行需给 `import_service.py` 三处造行点显式 `source=0`（最小行改动），与 M3 同文件 → **M2 先合、M3 开工时重读落盘后行号，勿回退 M2 改动**（设计 §0.2 注同口径）。
> 行号为设计快照参考位，开工以 grep 定位为准。

---

## 1. 数据模型（`models/category.py`，本模块独占）

- [x] 1.1 `Category` 新增列（设计 §3.1）：`source: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))`；补 `from sqlalchemy import Column, Integer` import；注释一行说明「1 = 系统预设或其 CoW 派生副本；0 = 用户自建」
- [x] 1.2 `is_preset` 既有列语义**一字不动**（§0.6 红线）

## 2. 预设定义 SSOT 迁移（新 `backend/app/presets.py`）

- [x] 2.1 新文件导出 `PRESET_CATEGORIES: list[dict]`——14 条与 main.py 现 seed（约 :46-65）**逐字一致**，每条内嵌 `"is_preset": 1, "source": 1`（§3.2）
- [x] 2.2 `main.py` 删除本地定义改 `from app.presets import PRESET_CATEGORIES`（单行级改动）；`restore_default_categories` 内的函数级 import 同步改指 `app.presets`
- [x] 2.3 §0.4-6 造行点写入规则逐点钉死：

| 造行点 | source | 实现要求 |
|---|---|---|
| main.py seed（经 presets） | 1 | dict 内嵌 |
| category_service update CoW 副本（约 :191） | 1 | 显式 `source=1` |
| category_service reorder CoW 副本（约 :247） | 1 | 同上 |
| category_service create 自建（约 :128） | 0 | default 即 0，**显式写出** |
| import_service :385 / :1285 / :1630 | 0 | 同上；**仅此三行最小改动，不碰该文件其余逻辑**（串线与 M3 关系见页首注） |

## 3. 迁移脚本（新 `backend/migrate_to_v1.4.4_source.py`，沿 dormant 脚本范式）

- [x] 3.1 幂等判据：`PRAGMA table_info(categories)` 已含 `source` 列 → 整体 no-op `[SKIP]`
- [x] 3.2 步骤：`ALTER TABLE categories ADD COLUMN source INTEGER NOT NULL DEFAULT 0` → `UPDATE categories SET source=1 WHERE is_preset=1` → `UPDATE categories SET source=1 WHERE is_preset=0 AND user_id IS NOT NULL AND name IN (14 个预设名)`
- [x] 3.3 14 名**在脚本内独立硬编码**（不 import app 代码，保证停服窗口可独立执行），与 `presets.py` 以**一致性断言**钉住（沿 boot2 脚本同款做法）
- [x] 3.4 前置只读检查：`PRAGMA integrity_check` 非 ok 只告警不中止
- [x] 3.5 已知边界写进脚本 docstring（刻意不修）：v1.4.2 前「同名删除重建」历史自建行会被回填为 `source=1`；用户删除后重建同名即归位 `source=0`，与 REQ-004 自洽
- [x] 3.6 新库（create_all）路径无需脚本：列 `server_default="0"` + seed 写 1

## 4. 服务层重写（`category_service.restore_default_categories`，约 :407-494）

单事务控制流（设计 §3.4 五步，全部写完**一次 commit**；任意异常不 commit 整体回滚——原子性红线）：

- [x] 4.1 步骤 1 分堆：载入当前用户全部行 → `derived = source==1 且 user_id 非空`，`custom = source==0`
- [x] 4.2 步骤 2 副本堆合并：逐行按 `name` 找全局预设（`user_id IS NULL AND name==row.name AND is_preset==1`），命中则：
  - ① `UPDATE records SET category_id=g.id WHERE category_id=row.id`（账单改指全局行 id，**不迁移不乱动**——REQ-005）
  - ② `budget_categories` 关联逐条改指 `g.id`；`(budget_id, g.id)` 已存在则删副本侧关联行（`UNIQUE(budget_id,category_id)` 冲突防御）；改指后关联保持有效、**不触发休眠**
  - ③ `UPDATE tags SET category_id=g.id WHERE category_id=row.id AND user_id==uid`；指向已失效行的剩余 `tags.category_id` 置 NULL——**绝不留新增 FK 违规**
  - ④ `db.delete(row)`；`merged_presets += 1`
- [x] 4.3 定制判据（**前后端唯一口径**，§3.4）：`row.name ≠ 预设原名` 或 `row.icon ≠ 预设原图标` → 计 1；改序判据带尾记——派生序列表（可见列表序 `sort_order, id` 升序中全部 `source==1` 行，剔除「其他家族」行）自上而下贪心匹配 `presets.py` 序，匹配跳过的行各计 1（整表单调计 0）；`discarded_customizations = 名/图标破坏数 + 序尾记数`
- [x] 4.4 步骤 2 未命中（影子行）→ 并入 `custom` 堆按步骤 4.5 处理
- [x] 4.5 步骤 3 自建堆：维持现状语义——账单改挂「其他」全局行（无「其他」行时删行兜底，同现状）、`tags.category_id` 置 NULL、`_dormant_budgets_for_deleted_category`、删行、计数
- [x] 4.6 步骤 4 预设复位：遍历 `presets.py`，UPDATE 全局行 `name/icon/sort_order = 默认值`、`source=1`、`is_preset=1`（幂等保险）；**全局行仅此处合法复位，其余路径零写入**
- [x] 4.7 步骤 5 一次 commit；返回 data 五键（§3.3）：`deleted_categories / affected_records / dormant_budgets / merged_presets / discarded_customizations`
- [x] 4.8 病态数据防御（§3.7）：命中全局行还须 `is_preset==1 AND user_id IS NULL`，否则落入 custom 堆（宁删不错并）；预算 `scope_mode=exclude` 关联改指同 include 处理

## 5. 副本不可单删（D8，连坐裁定已确认）

- [x] 5.1 `delete_category` 增加拦截：`category.source == 1` 一律 `raise PermissionError("预设分类不可删除")`（覆盖 CoW 副本；现状「`is_preset==1` 不可删」保留）；路由转 403 `Code.FORBIDDEN`
- [x] 5.2 **执行期不得加单点回退入口**（用户裁定 a=维持现状仅登记——反悔只能「恢复默认」全量丢弃）
- [x] 5.3 前端 `source===1` 行隐藏删除按钮（编辑/拖拽照旧，保存即 CoW）

## 6. 接口契约（`schemas/category.py`、`routers/categories.py`）

- [x] 6.1 `CategoryResponse` 增字段 `source: int`（只增不改不删）
- [x] 6.2 新端点 `GET /api/categories/presets`（`require_auth`；声明在 `/{category_id}` 之前）：`data = [{"name","icon","sort_order"}]` 逐字取 `presets.py`，仅供恢复默认弹窗计算 M
- [x] 6.3 `POST /api/categories/restore-defaults` 响应 data 扩为五键；message 由路由拼装：`已恢复默认分类：删除 N 个自定义分类，M 个预设定制已复原，K 条记录归入「其他」`（K=0 不提该句；N=0/M=0 同理省略对应段）

## 7. 前端（`api/categories.js` + `SettingsCategoriesPage.vue`）

- [x] 7.1 `getPresetCategories()` → `request.get('/categories/presets')`
- [x] 7.2 徽章条件 `v-if="cat.is_preset"` → `v-if="cat.source === 1"`（约 :77）
- [x] 7.3 纯函数 `computeRestoreCounts(list, presets)`（§3.4 同判据；置于 script 可 import/可断言位置）——**用例表与后端 §8.1-10 逐字同源，禁止各写各的**
- [x] 7.4 恢复默认弹窗重写（D6）：点按钮时拉 presets + 用 store 可见列表算 `N = count(source===0)`、`M = computeRestoreCounts(...)`；三条列表文案逐字：
  1. `删除 N 个自定义分类（其下账单改挂「其他」）`
  2. `丢弃 M 个预设分类的定制（名称/图标/排序回到系统默认）`
  3. `账单总数不变，此操作不可撤销`
- [x] 7.5 presets 接口失败 → 弹窗退化为无数字版（`删除所有自定义分类，账单改挂「其他」`/`预设分类恢复默认，定制将被丢弃` 两条），主流程不阻塞
- [x] 7.6 恢复成功 toast 用后端新 message；成功刷新走既有 `restoreDefaults()`（store 内 `fetchCategories` 不动）；`N=0 且 M=0` 照常可执行（幂等）
- [x] 7.7 「其他」家族置尾、拖拽永远可用等 v1.4.3-boot2 语义零触碰

## 8. 测试

### 8.1 后端（新 `test_category_source.py` 等，设计 §3.8 十条逐号）

- [x] 8.1.1 预设改名/换图标 CoW 后 `GET /categories` 副本行 `source==1`；拖序保存→重取仍 `source==1`（REQ-003 双时点）
- [x] 8.1.2 `create_category` 同名「餐饮」重建 → `source==0`（REQ-004）
- [x] 8.1.3 **恢复默认黄金链路**：定制「餐饮」（改名+换图标+改序，下挂 5 条账单 + 1 条 include 预算关联）→ 恢复后账单 `category_id==全局餐饮id`、副本行不存在、全局行名/图标/序=默认、预算关联存在且 `dormant==0`、`merged_presets==1, discarded_customizations==1`、账单总数前后相等（REQ-005 三验收逐字对）
- [x] 8.1.4 自建分类账单改挂「其他」全局行 id；`deleted_categories` 计数含影子未命中行
- [x] 8.1.5 副本单删 → 403 `FORBIDDEN`；`DELETE /categories/{id}` 对全局行行为不变
- [x] 8.1.6 原子性：mock 步骤 3（自建堆）抛错 → 零变更（副本仍在、账单仍挂副本、全局行未复位）
- [x] 8.1.7 `GET /categories/presets` 返回 14 条与 `presets.py` 逐字一致；新库 seed 后全局行 `source==1`
- [x] 8.1.8 迁移脚本（临时库注入旧形制数据）：二次跑幂等 no-op；`is_preset=1→1`、同名副本→`1`、无关自建→`0` 三类回填断言
- [x] 8.1.9 恢复默认后 `PRAGMA foreign_key_check` 零新增违规（tags 改指或置 NULL，无孤儿引用）
- [x] 8.1.10 **序尾记判据用例表**：期望值必须是**具体整数**，按 §3.4 贪心口径逐行人工推演写死（「单调=0」「单行改名=1」「两行互换=推演定值，禁止『或』字多解」）；与前端 §8.2.3 同表——两实现不一致即为缺陷，**以后端返回值为准回炉用户，不得各改各的表**

### 8.2 前端（`SettingsSubPages.test.js` 追加 describe + 既有徽章用例改写）

- [x] 8.2.1 徽章渲染源为 `source`：`is_preset=1, source=0` 畸形 mock 行**无**徽章；`is_preset=0, source=1` 有徽章
- [x] 8.2.2 `source===1` 行无删除按钮；编辑按钮仍在
- [x] 8.2.3 `computeRestoreCounts` 断言表 = §8.1.10 同一张（**表逐字复制**方式同源）
- [x] 8.2.4 恢复弹窗含「丢弃 M 个预设分类的定制」文案与数字；presets reject 时退化为无数字版且按钮可用

## 9. 验收门槛

- [x] 9.1 本模块前后端测试全绿；全量 `pytest` / `npx vitest run` 绿（对向泳道在途红灯按编排约定 E3 归属登记）
- [x] 9.2 mypy 基线零新增（新列 `source: int`，`Category(**dict)` 路径 dict 已含键，无 Any 泄漏）；ruff clean；eslint 基线零新增
- [x] 9.3 红线自查：`is_preset` 语义未动；全局预设行除 §4.6 复位外零写入；`backend/money.db` 零触碰（迁移只在脚本+临时库测试里发生）
- [x] 9.4 pathspec 精确提交：§「涉及文件」全清单 + 本任务文件；main.py 改动为单行级（M4 之后合入时互不冲突）；不 push
- [ ] 9.5 迁移脚本执行窗口说明抄入 progress.md 发布备忘：备份现场库 → 停服 → **先于新版后端启动**执行 → 再起新版

**验收标准（REQ-003/004/005）**：拖动/改名/换图标后徽章不丢、刷新仍在、自建无徽章；删副本重建同名无徽章；恢复默认后定制回原状且其账单仍在该分类下、自建删除账单归「其他」、恢复前后账单总数不变。真机观感项见 progress.md 人工清单。
