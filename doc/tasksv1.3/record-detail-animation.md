# 模块 3：账单详情展开动画

> **优先级：** 中 | **复杂度：** 中 | **涉及文件：** `useAppStore.js`, `AppLayout.vue`, `RecordListPage.vue`, `RecordDetailPage.vue`, `global.scss`

## 子任务

### useAppStore 扩展

- [ ] 3.1 在 `useAppStore.js` 中新增 `transitionOrigin` ref 和 `setTransitionOrigin()` 方法

### RecordListPage.vue 传递坐标

- [ ] 3.2 修改 `goToDetail(event, id)`：通过 `getBoundingClientRect()` 获取条目中心坐标
- [ ] 3.3 调用 `appStore.setTransitionOrigin({x, y})` 后再 `router.push`

### AppLayout.vue 自定义路由过渡

- [ ] 3.4 实现 `getTransitionName(route)`：`/detail/*` 且有 origin 时返回 `'expand'`，否则 `'page'`
- [ ] 3.5 实现 `onBeforeEnter(el)`：设置 `transformOrigin`、`transform: scale(0)`、`opacity: 0`
- [ ] 3.6 实现 `onEnter(el, done)`：强制 reflow → 设置 transition → `scale(1)` + `opacity(1)` → `transitionend` done
- [ ] 3.7 实现 `onLeave(el, done)`：`scale(0.9)` + `opacity(0)` → `transitionend` 清除 origin + done
- [ ] 3.8 将 `<router-view>` 的 `<transition>` 改为动态 `:name` + JS 钩子 + `mode="out-in"`

### RecordDetailPage.vue 返回处理

- [ ] 3.9 在详情页返回按钮中调用 `appStore.setTransitionOrigin(null)` 后 `router.back()`

### global.scss（可选）

- [ ] 3.10 新增 `.expand-enter-active` / `.expand-leave-active` CSS 类（备用，主要靠 JS 钩子）

## 验收测试

- [ ] 账单列表点击条目 → 从条目位置展开至详情页
- [ ] 详情页点返回 → 使用默认过渡回到列表
- [ ] 直接访问 `/detail/:id`（非从列表跳转）→ 使用默认 page 过渡
- [ ] 动画流畅无卡顿
