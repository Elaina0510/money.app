# 模块 2：日历组件风格升级与动画

> **优先级：** 中 | **复杂度：** 中 | **涉及文件：** `ExpandTransition.vue`(新增), `DatePickerPopover.vue`(新增), `RecordFormPage.vue`, `RecordListPage.vue`

## 子任务

### ExpandTransition.vue（公共动画组件）

- [ ] 2.1 新建 `frontend/src/components/common/ExpandTransition.vue`
- [ ] 2.2 定义 Props：`modelValue`(Boolean)、`origin`({x,y})、`duration`(默认 250)
- [ ] 2.3 实现 `calcOrigin(dialogEl, clickX, clickY)` 计算 transform-origin 百分比
- [ ] 2.4 使用 `v-dialog` 作为容器，自定义 Vue transition 函数
- [ ] 2.5 编写 CSS：`scale(0)→scale(1)` + `opacity` 过渡，`ease` 缓动

### DatePickerPopover.vue（日历弹出组件）

- [ ] 2.6 新建 `frontend/src/components/common/DatePickerPopover.vue`
- [ ] 2.7 定义 Props：`modelValue`(日期)、`modelValueTime`(时间)、`showTime`(Boolean)
- [ ] 2.8 定义 Events：`update:modelValue`、`update:modelValueTime`（v-model 双向绑定所需）
- [ ] 2.9 封装 Vuetify `v-date-picker`，配合 `ExpandTransition` 展示
- [ ] 2.10 通过 `#activator` 插槽暴露触发元素，点击时传递 `(clientX, clientY)` 给 ExpandTransition
- [ ] 2.11 可选附带 `v-text-field type="time"` 用于时间选择

### RecordFormPage.vue 替换

- [ ] 2.12 将消费日期 `<v-text-field type="date">` 替换为 `DatePickerPopover`（含 `show-time` prop）
- [ ] 2.13 确保 `consumeDate` / `consumeTime` 绑定正常工作

### RecordListPage.vue 替换

- [ ] 2.14 将筛选栏两个 `<v-text-field type="date">` 替换为 `DatePickerPopover`（不含时间）
- [ ] 2.15 确保筛选日期绑定和筛选逻辑正常工作

## 验收测试

- [ ] 记账页点击日期字段 → 日历从点击位置展开
- [ ] 账单页点击开始/结束日期 → 同样的展开动画
- [ ] 选择日期后日历收起，字段值正确更新
- [ ] 动画流畅 ≥ 60fps
