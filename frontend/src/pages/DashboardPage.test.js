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

  it('用例9: 点按区结构（role=button + user-select）与动画字面量口径（§1.2 待 M14 回填）', () => {
    expect(dashboardSource).toMatch(/class="overview-cycle-area[^"]*"\s+role="button"/)
    expect(dashboardSource).toMatch(/@click="cycleView"/)
    expect(dashboardSource).toMatch(/user-select:\s*none/)
    // 切换动画：out-in + :key="view"，时长/缓动为与 --expand-duration/--expand-easing 同值的字面量
    expect(dashboardSource).toMatch(/<Transition name="amount-switch" mode="out-in">/)
    expect(dashboardSource).toMatch(/:key="view"/)
    expect(dashboardSource).toMatch(/opacity 220ms cubic-bezier\(0\.25, 0\.8, 0\.5, 1\)/)
    expect(dashboardSource).toMatch(/transform 220ms cubic-bezier\(0\.25, 0\.8, 0\.5, 1\)/)
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
const EXPENSE_COLOR = /#FF6B6B|rgb\(255,\s*107,\s*107\)/i
const INCOME_COLOR = /#20C997|rgb\(32,\s*201,\s*151\)/i

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

    const expenseAmount = rows[0].find('.font-weight-bold')
    expect(expenseAmount.attributes('style')).toMatch(EXPENSE_COLOR)
    expect(expenseAmount.text()).toBe('-¥58.50')

    const incomeAmount = rows[1].find('.font-weight-bold')
    expect(incomeAmount.attributes('style')).toMatch(INCOME_COLOR)
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
