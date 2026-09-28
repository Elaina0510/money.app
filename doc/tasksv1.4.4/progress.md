# Money App v1.4.4 总体进度

> 唯一进度载体，仅主 Agent 读写。基线：v1.4.3-boot3 终验后 HEAD `41917b4`（含导出器热修 `2199169`）。
> 本批 = 基于真实使用反馈的 5 项体验改进（标签批量治理 / 分类出身徽章+恢复默认复原 / 导入映射弹窗 / 关于页+版本真值源 / 横屏图标列）。权威需求：`doc/proposalv1.4.4.md`（REQ-001~012）；权威设计：`doc/detailed-designv1.4.4.md`（D1–D10，2026-09-27 逐节经用户确认，含审查轮落定）。
> **本批含全批唯一 schema 变更**（M2 `categories.source` 新列）+ **一次性迁移脚本** → 发布窗口须停库执行（见「发布备忘」）。

---

## 模块清单（6 个，与设计 §0.1 1:1）

| 模块 | 名称 | 需求 | 任务文件 | 状态 | 提交 |
|------|------|------|----------|------|------|
| M0 | 软删标签读链路收口（后端热修） | REQ-001/002 前提（D2） | `m0-soft-delete-readpath.md` | done | `55f8531` |
| M1 | 标签批量治理 | REQ-001、REQ-002 | `m1-tag-batch-governance.md` | done | `50c67cf`（主 Agent 补 commit） |
| M2 | 分类出身徽章 + 恢复默认连定制复原 | REQ-003、REQ-004、REQ-005 | `m2-category-source.md` | done | `87afda2`（E4 接力补全前端半区） |
| M3 | 导入映射弹窗 | REQ-006、REQ-007 | `m3-import-dialog.md` | done | `f60ddf3`（主 Agent 补 commit，E6） |
| M4 | 关于页 + 版本单一真值源 | REQ-008、REQ-009 | `m4-about-page-version.md` | done | `2047043` |
| M5 | 横屏侧边栏图标列 | REQ-010、REQ-011、REQ-012 | `m5-sidebar-rail.md` | done | `a3e278f` |

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
6. 既有测试零删除、零放宽——唯一允许的既有断言改写：M2 徽章用例改 `source` 口径、M5 AppLayout 收起/展开断言更新（设计点名）。**执行期裁定（2026-09-28，主 Agent）**：另认可第三处=M4 对 `SettingsSubPages.test.js` 的 4 处穷尽式结构计数机械同步（设计明令新增「关于」入口卡的必然后果，纯 +1、逐项同锁、非放宽；详见 M4 执行记录）。
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
- [ ] mypy = 开工基线零新增；`ruff check` All checks passed（口径=基线登记的 `ruff check app tests`；`ruff check .` 另命中 legacy `migrate_to_v1.4.py` 两条 E501，属 v1.4 时代已入库文件、本批零改动，不在门禁范围——2026-09-28 终验期核实登记）
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
| M0 | 17（Prompt §二 记 14，任务文件实数 17，以文件为准） | 17 | 100% |
| M1 | 35 | 35 | 100% |
| M2 | 51 | 50（§9.5 现场库迁移窗口留人工） | 98% |
| M3 | 32（Prompt 登记 27，任务文件实数 32，以文件为准） | 31（§7.5 真机项留人工=清单①） | 97% |
| M4 | 27 | 25（§5.5 归主 Agent 终验、§5.6 真机项留人工=清单③） | 93% |
| M5 | 28 | 27（§5.4 真机项留人工） | 96% |
| **合计** | **200**（195 登记值 + M3 实数差 +5） | 185 | 93% |

## 模块执行记录

### M0 软删标签读链路收口（done，`55f8531`，2026-09-28）

- 提交 pathspec：record_service.py / statistics_service.py / export_service.py / tests/test_soft_deleted_tags.py（新）/ m0 任务文件，共 5 文件；无 dist、无 -A/-f，主 Agent `git show --stat` 复核通过。
- 主 Agent 复跑：pytest **670/670**（基线 665 + 新增 5）、mypy **85 errors / 14 files**（= 开工基线零新增）、ruff All checks passed（复跑时工作区含 M2/M5 在途改动仍全绿）。子 Agent 另以 tmp 副本库做 uvicorn 冒烟 /docs 200 两次取证（HEAD 纯净副本 + 真实工作区各一）。
- 三处收口实地 grep 复核在场：record_service.py:534 `if tag and tag.deleted_at is None:`；statistics_service.py:152 软删过滤；export_service.py:45 `(user_id = :uid OR user_id IS NULL) AND deleted_at IS NULL`（OR 两段括号钉死）；:32 分类查找 SQL 一字未动；SQL 导出零 hunk。
- 全仓 `deleted_at` grep：**无第四处读链路命中**，未自扩面（notes 含命中全集逐条判定）。
- 认可的偏离：`Tag.deleted_at.is_(None)` → `col(Tag.deleted_at).is_(None)`（同 tag_service.py:47 既有写法，运行时等价，为守 mypy 基线零新增；设计原串仍可 grep 命中）。
- 防过度收口锚在场：§4.2 未删标签分组数值逐字钉死；§4.3 (归属×软删) 四格真值表含全局预设仍出名字；§4.4 软删前后 SQL 文本除 `-- Date:` 头行逐字相同。
- manual_items：无（M0 任务文件无人工/真机条目，grep 零命中）。
- 口径差上报：Prompt §二 记 M0 勾选数 14，任务文件实为 17 项，以文件实数登记。
- 交接 M1（已写入派单简报）：软删口径三落点行号 + 670 基线 + `55f8531`。
- 遗留：子 Agent 隔离冒烟临时目录 `Temp\m0smoke` 未删（rm 被权限层拦，仓外无影响）；真树启动冒烟曾两度红灯，traceback 核实均为 M2 在途中间态（`no such column: categories.source` / `NameError: Sequence`），非 M0 引入，M2 落定后复跑即绿——E3 归属登记。

### M5 横屏侧边栏图标列（done，`a3e278f`，2026-09-28）

- 提交 pathspec：AppLayout.vue / AppLayout.test.js / m5 任务文件（首入库），共 3 文件；`AppLayout.wideScreenZoom.test.js` 零改动未入提交；无 dist（build 脏化后已 `git restore` 复原）、无 -A/-f，主 Agent `git show --stat` 复核通过。
- 主 Agent 复跑：vitest **421/421**（基线 411 + 新增 10，15 files 含 wideScreenZoom 11 条零改动通过）、eslint **0 errors / 2 warnings**（基线同值）。build 子 Agent 跑成功（dist 复原），主 Agent 不重复跑、终验统一重建兜底。
- 实地 grep 复核在场：`:rail-width="72"` prop（AppLayout.vue:10）；全仓源码 `--v-navigation-drawer-rail-width` **零命中**（红线 7）；rail 区块色绑定 4 处三元式（导航/设置）+ 2 处恒 `on-surface-variant`（主题 :96 / 登出 :113）；`mdi-menu` 全文件仅 1 处=侧栏切换钮本体（:26，两态同 DOM 位 `rail ? 'mdi-menu' : 'mdi-backup-restore'`），顶栏 `app-top-bar` 内汉堡块已删、右侧深色钮保留（:224–236 目视复核）；竖屏三处逐字正则钉死断言在场（M5-T4.8）。
- prop 实测证据（子 Agent notes）：Vuetify 3.12.6 `VNavigationDrawer.js:46` 定义 `railWidth`（default 56）、:136 参与计算宽；jsdom 真实渲染探针输出 rail=true → 内联 `width: 72px`。测试环境全 stub 已核实，断言走 props 白名单 + attribute + `?raw` 区块切片正则，零真实类名/计算样式断言。
- **认可的设计偏离（重要，设计 §6.1 字面不成立）**：设计/任务字面 `drawer.value = !rail.value` 实测会让 permanent 抽屉在 modelValue=false 时被写 `inert` + `translateX(-72px)`——收起态图标列不可见不可点，直接违背 REQ-010 验收。实现改为宽屏分支翻转 `rail` 后 `drawer.value = true`（「在位可见」语义），竖屏 `drawer = !drawer` 逐字未动。**属实现细节修正、不动 D9 裁定本体**，认可；`doc/detailed-designv1.4.4.md` §6.1 对应句待回改（该文档属未提交输入文档批，随人工复核处理）。
- 其余偏离登记（均已在任务文件就地注明）：高亮判据新增 `railActive` 计算属性（`currentRoute` 本体不动，避免牵动竖屏底栏）；rail 钮 `size="48"` + `aria-label`（ui-design §0.8 触控目标/图标钮用途名）；抽屉 append 尾区加 `v-if="!(isDesktop && rail)"` 守卫满足「rail 块零 span 文本」；既有 stub 补 `v-tooltip`（纯增补）；唯一既有断言改写 = M1-T2b 顶栏钮数 2→1（红线 6 点名允许处）。
- 真机观察线索（转人工清单②）：`global.scss:94` `.v-navigation-drawer { border-radius: 0 20px 20px 0 !important }` 会作用于 72px rail 列右边缘（该文件不在 M5 文件面未动）——人工点验时留意观感是否可接受。
- fixed_rounds: 1（CSS 注释含被禁字面量 → 改写 + 测试侧 join('-') 构名）。

### M1 标签批量治理（done，`50c67cf` 主 Agent 补 commit，2026-09-28）

- **E6 实况**：子 Agent `git add` 被权限层两次拦下（判定「并发在途泳道文件」），改动留盘未暂存；主 Agent 核验通过后按九件精确 pathspec 补 add + commit（`git diff --cached --name-only` 复核恰 9 文件：tag schema/service/router/test + api/tags.js + SettingsTagsPage.vue + useCategoriesStore.js + SettingsSubPages.test.js + m1 任务文件）。
- 主 Agent 复跑核验：`pytest tests/test_tags.py tests/test_soft_deleted_tags.py` **27 passed**；SettingsSubPages.test.js 单跑 **91/91**（提交前现况健康确认）；实地 grep：路由序 `/paged`(30)→`POST /batch-delete`(59)→`POST /clear-all`(81)→`GET /{tag_id}`(96) 红线序正确；勾选图标 `mdi-checkbox-blank-circle`/`mdi-checkbox-marked` 3 处在场、旧字面量 `mdi-checkbox-blank-circle-outline|mdi-check-circle` 标签页**零命中**（终验⑧口径）；「清空」钮 `variant="text"` 不传 color、`:disabled="total === 0"`、多选态 `v-if="!multiSelect"` 不渲染。
- 子 Agent 报告数字（主 Agent 未重复全开，终验兜底）：pytest 全量 715/715（基线 670+6 新增，含 M2 在途工作区仍全绿）、vitest 426/426（基线 421+5）、mypy 84/14 ≤ 85、ruff clean；fixed_rounds 2（vitest 侧）。
- 原子性/归属口径确认（notes + §7.2/7.3/7.5 用例在场）：一次查询无 N+1 → 命中数≠len(set(ids)) 整单 ValueError 零落删除 → 逐行置 deleted_at 一次 commit；批量两接口只认 `user_id == current_user.id`，全局行计入「不存在」整单 400；clear-all 0 条成功返回、message「标签已全部清空」幂等；不写回溯、不发事件、无条数上限。
- describe 块名：`v1.4.4 M1 标签批量治理`（文件末尾追加；提交时点 M2 尚未在该文件留块，P3 共写纪律无冲突）。
- 认可的偏离（4 条，等价实现/环境边界）：① `now(...)` 伪码 → 沿 `delete_tag` 既有 `datetime.now().strftime(...)` 手法；② `col(Tag.deleted_at).is_(None)`（与 M0 同类，mypy 零新增）；③ 任务文件记 `pages/__tests__/SettingsSubPages.test.js`，仓库实际在 `pages/`，按实际路径落笔（**文档笔误登记**）；④ 单 chip ✕ 在 v-chip 具名插槽、全 stub 环境不渲染 → §8.5 该契约改 `?raw` 源码正则承载，块头注释已标明不冒充已验证。
- manual_items：无（该链路归 P4 实测①：清空流+多选批量删流含确认弹窗文案、账单标签标记消失）。
- 既有测试零删除零放宽零改写。

### M2 分类出身徽章 + 恢复默认连定制复原（done，`87afda2`，E4 接力补全，2026-09-28）

- **接力性质**：首手 150 轮触顶截断于五步事务写作中（后端半区实质完成、0/51 勾选）；收尾 Agent 审计后**后端半区原样保留续用**、**补全前端半区**（前手零进度）+ 修一处潜在运行时缺陷。整模块一次 pathspec 提交 13 文件（models/schemas/category、category_service、routers/categories、main.py、import_service、presets.py 新、迁移脚本新、test_category_source.py 新 956 行、api/categories.js、SettingsCategoriesPage.vue、SettingsSubPages.test.js、m2 任务文件）。
- 主 Agent 复跑：pytest **716/716**（其中 test_category_source 40）、mypy **83 errors/14 files**（≤ 开工基线 85 零新增；M2 唯一新增 `:503` 已由接力修掉）、ruff All checks passed、vitest **446/446**、eslint 0e/2w。`backend/money.db` SHA256 逐字一致（临时库迁移，真实库零触碰，`git diff backend/money.db` 空）。
- 实地 grep 复核在场：`import_service.py` 三处 `source=0` 造行点 **:390/:1296/:1642**（§0.4-6，逐点注释钉死）；`delete_category` 对 `source==1` 抛 `PermissionError("预设分类不可删除")`→路由 403（D8，:389）；`@router.get("/presets")`(:38) 声明在 `/{category_id}`(:123) 之前；main.py `from app.presets import PRESET_CATEGORIES`(:16) 单行、函数级 import 指 `app.presets`（附带效应 `app.main.PRESET_CATEGORIES` 仍可解析→两个 v1.4.3 迁移测试零改动通过）。
- **终验闭环第 2 条预核通过**：序尾记双表**逐字同源**——后端 `test_category_source.py::ORDER_TAIL_CASES`(:833) 与前端 `SettingsSubPages.test.js::ORDER_TAIL_CASES`(:3653) 十四行用例名与期望整数一一对应（空0/单调0/改名1/换图标1/相邻互换1/改名+换图标1/换图标+改序1/三行轮转2/首移末1/整表逆序12/其他置首0/家族过渡2/自建混入0/改名破坏2），期望值全为具体整数、无「或」字多解。
- 五步单事务落地：分堆→CoW 副本按 name 合并回合法全局行（`is_preset==1 AND user_id IS NULL` 硬校验，否则转自建「宁删不错并」；账单改指、budget_categories 改指去重不休眠、tags 改指/NULL、删副本计 merged）→自建堆维持现状→预设复位（全局行唯一合法写点）→一次 commit 返五键；§8.1.6 mock 步骤 3 抛错钉住整体回滚零变更。§8.1.9 恢复默认后 `PRAGMA foreign_key_check` 零新增违规。
- 迁移脚本幂等实测：临时库注入旧形制 RUN1（加列+回填 14 预设/1 副本、`is_noop=False`）→ RUN2（`[SKIP]` no-op、`is_noop=True`、数据零变）；`integrity_check` 只告警；14 名独立硬编码与 presets.py 一致性断言；7 条脚本证据测试。
- 接力额外修的运行时缺陷：`_relink_budget_categories` 原 `int(row[0])` 在 SQLModel 标量返回下、恰在 UNIQUE 冲突去重分支抛 TypeError（既有用例全走「改指」分支未暴露）→ 改绑标量 + 新增 `test_restore_default_relink_dedups_already_linked_budget` 锁分支。
- 认可的偏离（4 条，口径承载不扩权，详见提交 notes）：① 黄金链路 §8.1.3 取「换图标」形态（改名/改序与 `merged_presets==1` 互斥，序尾记覆盖改序、独立用例覆盖改名入自建）；② 恢复成功 toast 因响应拦截器只回传 `res.data`（后端 message 到不了页面）→ 前端 `restoreResultMessage` 优先 `result.message`、缺失按后端逐字口径本地拼五键（同 `importResultMessage` 范式，后端拼装仍 §8.1.3 断言）；③ import_service 首处 `Category(...)` 为容 source 注释改多行（kwargs 未动）；④ `computeRestoreCounts` 置 `<script setup>` 内经 `wrapper.vm` 断言（本仓无具名导出先例）。
- manual_items（见待人工清单④ + 发布备忘）：现场库迁移窗口（备份→停服→**先于新版**执行→起新版）；REQ-003/004/005 真机观感（拖拽/改名/换图标后徽章不丢、删副本重建同名无徽章、恢复默认后定制回原状账单仍挂该分类、自建删除账单归「其他」、总数不变）；已知边界「v1.4.2 前同名删除重建历史自建行回填 `source=1`」随条目公告。
- fixed_rounds: 1（vitest 8.2.4b 口径）；后端 :503 修复在前手会话内完成。9.5（迁移窗口说明）属主 Agent 发布备忘登记项，已勾入本处发布备忘，任务文件该项按红线留人工不代勾。

### M4 关于页 + 版本单一真值源（done，`2047043`，2026-09-28）

- 提交 pathspec 11 文件 +595/−13：constants.py（新）/ main.py / routers/version.py（新）/ tests/test_version.py（新）/ m4 任务文件 / api/version.js（新）/ SettingsAboutPage.test.js（新）/ SettingsAboutPage.vue（新）/ SettingsPage.vue / SettingsSubPages.test.js / router/index.js；无 dist、无 -A/-f，主 Agent `git show --stat` 复核通过。
- 主 Agent 复跑：pytest **727/727**、mypy **83 errors/14 files**（零新增）、`ruff check app tests` All checks passed、vitest **458/458**（含 M3 在途 8 条）、eslint 0e/2w。`backend/money.db` SHA256 逐字一致。
- 版本收敛实测：`grep '"1.1.0"|"1.0.0"' backend/app backend/tests frontend/src` **零命中**；全仓版本字面量只剩 `constants.py:13 APP_VERSION="1.4.4"`（其余 v1.4.4 命中均为注释/文档性字样）；AboutPage/AppLayout 零硬编码版本，页面经 `getAppVersion()` 消费 `/api/version`。
- main.py 四个单行动作逐 diff 复核：① `from app.constants import APP_VERSION`(:13)；② `routers` import 块 +`version`(:29)；③ `version="1.1.0"`→`version=APP_VERSION`(:81)；④ root 兜底删 `"version": "1.0.0"` 键(:147 起，含去向注释)。**M2 的 `app.presets` import(:17) 与 `description="个人记账程序 API V1.1"` 均原样在场**（闭环③预核过）。
- **认可的偏离（红线 6 第三处既有断言改写，主 Agent 裁定）**：M4 触碰禁触清单文件 `SettingsSubPages.test.js`，机械同步 4 处结构计数（入口 4→5、`.entry-avatar` 7→8、摘要 v-card 5→6、字阶 title 5→6）。裁定=**接受**：设计明令新增「关于」入口卡（REQ-008/§5.4）必然使穷尽式计数断言失效；逐 hunk 复核为纯计数 +1 且新入口同列钉死（逐项穷尽、非放宽），全部带【v1.4.4 M4 计数改写】注记，零删除、零放宽、未触碰 M1/M2 describe 块。设计两可处（T2 独立测试文件）已按任务审查轮 T2 落 `SettingsAboutPage.test.js`。**登记红线 6 修订见其行内注**。另两条小偏离认可：测试路径按仓库实际（`pages/` 非 `__tests__/`，沿 M1 先例文档笔误）；`getAppVersion()` 返回解包后的版本字符串（消费方直接可用，无包装对象泄漏）。
- manual_items：§5.6 真机项不勾选、原文入待人工清单③（关于页深浅两主题截图；设置页进出返回路径通畅）。§5.5 收尾顺带项（README 版本政策一句）由主 Agent 终验承接（终验清单已含该句，M4 内未改 README 合规）。
- fixed_rounds: 0（子 Agent 报告一轮转绿）。

### M3 导入映射弹窗（done，`f60ddf3` 主 Agent 补 commit，E6，2026-09-28）

- **E6 实况**：子 Agent 六文件 `git add` 首轮成功、`git commit` 两次被权限层拦（progress.md 归主 Agent 登记的口径）；任务文件后两处行号/偏离修订未暂存——主 Agent 复核后补 add，`git diff --cached --name-only` 恰 6 文件（schemas/import_.py、import_service.py、test_csv_import_export.py、m3 任务文件、CsvMappingDialog.test.js（新）、CsvMappingDialog.vue）后代提交。`.claude/skills/ui-design.md` 在途改动未并入。
- 主 Agent 实地核验：M2 三处 `source=0` 未回退（行号漂移 +35 后现 **:390/:1331/:1677**，逐点注释在场）；`<div class="mapping-body" tabindex="0">`(CsvMappingDialog.vue:24) 在场且容器类名唯一命中；禁触清单（main.py/constants.py/version 链路/SettingsSubPages.test.js/AppLayout/tags/迁移脚本/money.db/dist）复核零改动。
- `_touched` 出网锁死证据（子 Agent notes + 全量套件复跑）：前端断言本地态 `{action:'create', name:'外卖', _touched:false}` 而出网载荷 `toEqual({action:'create'})`；未编辑态与旧版逐字节一致由既有红线（SettingsSubPages 10.5、M4-8 SQL 路径 `Object.keys` 两字段）继续绿双向锁死；`buildCategoryMappingPayload` 内 `_touched` 经 `JSON.stringify` 断言零出网。
- memo 口径实测：键=文件内原分类名（`list(memo)==["外卖"]`）、落库名=自定义名（「买菜」）、`categories` 只多一行；`_resolve_or_create_category` 本体零改动；`fallback_category` 调用点保持 5 参 → SQL 导入路径零 hunk（boot3 旧载荷逐字回归锚全绿）。
- **认可的偏离（4 条，均不违红线）**：① 名称输入用原生 `<input class="create-name-input">` 而非 `v-text-field`——`SettingsSubPages.test.js` M4-9 以 `?raw` 把模板 Vuetify 标签集合封闭为七件套，引入新组件会改红既有绿灯（零放宽红线优先）；② 实时校验走 `computed` 且新建名报错折进既有 `missingRequiredCount`，保住被逐字断言的 `:disabled="unmappedCount > 0 || missingRequiredCount > 0"` 字面量；③ 缺项清单门槛 `missingRequiredCount > 0`→`missingRequired.length > 0`（否则重名报错时渲染空清单；该字面量不在任何既有断言中）；④ `.mapping-body` 加 `overflow-x: hidden`——单轴 auto 的姊妹轴按 CSS 规范计算为 auto，17 列样例行会在中段撑出设计 §4.1 明令禁止的横向滚动条。
- 口径差上报：Prompt/E4 记 M3 勾选数 27，任务文件实数 32（31 勾 + §7.5 真机留人工），以文件为准登记（同 M0 先例）。
- manual_items：§7.5 原文入待人工清单①（1280×720 17 列全量：确认按钮不出屏、映射行全部可滚动触达；短文件无多余留白；SQL 弹窗复用不回归）。
- fixed_rounds: 1（仅测试写法两处，被测代码零改动转绿）。

## 阻塞清单

- **（已解除）M2 触顶中断 → E4 接力成功**：首手子 Agent 达 150 轮上限截断于「五步事务」写作中，0/51 勾选；后端半成品已在场。主 Agent 按 E4 派收尾接力 Agent：审计前手（后端半区完整保留续用）→ 补全前端半区（徽章/删除钮改读 source、D6 弹窗 N/M、computeRestoreCounts 纯判据、既有徽章用例改写）→ 全门禁绿 → 50/51 勾选 → pathspec 提交 `87afda2`（13 文件 +2042/−92）。核验见下「M2 执行记录」。**未触发 §五 第 3 条回滚**（接力在 3 轮预算内完成）。M3、M4 已随之并行派发（`import_service.py` / `main.py` 此时无对向写者）。
- **（已解除）M3 提交被拦 → E6 主 Agent 代提交 `f60ddf3`**（见 M3 执行记录）。
- 当前无活跃阻塞。**六模块全部 done**，进入 §6.2 终验。

## 待人工抽检清单（子 Agent 不勾选，执行时逐条抄录原文）

设计附录已点名四项（执行期各模块真机项再抄入此处）：
- [ ] ① 真机 1280×720 Cashew 17 列导入弹窗观感（REQ-006，M3 §7.5；M3 原文：确认按钮不出屏、映射行全部可滚动触达；短文件无多余留白；SQL 弹窗复用不回归）
- [ ] ② 横屏收起/展开图标列真机点验与截图（REQ-010/011，M5 §5.4；含 rail 计算宽 72px、无文字残留/无横向滚动条、悬停提示真实出现三项）
- [ ] ③ 关于页深浅主题目检（REQ-009，M4 §5.6；M4 原文：关于页深浅两主题截图；设置页进出返回路径通畅）
- [ ] ④ 现场库发布窗口：`migrate_to_v1.4.4_source.py` 先备份→停服→执行→起新版（M2 迁移，沿发布备忘流程）

M2 执行期补抄（子 Agent manual_items 原文）：
- [ ] ⑤ REQ-003/004/005 真机观感：拖动/改名/换图标后徽章不丢、刷新仍在、自建无徽章；删副本重建同名无徽章；恢复默认后定制回原状且其账单仍挂该分类、自建删除账单归「其他」、恢复前后账单总数不变（M2 逻辑判据已由 §8.1/§8.2 双表 + 五步事务测试覆盖，P4 浏览器实测②覆盖弹窗 N/M 数字与黄金链路，真机目检留人工终判）
- [ ] ⑥ M2 已知边界复核：v1.4.2 前「同名删除重建」历史自建行回填 `source=1`（显示「预设」徽章）——随版本条目公告，用户是否接受此历史数据表现
- [ ] ⑦ D8 后果复核项（随人工清单一并呈报）：预设定制无单点回退（反悔只能「恢复默认」全量丢弃）是否改变主意；执行期未加回退入口（用户裁定 a=维持）
