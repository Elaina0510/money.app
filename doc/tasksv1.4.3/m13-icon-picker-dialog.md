# M13 - 分类图标选择改独立居中弹窗（需求十三）

> 对应需求十三（设计 §十三）。`CategoryIconPicker` 双分支（宽屏内联撑大外层对话框 / 窄屏 fullscreen 嵌表单内 + 240px 写死网格带）重写为**全端统一居中独立小弹窗**，与新增/编辑分类对话框解耦；组件 API 不变（`modelValue` + `update:modelValue`）。
> 涉及文件：`frontend/src/components/common/CategoryIconPicker.vue`（重写）、`CategoryIconPicker.test.js`（重写）。
> 依赖：无。批 2 紧随 M8（M8 已删类型下拉，表单形态稳定后再动图标字段）。浮层动画统一收编归 M14。

---

## 1. 删除双分支（设计 §13.2 第 1 点，用户裁定否决底部面板与双分支）

- [x] 1.1 删除 `NARROW_BREAKPOINT`/`isNarrow`/resize 监听
- [x] 1.2 删除宽屏表单下内联展开分支（:28-37）与窄屏 `fullscreen` dialog 分支（:40-58）——全端仅一条居中路径
- [x] 1.3 删除网格容器写死 `max-height: 240px`（:204-207）

## 2. 居中弹窗结构

- [x] 2.1 `v-dialog`（非 fullscreen）：`max-width="min(560px, 92vw)"`（需求示例 90vw，「具体设计定」条款下取 92vw 与内边距节奏统一）、卡片 `max-height: 80vh`；**竖屏下不得超出视口**
- [x] 2.2 弹窗体 `display:flex; flex-direction:column`：顶部 标题「选择图标」+ 当前选中预览（大预览 48px + 图标名）
- [x] 2.3 网格滚动区：`flex:1; min-height:0; overflow-y:auto` **撑满弹窗可用高度**；`repeat(auto-fill, minmax(44px, 1fr)); gap 8px`，列数随宽度自适应，单元格 `aspect-ratio:1`；约 100 个图标全部可滚到
- [x] 2.4 底部「完成」按钮（+ ✕ 关闭）；activator 保持现状（圆底 32 + 图标名 + 「▾ 选择图标」+ 非精选集提示）

## 3. 交互与层级

- [x] 3.1 点选即 `emit('update:modelValue', icon)` + 高亮描边（`.icon-cell--selected` 现样式沿用）+ 顶部预览响应式更新；「完成」/✕/遮罩**仅关闭、不再 emit**（单段式保持）
- [x] 3.2 关闭后回到分类表单实时预览所选图标；`modelValue` 非精选集（存量图标）：提示 chip 保留、网格无选中项、预览显示原图标、选新图标即覆盖（无强制迁移，沿 v1.4.2 D6）
- [x] 3.3 **焦点与层级**：activator 持 ref；dialog `@after:leave` → `activatorRef.focus()`（需求 13.3 回焦表单）；嵌套于分类对话框之上——Vuetify overlay 默认后开者置上，无需手动 z-index
- [x] 3.4 初版过渡 `transition="dialog-bottom-transition"`（非瞬现即合规；M14 收编为 AppDialog 原点点开，替换本条）
- [x] 3.5 快速连点 activator：受控 modelValue 幂等开关，无叠层；极窄视口（<360px）：92vw + auto-fill 至少 5 列无溢出、80vh 上限保证「完成」常驻可见

## 4. 测试（`CategoryIconPicker.test.js` 重写，设计 §13.4）

- [x] 4.1 activator 点击 → dialog 渲染（stub 断言 `fullscreen` prop 不存在/为 false）；条目数 = CATEGORY_ICONS.length
- [x] 4.2 点选第 n 项 → emit 对应名、选中类切换、预览更新；「完成」→ 关闭且不再 emit
- [x] 4.3 宽/窄两档 `window.innerWidth`（mock）下渲染同一居中 dialog（`.icon-panel` 内联展开区零命中）
- [x] 4.4 非选集 modelValue 行为回归（提示 chip / 预览）
- [x] 4.5 `?raw` 断言：组件不含 `max-height: 240px`、不含 `fullscreen`

## 5. 验收与质量门槛

- [x] 5.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 5.2 手工自查：竖屏图标层为不超视口居中弹窗、网格占满弹窗、滚动可选全部图标；宽屏「新增分类」对话框尺寸不膨胀；选中保存后列表/表单预览正确；z 层级与关闭回焦；明暗主题
