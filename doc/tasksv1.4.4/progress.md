# Money App v1.4.4 总体进度

> 唯一进度载体，仅主 Agent 读写。基线：v1.4.3-boot3 终验后 HEAD `41917b4`（含导出器热修 `2199169`）。
> 本批 = 基于真实使用反馈的 5 项体验改进（标签批量治理 / 分类出身徽章+恢复默认复原 / 导入映射弹窗 / 关于页+版本真值源 / 横屏图标列）。权威需求：`doc/proposalv1.4.4.md`（REQ-001~012）；权威设计：`doc/detailed-designv1.4.4.md`（D1–D10，2026-09-27 逐节经用户确认，含审查轮落定）。
> **本批含全批唯一 schema 变更**（M2 `categories.source` 新列）+ **一次性迁移脚本** → 发布窗口须停库执行（见「发布备忘」）。

---

## 模块清单（6 个，与设计 §0.1 1:1）

| 模块 | 名称 | 需求 | 任务文件 | 状态 | 提交 |
|------|------|------|----------|------|------|
| M0 | 软删标签读链路收口（后端热修） | REQ-001/002 前提（D2） | `m0-soft-delete-readpath.md` | pending | — |
| M1 | 标签批量治理 | REQ-001、REQ-002 | `m1-tag-batch-governance.md` | pending | — |
| M2 | 分类出身徽章 + 恢复默认连定制复原 | REQ-003、REQ-004、REQ-005 | `m2-category-source.md` | pending | — |
| M3 | 导入映射弹窗 | REQ-006、REQ-007 | `m3-import-dialog.md` | pending | — |
| M4 | 关于页 + 版本单一真值源 | REQ-008、REQ-009 | `m4-about-page-version.md` | pending | — |
| M5 | 横屏侧边栏图标列 | REQ-010、REQ-011、REQ-012 | `m5-sidebar-rail.md` | pending | — |

## 开发顺序（设计 §0.1 依赖）

```
第一波（三线并行）：M0 → M1 链 ｜ M2 ｜ M5
第二波（串行接力）：M3（串在 M2 后，同文件 import_service.py）｜ M4（串在 M2 后，同文件 main.py）
收尾：主 Agent 终验（六命令 + dist 重建 + README 条目 + 版本政策一句）
```

- **M0 必须先于 M1 合入**（M1 验收断言依赖 M0 的软删口径）——两泳道：`M0 → M1` 串行一条，M2 独立一条。
- M2 落盘后再派 M3、M4（各自只等自己共享文件的半区）。
- M5 纯前端独立泳道，随时可并行。

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `record_service.py` / `statistics_service.py` / `export_service.py` | M0 | 独占 |
| `tags.py`(router/service/schema) + `api/tags.js` + `SettingsTagsPage.vue` + `useCategoriesStore.js` + `test_tags.py` | M1 | 独占 |
| `category*`（model/schema/service/router/presets/迁移脚本）+ `api/categories.js` + `SettingsCategoriesPage.vue` + `main.py` | M2 | main.py 单行级 |
| `import_*.py`（schemas/service）+ `CsvMappingDialog.vue`(+新 test 文件) | M3 | **`import_service.py` 与 M2 共享**（M2 只给三处造行点加 `source=0`）→ M2 先合，M3 开工重读行号勿回退 |
| `constants.py` + `routers/version.py` + **`main.py`** + 关于页/路由/设置页 | M4 | **main.py 与 M2 共享**（均为单行 import/参数替换）→ 按 **M2 → M4** 顺序合入（设计 §0.2 注） |
| `AppLayout.vue` + 两测试 | M5 | 独占 |
| `SettingsSubPages.test.js` | M1、M2 | 各模块**只增自己的 describe 块**，不触碰对方；M4 已裁定**新建独立 `SettingsAboutPage.test.js`**，不进该文件 |
| `backend/money.db` | — | **全程只读**；开工/终验 SHA256 双对照 |

## 已确认设计决策（实现约束，执行期不得重议；逐条以设计 §0.3 为准）

- **D1** 标签批量接口 = `POST /api/tags/batch-delete`（body `{ids}`）+ `POST /api/tags/clear-all`，命名沿 `/records/batch-delete`。
- **D2** 软删标签 =「对用户不存在」，三处读链路收口（账单 `tag:null` / 统计排除 / CSV 导出 `tag_name:""`）；**SQL 导出不改**（备份语义）——超出 REQ 字面的既有缺陷翻案，用户明确拍板。
- **D3** 徽章出身 = `categories.source` 新列 + 迁移脚本 `migrate_to_v1.4.4_source.py`；不用名字推导、不改 `is_preset` 语义。
- **D4** 版本真值 = `backend/app/constants.py::APP_VERSION="1.4.4"` + 无鉴权 `GET /api/version`。
- **D5** 弹窗钳高在 CsvMappingDialog 内部三段式（90vh 定值），不动全站 AppDialog 壳。
- **D6** 恢复默认弹窗预告 N/M 数字；M 判据 = 名/图标破坏 + 序尾记；前后端共享**同一张具体整数用例表**，冲突以后端为准回炉用户。
- **D7** 标签页头部 `多选`｜`新增`（tonal）+`清空`（text 弱化，0 标签禁用）。
- **D8** CoW 副本**不可单删**（`source===1` 前端隐藏删除钮 + 后端 403）；副本「消失」仅经恢复默认。
- **D9** 收起态图标列宽固定 72px；登出沿用现行为无二次确认；未登录退出图标不渲染。
- **D10** 分类映射 `create` 载荷新增可选 `name`；前端「编辑过才发 name」保向后兼容。
- **审查轮落定（2026-09-27）**：① M5 rail 宽走 Vuetify 3.12 `:rail-width="72"` **prop**（仓里不存在对应 CSS 变量，勿样式覆写）；② AppLayout 测试环境全 stub → 断言只走 props + 源码正则，计算宽/悬停/滚动条归真机人工；③ D8「预设定制无单点回退」后果，用户裁定 a=**维持现状仅登记**，执行期不得加单点回退入口。
- 需求开放问题 **Q1/Q2 均已落定**（D7/D6）；标签清空/批量删除**不写回溯**（2026-09-27 裁定，推翻早先口径）。
- **ui-design 审查轮（2026-09-28，skill `.claude/skills/ui-design.md` 全文过设计，用户裁定「补」已回文档）**：① M3 §4.1——`rounded="xl"` 登记为被全局压至 20px 的遗留属性（不依赖其圆角值）、`div.mapping-body` 挂 `tabindex="0"` 键盘可达（M3 任务 3.2/3.3/6.1 同步）；② M5 §6.2——rail 钮前景色口径：导航/设置 4 钮 `:color` 三元式（命中 `primary`/未命中 `on-surface-variant`），主题/登出恒 `on-surface-variant`（M5 任务 2.3/4.2 同步）；③ M1 §2.3——「弱色」落定=text 钮不传 color；多选勾选图标改同系 filled 配对（`mdi-checkbox-blank-circle`/`mdi-checkbox-marked`）（M1 任务 5.1/5.3 同步）。设计 §0.3 已加注：**均为口径细化，不改 D 决策本体，执行期以更新后的设计+任务文件为准**。低级项 #6 text-error、#7 版本号 tabular-nums、#8 90vh 复核为不违规/不处理。**后续裁定（同日提问落定）**：#2 rail 前景色取 `on-surface-variant`、#3 图标同系 filled 配对均维持；skill `ui-design.md` 已同步（十四章新增「自身可滚动容器挂 tabindex=0」裁定 + 审查清单一条 + 复核日期续至 2026-09-28）；本批文档改动（设计 + m1/m3/m5 任务 + progress + skill）**暂不提交，用户先复核**，提交时点另行裁定。
- **任务审查轮（2026-09-27，任务文件对账后用户拍板）**：T1 关于页核心优势 = **5 条**（设计 §5.2 六句中「快速记账模板」并入首条，其余逐字成条，不扩写）；T2 M4 前端测试 = **新建独立 `SettingsAboutPage.test.js`**（设计两可作废）；T3 清空/多选/恢复默认三处确认弹窗文案 = **照设计文案定稿**。实测核验排除两疑点：restore-default 自建堆现实现即「改挂其他」（`category_service.py:426-436`），与设计一致；标签页 `total` 即服务端全量计数，清空文案口径无歧义。另修正 M5 §2.2 计数笔误（六项→七项）。

## 全局红线（各模块共同遵守）

1. `backend/money.db` 全程只读；开工/终验 SHA256 双对照；禁 `git add -f`。
2. 业务错误：service 抛中文 `ValueError` → 路由转 `error_response(Code.PARAM_ERROR, str(e))`；不依赖 FastAPI 422（M1 batch-delete 畸形 body 的 422 为设计明示例外）。
3. 批量写库**单事务原子提交**（与 reorder 同口径）；`user_id IS NULL` 全局预设/标签行不被写脏的红线维持（例外仅 M2 §3.4 步骤 4 的合法复位）。
4. 质量门禁六命令全绿；mypy 基线零新增口径；`frontend/dist` 不随模块提交、终验统一重建单独提交。
5. §0.6 全局 Non-Goals 即禁扩清单：不做标签映射自定义名称；多选不持久化不跨页；关于页无网址/部署方式/外链；不改竖屏抽屉与底栏、不动顶栏右侧深色钮、不改 FAB；不改 `is_preset` 既有语义；不做历史回溯补录与撤销通道；SQL 导出不加 `deleted_at` 过滤；`frontend/package.json` 的 `0.0.0` 不改；不重构 AppDialog 壳；不引入 v-stepper/新依赖。
6. 既有测试零删除、零放宽——唯一允许的既有断言改写：M2 徽章用例改 `source` 口径、M5 AppLayout 收起/展开断言更新（设计点名）。
7. 组件/函数不重命名（`CsvMappingDialog.vue` 等）；`CategoryMappingItem.type` 空转字段不删。
8. 本批除 M2 外零 schema 变更；M2 迁移脚本不进启动自动执行路径（独立一次性，沿 dormant 范式）。
9. 标签批量操作、恢复默认均**不写数据回溯**；不回补历史回溯记录。
10. README 只改 Version History（+ M4 收尾的版本政策一句，登记于终验）；`screenshots/` 不提交。

## 编排约定（仅主 Agent）

- **E1** 主 Agent 不亲自写业务代码；子 Agent 不 push、不建分支、不 `git add -A`；每模块测试全绿后 pathspec 精确提交（含本模块任务文件），progress.md 由主 Agent 单独 pathspec-only 提交。
- **E2** 派单简报必须显式列出并发在途的禁触清单（对向泳道全部文件 + 他模块任务文件 + 本 progress.md + `backend/money.db`）。
- **E3** 全量测试若唯一红灯出自对向泳道在途文件，`notes` 登记归属 + 复跑确认非本模块引入即可提交。
- **E4** 大模块触顶风险（实测勾选数：M2 51 / M1 35 / M5 28 / M4 27 / M3 27 / M0 14）：M2 优先拆**后端半区（不提交）→ 前端半区（含整模块 pathspec 提交）**两段接力，M1 视子 Agent 负荷同样处理；中断后派收尾 Agent（审计工作树 vs 任务文件 → 补缺 → 勾选 → 精确提交）。
- **E5** 子 Agent 简报与本文件/D 裁定冲突时，以任务文件 + 设计 D 裁定为准执行并在 notes 上报；主 Agent 核验实地 grep 复核自证，不轻信报告。
- **E6** 涉及 push/远端状态陈述必须先 `git status -sb` 实测；子 Agent `git commit` 可能被权限层拦下而 `git add` 已成功——主 Agent 提交一律 pathspec-only 且提交前查 `git diff --cached --name-only`。
- **E7** general-purpose 子 Agent 无 browser-use MCP：涉及浏览器取证的任务按「DOM/ASGI 级等价取证 + 移交主 Agent 终判」降级口径派单，真机观感留人工。

## 发布备忘（M2 迁移窗口，设计 §3.1）

- [ ] 现场库发布窗口：备份 `money.db` → 停服 → **先于新版后端启动**执行 `python migrate_to_v1.4.4_source.py` → 再起新版后端 + 新 dist
- [ ] 迁移幂等：`source` 列已在场 → `[SKIP]` no-op（二次跑安全，测试已断言）
- [ ] 已知边界随条目公告：v1.4.2 前「同名删除重建」历史自建行回填为 `source=1`（显示「预设」徽章）；用户删除后重建同名即归位 `source=0`
- [ ] 除 M2 外零 schema 变更、零新增依赖（前后端）
- [ ] 回退：换回旧后端 + 旧 dist；`source` 列为 additive 列，旧版代码不读取该列，无需回滚数据（登记确认即可）

## 终验清单（质量门，主 Agent 执行）

- [x] 开工登记：复测六命令基线并写入下方「基线」节（2026-09-28 实测：pytest 665 / vitest 411 / mypy 85 / ruff clean / eslint 0e+2w / dist gzip 538,444 B）
- [ ] `pytest tests/ -q` 全绿、0 skipped
- [ ] `npx vitest run` 全绿
- [ ] mypy = 开工基线零新增；`ruff check` All checks passed
- [ ] eslint 基线零新增；`npm run build` 成功 + dist 重建单独提交（gzip 增量对比开工基准，可接受性留人工裁定）
- [ ] `backend/money.db` SHA256 收档 = 开工登记逐字一致
- [ ] 跨模块闭环点必查：① M0→M1 软删口径联动用例在场；② M2/M3 序尾记用例表**逐字同源** grep 比对；③ M2→M4 main.py 两笔改动共存无回退；④ M2→M3 `import_service.py` `source=0` 三处在位且 M3 未回退；⑤ `SettingsSubPages.test.js` 各模块 describe 块互不触碰；⑥ 全仓版本字面量收敛（后端只剩 constants.py）；⑦ M5 rail-width 走 prop 非 CSS 覆写（grep `--v-navigation-drawer-rail-width` 零命中）；⑧ ui-design 审查轮（2026-09-28）补口径三处在位：M3 `mapping-body tabindex="0"`、M5 rail 钮 `color` 三元式 + 主题/登出恒 `on-surface-variant`、M1 勾选图标 `mdi-checkbox-blank-circle`/`mdi-checkbox-marked`（grep 旧字面量 `mdi-checkbox-blank-circle-outline`/`mdi-check-circle` 在标签页零命中）
- [ ] README Version History 条目 + 版本政策一句（「版本号唯一定义于 `backend/app/constants.py`」）
- [ ] 浏览器实测（主 Agent 亲执，tmp 副本库）：标签清空/多选流、恢复默认弹窗 N/M 数字与黄金链路、导入弹窗 90vh 中段滚动、关于页版本渲染、宽屏 rail 图标列切换
- [ ] progress.md 全模块状态收口 + 本文件 pathspec-only 提交

## 基线（2026-09-28 开工实测登记）

- HEAD：`41917b4`（`git rev-parse --short HEAD` 实测）
- `backend/money.db` SHA256：`b7974d151c6edc17ec964969ef103570f0688d8ec521e05d3f58d899e6c7deb3`（sha256sum 实测，全程只读双对照）
- 六命令基准（2026-09-28 实测，不得沿用 boot3 参考值）：
  - `pytest tests/ -q`：**665 passed**（0 failed；仅 WinError 5 .pytest_cache 写入警告，非失败）
  - `mypy app`：**85 errors in 14 files**（基线零新增口径对照值；CLI 参数被 pyproject strict=true 覆盖，同数字）
  - `ruff check app tests`：**All checks passed**
  - `npx vitest run`（npm test）：**411 passed / 411**（15 files）
  - `npm run lint`：**0 errors / 2 warnings**（CsvMappingDialog.vue 既有 require-default-prop 两条，基线同值）
  - dist gzip 基准：**538,444 B**（现行 dist，js/css/html 合计 `gzip -c` 默认级别，37 文件；与 `17971aa` 提交记录逐字一致）

## 进度统计

| 模块 | 总任务数 | 已完成 | 进度 |
|------|---------|--------|------|
| M0 | 14 | 0 | 0% |
| M1 | 35 | 0 | 0% |
| M2 | 51 | 0 | 0% |
| M3 | 27 | 0 | 0% |
| M4 | 27 | 0 | 0% |
| M5 | 28 | 0 | 0% |
| **合计** | **192** | 0 | 0% |

## 模块执行记录

（主 Agent 逐模块核验后填写：提交 pathspec、复跑结果、认可的偏离、交接事实）

## 阻塞清单

（空）

## 待人工抽检清单（子 Agent 不勾选，执行时逐条抄录原文）

设计附录已点名四项（执行期各模块真机项再抄入此处）：
- [ ] ① 真机 1280×720 Cashew 17 列导入弹窗观感（REQ-006，M3 §7.5）
- [ ] ② 横屏收起/展开图标列真机点验与截图（REQ-010/011，M5 §5.4；含 rail 计算宽 72px、无文字残留/无横向滚动条、悬停提示真实出现三项）
- [ ] ③ 关于页深浅主题目检（REQ-009，M4 §5.6）
- [ ] ④ 现场库发布窗口：`migrate_to_v1.4.4_source.py` 先备份→停服→执行→起新版（M2 迁移，沿发布备忘流程）
