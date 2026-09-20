# M6 - 二级页面内部间距疏朗化（需求六）

> 对应需求六（设计 §六）。全局疏朗化口径（D10）落 `global.scss`，标签管理/快速记账/数据回溯三页套用；**分类管理页由 M8 重写时直接按本口径落样式，M6 不触碰该文件**（设计 §0.1 防两模块互相覆盖）。
> 涉及文件：`frontend/src/styles/global.scss`、`SettingsTagsPage.vue`、`SettingsQuickTemplatesPage.vue`、`HistoryPage.vue`、`SettingsSubPages.test.js`。
> 依赖：无（分类页部分排在 M8 后由 M8 承接）。批 1 即可完成其余三页（设计附录 B）。

---

## 1. 全局口径（D10，`global.scss` 统一承载）

- [x] 1.1 `.page-card` padding：16px → **20px**（:109-115）
- [x] 1.2 `.page-card .v-list-item { min-height: 48px; margin-block: 4px; }`（行高下限 + 行间垂直间距）
- [x] 1.3 `.page-card .v-list { padding: 0; }`
- [x] 1.4 新区块标题类：`.section-title { margin: 8px 0 12px; }`（配 `text-caption text-grey font-weight-medium` 语义类使用）；`.section-block + .section-block { margin-top: 20px; }`
- [x] 1.5 页面底部滚动余量：外层 `AppLayout .content-wrapper` 已有 `padding-bottom: 100px`（含安全区）——**不新增规则**，仅列自查项（需求 6.2.4 已满足）
- [x] 1.6 四页 + M5 新页经 `.page-card` 自动受益；规则全部限定 `.page-card` 作用域内，设置主页卡片（非 page-card）不受影响

## 2. 逐页套用（三页）

- [x] 2.1 标签管理 `SettingsTagsPage.vue`：分页列表外层确认包 `.page-card`（v1.4.2 已有则核）；分组标题改挂 `section-title`；`v-list` 去 `density="compact"`（若保留则行高由 min-height 托底，二选一按视觉定）
- [x] 2.2 快速记账 `SettingsQuickTemplatesPage.vue`：模板列表同上口径；新增对话框不动（样式收敛归 M14）
- [x] 2.3 数据回溯 `HistoryPage.vue`：:27 `<v-card v-else rounded="xl" class="mb-4">` → `.page-card` div 容器（`v-else` 分支条件移至 div，内部 `v-list` 保留）；空态分支（:22）已是 `page-card` 不动；回溯详情展开区行距随全局规则受益

## 3. 边界自检（设计 §6.3）

- [x] 3.1 全局 min-height 对 `.page-card` 内嵌套头像行（History 详情展开）：48px 为下限，不压缩现有高度；逐页自查过一遍
- [x] 3.2 深色模式：纯间距零色彩改动，无风险，走查确认即可

## 4. 测试（设计 §6.4，`SettingsSubPages.test.js` ?raw 断言组）

- [x] 4.1 `global.scss ?raw` 含 `.page-card` 内 `padding: 20px`、`.v-list-item` `min-height: 48px`、`section-title` 规则
- [x] 4.2 `HistoryPage.vue ?raw`：主体改挂 `page-card`，且模板区不含字面量 `<v-card v-else rounded="xl" class="mb-4">`
- [x] 4.3 标签/快速记账两页 `?raw` 含 `section-title`

## 5. 验收与质量门槛

- [x] 5.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 5.2 手工自查：标签/快速记账/数据回溯三页（分类页待 M8 后同查）与设置主页节奏一致、明显不再拥挤；行与块间距有节奏；末行不被底栏/安全区遮挡；深色模式同查；竖/宽屏
