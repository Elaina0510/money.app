# M10 - 主页最近账单与账单页行图标 primary 色系统一（需求十）

> 对应需求十（设计 §十）。主页最近账单删收支箭头、行首改分类图标（缺失回退 `mdi-circle`）；账单页行图标改 `.entry-avatar` 同款 primary 色系；收支仅由金额红/绿表达。三处共用既有 `.entry-avatar`（D8），**global.scss 零改动**。
> 涉及文件：`frontend/src/pages/DashboardPage.vue`（:124-147）、`frontend/src/pages/RecordListPage.vue`（:108-118）。
> 依赖：无。与 M2 同文件（DashboardPage 大卡区）区域无交叉可并行；与 M3/M11 同文件（RecordListPage 月份条）区域无交叉可并行。**记录详情页本次不改**（需求 10.4 裁定）。

---

## 1. 主页最近账单行（设计 §10.2）

- [x] 1.1 删除行首收支箭头 avatar 整块（:125-129，mdi-arrow-down/up）与标题行内小分类图标（:132-134）→ 合并为单一图标
- [x] 1.2 行首新图标：`<v-avatar class="entry-avatar mr-2" size="42"><v-icon color="primary" size="20">{{ record.category_icon || 'mdi-circle' }}</v-icon></v-avatar>`
- [x] 1.3 金额红/绿 + −/+ 前缀保持现状（:140-147 不动）

## 2. 账单页行图标

- [x] 2.1 `RecordListPage.vue:109-117`：`v-avatar` 的收支双色 `:color`（`#FFE8E8`/`#E8FFF3`）→ `class="entry-avatar"`；`v-icon` 色 → `color="primary"`（尺寸 40/20 原样保留）
- [x] 2.2 图标本身仍是各自的分类图标；金额区（:128-135）不动

## 3. 边界自检（设计 §10.3）

- [ ] 3.1 深色主题：`.entry-avatar` 用 `--v-theme-primary` 变量自动跟随（v1.4.2 已验证），走查确认
  > 人工走查项（明暗主题两档 × 三页同款观感）：代码侧已由「零新增类、复用全局 `.entry-avatar`」保证与设置页同源同变量；本次未做真机/浏览器主题走查，留人工清单。
- [x] 3.2 无分类记录：`category_icon` 空串 → 回退 `mdi-circle`；标题维持 `tag?.name || category_name || '未分类'` 链不变
- [x] 3.3 统计页分类排行等其他图标**不动**（超出需求范围；主页「分类支出排行」卡带色板图标非列表行图标）
  > 主页排行卡 `:color="item.color + '20'"` 原样保留（并由测试用例5 锁住）；统计页文件未进入本模块改动集；`RecordDetailPage.vue` 按需求 10.4 裁定不改（两色字面量仅存于详情页与设置页快捷模板/记账页，均在本模块范围外）。

## 4. 测试（设计 §10.4）

- [x] 4.1 `DashboardPage.test.js`：行首 avatar 含 `entry-avatar` 类、渲染 `record.category_icon`、组件树不含 `mdi-arrow-down/up`；分类图标缺失行渲染 `mdi-circle`；金额色/前缀回归
  > 新增 M10 组 5 条用例（同文件 M2 组 10 条不动 → 合计 15 passed）。行首图标与金额位于 `v-list-item` 具名插槽内，jsdom 未装 Vuetify 时自定义元素不渲染具名插槽内容，故用 `v-list-item` 透传桩件使行内 DOM 可寻址（与 §10.4-2 的 `?raw` 断言互为补充）。
- [x] 4.2 `RecordListPage.test.js`：行 avatar `entry-avatar`；`?raw` 辅助断言 `#FFE8E8`/`#E8FFF3` 两色字面量在模板区零命中
  > 新增 M10 组 3 条 `?raw` 用例；并把本文件原有两条 `should maintain expense/income background color`（断 `#FFE8E8`/`#E8FFF3`，且因插槽不渲染而带 `if (exists())` 空转守卫）按设计 §10.4 的口径反转为 `entry-avatar` + `color="primary"` + 金额红/绿的真实断言（用例数不减、去掉空转守卫，非削弱）。

## 5. 验收与质量门槛

- [x] 5.1 `npm test` 全绿；`npm run lint` 通过
  > 实跑：`npx vitest run` → 13 files / 232 tests 全绿（含 `RecordListPage.test.js` 46、`DashboardPage.test.js` 15）；`npm run lint` → 0 error（仅 `CsvMappingDialog.vue` 2 条既存 `vue/require-default-prop` warning，非本模块文件）。
- [ ] 5.2 手工自查：主页最近账单行首为分类图标（primary 色系底色）无箭头；账单页图标风格与设置页入口一致，三页同款观感；支出红/收入绿；明暗主题、竖/宽屏
