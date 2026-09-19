# M8 - 设置页/统计页入口图标颜色与位置统一

> 对应需求八（设计 §八）。设置页 7 入口 + 导入导出子条目 + 统计页预算入口图标统一 primary 色系圆底（`.entry-avatar`），删除内联 rgba 与静态 Material 色名，容器/左偏移/字阶对齐。基准 = 外观设置入口样式。
> 涉及文件：`frontend/src/styles/global.scss`、`SettingsPage.vue`、`StatisticsPage.vue`、`SettingsSubPages.test.js`。
> 依赖：无（第 1 梯队可并行）。与 M5 同改 SettingsPage.vue 但区域隔离（onMounted vs 模板入口）；与 M4 同改 global.scss 不同段落。仅调颜色/容器/对齐，不改文案、顺序与功能（需求 5 条）。

---

## 1. 全局工具类（`styles/global.scss` 新增）

- [x] 1.1 `/* 入口头像统一底色：主题 primary 10% 透明底，明暗自动跟随 */ .entry-avatar { background: rgba(var(--v-theme-primary), 0.1); }`
- [x] 1.2 确认外观基准色 `rgba(139,126,116,.1)` 即 light primary 的 10%（视觉零变化）
- [x] 1.3 主题色半透明底一律走 CSS 类——Vuetify color props 不支持 alpha 后缀（全局约定 §0.5）

## 2. 统一模板规范（所有入口，含导入导出四子条目）

- [x] 2.1 结构统一：`<v-avatar size="36" class="entry-avatar mr-2"><v-icon color="primary" size="20">mdi-xxx</v-icon></v-avatar>`
- [x] 2.2 **删除**全部内联 `rgba(...)` 头像底色与 `info/teal/blue/orange/warning/purple` 图标色——图标一律 `color="primary"`
- [x] 2.3 逐入口对照 §8.1 表处理：外观（基准）、分类、标签（原 info）、快速记账（原 teal）、导入导出（原 blue）、数据回溯（原 orange）、账号（原 warning）

## 3. 结构性修复

- [x] 3.1 导入导出子条目（:102-136）：裸 `v-icon size="20" class="mr-3"` 外套 `v-avatar size="36" class="entry-avatar mr-2"`，与卡头同规格
- [x] 3.2 数据回溯卡（:140-155）：`v-card pa-4` 去 `pa-4`（对齐摘要入口，消除双层 padding 叠加）；`v-list` 补 `class="bg-transparent pa-0"`（消除深色模式白底隐患）；头像按规范替换
- [x] 3.3 左偏移基准：摘要类入口（分类/标签/快速记账/数据回溯）统一 `v-card` 无 pa + `v-list-item` 默认内衬（≈16px）；区块类卡头（外观/导入导出/账号）flex `pa-4` 保持
- [x] 3.4 字阶统一取 `text-body-1 font-weight-medium`：数据回溯（:148 text-body-2）、导入导出子条目、账号区条目对齐升级；外观/导入导出卡头（text-subtitle-2）加挂覆盖类
- [x] 3.5 骨架不强行归一（v-card+v-list-item vs flex 头保留现状，需求 5 条不动布局骨架）

## 4. 统计页预算入口（需求 4 条）

- [x] 4.1 `StatisticsPage.vue:128-130`：`color="rgba(156,39,176,0.1)"` + `color="purple"` → `class="entry-avatar"` + `color="primary"`
- [x] 4.2 **红线**（易错点 9）：图表配色（`chartColors`/`balanceColor`/`getBudgetColor`/`BUDGET_COLORS`）是数据可视化语义色，**不在统一范围**，M8 仅动预算卡头一处

## 5. 测试（`SettingsSubPages.test.js` 新增源码红线断言）

- [x] 5.1 两类可寻址红线（不整文件扫 `rgba(`——StatisticsPage 图表配置合法使用）：
  ```javascript
  const AVATAR_INLINE_RGBA = /<v-avatar[^>]*color="rgba\(/s
  const STATIC_ICON_COLOR  = /<v-icon[^>]*color="(teal|blue|orange|warning|info|purple)"/s
  for (const src of [settingsPageSource, statisticsPageSource]) {
    expect(src).not.toMatch(AVATAR_INLINE_RGBA)
    expect(src).not.toMatch(STATIC_ICON_COLOR)
  }
  expect(settingsPageSource).toContain('entry-avatar')
  ```
- [x] 5.2 SettingsPage 可用更严断言：整文件 `not.toContain('rgba(')`（现状 rgba 仅 7 处 v-avatar color，scoped 样式零使用）
- [x] 5.3 渲染：挂载后 `.entry-avatar` 计数 ≥ 11（7 入口卡头 + 4 导入导出子条目）；其内图标均带 primary 色类
- [x] 5.4 源码断言：数据回溯卡不再出现 `class="pa-4 mb-3 settings-card"` 叠加写法

## 6. 验收与质量门槛

- [x] 6.1 `npm test`、`npm run lint` 通过
- [ ] 6.2 手工验收四组合（浅色/深色 × 375px/1280px）：设置页全入口 + 统计页预算头，同 primary 色系圆底、同 36/20 尺寸、逐行左偏移对齐；深色模式无静态 Material 色残留；导入导出子条目圆底与卡头一致
- [x] 6.3 抽查代码：两页不再出现内联 `rgba(...)` 底色与 `teal/blue/orange/purple/info/warning` 图标色
