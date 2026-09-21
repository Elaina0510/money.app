# M2 - Bug 修复（阻断级）：记一笔分类恒久空白 + 加载解耦 + 空态兜底（需求二）★先复现后修

> 对应需求二（设计 §二）。记一笔页分类九宫格恒久空白 → categoryId 恒 null → 无法保存账单。三候选根因（A 联动失败 / B 迁移缺失 / C 后端异常 / D 空列表），先复现取证再对症修；**解耦与兜底改造无论根因为何都实施**（D3）。
> 涉及文件：`RecordFormPage.vue`（onMounted :448-486 + 分类卡模板 :66-108）。RecordFormPage 三模块串行：**M2 → M3 → M4**。
> 红线：先隔离复现再碰真实数据；取证期间对现场库一切只读；如需动库先备份。

---

## 1. 复现与根因判定（设计 §2.2.0，执行前置，不得跳过）

- [x] 1.1 步骤①：DevTools Network 进记一笔页，记录 `/api/categories`、`/api/quick-templates` 状态码与响应体——quick-templates 失败且 categories 成功 → **根因 A（联动失败）**
- [x] 1.2 步骤②：categories 500 → 查后端日志栈——表结构类错误（no such column/constraint）→ **根因 B（迁移缺失）**，走 §6 发布窗口程序不改代码；业务异常 → **根因 C（后端缺陷）**，pytest 最小复现用例后修后端（mypy 基线零新增）
- [x] 1.3 步骤③：categories 200 且 `data: []` → **根因 D（可见集合为空）**：走 §3 空态兜底 + 设置页恢复预设既有链路；判定预设 seed 缺失则同时修 `init_preset_data` 触发条件
- [x] 1.4 步骤④：现场 dist 版本核对（index.html 引用 hash vs 仓库重建产物）——过旧则重建部署（终验统一重建口径）
- [ ] 1.5 复现结论登记 progress.md 备注（主 Agent 落盘）；若根因非 A 且代码修改范围扩大 → 回写设计 §2.2.0 ※本项归主 Agent（子 Agent 禁触碰 progress.md），结论已随 M2 完成报告 notes 移交

## 2. 加载解耦（设计 §2.2.1，script 重构，无论根因都实施）

- [x] 2.1 新增 `categoriesLoading = ref(true)`、`categoriesError = ref(false)` 独立状态
- [x] 2.2 拆出 `loadCategories()`：独立 try/catch/finally；默认分类选中带 `categoryId.value === null` 守卫（编辑回填竞态安全，写在默认选中时刻而非 onMounted 末尾）；失败置 `categories=[]` + `categoriesError=true`
- [x] 2.3 拆出 `loadTemplates()`：失败只清 `templates=[]`（模板卡 `v-if="templates.length"` 自然隐藏），不牵连分类
- [x] 2.4 拆出 `loadRecordForEdit()`：现 :460-480 逻辑原样搬入自带 try/catch；失败 toast「账单加载失败」不空白表单
- [x] 2.5 `onMounted` 改 `Promise.allSettled([loadCategories(), loadTemplates(), (isEdit? loadRecordForEdit())])`，`initialSnapshot = takeSnapshot()` **恒定落定**（消解 :482 快照被联动失败废掉、dirty 追踪失效的第三处连坐）
- [x] 2.6 新增 `retryLoadCategories()` 包装：`await loadCategories()` 后若 `!categoriesError` 则重取 `initialSnapshot`——系统补选默认分类并入基线，isDirty 不因重试翻真
- [x] 2.7 模板 :260-262 `canSubmit` 不动（分类为空自然禁存）
- [x] 2.8 回归红线：既有测试消费的公开名与类名不改——`currentCategories`（`RecordFormPage.test.js` M8 组 :228-243 经 `wrapper.vm.currentCategories` 消费）、`.category-chip`/`.active-category` 类名、`onTagSearch`/`tagSearchResults`/`tagSearching`（标签搜索组 :189-208 消费）；解耦重构只动加载编排，误伤即红灯

## 3. 分类卡三态 UI（设计 §2.2.2，模板 :66-108 改造）

- [x] 3.1 加载态：`v-if="categoriesLoading"` → `v-progress-circular` 居中（color primary size 28）
- [x] 3.2 错误态：`v-else-if="categoriesError"` → `mdi-alert-circle-outline`(error 40px) + 「分类加载失败，请检查网络后重试」+ 重试按钮绑 `retryLoadCategories`（需求 2.2：可见错误提示 + 重试入口，不再静默留白）
- [x] 3.3 空态：`v-else-if="categories.length === 0"` → `mdi-shape-outline`(grey 40px) + 「暂无分类，请先到 设置 → 分类管理 添加分类」（需求 2.3：不得渲染无信息空白）
- [x] 3.4 正常态：`v-else` 现有九宫格 v-row 原样；分支顺序错误态在空态之前
- [x] 3.5 三态块纯居中排布（`.category-state` 类），cols="3" 响应式不动，明暗主题文案可读

## 4. 边界与异常（设计 §2.3，走查 + 用例覆盖）

- [x] 4.1 分类成功 + 模板 500：九宫格完整、模板卡隐藏、无 toast（静默降级既有设计）
- [x] 4.2 分类 500 + 模板成功：错误态+重试；保存按钮因 categoryId null 禁用
- [x] 4.3 两路全失败：各自状态独立成立
- [x] 4.4 编辑态分类失败、记录成功：categoryId 非 null 可保存（更新不依赖列表展示）
- [x] 4.5 竞态：categories 慢 resolve + getRecord 快 resolve → 终态 categoryId===record.category_id
- [x] 4.6 重试多次幂等；loading 期重试按钮不可见（分支互斥）
- [x] 4.7 401 走 request.js 全局登出链路，不在本页处理

## 5. 测试（设计 §2.4）

- [x] 5.1 vitest：模板 reject + 分类正常 → 九宫格全量、默认选中、模板卡不渲染、无错误态
- [x] 5.2 vitest：分类 reject → 错误文案+重试按钮在场；点重试转成功 → 分类渲染+默认选中+**isDirty===false**
- [x] 5.3 vitest：分类 resolve `[]` → 空态引导文案渲染
- [x] 5.4 vitest：分类 resolve 后 initialSnapshot 已落定（改任意字段 isDirty===true——锁死 :482 联动缺陷不复发）
- [x] 5.5 vitest：编辑态 getRecord reject → 分类仍完整渲染
- [x] 5.6 vitest：竞态用例（同 4.5）
- [x] 5.7 `?raw` 红线：`Promise.all([getCategories` 零命中（解耦完成判据）；`Promise.allSettled` 在场
- [x] 5.8 `RecordFormPage.test.js` 只增「加载解耦与三态」组，M3/M4 组不触碰

## 6. 验收与发布联动

- [x] 6.1 `npm test` 全绿；`npm run lint`；若触后端：pytest + mypy 基线零新增
- [ ] 6.2 人工·当前环境重建部署：进记一笔页九宫格完整展示全部共用品类；选分类+输金额可正常保存账单（需求验收 1；含根因 B/D 时先走附录 A）
- [ ] 6.3 人工·DevTools 网络面板模拟两接口分别断网/500 复核两分支表现
- [ ] 6.4 人工·明暗主题下错误/空态配色可读
- [ ] 6.5 根因 B 落地时：发布备忘登记——发布窗口执行 `backend/migrate_to_v1.4.3.py`（停服→备份 money.db→跑脚本核对 [OK]→部署），本批不新增迁移脚本
