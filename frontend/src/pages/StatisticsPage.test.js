import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import dayjs from 'dayjs'

const CATEGORIES = [
  { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
  { id: 2, name: '出行', type: 'expense', icon: 'mdi-bus' },
  { id: 3, name: '购物', type: 'expense', icon: 'mdi-cart' },
  { id: 9, name: '工资', type: 'income', icon: 'mdi-wallet' },
]

function makeBudget(overrides) {
  return {
    id: 11,
    category_id: 1,
    category_name: '餐饮',
    type: 'expense',
    month: dayjs().format('YYYY-MM'),
    amount: 100,
    spent: 10,
    remaining: 90,
    percentage: 10,
    ...overrides,
  }
}

// ── Mocks ──────────────────────────────────────────────────────────
vi.mock('@/api/statistics', () => ({
  getSummary: vi.fn().mockResolvedValue({ total_income: 0, total_expense: 0 }),
  getByCategory: vi.fn().mockResolvedValue({ items: [] }),
  getTrend: vi.fn().mockResolvedValue({ items: [] }),
}))

vi.mock('@/api/budgets', () => ({
  getBudgets: vi.fn().mockResolvedValue([]),
  getBudgetYearSummary: vi.fn().mockResolvedValue({ months: [] }),
  batchSetBudgets: vi.fn().mockResolvedValue([]),
  deleteBudget: vi.fn().mockResolvedValue({}),
}))

vi.mock('@/stores/useCategoriesStore', () => ({
  useCategoriesStore: () => ({
    categories: CATEGORIES,
    loaded: true,
    fetchCategories: vi.fn().mockResolvedValue([]),
  }),
}))

vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({ showToast: vi.fn() }),
}))

// chart.js 在 jsdom 下无法绘制，替换为轻量桩件
// M7：桩件声明 data/options props（便于配置断言），并以 mounted 计数验证「实例全程存活、未被重建」
const chartStub = vi.hoisted(() => ({ barMounts: 0, lineMounts: 0 }))

vi.mock('vue-chartjs', () => ({
  Bar: {
    name: 'Bar',
    props: {
      data: { type: Object, default: null },
      options: { type: Object, default: null },
    },
    mounted() {
      chartStub.barMounts += 1
    },
    template: '<div class="chart-stub bar-stub"></div>',
  },
  Line: {
    name: 'Line',
    props: {
      data: { type: Object, default: null },
      options: { type: Object, default: null },
    },
    mounted() {
      chartStub.lineMounts += 1
    },
    template: '<div class="chart-stub line-stub"></div>',
  },
}))

import { getBudgets, getBudgetYearSummary, batchSetBudgets, deleteBudget } from '@/api/budgets'
import { getByCategory, getTrend } from '@/api/statistics'
import StatisticsPage from './StatisticsPage.vue'
import settingsPageSource from './SettingsPage.vue?raw'
import statisticsPageSource from './StatisticsPage.vue?raw'

async function mountPage() {
  const wrapper = mount(StatisticsPage)
  await flushPromises()
  return wrapper
}

// 未安装 Vuetify 时 v-progress-linear 被降级渲染为同名元素，color 直接落在属性上
function barColors(wrapper) {
  return wrapper.findAll('v-progress-linear').map((bar) => bar.attributes('color'))
}

describe('StatisticsPage - M6 预算区块', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getBudgets.mockResolvedValue([])
    getBudgetYearSummary.mockResolvedValue({ months: [] })
    // 固定"今天"为 2026-01-15，使年月偏移断言可预期（只冻结 Date）
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-01-15T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // 用例 1
  it('用例1: 默认月视图以当前年月调用 getBudgets，并渲染概览与分类列表', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({ id: 11, category_id: 1, amount: 1000, spent: 200 }),
    ])

    const wrapper = await mountPage()

    expect(getBudgets).toHaveBeenCalledWith({ month: '2026-01' })
    expect(getBudgetYearSummary).not.toHaveBeenCalled()

    const text = wrapper.text()
    expect(text).toContain('预算管理')
    expect(text).toContain('2026年1月 预算')
    expect(text).toContain('餐饮')
    expect(wrapper.vm.budgetMonth).toBe('2026-01')
  })

  // 用例 1 补充：无预算时月视图空态
  it('用例1b: 月视图无预算时显示空态文案', async () => {
    getBudgets.mockResolvedValue([])
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('暂无预算设置，点击上方按钮添加分类预算')
  })

  // 用例 2
  it('用例2: prevPeriod 翻到上一年 12 月时 getBudgets 参数随 budgetMonth 变化', async () => {
    const wrapper = await mountPage()
    expect(getBudgets).toHaveBeenLastCalledWith({ month: '2026-01' })

    await wrapper.vm.prevPeriod()
    await flushPromises()
    expect(getBudgets).toHaveBeenLastCalledWith({ month: '2025-12' })

    await wrapper.vm.nextPeriod()
    await flushPromises()
    expect(getBudgets).toHaveBeenLastCalledWith({ month: '2026-01' })

    expect(wrapper.vm.budgetMonth).toBe('2026-01')
  })

  it('用例2b: 月视图新增预算写入所选月而非系统当前月', async () => {
    const wrapper = await mountPage()

    // 翻到上一月（2025-12）后新增
    await wrapper.vm.prevPeriod()
    await flushPromises()

    wrapper.vm.openBudgetAddDialog()
    wrapper.vm.budgetForm = { category_id: 2, amount: 500 }
    await wrapper.vm.saveBudget()
    await flushPromises()

    expect(batchSetBudgets).toHaveBeenCalledWith({
      month: '2025-12',
      budgets: [{ category_id: 2, amount: 500 }],
    })
  })

  // 用例 3
  it('用例3: 切到年视图调用 getBudgetYearSummary，点击月份行下钻回月视图且 offset 指向该月', async () => {
    const months = Array.from({ length: 12 }, (_, i) => {
      const month = `2026-${String(i + 1).padStart(2, '0')}`
      const has = i === 2
      return {
        month,
        total_amount: has ? 1200 : 0,
        total_spent: has ? 900 : 0,
        budgets: has
          ? [makeBudget({ id: 21, category_id: 1, month, amount: 1200, spent: 900 })]
          : [],
      }
    })
    getBudgetYearSummary.mockResolvedValue({ year: 2026, months })

    const wrapper = await mountPage()
    wrapper.vm.switchPeriod('yearly')
    await flushPromises()

    expect(getBudgetYearSummary).toHaveBeenCalledWith({ year: '2026' })
    const text = wrapper.text()
    expect(text).toContain('2026年')
    expect(text).toContain('3月')
    expect(text).toContain('暂无预算')

    // 第 3 行 = 3 月，点击下钻
    const rows = wrapper.findAll('.budget-month-row')
    expect(rows.length).toBe(12)
    await rows[2].trigger('click')
    await flushPromises()

    expect(wrapper.vm.periodType).toBe('monthly')
    expect(wrapper.vm.periodOffset).toBe(2)
    expect(wrapper.vm.budgetMonth).toBe('2026-03')
    expect(getBudgets).toHaveBeenLastCalledWith({ month: '2026-03' })
  })

  it('用例3b: 年视图整年无预算时显示"该年暂无预算设置"', async () => {
    const months = Array.from({ length: 12 }, (_, i) => ({
      month: `2026-${String(i + 1).padStart(2, '0')}`,
      total_amount: 0,
      total_spent: 0,
      budgets: [],
    }))
    getBudgetYearSummary.mockResolvedValue({ year: 2026, months })

    const wrapper = await mountPage()
    wrapper.vm.switchPeriod('yearly')
    await flushPromises()

    expect(wrapper.text()).toContain('该年暂无预算设置')
    expect(wrapper.text()).not.toContain('2026年1月 预算')
  })

  // 用例 4
  it('用例4: 进度条阈值配色分支（>80% error / >50% warning / 其余 success|primary）', async () => {
    // >80%：概览与分类行都是 error
    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 90 })])
    let wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['error', 'error'])

    // >50%：概览 warning、分类行 warning
    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 60 })])
    wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['warning', 'warning'])

    // 其余：概览 success、分类行 primary
    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 10 })])
    wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['success', 'primary'])

    await nextTick()
  })

  it('用例4b: 年视图逐月迷你进度条沿用同一阈值配色', async () => {
    const months = Array.from({ length: 12 }, (_, i) => ({
      month: `2026-${String(i + 1).padStart(2, '0')}`,
      total_amount: 100,
      total_spent: i === 0 ? 90 : i === 1 ? 60 : 10,
      budgets: [makeBudget({ amount: 100, spent: i === 0 ? 90 : i === 1 ? 60 : 10 })],
    }))
    getBudgetYearSummary.mockResolvedValue({ year: 2026, months })

    const wrapper = await mountPage()
    wrapper.vm.switchPeriod('yearly')
    await flushPromises()

    const colors = barColors(wrapper)
    expect(colors.length).toBe(12)
    expect(colors[0]).toBe('error')
    expect(colors[1]).toBe('warning')
    expect(colors[2]).toBe('primary')
  })

  // 迁移等价：行内编辑与删除
  it('用例5: 行内编辑走 batchSetBudgets（月份为所选月），删除走 deleteBudget', async () => {
    getBudgets.mockResolvedValue([makeBudget({ id: 31, category_id: 1, amount: 800, spent: 100 })])
    const wrapper = await mountPage()

    const item = wrapper.vm.enrichedBudgets[0]
    wrapper.vm.startBudgetEdit(item)
    expect(wrapper.vm.editingBudget).toBe(1)
    expect(wrapper.vm.editBudgetAmount).toBe(800)

    wrapper.vm.editBudgetAmount = 900
    await wrapper.vm.saveBudgetEdit(item)
    await flushPromises()
    expect(batchSetBudgets).toHaveBeenCalledWith({
      month: '2026-01',
      budgets: [{ category_id: 1, amount: 900 }],
    })
    expect(wrapper.vm.editingBudget).toBeNull()

    wrapper.vm.confirmDeleteBudget({ id: 31, category_id: 1, category_name: '餐饮' })
    expect(wrapper.vm.showDeleteBudgetDialog).toBe(true)
    wrapper.vm.deletingBudget = { id: 31, category_id: 1, category_name: '餐饮' }
    await wrapper.vm.handleDeleteBudget()
    await flushPromises()
    expect(deleteBudget).toHaveBeenCalledWith(31)
    expect(wrapper.vm.showDeleteBudgetDialog).toBe(false)
  })

  it('用例6: 分类下拉只列出未设置预算的支出分类', async () => {
    getBudgets.mockResolvedValue([makeBudget({ category_id: 1 })])
    const wrapper = await mountPage()

    const ids = wrapper.vm.availableBudgetCategories.map((c) => c.id)
    expect(ids).toEqual([2, 3])
    expect(wrapper.vm.enrichedBudgets[0].icon).toBe('mdi-food')
  })

  // 回归红线：迁移后设置页不得残留任何预算代码/入口
  it('用例7: SettingsPage 无 budget 残留（grep 源码断言）', () => {
    expect(settingsPageSource).not.toMatch(/budget/i)
    expect(settingsPageSource).not.toContain('预算')
    expect(settingsPageSource).not.toMatch(/BUDGET_COLORS|currentMonth|formatAmount/)
  })
})

// ── M7 分类柱状图过渡动画（设计 §7.4）────────────────────────────────
describe('StatisticsPage - M7 分类柱状图过渡动画', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    chartStub.barMounts = 0
    chartStub.lineMounts = 0
    getByCategory.mockResolvedValue({ items: [] })
    getTrend.mockResolvedValue({ items: [] })
    getBudgets.mockResolvedValue([])
    getBudgetYearSummary.mockResolvedValue({ months: [] })
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-01-15T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
    // 不污染前序/后续用例的默认桩返回
    getByCategory.mockResolvedValue({ items: [] })
    getTrend.mockResolvedValue({ items: [] })
  })

  // 5.1 配置断言
  it('用例M7-1: Bar 收到 animation/transitions 动画配置，scales 现状保留', async () => {
    const wrapper = await mountPage()
    const options = wrapper.findComponent({ name: 'Bar' }).props('options')

    expect(options.animation).toEqual({ duration: 750, easing: 'easeOutQuart' })
    expect(options.transitions.active).toEqual({ duration: 750, easing: 'easeOutQuart' })
    // 现状配置保留（类目轴 x 去网格、数值轴 y beginAtZero）
    expect(options.scales.x.grid.display).toBe(false)
    expect(options.scales.y.beginAtZero).toBe(true)
    expect(options.plugins.legend.display).toBe(false)
    expect(options.responsive).toBe(true)
    expect(options.maintainAspectRatio).toBe(false)
  })

  // 5.2 空态回归 + 4.3 月↔年切换
  it('用例M7-2: 空数据时 Bar 仍挂载且叠加覆盖层；转非空覆盖层消失、图表实例不重建', async () => {
    getByCategory.mockResolvedValue({ items: [] })
    const wrapper = await mountPage()

    // canvas 常驻：Bar 桩件在空数据下依然渲染，且叠加空态覆盖层
    expect(wrapper.find('.chart-stub').exists()).toBe(true)
    expect(wrapper.find('.bar-stub').exists()).toBe(true)
    expect(wrapper.find('.chart-holder').exists()).toBe(true)
    const overlay = wrapper.find('.chart-empty-overlay')
    expect(overlay.exists()).toBe(true)
    expect(overlay.text()).toContain('暂无数据')
    // 明细列表为非动画元素，仍按 v-if 隐藏（2.5）
    expect(wrapper.find('.category-list').exists()).toBe(false)

    const mountsAfterEmpty = chartStub.barMounts

    // 转非空：覆盖层消失、柱表容器与实例持续存活
    getByCategory.mockResolvedValue({
      items: [
        { category_name: '餐饮', total: 300 },
        { category_name: '出行', total: 120 },
      ],
    })
    await wrapper.vm.nextPeriod()
    await flushPromises()

    expect(wrapper.find('.chart-empty-overlay').exists()).toBe(false)
    expect(wrapper.find('.bar-stub').exists()).toBe(true)
    expect(wrapper.find('.category-list').exists()).toBe(true)
    expect(chartStub.barMounts).toBe(mountsAfterEmpty)

    // 月↔年视图切换：labels 整体替换，实例仍不重建
    getByCategory.mockResolvedValue({
      items: [{ category_name: '购物', total: 900 }],
    })
    wrapper.vm.switchPeriod('yearly')
    await flushPromises()

    expect(wrapper.vm.periodType).toBe('yearly')
    expect(wrapper.vm.categoryBarData.labels).toEqual(['购物'])
    expect(wrapper.find('.chart-empty-overlay').exists()).toBe(false)
    expect(chartStub.barMounts).toBe(mountsAfterEmpty)
  })

  // 5.3 + 3.1 防闪 0
  it('用例M7-3: 切期 pending 期间 categoryBarData 保持旧值，resolve 后 labels/data 同步', async () => {
    getByCategory.mockResolvedValue({
      items: [
        { category_name: '餐饮', total: 300 },
        { category_name: '出行', total: 120 },
      ],
    })
    const wrapper = await mountPage()
    expect(wrapper.vm.categoryBarData.labels).toEqual(['餐饮', '出行'])
    expect(wrapper.vm.categoryBarData.datasets[0].data).toEqual([300, 120])

    let resolvePending
    getByCategory.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePending = resolve
        })
    )
    wrapper.vm.nextPeriod()
    await flushPromises()

    // pending：未置空、过渡起点仍是当前显示值（不闪 0）
    expect(wrapper.vm.categoryStats.length).toBe(2)
    expect(wrapper.vm.categoryBarData.datasets[0].data).toEqual([300, 120])
    expect(wrapper.find('.chart-empty-overlay').exists()).toBe(false)

    // resolve：按索引重映射，数量差即时消化（4.2）
    resolvePending({ items: [{ category_name: '购物', total: 500 }] })
    await flushPromises()
    expect(wrapper.vm.categoryBarData.labels).toEqual(['购物'])
    expect(wrapper.vm.categoryBarData.datasets[0].data).toEqual([500])
    expect(chartStub.barMounts).toBe(1)
  })

  // 2.4 空数据形状：labels 与 data 均为空，柱条动画缩到 0
  it('用例M7-4: 空数据时 categoryBarData 为空 labels + 单数据集空 data（不卸载 canvas）', async () => {
    getByCategory.mockResolvedValue({ items: [] })
    const wrapper = await mountPage()
    const data = wrapper.vm.categoryBarData

    expect(data.labels).toEqual([])
    expect(data.datasets.length).toBe(1)
    expect(data.datasets[0].data).toEqual([])
    expect(wrapper.vm.categoryStats).toEqual([])
  })

  // 4.4 + 红线：局部配置、不翻转轴向、不清空、无手工动画队列；2.1-2.3 覆盖层结构
  it('用例M7-5: 动画配置仅落在 barChartOptions，Line 图不受影响（源码 + 运行时断言）', async () => {
    // 收支趋势 Line 图有数据时才渲染，取不到 props 会让断言空转
    getTrend.mockResolvedValue({
      items: [{ period: '2026-01-01', income: 10, expense: 5 }],
    })
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('收支趋势')
    const lineOptions = wrapper.findComponent({ name: 'Line' }).props('options')
    expect(lineOptions).toBeTruthy()
    expect(lineOptions.animation).toBeUndefined()
    expect('animation' in lineOptions).toBe(false)

    // 无全局 Chart.js defaults 污染、不加 indexAxis 翻转方向
    expect(statisticsPageSource).not.toMatch(/(ChartJS|Chart)\s*\.\s*defaults/)
    expect(statisticsPageSource).not.toContain('indexAxis')
    // 禁止「先清空再赋值」
    expect(statisticsPageSource).not.toContain('categoryStats.value = []')
    // 无手工 rAF/队列驱动动画（4.1：由 Chart.js update 自身打断重估）
    expect(statisticsPageSource).not.toMatch(/requestAnimationFrame|setTimeout\([^)]*chart/i)

    // 覆盖层结构：Bar 外层无 v-if，容器定位 + surface 底
    const holder = statisticsPageSource.match(/<div class="chart-holder">[\s\S]*?<\/div>/)
    expect(holder).not.toBeNull()
    expect(holder[0]).toContain('<Bar')
    expect(holder[0]).not.toMatch(/<Bar[^>]*v-if/)
    expect(statisticsPageSource).toMatch(
      /v-if="categoryStats\.length === 0"[^>]*chart-empty-overlay/
    )
    expect(statisticsPageSource).toMatch(/\.chart-holder\s*\{[^}]*position:\s*relative/s)
    expect(statisticsPageSource).toMatch(
      /\.chart-empty-overlay\s*\{[^}]*background:\s*rgb\(var\(--v-theme-surface\)\)/s
    )
  })
})
