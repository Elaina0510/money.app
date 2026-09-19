# M4 - 设置二级页面统一卡片图层容器

> 对应需求四（设计 §四）。从设置进入的二级页主体内容统一包 `.page-card` 卡片图层（surface 底/16px 圆角/level-1 阴影/16px 内边距），消除列表透视到页面背景。
> 涉及文件：`frontend/src/styles/global.scss`、`SettingsCategoriesPage.vue`、`SettingsTagsPage.vue`、`SettingsQuickTemplatesPage.vue`、`HistoryPage.vue`、`SettingsSubPages.test.js`。
> 依赖：无（第 1 梯队）。范围核对结论 D7：外观设置/导入导出是主页卡区块无二级页，不动；二级页 = 分类/标签/快速记账/数据回溯四页。分类页与 M1-M3 同文件但区域不同（外层包裹），快速记账页与 M6 共享（按 M4 → M6 合并）。

---

## 1. 全局规范容器（`styles/global.scss` 新增）

- [x] 1.1 新增 `.page-card`：
  ```css
  .page-card {
    background: rgb(var(--v-theme-surface));
    border-radius: 16px;
    box-shadow: var(--shadow-level-1);
    padding: 16px;
    margin-bottom: 12px;   /* 对齐设置主页 .mb-3 节奏 */
  }
  ```
- [x] 1.2 深色模式不加分支：`--v-theme-surface` 运行时随主题切换（light #FFFFFF / dark #2C2C2C），确认对比可辨
- [x] 1.3 `.settings-card` 钩子类**不**另行赋样式——统一改用 `.page-card`；既有文件上挂载的 `settings-card` 类名保留为语义标记（避免无谓 diff）

## 2. 三个二级页容器结构（统一形态）

- [x] 2.1 统一结构：页头（返回+副标题+操作按钮）留卡外不动；主体内容包入 `<div class="page-card">`
- [x] 2.2 分类页：支出/收入两块**同卡分区**（卡内「支出分类/收入分类」两级小标题，块间距 `mb-4`）
- [x] 2.3 标签页：chip 云（+ M5 分页控件）入卡
- [x] 2.4 快速记账页：模板列表入卡
- [x] 2.5 去除**页面级透视**的列表 `bg-transparent`（分类 :30、:83；模板 :26）——口径：`.page-card` 之外不得有内容直贴页面背景；M3 合入后 Draggable 所在 `<v-list class="bg-transparent pa-0">` 位于卡壳**内部**、不再产生透视，属合法保留，不纳入清除范围（易错点 6，与 M3 §4.1 注记对齐）
- [x] 2.6 各页 scoped 内与卡壳冲突的旧样式（对列表的透明假设）逐一清除；页面根 `padding-bottom: 20px` 保留

## 3. 数据回溯页（HistoryPage）核对

- [x] 3.1 空态块（:22-25「暂无记录」）包入 `.page-card`（实施取包卡统一）
- [x] 3.2 既有列表 `v-card`（:27）已符合规范，不重构

## 4. 测试（`SettingsSubPages.test.js` 增补，?raw 源码断言手法）

- [x] 4.1 三个二级页源码均含 `page-card`
- [x] 4.2 分类/模板页断言**页面级无透视容器**：`.page-card` 之前的外层结构不再出现列表直贴页面背景的写法。断言实现禁止用整串字面量 `not.toContain('class="bg-transparent pa-0"')`——M3 合入后该串在 Draggable 的 v-list 上合法存在，整串断言必红；取"`.page-card` 外无 `bg-transparent`"的结构性口径（截取卡壳外模板片段再断言，或按 M3 合入先后与本模块 §2.5 口径同步调整）
- [x] 4.3 渲染快照：分类页支出/收入标题位于 `.page-card` 内部（`wrapper.find('.page-card').text()` 含两组标题）

## 5. 验收与质量门槛

- [x] 5.1 `npm test`、`npm run lint` 通过
- [ ] 5.2 手工验收四组合（浅色/深色 × 375px/1280px）：分类/标签/快速记账/数据回溯四页，内容与设置主页观感一致——卡片浮于米白背景、四周留白与阴影可见，非文字直压背景
- [ ] 5.3 深色模式下卡片与背景对比清晰、层级同样成立
