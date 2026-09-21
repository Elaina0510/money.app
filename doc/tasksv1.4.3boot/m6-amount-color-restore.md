# M6 - 金额红/绿配色全站恢复 + 列表金额格式对齐（需求六）

> 对应需求六（设计 §六）。根因已实测锁定：`global.scss:275-287`（实测区间）深色主题对排版类的 `color: … !important` 压制内联配色（样式表 !important > 内联），深色下红绿全灭。统一方案（D7）= 新增 `.amount-expense/.amount-income/.amount-neutral` 专用类（明暗同色、带 !important），7 个受害节点内联→类迁移；**不删不削弱深色文字强制规则**（红线）。
> 涉及文件：`global.scss`（新段落，独占）、`RecordListPage.vue` :136-141、`DashboardPage.vue` :164-169/:78/:87/:119、`RecordDetailPage.vue` :32-37、`StatisticsPage.vue` :50-52/:59-62/:68-70、`utils/format.js`（删 getTypeColor）、测试 3 文件。
> 依赖：无。与 M1（DashboardPage）、M5（RecordListPage）同文件不同区域可并行。

---

## 1. 专用配色类（设计 §6.2.1，global.scss 新段落）

- [x] 1.1 紧邻深色文字规则之后新增段落并互注：`.amount-expense { color: #FF6B6B !important; }`、`.amount-income { color: #20C997 !important; }`、`.amount-neutral { color: #9E9E9E !important; }`（明暗同色；!important 是对抗深色排版强制色的显式让渡）
- [x] 1.2 红线核验：`global.scss:275-287` 深色文字规则块**逐字不动**（需求六 1：不得删削弱）

## 2. 七节点迁移（设计 §6.2.2，配色口径与前后缀零变化）

- [x] 2.1 #1 账单列表金额（`RecordListPage.vue:136-141`）：`:style` 三元 → `class="… mr-2 amount-node" :class="record.type === 'expense' ? 'amount-expense' : 'amount-income'"`；文本 → `{{ record.type === 'expense' ? '-' : '+' }}{{ formatAmount(record.amount) }}`（格式对齐：`−¥128.00` 形制）；文件头补 `import { formatAmount } from '@/utils/format'`
- [x] 2.2 #2 主页最近账单金额（`DashboardPage.vue:164-169`）、#3 详情页大数字（`RecordDetailPage.vue:32-37`）：同型 `:class` 三元替换 `:style`（文本现值已是 +/- + formatAmount，不动）
- [x] 2.3 #4 统计页支出卡（:50-52，**D8 新增**）、#5 收入卡（:59-62）、#7 主页期间支出/收入卡（:78/:87）、#8 分类支出排行金额（:119）：删内联 `style="color: …"`，挂静态类 `amount-expense`/`amount-income`
- [x] 2.4 #6 统计页结余（:68-70）：`:class="balance > 0 ? 'amount-income' : balance < 0 ? 'amount-expense' : 'amount-neutral'"`；`balanceColor`（:458-463）**保留**仅供同行 `<v-icon :color>`（图标 color 属性不受压制）
- [x] 2.5 前缀维持 ASCII `-`（不引入 U+2212）；各节点排版类（font-weight-bold/text-body-x）全部保留——只把颜色让给专用类
- [x] 2.6 `.amount-node` 测试锚点类各页统一挂用（无样式，供 ?raw/DOM 断言）

## 3. 死助手处置（设计 §6.2.3）

- [x] 3.1 删除 `utils/format.js:45-47` `getTypeColor`（全库零消费方已核实；配色真源收敛到 CSS 类）

## 4. 防扩散锁定项（设计 §6.2.4）

- [x] 4.1 巡查复核：五个业务文件模板区不再出现 `:style="{ color:` 与 `style="color: #FF`/`#20` 于文字金额节点（v-icon/v-avatar 的 :color 与 background 内联不在禁列）
- [x] 4.2 需求 4「新命中一并纳入」结论确认：D8 巡查终版命中 = 清单一处新发现（统计页支出卡），已并入 §2.3

## 5. 测试（设计 §6.4，附录 B 改写总览）

- [x] 5.1 `global.scss` raw 断言：三张专用类声明在场（含 !important）；`.v-theme--dark .font-weight-bold` 深色强制块原样在场（红线：未削弱全局可读性规则）
- [x] 5.2 五文件 `?raw`：金额节点挂 `amount-expense|amount-income`；`RecordListPage.vue` 不含 `:style="{ color: record.type`、不含 `{{ record.amount }}`（必须过 formatAmount）；`StatisticsPage.vue` 三卡含类且 `balanceColor` 仅 v-icon 消费（div 行零命中）
- [x] 5.3 DOM 断言：RecordListPage 行金额 class 含语义类、文本匹配 `/^[+-]¥[\d,]+\.\d{2}$/`；DashboardPage/StatisticsPage 同型各一组；结余正/负/零三态→类映射参数化
- [x] 5.4 **改写固化用例（粒度红线）**：
  - `RecordListPage.test.js` 用例 3（:1164-1173）**只改 :1166-1172 两条断言**（内联三元色 → 语义类断言；裸 `record.amount` → formatAmount 断言）；**:1165 `category_icon || 'mdi-circle'` 回退断言为 M10 资产必须保留**，勿整用例重写丢断言
  - `DashboardPage.test.js` 用例 4（:369-382）：`attributes('style')` 内联色断言 → `classes()` 含 `amount-expense`/`amount-income` 断言；文本 `-¥58.50`/`+¥3,000.00` 前缀断言保持（现值已合规）
  - `StatisticsPage.test.js` 摘要卡组涉内联色断言处同步 → 类断言（实现时定位具体行）
- [x] 5.5 `utils/format.js` 导出面：`getTypeColor` 不存在断言（或既有用例删除即锁）
- [x] 5.6 `RecordListPage.test.js` 只动金额块（:1164-1173），M5 箭头块不触碰（串行提交）

## 6. 验收门槛（深色实测为验收主体）

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 6.2 人工·深色模式账单页：同屏一笔支出一笔收入，金额一红一绿、前缀一 − 一 +，肉眼可辨；显示 `−¥128.00` 完整格式（需求验收 1）
- [ ] 6.3 人工·深色模式其余位置：主页两处金额+分类排行、详情页大数字、统计页三卡全部恢复红绿（需求验收 2）
- [ ] 6.4 人工：浅色模式零变化不回退；深色下标题/正文/说明文字颜色体系不受影响（抽查设置页/详情页文本）
- [ ] 6.5 判别预案：若浅色也见不到红绿 → 属 `record.type` 字段缺失/改名另一根因，转 M2 §1 环境排查流程补查后修，验收标准不变
- [ ] 6.6 明暗、竖/宽屏自查清单执行
