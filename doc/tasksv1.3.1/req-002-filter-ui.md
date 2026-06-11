# REQ-002 账单页筛选列表UI优化

> **优先级**: P2 · **涉及文件**: RecordListPage.vue, global.scss

## 任务清单

### 1. 筛选栏卡片样式增强
- [x] 添加 `variant="flat"` 或 `elevation="0"`（配合 REQ-003 全局阴影系统）
- [x] 添加内部 padding `pa-4`
- [x] 筛选项之间使用 `v-row` + `v-col` 响应式布局

### 2. v-select 样式微调
- [x] 确认 variant（`outlined`），调整 `bg-color="surface"`
- [x] 确保 `rounded="lg"` 与整体风格一致
- [x] 类型筛选添加 `prepend-inner-icon="mdi-swap-vertical"`
- [x] 分类筛选添加 `prepend-inner-icon="mdi-shape-outline"`

### 3. 筛选栏响应式布局
- [x] 使用 `v-row` + `v-col` 实现响应式排列
- [x] 日期筛选和类型/分类筛选在同一行（4列布局）
- [x] 移动端：每行 2 个筛选项（`cols="6"`）
- [x] 桌面端：一行 4 个筛选项（`sm="3"`）

### 4. 测试验收
- [ ] 视觉审查：圆角、间距、颜色与整体一致
- [ ] 切换深色/浅色模式后筛选栏样式正常
- [ ] 使用各筛选组合验证数据过滤正确
- [ ] 375px / 768px / 1440px 下布局正确
