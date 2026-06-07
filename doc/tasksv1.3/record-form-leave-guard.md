# 模块 1：记账页返回时未保存提醒

> **优先级：** 高 | **复杂度：** 低 | **涉及文件：** `RecordFormPage.vue`

## 子任务

- [ ] 1.1 新增 `isDirty`、`showLeaveDialog`、`pendingNavigation` 三个 ref
- [ ] 1.2 实现 `takeSnapshot()` 函数，序列化当前表单字段为 JSON 字符串
- [ ] 1.3 在 `onMounted` 中加载完成后保存 `initialSnapshot`（新建模式取默认值快照）
- [ ] 1.4 使用 `watch` 监听所有表单字段深层变化，与 `initialSnapshot` 对比更新 `isDirty`
- [ ] 1.5 实现 `onBeforeRouteLeave` 守卫：`isDirty` 为 true 时拦截导航、存入 `pendingNavigation`
- [ ] 1.6 修改页面返回按钮：`router.back()` 改为 `handleBack()`，脏状态时显示弹窗
- [ ] 1.7 复用 `ConfirmDialog.vue`，配置 `title`、`message`、`confirm-text="确定放弃"`、`confirm-color="error"`
- [ ] 1.8 实现 `confirmLeave()`：清除 `isDirty` → 关闭弹窗 → 执行 `pendingNavigation`
- [ ] 1.9 实现 `cancelLeave()`：关闭弹窗 → 清除 `pendingNavigation`
- [ ] 1.10 在 `submit()` 成功后、`router.push('/')` 前设置 `isDirty.value = false`

## 验收测试

- [ ] 进入记账页 → 不做修改 → 点返回 → 直接退出
- [ ] 进入记账页 → 修改金额 → 点返回 → 弹出确认框
- [ ] 确认框点"取消" → 留在页面
- [ ] 确认框点"确定放弃" → 退出页面
- [ ] 编辑模式 → 改回原始值 → 点返回 → 直接退出（快照对比）
- [ ] 编辑模式 → 修改后点保存 → 正常提交不弹框
- [ ] 移动端浏览器物理返回键 → 同样触发确认框
