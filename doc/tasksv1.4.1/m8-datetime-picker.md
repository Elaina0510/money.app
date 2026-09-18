# M8 - 快速记账日期/时间布局与时间弹层动画

> 对应需求九：日期/时间拆两行；时间弹层改为点击位置圆形展开的表盘时钟（含取消/确定），收起同为圆形。
> 涉及文件：`frontend/src/components/common/DatePickerPopover.vue`、`frontend/src/components/common/ExpandTransition.vue`、`frontend/src/pages/RecordFormPage.vue`
> 依赖：无。回归约束：账单页筛选复用 DatePickerPopover（不启用 `show-time`），必须逐像素不变（易错点 9）。

---

## 1. DatePickerPopover.vue：两行结构改造

### 1.1 模板（现 :4-30 activator 同行布局拆除）

- [x] 根容器改 `.date-time-fields`，内含两个平级 `ExpandTransition` 实例：
  - [x] 第一行：日期 ExpandTransition（占满行宽）——activator 保留默认 slot 与自定义 slot 兼容，`v-text-field` 加 `class="w-100"`，内嵌 `v-date-picker` 行为不变（选日即回填并收起）
  - [x] 第二行：`v-if="showTime"` 的时间 ExpandTransition（`:max-width="360"`）——activator 为 `v-text-field :model-value="selectedTime" readonly label="时间" prepend-inner-icon="mdi-clock-outline" class="w-100"`
- [x] 时间弹层内容卡（`.time-picker-card`）：标题"选择时间" + `<v-time-picker v-model="pendingTime" color="primary" format="24hr" width="280" />`（24 小时制表盘时钟）+ 「取消 / 确定」按钮
- [x] 删除独立时间 `v-dialog`（:47-66）

### 1.2 脚本

- [x] 新增 `const timeOrigin = ref({ x: 0, y: 0 })`
- [x] `openTimePicker(event)`：`timeOrigin.value = { x: event.clientX, y: event.clientY }`（圆形展开原点）、`pendingTime.value = selectedTime.value || '12:00'`、`showTimePicker.value = true`
- [x] `cancelTime()`：仅关闭弹层，不回写 `selectedTime`
- [x] `confirmTime()`：`selectedTime.value = pendingTime.value`、`emit('update:modelValueTime', pendingTime.value)`、关闭
- [x] 两实例平级后，`openTimePicker` 不再需要 `.stop`

### 1.3 样式

- [x] 删除 `.time-field { max-width: 140px }`（:140-142）
- [x] 新增 `.date-time-fields { display: flex; flex-direction: column; gap: 8px; }`（宽屏与竖屏同一套两行布局）
- [x] 确认 `showTime=false` 时仅渲染单行日期字段（账单页筛选路径）

## 2. ExpandTransition.vue：补圆形收起动画

- [x] `watch(() => props.modelValue)`：`val` 为 true → `show = true`；为 false 且 `show.value` → `applyCollapseAnimation()`（播完再真正关闭 dialog）
- [x] 实现 `applyCollapseAnimation()`：
  - [x] `contentRef` 不存在 → 直接 `show = false`
  - [x] `el.style.transformOrigin = calcOrigin(props.origin.x, props.origin.y)`（收回同一原点）
  - [x] `transition: transform {duration}ms ease, opacity {duration}ms ease`；`transform: scale(0)`；`opacity: 0`
  - [x] `setTimeout(() => { show.value = false }, props.duration)`（fake timers 可测）
- [x] **易错点 10 双关闭路径**：拦截 `v-dialog` 的 `@update:model-value`（用户侧遮罩/ESC 关闭），先播收起动画再置 `show=false`；programmatic（确定/取消/选日）与 interactive 两条路径均验证圆形收起
- [x] `duration` 复用 250ms 与展开对称；动画期间 dialog 留在 DOM 中无闪烁
- [x] 日期弹层现有"选日即回填并收起"交互逻辑不变（仅动画受益）

## 3. RecordFormPage.vue：外层容器

- [x] 现 :115 `<div class="d-flex ga-2">` → 改为普通 `<div>`（纵向堆叠后不再需要 flex 行）
- [x] `DatePickerPopover` 上的 `class="flex-grow-1"` 移除（组件根 `w-100` 自然占满）
- [x] "消费时间"标题与分隔线位置不动
- [x] 回归确认：金额键盘、标签选择等其余区域不动；`CsvMappingDialog`/`HistoryPage` 等其他 `v-dialog` 使用方不受影响

## 4. 测试（vitest）

### 4.1 DatePickerPopover.test.js（重写）

- [x] 用例 1：`show-time` 时渲染两个输入项，分属 `.date-time-fields` 下两个直接子块（非同一 flex-row）
- [x] 用例 2：未传 `show-time` → 仅日期字段（账单筛选场景回归）
- [x] 用例 3：点击时间字段 → 第二个 ExpandTransition `modelValue` 变 true 且 `origin` 为点击坐标；弹层含"取消/确定"
- [x] 用例 4：确定 → `update:modelValueTime` 回抛所选值、弹层关闭；取消 → 不回抛、`selectedTime` 不变
- [x] 用例 6：日期弹层选日仍即回填并收起（现有用例保持通过）

### 4.2 ExpandTransition.test.js（扩展）

- [x] 用例 5：`modelValue` 变 false 后先应用 collapse 样式（`transform: scale(0)`），`duration` 后 dialog 才真正关闭（fake timers）

## 5. 手工验收（竖屏 375px + 宽屏 1280px）

- [ ] 记一笔/编辑页：日期、时间各占一行，无贴挤
- [ ] 点击时间项：自点击位置圆形展开表盘时钟（24 小时制），含取消/确定；确定回填时间
- [ ] 收起为圆形收缩回原点——确定、取消、遮罩点击、ESC 四种关闭方式动画一致
- [ ] 日期弹层行为与改版前一致（选日即回填并收起）
- [ ] 账单页筛选日期控件（无 show-time）外观与行为逐像素不变
- [ ] M2 已合入时：宽屏 zoom 下弹层定位与动画正常（v-dialog teleport 到 body 不在 zoom 上下文）

## 6. 质量门槛

- [x] `cd frontend && npm test && npm run lint && npm run build` 通过
