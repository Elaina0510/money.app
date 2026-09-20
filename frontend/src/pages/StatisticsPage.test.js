import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import dayjs from 'dayjs'

// v1.4.3 M8 起分类收支共用单套列表（无 type 语义）——预算对话框候选即该全量列表
const CATEGORIES = [
  { id: 1, name: '餐饮', icon: 'mdi-food' },
  { id: 2, name: '出行', icon: 'mdi-bus' },
  { id: 3, name: '购物', icon: 'mdi-cart' },
  { id: 9, name: '工资', icon: 'mdi-wallet' },
]

// v1.4.3 M12：BudgetDetail 新形（每月多条命名预算，无顶层 category_id/type）
function makeBudget(overrides) {
  return {
    id: 11,
    month: dayjs().format('YYYY-MM'),
    name: '日常开销',
    amount: 1000,
    spent: 200,
    remaining: 800,
    percentage: 20,
    scope_mode: 'include',
    category_ids: [1],
    category_names: ['餐饮'],
    details: [{ category_id: 1, category_name: '餐饮', icon: 'mdi-food', spent: 200 }],
    created_at: '2026-01-01 00:00:00',
    updated_at: '2026-01-01 00:00:00',
    ...overrides,
  }
}

// ── Mocks ──────────────────────────────────────────────────────────
vi.mock('@/api/statistics', () => ({
  getSummary: vi.fn().mockResolvedValue({ total_income: 0, total_expense: 0 }),
  getByCategory: vi.fn().mockResolvedValue({ items: [] }),
  getTrend: vi.fn().mockResolvedValue({ items: [] }),
}))

// v1.4.3 M12：createBudget（POST 纯创建）/ updateBudget（PUT 全字段）替掉整月批量封装
vi.mock('@/api/budgets', () => ({
  getBudgets: vi.fn().mockResolvedValue([]),
  getBudgetYearSummary: vi.fn().mockResolvedValue({ months: [] }),
  createBudget: vi.fn().mockResolvedValue({}),
  updateBudget: vi.fn().mockResolvedValue({}),
  deleteBudget: vi.fn().mockResolvedValue({}),
}))

const appStoreMock = vi.hoisted(() => ({ showToast: vi.fn() }))

vi.mock('@/stores/useCategoriesStore', () => ({
  useCategoriesStore: () => ({
    categories: CATEGORIES,
    loaded: true,
    fetchCategories: vi.fn().mockResolvedValue([]),
  }),
}))

vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => appStoreMock,
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

import {
  getBudgets,
  getBudgetYearSummary,
  createBudget,
  updateBudget,
  deleteBudget,
} from '@/api/budgets'
import { getByCategory, getTrend } from '@/api/statistics'
import StatisticsPage from './StatisticsPage.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
// v1.4.3 M14：预算对话框外壳收编断言所需
import AppDialog from '@/components/common/AppDialog.vue'
import settingsPageSource from './SettingsPage.vue?raw'
import statisticsPageSource from './StatisticsPage.vue?raw'
import budgetsApiSource from '../api/budgets.js?raw'
// v1.4.3 M14：展开动画口径单点定义（:root 变量 + slide-y 一处覆写）源码锁
// （.scss 走 ?raw 会被样式管线返回空串 → 直接读文件文本）
import fs from 'node:fs'
import path from 'node:path'
import { cwd } from 'node:process'

const globalStyleSource = fs.readFileSync(path.resolve(cwd(), 'src/styles/global.scss'), 'utf8')

async function mountPage() {
  const wrapper = mount(StatisticsPage)
  await flushPromises()
  return wrapper
}

// 未安装 Vuetify 时 v-progress-linear 被降级渲染为同名元素，color 直接落在属性上
// 月视图 DOM 顺序：[0] 月度总览小卡 → 其后按预算卡列表逐卡一条
function barColors(wrapper) {
  return wrapper.findAll('v-progress-linear').map((bar) => bar.attributes('color'))
}

function reloadCount(api) {
  return api.mock.calls.length
}

// 未装 Vuetify 时 <v-btn> 降级为同名元素，:disabled 落为字符串属性（"true"/"false" 皆有值），
// 故按字符串真值判定禁用态
function saveBtnDisabled(wrapper) {
  const raw = wrapper.find('.budget-save-btn').attributes('disabled')
  return raw !== undefined && raw !== 'false'
}

describe('StatisticsPage - M12 每月多条命名预算（预算卡列表）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getBudgets.mockResolvedValue([])
    getBudgetYearSummary.mockResolvedValue({ months: [] })
    createBudget.mockResolvedValue({ id: 99 })
    updateBudget.mockResolvedValue({ id: 1 })
    deleteBudget.mockResolvedValue({})
    // 固定"今天"为 2026-01-15，使年月偏移断言可预期（只冻结 Date）
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-01-15T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // 任务 5.1 + 5.2：月视图渲染预算卡片列表（名称/已用/预算/进度/简述各一）
  it('用例1: 月视图渲染多条预算卡片列表，月度总览 = Σ 各预算（D4 口径）', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({
        id: 11,
        name: '日常开销',
        amount: 3000,
        spent: 1850,
        remaining: 1150,
        percentage: 61.7,
        category_ids: [1, 2, 3],
        category_names: ['餐饮', '出行', '购物'],
        details: [
          { category_id: 1, category_name: '餐饮', icon: 'mdi-food', spent: 800 },
          { category_id: 2, category_name: '出行', icon: 'mdi-bus', spent: 350 },
          { category_id: 3, category_name: '购物', icon: 'mdi-cart', spent: 700 },
        ],
      }),
      makeBudget({ id: 12, name: '学习', amount: 500, spent: 100, category_ids: [3], category_names: ['购物'] }),
    ])

    const wrapper = await mountPage()

    expect(getBudgets).toHaveBeenCalledWith({ month: '2026-01' })
    expect(getBudgetYearSummary).not.toHaveBeenCalled()
    expect(wrapper.vm.budgetMonth).toBe('2026-01')

    const cards = wrapper.findAll('.budget-card')
    expect(cards.length).toBe(2)

    const first = cards[0]
    // 名称 / 范围标签 / 已用与预算金额 / 进度百分比 / 覆盖简述 / 语义提示各一
    expect(first.find('.budget-name').text()).toBe('日常开销')
    expect(first.find('.budget-scope-chip').text()).toBe('包含')
    expect(first.find('.budget-spent').text()).toContain('1,850.00')
    expect(first.find('.budget-amount').text()).toContain('3,000.00')
    expect(first.find('.budget-percent').text()).toBe('61.7%')
    expect(first.find('.budget-scope').text()).toContain('覆盖：餐饮、出行等 3 类')
    expect(first.find('.budget-scope-hint').text()).toBe('仅计入所选分类')
    expect(cards[1].find('.budget-name').text()).toBe('学习')
    expect(cards[1].find('.budget-scope').text()).toContain('购物')

    // 进度条：总览 + 每卡各一条；总览 1950/3500=55.7%、卡1 61.7%、卡2 20%
    expect(barColors(wrapper)).toEqual(['warning', 'warning', 'primary'])

    // 月度总览小卡保留（任务 5.2），金额 = Σ 各预算
    const text = wrapper.text()
    expect(text).toContain('预算管理')
    expect(text).toContain('2026年1月 预算')
    expect(text).toContain('3,500.00')
    expect(wrapper.vm.totalBudget).toBe(3500)
    expect(wrapper.vm.totalSpent).toBe(1950)
  })

  // 任务 5.1 空态引导（旧「添加分类预算」口径随每分类一条预算模型一并反转）
  it('用例1b: 月视图无预算时显示新增引导空态', async () => {
    getBudgets.mockResolvedValue([])
    const wrapper = await mountPage()
    expect(wrapper.findAll('.budget-card').length).toBe(0)
    const text = wrapper.text()
    expect(text).toContain('暂无预算，点击右上角「新增预算」为该月创建第一条命名预算')
    expect(text).not.toContain('添加分类预算')
  })

  // 任务 8.1 周期翻页（GET 参数随所选月变化，行为不变）
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

  // 任务 2.2 / 7.1：新增走 POST 纯创建，月份取所选月（原批量封装已下线）
  it('用例2b: 新增预算走 createBudget(POST 纯创建)，month = 所选月而非系统当前月', async () => {
    const wrapper = await mountPage()

    // 翻到上一月（2025-12）后新增
    await wrapper.vm.prevPeriod()
    await flushPromises()

    wrapper.vm.openBudgetAddDialog()
    expect(wrapper.vm.showBudgetDialog).toBe(true)
    expect(wrapper.vm.budgetForm).toEqual({
      id: null,
      month: '2025-12',
      name: '',
      amount: 0,
      scope_mode: 'include',
      category_ids: [],
    })

    wrapper.vm.budgetForm = {
      id: null,
      month: '2025-12',
      name: '日常开销',
      amount: 3000,
      scope_mode: 'include',
      category_ids: [1, 2],
    }
    const before = reloadCount(getBudgets)
    await wrapper.vm.saveBudget()
    await flushPromises()

    // 载荷字段精确（POST 纯创建带 month）
    expect(createBudget).toHaveBeenCalledWith({
      month: '2025-12',
      name: '日常开销',
      amount: 3000,
      scope_mode: 'include',
      category_ids: [1, 2],
    })
    expect(updateBudget).not.toHaveBeenCalled()
    expect(wrapper.vm.showBudgetDialog).toBe(false)
    // 保存后重拉
    expect(reloadCount(getBudgets)).toBe(before + 1)
  })

  // 任务 6.2：校验联动（include 0 选禁用保存；exclude 允许 0 选 = 全部分类）
  it('用例2c: include 未选分类时保存禁用并提示，改 exclude 后允许 0 选并提交', async () => {
    const wrapper = await mountPage()
    wrapper.vm.openBudgetAddDialog()
    wrapper.vm.budgetForm = {
      id: null,
      month: '2026-01',
      name: '日常开销',
      amount: 500,
      scope_mode: 'include',
      category_ids: [],
    }
    await nextTick()

    expect(wrapper.vm.budgetIncludeEmpty).toBe(true)
    expect(wrapper.vm.budgetFormValid).toBe(false)
    expect(wrapper.vm.budgetScopeError).toBe('包含模式至少需要选择 1 个分类')
    expect(saveBtnDisabled(wrapper)).toBe(true)
    expect(wrapper.find('.budget-dialog-error').text()).toContain('包含模式至少需要选择 1 个分类')

    await wrapper.vm.saveBudget()
    await flushPromises()
    expect(createBudget).not.toHaveBeenCalled()

    // exclude：0 选合法（= 全部分类），提示改为语义说明
    wrapper.vm.budgetForm = { ...wrapper.vm.budgetForm, scope_mode: 'exclude' }
    await nextTick()
    expect(wrapper.vm.budgetFormValid).toBe(true)
    expect(wrapper.vm.budgetScopeError).toBe('')
    expect(wrapper.find('.budget-dialog-error').exists()).toBe(false)
    expect(saveBtnDisabled(wrapper)).toBe(false)

    await wrapper.vm.saveBudget()
    await flushPromises()
    expect(createBudget).toHaveBeenCalledWith({
      month: '2026-01',
      name: '日常开销',
      amount: 500,
      scope_mode: 'exclude',
      category_ids: [],
    })
  })

  // 名称必填 / 金额 > 0（任务 6.1 校验）
  it('用例2d: 名称空白与金额 ≤0 时保存禁用', async () => {
    const wrapper = await mountPage()
    wrapper.vm.openBudgetAddDialog()
    wrapper.vm.budgetForm = {
      id: null,
      month: '2026-01',
      name: '   ',
      amount: 100,
      scope_mode: 'include',
      category_ids: [1],
    }
    expect(wrapper.vm.budgetNameMissing).toBe(true)
    expect(wrapper.vm.budgetFormValid).toBe(false)

    wrapper.vm.budgetForm = { ...wrapper.vm.budgetForm, name: '日常开销', amount: 0 }
    expect(wrapper.vm.budgetAmountInvalid).toBe(true)
    expect(wrapper.vm.budgetFormValid).toBe(false)

    wrapper.vm.budgetForm = { ...wrapper.vm.budgetForm, amount: 800 }
    expect(wrapper.vm.budgetFormValid).toBe(true)
  })

  // 任务 6.3 / 7.1（审查记录⑤）：编辑链路 batch → PUT 重接
  it('用例5: 编辑复用同对话框回填全字段，保存走 updateBudget(PUT 全字段) 且载荷不含 month', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({ id: 31, name: '日常开销', amount: 800, spent: 100, category_ids: [1], category_names: ['餐饮'] }),
    ])
    const wrapper = await mountPage()

    wrapper.vm.openBudgetEditDialog(wrapper.vm.budgets[0])
    expect(wrapper.vm.showBudgetDialog).toBe(true)
    expect(wrapper.vm.budgetForm).toEqual({
      id: 31,
      month: '2026-01',
      name: '日常开销',
      amount: 800,
      scope_mode: 'include',
      category_ids: [1],
    })

    wrapper.vm.budgetForm.amount = 900
    wrapper.vm.budgetForm.category_ids = [1, 2]
    const before = reloadCount(getBudgets)
    await wrapper.vm.saveBudget()
    await flushPromises()

    expect(updateBudget).toHaveBeenCalledWith(31, {
      name: '日常开销',
      amount: 900,
      scope_mode: 'include',
      category_ids: [1, 2],
    })
    // month 不可改：不出现在 PUT 载荷里
    expect('month' in updateBudget.mock.calls[0][1]).toBe(false)
    expect(createBudget).not.toHaveBeenCalled()
    expect(reloadCount(getBudgets)).toBe(before + 1)
  })

  // 任务 5.5：删除走 ConfirmDialog，message 含预算名称
  it('用例5b: 删除走 ConfirmDialog（message 含名称），确认后 deleteBudget + 重拉', async () => {
    getBudgets.mockResolvedValue([makeBudget({ id: 41, name: '学习基金' })])
    const wrapper = await mountPage()

    const card = wrapper.findAll('.budget-card')[0]
    await card.find('.budget-delete-btn').trigger('click')
    expect(wrapper.vm.showDeleteBudgetDialog).toBe(true)

    const confirm = wrapper.findComponent(ConfirmDialog)
    expect(confirm.props('message')).toBe('确定要删除「学习基金」预算吗？')
    expect(confirm.props('title')).toBe('删除预算')

    const before = reloadCount(getBudgets)
    await wrapper.vm.handleDeleteBudget()
    await flushPromises()

    expect(deleteBudget).toHaveBeenCalledWith(41)
    expect(reloadCount(getBudgets)).toBe(before + 1)
    expect(wrapper.vm.showDeleteBudgetDialog).toBe(false)
    expect(wrapper.vm.deletingBudget).toBeNull()
  })

  // 后端拦截（40001 PARAM_ERROR）时提示后端 message 且保留对话框
  it('用例5c: PUT 被后端校验拦截时弹后端 message，不关对话框', async () => {
    getBudgets.mockResolvedValue([makeBudget({ id: 51, name: '日常开销' })])
    updateBudget.mockRejectedValueOnce(new Error('分类不存在：999'))
    const wrapper = await mountPage()

    wrapper.vm.openBudgetEditDialog(wrapper.vm.budgets[0])
    wrapper.vm.budgetForm.category_ids = [999]
    await wrapper.vm.saveBudget()
    await flushPromises()

    expect(appStoreMock.showToast).toHaveBeenCalledWith('分类不存在：999', 'error')
    expect(wrapper.vm.showBudgetDialog).toBe(true)
  })

  // 任务 5.4：展开明细（仅列计入分类）
  it('用例8: 展开明细按卡独立切换，明细行来自 details 字段', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({
        id: 61,
        details: [
          { category_id: 1, category_name: '餐饮', icon: 'mdi-food', spent: 800 },
          { category_id: 2, category_name: '出行', icon: 'mdi-bus', spent: 350 },
        ],
      }),
      makeBudget({ id: 62, name: '全支出', scope_mode: 'exclude', details: [] }),
    ])
    const wrapper = await mountPage()

    expect(wrapper.findAll('.budget-detail-row').length).toBe(0)
    const toggles = wrapper.findAll('.budget-detail-toggle')
    expect(toggles.length).toBe(1) // details 为空的卡不给展开入口
    expect(toggles[0].text()).toContain('展开明细')

    await toggles[0].trigger('click')
    expect(wrapper.vm.isBudgetExpanded(61)).toBe(true)
    const rows = wrapper.findAll('.budget-detail-row')
    expect(rows.length).toBe(2)
    expect(rows[0].text()).toContain('餐饮')
    expect(rows[0].text()).toContain('¥800.00')
    expect(rows[1].text()).toContain('¥350.00')
    expect(toggles[0].text()).toContain('收起明细')

    await toggles[0].trigger('click')
    expect(wrapper.vm.isBudgetExpanded(61)).toBe(false)
    expect(wrapper.findAll('.budget-detail-row').length).toBe(0)
  })

  // 任务 5.3：覆盖简述纯函数
  it('用例7: scopeSummary 文案口径（include 1/2/3/4 类、exclude 空/非空）', async () => {
    const wrapper = await mountPage()
    const fn = wrapper.vm.scopeSummary

    expect(fn({ scope_mode: 'include', category_ids: [1], category_names: ['餐饮'] }, CATEGORIES)).toBe('餐饮')
    expect(
      fn({ scope_mode: 'include', category_ids: [1, 2], category_names: ['餐饮', '出行'] }, CATEGORIES)
    ).toBe('餐饮、出行')
    expect(
      fn(
        { scope_mode: 'include', category_ids: [1, 2, 3], category_names: ['餐饮', '出行', '购物'] },
        CATEGORIES
      )
    ).toBe('餐饮、出行等 3 类')
    expect(
      fn(
        {
          scope_mode: 'include',
          category_ids: [1, 2, 3, 9],
          category_names: ['餐饮', '出行', '购物', '工资'],
        },
        CATEGORIES
      )
    ).toBe('餐饮、出行等 4 类')
    expect(fn({ scope_mode: 'exclude', category_ids: [], category_names: [] }, CATEGORIES)).toBe('全部分类')
    expect(fn({ scope_mode: 'exclude', category_ids: [9], category_names: ['工资'] }, CATEGORIES)).toBe(
      '除 工资 外全部支出'
    )
    expect(
      fn({ scope_mode: 'exclude', category_ids: [9, 3], category_names: ['工资', '购物'] }, CATEGORIES)
    ).toBe('除 工资、购物 外全部支出')
    // category_names 缺失时按 id 从分类列表兜底解析
    expect(fn({ scope_mode: 'include', category_ids: [2, 3] }, CATEGORIES)).toBe('出行、购物')
    // 迁移产出的「未知分类」只读态（include 空集）
    expect(fn({ scope_mode: 'include', category_ids: [], category_names: [] }, CATEGORIES)).toBe('未知分类')

    // 语义提示（任务 5.3）
    expect(wrapper.vm.scopeHint({ scope_mode: 'include' })).toBe('仅计入所选分类')
    expect(wrapper.vm.scopeHint({ scope_mode: 'exclude' })).toBe('选中分类不计入本预算')
  })

  // 任务 5.1/5.3：排除模式卡片形态
  it('用例9: 排除模式卡显示「排除」标签与不计入语义提示，空排除集简述为全部分类', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({
        id: 71,
        name: '除工资外全支出',
        amount: 4000,
        spent: 1200,
        scope_mode: 'exclude',
        category_ids: [],
        category_names: [],
        details: [{ category_id: 1, category_name: '餐饮', icon: 'mdi-food', spent: 1200 }],
      }),
      makeBudget({
        id: 72,
        name: '除工资理财外',
        amount: 2000,
        spent: 100,
        scope_mode: 'exclude',
        category_ids: [9],
        category_names: ['工资'],
        details: [],
      }),
    ])
    const wrapper = await mountPage()
    const cards = wrapper.findAll('.budget-card')
    expect(cards.length).toBe(2)

    expect(cards[0].find('.budget-scope-chip').text()).toBe('排除')
    expect(cards[0].find('.budget-scope').text()).toContain('覆盖：全部分类')
    expect(cards[0].find('.budget-scope-hint').text()).toBe('选中分类不计入本预算')
    expect(cards[1].find('.budget-scope').text()).toContain('除 工资 外全部支出')
  })

  // 任务 10.3：同月同名两条预算各自成卡（key=id，不合并）
  it('用例10: 同月同名两条预算各自成卡，进度互不影响', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({ id: 81, name: '日常开销', amount: 1000, spent: 100 }),
      makeBudget({ id: 82, name: '日常开销', amount: 2000, spent: 900 }),
    ])
    const wrapper = await mountPage()
    const cards = wrapper.findAll('.budget-card')
    expect(cards.length).toBe(2)
    expect(cards[0].find('.budget-name').text()).toBe('日常开销')
    expect(cards[1].find('.budget-name').text()).toBe('日常开销')
    // 总览 1000/3000=33% success、卡1 10% primary、卡2 45% primary
    expect(barColors(wrapper)).toEqual(['success', 'primary', 'primary'])
  })

  // 任务 9.3（迁移产出只读态）：展示正常、可删、编辑须补选分类
  it('用例11: 「未知分类」只读预算正常展示可删，编辑须补选分类才能保存', async () => {
    getBudgets.mockResolvedValue([
      makeBudget({
        id: 91,
        name: '未知分类',
        amount: 600,
        spent: 0,
        percentage: 0,
        category_ids: [],
        category_names: [],
        details: [],
      }),
    ])
    const wrapper = await mountPage()
    const card = wrapper.findAll('.budget-card')[0]
    expect(card.find('.budget-name').text()).toBe('未知分类')
    expect(card.find('.budget-scope').text()).toContain('覆盖：未知分类')
    expect(card.find('.budget-delete-btn').exists()).toBe(true)
    expect(wrapper.findAll('.budget-detail-toggle').length).toBe(0)

    wrapper.vm.openBudgetEditDialog(wrapper.vm.budgets[0])
    expect(wrapper.vm.budgetForm.category_ids).toEqual([])
    expect(wrapper.vm.budgetFormValid).toBe(false)
    expect(wrapper.find('.budget-dialog-error').text()).toContain('包含模式至少需要选择 1 个分类')

    await wrapper.vm.saveBudget()
    await flushPromises()
    expect(updateBudget).not.toHaveBeenCalled()

    // 补选分类后即可保存（后端 include ≥1 校验维持，不在此处绕过）
    wrapper.vm.budgetForm.category_ids = [1]
    await wrapper.vm.saveBudget()
    await flushPromises()
    expect(updateBudget).toHaveBeenCalledWith(91, {
      name: '未知分类',
      amount: 600,
      scope_mode: 'include',
      category_ids: [1],
    })
  })

  // 任务 6.1（M8 单套分类）：候选为全量列表，无 type 过滤、不排除已设预算的分类
  it('用例12: 对话框分类候选为单套全量分类（无 type 过滤 / 已设预算分类仍可再选）', async () => {
    getBudgets.mockResolvedValue([makeBudget({ category_ids: [1], category_names: ['餐饮'] })])
    const wrapper = await mountPage()
    wrapper.vm.openBudgetAddDialog()
    expect(wrapper.vm.budgetCategoryOptions).toEqual([
      { id: 1, name: '餐饮' },
      { id: 2, name: '出行' },
      { id: 3, name: '购物' },
      { id: 9, name: '工资' },
    ])
  })

  // 任务 3.4 / §8.8：色档沿用三处同型，无 100% 独立档
  it('用例4: 进度阈值配色 >80% error / >50% warning / 其余 primary（超支亦为 error）', async () => {
    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 90 })])
    let wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['error', 'error'])

    // >100% 超支：仍走 error 档，不新增 100% 独立档
    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 130 })])
    wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['error', 'error'])

    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 60 })])
    wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['warning', 'warning'])

    // 其余：概览 success、卡片 primary
    getBudgets.mockResolvedValue([makeBudget({ amount: 100, spent: 10 })])
    wrapper = await mountPage()
    expect(barColors(wrapper)).toEqual(['success', 'primary'])

    await nextTick()
  })

  // 任务 8.1：年视图行数字 = 后端 Σ 口径透传 + 下钻
  it('用例3: 年视图透传 total_amount/total_spent，点击月份行下钻回该月预算卡列表', async () => {
    const months = Array.from({ length: 12 }, (_, i) => {
      const month = `2026-${String(i + 1).padStart(2, '0')}`
      const has = i === 2
      return {
        month,
        total_amount: has ? 1700 : 0,
        total_spent: has ? 1500 : 0,
        budgets: has
          ? [
              makeBudget({ id: 21, name: '日常开销', month, amount: 1200, spent: 1000 }),
              makeBudget({ id: 22, name: '学习', month, amount: 500, spent: 500 }),
            ]
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
    expect(wrapper.vm.yearTotalBudget).toBe(1700)
    expect(wrapper.vm.yearTotalSpent).toBe(1500)

    // 行数字 = 后端字段原样（D4：两条预算 Σ 直加）
    const rows = wrapper.findAll('.budget-month-row')
    expect(rows.length).toBe(12)
    expect(rows[2].text()).toContain('1,500.00')
    expect(rows[2].text()).toContain('1,700.00')

    // 下钻：切回月视图并渲染该月预算卡列表
    getBudgets.mockResolvedValue([makeBudget({ id: 21, name: '日常开销', month: '2026-03' })])
    await rows[2].trigger('click')
    await flushPromises()

    expect(wrapper.vm.periodType).toBe('monthly')
    expect(wrapper.vm.periodOffset).toBe(2)
    expect(wrapper.vm.budgetMonth).toBe('2026-03')
    expect(getBudgets).toHaveBeenLastCalledWith({ month: '2026-03' })
    expect(wrapper.findAll('.budget-card').length).toBe(1)
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

  // 迁移等价：预算区不残留行内编辑态与批量端点封装（jsdom 布局不可测 → ?raw 源码断言）
  it('用例6: 源码结构锁——卡片列表 key=id、无行内编辑态与批量封装、展开动画口径上收全局（M14）', () => {
    expect(statisticsPageSource).not.toMatch(/editingBudget|editBudgetAmount|enrichedBudgets|availableBudgetCategories/)
    expect(statisticsPageSource).not.toContain('batchSetBudgets')
    expect(statisticsPageSource).toMatch(/<v-card\s+v-for="budget in budgets"[\s\S]{0,60}:key="budget\.id"/)
    expect(statisticsPageSource).toMatch(/v-for="row in budget\.details"/)
    expect(statisticsPageSource).toMatch(/<v-slide-y-transition>/)
    // M14（任务 7.3）：slide-y 时长/缓动覆写上收 global.scss 一处（重复类名提级 + !important），
    // 本页不再留 220ms 字面量与页内覆写；变量单点定义在 :root，本页只消费——意图不放宽。
    expect(statisticsPageSource).not.toMatch(/transition-duration:\s*220ms/)
    expect(statisticsPageSource).not.toMatch(/slide-y-transition-(enter|leave)-active/)
    expect(statisticsPageSource).not.toMatch(/--expand-(duration|easing)\s*:/)
    // 全局单点定义与消费侧一致（D10 量化口径）
    expect(globalStyleSource).toMatch(/--expand-duration:\s*220ms/)
    expect(globalStyleSource).toMatch(/--expand-easing:\s*cubic-bezier\(0\.25,\s*0\.8,\s*0\.5,\s*1\)/)
    expect(globalStyleSource).toMatch(
      /\.slide-y-transition-enter-active\.slide-y-transition-enter-active[\s\S]{0,600}transition-duration:\s*var\(--expand-duration\)/,
    )
    // 统计页预算入口图标不动（M10 域，本模块不改样式）
    expect(statisticsPageSource).toContain('mdi-piggy-bank-outline')
    expect(statisticsPageSource).toContain('entry-avatar')

    // api/budgets.js：批量封装随端点下线，新增单条创建、PUT 载荷全字段
    expect(budgetsApiSource).toMatch(/export function createBudget\(data\)[\s\S]*request\.post\('\/budgets'/)
    expect(budgetsApiSource).toMatch(/export function updateBudget\(id, data\)[\s\S]*request\.put\(`\/budgets\/\$\{id\}`/)
    expect(budgetsApiSource).not.toMatch(/export function batch|\/budgets\/batch/)
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

// ── v1.4.3 M14 全站展开画面统一「从触发点展开」：本页预算对话框收编（任务 6.6）──────
describe('v1.4.3 M14 预算新增/编辑对话框收编 AppDialog', () => {
  it('用例M14-统1: 页内零 <v-dialog、零底部上浮过渡字面量，预算对话框外壳为 AppDialog', () => {
    expect((statisticsPageSource.match(/<v-dialog/g) || [])).toHaveLength(0)
    expect(statisticsPageSource).not.toMatch(/dialog-bottom-transition/)
    expect((statisticsPageSource.match(/<AppDialog\b/g) || [])).toHaveLength(1)
    expect(statisticsPageSource).toMatch(/<AppDialog v-model="showBudgetDialog" max-width="480">/)
    expect(statisticsPageSource).toMatch(/import AppDialog from '@\/components\/common\/AppDialog\.vue'/)
    // M12 功能面零改动：对话框字段与保存链路原样（只换外壳组件）
    expect(statisticsPageSource).toMatch(/v-model="budgetForm\.name"/)
    expect(statisticsPageSource).toMatch(/@click="saveBudget"/)
  })

  it('用例M14-统2: 打开预算对话框 → 由 AppDialog 承载并应用原点展开内联样式', async () => {
    const rectSpy = vi
      .spyOn(window.HTMLElement.prototype, 'getBoundingClientRect')
      .mockImplementation(() => ({ left: 100, top: 50, width: 250, height: 200, right: 350, bottom: 250, x: 100, y: 50, toJSON: () => ({}) }))
    const wrapper = await mountPage()
    wrapper.vm.openBudgetAddDialog()
    await nextTick()
    await nextTick()

    const shell = wrapper.findComponent(AppDialog)
    expect(shell.exists()).toBe(true)
    expect(shell.props('modelValue')).toBe(true)

    const content = wrapper.find('.app-dialog__content')
    expect(content.exists()).toBe(true)
    // 展开样式已应用（非瞬现）；无触发点时退化中心（appStore 在本案为桩，lastClickOrigin 为空）
    expect(content.element.style.transform).toBe('scale(1)')
    expect(content.element.style.transformOrigin).toBe('center center')

    wrapper.unmount()
    rectSpy.mockRestore()
  })
})
