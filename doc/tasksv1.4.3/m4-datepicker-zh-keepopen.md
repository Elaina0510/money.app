# M4 - 日期弹窗中文化 + 实时显示已选日期 + 选后不关（需求四）

> 对应需求四（设计 §四）。注册 Vuetify zhHans locale；`DatePickerPopover` 改「选后不关、关闭时才回写」全站统一交互（账单筛选与记一笔两场景不做 prop 分叉，需求 4.4 裁定）；内置 header 隐藏改自绘实时只读展示行（D6）。
> 涉及文件：`frontend/src/main.js`（locale 注册）、`frontend/src/components/common/DatePickerPopover.vue`、`DatePickerPopover.test.js`（重写）、`RecordFormPage.test.js`（补一条）。
> 依赖：无。`RecordListPage.vue` / `RecordFormPage.vue` 调用点**零改动**（组件对外 props/emits 签名不变）。与 M14 同触 ExpandTransition 链路但本模块不改其文件。M4 先行、M14 后收编。

---

## 1. 注册 zhHans locale（设计 §4.2.1）

- [x] 1.1 `main.js`：`import { zhHans } from 'vuetify/locale'`
- [x] 1.2 `createVuetify` 增加 `locale: { locale: 'zhHans', messages: { zhHans } }`（`vite-plugin-vuetify` 确未启用，走显式 import，设计 §0.3 补充核实）
- [x] 1.3 核查结论落实：日历标题/星期/月份、「Select date」等内置文案全中文；`v-pagination`/data footer 等站内未使用组件天然受益，无需逐处处理
  - 落实口径（自动化侧）：断言注册的那份语言包内置键为中文（`datePicker.title` 选择日期 / `header` 输入日期 / `ariaLabel.previousMonth·nextMonth` / `pagination.ariaLabel.next`）+ 断言 locale 标签 `zhHans` 可被 `Intl` 接受且月份/星期名输出中文（日历表头与日期格文案走 Intl，非翻译键）。视觉「无英文残留」仍归 6.2 人工项。

## 2. DatePickerPopover 交互改造（设计 §4.2.2）

- [x] 2.1 内部状态 `picked`（ref）：`openPicker` 时 `picked = props.modelValue`；`v-date-picker` 绑 `picked`
- [x] 2.2 `@update:model-value` 仅 `toDateString(d)` 归一存 `picked`（v1.4.1 热修口径保留），**不再即时 emit、不再关闭**
- [x] 2.3 D6 落地：`:deep(.v-date-picker-header) { display: none }` 隐藏内置 header（该行为内置文本区、非可编辑输入框）；其下渲染 `<div class="selected-date-display">`：`picked ? dayjs(picked).format('YYYY年M月D日') : '请选择日期'`，随每次点选即时更新
  - 实测（Vuetify 3.12 结构）：`.v-date-picker-header` 是 VPicker header 槽里的「输入日期 / 已选日期」文本行，翻页箭头在同级的 `.v-date-picker-controls`——隐藏 header 不损失月份/年份翻页。
- [x] 2.4 底部 `<v-card-actions>` 单个「完成」按钮（tonal primary）
- [x] 2.5 统一出口 `closeAndCommit()`：`showPicker=false` 后 dialog 真正关闭时（经 ExpandTransition `update:modelValue false` 事件语义），若 `picked !== props.modelValue` 则 `emit('update:modelValue', picked)`；「完成」/遮罩点击/ESC 三路径同源（ExpandTransition 现有拦截已归一）
  - 接线：日期块由 `v-model="showPicker"` 改 `:model-value="showPicker"` + `@update:model-value="closeAndCommit"`；「完成」只 `showPicker=false`（`closePicker`），回写一律发生在收起动画播完后的那条 `false` 回声上——三路径单出口，一次关闭最多回写一次。
- [x] 2.6 时间弹层（showTime）保持现状「取消/确定」语义（本就选后不关 + 确定回写），不改
- [x] 2.7 对外 props/emits 签名不变：`RecordListPage.vue:12/:15`（filters.start/end_date 两处调用，import :170）与 `RecordFormPage.vue:116-121`（consumeDate）零改动
  - 两调用点与防抖 watch 以 `?raw` 源码锁固化在 `DatePickerPopover.test.js`（本模块不改调用方文件）。
- [x] 2.8 选后不关与 ExpandTransition 展开动画兼容（收起动画进行中重开走既有 cancel-collapse 机制，picked 重同步）

## 3. 账单页查询时机（设计 §4.2.3）

- [x] 3.1 `RecordListPage.vue:288-294` 300ms 防抖 watch 与同参去重逻辑**原样保留**（emit 只发生在关闭时，一次关闭触发一次查询）；不引入新机制
- [x] 3.2 记一笔页：回写目标为表单 `consumeDate`，dirty watch 照常捕获，行为以关闭为准

## 4. 边界自检（设计 §4.3）

- [x] 4.1 打开后未改选直接关（完成/遮罩/ESC）：`picked === modelValue`，不 emit、不触发查询
- [x] 4.2 连续改选多日：展示行实时跟新；仅最后一次点选被回写
- [x] 4.3 开始/结束两弹窗并排：各自独立实例，行为一致

## 5. 测试（设计 §4.4）

- [x] 5.1 `DatePickerPopover.test.js` 重写交互用例（实测现固化「点选日期即关」旧行为的恰为两处，改写它们并扩展：`:158-165` "should close picker after date selection"、`:296-313` 用例 6 "date picker still fills value and collapses on select"）：
  - [x] 点选日历日 → dialog 不关、不 emit、展示行显示「YYYY年M月D日」
  - [x] 再点另一日 → 展示行更新；点「完成」→ emit 最终日一次 + dialog 关
  - [x] 模拟遮罩关闭路径 → 同样回写最终值
  - [x] 未选打开 → 展示行「请选择日期」
  - 旧口径改写清单（零删除、按设计点名反转）：① `:158` "should close picker after date selection" → 选后不关；② `:296` 用例 6 "date picker still fills value and collapses on select" → 新交互全链路（origin/picked 同步 + 关闭才回写并收起）；③ `:126` "should emit update:modelValue on date selection"（同属即关机制的即时 emit 面）→ 点选仅写 `picked` 不即时 emit；④ `:138` "normalizes Date object…"（v1.4.1 热修回归）→ 归一口径保留、断言改到关闭回写时。`:147` "should emit update:modelValueTime on time confirm"（2.6 不改语义）原样保留。
- [x] 5.2 `main.js ?raw` 断言含 `zhHans` 与 `locale: {`
- [x] 5.3 `RecordFormPage.test.js` 补一条：DatePickerPopover emit 新日期 → `consumeDate` 更新 + dirty=true

## 6. 验收与质量门槛

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过；`npm run build` 记录 locale 包体增量（gzip 约 +2–3KB，终验复核）
  - 实测：vitest 265/265（基线 250，本模块 +15）；`eslint src` 0 error（仅 CsvMappingDialog.vue 既有 2 warning，非本模块文件）；`vite build` 通过。locale 包体增量（同码对照构建，唯一变量=main.js locale 段）：入口 `index.js` gzip 239,532 → 241,575 B（**+2,043 B**），全量 assets gzip 2,699,091 → 2,701,141 B（**+2,050 B ≈ +2.0KB**），raw +3,378 B，CSS 增量 0 —— 落在设计 §0.4 估算 +2–3KB 区间下沿。dist 未重建未提交（P4），对照构建输出到 node_modules 临时目录后删除。
- [ ] 6.2 手工自查：日历无任何英文残留；点选不关、下方实时显示、改选跟新；「完成」/外部关闭后列表按最终日期过滤（Network 面板单次请求）；记一笔选日期不即时收起、关闭后表单日期正确回写；明暗主题
