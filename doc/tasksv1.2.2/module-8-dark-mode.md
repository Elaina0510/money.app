# 模块 8：深色模式 - 字体可读性优化

> 需求编号：#4
> 优先级：中
> 影响范围：前端 main.js、global.scss

---

## 任务列表

### 8.1 前端 - 全局深色模式文字颜色

- [ ] 在 `global.scss` 增强 `.v-theme--dark` 文字颜色覆盖
- [ ] 主标题（h5/h6/subtitle）使用纯白 `#FFFFFF`
- [ ] 正文（body-1/body-2）使用浅灰 `#E6E1E5`
- [ ] 副标题（caption）使用中灰 `#C8C3CE`
- [ ] 辅助文字（text-grey）使用 `#C8C3CE`

### 8.2 前端 - 修复内联颜色

- [ ] 在 `global.scss` 定义 `.page-subtitle` 全局类
- [ ] 深色模式下 `.page-subtitle` 使用 `#C8C3CE`
- [ ] 移除 `SettingsPage.vue` 的 `.page-subtitle` 内联颜色
- [ ] 移除 `RecordDetailPage.vue` 的 `.page-subtitle` 内联颜色
- [ ] 移除 `RecordListPage.vue` 的 `.page-subtitle` 内联颜色
- [ ] 移除 `RecordFormPage.vue` 的 `.page-subtitle` 内联颜色
- [ ] 移除 `AppLayout.vue` 副标题的 inline style

---

## 验收标准

- [ ] 深色模式首页副标题文字清晰可读
- [ ] 深色模式账单页副标题文字清晰可读
- [ ] 深色模式统计页副标题文字清晰可读
- [ ] 深色模式设置页所有文字可读
- [ ] 浅色模式无影响
