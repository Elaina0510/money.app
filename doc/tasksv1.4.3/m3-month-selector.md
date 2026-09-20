# M3 - 账单页月份条放大 + 选中月滚动居中 + 选中态失色修复（需求三）

> 对应需求三（设计 §三）。保持「年份箭头 + 当年 12 月 chip」结构不变，整体放大疏朗化；选中月自动平滑滚动到视口水平居中；修复往年选中月失色（去除 `selectedYear === currentYear` 限定）。
> 涉及文件：`frontend/src/pages/RecordListPage.vue`（月份条 :21-62 + script 滚动逻辑 + scoped 样式）。
> 依赖：无。**`.month-scroller` 类为 M11 overscroll 属性的挂载点**（本模块建类不含 overscroll，M11 在该类上追加）。与 M10 同文件不同区域，可并行。

---

## 1. 放大口径（设计 §3.2.1 / D10）

- [x] 1.1 chip `size`：`small`（32px）→ `default`（40px）；chip 加 `text-subtitle-2 font-weight-medium`（字号 14→16px）
- [x] 1.2 chip 外层包装器 `min-width`：48px → **64px**（保留内联或入类，同值）
- [x] 1.3 年份箭头：`size="x-small"` icon small → `size="small"` icon 20
- [x] 1.4 外层 v-card 内边距：`pa-2`（:21）→ `pa-3`
- [x] 1.5 明暗主题零定制：chip 全部走 Vuetify 语义色

## 2. `.month-scroller` 样式类收敛（设计 §3.2.2）

- [x] 2.1 新增 scoped 类 `.month-scroller`：`display: flex; flex-grow: 1; overflow-x: auto; gap: 8px; padding-bottom: 8px; scrollbar-width: none`
- [x] 2.2 滚动容器（:32）原「工具类 `d-flex ga-1 overflow-x-auto flex-grow-1 pb-1` + 内联 `scrollbar-width:none`」整体替换为该类（chip 水平间距 4→8px、滚动条留白随之收敛）
- [x] 2.3 ref 收集：`const chipRefs = ref([])`（`:ref="el => chipRefs[m - 1] = el"`）+ `const monthScroller = ref(null)` 绑容器

## 3. 选中月滚动居中（设计 §3.2.3）

- [x] 3.1 实现 `centerSelectedMonth({ smooth = true })`：`selectedMonth == null` 时 `scrollTo({ left: 0 })` 回卷左端；否则 `await nextTick()` 后 `left = chip.offsetLeft - (scroller.clientWidth - chip.offsetWidth) / 2`，`scrollTo({ left: Math.max(left, 0), behavior: smooth ? 'smooth' : 'auto' })`
- [x] 3.2 **红线**：不用 `scrollIntoView`（会连带垂直滚动祖先，打断 M11 滚动定位恢复与详情页返回现场滚动）——只用作用于月份条容器的 `scrollTo`
- [x] 3.3 触发点全覆盖（均 `await centerSelectedMonth()`）：`onMounted` 首屏（`smooth: false` 即时定位）；`selectMonth()`；`prevYear()` / `nextYear()`（含选中月为 null 回卷 1 月侧）；详情页返回现场恢复 `saved.month` 后
- [x] 3.4 跨年翻页后 offsetLeft 天然按目标年重排，由同一函数覆盖，无需额外分支
- [x] 3.5 宽屏内容不溢出时 `scrollTo` 无效即无动作，无需分支

## 4. 选中态失色修复（需求 3.4 / 设计 §3.2.4）

- [x] 4.1 :35 选中色条件删去 `&& selectedYear === currentYear`，仅 `selectedMonth === m` 即 `color="primary" variant="flat"`——任何年份选中月均高亮

## 5. 边界自检（设计 §3.3）

- [x] 5.1 首屏恢复现场为上一年某月：年份箭头出现、chip 组渲染、居中且高亮该月
- [x] 5.2 `selectedMonth=null`（翻年后）：条回卷左端显示 1 月侧；点任意 chip 恢复选中 + 居中
- [x] 5.3 连续快速点选两端月份：每次 `scrollTo smooth`，浏览器接管中段取消，无报错

## 6. 测试（设计 §3.4，jsdom 无布局 → 调用参数断言 + ?raw 组合）

- [x] 6.1 `RecordListPage.test.js` 扩展：mock `Element.prototype.scrollTo`；挂载后（`behavior:'auto'`）、`selectMonth(1)` 后、`prevYear()` 后均被调用（其余 `'smooth'`）
- [x] 6.2 chip DOM 数 12、文本 `1月…12月`
- [x] 6.3 `?raw` 断言：容器绑定 `month-scroller` 类；`.month-scroller` 样式含 `gap: 8px`、`scrollbar-width: none`；chip 包装器含 `min-width: 64px`
- [x] 6.4 `?raw` 断言：选中色表达式不含 `selectedYear === currentYear`
- [x] 6.5 既有用例回归通过（点月查询、年份箭头边界、返回现场恢复）

## 7. 验收与质量门槛

- [x] 7.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 7.2 手工自查（竖屏）：进账单页当前月 chip 水平居中且高亮；点第 1/12 月、点年份箭头后选中月均回中；往年选中月高亮正常；视觉比 v1.4.2 明显更大、更疏朗；明暗主题
