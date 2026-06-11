# REQ-008 深色/浅色模式自动切换

> **优先级**: P1 · **涉及文件**: useAppStore.js, AppLayout.vue, SettingsPage.vue

## 任务清单

### 1. useAppStore.js — 新增 themeMode state
- [x] 定义 `THEME_KEY = 'money-app-theme-mode'`
- [x] 新增 `themeMode` ref，从 localStorage 读取初始值，默认 `'auto'`
- [x] 新增 `resolveDarkMode()` 函数：`auto` 时读取 `matchMedia`，否则按 `themeMode` 判断

### 2. useAppStore.js — 新增 setThemeMode action
- [x] 更新 `themeMode.value`
- [x] 写入 `localStorage.setItem(THEME_KEY, mode)`
- [x] 更新 `darkMode.value = resolveDarkMode()`

### 3. useAppStore.js — 新增 initThemeListener
- [x] 初始化时调用 `resolveDarkMode()` 设置 `darkMode`
- [x] `matchMedia('(prefers-color-scheme: dark)')` 监听 `change` 事件
- [x] 仅在 `themeMode === 'auto'` 时响应系统变化

### 4. useAppStore.js — 修改 toggleDarkMode
- [x] 快速切换时：如果当前是 `auto`，切换为与当前状态相反的固定模式
- [x] 非 `auto` 时：正常切换 `dark` / `light`

### 5. useAppStore.js — 暴露新属性
- [x] return 中新增 `themeMode`
- [x] return 中新增 `setThemeMode`, `initThemeListener`

### 6. AppLayout.vue — 移除强制 light mode
- [x] 删除 `onMounted` 中的 `appStore.setDarkMode(false)`

### 7. AppLayout.vue — 初始化主题监听
- [x] 将 `appStore.initThemeListener()` 添加到现有的 `onMounted` 钩子中

### 8. SettingsPage.vue — 新增外观设置卡片
- [x] 导入 `useAppStore`（已导入）
- [x] 新增外观设置卡片作为第一个设置项
- [x] 使用 `v-btn-toggle` 实现三态切换：自动 / 浅色 / 深色
- [x] 绑定 `v-model="appStore.themeMode"`，`@update:model-value="appStore.setThemeMode"`
- [x] 每个按钮带 `v-icon`：`mdi-brightness-auto` / `mdi-weather-sunny` / `mdi-weather-night`

### 9. 测试验收
- [ ] 选择"自动"后，切换系统深色/浅色，应用跟随变化
- [ ] 选择"深色"/"浅色"后，切换系统设置，应用不变
- [ ] 刷新页面后，上次选择的模式保持
- [ ] 系统主题变化时，应用实时切换无需刷新
- [ ] 侧边栏/顶部栏的快速切换按钮仍可使用
