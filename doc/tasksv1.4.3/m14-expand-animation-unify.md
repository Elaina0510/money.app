# M14 - 全站展开画面统一「从触发点展开」动画（需求十四）· 收编型

> 对应需求十四（设计 §十四）。以 `ExpandTransition` 现有逻辑抽出通用 composable + `AppDialog` 统一对话框壳，全站展开类画面统一"从触发点（点击原点）展开、反向收起"动画，时长 220ms/缓动统一（D10）；无触发点退化中心/底部，不得瞬现。**实现顺序放最后，逐处替换、逐处回归**（设计 §0.1 模块独立性第 3 条）。
> 涉及文件：新增 `frontend/src/composables/useExpandAnimation.js`（`composables/` 目录本版新建）、新增 `frontend/src/components/common/AppDialog.vue`；重构 `ExpandTransition.vue`、`ConfirmDialog.vue`；修改 `AppLayout.vue`、`appStore`、`main.js`（`defaults.VMenu`，与 M4 locale 不同段落）、`global.scss`（`:root` 变量 + slide-y 时长覆写）、各对话框宿主页面。
> 依赖：排在 M2/M4/M12/M13（及 M5/M8）之后统一收编；对它们只做**动画来源替换**，不反向改功能。

---

## 1. 全局时长口径（D10，`global.scss`）

- [x] 1.1 `:root { --expand-duration: 220ms; --expand-easing: cubic-bezier(0.25, 0.8, 0.5, 1); }`（需求 200–250ms 取中）
- [x] 1.2 `@media (prefers-reduced-motion: reduce)` 下 `--expand-duration: 1ms`（可访问性口径，一处生效全站）
- [x] 1.3 JS 侧同步常量 `EXPAND_DURATION = 220`（composable 默认值），与 CSS 变量**注释互指防漂移**
- [x] 1.4 全站展开类动画一律引用变量/常量，禁止逐处硬编码时长（含 M2 大数字切换、M12 预算卡展开）

## 2. `useExpandAnimation.js`（新增，单一实现源，设计 §14.2.1）

- [x] 2.1 迁移 `ExpandTransition.vue` 的 `calcOrigin/applyExpand/applyCollapse/collapseTimer` 全逻辑；参数 `(contentRef, { origin, duration, easing })`
- [x] 2.2 **新增退化规则修正**：origin 未设或为默认 `{x:0,y:0}` → `'center center'`（现实现以视口坐标减 rect 求百分比，(0,0) 会算出负百分比、落点在元素外左上方——修正为需求 14.2「无触发点退化中心」）

## 3. `ExpandTransition.vue` 重构（外部行为不变）

- [x] 3.1 内部换用 composable；继续服务 `DatePickerPopover`（其 activator 本就传真实 click 坐标）
- [x] 3.2 **红线**：`ExpandTransition.test.js` 既有用例全量保持通过（重构行为不变的红线测试）

## 4. 点击原点来源（D7）

- [x] 4.1 `appStore` 新增 `lastClickOrigin` 状态
- [x] 4.2 `AppLayout.vue onMounted`：`document.addEventListener('pointerdown', e => lastClickOrigin = {x:e.clientX, y:e.clientY}, { capture: true, passive: true })`——所有对话框（含路由级/程序化）打开天然取到最近点击位置；键盘触发无 pointer 事件时维持上一次/中心，均可接受

## 5. `AppDialog.vue`（新增，全站对话框统一壳）

- [x] 5.1 结构：`v-dialog(:transition="null") > Transition(appear, :css="false", JS hooks = useExpandAnimation) > 内容 slot 容器`；props `modelValue`/`origin?`，`maxWidth` 等 v-dialog 属性经 `$attrs` 透传
- [x] 5.2 `origin = props.origin ?? appStore.lastClickOrigin`
- [x] 5.3 关闭（完成/取消/遮罩/ESC）= 反向收缩：collapse 播完再真正关 v-dialog（ExpandTransition 同套拦截逻辑复用）；重开取消收起（collapse-cancel）机制同套
- [x] 5.4 程序化打开（如导入成功自动弹映射框）：lastClickOrigin = 触发那一次点击，语义成立

## 6. 收编清单（v-dialog → AppDialog 逐处替换，功能零改动，设计 §14.2.2）

- [x] 6.1 `ConfirmDialog.vue` **内部换壳**——一次惠及全站确认弹窗（批量删除、分类删除、模板删除、回溯确认、预算删除、恢复默认等）
- [x] 6.2 `SettingsCategoriesPage.vue`：M8 改造后的新增/编辑分类、恢复默认两处 dialog
- [x] 6.3 `SettingsTagsPage.vue`：标签新增/编辑（现为 dialog-bottom-transition）
- [x] 6.4 `SettingsQuickTemplatesPage.vue`：快速记账新增模板
- [x] 6.5 `CsvMappingDialog.vue` + `SettingsImportExportPage.vue`：CSV 映射 / SQL 确认 / SQL 映射
- [x] 6.6 `StatisticsPage.vue`：M12 预算新增/编辑对话框（M12 先行，M14 只换外壳组件）
- [x] 6.7 `CategoryIconPicker.vue`：替换 13.2 初版过渡为 AppDialog 原点展开
- [x] 6.8 全库 `grep -n "<v-dialog"` 收口：以 grep 清单为准逐个收编；实测现存 **11 处 / 10 文件**（CategoryIconPicker:40、ConfirmDialog:2、CsvMappingDialog:2、ExpandTransition:2、SettingsCategoriesPage:146/:189、SettingsPage:190、SettingsQuickTemplatesPage:61、SettingsTagsPage:52、StatisticsPage:301、**BudgetPage:92**）。**审查修订：`BudgetPage.vue` 为无路由引用死文件（范围外红线保留不动），收编清单显式豁免该文件**；替换后全站 `dialog-bottom-transition` 字面量**零命中**（实测现存 3 处：CategoryIconPicker:43、SettingsCategoriesPage:146、SettingsTagsPage:52，分别随 M13/M8 改造与本期收编消除）

## 7. 非 dialog 展开类（设计 §14.2.3）

- [x] 7.1 `main.js` `defaults: { VMenu: { transition: 'fab-transition' } }`（v-select/v-autocomplete 下拉）；实现时验证 VSelect 菜单是否继承该 defaults，不继承则调用点显式传 `menu-transition="fab-transition"`（站点使用量小可枚举）
- [x] 7.2 批量操作条（`RecordListPage.vue:65-78`）：包 `<Transition name="batch-bar">`，enter/leave 对称（translateY ±10px + opacity，`--expand-duration`），替换现"仅 enter 有动画、leave 瞬删"的 slideDown；不接原点（贴列表顶部，位移方向即触发语境）
- [x] 7.3 `global.scss` 一处覆写：`.v-slide-y-enter-active, .v-slide-y-leave-active { transition-duration: var(--expand-duration) }`（预算卡展开明细/图标面板收起等区内展开统一，不逐组件配置）
- [x] 7.4 **M2 回填**：大数字切换动画字面量 220ms 替换为 `var(--expand-duration)`/`var(--expand-easing)`（§2.2.3 预留动作）

## 8. 兼容红线（设计 §14.2.4）

- [x] 8.1 不破坏 M11：动画只作用于 overlay 内容节点，不触达页面主体/滚动容器；AppDialog transform 不新建横向滚动上下文（在 `.v-dialog__content` 内层容器，overflow 裁剪层不变）
- [x] 8.2 不破坏 M3 滚动居中：dialog 动画不劫持 focus/scroll；M13 回焦与 `after:leave` 时序不变
- [x] 8.3 快速连续点击：沿用 collapse-cancel（重开取消收起）机制于 ExpandTransition 与 AppDialog；验收含"无动画错位/卡帧"

## 9. 测试（设计 §14.4）

- [x] 9.1 新增 `useExpandAnimation.test.js`：origin 缺省/{0,0} → 'center center'；坐标映射百分比数学；collapse 计时与 cancel
- [x] 9.2 新增 `AppDialog.test.js`：open 应用 enter 内联样式（transformOrigin 非空）；`modelValue→false` 后 dialog 延时关闭（timer mock）；动画中重开不报错
- [x] 9.3 `ExpandTransition.test.js` 既有用例全量保持
- [x] 9.4 `?raw` 全站锁三条：`<v-dialog` 仅存在于 AppDialog/ExpandTransition 两文件（grep 计数断言；**统计范围排除死文件 `BudgetPage.vue`——实测其 :92 含 v-dialog，不豁免则锁必误报，见 §6.8**）；`dialog-bottom-transition` 全站零命中；`main.js` 含 `VMenu` defaults
- [x] 9.5 `RecordListPage.test.js`：批量条出现/消失均经 Transition（快照类名变化）

## 10. 验收与质量门槛

- [x] 10.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 10.2 手工任选 6 类触发点逐点验（分类新增、确认删除、日期弹窗、图标浮层、CSV 映射、预算新增）：自点击处平滑展开、收起有反向动画；全站无"瞬时蹦出"画面
- [ ] 10.3 连点无动画错位/卡帧；`prefers-reduced-motion` 系统开关下近似瞬开
- [ ] 10.4 回归：M3 选中月居中、M11 横滑手势不复发；明暗主题、竖/宽屏

---

## 11. 实现备忘（子 Agent 落盘，与 progress.md 备注同权威）

- **收编实况（以实时 grep 为准，非设计计数）**：开工实测 `<v-dialog` 11 处 / 10 文件，与任务 6.8 清单一致，但行号已漂移且 `SettingsPage:190` 早由 M5 迁出（0 处）。收编 9 处 / 8 文件（ConfirmDialog 1、CategoryIconPicker 1、CsvMappingDialog 1、SettingsCategoriesPage 2、SettingsImportExportPage 1、SettingsQuickTemplatesPage 1、SettingsTagsPage 1、StatisticsPage 1）；收编后直持者仅剩 AppDialog / ExpandTransition 两合法壳 + `BudgetPage.vue`（审查记录③豁免，死文件原样未动）。`dialog-bottom-transition` 全站零命中（含注释字面量）。
- **7.1 实测偏离（已按设计预留分支处置）**：Vuetify 3.12 的 `VSelect` 把自己的 `transition`（默认 `VDialogTransition` 对象）直传 `VMenu`，`defaults.VMenu` 对 v-select **不继承** → 按任务 7.1 明示的兜底分支在 5 个调用点（CsvMappingDialog×2、RecordFormPage 的 v-autocomplete、SettingsQuickTemplatesPage、SettingsTagsPage、StatisticsPage 预算多选）显式传 `transition="fab-transition"`；`defaults.VMenu` 同时保留（真 v-menu 路径生效）。
- **7.3 收编 M12 遗留**：slide-y 时长覆写以「重复类名提级 + !important」上收 `global.scss` 一处（含 `slide-y` / `slide-y-reverse` / `v-slide-y` 三族），StatisticsPage 页内双类覆写删除；M2 大数字切换（DashboardPage）与 M12 明细展开的字面量均回填 `var(--expand-duration)/var(--expand-easing)`，对应 `?raw` 用例（DashboardPage 用例9、StatisticsPage 用例6）同步改锁变量口径（意图不放宽：仍锁引用存在 + 硬编码零残留）。
- **红线 8 保持**：`ExpandTransition.vue` 对外 props/emits/行为不变、既有用例 15 条全量通过（仅内部改调 composable）。**唯一冻结项**：其 `duration` 默认值仍为 250（被既有 `should have duration prop with default` 锁定，属对外 API）→ 220ms 统一口径由 `--expand-duration`/`EXPAND_DURATION` 承载，`AppDialog` 走该默认；DatePickerPopover 因此仍为 250ms（本体按 M4 口径不动）。
- **origin 退化修正**：`{0,0}` / 非坐标 / 无 rect 一律 `center center`（旧实现 (0,0) 会算出负百分比落点在元素外）；坐标映射与「未设原点」两条均落 `useExpandAnimation.test.js` 用例M14-1/2。
- **既有 M13/M4 交接事项处置**：`CategoryIconPicker` 换壳后 `<v-dialog` 计数锁（用例M13-4）改口径为「0 处 + 恰 1 处 `<AppDialog`」；`after:leave` 经 AppDialog 显式 `emits` 透传回宿主（回焦链时序不变，用例3.3 仍绿）；`flex + 80vh` 滚动结构未触碰并新增源码锁。关闭改「反向收缩播完才卸载」，故 M13/M4 侧「关闭后画面消失」断言改为等收起播完（`settleCollapse`，不放宽）。
- **9.4 全站锁实现手法**：因 jsdom 不处理 CSS，`?raw` 取 `.scss` 返回空串（M11 已登记），锁用例改用 `node:fs` 直读源码目录做「grep 同等口径」计数断言（新增宿主漏收编即红），并断言 pointerdown 捕获、VMenu defaults、无硬编码时长残留。
- **9.5 运行时可观测性**：jsdom 下 Transition 进出类在断言窗口内不可稳定观测（`getTransitionInfo` 零时长即回调），故批量条用例改按「Transition 组件托管 + name 口径 + DOM 进出结果」断言，对称样式与时序口径由 `?raw` 源码锁承载。
- **测试数字**：vitest 326/326（基线 290 + 新增 36）、lint 0 error（2 既有 warning 非本期引入）、build 通过、pytest 245/245 复核（后端零改动）。
- **手工项 10.2 / 10.3 / 10.4 未执行、未勾选**，原文已在 progress.md「待人工抽检清单 · M14」段（本模块完成报告另抄录）。
