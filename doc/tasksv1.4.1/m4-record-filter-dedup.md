# M4 - 账单页请求合并与筛选精简

> 对应需求七（点击月份多次刷新/闪烁 Bug）+ 需求八（筛选仅保留日期）。两项改动同一文件同一逻辑域，合并实施。
> 涉及文件：`frontend/src/pages/RecordListPage.vue`
> 依赖：排在 M3 之后（同文件串行，避免行号冲突）。

---

## 1. 筛选精简（需求八）

### 1.1 模板（现 :9-48）

- [x] 筛选卡片仅保留两个日期控件，竖屏两列一行：
  ```html
  <v-card class="pa-4 mb-3 filter-card" rounded="xl">
    <v-row dense>
      <v-col cols="6"><DatePickerPopover v-model="filters.start_date" label="开始日期" /></v-col>
      <v-col cols="6"><DatePickerPopover v-model="filters.end_date" label="结束日期" /></v-col>
    </v-row>
  </v-card>
  ```
- [x] 移除「类型」下拉与「分类」下拉控件

### 1.2 脚本停用项（前端移除；store 字段与后端能力保留不动）

- [x] 删除 `typeOptions`（:210-214）
- [x] 删除 `categoryOptions`（:216-224）
- [x] 删除 `categories` ref 与 `getCategories` 调用（含 import）
- [x] 删除 `filters.type` 变化清空 `category_id` 的 watch（:296-301）
- [x] 删除请求参数中 `type`/`category_id` 两行（:266-267）
- [x] **红线（易错点 11）**：`useRecordsStore.filters` 中 `type/category_id/tag_id/keyword` 字段（:21-28）原样保留；后端 `/api/records` 参数原样保留

## 2. 一次点击一次请求（需求七）

### 2.1 search 重构：同参去重 + 加载态分流

- [x] 新增状态：`const refreshing = ref(false)`（已有列表时的后台刷新标记）、`const pageNum = ref(1)`、模块级 `let lastQueryKey = ''`
- [x] 抽取 `buildQuery()`：`{ page: pageNum.value, page_size: 20 }` + 非空的 `start_date/end_date`
- [x] 重写 `search({ append = false, force = false } = {})`：
  - [x] `if (!append) pageNum.value = 1`
  - [x] `const key = JSON.stringify(params)`；`if (!force && key === lastQueryKey) return`（去重）
  - [x] 发请求前置 `lastQueryKey = key`
  - [x] 加载态分流：`append || records.value.length > 0` → `refreshing = true`；否则 `loading = true`
  - [x] `catch` 中 `lastQueryKey = ''`（失败后允许同参重试，易错点 2）
  - [x] `finally` 中同时复位 `loading`/`refreshing`
  - [x] 成功赋值：`records`（append 时追加）、`totalCount`、`hasMore`

### 2.2 分页修复（顺带，不扩大范围）

- [x] `loadMore()`：`pageNum.value += 1` 后 `await search({ append: true, force: true })`
  （现有 loadMore 固定重查 page 1 且整体替换，去重后会变 no-op，必须参数化页码）

### 2.3 调用入口收敛

- [x] `selectMonth()`（:230-238）：删除末尾显式 `search()`（:237），只负责写 `filters.start_date/end_date`
- [x] `onMounted`：`selectMonth()` 后显式调用一次 `search()`（filters 恰好同值时 watch 不触发；同参由去重合并为一次实际请求）
- [x] 防抖 watch 依赖数组仅保留 `[filters.start_date, filters.end_date]`（:285-293 收窄，300ms 防抖不变）

### 2.4 模板加载态（现 :112-115）

- [x] 有数据时顶部细进度条：`<v-progress-linear v-if="refreshing" indeterminate color="primary" height="2" rounded class="mb-2" />`
- [x] 首屏整块 spinner 条件：`v-if="loading && records.length === 0"`
- [x] 列表/空态渲染条件基于 `records.length`，`v-else-if` 链顺序保持现状（:112-126 调整入口条件）
- [x] 月份芯片高亮逻辑确认维持现状不修改（设计 §4.3）

## 3. 测试（vitest，RecordListPage.test.js 重写相关用例，mock `@/api/records`）

- [x] 用例 1：`selectMonth(m)` 后推进 300ms 定时器，`getRecords` 调用次数 === 1
- [x] 用例 2：onMounted 时 filters 已等于目标月区间 → 显式 search 与 watch 同参被去重 → 仅 1 次请求
- [x] 用例 3：修改 filters 两次且最终参数与上次相同 → 第 2 次不发请求
- [x] 用例 4：筛选卡片不再渲染"类型/分类"控件；请求 params 不含 `type/category_id`
- [x] 用例 5：`loadMore` → page 参数递增且 items 追加
- [x] 用例 6：请求失败后同参再次调用可重发

## 4. 手工验收

- [ ] 点击任意月份，DevTools Network 恰有一次 `/api/records` 请求
- [ ] 切换月份期间列表保留、顶部细进度条一闪，无整块"加载中↔内容"闪没
- [ ] 筛选区只剩开始/结束两个日期控件，布局无贴挤
- [ ] 修改日期筛选同样只触发一次请求
- [ ] 上拉/加载更多分页追加正常，不重复首屏数据

## 5. 质量门槛

- [x] `cd frontend && npm test && npm run lint && npm run build` 通过
