# Money App v1.4.3 总体进度

> 基于 v1.4.2 版本，四大主线：① 主页/账单页文案与视觉一致性；② 分类模型重构（收支共用统一标签，含迁移）；③ 预算模型重构（每月多条命名预算 + 包含/排除范围，含迁移）；④ 交互缺陷与体验修复（横滑误切页、日期弹窗中文化、图标独立浮层、展开动画统一等）。
> 需求文档：`doc/proposalv1.4.3.md`　详细设计：`doc/detailed-designv1.4.3.md`
> 任务拆解：每模块一个文件（见模块清单链接），子任务以 checklist 表示完成状态。

---

## 模块清单（14 个，与需求十四节一对一）

- [ ] [M1 - 顶栏标题「首页」统一为「主页」](m1-home-title-text.md) —— 需求一（总览 1）
- [x] [M2 - 主页大卡「总收支」三视图点按切换](m2-dashboard-total-views.md) —— 需求二（2）
- [x] [M3 - 账单页月份条放大 + 选中月滚动居中 + 选中态修复](m3-month-selector.md) —— 需求三（3、4）
- [x] [M4 - 日期弹窗中文化 + 实时显示 + 选后不关](m4-datepicker-zh-keepopen.md) —— 需求四（5）
- [ ] [M5 - 导入导出改为设置二级页面](m5-import-export-subpage.md) —— 需求五（6）
- [x] [M6 - 二级页面间距疏朗化（三页 + 全局口径）](m6-page-spacing.md) —— 需求六（7）
- [ ] [M7 - 设置页账号区用户行头像缩进对齐](m7-account-row-indent.md) —— 需求七（8）
- [x] [M8 - 分类模型重构：收支共用统一分类 ★重构+迁移](m8-category-model-unify.md) —— 需求八（9）
- [x] [M9 - 分类拖拽 flip 让位动画](m9-drag-flip-animation.md) —— 需求九（10）
- [x] [M10 - 主页/账单页行图标 primary 色系统一](m10-row-icon-primary-unify.md) —— 需求十（11、12）
- [x] [M11 - Bug 修复：竖屏左右滑动误切标签页](m11-swipe-tab-switch-fix.md) —— 需求十一（13）
- [x] [M12 - 预算模型重构：每月多条命名预算 ★重构+迁移](m12-budget-model-rebuild.md) —— 需求十二（14）
- [ ] [M13 - 分类图标选择改独立居中弹窗](m13-icon-picker-dialog.md) —— 需求十三（15）
- [ ] [M14 - 全站展开画面统一「从触发点展开」动画（收编型）](m14-expand-animation-unify.md) —— 需求十四（16）

## 开发顺序（设计附录 B 依赖链）

```
批 1（零依赖，可并行）：M1 M2 M3 M4 M5 M7 M10 M11；M6 其余三页（标签/模板/回溯）同批并行
批 2：M8（后端 + 迁移阶段 A + 前端）→ M9、M6 分类页区域验证（已并入 M8 落样式）、M13 紧随
批 3：M12（依赖 M8 接口与迁移脚本两阶段联调）
批 4：M14（收编全站对话框，最后做、逐处替换逐处回归）
```

模块间依赖三处（设计 §0.1）：**M9 ← M8**（flip 作用于单列表）、**M12 ← M8**（单套分类多选 + 同脚本两阶段「分类在前、预算在后」）、**M14 收编型**（只换动画来源不改功能）。M6 与 M8 分工：分类页疏朗化由 M8 一次落地，M6 只负责其余三页 + 全局规则。

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `SettingsCategoriesPage.vue` | M6、M8、M9、M14 | 串行：M8（重写列表+删类型下拉+落 M6 口径样式）→ M9（追加 `:animation`）→ M14（两 dialog → AppDialog） |
| `RecordListPage.vue` | M3、M10、M11 | M3 先建 `.month-scroller` 类；M11 在该类追加 overscroll 属性；M10 只改行图标区 |
| `DashboardPage.vue` | M2、M10 | 区域无交叉（大卡 :4-42 vs 最近账单 :124-147），可并行 |
| `SettingsPage.vue` | M5、M7、M8 | 区域无交叉可并行；M5 动 template 大段，合并以 M5 为主 |
| `StatisticsPage.vue` | M12、M14 | M12 先行重写预算区；M14 只换对话框外壳组件 |
| `main.js` | M4、M14 | M4 加 locale、M14 加 `defaults.VMenu`，不同段落可并行 |
| `global.scss` | M6、M10、M11、M14 | M6 `.page-card` padding、M11 根级 overscroll、M14 `:root` 变量与 slide-y 覆写；M10 复用 `.entry-avatar` 零改动；均不同段落可并行 |
| `backend/.../category_*` + `main.py` | M8 | 单模块独占（budget 侧 M12 独占） |
| `migrate_to_v1.4.3.py` | M8（阶段 A）、M12（阶段 B） | 同一脚本两阶段、单事务；M8 建骨架留挂点，M12 续写，整体在 M8+M12 联调时落定 |
| `DatePickerPopover.vue` / `ExpandTransition.vue` | M4 / M14 | M4 先行改交互内核；M14 不动 DatePickerPopover（机制换壳在 ExpandTransition 内） |
| `SettingsSubPages.test.js` | M5、M6、M8、M9、M13、M14 | 各模块只动各自用例块，按模块串行提交 |

## 已确认设计决策（实现约束，设计 §0.3）

| # | 决策 | 落点 |
|---|------|------|
| D1 | 迁移载体 = 独立幂等脚本 `backend/migrate_to_v1.4.3.py`（项目从未引入 Alembic），单脚本两阶段全程单事务；表级 UNIQUE 换形一律整表重建，幂等判据读 `sqlite_master` 建表文本 | M8/M12 |
| D2 | `categories.type` 保留列、废弃语义；新行恒写占位 `'expense'`；唯一约束改 `(name, user_id)` | M8 |
| D3 | 预算新表 `budgets(name/month/amount/scope_mode)` + `budget_categories` 关联表 | M12 |
| D4 | 年视图逐月「已用」= 各预算 spent 直加（重叠可大于当月实际支出，属预期） | M12 |
| D5 | 主页大卡初始视图=支出，循环 expense→balance→income；结余负数色 `#FFC7C7` | M2 |
| D6 | Enter date 行 = `:deep(.v-date-picker-header){display:none}` 隐藏 + 自绘只读展示行（dayjs「YYYY年M月D日」/「请选择日期」） | M4 |
| D7 | 展开动画 = `useExpandAnimation` composable + `AppDialog` 壳 + `ConfirmDialog` 内部换壳；原点来源 appStore.lastClickOrigin（pointerdown 捕获），无坐标退化中心 | M14 |
| D8 | 列表行图标直接复用 `.entry-avatar`，不新增类不分叉 | M10 |
| D9 | 手动模板 type 改取该标签最近一笔流水的交易 type，无流水兜底 `'expense'` | M8 |
| D10 | 量化口径：`.page-card` 20px；行 min-height 48 + margin-block 4；section-title 8/12、块间 20；`--expand-duration: 220ms` + 统一缓动；拖拽 flip `animation: 180` 独立口径 | M6/M14/M9 |
| D11 | 分类合并细则：判据「同名即其他类」、CoW 仅按 name、预设换 14 条单套、「其他」固定 `mdi-cash-minus` 精选集内 | M8 |
| D12 | 预算旧接口：GET 去 type；POST 改纯创建；删 `POST /batch`；PUT 全字段、month 不可改；均站内自用无兼容负担 | M12 |

## 进度统计

| 模块 | 层 | 状态 | 完成 commit | 备注 |
|------|----|------|-------------|------|
| M1 | 前端 | ⬜ 待开始 | | |
| M2 | 前端 | ✅ 已完成 | `d7cd977` | D5 循环/负结余 #FFC7C7 落定；220ms 字面量带 M14 回填标记；DashboardPage.test.js 新建 |
| M3 | 前端 | ✅ 已完成 | `036b286` | `.month-scroller` 类已建（M11 挂载点就绪）；vitest 200 全绿 |
| M4 | 前端 | ✅ 已完成 | `ecf5152` | 选后不关+closeAndCommit 单出口；locale gzip 实测 +2,050B（估算下沿，见备注） |
| M5 | 前端 | ⬜ 待开始 | | |
| M6 | 前端 | ✅ 已完成 | `ca9a482` | 全局 `.page-card`/`.section-title` 定义已落（P2 窗口闭合）；分类页 scoped margin 静默覆写已修 |
| M7 | 前端 | ⬜ 待开始 | | |
| M8 | 全栈 | ✅ 已完成 | `8652bec` | ★迁移阶段 A + 脚本骨架/挂点就绪（单事务、sqlite_master 判据、整表重建）；pytest 212 全绿；money.db 未触碰 |
| M9 | 前端 | ✅ 已完成 | `e00285a` | 仅 :animation="180" 一行改动；vuedraggable animation 落 $attrs 口径偏离见备注 |
| M10 | 前端 | ✅ 已完成 | `5ec01d4`（dashboard 半区在 `d7cd977`） | D8 纯复用 .entry-avatar 零新增类；详情页未动（红线1） |
| M11 | 前端 | ✅ 已完成 | `d03ce93` | 按 P3 浏览器自动化复现尝试（结论见备注）；纯 CSS overscroll 隔离；vitest 206 全绿 |
| M12 | 全栈 | ✅ 已完成 | `7912906` | ★迁移阶段 B 同事务续写 + merge_map 接力；D12 四端点、batch→PUT 重接；spent user_id 隔离；顺带修复导出丢关联 bug；pytest 245/vitest 247 |
| M13 | 前端 | ⬜ 待开始 | | |
| M14 | 前端 | ⬜ 待开始 | | 收编型，最后做 |

## 测试结果记录

| 时点 | pytest | vitest | mypy | ruff | lint | build |
|------|--------|--------|------|------|------|-------|
| M3 `036b286` | 无涉及 | 38（单文件）/200 全量 | — | — | 通过 | skip |
| M11 `d03ce93` | 无涉及 | 43（单文件）/206 全量 | — | — | 通过 | skip |
| M8 `8652bec` | 212/212 | 232/232 全量 | 基线零新增（107→106） | 通过 | 通过 | skip |
| M6 `ca9a482` | 212/212 回归 | 237/237 全量 | — | — | 通过 | skip |
| M2 `d7cd977` | 无涉及 | 237/237 全量 | — | — | 通过 | skip |
| M10 `5ec01d4` | 无涉及 | 237/237 全量 | — | — | 通过 | skip |
| M12 后端 | 245/245 | — | 零新增（90 vs 基线106） | 通过 | — | skip |
| M12 `7912906` | 245/245 复核 | 247/247 复核 | 同上 | 通过 | 通过 | skip |
| M9 `e00285a` | 无涉及 | 250/250 全量 | — | — | 通过 | skip |
| M4 `ecf5152` | 无涉及 | 265/265 全量 | — | — | 通过 | 通过（对照法） |

## 待人工抽检清单（各模块任务文件「验收与质量门槛」手工项汇总）

### M1
- [ ] 3.2 顶栏 / bottom nav / 桌面侧栏三处同显「主页」

### M2
- [ ] 6.2 真机竖屏一次点击即切换无连环跳；primary 深底红/白对比度；明暗 × 竖/宽四组合

### M3
- [ ] 7.2 进页当前月水平居中且高亮；点两端月份/翻年回中；往年选中月高亮；视觉明显放大疏朗；明暗主题

### M4
- [ ] 6.2 手工自查：日历无任何英文残留；点选不关、下方实时显示、改选跟新；「完成」/外部关闭后列表按最终日期过滤（Network 面板单次请求）；记一笔选日期不即时收起、关闭后表单日期正确回写；明暗主题

### M5
- [ ] 6.2 二级页四功能全可用（导出真实下载、导入走映射/确认）；设置主页无内联四行；明暗 × 竖/宽

### M6
- [ ] 5.2 三页（+M8 后分类页）不再拥挤、节奏一致；末行不被遮挡；深色同查

### M7
- [ ] 4.2 用户行头像与标题行图标 44px 同列缩进；明暗 × 竖/宽四格

### M8
- [ ] 11.3 真实 v1.4.2 备份库跑脚本 → 全页面巡检；记账选任意分类；迁移前后月度合计不变
- [ ] 11.4 明暗 × 竖/宽自查

### M9
- [ ] 4.2 **真机必测**：竖屏触摸拖动分类，其余行随拖动位置实时平滑让位、全程无跳变；松手落位顺序保持、刷新不丢
- [ ] 4.3 桌面鼠标路径同测；明暗主题走查

### M10
- [ ] 5.2 主页行首分类图标无箭头；账单页与设置页入口同款；金额红绿；明暗 × 竖/宽

### M11
- [ ] 1.3 复现结论登记（触发区域/起点/到边情况）
- [ ] 2.4 保持 `.content-overflow{overflow-x:hidden}` 现状复验：任意页面主体 `scrollX` 恒 0、无横向可滚溢出
- [ ] 3.2 iOS Safari：`overscroll-behavior-x` 对 iOS 手势无效但 iOS 本无历史横滑导航（系统侧滑返回已排除，不在缺陷域）
- [ ] 3.3 桌面 Chrome 触控板双指横滑：同被 contain 阻断导航，页面行为不变
- [ ] 5.2 真机三区横滑不切页、`scrollX` 恒 0
- [ ] 5.3 月份条横滑/点选居中正常；底栏切换正常

### M12
- [ ] 13.2 手工验收场景复算：同月「日常开销 3000 包含 餐饮/交通/日用」+「学习 500 包含 教育」两卡独立进度正确；「除工资外全支出 4000」排除模式已用 = 当月支出 − 工资类支出
- [ ] 13.3 升级回归：旧数据迁移后原分类预算以单分类命名预算完整保留（金额月份一致）；年视图合计 = 当月各预算金额之和
- [ ] 13.4 明暗主题、竖/宽屏自查；`frontend/dist` 不随本模块提交

### M13
- [ ] 5.2 竖屏居中弹窗不超视口、网格占满可滚全部；宽屏外层对话框不膨胀；回焦与 z 层级；明暗主题

### M14
- [ ] 10.2 六类触发点原点展开/反向收起，全站无瞬现
- [ ] 10.3 连点无卡帧；reduced-motion 生效
- [ ] 10.4 回归 M3 居中与 M11 手势；明暗 × 竖/宽

## 阻塞清单

（暂无）

> 执行备注：泳道编排 Agent 两度触 150 轮上限（M8/M2 期间），主 Agent 改为直接逐模块派实现/收尾 Agent，链路顺序与互斥口径不变；M2 任务文件因入库时序由 9237b59 代提交，内容一致。

## 备注

（各模块完成报告 notes 汇总于此：设计偏差裁定、测试口径反转、交接事项、遗留项。）

- **M4 完成（`ecf5152`）**：① 包体记录——locale 增量以同树单变量对照法实测（build 重定向 outDir，dist 零写入）：全量 gzip **+2,050B**、入口 index.js gzip +2,043B、CSS +0，落于设计 §0.4 估算 +2–3KB 下沿，终验复核；② **M14 收编注意（实测时序）**：真实 ExpandTransition 对关闭回声天然去重（collapseTimer 守卫），回写骑在收起后回声中→「完成后 ≈250ms 内重开」丢弃未关闭点选（§4.3 重开重同步口径，已有边界用例锁定）；查询/回写发生于关闭后 ≈550ms 仍单次请求；`picked` null 以空串兜底；③ 旧「即关」口径反转改写 4 处（:158/:296 点名两处 + :126/:138 机制面），零删除零放宽，中途误删的 :147 时间用例已同提交恢复；④ D6 核实：`.v-date-picker-header` 仅文本行，翻页箭头在 `.v-date-picker-controls` 同级，隐藏不损失导航。

- **M9 完成（`e00285a`）口径偏离（已接受）**：设计 §9.4 字面断言 `props('animation') === 180` 实测不可达——vuedraggable@4.1.0 声明面无 animation，该 prop 落 `$attrs` 透传 Sortable；用例改按本文件既定 `sortableOptionsOf()` 归一口径断 `$attrs.animation===180` + `props()` 不含 animation 键快照，未降断言。M14 收编本页对话框不受影响。

- **M12 完成报告要点（`7912906`，主 Agent 已复核 pytest 245/245 + vitest 247/247 复跑）**：① 口径反转改写除任务点名的 test_budgets/test_data_isolation/StatisticsPage 预算块外，还包括 `test_security.py` 两条预算 IDOR（403 意图保留并加强「无痕迹」核验）与 `test_migration_v143.py` ⑦/⑥ 重指向两阶段真态（阶段 A 单元不变量拆新用例，零删除）；② **越文件改锁（已裁定接受）**：`SettingsSubPages.test.js` 用例M8-3 锁定了 M12 按设计删除的「每分类一条预算行」标记，就地改锁预算卡色档函数（意图不变），设计附录 C 未预见该交叉；③ **顺带修复真实 bug**：导出 `budget_categories` 缺 `category_name` 致导入后预算关联全丢，导出双写名称+导入三级解析，3 新用例锁；修复了 `/api/export/sql` 对持有预算用户必崩的既有缺陷；④ 遗留登记：`BudgetPage.vue`（死文件红线）仍 import 已下线的 `batchSetBudgets`（悬空、不入包）；slide-y 覆写因 Vuetify `!important` 时长用双类提级，M14 收编统一；⑤ **既有缺陷不修登记（越权判定）**：`restore_default_categories` 对持有账单记录的自定义分类置空 `records.category_id` 违反 NOT NULL（基线 8652bec 即存在，v1.2.3 遗留）→ 该场景 500；M12 用例 4.4 绕开该形制并在测试内注释，建议下版单独立项修复。

- **M11 1.3 复现尝试结论登记（按裁定 P3，2026-09-20）**：子 Agent 以浏览器自动化（dev server 起服 + Chromium 375px DevTools 移动模拟）在账单列表区/月份条（含滑至左右两端继续滑）/页面空白区尝试复现左右横滑切页，**未能复现**历史导航触发；按 §11.2 overscroll 根因假设实施纯 CSS 修复（html,body + `.month-scroller` contain），提交 `d03ce93`，**未经真机复现**，真机验收 5.2/5.3 保留人工清单。全站横滚容器审计实测：可横滚容器仅月份条一处（AppLayout `overflow-x:hidden` 属裁剪非可滚容器，保持现状）。

- **任务文件审查记录（2026-09-20，对照双文档 + 实测代码）**：① M4 2.7 调用点行号修正（RecordListPage 日期弹窗实为 :12/:15）；② **M12 3.1 裁定性偏离登记（2026-09-20 用户已认可）**——旧 `_enrich_budget`（budget_service :87-92）spent 查询缺 `user_id` 隔离属既有缺陷，新聚合函数补隔离并落 `test_data_isolation.py` 用例；③ **M14 全站锁豁免 `BudgetPage.vue:92`**（死文件含 v-dialog，不豁免则 §9.4 断言必红）；④ M8 9.3a conftest:34-42 过期预设副本陷阱登记；⑤ M4 5.1 点名旧行为锁死用例两处、M12 7.1 登记「编辑现走 batchSetBudgets、updateBudget 未 import」重接事项、M12 涉及文件行号拆分精化；⑥ 输入文档侧行号瑕疵仅登记不改设计文档：需求 §14「ExpandTransition :107-145 用 event.clientX」实为 DatePickerPopover 传坐标 + ExpandTransition apply/collapse 函数体、设计 §8.1 表「category_service :120-131 CoW 副本分支」实为 :166-194、`export INSERT` 实为 :104-109、`schemas sort_order` 实为 :26/:35。其余 60+ 处引用实测一致。

- 迁移与发布备忘（附录 A，M8+M12 合并交付）：① 脚本单文件两阶段单事务一次执行，发布步骤 = 停服→备份 money.db→跑脚本核对 `[OK]/[SKIP]`→部署新前后端→抽检升级回归（§8.4/§12.4 人工清单）；② 回滚 = 恢复备份 db + 回滚应用版本（无 downgrade 代码路径）；③ `frontend/dist` 终验统一重建，包体记录 zhHans locale 增量与总体 gzip 对比；④ 开发库旧形制不齐登记（budgets 无 user_id 唯一形、quick_templates 无 kind 列）——不假设库必处于 v1.4.2 后标准态，升级抽检以 `sqlite_master` 输出核对现场形制。

## 质量门槛（沿既定口径）

- 后端：`pytest` 相关 + 全量回归；`mypy` **基线零新增**；`ruff check` 通过
- 前端：`npm test`（vitest run）、`npm run lint`；终验 `npm run build` 复核包体（locale 增量）
- `frontend/dist` 不随模块提交，终验统一重建（既定裁定）
- 明暗两主题 × 竖屏 375px / 宽屏 1280px 逐模块手工自查（UI 改动遵循 `doc/rules/uidesign.md`）
- 既有测试口径反转四处，**与模块代码同提交**：分类 type 过滤/双列表用例（M8）、点选日期即关用例（M4）、导入导出内联卡用例（M5）、每分类一条预算用例（M12）
- 两大大型重构（M8/M12）须配套迁移脚本自测（`test_migration_v143.py` 幂等/回滚/合计不差）与升级回归用例

## 范围外红线（本期不做）

- 记录详情页行图标/配色不改（需求 10.4 裁定）
- `BudgetPage.vue` 死文件（无路由引用）保留不动，不参与 M12 适配
- 统计页分类排行图等其他图标不动（非列表行图标，超出需求范围）
- 月份选择器不改为连续时间轴（保持年份箭头 + 12 月 chip 结构，需求 3.1）
- 不引入 Alembic（D1 独立脚本）；不为分类 type 列提供 downgrade 代码路径
- iOS 系统侧滑返回不在 M11 缺陷域（用户已排除）
- `DatePickerPopover` 不为账单/记账两场景做 prop 分叉（需求 4.4 全站统一裁定）
