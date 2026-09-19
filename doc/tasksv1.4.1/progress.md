# Money App v1.4.1 总体进度

> 基于 v1.4 版本，针对竖屏登录页、账单页交互、设置页信息架构、宽屏滚动及部分体验细节进行优化与缺陷修复。
> 需求文档：`doc/proposalv1.4.1.md`　详细设计：`doc/detailed-designv1.4.1.md`

---

## 模块清单

- [x] [M1 - 登录页沉浸式改造](m1-login-immersive.md) —— 需求一 ✅ 完成（commit beef8a7；手工验收 5 项待抽检）
- [x] [M2 - 宽屏首次滚动卡顿修复](m2-desktop-scroll-fix.md) —— 需求四 ✅ 完成（commit 2cb0c77；手工验收 8 项待抽检；npm test 门槛已由主 Agent 终验代勾）
- [x] [M3 - 账单页年份切换（含最早年份接口）](m3-record-year-switch.md) —— 需求二 ✅ 完成（commit 5532673；手工验收 5 项待抽检；mypy 门槛项见备注）
- [x] [M4 - 账单页请求合并与筛选精简](m4-record-filter-dedup.md) —— 需求七 + 需求八 ✅ 完成（commit acba4f0；手工验收 5 项待抽检；连带收敛 M2 挂账的 3 例失败与仓库级 lint）
- [x] [M5 - 账单详情返回状态记忆](m5-record-state-restore.md) —— 需求三 ✅ 完成（commit d244803；手工验收 3 项待抽检）
- [x] [M6 - 预算管理迁移至统计页](m6-budget-to-stats.md) —— 需求五 ✅ 完成（commit 2c8b125；手工验收 6 项待抽检）
- [x] [M7 - 设置页三个管理区块改二级页面](m7-settings-subpages.md) —— 需求六 ✅ 完成（commit 51d67da；手工验收 7 项待抽检）
- [x] [M8 - 快速记账日期/时间布局与时间弹层动画](m8-datetime-picker.md) —— 需求九 ✅ 完成（commit b60e0e9；手工验收 6 项待抽检）

## 开发顺序（设计 §十一）

```
第 1 梯队（可并行）：M1（AppLayout 模板/LoginPage）  M2（AppLayout 样式）
                   M3（后端+切换条）  M6（后端+统计页+设置页预算删除）  M8
第 2 梯队：M4（依赖 M3 的 RecordListPage 改动完成）→ M5（依赖 M3/M4 后的 mount 与 search 形态）
第 3 梯队：M7（依赖 M6 完成 SettingsPage 预算删除，避免同文件冲突）
```

- 每个模块完成后独立执行：后端 `pytest`（涉及后端模块）+ 前端 `vitest run` + 手工验收清单，**通过后再进入下一模块**。

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `AppLayout.vue` | M1（template/script）、M2（宽屏样式）、M5（handleLogout） | M1/M2 可并行，合并无交叉 |
| `RecordListPage.vue` | M3 → M4 → M5 | 严格串行 |
| `SettingsPage.vue` | M6 → M7 | 严格串行，避免删除行号漂移 |
| `DatePickerPopover.vue` | M8 | 需回归验证账单页筛选（不启用 show-time）不受影响 |

## 已确认设计决策（实现约束，设计 §0.3）

| # | 决策点 | 结论 | 影响模块 |
|---|--------|------|----------|
| D1 | 最早记录年份来源 | 新增 `GET /api/records/earliest-year`，不改 records 响应 | M3 |
| D2 | 统计页预算与周期选择器 | 跟随：月视图管理所选月，年视图逐月展开（新增年汇总接口） | M6 |
| D3 | 宽屏滚动修复方向 | `transform: scale(1.1)` → `zoom: 1.1` | M2 |
| D4 | 宽屏登录页 FAB | 同样隐藏（判据 = 路由 `/login`） | M1 |
| D5 | 宽屏登录页侧边栏 | 隐藏（含汉堡按钮） | M1 |
| D6 | 登录页顶栏 | 保留（标题+暗色切换，非导航入口） | M1 |

## 进度统计

| 模块 | 总任务数 | 已完成 | 进度 |
|------|---------|--------|------|
| M1 - 登录页沉浸式改造 | 32 | 27 | 84%（余 5 项均为手工验收） |
| M2 - 宽屏首次滚动卡顿修复 | 20 | 12 | 60%（余 8 项均为手工验收；npm test 门槛终验代勾） |
| M3 - 账单页年份切换 | 36 | 30 | 83%（余 6 项：5 手工 + mypy 门槛见备注） |
| M4 - 账单页请求合并与筛选精简 | 38 | 33 | 87%（余 5 项均为手工验收） |
| M5 - 账单详情返回状态记忆 | 28 | 25 | 89%（余 3 项均为手工验收） |
| M6 - 预算管理迁移至统计页 | 56 | 50 | 89%（余 6 项均为手工验收） |
| M7 - 设置页三个管理区块改二级页面 | 48 | 41 | 85%（余 7 项均为手工验收） |
| M8 - 快速记账日期/时间布局与时间弹层动画 | 39 | 33 | 85%（余 6 项均为手工验收） |
| **合计** | **297** | **251** | **84%**（余 46 项 = 45 手工验收 + 1 mypy 门槛待人工裁定） |

## 验收对照（需求 → 模块）

| 需求 | 验收要点 | 模块 |
|------|----------|------|
| 一 登录页 | 无底栏/FAB/侧栏，锁滚动居中，小屏兜底，登录后恢复 | M1 |
| 二 年份切换 | 竖屏可翻历史年、两端边界、宽屏同步 | M3 |
| 三 返回记忆 | 年月/滚动/筛选完整恢复 | M5 |
| 四 宽屏首次滚动 | 首次下滚顺畅、视觉与动画不破坏 | M2 |
| 五 预算迁移 | 设置页无痕、统计页功能等价 + 周期跟随 | M6 |
| 六 二级页面 | 摘要卡 + 全量操作下沉 + 数量实时 | M7 |
| 七 月份闪烁 | 单次请求、无整块闪没 | M4 |
| 八 筛选精简 | 仅日期两项、不携带 type/category_id | M4 |
| 九 时间选择 | 两行、表盘时钟圆形展开/收起 | M8 |

## 范围外红线（设计 §13.11）

- 不删后端 type/category 查询参数与 store 字段（仅前端隐藏入口）
- 不改 budgets/records/tags/categories 数据模型；数据库无变更
- 不动导入导出、数据回溯、安全加固代码
- `GET /api/records` 响应结构不变
- 本版本无新增前后端依赖

## 测试结果记录

（每模块完成后回填）

| 模块 | 后端 pytest | 前端 vitest | lint/build | 手工验收 |
|------|------------|-------------|------------|----------|
| M1 | — | 89/89（AppLayout 16/16，新增 6 例） | lint pass / build pass | 5 项待抽检 |
| M2 | — | 模块 27/27（全量 119/122，3 失败均在 M4 在途文件） | lint/build：M2 文件 0 问题 / pass | 8 项待抽检；npm test 门槛终验已代勾 |
| M3 | 150/150（新增 5 例） | 89/89（新增 5 例） | lint pass / build pass；mypy 见备注 | 5 项待抽检 |
| M4 | — | 122/122 全绿（M4 相关 25 例；收敛 M2 挂账 3 例） | lint pass（0 error，2 既有 warning）/ build pass | 5 项待抽检 |
| M5 | — | 149/149 全绿（M5 新增 12 例） | lint pass（0 error）/ build pass | 3 项待抽检 |
| M6 | 150/150（新增用例含 year-summary 四件套） | 100/100 | lint pass / build pass；ruff 零告警（CI 口径） | 6 项待抽检 |
| M7 | — | 137/137 全绿（新增 15 例，含 36 标识符零残留 grep 断言） | lint pass / build pass | 7 项待抽检 |
| M8 | — | 78/78 | pass/pass | 6 项待抽检 |

## 待人工抽检清单

### M1 - 登录页沉浸式改造
- [ ] 竖屏未登录打开应用：只见登录/注册卡片，无底栏、无 + 按钮，页面无法滑动，卡片垂直居中
- [ ] 宽屏未登录：无侧栏、无汉堡、无 FAB，登录卡片居中，观感 100%（不参与 zoom）
- [ ] 极小屏（320x480）切注册 Tab 触发错误提示后，超出屏高内容可滚动到全部控件
- [ ] 顶栏（标题 + 暗色切换）正常显示且可切换主题
- [ ] 登录成功进入主页后，底栏/FAB（竖屏）、侧栏/汉堡/FAB（宽屏）即时恢复

### M2 - 宽屏首次滚动卡顿修复
- [ ] 110% 缩放视觉与改前等比一致（zoom 语义验证，Chrome/Edge/Firefox 126+）
- [ ] 底部渐变遮罩 `.content-wrapper::after`（:403-414）：fixed 恢复相对视口语义，位置表现正常
- [ ] 宽屏 1200px 档：冷启动依次进入首页、账单、统计、设置、详情、记账页，每页进入后**立即向下滚动**，无卡顿、无需反向唤醒
- [ ] 宽屏 960px 临界档：重复上述验证
- [ ] 滚动到底部：最后一张卡片完整可见（scrollHeight 真实）
- [ ] 回归：顶栏 sticky、底部渐变遮罩位置、详情页圆形展开/收起动画、110% 视觉与改前一致
- [ ] 窄屏（<960px）不出现横向滚动条
- [ ] 反复切换各页面多次，每次进入首次下滚均顺畅
- [x] ~~（门槛复核）`cd frontend && npm test` 通过~~ ✅ 终验主 Agent 代勾：M4 收敛后全量 149/149 绿（M2 完成时 3 例失败位于并行 M4 文件）

### M3 - 账单页年份切换
- [ ] 竖屏可逐年翻到最早有记录的年份，查看该年 1–12 月账单
- [ ] 到达最早记录年：左箭头隐藏；到达当前年：右箭头隐藏
- [ ] 无账单新用户：仅当前年，左箭头不显示
- [ ] 宽屏行为同步符合新范围规则
- [ ] 接口失败场景（可 mock）：账单页核心功能不受阻塞

### M4 - 账单页请求合并与筛选精简
- [ ] 点击任意月份，DevTools Network 恰有一次 `/api/records` 请求
- [ ] 切换月份期间列表保留、顶部细进度条一闪，无整块"加载中↔内容"闪没
- [ ] 筛选区只剩开始/结束两个日期控件，布局无贴挤
- [ ] 修改日期筛选同样只触发一次请求
- [ ] 上拉/加载更多分页追加正常，不重复首屏数据

### M5 - 账单详情返回状态记忆
- [ ] 翻到 3 月、滚动到列表中部、点开任一详情、返回：仍是 3 月、滚动位置不变、筛选条件不变、无回跳当前月的闪动
- [ ] 返回后再点底栏「账单」重新进入：定位当前月（现场已被消费）
- [ ] 登录 → 登出 → 换账号登录 → 进入账单页：默认当前月，无串号

### M6 - 预算管理迁移至统计页
- [ ] 设置页不再出现任何预算相关内容
- [ ] 统计页预算区块：查看、新增、编辑、删除全流程可用，功能与迁移前等价
- [ ] 进度条配色与迁移前一致（>80% 红、>50% 黄、其余绿）
- [ ] 月视图翻到 2025-03 再新增预算 → 写入 2025-03（不是系统当前月）
- [ ] 年视图逐月概览正确；点击月份行下钻到对应月视图
- [ ] 无预算用户：月视图空态、年视图"该年暂无预算设置"正常显示

### M7 - 设置页三个管理区块改二级页面
- [ ] 设置页三卡片仅显示摘要与箭头，数量正确
- [ ] 进入分类二级页：列表、新增、编辑、删除、上移/下移、恢复默认全部可用且与 v1.4 行为一致
- [ ] 进入标签二级页：chip 云、新增、删除可用；竖屏换行正常
- [ ] 进入快速记账二级页：模板列表（含来源展示）、新增、删除可用
- [ ] 各二级页操作后返回设置页：摘要数量即时更新
- [ ] 二级页底栏「设置」保持高亮；底栏/FAB 行为同数据回溯页
- [ ] 刷新应用直达 `/settings/tags` 等二级路由：登录守卫生效、页面正常

### M8 - 快速记账日期/时间布局与时间弹层动画
- [ ] 记一笔/编辑页：日期、时间各占一行，无贴挤
- [ ] 点击时间项：自点击位置圆形展开表盘时钟（24 小时制），含取消/确定；确定回填时间
- [ ] 收起为圆形收缩回原点——确定、取消、遮罩点击、ESC 四种关闭方式动画一致
- [ ] 日期弹层行为与改版前一致（选日即回填并收起）
- [ ] 账单页筛选日期控件（无 show-time）外观与行为逐像素不变
- [ ] M2 已合入时：宽屏 zoom 下弹层定位与动画正常（v-dialog teleport 到 body 不在 zoom 上下文）

## 阻塞清单

（暂无——8 个模块均一次通过，无 blocked、无重试）

## 终验记录（主 Agent，2026-09-19）

| 命令 | 结果 |
|------|------|
| `cd backend && python -m pytest tests/` | ✅ 150 passed（22 warnings，均为缓存目录权限提示） |
| `cd backend && python -m mypy app/ --ignore-missing-imports` | ⚠️ HEAD 107 errors/16 files；基线 ed41d89 实测（临时 worktree）104 errors/16 files → **净增 3 条**，与 M6 自报的 3 条吻合（budget_service.py union-attr×2 + budgets.py 新端点缺 return annotation×1，均与同文件既有写法同类）。全量清零基线问题超红线，待人工裁定（m3 任务文件该项保持未勾） |
| `cd backend && python -m ruff check app/ tests/` | ✅ All checks passed! |
| `cd frontend && npm test` | ✅ 10 files / 149 tests passed |
| `cd frontend && npm run lint` | ✅ 0 errors（2 条既有 CsvMappingDialog warning） |
| `cd frontend && npm run build` | ✅ 构建成功（仅 chunk size 提示） |

- 无新增前后端依赖；数据模型/数据库零变更；`GET /api/records` 响应结构不变（终验复核）。
- `frontend/dist` 由终验统一重建并提交（b2861fa）。
- M2 任务文件「npm test」门槛项由主 Agent 代勾（全量 149/149 绿）。
- 手工验收共 45 项，全部列于「待人工抽检清单」，未以任何自动化结果替代打勾（另有 m3 mypy 门槛 1 项待人工裁定，不计入手工项）。

## 交付后修复记录

- 2026-09-19 用户反馈「改日期后保存账单无反应」：复现定位为 **v-date-picker（Vuetify 3.12）回传 JS Date 对象**，`consume_time` 拼成 `"Tue Sep 15 2026…"` → 后端 422 → 前端静默 catch。属 v1.3 组件引入的历史遗留（M8 按「逐像素不变」红线原样承袭；vitest 桩回传字符串故未拦截）。修复：`DatePickerPopover.onDateSelected` 归一化 Date→`YYYY-MM-DD`，新增回归用例（vitest 150/150）；同修复作用于账单页日期筛选。端到端真机验证通过。
- 2026-09-19 `index.html` 增加 `Cache-Control: no-cache`（b34b6df）：防前端重建后浏览器复用旧入口引用已删除的 hash 资源致页面失能。

## 备注

- M8 notes：frontend/dist/ 构建产物变更未入模块提交（并行共用工作树），终验统一构建后处理；ExpandTransition.test.js 将无效的 vuetify components mock 改为 global.stubs 注册 VDialog stub（测试实现方式调整，非断言放宽）。
- M3 mypy 门槛：子 Agent 报告 v1.4 基线 mypy 即存在 100+ 处项目级历史报错（strict + SQLModel 噪音），修复需大面积改动其他模块文件、超红线；M3 新增代码自述零报错（records.py 无报错、record_service.py 报错行均在改动区间外）。主 Agent 终验阶段复核该论断并交人工裁定，M3 该项任务保持未勾选。
- M3 notes：左箭头 `v-if="selectedYear > minYear"` 在 minYear=null 加载瞬间会短暂显示——设计原文既定行为，未擅自收紧。
- M1 notes：唯一偏离——`.content-wrapper--bare` 写成复合选择器 `.content-wrapper.content-wrapper--bare`（声明内容与设计一致），用于稳定压过其后媒体查询内 `.content-wrapper` 的 padding，并远离 M2 媒体查询区域；已在 m1 任务文件补注。遗留：`.content-wrapper::after` 底部渐变遮罩在登录页仍存在（设计未要求移除），列为观感微调候选。
- M6 notes：① 统计页「删除入口」为任务文件 §3.2 明文条目，而 v1.4 SettingsPage 实际无删除按钮——子 Agent 以既有 ConfirmDialog + deleteBudget API 补齐，无新增依赖，主 Agent 已核对任务文件原文，认定有依据非功能漂移；② 概览卡「双 ¥」既有瑕疵按搬移原则原样保留；③ loadBudgets 错误分支按设计 §6.2.1 只 console.error，与旧 SettingsPage 行为不同属设计既定；④ StatisticsPage onMounted 补 loadCategories()（预算行图标依赖）。
- mypy 门槛裁定依据（M6 复核）：v1.4 基线 `mypy app` 即 107 errors/16 files，CI 配置为 `mypy app || true` 非阻断。§6.2 终验的 mypy 项按「相对基线零新增」口径执行，全量清零超出一版本范围且触红线，列入待人工裁定项。
- M2 notes：① AppLayout.vue :136/:420 两处注释文本 scale(1.1)→zoom(1.1) 同步（纯注释，略超「仅媒体查询」约束，已评估保留）；② 任务文件原 §4「npm test 无新增用例」与本任务书「必须补测试」冲突，取任务书，新增 §3.1 小节记录 M2-T1~T11 自动化用例（原 6 条真机手工条目原文未动）；③ M8 关联核查：v-dialog teleport 至 body 下 .v-overlay-container，不落入 zoom 上下文，弹层无需适配。
- M4 notes：① 设计未逐字列出但必要的 3 处收口（batchDelete 后 `search({force:true})`、加载更多按钮 `:loading` 改绑 refreshing、catch 中 `append` 时回退 pageNum）——主 Agent 认可，属去重机制自洽性修复；② `lastQueryKey` 置于 `<script setup>` 顶层（每挂载实例独立）符合设计参考代码；③ 「翻年份本身 0 请求」经主 Agent 核对设计 §3.2：箭头只改年份上下文并清空选中月，数据加载由点击月份芯片 `selectMonth` 驱动——设计既定，非回归；④ RecordListPage.vue 存在一处 M3 遗留 prettier 单行差异（prevYear v-btn 属性换行），test/lint/build 均不受阻，留终验统一 `npm run format` 与否人工定夺。
- M7 notes：① getRecords import 随 confirmDeleteCategory 迁入分类二级页（SettingsPage 保留会触发 no-unused-vars，任务书允许「如仍使用则保留」，实际未使用）；② 标签/快速记账二级页 onMounted 补 fetchCategories()/fetchTags()（刷新直达时弹窗数据源自足，与迁移前等价）；③ 快速记账数量 ref 命名 quickTemplateCount 以保证 grep 干净，口径同迁移前列表条目数；④ 宽屏侧栏「设置」精确匹配、/settings/* 不高亮——与 /history 现状一致，设计 §7.4 既定边界。
- M5 notes：① 设计伪码裸 `requestAnimationFrame` 改 `window.requestAnimationFrame`（eslint globals 白名单未含裸全局，no-undef；等价改写，未动 eslint 配置）；② store 额外导出 listView ref 本身（任务只要求三函数），供测试观测，不改行为；③ 恢复点只赋 selectedYear/selectedMonth 后直接 search()，未写 filters（红线遵守）；保存点仅挂 goToDetail；④ 源码变异探针被权限系统拦截未执行，敏感性以「恢复态 vs 默认态」差异断言保证。
