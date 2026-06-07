# 模块 6：宽屏适配 110% 放大

> **优先级：** 低 | **复杂度：** 低 | **涉及文件：** `AppLayout.vue`

## 子任务

- [ ] 6.1 在 `AppLayout.vue` scoped style 中添加 `@media (min-width: 960px)` 媒体查询
- [ ] 6.2 对 `.content-wrapper` 设置 `transform: scale(1.1); transform-origin: top center`
- [ ] 6.3 补偿底部间距：`padding-bottom: calc(100px * 1.1)`
- [ ] 6.4 在 `.main-content` 上添加 `overflow-x: hidden` 防止水平溢出
- [ ] 6.5 确认侧边栏和底部导航栏布局不受影响

## 验收测试

- [ ] 移动端（<960px）→ 内容保持原始比例
- [ ] 桌面端（≥960px）→ 内容放大 110%
- [ ] 放大后无水平滚动条
- [ ] 放大后点击、滚动、输入均正常
- [ ] 侧边栏展开/折叠不受影响
