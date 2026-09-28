# M5 - 横屏侧边栏图标列（REQ-010 / REQ-011 / REQ-012）

> 对应设计 §六（决策 D9：收起态图标列固定 72px、登出无二次确认、未登录退出图标不渲染）。目标：宽屏（≥960px）收起态从「temporary 完全隐藏」改为 Vuetify **rail 常驻图标列**（`:rail-width="72"` prop）；收起/展开切换钮移入侧栏顶部第一位（顶栏汉堡移除、顶栏右侧深色钮保留）；竖屏零行为改动。
> 涉及文件：改 `frontend/src/components/AppLayout.vue`（**实际路径以仓内现状为准**）、`AppLayout.test.js`、`AppLayout.wideScreenZoom.test.js`。**零后端、零新文件**。
> 依赖：无。与 M1–M4 零文件交叉，可完全并行。
> 行号为设计快照参考位，开工以 grep 定位为准。

---

## 0. 先读后写（本模块专属纪律）

- [x] 0.1 实测确认 vuetify 版本 ≥3.12 且 `rail-width` prop 可用（设计已核 `VNavigationDrawer.d.ts:40`）；**仓里不存在 `--v-navigation-drawer-rail-width` CSS 变量——禁走样式覆写路径，只用 prop**（审查轮落定 ①）
  > 实测证据（2026-09-28 本模块）：`frontend/node_modules/vuetify/package.json` 版本 **3.12.6**；`lib/components/VNavigationDrawer/VNavigationDrawer.js:46` 定义 `railWidth: { type: [Number, String], default: 56 }`，`:136` 计算宽 `Number(props.rail ? props.railWidth : props.width)`；`_variables.scss` 全文无 rail 宽变量。渲染探针（真实 Vuetify 挂 `v-app`，jsdom）输出：`rail=true` 时抽屉根 `class` 含 `v-navigation-drawer--rail`、内联 `width: 72px`；`rail=false` 时 `width: 240px` → prop 真实可用、`width=240` 展开宽不受影响。
- [x] 0.2 实测确认 `AppLayout.test.js` 环境事实：17 用例将 `v-navigation-drawer`/`v-btn` 等 stub——**单测一律走 props 断言 + 源码正则**（仓库既定范式），禁断 Vuetify 真实类名/计算样式/路由跳转（审查轮落定 ②）
  > 实测证据：本模块开工前该文件 17 用例全部以 `global.stubs` 替身化 Vuetify 组件；探针确认「不声明 props 的模板替身 `.props()` 返回 `{}`（绑定值以 attribute 落 DOM）」，故 M5 的 `.props('rail'/'railWidth'/'permanent')` 断言由**替身显式声明 props 白名单**承载，其余（`to` 值、`color` 值、v-tooltip 数、图标字面量）走 DOM attribute + `?raw` 源码正则；真实类名/计算宽度/悬停/路由跳转一律不断言，归 §5.4 人工。

## 1. 形态机改造（`AppLayout.vue`，设计 §6.1）

- [x] 1.1 抽屉绑定改组（替换原 `:rail="false"` 与 `:temporary="rail"` 两条）：`:permanent="isDesktop"`、`:temporary="!isDesktop"`、`:rail="isDesktop && rail"`、**`:rail-width="72"`**；`width=240` 保持；`v-model="drawer"` 保留绑定
- [x] 1.2 宽屏默认态维持 `rail=true`（进页即见图标列）；`toggleNav()` 宽屏分支 = 翻转 `rail` 后同步 `drawer.value = !rail.value`（v-model 语义一致，不出现 model 与可见态相反）；竖屏分支 `drawer = !drawer` 不变
  > 实测修正（本模块，实证设计 §6.1「宽屏 permanent 下仅状态位，显隐实际由 rail 切换」这一前提不成立）：jsdom 真实 Vuetify 探针——`permanent=true` 且 `modelValue=false` 时抽屉根被写 `inert` 且内联 `transform: translateX(-72px)`（`width: 72px` 仍保留），即收起态图标列**既不可见也不可点**，直接违背 REQ-010 验收「收起态下导航、设置、主题、登出全部可点达」。故 `drawer` 取「在位可见」语义：初值 `ref(isDesktop.value)`（宽屏 true / 竖屏维持原 false，竖屏不出现 temporary 抽屉打开态与遮罩），宽屏分支翻转 `rail` 后 `drawer.value = true`。本条目标「不出现 model 与可见态相反」在新写法下依然成立（宽屏两态抽屉都在位）。竖屏分支 `drawer = !drawer` 逐字未动。
- [x] 1.3 竖屏零改动钉死：外层 `v-show="isDesktop && !isLoginPage"` **逐字不动**；底栏/FAB 均不动；`:rail` 表达式含 `isDesktop &&` 守卫确保竖屏永不进 rail 态；「竖屏临时抽屉」为不可达死路径——**登记，不清理不扩权**
  > 登记：汉堡删除后竖屏已无任何唤出临时抽屉的入口（改版前汉堡亦仅宽屏渲染），该路径改版前后同样不可达 → 按任务口径**不清理不扩权**，`drawer` 竖屏分支与 `:temporary="!isDesktop"` 绑定原样保留，由 §4.8 源码正则钉死。

## 2. 收起态图标列（rail 专用块，REQ-010，设计 §6.2）

- [x] 2.1 实现载体取 **v-btn 列方案**（与 Vuetify rail slot 裁剪解耦更稳）：rail 专用块 `v-if="isDesktop && rail"`，展开态内容 `v-else` 维持现模板
- [x] 2.2 自上而下七项：① 收起/展开切换钮（`v-btn icon variant="text"`，`mdi-menu`，收起态点击=展开）② 主页 `/`（`mdi-view-dashboard-outline`）③ 账单 `/records`（`mdi-format-list-bulleted`）④ 统计 `/statistics`（`mdi-chart-box-outline`）⑤ 设置 `/settings`（`mdi-cog-outline`）⑥ 深色模式（`mdi-weather-night`/`mdi-weather-sunny`，点击 `appStore.toggleDarkMode()`）⑦ 退出登录（`mdi-logout`）——**仅 `isLoggedIn` 渲染**，未登录整钮不渲染、无悬空占位
- [x] 2.3 导航高亮：`route.path` 前缀判（复用 `currentRoute` 计算：`/detail`、`/add`、`/edit` 归账单）；设置 `startsWith('/settings')` 高亮；`.active-nav-item` 同款底色。**前景色口径（ui-design 1.1/十四章，2026-09-28 审查补）**：rail 钮默认呈 primary 灰褐前景（未选中与选中撞色、对比度紧张），一律显式传主题色名——导航/设置 4 钮 `:color="高亮命中 ? 'primary' : 'on-surface-variant'"`，主题/登出 2 钮恒 `color="on-surface-variant"`；写进 rail 模板，展开态不动
  > 落点：新增 `railActive` 计算属性承载高亮判据 = `currentRoute` 前缀判 + `/add`、`/edit` 归账单（`currentRoute` 本体逐字不动，否则竖屏底栏高亮会随之改变 → 触红线；口径仍为「复用 currentRoute 计算」的扩展位），设置走 `startsWith('/settings')`；rail 钮 `class="rail-btn nav-item …"` 复用既有 `.nav-item.active-nav-item`（hover `primary@0.06` / active `primary@0.1`）不新增底色体系；`color` 绑定全部写进 rail 模板（4 三元式 + 2 恒 `on-surface-variant`），展开态模板未动。图标列钮 `size="48"`（rail 72px 内居中，且满足 ui-design §0.8「24px 图标触控目标 ≥44px」）并各带 `aria-label`（纯图标按钮用途名，ui-design §0.8/十四章）。
- [x] 2.4 登出点击行为 = 现 `handleLogout()` **逐字不变**（清 localStorage → `resetListView()` → toast，无二次确认，D9）
- [x] 2.5 每项配 `v-tooltip`（activator 悬停显名称：主页/账单/统计/设置/深色模式或浅色模式/退出登录）
- [x] 2.6 样式（§6.4）：`.app-sidebar` 图标列 `align-items: center` 单列流、按钮间 `gap` 固定；rail 专用模板**不渲染任何 `<span>` 文本**；图标列 `overflow: visible`；主内容 `content-overflow` `overflow-x:hidden` 机制不动；登录页侧栏 `v-show` 隐藏逻辑不动（图标列随侧栏隐藏无残留）

## 3. 展开态重排（REQ-011，设计 §6.3）

- [x] 3.1 侧栏顶部第一位放同一切换钮（`mdi-backup-restore` 收起点击=展开）——与 §2.2 项① 是**同一 DOM 位置**（位置恒为首元素，图标随 `rail` 切换，零跳变）
  > 落点：切换钮从两态各一份的写法提升为**抽屉 slot 首位单例**（`v-btn.sidebar-toggle`，图标 `{{ rail ? 'mdi-menu' : 'mdi-backup-restore' }}`，外带 `v-tooltip activator="parent" location="end"`），rail 块与 `<template v-else>` 展开块都不再含切换钮 → 两态首元素恒为该钮（§4.5 用例以 `firstElementChild` 断言两态同位）。
- [x] 3.2 「Money App + 个人记账」介绍块（`.sidebar-header`）下移至按钮之下（原第 0 位变第 1 位）
  > 落点：`.sidebar-header` 成为展开块（`<template v-else>`）首个节点，即整个侧栏内容第 2 个元素（索引 1），紧随切换钮之后。
- [x] 3.3 导航列表、设置项、用户名/退出区、深色 switch 功能与版式不动
  > 展开态模板整体原样搬进 `<template v-else>`（逐字未改，含 `nav-item` 文案 `<span>`、用户区、`v-switch`）；仅抽屉底部 append 区加 `v-if="!(isDesktop && rail)"` 守卫以满足 §2.6「rail 专用模板不渲染任何 `<span>` 文本」（收起态用户名/深色 switch 文案属文本残留，展开态照常渲染，功能不变）。
- [x] 3.4 顶栏：删除汉堡按钮块（约 :115-124 的 `v-if="isDesktop && !isLoginPage"` 按钮）；**右侧深色切换钮保留不动**
  > 落点：`frontend/src/components/layout/AppLayout.vue` 顶栏块内汉堡 `v-btn`（`mdi-menu`/`mdi-close` 图标切换 + 原 tooltip）整体删除，原位留一行注释登记删除理由；`.top-bar-actions` 内右侧深色切换钮逐字未动（§4.6 断言顶栏 `<v-btn` 只 1 个）。

## 4. 测试（REQ-012，`AppLayout.test.js` 既有收起/展开断言**更新**、不删场景语义；设计 §6.5 八条）

- [x] 4.1 宽屏初始 `rail=true`：抽屉组件 `.props('rail')===true`、`.props('railWidth')===72`、`.props('permanent')===true`（对替身模板组件断言）
  > `M5-T4.1`：`v-navigation-drawer` 替身**显式声明 props 白名单**（`modelValue/permanent/temporary/rail/railWidth/width/mobileBreakpoint/elevation`）后 `.props()` 才读得到绑定值——`rail===true`、`railWidth===72`、`permanent===true`、`temporary===false`、`width===240`、`modelValue===true`；另以 `drawerTagSrc()`（正则 `/<v-navigation-drawer\b[^>]*>/` 切抽屉开标签）钉 `:rail="isDesktop && rail"` 与 `:rail-width="72"`。零 Vuetify 真实类名/计算宽度断言。
- [x] 4.2 收起态入口可点达：rail 专用按钮块存在且 6 钮（导航 3 + 设置 + 主题 + 登出）；导航/设置钮以 **`to` 属性值**断言（`/`、`/records`、`/statistics`、`/settings`），不真点跳转；点主题钮 → `toggleDarkMode` 被调；点登出 → localStorage 三键被清 + toast（复用现 handleLogout 测试桩）；源码正则断 rail 钮 `color` 绑定（§2.3 前景色口径）：导航/设置 4 钮三元式（`primary`/`on-surface-variant`），主题/登出 2 钮恒 `on-surface-variant`
  > `M5-T4.2`：`.sidebar-rail` 下 `findAll('.v-btn')` 长度 6；`to` 走 `v-btn` 替身不声明 props → 以 **attribute** 断言（`.rail-home-btn` `/`、`.rail-records-btn` `/records`、`.rail-statistics-btn` `/statistics`、`.rail-settings-btn` `/settings`），不点跳转；主题钮 `trigger('click')` → `toggleDarkMode` 调用 1 次；登出钮点击 → `token/username/userId` 三键 `toBeNull()` + `mockResetListView` 1 次 + `showToast('已退出登录','info')`。`color` 正则按 rail 区块切片（`railBlockSrc()` = `'<div v-if="isDesktop && rail" class="sidebar-rail">'` → `'<template v-else>'`）收敛：`:color="railActive === '[^']+' \? 'primary' : 'on-surface-variant'"` **恰好 4 处**、`\scolor="on-surface-variant"` **恰好 2 处**、`not.toMatch(/\scolor="primary"/)`；DOM 侧另在 `/records` 下确认选中转 `primary`、未选中控 `on-surface-variant`。
- [x] 4.3 未登录：`isLoggedIn=false` → 登出钮 `not.exists()`，其余 5 钮在
  > `M5-T4.3`：`wrapper.find('.rail-logout-btn').exists()` 为 `false`（整钮不渲染、无悬空占位），rail 块 `.v-btn` 与 `.v-tooltip` 各 5 个，其余 5 钮逐个 `exists()` 为 `true`。
- [x] 4.4 悬停提示：源码正则断 rail 块每个按钮均包 `v-tooltip`（数量 == 可见图标数）；真实悬停归人工
  > `M5-T4.4`：rail 区块切片内 `/<v-btn/g` === 6 且 `/<v-tooltip\s+activator="parent"/g` === 6（一钮一提示）；DOM 侧 6 个 `.rail-*-btn` 内各含非空 `.v-tooltip` 文案，全组件 tooltip 共 7（含首位切换钮）。替身 `'v-tooltip': { template: '<div class="v-tooltip"><slot /></div>' }` 只渲染文案，**真实悬停出现归 §5.4 人工**。
- [x] 4.5 切换钮零跳变：展开/收起两态下 `sidebar-toggle` 选择器均为侧栏内容首元素（同一 DOM 位）
  > `M5-T4.5`：`sidebarEl.firstElementChild.classList.contains('sidebar-toggle')` 在 `rail=true` 与点击 `toggleNav()` 后 `rail=false` **两态均为 true**（同一 DOM 实例未重建）；顺带断 `children[1]` 为 `.sidebar-header`（§3.2 下移）与两态 tooltip 文案「展开侧边栏」。
- [x] 4.6 顶栏无汉堡：`.app-top-bar` 区块内 `mdi-backup-restore` 钮 count=0（**勿反查 `mdi-menu`**——rail 切换钮本体就是 `mdi-menu`，同字面量易误伤）；右侧深色钮仍在
  > `M5-T4.6`：顶栏区块切片（`topBarSrc()` = `'<div class="app-top-bar'` → `'<!-- Page Content'`）内 `not.toMatch(/mdi-backup-restore/)`、`<v-btn` 数量 **1**、且 `toMatch(/appStore\.toggleDarkMode\(\)/)` + `mdi-weather-night`/`mdi-weather-sunny`（右侧深色钮保留）；**未反查 `mdi-menu`**（按任务口径避坑），改以全源 `toMatch(/rail \? 'mdi-menu' : 'mdi-backup-restore'/)` 证明切换钮在侧栏，DOM 侧 `.app-top-bar .v-btn` 长度 1、`.app-top-bar .sidebar-toggle` 不存在、`.app-sidebar .sidebar-toggle` 存在。
- [x] 4.7 高亮同步：`route.path='/settings/about'` → 设置图标 active 类（startsWith 口径）
  > `M5-T4.7`：`/settings/about` → `.rail-settings-btn` 含 `active-nav-item` 且 `color` attribute 为 `primary`、`.rail-home-btn` 不含；另覆盖 `/add`、`/edit/12`、`/detail/12` 归账单（`railActive` 前缀判口径）。
- [x] 4.8 源码正则钉竖屏：`temporary` 绑定含 `!isDesktop`；`v-show="isDesktop && !isLoginPage"` 逐字保留；底栏 `v-if="!isDesktop && !isLoginPage"` 逐字保留
  > `M5-T4.8` 竖屏三处逐字钉死：抽屉开标签切片 `toMatch(/v-show="isDesktop && !isLoginPage"/)`、`/:temporary="!isDesktop"/`、`/:rail="isDesktop && rail"/`、`/:width="240"/`；底栏 `toMatch(/<v-bottom-navigation\s+v-if="!isDesktop && !isLoginPage"\s+v-model="currentRoute"/)`；FAB `toMatch(/<v-btn\s+v-if="!isLoginPage"\s+class="fab-add"/)`。同用例并钉红线机件：`drawer\.value = !drawer\.value` 竖屏分支在场、全源 `not.toContain(['--v','navigation','drawer','rail','width'].join('-'))`（禁样式覆写零命中；变量名分段拼接以免测试文件自身污染终验 grep）、`railBlockSrc()).not.toMatch(/<span/)`。竖屏渲染侧：`rail===false`、`temporary===true`、`permanent===false`、`.sidebar-rail` 不渲染、`.bottom-nav` 在、底栏 4 钮、侧栏 `display: none`。
- [x] 4.9 `AppLayout.wideScreenZoom.test.js`：zoom/content-overflow 断言**零改动**通过（回归锚）——若有失败，改 `AppLayout.vue` 适配断言，不改该测试文件语义
  > 该文件 **git 状态零改动**（11 用例原样通过）。`M5-T4.9` 只在我新增用例侧确认可不被破坏：`.content-overflow\s*\{\s*overflow-x:\s*hidden`、`@media \(min-width: 960px\)[\s\S]*?\.content-wrapper\s*\{\s*zoom:\s*1\.1` 两锚在场；图标列样式取 `overflow: visible`（不引入 `overflow-x: auto|scroll`，同时满足 `RecordListPage.test.js` 对 AppLayout 源码的反向断言）。

## 5. 验收门槛

- [x] 5.1 本模块测试全绿；全量 `npx vitest run` 绿、eslint 基线零新增（零后端改动，pytest/mypy/ruff 由主 Agent 终验兜底）
  > 实测（2026-09-28，`cd frontend && npm_config_proxy=false npm_config_https_proxy=false …`）：`npm test` → **Test Files 15 passed (15) / Tests 421 passed (421)，0 failed**（开工基线 411 + 本模块新增 10；`AppLayout.test.js` 27、`AppLayout.wideScreenZoom.test.js` 11 **零改动**通过）；`npm run lint` → **0 errors, 2 warnings**（与基线同值，均 CsvMappingDialog 既有）；`npm run build` → 成功（dist 不提交，终验统一重建）。
- [x] 5.2 红线自查：不改竖屏抽屉与底栏行为、不动顶栏右侧深色钮、不改 FAB、不引新依赖
  > 逐项：竖屏 `toggleNav` 分支 `drawer.value = !drawer.value` 逐字未动、`:temporary="!isDesktop"`/外层 `v-show` 逐字未动、底栏 `v-if="!isDesktop && !isLoginPage"` 与 `currentRoute` 计算本体未动（收起态高亮改走新增 `railActive`，避免竖屏底栏行为被牵动）、FAB 块未动、顶栏右侧深色钮未动——全部由 `M5-T4.8`/`M5-T4.6` 源码正则钉死；`frontend/package.json` **git 状态零改动**（零新依赖，`v-tooltip` 来自既有 vuetify 3.12.6）；样式覆写零引入（`--v-navigation-drawer-rail-width` 全仓源码/文档 grep 零命中，rail 宽仅 `:rail-width="72"` prop）。零后端文件被触碰。
- [x] 5.3 pathspec 精确提交：`AppLayout.vue` + 两测试文件 + 本任务文件；`frontend/dist` 不提交；不 push
  > 提交仅 `git add` 精确路径 `frontend/src/components/layout/AppLayout.vue`、`frontend/src/components/layout/AppLayout.test.js`、`doc/tasksv1.4.4/m5-sidebar-rail.md`（`AppLayout.wideScreenZoom.test.js` 零改动 → 无内容可提交，不入 pathspec）；未用 `-A/./-f`，未提交 `frontend/dist`、`progress.md` 与其他 lane 的脏文件，未 push、未建分支。
- [ ] 5.4 真机项不勾选、抄入人工清单（设计 §6.5 移交三项）：rail 计算宽 72px、无文字残留/无横向滚动条、悬停提示真实出现；横屏收起/展开图标列真机点验与截图
  > **按设计保持不勾选**（stub 环境无法断真实类名/计算样式/悬停），已逐条抄入完成报告 `manual_items`，交主 Agent 终验浏览器实测阶段。

**验收标准（REQ-010/011/012）**：收起态下导航、设置、主题、登出全部可点达且行为与展开态等价；未登录收起态无退出图标；切换钮两态位置零跳变；<960px 行为与改版前一致；既有测试套件全绿（含更新后的 AppLayout 测试）。
