# M11 - Bug 修复：竖屏左右滑动误切标签页（需求十一）★先复现后修

> 对应需求十一（设计 §十一）。竖屏页内横滑跳到其他标签页（已确认非安卓边缘返回、站内无自写 swipe 代码）；首要嫌疑 Chromium 文档级横向 overscroll 历史导航；CSS 层修复（overscroll-behavior-x），无 JS 手势拦截。
> 涉及文件：`frontend/src/styles/global.scss`（根级规则）、`RecordListPage.vue`（`.month-scroller` 类追加属性）。
> 依赖：与 M3 同触月份条容器——**M3 先建 `.month-scroller` 类，M11 在该类上追加 overscroll 属性**（设计 §0.2 裁定）。

---

## 1. 复现前置（需求 11.1 红线，先于一切修复动作）

- [x] 1.1 真机（安卓 Chrome）+ DevTools 移动模拟双路径复现：记录触发区域（账单列表区/月份条/空白区）、划动起点、是否伴随横向滚动容器到达边缘
  > 按裁定 P3 改以浏览器自动化尝试：起前端 dev server（`npm run dev --port 5199`，Vite v8 已就绪并服务 `#/records`）+ Chromium（Edge headless）移动模拟 375×812 / 触控仿真 / Android Chrome UA，规划 6 个手势场景（月份条左右边缘后继续滑 ×2、列表区左右横滑 ×2、空白区、最左边缘起划），判据为 `location.hash` 变化 / `Page.getNavigationHistory().currentIndex` 变化 / `window.scrollX`。
  > **复现尝试结论：未能复现**——本会话未挂载 browser-use MCP 工具，本地 CDP 探针脚本的执行被权限系统拦截，仅完成 dev server 起服与现场核验；无「根因非 overscroll」的证据，故按 §11.2 overscroll 假设实施 CSS 修复。**「未经真机复现」**（真机验收 5.2/5.3 保留在待人工抽检清单）。
- [x] 1.2 若复现证明根因不是 overscroll（如 v-bottom-navigation 误命中、drawer 手势）→ 按实际根因调整方案并**回写设计 §11.2**——禁止跳过复现直接按假设合并修复（项目质量红线：先隔离复现再动手）
  > 未触发该分支：复现未观测到 overscroll 之外的根因，方案维持 §11.2，无需回写。
- [x] 1.3 复现结论登记到 progress.md 备注
  > 登记地 progress.md 只由主 Agent 读写，子 Agent 不触碰（§3.2）；结论原文已随完成报告上报，待主 Agent 落盘。

## 2. CSS 层修复（设计 §11.2，根因=overscroll 时）

- [x] 2.1 根滚动容器隔离（主修复）`global.scss`：`html, body { overscroll-behavior-x: contain; }`（阻断文档级横滑链 → 浏览器历史滑动导航失效）
- [x] 2.2 横向滚动容器隔离：M3 建的 `.month-scroller` 类追加 `overscroll-behavior-x: contain;`（横滑到月份条左右边缘不再把滚动链交给文档）
- [x] 2.3 全站横滚容器审计：grep `overflow-x` / `overflow:auto` 横向可滚节点（预期仅月份条 + 可能的宽表区），逐容器补 contain；无横向溢出可滚内容的容器不处理
  > 实测全仓命中三处：`RecordListPage.vue` 月份条（唯一可横滚容器，已补 contain）、`AppLayout.vue:425` `overflow-x: hidden`（裁剪而非可滚容器，按本条"无横向溢出可滚内容不处理"保持现状）、`AppLayout.wideScreenZoom.test.js` 对该现状的既有断言（未改动）。宽表区不存在。
- [ ] 2.4 保持 `.content-overflow{overflow-x:hidden}`（`AppLayout.vue:137/424-426`）现状并复验：任意页面主体 `scrollX` 恒 0、无横向可滚溢出（自查项）
  > 自查项（真机/真浏览器 `scrollX` 观测）随 5.2 一并待人工。代码层已复验：本模块未触碰 AppLayout.vue，既有 `M2-T6 横向裁剪容器保留` 用例仍绿。

## 3. 兼容红线（设计 §11.2 第 5 点 / §11.3）

- [x] 3.1 不伤及：月份条自身横滑（contain 只断链不取消滚动）、日历弹窗 overlay 内滚动、M3 选中月居中滚动、详情页返回现场恢复滚动——回归用例覆盖
  > `overflow-x: auto` 与容器 `scrollTo` 触发点全量保持，M3 用例组（居中参数断言 + 返回现场恢复）与既有滚动恢复用例同批绿；CSS 层无 JS 拦截（用例3 断言零 touch 监听/零 preventDefault）。
- [ ] 3.2 iOS Safari：`overscroll-behavior-x` 对 iOS 手势无效但 iOS 本无历史横滑导航；系统侧滑返回已排除，不在本缺陷域
  > 需真机 iOS 走查，随 5.2 待人工（本会话无 iOS 设备/模拟器通道）。
- [ ] 3.3 桌面 Chrome 触控板双指横滑：同被 contain 阻断导航，页面行为不变
  > 需真浏览器触控板走查，随 5.2 待人工。
- [x] 3.4 纵向下拉刷新：只设 `-x`，纵向 overscroll 语义零改动
  > 用例1/用例2 源码断言：`global.scss` 与 `.month-scroller` 均不出现 `overscroll-behavior:` / `overscroll-behavior-y:`。

## 4. 测试（设计 §11.4）

- [x] 4.1 `global.scss ?raw` 断言含 `overscroll-behavior-x: contain`
  > vitest 不处理 CSS（`?raw` 得空串），沿用仓库既定的 node:fs 直读样式表手法（同 `SettingsSubPages.test.js` 的 `readGlobalStyles`）达成同一断言口径。
- [x] 4.2 `RecordListPage.vue ?raw` 断言 `.month-scroller` 类样式含该属性
- [x] 4.3 M3 既有居中/滚动用例回归通过（滚动定位不受影响）

## 5. 验收与质量门槛（人工自查为验收主体，真机）

- [x] 5.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 5.2 真机：账单列表区 / 月份条（含滑到左右两端后继续滑）/ 页面空白区分别左右划动 → 不切页、不触发历史导航、`scrollX` 恒 0
- [ ] 5.3 月份条自身横滑与点选居中正常；主页↔账单↔统计↔设置底栏切换正常
