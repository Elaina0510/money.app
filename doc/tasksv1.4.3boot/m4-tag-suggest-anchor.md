# M4 - 标签建议浮层锚定输入框正下方（需求四）

> 对应需求四（设计 §四）。建议层现为 v-autocomplete 内部 VMenu teleport 到 body 的游离浮层，滚动/软键盘弹起时漂移。主方案（D5）= 保留控件 + wrap 容器 + `:menu-props` attach；预案 B（自绘层）仅真机三场景不达标且 CSS 不可救时切换。
> 涉及文件：`RecordFormPage.vue`（标签区模板 :127-155 加 wrap div + menuProps + scoped 样式追加）。RecordFormPage 串行：M2 → M3 → **M4**。
> 交接点（§4.2.2）：控件本体、v-model、搜索/选中/归一逻辑全部不动（M3 消费 script，M4 只加模板/样式）——两模块 diff 无交叉行。

---

## 1. 主方案：menuProps attach（设计 §4.2.1）

- [x] 1.1 模板：标签 `v-autocomplete` 外套 `<div ref="tagFieldAnchorRef" class="tag-field-anchor">`，控件加 `:menu-props="tagMenuProps"`，现有 props（含 `transition="fab-transition"` :132）不动（需求 4.4 全站口径，不引入新动画体系）
- [x] 1.2 script：`tagMenuProps = computed(() => ({ attach: tagFieldAnchorRef.value ?? false, maxHeight: 240, contentClass: 'tag-suggest-menu' }))`——ref 未挂载时回落 body 现状，降级无损（需求 4.3 内滚+最大高）

## 2. scoped 样式（设计 §4.2.1）

- [x] 2.1 `.tag-field-anchor { position: relative; }`
- [x] 2.2 `:deep(.tag-suggest-menu)` 三条：`left: 0 !important`、`width: 100% !important`、`border-radius: 12px; max-height: 240px; overflow-y: auto`——上缘紧贴由 connected 策略几何保证，宽度/水平对齐由 !important 锁死（需求 4.1「正下方、同宽、无游离间隙」）

## 3. 几何取证（实现首验，主方案三点判据）

<!-- 取证方式登记（P4）：子 Agent 工具面无 browser-use 类浏览器自动化（起 dev server + headless Edge 的实测路径被权限层拦阻），
     故 3.1 以「jsdom + 真实 Vuetify 组件挂载」取证并在用例 6.3 长期锁定：overlay 根节点确进 wrap 容器
     （`.tag-field-anchor .v-overlay-container .v-overlay--absolute` 命中）且 `.v-overlay__content` 带
     `tag-suggest-menu` 类、内联 `max-height: 240px`，内联 top/left 由 connected 策略写入（值本身无布局真值）。
     3.2/3.3 需真实布局 → 移交主 Agent 浏览器实测终判；任一不符且 CSS 不可救再走 §4。 -->

- [x] 3.1 DevTools 核验①：`.v-overlay` 根节点挂进 wrap 容器且带 `v-overlay--absolute` 类（本仓库取证=用例 6.3 真实 Vuetify 结构断言）
- [ ] 3.2 核验②：`.v-overlay__content` 内联 `top` 参照系是 wrap（容器内坐标而非视口坐标）——**移交主 Agent 浏览器实测**
- [ ] 3.3 核验③：!important 覆写后 computed `left:0` / `width = 输入框宽`——**移交主 Agent 浏览器实测**
- [ ] 3.4 三点任一不符 = 策略计算层问题（CSS 覆写不可救）→ 触发预案 B 判定（§4）——**待 3.2/3.3 实测后裁定**

## 4. 预案 B（仅主方案实测不可控时，设计 §4.2.3）

- [ ] 4.1 决策规则：主方案在真机（竖屏+软键盘、页面滚动、深色）三场景任一不达标且 CSS 不可救 → 切换；否则不做（真机三场景属人工项，见 §7）
- [ ] 4.2 若切换：控件换 `v-text-field`（显示值 script 维护：选中态显 selectedTagName 否则 tagSearchQuery）+ 自绘 `.tag-suggest-panel`（`position:absolute; top:100%; left:0; right:0; max-height:240px; overflow-y:auto; z-index:5`，v-list 建议项 + 空态槽，约 60 行含点选/清除/高亮/键盘导航）
- [ ] 4.3 切换后回写设计 §4.2 标注实际采用方案

## 5. 边界与异常（设计 §4.3）

- [ ] 5.1 页面滚动中浮层打开：attach 后代随容器位移保持吸附（需求 4.2）——**机制已具备（overlay 为容器 absolute 后代），吸附真值属人工/浏览器项**
- [x] 5.2 建议 25 条（后端上限）：maxHeight 240 内滚，列表项紧凑密度现状；贴底空间不足 connected 策略自动翻转上方（真机自查覆盖，需求 4.3 保存按钮可达）
- [ ] 5.3 软键盘弹起输入框上移：visualViewport resize 重算；失准即触发预案 B 判定——**人工/真机项**
- [x] 5.4 clearable ✕ 与浮层焦点：`closeOnContentClick` 默认行为保持，不新增 persistent（用例 6.5 源码锁）
- [x] 5.5 `no-data` 空态槽（:147-153「无匹配标签…」）在同一锚定层内展示（menu 内容整体承载，零改动，需求 4.4）——用例 6.4

## 6. 测试（设计 §4.4）

- [x] 6.1 vitest：mount 后 `menuProps.attach` === wrap 元素（ref 对象同一性）、`menuProps.maxHeight === 240`、`contentClass` 含 `tag-suggest-menu`
- [x] 6.2 `?raw` 断言：`.tag-field-anchor` 含 `position: relative`；覆写块含 `left: 0 !important` 与 `width: 100% !important`；`transition="fab-transition"` 保留（不引入新动画体系红线）
- [x] 6.3 vitest：输入触发搜索 → `.tag-field-anchor .v-overlay__content` 存在（jsdom teleport-to-element 生效）
- [x] 6.4 vitest：`.tag-field-anchor` 子树含「无匹配标签」文案（no-data 在锚定层内）
- [x] 6.5 回归红线：M3 既有用例全量保持通过（控件逻辑零改动）
- [x] 6.6 `RecordFormPage.test.js` 只增「标签建议层锚定」组
- [x] 6.7 **M3+M4 联合验收链路用例**（D9）：a) 输入 → 锚定建议层出现 → 点选 → 保存；b) 输入 → 免回车直接保存

## 7. 验收门槛（人工自查为锚定验收主体）

- [x] 7.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 7.2 人工·真机竖屏：输入时建议层紧贴输入框正下方、同宽；选中后表单布局无跳动（需求验收）
- [ ] 7.3 人工：打开建议层后滚动页面，层与输入框保持吸附
- [ ] 7.4 人工：软键盘弹起不脱节；建议多条内滚、不挡保存按钮
- [ ] 7.5 人工：展开动画与站内其他浮层观感一致（§十四 口径）；深浅主题
