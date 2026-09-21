# M5 - 账单页年份箭头常驻 + 边界置灰 + 尺寸回退 x-small（需求五）

> 对应需求五（设计 §五）。左右箭头现为 `v-if` 条件渲染（:24/:60）边界即消失，尺寸为 v1.4.3 §三 放大的 small/20 偏大。改为：常驻 + disabled 置灰 + x-small/16，无 tooltip。
> 涉及文件：`RecordListPage.vue`（箭头区 :23-31、:59-67）、`RecordListPage.test.js`（年份切换 describe 组 :313-406（设计引 :317-406，实测组起 :313）+ 尺寸红线 :1041-1043 整组改写）。与 M6 同文件不同区域（M6 改行金额 :134-141），可并行。
> 依赖：无。不动项：月份 chip 尺寸、`centerSelectedMonth` 居中滚动、跨年高亮、年份注释行（:50-56）。

---

## 1. 模板改造（设计 §5.2.1，两按钮对称）

- [x] 1.1 左箭头：删 `v-if="selectedYear > minYear"` → 常驻；加 `:disabled="leftDisabled"` + `class="year-nav-btn"`；`size="x-small"`、`<v-icon size="16">mdi-chevron-left</v-icon>`
- [x] 1.2 右箭头对称：删 `v-if="selectedYear < currentYear"`；`:disabled="rightDisabled"`；`@click="nextYear"`
- [x] 1.3 禁用态不加 tooltip / 无「已是最新年份」提示文案（需求 5.3，用户确认从简）

## 2. script 禁用判定（设计 §5.2.1，D6）

- [x] 2.1 `leftDisabled = computed(() => selectedYear.value <= (minYear.value ?? selectedYear.value))`——minYear 未加载（null）按已到边界处理，置灰而非消失/可点（保守向）
- [x] 2.2 `rightDisabled = computed(() => selectedYear.value >= currentYear)`
- [x] 2.3 接口失败回退链（需求 5.5）：`loadEarliestYear()`（:225-233）catch 已回退 `minYear=currentYear` → 左箭头灰色在场——核验

## 3. 行为收口（设计 §5.2.2）

- [x] 3.1 `prevYear()/nextYear()`（:246-258）函数内边界守卫**保留不删**（disabled 挡点击、守卫挡键盘/程序化调用双保险）
- [ ] 3.2 禁用态可辨性：Vuetify `v-btn--disabled`（--v-disabled-opacity .38）明暗两主题肉眼可辨；若真机判不清，仅允许 `.year-nav-btn[disabled]` scoped 内微调 opacity，不改非禁用态

## 4. 边界与异常（设计 §5.3）

- [x] 4.1 `earliest_year=null` 无账单用户：minYear=currentYear → 双灰但均在（现状双消失→本模块改正）
- [x] 4.2 minYear 加载完成前首帧：左箭头即渲染禁用，加载后按实值放开——无闪烁跳位（宽度恒定）
- [x] 4.3 已翻到非当前年（selectedMonth=null）点右箭头回当前年：现有行为不变，到 currentYear 即灰
- [x] 4.4 键盘 focus + Enter 触发 disabled 按钮：Vuetify 原生阻断
- [x] 4.5 x-small 后 `d-flex` 行内 chip 区 flex-grow 吸收宽度变化：自查无挤压换行

## 5. 测试（设计 §5.4，附录 B 改写总览）

- [x] 5.1 **改写**尺寸红线 :1041-1043 → `size="x-small"\s+@click="prevYear"` … `<v-icon size="16">` 断言 + 反向断言不再含 small/20 箭头（:1043 旧反向断言删除）；同用例 :1039 注释「年份箭头 x-small/small → small/20」同步改为回退后口径，防注释与断言矛盾
- [x] 5.2 **改写**箭头边界组——**范围限定**在 `describe('RecordListPage - 年份切换')`（:313-406）组内：「箭头不存在 `toHaveLength(0)`」共 6 处（:329/:358/:380/:395/:396/:406）全部改为「在场且 `props('disabled')===true`」。**勿扩大**：:586 的 `toHaveLength(0)` 属「请求合并与筛选精简」组（filterCard v-select 断言），与本模块无关不得触碰
- [x] 5.3 新增「两按钮任何年份组合均在 DOM」：currentYear/minYear/中间年三态 × 左右两钮参数化矩阵
- [x] 5.4 `leftDisabled` 单元：minYear=null→true；minYear=currentYear→true；minYear<selectedYear→false
- [x] 5.5 `?raw`：`v-if="selectedYear` 在箭头区零命中（常驻判据）
- [x] 5.6 既有回归全保持：点选月份查询、居中滚动（:949-966 组）、返回现场用例
- [x] 5.7 `RecordListPage.test.js` 只动箭头/尺寸块，M6 金额块（:1164-1173）不触碰（串行提交）

## 6. 验收门槛

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 6.2 人工：最新年份右灰左可点；翻到 minYear 双灰但均在；无账单用户双灰在场（需求验收 1）
- [ ] 6.3 人工：箭头明显比 v1.4.3 小一档；月份点选/居中/跨年高亮不回退（需求验收 2）
- [ ] 6.4 人工：明暗两主题禁用态可辨；竖/宽屏布局无挤乱
