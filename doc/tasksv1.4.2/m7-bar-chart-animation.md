# M7 - 统计页分类柱状图过渡动画

> 对应需求七（设计 §七）。分类统计柱状图数值/坐标轴平滑过渡（切月、切年、下钻、翻期全覆盖）；canvas 常驻消除空↔非空挂载闪白。沿用 Chart.js，不引入新库。
> 涉及文件：`frontend/src/pages/StatisticsPage.vue`、`StatisticsPage.test.js`。
> 依赖：无（第 1 梯队可并行）。与 M8 同文件但区域隔离（图表卡 :75-106 vs 预算卡头 :128-130）。

---

## 1. 动画配置（§7.2.1）

- [x] 1.1 定义 `const CHART_ANIMATION = { duration: 750, easing: 'easeOutQuart' }`
- [x] 1.2 `barChartOptions`（:422-442）补 `animation: CHART_ANIMATION` + `transitions: { active: CHART_ANIMATION }`；scales/plugins 现状保留
- [x] 1.3 确认机制无需手动 `chart.update()`：vue-chartjs v5 对 data/options prop 变化自动 update，切月/切年/下钻/翻期共用 `loadData → refs → computed` 单一入口，配置一次全覆盖
- [x] 1.4 **轴向事实核定记录**：现状 `<Bar>` 未配 `indexAxis`，实为竖直柱状图，数值轴是 **y**（beginAtZero 所在轴）；本模块不翻转图表方向，「坐标轴同步过渡」落在 y 轴刻度渐变，验收按此口径

## 2. 消除挂载跳变（§7.2.2 覆盖层方案）

- [x] 2.1 图表卡模板改造：`<Bar>` 外层去掉 `v-if`（现 :81-87），canvas 永不卸载；外层 `.chart-holder`（`position:relative; height:200px; margin-bottom:12px`）
- [x] 2.2 空态改覆盖层：`<div v-if="categoryStats.length === 0" class="chart-empty-overlay">暂无数据</div>`
- [x] 2.3 `.chart-empty-overlay { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background: rgb(var(--v-theme-surface)); }`（明/暗均 surface 底）
- [x] 2.4 空数据时 `categoryBarData = { labels: [], datasets: [{ data: [] }] }`：柱条按动画缩到 0、canvas 保持挂载
- [x] 2.5 下方明细列表（:88-104）非动画元素，`v-if="categoryStats.length"` 保留

## 3. 数据流防闪 0（§7.2.3）

- [x] 3.1 `loadData()`（:699-715）保持赋值式更新——**禁止**pending 期间先置空 `categoryStats`（易错点 8：置空会把过渡起点变 0、动画语义失效）
- [x] 3.2 `prevPeriod/nextPeriod/switchPeriod/drillDownToMonth`（:693-731）确认无需改动（动画收益来自配置层）

## 4. 边界自查（§7.3）

- [x] 4.1 动画期间再次切期：Chart.js update 自当前显示值起过渡新值，不报错不卡死（无手工 rAF 队列）
- [x] 4.2 分类集合变化（6 项→3 项）：按索引重映射，数量差即时消化、保留项数值平滑（接受该视觉折衷）
- [x] 4.3 月↔年视图切换：labels 整体替换，柱条与坐标轴同配变化
- [x] 4.4 收支趋势 Line 图不改；动画配置仅 `barChartOptions` 局部，无全局污染

## 5. 测试（`StatisticsPage.test.js`，Bar 已是 stub）

- [x] 5.1 配置断言：传入 Bar 的 `options.animation` 深度等于 `{duration: 750, easing: 'easeOutQuart'}`
- [x] 5.2 空态回归：mock `getByCategory` 返回 `[]` → `.chart-stub` 仍渲染（容器存在）+ `.chart-empty-overlay` 出现；切非空 → overlay 消失、chart 组件实例持续未重建
- [x] 5.3 `categoryBarData`：`categoryStats` 替换后 labels/data 同步，`getByCategory` resolve 前 data 保持旧值（无中间置空）

## 6. 验收与质量门槛

- [x] 6.1 `npm test`、`npm run lint` 通过
- [ ] 6.2 手工验收：8 月（有数据）↔9 月（全 0）来回切换，柱条与 y 轴刻度明显渐变、无瞬间跳变、无 canvas 闪白
- [ ] 6.3 切年视图、预算行下钻、前后翻期同等过渡；动画期间连续快切无报错不卡死
- [ ] 6.4 375px 真机走查帧率观感（单数据集 ≤15 柱条 750ms）
