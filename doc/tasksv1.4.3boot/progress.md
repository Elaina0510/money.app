# Money App v1.4.3-boot 总体进度

> v1.4.3 发布后的跟进批次：六项用户使用中发现的问题与优化——① 主页总收支大卡左右横滑切换；② 记一笔页分类恒久空白（阻断级 Bug）；③ 标签输入免回车；④ 标签建议层锚定输入框正下方；⑤ 账单页年份箭头常驻+边界置灰+尺寸回退；⑥ 金额红/绿深色下被 `!important` 压制（根因已实测锁定），全站一次性恢复。
> 需求文档：`doc/proposalv1.4.3boot.md`　详细设计：`doc/detailed-designv1.4.3boot.md`
> 任务拆解：每模块一个文件（见模块清单链接），子任务以 checklist 表示完成状态。

---

## 模块清单（6 个，与需求六节一对一）

- [ ] [M1 - 主页总收支大卡左右横滑切换（点击保留）](m1-swipe-view-switch.md) —— 需求一（总览 1）
- [x] [M2 - Bug 修复（阻断）：记一笔分类恒久空白 + 加载解耦 + 空态兜底](m2-categories-blank-fix.md) —— 需求二（2）★先复现后修 ✅ 2789bcb（根因 A）
- [x] [M3 - 标签输入免回车：保存账单即保存标签](m3-tag-no-enter-save.md) —— 需求三（3）✅ 6a405c2
- [x] [M4 - 标签建议浮层锚定输入框正下方](m4-tag-suggest-anchor.md) —— 需求四（4）✅ 019c470（主方案；②③几何待终验浏览器实测）
- [x] [M5 - 账单页年份箭头常驻 + 边界置灰 + 尺寸回退 x-small](m5-year-nav-always-visible.md) —— 需求五（5）✅ 4ae8269
- [x] [M6 - 金额红/绿配色全站恢复 + 列表金额格式对齐](m6-amount-color-restore.md) —— 需求六（6）✅ b03a881

## 开发顺序（设计附录 A）

```
优先级（线上可用性 Bug 先行）：M2、M6
批 1（并行）：M1（Dashboard） · M5（RecordList） · M6（global.scss + 5 文件） · M2（RecordForm 解耦）
批 2：M3（RecordForm script，依赖 M2 合入）→ M4（RecordForm 模板/样式，依赖 M3 合入）
批 3：M3+M4 联合验收链路（D9）+ 全站终验
```

模块间无功能依赖，全部耦合为同文件不同区域的文件级耦合；唯一串行链为 RecordFormPage 上的 M2 → M3 → M4（M3/M4 各自独立提交，末了联合验收）。

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `RecordFormPage.vue` | M2、M3、M4 | 串行 M2→M3→M4；M2 改 onMounted+分类卡、M3 改 submit+标签 script、M4 加 wrap+menuProps+scoped 样式，diff 无交叉行 |
| `RecordListPage.vue` | M5、M6 | 区域无交叉可并行（M5 箭头 :23-67，M6 行金额 :134-141 + formatAmount import） |
| `DashboardPage.vue` | M1、M6 | 区域无交叉可并行（M1 点按区 :25-52+script，M6 :78/:87/:119/:166） |
| `global.scss` | M6 独占 | 新增 `.amount-*` 段落；:275-287 深色强制规则逐字不动（红线） |
| `RecordListPage.test.js` | M5、M6 | M5 改年份切换组 :313-406（组内 6 处 `toHaveLength(0)`；:586 筛选组断言不在范围）+尺寸红线 :1041-1043；M6 改用例 3 内 :1166-1172 两条金额断言（:1165 icon 回退断言保留）；各自动各自断言，串行提交 |
| `RecordFormPage.test.js` | M2、M3、M4 | 各只增/改各自用例组 |
| `StatisticsPage.test.js`、`utils/format.js` | M6 | 单模块 |

## 已确认设计决策（实现约束，设计 §0.3）

| # | 决策 | 落点 |
|---|------|------|
| D1 | 手势载体=原生 Pointer Events（down/up/cancel 三点位，**不挂 pointermove**）+ `touch-action: pan-y`；滑动仅 pointerup 一次判定，拖动零反馈零 preventDefault | M1 |
| D2 | 阈值 48px + `\|dx\|>\|dy\|` 主轴判定；滑动后置 `suppressClickUntil=now+350ms` 吞 click；测试合成事件须 `{bubbles:true}`（up 监听在 window） | M1 |
| D3 | M2 设计给复现判定树（根因 A 联动失败/B 迁移缺失/C 后端/D 空列表），实现先复现取证（现场库只读）；解耦改造无论根因都实施 | M2 |
| D4 | submit 归一：现有 results 精确同名 → 非防抖 `searchTags` 兜底 → 无同名才 createTag；**兜底查询失败→中止保存**（后端无查重无唯一约束，不静默造重复）；toast 带「已新建标签「x」」；✕ 清除同步清空 tagSearchQuery | M3 |
| D5 | 锚定主方案=v-autocomplete + wrap(`position:relative`) + `:menu-props={attach: wrapEl, maxHeight:240, contentClass}` + scoped !important 锁 left/width（Vuetify 3.12.6 源码核验支持）；几何取证三点不符即触发预案 B（v-text-field + 自绘 absolute 层），以真机实测为准 | M4 |
| D6 | `leftDisabled = selectedYear <= (minYear ?? selectedYear)`——未加载按禁用（保守向）；接口失败回退 minYear=currentYear → 左灰在场不消失 | M5 |
| D7 | `.amount-expense/.amount-income/.amount-neutral`（!important 明暗同色）；7 节点内联→类；深色强制规则不删不削弱；getTypeColor 删除；balanceColor 保留供图标色；列表金额改 formatAmount、前缀维持 ASCII `-` | M6 |
| D8 | 防扩散巡查终版：受害节点 7 处 = 需求 6 处 + 新发现 `StatisticsPage.vue:50-52` 支出卡（用户裁定纳入 M6）；其余内联 color 非「文字金额」组合不在修复域 | M6 |
| D9 | M3/M4 各自独立提交、各自测试全绿后，追加联合验收链路：「输入→锚定层→点选→保存」与「输入→免回车保存」 | M3+M4 |

## 全局红线（各模块共同遵守）

- 不回退 v1.4.3 已验收项：§十一 横滑误切页 overscroll 修复、§十四 展开动画统一、§八 分类收支共用。
- M2 复现期对真实库一切只读；如需动库先备份再操作。
- `frontend/dist` 不随模块提交，终验统一重建，与 v1.4.3 包体做 gzip 对比（本批预期增量≈0）。
- 后端默认零改动（仅 M2 根因 C 分支触后端）；mypy 按「基线零新增」口径。
- 明暗两主题、竖/宽屏两形态逐模块自查。

## 终验清单（设计附录 A，批 3）

- [ ] 全部 vitest 绿；`RecordFormPage.test.js` M2/M3/M4 三组 + 既有组全量
- [ ] 深色模式逐处截图核验 M6 七节点位置清单
- [ ] 真机（竖屏触摸滑动 + 软键盘 + 滚动）三场景过 M1/M4
- [ ] `frontend/dist` 统一重建 + gzip 对比
- [ ] M2 若落根因 B：发布窗口执行 `backend/migrate_to_v1.4.3.py`（停服→备份→核对 [OK]→部署），本批不新增迁移脚本

## 进度统计

| 模块 | 层 | 状态 | 完成 commit | 备注 |
|------|----|------|-------------|------|
| M1 | 前端 | ⬜ 未开始 | — | |
| M2 | 前端（复现或牵连后端/迁移） | ✅ 完成 | 2789bcb | 33/38 勾选（1.5 归主 Agent 本节落盘；6.2–6.5 人工/备忘项）；P1 副本沙盒复现=**根因 A**，后端零改动；vitest RecordFormPage 27/27 |
| M3 | 前端 | ✅ 完成 | 6a405c2 | 26/31 勾选（6.2–6.6 人工/D9 项）；RecordFormPage 42/42 绿（主 Agent 复跑）+ eslint 净；D9 联合链路用例由 M4 落 |
| M4 | 前端 | ✅ 完成 | 019c470 | 16/28 勾选（余 12 = 浏览器终判/真机/人工/预案 B 条件项）；主方案 D5 落地零依赖；判据①已 jsdom 真实 Vuetify 取证，**②③并入终验浏览器会话实测**；RecordFormPage 49/49 绿 |
| M5 | 前端 | ✅ 完成 | 4ae8269 | 20/24 勾选（3.2+6.2–6.4 人工项）；RecordListPage.test.js 58/58 绿（主 Agent 复跑）；含 2 处已裁定执行级偏差（见执行记录） |
| M6 | 前端 | ✅ 完成 | b03a881 | 18/23 勾选（6.2–6.6 为人工项）；vitest 新增 12 条、M6 相关 105/105 绿；主 Agent 独立复跑通过；含特异度提级修正（见下） |

## 开工登记（2026-09-21，基线 4200ac3）

| 项 | 值 | 用途 |
|----|----|------|
| `backend/money.db` SHA256 | `f8e0c5de303c46f4acae01972f299b095f2b339bc004bcc647a36231f8246405` | P1 原件未动证明（终验复核） |
| pytest 基线 | 245 passed（22 warnings） | 终验对照 |
| mypy 基线 | Found 90 errors in 14 files（checked 51 source files） | 「基线零新增」口径对照 |
| ruff 基线 | All checks passed | 终验对照 |
| vitest 基线 | 326 passed / 15 files | 终验对照（本批只增不减） |
| eslint 基线 | 0 errors, 2 warnings | 终验对照（既有警告不新增） |
| dist 基准（v1.4.3） | 目录 5,694,218 bytes；js+css gzip 合计 534,154 bytes | §6.2 包体增量对比（本批预期≈0） |

环境说明：后端命令统一用 `backend/venv/Scripts/python.exe`；开发环境现场差异——M2 复现结论仅对现场库有效，沙盒取证基于原库副本。

## 模块执行记录

### M2（2789bcb）复现结论登记（任务 1.5，P1 副本沙盒取证）

**根因判定 = A（联动失败）；B/C/D 全部排除；后端零改动，P3 条件分支未触发。**

- 取证链：`DATABASE_URL` 指向副本起服务（原库全程只读，开工/收工 SHA256 双测均为登记值 `f8e0c5de…46405`）→ `/api/categories` 200（16 条非空）+ `/api/records/quick-templates` **500**（`sqlite3.OperationalError: no such column: quick_templates.kind`，两条 ORM 真实 SQL 在只读副本复现同列缺失）→ 旧 `Promise.all` 连坐致 `categories.value` 赋值根本不执行 → 用户所见「恒久空白 + 零提示」（组件 DOM 级复现留证）。
- 根因 B 验证：副本上跑 `migrate_to_v1.4.3.py` → 两阶段 `[OK]` 后 **`foreign_key_check 70 条违规回滚`（exit=1，副本哈希不变自证回滚干净）**；且该脚本不涉及 `quick_templates.kind`——500 真正触发源是 **v1.4.2 的 `migrate_to_v1.4.2.py` 未执行**（副本执行后加列成功、同 SQL 查询恢复）。属运维/发布窗口事实，非后端代码缺陷。
- 根因 D 排除：可见集合 16 条非空。根因 C 排除：后端行为符合契约。
- dist 核对：现场所部署 v1.4.3 包仍含旧 `Form load error` 连坐代码 → 修复须待本批终验重建 dist 后部署生效。
- **发布备忘增量（重要）**：① 现场库处于「v1.4.2 迁移未跑完」半截态，发布窗口应先补跑 `migrate_to_v1.4.2.py`（其正是 kind 列来源）；② `migrate_to_v1.4.3.py` 对该库形制（budgets 无 user_id 唯一约束混合格）当前**跑不通**（FK 检查 70 违规回滚）——原 6.5 备忘的迁移窗口程序须按此修订执行预案，交付报告展开。
- 环境事实修正：`backend/money.db` 实际**未被 git 跟踪**（`.gitignore` 含 `*.db`，`git ls-files` 空命中）——prompt 红线 1「git 已跟踪」表述与实况不符，但「原库只读/零 db 入库」约束照常执行且风险更低。
- 实现偏差（子 Agent notes，已核）：`retryLoadCategories` 成功后除重取快照外追加 `await nextTick()` 回算 `isDirty`（否则首屏补选 watcher 早于 await 续体，isDirty 残留 true，违背需求口径）；测试文件 `vue-router` mock 参数化为文件级 `mockRouteParams`（既有行为零变化）——M3/M4 子 Agent 复用现状即可。
- 沙盒残留：~~`%TEMP%\m2sandbox\` 与 `frontend/node_modules/.m2-forensics-quarantine/`~~ **主 Agent 已于 2026-09-21 14:29 清理完毕**（仓库外临时件，git 全程不涉）。

### M4（019c470）采用方案与几何取证登记

- **采用结论：主方案（D5 menuProps attach），预案 B 未启用**。零新增依赖、零新动画体系；控件本体/v-model/搜索/选中/M3 归一逻辑零改动；`transition="fab-transition"` 保留在场（?raw 锁）。
- 三点判据：① 已取证并测试锁定（仓内**首个真实 Vuetify 挂载用例组**：`.tag-field-anchor .v-overlay-container .v-overlay--absolute` 命中=overlay 进 wrap、attach 生效；`.v-overlay__content` 带 `tag-suggest-menu` + 内联 `max-height:240px`）；②③ 需真实布局，子 Agent 无 browser-use 且 headless Edge 自采被权限层拦阻 → **移交主 Agent 终验浏览器会话实测**（与 M6 深色截图同环境），任一不符且 CSS 不可救 → 按 §4.2.3 切预案 B（另计 3 轮）。
- 测试基建：真实 Vuetify 走 `vuetify/dist/vuetify.esm.js` 聚合构建；ResizeObserver/IntersectionObserver（异步投递）/visualViewport 三替身——仅测试文件内，零改配置与产品代码。
- 既有测试必要改写 1 处：M3 用例 5.9 末行反向锁（锁「M4 机制尚不存在」时序事实，M4 落地必假）→ 正向锁 `v-model`+`:menu-props` 在场。非放宽。
- 登记：`fab-transition` 在 Vuetify 3.12 VAutocomplete 未声明该 prop → 作未知 attribute 落 `<input>`（与设计 §4.1 defaults.VMenu 对 VSelect 不生效注记同源）；红线要求沿用现状未改。
- 卫生：M4 提交用 pathspec 限定（当时 M1 文件已 staged，未被卷入）。

### M3（6a405c2）执行登记

- 归一三段严格照设计 §3.2.1 落地（精确同名 `===` → 非防抖兜底、失败**中止保存**零调用锁死 → `createTag`）；✕ 清除同步清空 `tagSearchQuery`；`data` 六键载荷零变化；「文字优先」扩大由 5.4/5.9 源码正则锁死。
- 附录 B 口径改写=**无对象可改**（条件式）：既有测试从未固化「仅回车才建标签」表述（全文件 grep 回车零命中），新口径由 5.1/5.7a/5.7b 显式化，两条旧路径各留回归用例——判定合理，已核。
- 测试基建沿 M2 手法：`showToast` mock 参数化为文件级 `mockShowToast`（既有 27 用例零消费、行为不变）；M3 组 `afterEach` 还原全部文件级默认，不泄漏 M4。既有 27 条逐条原样（删除行仅 3 行 import/mock 工厂），零删除零放宽。
- 边界登记：孤儿标签（建标签成功但账单保存失败）按 §3.2.2 维持既有行为不扩 scope；建标签→存账单顺序已被源码断言锁定。
- 行号漂移按标识符定位（submit 实为 :417-453、清除分支 :361-366），未扩大改动面。

### M5（4ae8269）执行偏差与改写登记

- 附录 B 点名改写全部落地：年份组 6 处 `toHaveLength(0)`→「在场且禁用」（`findArrowBtn` helper 收拢在场断言，零删除零放宽）；尺寸红线正向断言翻转 + 删除固化回退目标的旧反向断言、代之以「不再指回 small/16」两条反向锁；:590 筛选组、M6 金额块与 :1165 icon 回退断言未触碰。
- 偏差①：jsdom 未装 Vuetify 时 `v-btn` 为自定义元素无 `.props()`——disabled 判据改读落地属性 `disabled="true"/"false"` + `wrapper.vm.leftDisabled/rightDisabled` 双端口径互锁（等价，任务书 `props('disabled')` 手法在本文件不可用）。
- 偏差②：设计 §5.2.1 参考代码属性序与 §5.4 要求正则冲突，实现按「:disabled、class 在前，size 紧邻 @click」排列，语义零损失（`vue/attributes-order` 已 off）。
- 3.2 禁用态 opacity 可辨性：子 Agent 未新增任何 scoped 样式，留真机判定（若判不清仅允许 `.year-nav-btn[disabled]` 微调）。

### M6（b03a881）设计与实现偏差登记

- **特异度提级修正（对设计 §6.2.1 参考代码的必要偏离，待 P4 截图终判）**：设计单类 `.amount-expense{...!important}` 特异度 (0,1,0)，打不过红线块 `.v-theme--dark .font-weight-bold` 的 (0,2,0) 同 !important（同 important 按特异度择优，源序仅打平用）→ 深色下金额仍会被压色。实现保留三张单类声明逐字在场 + 紧邻其后追加「重复类名提级」双类声明（`.amount-expense.amount-expense` 等，沿仓内 M14 slide-y 既有手法）追平 (0,2,0) 并以源序胜出。红线块逐字未动（diff 纯新增，测试反向锁内容与源序）。**若 P4 深色截图判不符 → 按 §4.2.3 类推处置**。
- jsdom 对 !important+特异度实现不完整（子 Agent 控制实验证实）→ 深色真值判定完全依赖 P4 浏览器截图，jsdom 侧仅 ?raw/DOM 断言——与设计口径一致。
- 测试改写范围比任务点名多两处（同属金额块、格式变更后必红的旧口径固化）：`RecordListPage.test.js` M10 组 :181-182/:207-208 `attributes('style')`→`classes()` + 金额文本改 `formatAmount` 形制；:1165 icon 回退断言逐字保留；M5 箭头组 :313-406、筛选组 :586、尺寸红线均未触碰。非删除、非放宽。
- `DashboardPage.test.js` 孤儿常量 `EXPENSE_COLOR`/`INCOME_COLOR` 按 §8.6 陷阱预案删除，色值锁改造复用于 `RecordListPage.test.js` M6 用例 1。
- 统计页摘要卡三卡类断言为**新增**（原文件确无内联色断言），符合任务文件「属新增非改写」口径。

## 待人工抽检清单（按模块分组，原文抄录）

### M2
- 6.2 人工·当前环境重建部署：进记一笔页九宫格完整展示全部共用品类；选分类+输金额可保存账单（需求验收 1；含根因 B/D 时先走附录 A）——**注：本批复现结论=根因 A，现场先按发布备忘补跑 v1.4.2 迁移再验证**
- 6.3 人工·DevTools 网络面板模拟两接口分别断网/500 复核两分支表现（沙盒侧 browser-use 真浏览器抓包未能覆盖，已由 ASGI 层状态码/响应体 + 组件 DOM 级双路等价取证补位）
- 6.4 人工·明暗主题下错误/空态配色可读

### M6
- 6.2 人工·深色模式账单页：同屏一笔支出一笔收入，金额一红一绿、前缀一 − 一 +，肉眼可辨；显示 `−¥128.00` 完整格式（需求验收 1）——**已列入 P4 深色截图自动化实测**（七节点+浅色对照），人工仅终判观感
- 6.3 人工·深色模式其余位置：主页两处金额+分类排行、详情页大数字、统计页三卡全部恢复红绿（需求验收 2）——**同上，已列入 P4**
- 6.4 人工：浅色模式零变化不回退；深色下标题/正文/说明文字颜色体系不受影响（抽查设置页/详情页文本）——**P4 浅色同点位复拍覆盖前半，后半人工**
- 6.5 判别预案：若浅色也见不到红绿 → 属 `record.type` 字段缺失/改名另一根因，转 M2 §1 环境排查流程补查后修，验收标准不变
- 6.6 明暗、竖/宽屏自查清单执行

### M5
- 3.2 禁用态可辨性：Vuetify `v-btn--disabled`（--v-disabled-opacity .38）明暗两主题肉眼可辨；若真机判不清，仅允许 `.year-nav-btn[disabled]` scoped 内微调 opacity，不改非禁用态
- 6.2 人工：最新年份右灰左可点；翻到 minYear 双灰但均在；无账单用户双灰在场（需求验收 1）
- 6.3 人工：箭头明显比 v1.4.3 小一档；月份点选/居中/跨年高亮不回退（需求验收 2）
- 6.4 人工：明暗两主题禁用态可辨；竖/宽屏布局无挤乱

### M3
- 6.2 人工：输入新标签名→不碰回车→点保存 → 账单保存成功、详情页可见该标签
- 6.3 人工：输入既有同名文字直接保存 → 关联既有标签，标签管理无重复条目
- 6.4 人工：点选/回车两条旧路径不回退
- 6.5 与 M4 联合验收链路（D9，用例见 m4 任务文件 §6）——**用例由 M4 自动化承载（§6.7 a/b），人工仅真机链路终判**
- 6.6 人工：明暗、竖/宽屏自查

### M4
- 7.2 人工·真机竖屏：输入时建议层紧贴输入框正下方、同宽；选中后表单布局无跳动（需求验收）
- 7.3 人工：打开建议层后滚动页面，层与输入框保持吸附
- 7.4 人工：软键盘弹起不脱节；建议多条内滚、不挡保存按钮
- 7.5 人工：展开动画与站内其他浮层观感一致（§十四 口径）；深浅主题
- 5.1 页面滚动中浮层打开吸附真值（机制已具备，真机/浏览器项）
- 5.2 后半 贴底空间不足 connected 策略自动翻转上方（真机自查覆盖，需求 4.3）
- 5.3 软键盘弹起 visualViewport resize 重算；失准即触发预案 B 判定
- 3.2/3.3 几何判据②③——**主 Agent 终验浏览器实测**（非人工项，实测结论落本节后更新）
- 4.1 预案 B 切换决策：待②③实测 + 真机三场景任一不达标且 CSS 不可救才触发

## 阻塞清单

（暂无）

## 巡查外发现（不扩大改动面，留交付报告供裁定）

- `frontend/src/pages/HistoryPage.vue:80`：`-/+` 前缀 + 裸 `{{ record.amount }}`，无内联 color、不在 §6.1 七节点清单与 D8 巡查终版命中内 → 按范围外保留。
