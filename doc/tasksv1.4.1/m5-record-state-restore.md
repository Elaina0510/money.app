# M5 - 账单详情返回状态记忆

> 对应需求三：从账单详情返回时恢复年月、滚动位置与筛选状态；主动重新进入账单页仍定位当前月。
> 方案：浏览现场提升到 `useRecordsStore`（内存级），一次性消费语义。
> 涉及文件：`frontend/src/stores/useRecordsStore.js`、`frontend/src/pages/RecordListPage.vue`、`frontend/src/components/layout/AppLayout.vue`（handleLogout）
> 依赖：排在 M3、M4 之后——恢复路径依赖 M3 的 selectedYear 边界与 M4 收敛后的 search 入口（去重机制）。

---

## 1. useRecordsStore.js：现场存取

- [x] 新增 `const listView = ref(null)`，形状 `{ year: number, month: number|null, scrollTop: number } | null`
- [x] 新增 `rememberListView(state)`：`listView.value = { ...state }`
- [x] 新增 `consumeListView()`：取出后置 `listView.value = null` 再返回（一次性消费，易错点 4）
- [x] 新增 `resetListView()`：置 null
- [x] 三者随 store 一并 return 导出
- [x] **红线**：`filters` 字段结构不动（仅复用其全局保留能力）

## 2. RecordListPage.vue：保存点

- [x] `goToDetail(event, id)` 中，在现有 `appStore.setTransitionOrigin({x, y})` 之后、`router.push` 之前追加：
  ```javascript
  recordsStore.rememberListView({
    year: selectedYear.value,
    month: selectedMonth.value,
    scrollTop: window.scrollY,
  })
  ```
- [x] 保存点只挂 `goToDetail`，**不用** `onBeforeUnmount`（避免跳去记一笔/编辑/切底栏离开时也记住现场）

## 3. RecordListPage.vue：恢复点（onMounted）

- [x] 改造 `onMounted`（M3/M4 完成后的形态）：
  ```javascript
  onMounted(async () => {
    loadEarliestYear()                                  // M3
    const saved = recordsStore.consumeListView()
    if (saved) {
      selectedYear.value = saved.year
      selectedMonth.value = saved.month
      // filters 已由 store 全局保留，不重置、不重写 → 不触发 M4 的 watch
      await search()                                    // 唯一一次请求；同参由 M4 去重兜底
      await nextTick()
      requestAnimationFrame(() => window.scrollTo({ top: saved.scrollTop }))
    } else {
      selectMonth(new Date().getMonth() + 1)            // 现有默认路径
      await search()
    }
  })
  ```
- [x] **易错点 3**：恢复路径不得重写 `filters`（重写会造成双请求或"闪回当前月"，属回归缺陷）
- [x] 滚动恢复在 `nextTick` + 一帧 `rAF` 后执行（列表未撑开时 scrollTo 会被钳制）
- [x] 确认 import `nextTick`

## 4. AppLayout.vue：登出清理

- [x] `handleLogout()`（:215-221）追加 `useRecordsStore().resetListView()`，避免切换账号后返回现场串号
- [x] 确认 AppLayout 已引入 `useRecordsStore`（未引入则补 import）

## 5. 测试

### 5.1 vitest（RecordListPage.test.js + useRecordsStore 用例）

- [x] 用例 1：`rememberListView` 后重挂载组件 → `selectedYear/selectedMonth` 恢复为存值；`getRecords` 仅一次且参数为离开时日期区间；filters 未被重写
- [x] 用例 2：恢复后再次 mount（listView 已 null）→ 回到当前月默认逻辑
- [x] 用例 3：`consumeListView` 幂等——第二次调用返回 null
- [x] 用例 4：`goToDetail` 写入的快照字段完整（含 scrollTop）
- [x] 用例 5：`resetListView` 清空

### 5.2 边界场景核查（设计 §5.3）

- [x] 详情页删除账单 → `router.push('/records')`：仍恢复原年月与滚动，消费后清空
- [x] 详情页编辑 → 返回：恢复现场，列表数据为最新
- [x] 现场月份数据被批量删除清空：显示既有空态卡片，不报错
- [x] F5 刷新应用：回到当前月默认（内存级状态自然消失）
- [x] 滚动位置超出新数据列表高度：浏览器自动钳制，不报错

## 6. 手工验收

- [ ] 翻到 3 月、滚动到列表中部、点开任一详情、返回：仍是 3 月、滚动位置不变、筛选条件不变、无回跳当前月的闪动
- [ ] 返回后再点底栏「账单」重新进入：定位当前月（现场已被消费）
- [ ] 登录 → 登出 → 换账号登录 → 进入账单页：默认当前月，无串号

## 7. 质量门槛

- [x] `cd frontend && npm test && npm run lint && npm run build` 通过
