import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// ---------------------------------------------------------------------------
// M2 需求二：主页大卡「总收支」三视图点按切换（设计 §2.4）
//   点按循环 expense→balance→income（初始视图=支出，D5）；结余为纯前端派生，零新增接口
//   jsdom 无 Vuetify 插件：Vuetify 组件渲染为同名自定义元素，故按类名与文本断言
// ---------------------------------------------------------------------------

const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ path: '/' }),
}))

vi.mock('@/api/records', () => ({
  getRecords: vi.fn(),
}))

vi.mock('@/api/statistics', () => ({
  getSummary: vi.fn(),
  getByCategory: vi.fn(),
}))

import { getRecords } from '@/api/records'
import { getSummary, getByCategory } from '@/api/statistics'
import DashboardPage from './DashboardPage.vue'
import dashboardSource from './DashboardPage.vue?raw'

const RECORDS = [
  {
    id: 1,
    type: 'expense',
    amount: 58.5,
    category_icon: 'mdi-food',
    category_name: '餐饮',
    consume_time: '2026-09-06 12:00',
  },
  {
    id: 2,
    type: 'income',
    amount: 3000,
    category_icon: 'mdi-cash',
    category_name: '工资',
    consume_time: '2026-09-05 09:00',
  },
]

// 与组件同口径的金额格式化（千分位 + 两位小数）
function money(val) {
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Transition mode="out-in" 的换页由 rAF/timeout 驱动，真定时器下等一帧即可观测末态
async function settle() {
  await flushPromises()
  await nextTick()
  await new Promise((r) => setTimeout(r, 80))
  await nextTick()
}

async function mountWithSummary(summaryData) {
  getRecords.mockResolvedValue({ items: RECORDS, total: 2, page: 1, total_pages: 1 })
  getSummary.mockResolvedValue(summaryData)
  getByCategory.mockResolvedValue({ items: [] })
  const wrapper = mount(DashboardPage)
  await settle()
  return wrapper
}

function numberText(wrapper) {
  return wrapper.find('.amount-number').text()
}

function viewLabelText(wrapper) {
  return wrapper.find('.view-label').text()
}

function activeDotIndex(wrapper) {
  return wrapper.findAll('.view-dot').findIndex((d) => d.classes().includes('view-dot--active'))
}

async function tapArea(wrapper) {
  await wrapper.find('.overview-cycle-area').trigger('click')
  await settle()
}

describe('DashboardPage - 总收支三视图点按切换（M2）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 逐用例清空残留实现（用例6 会装入挂起式 mockImplementation）
    getRecords.mockReset()
    getSummary.mockReset()
    getByCategory.mockReset()
  })

  it('用例1（任务 5.2）: 大卡标题为「{月份} 总收支」，不再写死「总支出」', async () => {
    const wrapper = await mountWithSummary({ total_income: 3000, total_expense: 1234.56, transaction_count: 7 })
    const card = wrapper.find('.monthly-overview-card')

    expect(card.text()).toMatch(/\d{4}年\d{2}月 总收支/)
    expect(card.text()).not.toContain('总支出')
    wrapper.unmount()
  })

  it('用例2（任务 5.3）: 初始视图=支出——大数字取 total_expense、标签「支出」、第 2 点高亮', async () => {
    const wrapper = await mountWithSummary({
      total_income: 3000,
      total_expense: 1234.56,
      transaction_count: 7,
    })

    expect(wrapper.vm.view).toBe('expense')
    expect(numberText(wrapper)).toBe(money(1234.56))
    expect(viewLabelText(wrapper)).toBe('支出')
    expect(wrapper.findAll('.view-dot')).toHaveLength(3)
    expect(activeDotIndex(wrapper)).toBe(1)
    wrapper.unmount()
  })

  it('用例3（任务 5.4）: 点按循环 expense→balance→income→expense，值/标签/指示同步', async () => {
    const summary = { total_income: 5000.28, total_expense: 1234.56, transaction_count: 9 }
    const wrapper = await mountWithSummary(summary)

    // 1) expense → balance（结余 = 收入 − 支出，纯前端派生）
    await tapArea(wrapper)
    expect(wrapper.vm.view).toBe('balance')
    expect(numberText(wrapper)).toBe(money(5000.28 - 1234.56))
    expect(viewLabelText(wrapper)).toBe('结余')
    expect(activeDotIndex(wrapper)).toBe(2)

    // 2) balance → income
    await tapArea(wrapper)
    expect(wrapper.vm.view).toBe('income')
    expect(numberText(wrapper)).toBe(money(5000.28))
    expect(viewLabelText(wrapper)).toBe('收入')
    expect(activeDotIndex(wrapper)).toBe(0)

    // 3) income → expense（回到起点，三视图闭环）
    await tapArea(wrapper)
    expect(wrapper.vm.view).toBe('expense')
    expect(numberText(wrapper)).toBe(money(1234.56))
    expect(viewLabelText(wrapper)).toBe('支出')
    expect(activeDotIndex(wrapper)).toBe(1)
    wrapper.unmount()
  })

  it('用例4（任务 5.5）: 结余为负时挂负数色类（#FFC7C7 口径），非负/零结余不挂', async () => {
    const wrapper = await mountWithSummary({
      total_income: 100,
      total_expense: 900.5,
      transaction_count: 3,
    })

    await tapArea(wrapper) // → balance（100 − 900.5 = -800.5）
    const number = wrapper.find('.amount-number')
    expect(wrapper.vm.view).toBe('balance')
    expect(number.classes()).toContain('amount-number--negative')
    expect(number.text()).toBe(money(100 - 900.5))
    expect(number.text().startsWith('-')).toBe(true)

    // 同一负结余下，收入/支出视图不挂负数类
    await tapArea(wrapper) // → income
    expect(wrapper.find('.amount-number').classes()).not.toContain('amount-number--negative')
    await tapArea(wrapper) // → expense
    expect(wrapper.find('.amount-number').classes()).not.toContain('amount-number--negative')
    wrapper.unmount()
  })

  it('用例4b（任务 2.5）: 结余=0 沿用现白，不挂负数类', async () => {
    const wrapper = await mountWithSummary({
      total_income: 500,
      total_expense: 500,
      transaction_count: 1,
    })

    await tapArea(wrapper)
    expect(wrapper.vm.view).toBe('balance')
    expect(wrapper.vm.balance).toBe(0)
    expect(wrapper.find('.amount-number').classes()).not.toContain('amount-number--negative')
    expect(numberText(wrapper)).toBe(money(0))
    wrapper.unmount()
  })

  it('用例5（任务 5.6）: 小字明细（收入/笔数/日均）不随视图切换变化', async () => {
    const wrapper = await mountWithSummary({
      total_income: 3000,
      total_expense: 1234.56,
      transaction_count: 7,
    })

    const detail = () =>
      wrapper.findAll('.stat-item').map((i) => i.text().replace(/\s+/g, ' ').trim())

    const before = detail()
    expect(before.join('|')).toContain('收入')
    expect(before.join('|')).toContain('笔数')
    expect(before.join('|')).toContain('日均')
    expect(before.join('|')).toContain(String(7))

    await tapArea(wrapper) // balance
    await tapArea(wrapper) // income
    expect(detail()).toEqual(before)
    wrapper.unmount()
  })

  it('用例6（任务 4.1）: summary 未加载时大数字为 0.00 且点按仍可切换', async () => {
    let resolveSummary
    getRecords.mockResolvedValue({ items: [], total: 0, page: 1, total_pages: 1 })
    getByCategory.mockResolvedValue({ items: [] })
    getSummary.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSummary = resolve
        })
    )
    const wrapper = mount(DashboardPage)
    await nextTick()

    expect(wrapper.vm.summary).toBeNull()
    expect(numberText(wrapper)).toBe(money(0))
    expect(viewLabelText(wrapper)).toBe('支出')

    await tapArea(wrapper)
    expect(wrapper.vm.view).toBe('balance')
    expect(numberText(wrapper)).toBe(money(0))

    // 数据到达后响应式刷新，视图不回滚
    resolveSummary({ total_income: 800, total_expense: 300.25, transaction_count: 4 })
    await settle()
    expect(wrapper.vm.view).toBe('balance')
    expect(numberText(wrapper)).toBe(money(800 - 300.25))
    wrapper.unmount()
  })

  it('用例7（任务 4.2）: 快速连点无 DOM 报错，末态与 view 一致', async () => {
    const wrapper = await mountWithSummary({
      total_income: 2000,
      total_expense: 500,
      transaction_count: 2,
    })

    const area = wrapper.find('.overview-cycle-area')
    await area.trigger('click')
    await area.trigger('click')
    await area.trigger('click')
    await area.trigger('click') // expense→balance→income→expense→balance
    await settle()

    expect(wrapper.vm.view).toBe('balance')
    expect(wrapper.findAll('.view-dot')).toHaveLength(3)
    expect(activeDotIndex(wrapper)).toBe(2)
    expect(viewLabelText(wrapper)).toBe('结余')
    expect(numberText(wrapper)).toBe(money(2000 - 500))
    expect(wrapper.findAll('.amount-number')).toHaveLength(1) // 无残留双节点
    wrapper.unmount()
  })

  it('用例8（任务 2.7）: 右上角跳统计容器 click.stop——点击不外溢成视图切换', async () => {
    const wrapper = await mountWithSummary({
      total_income: 3000,
      total_expense: 1234.56,
      transaction_count: 7,
    })

    await wrapper.find('.overview-jump').trigger('click')
    await settle()
    expect(wrapper.vm.view).toBe('expense')

    // 点按区自身仍可正常循环
    await tapArea(wrapper)
    expect(wrapper.vm.view).toBe('balance')
    wrapper.unmount()
  })

  it('用例9: 点按区结构（role=button + user-select）与动画变量口径（M14 已回填 :root 变量）', () => {
    expect(dashboardSource).toMatch(/class="overview-cycle-area[^"]*"\s+role="button"/)
    expect(dashboardSource).toMatch(/@click="cycleView"/)
    expect(dashboardSource).toMatch(/user-select:\s*none/)
    // 切换动画：out-in + :key="view"；M14（任务 7.4 / §2.2.3）把 M2 的字面量占位回填为
    // --expand-duration / --expand-easing 引用——意图不放宽：仍锁「引用存在 + 无硬编码残留」
    expect(dashboardSource).toMatch(/<Transition name="amount-switch" mode="out-in">/)
    expect(dashboardSource).toMatch(/:key="view"/)
    expect(dashboardSource).toMatch(/opacity var\(--expand-duration\) var\(--expand-easing\)/)
    expect(dashboardSource).toMatch(/transform var\(--expand-duration\) var\(--expand-easing\)/)
    expect(dashboardSource).not.toMatch(/220ms/)
    expect(dashboardSource).not.toMatch(/cubic-bezier\(0\.25/)
    // 本页只消费变量、不定义变量（单点定义在 global.scss :root，M14 全站锁另测）
    expect(dashboardSource).not.toMatch(/--expand-(duration|easing)\s*:/)
    expect(dashboardSource).toMatch(/translateY\(6px\)/)
    // 结余负数色为 D5 裁定值
    expect(dashboardSource).toMatch(/\.amount-number--negative \{[^}]*color: #FFC7C7/)
    // 三点指示 8px 圆点 + 当前/非当前透明度档
    expect(dashboardSource).toMatch(/\.view-dot \{[^}]*width: 8px/)
    expect(dashboardSource).toMatch(/\.view-dot \{[^}]*opacity: 0\.4/)
    expect(dashboardSource).toMatch(/\.view-dot--active \{[^}]*opacity: 1/)
  })
})

// ---------------------------------------------------------------------------
// M10 需求十：主页最近账单行首图标统一（设计 §10.2 / 测试 §10.4-1）
//   删行首收支箭头 avatar 整块 + 标题行内小分类图标 → 单一分类图标，复用全局 .entry-avatar（D8）；
//   收支仅由右侧金额红/绿与 −/+ 前缀表达；分类缺失回退 mdi-circle。
// ---------------------------------------------------------------------------

// 行首图标与金额都在 v-list-item 的具名插槽里：未装 Vuetify 时自定义元素不渲染具名插槽内容，
// 用透传桩件把插槽落回 DOM（原 class / color 属性由 fallthrough 保留，断言仍指向真实模板）。
const ROW_SLOT_STUBS = {
  'v-list-item': {
    template: '<div><slot name="prepend" /><slot /><slot name="append" /></div>',
  },
}
// 【v1.4.3-boot M6】原 EXPENSE_COLOR / INCOME_COLOR 内联色正则随用例 4 的
// attributes('style') → classes() 改写一并删除（否则 lint no-unused-vars）；
// 红/绿与灰的色值锁改由 global.scss 的 .amount-* 声明承载，断言见 RecordListPage.test.js M6 组用例1。

async function mountRows(items) {
  getRecords.mockResolvedValue({ items, total: items.length, page: 1, total_pages: 1 })
  getSummary.mockResolvedValue({ total_income: 0, total_expense: 0, transaction_count: 0 })
  getByCategory.mockResolvedValue({ items: [] })
  const wrapper = mount(DashboardPage, { global: { stubs: ROW_SLOT_STUBS } })
  await settle()
  return wrapper
}

describe('DashboardPage - 最近账单行图标 primary 色系统一（M10）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getRecords.mockReset()
    getSummary.mockReset()
    getByCategory.mockReset()
  })

  it('用例1（任务 1.1/1.2）: 行首为单一分类图标 avatar，挂 .entry-avatar 且图标 color="primary"', async () => {
    const wrapper = await mountRows([RECORDS[0]])
    const avatars = wrapper.findAll('.entry-avatar')

    // 单一图标：只有行首一枚（原「箭头 + 行内小图标」双图标已合并）
    expect(avatars).toHaveLength(1)
    expect(avatars[0].attributes('class')).toContain('entry-avatar')
    expect(avatars[0].attributes('color')).toBeUndefined()
    const icon = avatars[0].find('v-icon')
    expect(icon.attributes('color')).toBe('primary')
    expect(icon.text()).toBe('mdi-food')
    // 标题行只留文字，不再嵌第二枚图标
    expect(wrapper.find('v-list-item-title').find('v-avatar').exists()).toBe(false)
    wrapper.unmount()
  })

  it('用例2（任务 1.1）: 组件树不含收支箭头（mdi-arrow-down / mdi-arrow-up 字面量零命中）', async () => {
    const wrapper = await mountRows(RECORDS)
    expect(wrapper.html()).not.toMatch(/mdi-arrow-(down|up)/)
    expect(dashboardSource).not.toMatch(/mdi-arrow-(down|up)/)
    expect(wrapper.findAll('.entry-avatar')).toHaveLength(2)
    wrapper.unmount()
  })

  it('用例3（任务 3.2）: 分类图标缺失行回退 mdi-circle，标题仍走 tag→category→未分类链', async () => {
    const wrapper = await mountRows([
      { id: 9, type: 'expense', amount: 12, category_icon: '', consume_time: '2026-09-01 08:00' },
    ])
    const icon = wrapper.find('.entry-avatar v-icon')
    expect(icon.text()).toBe('mdi-circle')
    expect(wrapper.find('v-list-item-title').text()).toBe('未分类')
    wrapper.unmount()
  })

  it('用例4（任务 1.3）: 金额红/绿 + −/+ 前缀口径不动', async () => {
    const wrapper = await mountRows(RECORDS)
    const rows = wrapper.findAll('.record-card')
    expect(rows).toHaveLength(2)

    // 【v1.4.3-boot M6 改写】内联 style → .amount-* 专用类（色值与原内联逐字相同，见 global.scss）
    const expenseAmount = rows[0].find('.font-weight-bold')
    expect(expenseAmount.classes()).toContain('amount-expense')
    expect(expenseAmount.text()).toBe('-¥58.50')

    const incomeAmount = rows[1].find('.font-weight-bold')
    expect(incomeAmount.classes()).toContain('amount-income')
    expect(incomeAmount.text()).toBe('+¥3,000.00')
    wrapper.unmount()
  })

  it('用例5（任务 3.3 / D8）: 零新增类、global.scss 不动；行内不设收支双色底', () => {
    // 复用既有全局类，本页不得重新定义 .entry-avatar，也不得留下双色底色字面量
    expect(dashboardSource).not.toMatch(/\.entry-avatar\s*\{/)
    expect(dashboardSource).not.toMatch(/#FFE8E8|#E8FFF3/i)
    expect(dashboardSource).toMatch(/<v-avatar class="entry-avatar mr-2" size="42">/)
    // 「分类支出排行」卡带色板图标非列表行图标，按任务 3.3 保持不动
    expect(dashboardSource).toMatch(/:color="item\.color \+ '20'"/)
  })
})

// ---------------------------------------------------------------------------
// v1.4.3-boot M6（需求六）：主页四处金额节点内联色 → .amount-* 专用类
//   迁移表（设计 §6.2.2）：#7 期间支出卡 / 期间收入卡、#8 分类支出排行金额、
//   #2 最近账单行金额（三元）。深色排版强制规则与 global.scss 三张类的红线锁
//   在 RecordListPage.test.js M6 组用例1/1b 单点承载，本组只锁主页节点。
// ---------------------------------------------------------------------------
describe('DashboardPage - 金额红/绿语义专用类配色（M6）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getRecords.mockReset()
    getSummary.mockReset()
    getByCategory.mockReset()
  })

  async function mountAmountNodes() {
    getRecords.mockResolvedValue({ items: RECORDS, total: 2, page: 1, total_pages: 1 })
    getSummary.mockResolvedValue({ total_income: 3000, total_expense: 128, transaction_count: 2 })
    getByCategory.mockResolvedValue({
      items: [{ category_name: '餐饮', total: 128, color: '#8B7E74', icon: 'mdi-food' }],
    })
    const wrapper = mount(DashboardPage, { global: { stubs: ROW_SLOT_STUBS } })
    await settle()
    return wrapper
  }

  it('用例2（设计 §6.4-2 / 任务 5.2）: 四处节点挂语义类 + amount-node 锚点，内联 color 零残留', () => {
    // #7 期间两卡（静态语义类）
    expect(dashboardSource).toMatch(/class="text-h6 font-weight-bold amount-node amount-expense"/)
    expect(dashboardSource).toMatch(/class="text-h6 font-weight-bold amount-node amount-income"/)
    // #8 分类支出排行金额（语义恒支出 → 静态红类，无三元）
    expect(dashboardSource).toMatch(
      /class="text-body-2 font-weight-bold amount-node amount-expense"/,
    )
    // #2 最近账单行金额（三元类）
    expect(dashboardSource).toMatch(/class="font-weight-bold text-body-1 amount-node"/)
    expect(dashboardSource).toMatch(
      /:class="record\.type === 'expense' \? 'amount-expense' : 'amount-income'"/,
    )
    // 反向红线（防扩散 §6.2.4）：文字金额节点不再出现内联 color
    expect(dashboardSource).not.toMatch(/:style="\{ color:/)
    expect(dashboardSource).not.toMatch(/style="color: #FF|style="color: #20/)
    // 排版类全部保留（字号/字重不受影响，只把颜色让给专用类）
    expect(dashboardSource).toMatch(/text-h6 font-weight-bold amount-node/)
    expect(dashboardSource).toMatch(/text-body-2 font-weight-bold amount-node/)
  })

  it('用例3（设计 §6.4-3 / 任务 5.3）: DOM 四类金额节点挂语义类且不带内联 style', async () => {
    const wrapper = await mountAmountNodes()
    const nodes = wrapper.findAll('.amount-node')
    // 期间两卡 + 排行一条 + 最近账单两行 = 五处
    expect(nodes).toHaveLength(5)

    const [periodExpense, periodIncome, rankAmount, rowExpense, rowIncome] = nodes
    expect(periodExpense.classes()).toContain('amount-expense')
    expect(periodExpense.text()).toBe('¥128.00')
    expect(periodIncome.classes()).toContain('amount-income')
    expect(periodIncome.text()).toBe('¥3,000.00')
    expect(rankAmount.classes()).toContain('amount-expense')
    expect(rankAmount.text()).toBe('¥128.00')
    expect(rowExpense.classes()).toContain('amount-expense')
    expect(rowExpense.text()).toBe('-¥58.50')
    expect(rowIncome.classes()).toContain('amount-income')
    expect(rowIncome.text()).toBe('+¥3,000.00')

    for (const node of nodes) {
      // 内联 style 归零 → 颜色只可能来自专用类（深色下不再被排版 !important 压制）
      expect(node.attributes('style')).toBeUndefined()
      expect(node.text()).toMatch(/^[+-]?¥[\d,]+\.\d{2}$/)
    }
    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// v1.4.3-boot M1（需求一）：主页总收支大卡左右横滑切换（点击保留）——设计 §1.4
//   任务 5.1–5.6 六组编号用例 + §4 边界补测（2.2 鼠标非左键 / 4.4 pointercancel 清理 /
//   4.5 加载中滑动 / 4.6 快速连续滑动）+ 3.1 手势隔离复查。
//   合成事件红线（prompt §七-2）：up/cancel 监听挂在 window 上 → 合成事件必须冒泡形
//   `new MouseEvent('pointerup', { bubbles: true, clientX, clientY })`（jsdom 无
//   PointerEvent 构造器，以 MouseEvent 替身；Event 默认 bubbles:false，漏写将静默收
//   不到 → 用例假绿）。构造器经 window 取（eslint 全局表未声明 MouseEvent）。
// ---------------------------------------------------------------------------

function pointerEvent(type, x, y, init = {}) {
  return new window.MouseEvent(type, { bubbles: true, clientX: x, clientY: y, ...init })
}

// 与原生 PointerEvent 对齐的替身：jsdom MouseEvent 无 pointerType，需按用例显式补
function withPointerType(event, pointerType) {
  Object.defineProperty(event, 'pointerType', { value: pointerType })
  return event
}

function areaEl(wrapper) {
  return wrapper.find('.overview-cycle-area').element
}

// 一次完整滑动手势：区域 pointerdown → 区域 pointerup（冒泡到 window 单次判定）
async function swipeOnce(wrapper, x0, y0, x1, y1) {
  const el = areaEl(wrapper)
  el.dispatchEvent(pointerEvent('pointerdown', x0, y0))
  el.dispatchEvent(pointerEvent('pointerup', x1, y1))
  await settle()
}

const SWIPE_SUMMARY = { total_income: 3000, total_expense: 1234.56, transaction_count: 7 }

// 手势用例必须挂进文档树：up/cancel 监听在 window 上，VTU 默认容器是脱离 document 的
// div，事件冒泡断在容器根 → window 永远收不到（环境假红，非实现问题）。attachTo 后
// 冒泡链完整：区域 → …… → document → window，与真机一致。
async function mountSwipe(summaryData = SWIPE_SUMMARY) {
  getRecords.mockResolvedValue({ items: RECORDS, total: 2, page: 1, total_pages: 1 })
  getSummary.mockResolvedValue(summaryData)
  getByCategory.mockResolvedValue({ items: [] })
  const wrapper = mount(DashboardPage, { attachTo: document.body })
  await settle()
  return wrapper
}

describe('DashboardPage - 总收支大卡左右横滑切换（M1）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getRecords.mockReset()
    getSummary.mockReset()
    getByCategory.mockReset()
  })

  it('用例1（任务 5.1）: 左滑 dx=−60 → 支出→结余「一步且仅一步」，标签/指示点随同一 view 联动', async () => {
    const wrapper = await mountSwipe()
    expect(wrapper.vm.view).toBe('expense')

    await swipeOnce(wrapper, 200, 300, 140, 300)

    // 一步：落在 balance 而非连跳到 income
    expect(wrapper.vm.view).toBe('balance')
    expect(viewLabelText(wrapper)).toBe('结余')
    expect(activeDotIndex(wrapper)).toBe(2)
    expect(numberText(wrapper)).toBe(money(3000 - 1234.56))

    await settle()
    expect(wrapper.vm.view).toBe('balance') // 且仅一步：动画收尾后不追加、不回弹
    wrapper.unmount()
  })

  it('用例2（任务 5.2）: 右滑 dx=+60 → 支出→收入（prevView 反向映射 = nextView 逆运算）', async () => {
    const wrapper = await mountSwipe()

    await swipeOnce(wrapper, 140, 300, 200, 300)

    expect(wrapper.vm.view).toBe('income')
    expect(viewLabelText(wrapper)).toBe('收入')
    expect(activeDotIndex(wrapper)).toBe(0)
    expect(numberText(wrapper)).toBe(money(3000))
    wrapper.unmount()
  })

  it('用例3（任务 5.3）: 未达阈值 dx=+30、恰达阈值 dx=−48（严格 >）、斜向 dx=60/dy=90 均不判滑动', async () => {
    const wrapper = await mountSwipe()

    await swipeOnce(wrapper, 200, 300, 230, 300) // dx=+30 < 48
    expect(wrapper.vm.view).toBe('expense')

    await swipeOnce(wrapper, 300, 300, 252, 300) // dx=−48：阈值边界不满足严格大于
    expect(wrapper.vm.view).toBe('expense')

    await swipeOnce(wrapper, 200, 300, 260, 390) // dx=+60 / dy=+90：主轴为纵向
    expect(wrapper.vm.view).toBe('expense')
    expect(viewLabelText(wrapper)).toBe('支出')

    // 任务 4.1：未达标手势不置抑制窗口 → click 链完好，点击循环照常前进一位
    await wrapper.find('.overview-cycle-area').trigger('click')
    await settle()
    expect(wrapper.vm.view).toBe('balance')
    wrapper.unmount()
  })

  it('用例4（任务 5.4）: 纯 trigger(click) 点击循环保留（既有 M2 用例3 口径回归基线）', async () => {
    const wrapper = await mountSwipe()
    const area = wrapper.find('.overview-cycle-area')

    await area.trigger('click')
    await settle()
    expect(wrapper.vm.view).toBe('balance')

    await area.trigger('click')
    await settle()
    expect(wrapper.vm.view).toBe('income')

    await area.trigger('click')
    await settle()
    expect(wrapper.vm.view).toBe('expense') // 闭环：支出→结余→收入→支出不改
    wrapper.unmount()
  })

  it('用例5（任务 5.5）: 滑动后尾巴 click 被 350ms 窗口吞掉（只切一次），窗口外点击恢复（fake timers）', async () => {
    const wrapper = await mountSwipe()
    expect(wrapper.vm.view).toBe('expense')
    expect(wrapper.vm.suppressClickUntil).toBe(0)

    vi.useFakeTimers()
    try {
      vi.setSystemTime(2000000)
      const el = areaEl(wrapper)

      el.dispatchEvent(pointerEvent('pointerdown', 200, 300))
      el.dispatchEvent(pointerEvent('pointerup', 140, 300)) // dx=−60 → balance
      expect(wrapper.vm.view).toBe('balance')
      expect(wrapper.vm.suppressClickUntil).toBe(2000000 + 350) // D2：窗口 = now + 350ms

      // 同一手势尾巴派发的 click（touch 滑动后与桌面拖拽后浏览器都必派）→ 吞掉
      el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
      expect(wrapper.vm.view).toBe('balance')

      vi.advanceTimersByTime(300) // 2000300 仍在窗口内
      el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
      expect(wrapper.vm.view).toBe('balance')

      vi.advanceTimersByTime(100) // 2000400 已过窗口 → 点击恢复
      el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
      expect(wrapper.vm.view).toBe('income')
    } finally {
      vi.useRealTimers()
    }
    wrapper.unmount()
  })

  it('用例6（任务 5.6）: ?raw 手势红线——pan-y / 阈值 48 / 卸载清理 / 零默认行为阻止 / 不监听 move 阶段', () => {
    // 滑动容器 touch-action（D1：纵向滚动交还原生，横滑归 JS）
    expect(dashboardSource).toMatch(/\.overview-cycle-area \{[^}]*touch-action:\s*pan-y;/)
    // 阈值 48px（D2）
    expect(dashboardSource).toMatch(/const SWIPE_THRESHOLD = 48/)
    // 卸载清理（需求通用约束·性能）
    expect(dashboardSource).toMatch(/onBeforeUnmount\(onDragAbort\)/)
    // up/cancel 挂 window（与本组合成事件 bubbles 口径配对）+ 幂等摘除
    expect(dashboardSource).toMatch(/window\.addEventListener\('pointerup', onPointerUp\)/)
    expect(dashboardSource).toMatch(/window\.addEventListener\('pointercancel', onDragAbort\)/)
    expect(dashboardSource).toMatch(/window\.removeEventListener\('pointerup', onPointerUp\)/)
    expect(dashboardSource).toMatch(/window\.removeEventListener\('pointercancel', onDragAbort\)/)
    // 实现红线：零默认行为阻止（不阻断 click 链与键盘 Enter→cycleView）+ 不监听 move 阶段
    expect(dashboardSource).not.toMatch(/preventDefault/)
    expect(dashboardSource).not.toMatch(/pointermove/)
    // 点击保留：@click 与 @pointerdown 同区并存
    expect(dashboardSource).toMatch(/@click="cycleView"/)
    expect(dashboardSource).toMatch(/@pointerdown="onPointerDown"/)
    // 状态源唯一（§8-1）：滑动与点击都走 stepView，prevView 为 nextView 反向映射
    expect(dashboardSource).toMatch(/const prevView = \{ expense: 'income', balance: 'expense', income: 'balance' \}/)
    expect(dashboardSource).toMatch(
      /function stepView\(dir\) \{[^}]*dir > 0 \? nextView\[view\.value\] : prevView\[view\.value\]/,
    )
    expect(dashboardSource).toMatch(/if \(Date\.now\(\) < suppressClickUntil\.value\) return/)
    expect(dashboardSource).toMatch(/stepView\(1\)/)
    expect(dashboardSource).toMatch(/stepView\(dx < 0 \? 1 : -1\)/)
  })

  it('用例7（任务 4.4）: pointercancel（纵向滚动接管）→ 清理监听不残留，后续 pointerup 不误判', async () => {
    const wrapper = await mountSwipe()
    const el = areaEl(wrapper)

    el.dispatchEvent(pointerEvent('pointerdown', 200, 300))
    window.dispatchEvent(pointerEvent('pointercancel', 200, 300))
    expect(wrapper.vm.view).toBe('expense')

    // 监听已摘除：无新 pointerdown 的 pointerup 不产生任何判定
    el.dispatchEvent(pointerEvent('pointerup', 100, 300))
    await settle()
    expect(wrapper.vm.view).toBe('expense')

    // 下一次完整手势照常工作（既不残留也不丢失）
    await swipeOnce(wrapper, 200, 300, 140, 300)
    expect(wrapper.vm.view).toBe('balance')
    wrapper.unmount()
  })

  it('用例8（任务 2.2）: 鼠标非左键 pointerdown 直接 return（不记起点、不挂监听）；左键同位移必切', async () => {
    const wrapper = await mountSwipe()
    const el = areaEl(wrapper)

    el.dispatchEvent(withPointerType(pointerEvent('pointerdown', 200, 300, { button: 2 }), 'mouse'))
    el.dispatchEvent(withPointerType(pointerEvent('pointerup', 100, 300, { button: 2 }), 'mouse'))
    await settle()
    expect(wrapper.vm.view).toBe('expense')
    // 安全网：若守卫失效残留了 window 监听，此处摘净以免污染后续用例
    window.dispatchEvent(pointerEvent('pointercancel', 0, 0))

    // 对照：左键（button 0）同位移走满手势链路
    el.dispatchEvent(withPointerType(pointerEvent('pointerdown', 200, 300, { button: 0 }), 'mouse'))
    el.dispatchEvent(withPointerType(pointerEvent('pointerup', 100, 300, { button: 0 }), 'mouse'))
    await settle()
    expect(wrapper.vm.view).toBe('balance')
    wrapper.unmount()
  })

  it('用例9（任务 4.6）: 快速连续滑动每次 pointerup 恰一步，末态=最后一次 view，无残留节点', async () => {
    const wrapper = await mountSwipe({
      total_income: 2000,
      total_expense: 500,
      transaction_count: 2,
    })
    const el = areaEl(wrapper)

    // 四段左滑不 await：expense→balance→income→expense→balance
    for (let i = 0; i < 4; i += 1) {
      el.dispatchEvent(pointerEvent('pointerdown', 200, 300))
      el.dispatchEvent(pointerEvent('pointerup', 140, 300))
    }
    expect(wrapper.vm.view).toBe('balance')

    await settle()
    expect(wrapper.vm.view).toBe('balance') // mode="out-in" 排队后末态不漂移
    expect(wrapper.findAll('.amount-number')).toHaveLength(1)
    expect(wrapper.findAll('.view-dot')).toHaveLength(3)
    expect(activeDotIndex(wrapper)).toBe(2)
    expect(viewLabelText(wrapper)).toBe('结余')
    expect(numberText(wrapper)).toBe(money(2000 - 500))
    wrapper.unmount()
  })

  it('用例10（任务 4.5）: summary 加载中滑动照常切换视图，数值 || 0 兜底（现状行为）', async () => {
    let resolveSummary
    getRecords.mockResolvedValue({ items: [], total: 0, page: 1, total_pages: 1 })
    getByCategory.mockResolvedValue({ items: [] })
    getSummary.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSummary = resolve
        }),
    )
    const wrapper = mount(DashboardPage, { attachTo: document.body })
    await nextTick()

    expect(wrapper.vm.summary).toBeNull()
    expect(numberText(wrapper)).toBe(money(0))

    await swipeOnce(wrapper, 200, 300, 140, 300) // → balance
    expect(wrapper.vm.view).toBe('balance')
    expect(viewLabelText(wrapper)).toBe('结余')
    expect(numberText(wrapper)).toBe(money(0))

    resolveSummary({ total_income: 800, total_expense: 300.25, transaction_count: 4 })
    await settle()
    expect(wrapper.vm.view).toBe('balance') // 数据到达不回滚视图
    expect(numberText(wrapper)).toBe(money(800 - 300.25))
    wrapper.unmount()
  })

  it('用例11（任务 3.1）: 手势隔离复查——右上跳统计区不在点按区内，其 pointer 链零交叉', async () => {
    const wrapper = await mountSwipe()

    // 结构隔离：.overview-jump 不是 .overview-cycle-area 的后代
    expect(wrapper.find('.overview-cycle-area').find('.overview-jump').exists()).toBe(false)

    const jump = wrapper.find('.overview-jump').element
    jump.dispatchEvent(pointerEvent('pointerdown', 300, 100))
    jump.dispatchEvent(pointerEvent('pointerup', 100, 100)) // 大位移也不判滑动（无监听）
    await settle()
    expect(wrapper.vm.view).toBe('expense')

    // 点按区自身手势不受影响
    await swipeOnce(wrapper, 200, 300, 140, 300)
    expect(wrapper.vm.view).toBe('balance')
    wrapper.unmount()
  })
})
