# REQ-006 快速记账页日期时间栏布局调整

> **优先级**: P2 · **涉及文件**: DatePickerPopover.vue, RecordFormPage.vue · 建议与 REQ-007 一起实施

## 任务清单

### 1. 调整 activator 区域布局
- [x] 将 activator 区域改为 `d-flex align-center ga-2` 横向布局
- [x] 日期字段使用 `flex-grow-1` 占据剩余空间
- [x] 时间字段添加 `class="time-field"` 限制最大宽度（`max-width: 140px`）

### 2. 移除弹窗内的时间选择器
- [x] 当 `showTime` 为 true 时，不再在日期弹窗内显示时间输入
- [x] 时间选择改为在 activator 区域独立显示

### 3. 增强日期栏边框
- [x] `:deep(.v-text-field)` 添加 `border-radius: 12px`（由全局样式处理）
- [x] 确认 `variant="outlined"` 和 `density="compact"` 属性

### 4. 时间字段交互
- [x] 时间字段设为 `readonly`，不使用 `type="time"`，时间选择通过 REQ-007 的 `v-time-picker` 弹窗完成
- [x] 时间字段添加 `@click.stop="openTimePicker"`（打开独立时间弹窗）
- [x] 确认 `modelValueTime` 双向绑定逻辑正常

### 5. 确认 RecordFormPage 无需改动
- [x] 确认 `DatePickerPopover` 的 props 接口保持不变

### 6. 测试验收
- [ ] 记账页日期和时间在同一行显示
- [ ] 时间选择器右对齐
- [ ] 时间始终可见，无需额外操作
- [ ] 选择日期和时间后正确回显
