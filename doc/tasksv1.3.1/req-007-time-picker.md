# REQ-007 时间选择器UI优化

> **优先级**: P2 · **涉及文件**: DatePickerPopover.vue · 建议与 REQ-006 一起实施

## 任务清单

### 1. 确认 v-time-picker 可用
- [x] 确认 `v-time-picker` 从 `vuetify/components` 主包导出（Vuetify v3.12.6 已非 Labs 组件），`main.js` 中全量注册已包含

### 2. 新增独立时间选择弹窗
- [x] 添加 `showTimePicker` ref 状态
- [x] 使用 `v-dialog` + `v-card` 包裹 `v-time-picker`
- [x] `v-time-picker` 设置 `format="24hr"`, `color="primary"`, `width="100%"`
- [x] 弹窗标题："选择时间"
- [x] 弹窗底部添加"取消"和"确定"按钮

### 3. 新增交互逻辑
- [x] `openTimePicker()` — 打开时间选择弹窗
- [x] `confirmTime()` — emit `update:modelValueTime` 并关闭弹窗

### 4. 样式适配
- [x] `v-time-picker` 添加 `border-radius: 16px`（与日历组件一致）
- [x] 确认深色/浅色模式下弹窗样式正常

### 5. 测试验收
- [ ] 点击时间字段弹出圆形时钟面板
- [ ] 时钟面板与日历组件圆角、配色一致
- [ ] 切换深色/浅色主题后面板样式正常
- [ ] 选择时间后正确显示在输入框
