# M2 - 主页大卡「总收支」+ 三视图点按切换（需求二）

> 对应需求二（设计 §二）。月概览卡标题改「{月份} 总收支」，点按大数字区在 收入→支出→结余 循环切换（初始视图=支出，D5），三点指示示意可切换；收入/笔数/日均小字明细恒定。结余纯前端派生，零新增接口。
> 涉及文件：`frontend/src/pages/DashboardPage.vue`（大卡区 :4-42、computed :169-184、scoped 样式）。
> 依赖：无。动画时长与 M14 共用口径：M14 变量未落前先写字面量 220ms / `cubic-bezier(0.25,0.8,0.5,1)`，M14 落变量后回填替换（设计 §2.2.3 两模块解耦显式约定）。与 M10 同文件（:124-147 最近账单区）区域无交叉，可并行。

---

## 1. 视图状态与循环逻辑（D5）

- [x] 1.1 `views = ['income', 'expense', 'balance']`；`view = ref('expense')`（初始视图=支出，与改造前「总支出」卡语义连续）
- [x] 1.2 `nextView = { income: 'expense', expense: 'balance', balance: 'income' }` + `cycleView()`（点按推进序 expense→balance→income→expense，即需求「收入→支出→结余」循环）
- [x] 1.3 `viewLabel` 映射：income 收入 / expense 支出 / balance 结余
- [x] 1.4 `viewAmount` computed：income=`summary.total_income`、expense=`summary.total_expense`、balance=收入−支出；`summary` null 时 `|| 0` 兜底；格式化沿用现 toLocaleString 千分位两位小数口径（负数渲染 `-1,234.56`）

## 2. 模板结构（设计 §2.2.2）

- [x] 2.1 卡标题「{月份} 总支出」→「{月份} 总收支」（:8）；外层 `monthly-overview-card`（color=primary）结构不动
- [x] 2.2 点按区容器：包裹 视图标签 + 大数字 + 三点指示；`@click="cycleView"`、`role="button"`、`user-select:none`；不参与滚动链（不与第二行期间卡、最近账单区手势冲突）
- [x] 2.3 视图标签置于大数字上方：`text-caption`、白色 0.85 透明
- [x] 2.4 三点指示 `.view-dot`：8px 圆点，当前视图 opacity 1、其余 0.4，白字体系内，纯装饰无独立点击语义
- [x] 2.5 结余负数色 `#FFC7C7`（D5）：条件 `view === 'balance' && balance < 0` 挂负数类（如 `amount-number--negative`）；结余=0 与非负沿用现白
- [x] 2.6 小字明细行（收入 / 笔数 / 日均）保持现状，不随视图切换变化
- [x] 2.7 右上角「跳统计」chevron 所在容器补 `@click.stop` 以绝 bubbling 后患

## 3. 切换动画

- [x] 3.1 数字+标签包 `<Transition name="amount-switch" mode="out-in">`，`:key="view"`
- [x] 3.2 enter/leave 均为 opacity + translateY(6px)；时长/缓动先写字面量 220ms / `cubic-bezier(0.25, 0.8, 0.5, 1)`（M14 落 `--expand-duration`/`--expand-easing` 后回填为 var 引用）

## 4. 边界自检（设计 §2.3）

- [x] 4.1 `summary` 加载中（null）：大数字显示 `0.00`、切换仍可点、加载完成后响应式刷新
- [x] 4.2 快速连点：`mode="out-in"` 由 Vue Transition 排队，无 DOM 报错；末态=最后一次 view 值，标签/数字/指示一致
- [x] 4.3 无收入只有支出：结余视图负红正确显示

## 5. 测试（设计 §2.4）

- [x] 5.1 新增 `frontend/src/pages/DashboardPage.test.js`（stub api/records、api/statistics、router）
- [x] 5.2 标题断言含「总收支」
- [x] 5.3 初始视图=支出：大数字 = total_expense 格式化值、标签「支出」、第 2 点高亮
- [x] 5.4 点按循环：click→结余（值 = income−expense 精确断言）→click→收入→click→支出；标签与指示点 active 类同步
- [x] 5.5 结余负数视图带负数色类（`amount-number--negative`）
- [x] 5.6 小字明细不随视图变化：两次快照 收入/笔数/日均 文本一致

## 6. 验收与质量门槛

- [x] 6.1 `npm test` 全绿；`npm run lint` 通过
  > 实跑：`npx vitest run` → 13 files / 232 tests 全绿（本模块 `src/pages/DashboardPage.test.js` 的 10 条用例全过；同文件随后由 M10 追加 5 条 → 该文件现 15 条，均属另一模块的改动集）。`npm run lint` → 0 error（仅 `CsvMappingDialog.vue` 2 条既存 `vue/require-default-prop` warning，非本模块文件）。
- [ ] 6.2 手工自查（真机）：竖屏触摸一次即切换、无误触连环跳；primary 深底上红/白对比度可读；明暗主题、竖/宽屏四组合过一遍
