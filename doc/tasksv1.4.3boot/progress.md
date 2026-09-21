# Money App v1.4.3-boot 总体进度

> v1.4.3 发布后的跟进批次：六项用户使用中发现的问题与优化——① 主页总收支大卡左右横滑切换；② 记一笔页分类恒久空白（阻断级 Bug）；③ 标签输入免回车；④ 标签建议层锚定输入框正下方；⑤ 账单页年份箭头常驻+边界置灰+尺寸回退；⑥ 金额红/绿深色下被 `!important` 压制（根因已实测锁定），全站一次性恢复。
> 需求文档：`doc/proposalv1.4.3boot.md`　详细设计：`doc/detailed-designv1.4.3boot.md`
> 任务拆解：每模块一个文件（见模块清单链接），子任务以 checklist 表示完成状态。

---

## 模块清单（6 个，与需求六节一对一）

- [ ] [M1 - 主页总收支大卡左右横滑切换（点击保留）](m1-swipe-view-switch.md) —— 需求一（总览 1）
- [ ] [M2 - Bug 修复（阻断）：记一笔分类恒久空白 + 加载解耦 + 空态兜底](m2-categories-blank-fix.md) —— 需求二（2）★先复现后修
- [ ] [M3 - 标签输入免回车：保存账单即保存标签](m3-tag-no-enter-save.md) —— 需求三（3）
- [ ] [M4 - 标签建议浮层锚定输入框正下方](m4-tag-suggest-anchor.md) —— 需求四（4）
- [ ] [M5 - 账单页年份箭头常驻 + 边界置灰 + 尺寸回退 x-small](m5-year-nav-always-visible.md) —— 需求五（5）
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
| M2 | 前端（复现或牵连后端/迁移） | ⬜ 未开始 | — | ★先复现后修，阻断级优先 |
| M3 | 前端 | ⬜ 未开始 | — | 依赖 M2 合入 |
| M4 | 前端 | ⬜ 未开始 | — | 依赖 M3 合入；与 M3 联合验收 |
| M5 | 前端 | ⬜ 未开始 | — | 含测试红线改写 |
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

### M6（b03a881）设计与实现偏差登记

- **特异度提级修正（对设计 §6.2.1 参考代码的必要偏离，待 P4 截图终判）**：设计单类 `.amount-expense{...!important}` 特异度 (0,1,0)，打不过红线块 `.v-theme--dark .font-weight-bold` 的 (0,2,0) 同 !important（同 important 按特异度择优，源序仅打平用）→ 深色下金额仍会被压色。实现保留三张单类声明逐字在场 + 紧邻其后追加「重复类名提级」双类声明（`.amount-expense.amount-expense` 等，沿仓内 M14 slide-y 既有手法）追平 (0,2,0) 并以源序胜出。红线块逐字未动（diff 纯新增，测试反向锁内容与源序）。**若 P4 深色截图判不符 → 按 §4.2.3 类推处置**。
- jsdom 对 !important+特异度实现不完整（子 Agent 控制实验证实）→ 深色真值判定完全依赖 P4 浏览器截图，jsdom 侧仅 ?raw/DOM 断言——与设计口径一致。
- 测试改写范围比任务点名多两处（同属金额块、格式变更后必红的旧口径固化）：`RecordListPage.test.js` M10 组 :181-182/:207-208 `attributes('style')`→`classes()` + 金额文本改 `formatAmount` 形制；:1165 icon 回退断言逐字保留；M5 箭头组 :313-406、筛选组 :586、尺寸红线均未触碰。非删除、非放宽。
- `DashboardPage.test.js` 孤儿常量 `EXPENSE_COLOR`/`INCOME_COLOR` 按 §8.6 陷阱预案删除，色值锁改造复用于 `RecordListPage.test.js` M6 用例 1。
- 统计页摘要卡三卡类断言为**新增**（原文件确无内联色断言），符合任务文件「属新增非改写」口径。

## 待人工抽检清单（按模块分组，原文抄录）

### M6
- 6.2 人工·深色模式账单页：同屏一笔支出一笔收入，金额一红一绿、前缀一 − 一 +，肉眼可辨；显示 `−¥128.00` 完整格式（需求验收 1）——**已列入 P4 深色截图自动化实测**（七节点+浅色对照），人工仅终判观感
- 6.3 人工·深色模式其余位置：主页两处金额+分类排行、详情页大数字、统计页三卡全部恢复红绿（需求验收 2）——**同上，已列入 P4**
- 6.4 人工：浅色模式零变化不回退；深色下标题/正文/说明文字颜色体系不受影响（抽查设置页/详情页文本）——**P4 浅色同点位复拍覆盖前半，后半人工**
- 6.5 判别预案：若浅色也见不到红绿 → 属 `record.type` 字段缺失/改名另一根因，转 M2 §1 环境排查流程补查后修，验收标准不变
- 6.6 明暗、竖/宽屏自查清单执行

## 阻塞清单

（暂无）

## 巡查外发现（不扩大改动面，留交付报告供裁定）

- `frontend/src/pages/HistoryPage.vue:80`：`-/+` 前缀 + 裸 `{{ record.amount }}`，无内联 color、不在 §6.1 七节点清单与 D8 巡查终版命中内 → 按范围外保留。
