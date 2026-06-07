# 模块 5：页面滑动模糊渐变

> **优先级：** 中 | **复杂度：** 中 | **涉及文件：** `AppLayout.vue`, `global.scss`

## 子任务

### 顶部标题栏下方模糊渐变

- [ ] 5.1 在 `.app-top-bar` 添加 `::after` 伪元素
- [ ] 5.2 设置 `position: absolute; bottom: -24px; left: 0; right: 0; height: 24px`
- [ ] 5.3 使用 `mask-image: linear-gradient(to bottom, black, transparent)` 实现渐变
- [ ] 5.4 添加 `-webkit-mask-image` 兼容 Safari
- [ ] 5.5 设置 `pointer-events: none; z-index: 99`
- [ ] 5.6 背景色使用 `rgb(var(--v-theme-background))` 跟随主题

### 页面底部模糊渐变

- [ ] 5.7 在 `.content-wrapper` 添加 `::after` 伪元素
- [ ] 5.8 设置 `position: fixed; bottom: 0; left: 50%; transform: translateX(-50%)`
- [ ] 5.9 宽度使用 `min(100%, 640px)` 响应式适配
- [ ] 5.10 使用 `background: linear-gradient(to bottom, transparent, rgb(var(--v-theme-background)))` 实现渐变
- [ ] 5.11 设置 `pointer-events: none; z-index: 50`

## 验收测试

- [ ] 主页向下滚动 → 标题栏下方出现模糊过渡
- [ ] 页面底部可见模糊渐变效果
- [ ] 切换深色模式 → 渐变颜色跟随主题
- [ ] 移动端和桌面端均正常显示
- [ ] 渐变区域不阻挡点击事件
