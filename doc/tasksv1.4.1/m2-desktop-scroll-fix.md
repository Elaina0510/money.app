# M2 - 宽屏首次滚动卡顿修复

> 对应需求四（Bug 修复）：宽屏（≥960px）进入页面后首次向下滚动卡住，需反向滚动"唤醒"。
> 根因：`.content-wrapper` 的 `transform: scale(1.1)` 只改视觉不改布局高度，scrollHeight 失真（决策 D3：改用 `zoom: 1.1`）。
> 涉及文件：`frontend/src/components/layout/AppLayout.vue`（仅 `<style>` 中 `@media (min-width: 960px)` 区段）
> 依赖：无。与 M1 同文件不同区域，可并行；合并时互相确认登录页 `zoom: 1 !important` 豁免生效。

---

## 1. 样式修复

### 1.1 替换宽屏媒体查询（现 :489-495）

- [x] 删除 `transform: scale(1.1);` 与 `transform-origin: top center;`
- [x] 改为 `zoom: 1.1;`
- [x] `padding-bottom` 从 `calc(100px * 1.1)` 改回 `100px`（zoom 会把 padding 计入布局，无需手动乘系数）
- [x] 仅改 `@media (min-width: 960px)` 内规则——竖屏无 transform/zoom 逻辑，勿全局加 zoom（易错点 5）

### 1.2 联动确认（不改代码，只验证）

- [x] 确认 M1 的 `.content-wrapper--bare { zoom: 1 !important }` 使登录页豁免宽屏缩放
- [x] 确认 `.content-overflow { overflow-x: hidden }` 保留（窄宽屏 960px 附近横向裁剪）
- [x] 全局 grep `transform: scale` 确认 `.content-wrapper` 内无残留（合法残留：`.fab-add:hover` 的 scale(1.05) 与详情页/ExpandTransition 动画，均不在内容区，勿动）

## 2. 连带核查（设计 §2.3，均为确认项）

- [ ] 110% 缩放视觉与改前等比一致（zoom 语义验证，Chrome/Edge/Firefox 126+）
- [x] 详情页圆形展开动画：`AppLayout.onBeforeEnter/onEnter`（:301-329）与 `ExpandTransition.calcOrigin` 基于 `getBoundingClientRect`/`clientX/Y`，zoom 下语义不变；v-dialog teleport 到 body 不在 zoom 上下文内
- [ ] 底部渐变遮罩 `.content-wrapper::after`（:403-414）：fixed 恢复相对视口语义，位置表现正常
- [x] 顶栏 sticky：顶栏在 `.content-wrapper` 之外，不受影响
- [x] FAB/底栏：fixed 定位在 zoom 容器之外，不受影响

## 3. 测试

> zoom 的滚动行为无法用 jsdom 有效断言，以真机手工验收为准（设计 §2.4）。

- [ ] 宽屏 1200px 档：冷启动依次进入首页、账单、统计、设置、详情、记账页，每页进入后**立即向下滚动**，无卡顿、无需反向唤醒
- [ ] 宽屏 960px 临界档：重复上述验证
- [ ] 滚动到底部：最后一张卡片完整可见（scrollHeight 真实）
- [ ] 回归：顶栏 sticky、底部渐变遮罩位置、详情页圆形展开/收起动画、110% 视觉与改前一致
- [ ] 窄屏（<960px）不出现横向滚动条
- [ ] 反复切换各页面多次，每次进入首次下滚均顺畅

### 3.1 自动化用例（补充记录，不替代上述真机验收）

新增 `frontend/src/components/layout/AppLayout.wideScreenZoom.test.js`（M2-T1~T11）：
样式类断言以解析 `AppLayout.vue` `<style>` 源码规则实现（`zoom: 1.1` 命中宽屏媒体查询、`transform`/`transform-origin`/`calc(100px * 1.1)` 无残留、竖屏与基础规则无 zoom、登录页 `zoom: 1 !important` 豁免与 `.content-overflow` 裁剪保留、`.fab-add:hover` 等合法残留未动），
结构类断言以挂载渲染实现（顶栏/FAB 在缩放容器之外、豁免类按路由挂载、`onBeforeEnter` 坐标仍按 `getBoundingClientRect` 换算）。

## 4. 质量门槛

- [ ] `cd frontend && npm test` 通过（无新增用例，防回归）
- [x] `npm run build` 构建无报错
