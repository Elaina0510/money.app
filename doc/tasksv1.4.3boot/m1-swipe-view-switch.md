# M1 - 主页总收支大卡左右横滑切换（需求一）

> 对应需求一（设计 §一）。大数字区域支持左右横滑切换视图（滑动动作完成后才转换），点击循环切换保留，滑动与点击互不误判。
> 涉及文件：`DashboardPage.vue`（点按区 :25-52 + script 手势逻辑）。与 M6 同文件不同区域（M6 改 :78/:87/:119/:166 金额节点），可并行。
> 依赖：无。手势隔离红线：不触碰 `global.scss`（v1.4.3 §十一 overscroll 修复零改动）。

---

## 1. 视图步进统一（设计 §1.2.1，D2 方向映射）

- [x] 1.1 script 新增 `prevView` 反向映射（`{ expense:'income', balance:'expense', income:'balance' }`），`views`/`nextView` 现值（:194-201）不动
- [x] 1.2 新增 `stepView(dir)`：`dir>0` 走 nextView（左滑=前进），`dir<0` 走 prevView（右滑=后退）；循环顺序维持 支出→结余→收入→支出
- [x] 1.3 `cycleView()` 改为：`if (Date.now() < suppressClickUntil.value) return; stepView(1)`（点击=前进，窗口内吞掉）
- [x] 1.4 确认指示点（:44-51）与 `amount-switch` 动画（:31-43）绑定 `view` 不变——滑动与点击共用同一状态源天然联动；小字明细行不随视图变化

## 2. 手势监听（设计 §1.2.2，D1/D2 原生 Pointer Events）

- [x] 2.1 script 新增 `SWIPE_THRESHOLD = 48`、`drag = { active, x0, y0 }`、`suppressClickUntil = ref(0)`
- [x] 2.2 `onPointerDown(e)`：mouse 非左键直接 return；记录起点坐标；向 **window** 挂 `pointerup`/`pointercancel` 监听
- [x] 2.3 `onPointerUp(e)`：终点取 pointerup 自身坐标算 dx/dy；**仅当** `|dx| > 48 && |dx| > |dy|` 时 `stepView(dx<0 ? 1 : -1)` 并置 `suppressClickUntil = Date.now() + 350`；随后统一走 `onDragAbort()`
- [x] 2.4 `onDragAbort()`：复位 active + 移除两个 window 监听（幂等）；`onBeforeUnmount(onDragAbort)` 卸载清理（需求通用约束·性能）
- [x] 2.5 **不挂 pointermove**、全程**零 preventDefault**（拖动过程零采样零视觉反馈；不阻断 click 链与键盘 Enter→cycleView 路径）——实现红线
- [x] 2.6 模板 :25-29 点按区追加 `@pointerdown="onPointerDown"`（`@click="cycleView"` 保留）
- [x] 2.7 样式追加 `.overview-cycle-area { touch-action: pan-y; }`（纵向滚动交还原生，横滑归 JS；纵向手势被接管后收到 pointercancel 不误判）

## 3. 手势隔离复查（设计 §1.2.3）

- [x] 3.1 右上「跳统计」按钮（:10-21，`@click.stop`）不在点按区内，pointer 链无交叉——核验
- [x] 3.2 v1.4.3 §十一 修复零改动（本模块不触碰 global.scss；主页无横向滚动容器）——核验

## 4. 边界与异常（设计 §1.3，以代码走查 + 用例覆盖）

- [x] 4.1 轻拖 <48px 松手 → 不切换，click 正常走点击循环
- [x] 4.2 斜向滑（|dx| ≤ |dy|）→ 不判滑动
- [x] 4.3 滑动后尾巴 click → 350ms 窗口吞掉，不双跳
- [x] 4.4 pointerup 丢失（滚动/切换致 pointercancel）→ 清理；下次 pointerdown 前监听不残留（onDragAbort 幂等）
- [x] 4.5 summary 加载中滑动/点击 → 视图照常切换，数值 `|| 0` 兜底（现状行为）
- [x] 4.6 快速连续滑动 → 每次 pointerup 恰一步，`mode="out-in"` 末态=最后一次 view

## 5. 测试（设计 §1.4）

- [x] 5.1 vitest：滑动前进（dispatch pointerdown/pointerup，dx=−60）→ 支出→结余一步且仅一步。**合成事件红线**：up/cancel 挂 window，必须 `new MouseEvent('pointerup', { bubbles: true, clientX, clientY })`（jsdom 无 PointerEvent 构造器，漏 bubbles 静默收不到）
- [x] 5.2 vitest：滑动后退 dx=+60 → 支出→收入（prevView）
- [x] 5.3 vitest：未达阈值 dx=+30 → 不变；斜向 dx=60/dy=90 → 不变
- [x] 5.4 vitest：纯 `trigger('click')` 前进一位——既有点击循环用例保留为回归基线
- [x] 5.5 vitest：滑动后紧接 click → 只切一次（fake timers 控制 suppressClickUntil 窗口）
- [x] 5.6 `?raw` 断言：`touch-action: pan-y`、`SWIPE_THRESHOLD = 48`、`onBeforeUnmount(onDragAbort)` 在场；手势相关代码不含 `preventDefault`

## 6. 验收门槛

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 6.2 人工·真机竖屏：左右横滑大数字区，松手瞬间恰切一次、无中途蹦数、无一滑多跳；轻点仍可循环；上下滑页面不受影响
- [ ] 6.3 人工·宽屏鼠标：按住横拖达标；快速连续滑动无动画错位
- [ ] 6.4 人工：明暗主题抽查（纯交互零色改）；指示点随视图同步高亮；不回退 v1.4.3 §十一/§十四 项
