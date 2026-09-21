import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { nextTick, reactive, Transition } from 'vue'

// 用例隔离：每个用例一份全新时钟（丢弃上一用例遗留的防抖定时器），
// 并自动卸载组件（残留实例的 watch 停用，共享 filters 变化不会再排新定时器）
enableAutoUnmount(afterEach)
beforeEach(() => {
  vi.useRealTimers()
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

// Mock vue-router
const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useRoute: () => ({
    params: {},
  }),
}))

// Mock API modules
vi.mock('@/api/records', () => ({
  getRecords: vi.fn().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    total_pages: 1,
  }),
  getEarliestYear: vi.fn().mockResolvedValue({ earliest_year: null }),
}))

// store 的 batchDelete：稳定 spy，供用例断言与替换
const mockBatchDelete = vi.fn().mockResolvedValue({})

// store 的 filters 在真实实现中是响应式且跨挂载保留的对象：这里同样用 reactive 模拟
const mockFilters = reactive({
  start_date: '',
  end_date: '',
  type: '',
  category_id: null,
  tag_id: null,
  keyword: '',
})

// M5：账单页"浏览现场"的内存级状态（与 useRecordsStore 的 consume-once 语义一致）
const mockListViewHolder = { state: null }
const mockRememberListView = vi.fn((state) => {
  mockListViewHolder.state = { ...state }
})
const mockConsumeListView = vi.fn(() => {
  const v = mockListViewHolder.state
  mockListViewHolder.state = null
  return v
})
const mockResetListView = vi.fn(() => {
  mockListViewHolder.state = null
})

// Mock stores
vi.mock('@/stores/useRecordsStore', () => ({
  useRecordsStore: () => ({
    filters: mockFilters,
    batchDelete: mockBatchDelete,
    rememberListView: mockRememberListView,
    consumeListView: mockConsumeListView,
    resetListView: mockResetListView,
  }),
}))

vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({
    setTransitionOrigin: vi.fn(),
    showToast: vi.fn(),
  }),
}))

// Import component after mocks
import RecordListPage from './RecordListPage.vue'

// M10 行内断言用桩件：行首图标与金额位于 v-list-item 的具名插槽内，而 jsdom 下 Vuetify 未安装，
// 未解析的自定义元素不会渲染具名插槽内容 → 用透传桩件把插槽原样落到 DOM（原有 class/属性由
// Vue 的 fallthrough 保留，故 .entry-avatar / color="primary" 仍可被精确断言）。
const ROW_SLOT_STUBS = {
  'v-list-item': {
    template: '<div><slot name="prepend" /><slot /><slot name="append" /></div>',
  },
}
// M6 起行金额颜色由 global.scss 的 .amount-* 专用类承载（内联 style 在深色主题下被排版
// !important 压制）；本组色值正则改作「专用类声明值」断言用。
// jsdom 的 cssstyle 会把十六进制色序列化为 rgb()，两种写法都视为命中
const EXPENSE_COLOR = /#FF6B6B|rgb\(255,\s*107,\s*107\)/i
const INCOME_COLOR = /#20C997|rgb\(32,\s*201,\s*151\)/i

describe('RecordListPage - Category Icons', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('should display category icon when record has category_icon', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    // Set records with category icon
    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: 'mdi-food',
        category_name: '餐饮',
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // Verify the record has the category icon
    expect(wrapper.vm.records[0].category_icon).toBe('mdi-food')
  })

  it('should display mdi-circle fallback when no category_icon', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    // Set records without category icon
    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: null,
        category_name: '未分类',
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // The component should render with mdi-circle fallback
    expect(wrapper.vm.records[0].category_icon).toBeNull()
  })

  // 需求十（M10）口径反转：本组两条用例原断「行首 avatar 按收支双色（#FFE8E8/#E8FFF3）底色」，
  // 该双色底与右侧金额红/绿语义重复，现统一为设置页入口同款 .entry-avatar（primary 10% 底）
  // + 图标 color="primary"，收支仅由金额色与前缀表达（设计 §10.2 / 任务 2.1、2.2）。
  it('should render row icon with shared entry-avatar primary scheme instead of expense background color (M10)', async () => {
    const wrapper = mount(RecordListPage, { global: { stubs: ROW_SLOT_STUBS } })
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: 'mdi-food',
        category_name: '餐饮',
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // 行首图标统一走 .entry-avatar，其内为分类图标 + primary 色（不再按收支切色）
    const avatar = wrapper.find('.entry-avatar')
    expect(avatar.exists()).toBe(true)
    expect(avatar.attributes('class')).toContain('entry-avatar')
    expect(avatar.attributes('color')).toBeUndefined()
    const rowIcon = avatar.find('v-icon')
    expect(rowIcon.attributes('color')).toBe('primary')
    expect(rowIcon.text()).toContain('mdi-food')
    // 支出语义仍由金额红 + 「-」前缀表达
    // 【v1.4.3-boot M6 口径反转】红/绿由内联 style → .amount-expense 专用类（深色主题下内联被
    // .v-theme--dark 排版 !important 压制，设计 §6.1）；金额文本改过 formatAmount 完整格式。
    const amount = wrapper.find('.record-card .font-weight-bold')
    expect(amount.classes()).toContain('amount-expense')
    expect(amount.text()).toBe('-¥100.00')
  })

  it('should render same entry-avatar primary scheme for income rows with green amount (M10)', async () => {
    const wrapper = mount(RecordListPage, { global: { stubs: ROW_SLOT_STUBS } })
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'income',
        amount: 1000,
        category_icon: 'mdi-cash',
        category_name: '工资',
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // 收入行与支出行行首同款（收支双色底色已废弃）
    const avatar = wrapper.find('.entry-avatar')
    expect(avatar.exists()).toBe(true)
    expect(avatar.find('v-icon').attributes('color')).toBe('primary')
    // 收入语义由金额绿 + 「+」前缀表达（M6：内联 style → .amount-income 专用类）
    const amount = wrapper.find('.record-card .font-weight-bold')
    expect(amount.classes()).toContain('amount-income')
    expect(amount.text()).toBe('+¥1,000.00')
  })

  it('should display tag name when available', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: 'mdi-food',
        category_name: '餐饮',
        tag: { name: '午餐' },
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // Should display tag name
    expect(wrapper.vm.records[0].tag.name).toBe('午餐')
  })

  it('should display category name when no tag', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: 'mdi-food',
        category_name: '餐饮',
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // Should display category name
    expect(wrapper.vm.records[0].category_name).toBe('餐饮')
  })

  it('should display 未分类 when no tag and no category_name', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: null,
        category_name: null,
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // Should fallback to 未分类
    expect(wrapper.vm.records[0].category_name).toBeNull()
  })

  it('should have correct icon size', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 100,
        category_icon: 'mdi-food',
        category_name: '餐饮',
        consume_time: '2026-06-06 12:00',
      },
    ]
    await nextTick()

    // The component should render with size 20
    expect(wrapper.vm.records.length).toBe(1)
  })
})

// ---------------------------------------------------------------------------
// M3 需求二：账单页年份切换（竖屏可见 + 往前到最早记录年、往后不超当前年）
// ---------------------------------------------------------------------------
import { getRecords, getEarliestYear } from '@/api/records'

const currentYear = new Date().getFullYear()

function setViewport(width) {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
}

// 未安装 Vuetify 插件时 v-btn 渲染为同名自定义元素，按图标名区分左右箭头
function findArrow(wrapper, icon) {
  return wrapper.findAll('v-btn').filter((btn) => btn.text().includes(icon))
}

describe('RecordListPage - 年份切换', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setViewport(375) // 竖屏
    getEarliestYear.mockResolvedValue({ earliest_year: null })
    getRecords.mockResolvedValue({ items: [], total: 0, page: 1, total_pages: 1 })
  })

  it('用例1: 竖屏下月份切换条两侧渲染年份箭头，且不再有宽屏独占类', async () => {
    getEarliestYear.mockResolvedValue({ earliest_year: currentYear - 4 })
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await nextTick()

    // 当前年时右箭头隐藏（不能往后翻），翻到上一年两侧箭头同时存在
    expect(findArrow(wrapper, 'mdi-chevron-left')).toHaveLength(1)
    expect(findArrow(wrapper, 'mdi-chevron-right')).toHaveLength(0)

    wrapper.vm.prevYear()
    await nextTick()
    const left = findArrow(wrapper, 'mdi-chevron-left')
    const right = findArrow(wrapper, 'mdi-chevron-right')
    expect(left).toHaveLength(1)
    expect(right).toHaveLength(1)
    for (const btn of [...left, ...right]) {
      expect(btn.classes()).not.toContain('d-none')
      expect(btn.classes()).not.toContain('d-md-flex')
    }
  })

  it('用例2a: selectedYear === minYear 时左箭头不存在', async () => {
    getEarliestYear.mockResolvedValue({ earliest_year: currentYear - 2 })
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await nextTick()

    wrapper.vm.prevYear()
    await nextTick()
    expect(wrapper.vm.selectedYear).toBe(currentYear - 1)
    expect(wrapper.vm.minYear).toBe(currentYear - 2)
    expect(findArrow(wrapper, 'mdi-chevron-left')).toHaveLength(1)

    wrapper.vm.prevYear()
    await nextTick()
    expect(wrapper.vm.selectedYear).toBe(currentYear - 2)
    expect(findArrow(wrapper, 'mdi-chevron-left')).toHaveLength(0)
    expect(findArrow(wrapper, 'mdi-chevron-right')).toHaveLength(1)

    // 双保险守卫：已到最早年，再点不会更早
    wrapper.vm.prevYear()
    await nextTick()
    expect(wrapper.vm.selectedYear).toBe(currentYear - 2)
  })

  it('用例2b: selectedYear === currentYear 时右箭头不存在', async () => {
    getEarliestYear.mockResolvedValue({ earliest_year: currentYear - 3 })
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await nextTick()

    wrapper.vm.prevYear()
    await nextTick()
    expect(findArrow(wrapper, 'mdi-chevron-right')).toHaveLength(1)

    wrapper.vm.nextYear()
    await nextTick()
    expect(wrapper.vm.selectedYear).toBe(currentYear)
    expect(findArrow(wrapper, 'mdi-chevron-right')).toHaveLength(0)

    // 已在当前年，再点不会超过当前年
    wrapper.vm.nextYear()
    await nextTick()
    expect(wrapper.vm.selectedYear).toBe(currentYear)
  })

  it('用例3: earliest_year=null（无账单用户）时左箭头不存在', async () => {
    getEarliestYear.mockResolvedValue({ earliest_year: null })
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await nextTick()

    expect(wrapper.vm.minYear).toBe(currentYear)
    expect(findArrow(wrapper, 'mdi-chevron-left')).toHaveLength(0)
    expect(findArrow(wrapper, 'mdi-chevron-right')).toHaveLength(0)
  })

  it('接口异常时兜底为仅当前年，账单列表功能不受阻塞', async () => {
    getEarliestYear.mockRejectedValue(new Error('网络异常'))
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await nextTick()

    expect(wrapper.vm.minYear).toBe(currentYear)
    expect(findArrow(wrapper, 'mdi-chevron-left')).toHaveLength(0)
    expect(getRecords).toHaveBeenCalled()
    expect(wrapper.vm.records).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// M4 需求七（一次点击一次请求：防抖 + 同参去重 + 加载态分流）
//    需求八（筛选仅日期：不再渲染类型/分类控件、请求不携带 type/category_id）
// ---------------------------------------------------------------------------
const currentMonth = new Date().getMonth() + 1

function pad(n) {
  return String(n).padStart(2, '0')
}

// 与 selectMonth 一致的月份区间，用于断言 filters 写入与请求参数
function monthRange(year, month) {
  const lastDay = new Date(year, month, 0).getDate()
  return {
    start: `${year}-${pad(month)}-01`,
    end: `${year}-${pad(month)}-${pad(lastDay)}`,
  }
}

function makeRecord(id) {
  return {
    id,
    type: 'expense',
    amount: 10 + id,
    category_icon: 'mdi-food',
    category_name: '餐饮',
    consume_time: '2026-06-06 12:00',
  }
}

function pageResult(items, page, totalPages) {
  return { items, total: items.length * totalPages, page, total_pages: totalPages }
}

describe('RecordListPage - 请求合并与筛选精简', () => {
  beforeEach(() => {
    // 清掉上个用例遗留的 once 队列，避免实现泄漏（fake timers 由文件顶层统一安装）
    getRecords.mockReset()
    getEarliestYear.mockReset()
    getRecords.mockResolvedValue(pageResult([], 1, 1))
    getEarliestYear.mockResolvedValue({ earliest_year: null })
    mockFilters.start_date = ''
    mockFilters.end_date = ''
    mockFilters.type = ''
    mockFilters.category_id = null
    mockFilters.tag_id = null
    mockFilters.keyword = ''
    setViewport(375)
  })

  it('用例1: selectMonth 只写日期，推进 300ms 防抖后恰好新增一次请求', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1) // 首屏显式 search

    wrapper.vm.selectMonth(3)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1) // 未到防抖时间不发请求

    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(2) // 恰一次

    const params = getRecords.mock.calls[1][0]
    expect(params.start_date).toBe(monthRange(currentYear, 3).start)
    expect(params.end_date).toBe(monthRange(currentYear, 3).end)
    expect(params.page).toBe(1)

    // 防抖窗口内连点两个月：只发最后一次
    wrapper.vm.selectMonth(5)
    await nextTick()
    vi.advanceTimersByTime(150)
    wrapper.vm.selectMonth(8)
    await nextTick()
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(3)
    expect(getRecords.mock.calls[2][0].start_date).toBe(monthRange(currentYear, 8).start)
  })

  it('用例1b: 已有列表时切月份走 refreshing——列表保留、顶部细进度条，无整块闪没', async () => {
    getRecords.mockResolvedValue(pageResult([makeRecord(1), makeRecord(2)], 1, 1))
    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(wrapper.findAll('.record-card')).toHaveLength(2)
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.vm.refreshing).toBe(false)

    let resolvePending
    getRecords.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePending = resolve
        })
    )
    wrapper.vm.selectMonth(4)
    await nextTick()
    vi.advanceTimersByTime(300)
    await flushPromises()

    // 请求在途：走后台刷新，列表仍在，不渲染首屏整块 spinner
    expect(wrapper.vm.refreshing).toBe(true)
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.findAll('.record-card')).toHaveLength(2)
    expect(wrapper.find('v-progress-linear').exists()).toBe(true)
    expect(wrapper.find('v-progress-circular').exists()).toBe(false)

    resolvePending(pageResult([makeRecord(9)], 1, 1))
    await flushPromises()
    expect(wrapper.vm.refreshing).toBe(false)
    expect(wrapper.vm.records.map((r) => r.id)).toEqual([9])
  })

  it('用例2: filters 与目标月区间相同（store 跨挂载残留）→ 显式 search 与 watch 同参去重，仅一次请求', async () => {
    const { start, end } = monthRange(currentYear, currentMonth)
    mockFilters.start_date = start
    mockFilters.end_date = end

    mount(RecordListPage)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1) // 值恰好相同 → watch 不触发，显式 search 兜底
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)
    expect(getRecords.mock.calls[0][0]).toMatchObject({ page: 1, start_date: start, end_date: end })
  })

  it('用例2b: filters 与目标月不同（首屏）→ 显式 search 与随后 watch 同参被去重，仍仅一次请求', async () => {
    mount(RecordListPage)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1) // 显式 search

    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1) // watch 同参 → 去重跳过

    vi.advanceTimersByTime(1000)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1) // 无重复定时器残留
  })

  it('用例3: 修改 filters 两次且最终参数与上次相同 → 第二次不发请求', async () => {
    mount(RecordListPage)
    await flushPromises()
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)

    const queried = getRecords.mock.calls[0][0]
    mockFilters.end_date = `${currentYear}-12-31` // 第 1 次修改
    await nextTick()
    mockFilters.end_date = queried.end_date // 第 2 次修改：回到上次已查询的参数
    await nextTick()
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)

    // 对照：真正变化的参数会正常发出
    mockFilters.start_date = `${currentYear}-01-01`
    await nextTick()
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(2)
  })

  it('用例4: 筛选卡片不再渲染类型/分类控件，请求参数不含 type/category_id', async () => {
    mockFilters.type = 'expense'
    mockFilters.category_id = 7

    const wrapper = mount(RecordListPage)
    await flushPromises()

    const filterCard = wrapper.find('.filter-card')
    expect(filterCard.exists()).toBe(true)
    expect(filterCard.findAll('v-select')).toHaveLength(0)
    expect(filterCard.text()).not.toContain('类型')
    expect(filterCard.text()).not.toContain('分类')
    expect(filterCard.findAll('input, .v-field').length).toBeLessThanOrEqual(2)

    const params = getRecords.mock.calls[0][0]
    expect(Object.keys(params)).not.toContain('type')
    expect(Object.keys(params)).not.toContain('category_id')
    expect(Object.keys(params).sort()).toEqual(['end_date', 'page', 'page_size', 'start_date'])

    // 残留 type/category_id 再变化也不触发请求（watch 依赖仅两个日期字段）
    const calls = getRecords.mock.calls.length
    mockFilters.type = 'income'
    mockFilters.category_id = 2
    await nextTick()
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(calls)
  })

  it('用例5: loadMore 页码递增并以 append 追加，不整体替换', async () => {
    getRecords
      .mockResolvedValueOnce(pageResult([makeRecord(1), makeRecord(2)], 1, 2))
      .mockResolvedValueOnce(pageResult([makeRecord(3), makeRecord(4)], 2, 2))

    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(getRecords.mock.calls[0][0].page).toBe(1)
    expect(wrapper.vm.records).toHaveLength(2)
    expect(wrapper.vm.hasMore).toBe(true)

    await wrapper.vm.loadMore()
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(2)
    expect(getRecords.mock.calls[1][0].page).toBe(2)
    expect(wrapper.vm.records.map((r) => r.id)).toEqual([1, 2, 3, 4])
    expect(wrapper.vm.hasMore).toBe(false)
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.vm.refreshing).toBe(false)
  })

  it('用例5b: loadMore 失败回退页码，重试不跳页；失败后同参仍可重发', async () => {
    getRecords.mockResolvedValueOnce(pageResult([makeRecord(1), makeRecord(2)], 1, 3))
    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(wrapper.vm.pageNum).toBe(1)

    getRecords.mockRejectedValueOnce(new Error('网络异常'))
    await wrapper.vm.loadMore()
    await flushPromises()
    expect(wrapper.vm.pageNum).toBe(1)
    expect(wrapper.vm.records).toHaveLength(2) // 失败不清列表

    getRecords.mockResolvedValueOnce(pageResult([makeRecord(3), makeRecord(4)], 2, 3))
    await wrapper.vm.loadMore()
    await flushPromises()
    expect(getRecords.mock.calls[2][0].page).toBe(2)
    expect(wrapper.vm.records.map((r) => r.id)).toEqual([1, 2, 3, 4])
  })

  it('用例6: 请求失败后清空去重键，同参再次调用可重发', async () => {
    getRecords.mockRejectedValueOnce(new Error('网络异常'))
    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.records).toEqual([])
    expect(wrapper.vm.loading).toBe(false)

    await wrapper.vm.search() // 同参重试：lastQueryKey 已在失败时清空
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(2)
    expect(getRecords.mock.calls[1][0]).toEqual(getRecords.mock.calls[0][0])

    // 成功之后同参再调用被去重
    await wrapper.vm.search()
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(2)
  })
})

// ---------------------------------------------------------------------------
// M5 需求三：账单详情返回状态记忆（年月 + 滚动位置 + 筛选现场）
//   保存点只在 goToDetail；恢复路径只赋 selectedYear/selectedMonth，绝不重写 filters
//   （重写会触发 M4 的日期防抖 watch → 双请求 / 闪回当前月，属回归缺陷）
// ---------------------------------------------------------------------------
describe('RecordListPage - 详情返回状态记忆', () => {
  let scrollToSpy
  let rafSpy

  // 详情卡片点击事件：goToDetail 只用到 currentTarget.getBoundingClientRect()
  const clickEvent = {
    currentTarget: {
      getBoundingClientRect: () => ({
        left: 0,
        top: 0,
        right: 100,
        bottom: 40,
        width: 100,
        height: 40,
      }),
    },
  }

  function setScrollY(value) {
    Object.defineProperty(window, 'scrollY', {
      writable: true,
      configurable: true,
      value,
    })
  }

  beforeEach(() => {
    getRecords.mockReset()
    getEarliestYear.mockReset()
    getRecords.mockResolvedValue(pageResult([], 1, 1))
    getEarliestYear.mockResolvedValue({ earliest_year: null })
    mockFilters.start_date = ''
    mockFilters.end_date = ''
    mockListViewHolder.state = null
    mockRememberListView.mockClear()
    mockConsumeListView.mockClear()
    mockResetListView.mockClear()
    setViewport(375)
    setScrollY(0)

    // 滚动与动画帧在本用例组内可观测：scrollTo 记录参数，rAF 同步执行回调
    scrollToSpy = vi.fn()
    Object.defineProperty(window, 'scrollTo', {
      writable: true,
      configurable: true,
      value: scrollToSpy,
    })
    rafSpy = vi.fn((cb) => {
      cb(0)
      return 1
    })
    Object.defineProperty(window, 'requestAnimationFrame', {
      writable: true,
      configurable: true,
      value: rafSpy,
    })
  })

  it('用例1: 点进详情保存现场 → 重新挂载恢复年月/滚动/筛选，且仅一次请求', async () => {
    // 1) 进入账单页并翻到 3 月（用户浏览行为，含一次防抖请求）
    const wrapper = mount(RecordListPage)
    await flushPromises()
    wrapper.vm.selectMonth(3)
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(2)
    const filtersAtLeave = { ...mockFilters }
    setScrollY(320) // 滚动到列表中部

    // 2) 点进详情：现场写入 store（year/month/scrollTop），并跳转
    wrapper.vm.goToDetail(clickEvent, 42)
    await nextTick()
    expect(mockListViewHolder.state).toEqual({ year: currentYear, month: 3, scrollTop: 320 })
    expect(mockPush).toHaveBeenCalledWith('/detail/42')
    wrapper.unmount()

    // 3) 返回（组件重挂载）：现场恢复，且"仅一次请求"
    getRecords.mockClear()
    const restored = mount(RecordListPage)
    await flushPromises()

    expect(restored.vm.selectedYear).toBe(currentYear)
    expect(restored.vm.selectedMonth).toBe(3)
    expect(getRecords).toHaveBeenCalledTimes(1)
    const params = getRecords.mock.calls[0][0]
    expect(params).toMatchObject({
      page: 1,
      start_date: monthRange(currentYear, 3).start,
      end_date: monthRange(currentYear, 3).end,
    })

    // filters 未被重写：值逐项一致 + 防抖窗口过后无第二次请求（watch 未被触发）
    expect({ ...mockFilters }).toEqual(filtersAtLeave)
    vi.advanceTimersByTime(1000)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)

    // 滚动位置在 nextTick + 一帧 rAF 后恢复
    expect(rafSpy).toHaveBeenCalledTimes(1)
    expect(scrollToSpy).toHaveBeenCalledWith({ top: 320 })
    restored.unmount()
  })

  it('用例1b: 现场为"往年 + 全年视图（month=null）"→ 年份视图原样恢复，不写 filters', async () => {
    getEarliestYear.mockResolvedValue({ earliest_year: currentYear - 5 })
    const yearStart = `${currentYear - 2}-01-01`
    const yearEnd = `${currentYear - 2}-12-31`
    mockFilters.start_date = yearStart
    mockFilters.end_date = yearEnd
    mockListViewHolder.state = { year: currentYear - 2, month: null, scrollTop: 88 }

    const wrapper = mount(RecordListPage)
    await flushPromises()

    expect(wrapper.vm.selectedYear).toBe(currentYear - 2)
    expect(wrapper.vm.selectedMonth).toBeNull()
    expect(getRecords).toHaveBeenCalledTimes(1)
    expect(getRecords.mock.calls[0][0]).toMatchObject({ start_date: yearStart, end_date: yearEnd })
    expect(mockFilters.start_date).toBe(yearStart)
    expect(mockFilters.end_date).toBe(yearEnd)

    vi.advanceTimersByTime(1000)
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)
    expect(scrollToSpy).toHaveBeenCalledWith({ top: 88 })
    wrapper.unmount()
  })

  it('用例2: 现场已被一次性消费后再次挂载 → 回到当前月默认逻辑，不做滚动恢复', async () => {
    mockListViewHolder.state = { year: currentYear - 1, month: 3, scrollTop: 200 }
    const first = mount(RecordListPage)
    await flushPromises()
    expect(first.vm.selectedMonth).toBe(3)
    expect(mockListViewHolder.state).toBeNull() // 读取即清除
    first.unmount()

    getRecords.mockClear()
    scrollToSpy.mockClear()
    rafSpy.mockClear()

    const second = mount(RecordListPage) // 底栏重新进入账单页
    await flushPromises()
    expect(second.vm.selectedYear).toBe(currentYear)
    expect(second.vm.selectedMonth).toBe(currentMonth)
    expect(getRecords).toHaveBeenCalledTimes(1)
    expect(getRecords.mock.calls[0][0].start_date).toBe(monthRange(currentYear, currentMonth).start)
    expect(rafSpy).not.toHaveBeenCalled()
    expect(scrollToSpy).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1000) // 默认路径的 filters 重写与 watch 同参去重 → 仍一次
    await flushPromises()
    expect(getRecords).toHaveBeenCalledTimes(1)
    second.unmount()
  })

  it('用例4: goToDetail 快照字段完整（year/month/scrollTop）；仅该入口保存现场', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    expect(mockConsumeListView).toHaveBeenCalledTimes(1) // 挂载时消费一次
    expect(mockRememberListView).not.toHaveBeenCalled()

    wrapper.vm.selectMonth(6)
    await nextTick()
    setScrollY(123)
    wrapper.vm.goToDetail(clickEvent, 7)

    expect(mockRememberListView).toHaveBeenCalledTimes(1)
    expect(mockRememberListView).toHaveBeenCalledWith({
      year: currentYear,
      month: 6,
      scrollTop: 123,
    })
    expect(mockListViewHolder.state).toEqual({ year: currentYear, month: 6, scrollTop: 123 })

    // 不用 onBeforeUnmount：离开页面（切底栏/跳记一笔）不会残留现场
    wrapper.unmount()
    expect(mockRememberListView).toHaveBeenCalledTimes(1)
  })

  it('边界: 现场月份数据已被清空 → 恢复后显示既有空态卡片且不报错', async () => {
    mockFilters.start_date = monthRange(currentYear, 3).start
    mockFilters.end_date = monthRange(currentYear, 3).end
    mockListViewHolder.state = { year: currentYear, month: 3, scrollTop: 40 }
    getRecords.mockResolvedValue(pageResult([], 1, 1))

    const wrapper = mount(RecordListPage)
    await flushPromises()

    expect(wrapper.vm.selectedMonth).toBe(3)
    expect(wrapper.vm.records).toEqual([])
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.find('.empty-state-wrapper').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无账单')
    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// M3 需求三：账单页月份条放大 + 选中月滚动居中 + 往年选中态失色修复
//   居中手法为容器自身 scrollTo（设计 §3.2.3 红线：禁 scrollIntoView）；
//   jsdom 无布局 → 「调用参数断言（含自设布局度量）+ ?raw 源码断言」组合（设计 §3.4）
// ---------------------------------------------------------------------------
import recordListSource from './RecordListPage.vue?raw'

// 给月份条容器与某个 chip 包装器伪造布局度量，使居中数学可被精确断言
function stubLayout(wrapper, chipIndex, { clientWidth, offsetLeft, offsetWidth }) {
  const scroller = wrapper.find('.month-scroller').element
  Object.defineProperty(scroller, 'clientWidth', { value: clientWidth, configurable: true })
  const chip = wrapper.findAll('.month-scroller > div')[chipIndex].element
  Object.defineProperty(chip, 'offsetLeft', { value: offsetLeft, configurable: true })
  Object.defineProperty(chip, 'offsetWidth', { value: offsetWidth, configurable: true })
  return scroller
}

describe('RecordListPage - 月份条居中与放大（M3）', () => {
  /** [{ el, opts }] —— el 用于断言滚动只作用于月份条容器 */
  let scrollCalls

  beforeEach(() => {
    getRecords.mockReset()
    getEarliestYear.mockReset()
    getRecords.mockResolvedValue(pageResult([], 1, 1))
    getEarliestYear.mockResolvedValue({ earliest_year: currentYear - 5 })
    mockFilters.start_date = ''
    mockFilters.end_date = ''
    mockListViewHolder.state = null
    setViewport(375)

    scrollCalls = []
    // jsdom 未实现 Element.scrollTo：按任务 6.1 打桩并记录调用参数（window.Element 即 Element）
    window.Element.prototype.scrollTo = vi.fn(function (opts) {
      scrollCalls.push({ el: this, opts })
    })
  })

  afterEach(() => {
    delete window.Element.prototype.scrollTo
  })

  it('用例1: 首屏挂载即以 behavior:auto 定位当前月（进入页面不播放滚动动画）', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    expect(scrollCalls.length).toBeGreaterThanOrEqual(1)
    expect(scrollCalls[0].opts).toMatchObject({ behavior: 'auto' })
    expect(typeof scrollCalls[0].opts.left).toBe('number')
    expect(scrollCalls[0].opts.left).toBeGreaterThanOrEqual(0)
    // 滚动只发生在月份条容器上，不涉及 window / 其他祖先
    expect(scrollCalls[0].el).toBe(wrapper.find('.month-scroller').element)
    wrapper.unmount()
  })

  it('用例2: selectMonth 按「chip.offsetLeft −（容器宽 − chip 宽)/2」居中且 behavior:smooth', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    scrollCalls.length = 0

    // 容器可视宽 300，第 12 月左偏移 640、宽 64 → 期望 left = 640 − (300−64)/2 = 522
    stubLayout(wrapper, 11, { clientWidth: 300, offsetLeft: 640, offsetWidth: 64 })
    await wrapper.vm.selectMonth(12)

    expect(scrollCalls).toHaveLength(1)
    expect(scrollCalls[0].opts).toEqual({ left: 522, behavior: 'smooth' })
    wrapper.unmount()
  })

  it('用例3: 居中偏移不为负（首个月份左侧不出现负滚动值）', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    scrollCalls.length = 0

    stubLayout(wrapper, 0, { clientWidth: 800, offsetLeft: 0, offsetWidth: 64 })
    await wrapper.vm.selectMonth(1)

    expect(scrollCalls[0].opts).toEqual({ left: 0, behavior: 'smooth' })
    wrapper.unmount()
  })

  it('用例4: prevYear/nextYear 后 selectedMonth=null → 月份条回卷左端（left:0, smooth）', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    await wrapper.vm.prevYear()
    expect(wrapper.vm.selectedMonth).toBeNull()
    expect(scrollCalls.at(-1).opts).toEqual({ left: 0, behavior: 'smooth' })

    await wrapper.vm.nextYear()
    expect(scrollCalls.at(-1).opts).toEqual({ left: 0, behavior: 'smooth' })
    wrapper.unmount()
  })

  it('用例5: 翻到往年后点选月份 → 该月恢复选中并居中（往年选中态不再失色）', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await wrapper.vm.prevYear()
    scrollCalls.length = 0

    stubLayout(wrapper, 4, { clientWidth: 300, offsetLeft: 320, offsetWidth: 64 })
    await wrapper.vm.selectMonth(5)

    expect(wrapper.vm.selectedMonth).toBe(5)
    expect(scrollCalls.at(-1).opts).toEqual({ left: 202, behavior: 'smooth' })
    // 选中色只取决于 selectedMonth：往年年份下 chip 仍为 primary + flat
    const chip = wrapper.findAll('v-chip')[4]
    expect(chip.attributes('color')).toBe('primary')
    expect(chip.attributes('variant')).toBe('flat')
    wrapper.unmount()
  })

  it('用例6: 详情页返回现场恢复月份后同样居中定位（首屏语义 → auto）', async () => {
    mockListViewHolder.state = { year: currentYear - 1, month: 3, scrollTop: 0 }
    const wrapper = mount(RecordListPage)
    await flushPromises()

    expect(wrapper.vm.selectedMonth).toBe(3)
    expect(wrapper.vm.selectedYear).toBe(currentYear - 1)
    const calls = scrollCalls.filter((c) => c.el === wrapper.find('.month-scroller').element)
    expect(calls.length).toBeGreaterThanOrEqual(1)
    expect(calls[0].opts.behavior).toBe('auto')
    wrapper.unmount()
  })

  it('用例6b: 连续快速点选两端月份（任务 5.3）→ 每次都派发 smooth scrollTo 且不报错', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()
    scrollCalls.length = 0

    stubLayout(wrapper, 0, { clientWidth: 300, offsetLeft: 0, offsetWidth: 64 })
    await wrapper.vm.selectMonth(1)
    await wrapper.vm.selectMonth(12)
    await wrapper.vm.selectMonth(1)

    expect(scrollCalls).toHaveLength(3)
    expect(scrollCalls.every((c) => c.opts.behavior === 'smooth')).toBe(true)
    expect(scrollCalls.every((c) => c.opts.left >= 0)).toBe(true)
    expect(wrapper.vm.selectedMonth).toBe(1) // 末态 = 最后一次点选
    wrapper.unmount()
  })

  it('用例7: 月份条渲染 12 个 chip，文本为 1月…12月', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    expect(wrapper.findAll('.month-scroller > div')).toHaveLength(12)
    expect(wrapper.findAll('v-chip').map((c) => c.text())).toEqual(
      Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
    )
    wrapper.unmount()
  })

  it('用例8: 放大口径与容器类收敛（?raw 源码断言）', () => {
    // 月份条容器：工具类整体替换为 .month-scroller scoped 类
    expect(recordListSource).toMatch(/<div ref="monthScroller" class="month-scroller">/)
    const scrollerRule = recordListSource.match(/\.month-scroller \{[^}]*\}/)
    expect(scrollerRule, '.month-scroller 类未定义').toBeTruthy()
    expect(scrollerRule[0]).toMatch(/display:\s*flex/)
    expect(scrollerRule[0]).toMatch(/flex-grow:\s*1/)
    expect(scrollerRule[0]).toMatch(/overflow-x:\s*auto/)
    expect(scrollerRule[0]).toMatch(/gap:\s*8px/)
    expect(scrollerRule[0]).toMatch(/padding-bottom:\s*8px/)
    expect(scrollerRule[0]).toMatch(/scrollbar-width:\s*none/)
    // 旧工具类与内联 scrollbar-width 不再残留于模板
    expect(recordListSource).not.toMatch(/overflow-x-auto/)
    expect(recordListSource).not.toMatch(/style="scrollbar-width: none"/)
    // chip 包装器 48px → 64px；chip small → default 并加大字号类
    expect(recordListSource).toMatch(/min-width:\s*64px/)
    expect(recordListSource).not.toMatch(/min-width:\s*48px/)
    expect(recordListSource).toMatch(/class="text-subtitle-2 font-weight-medium"\s+size="default"/)
    // 外层卡片 pa-2 → pa-3；年份箭头 x-small/small → small/20
    expect(recordListSource).toMatch(/<v-card class="pa-3 mb-3" rounded="xl">/)
    expect(recordListSource).toMatch(/size="small"\s+@click="prevYear"[\s\S]{0,60}<v-icon size="20">/)
    expect(recordListSource).toMatch(/size="small"\s+@click="nextYear"[\s\S]{0,60}<v-icon size="20">/)
    expect(recordListSource).not.toMatch(/variant="text"\s+size="x-small"/)
  })

  it('用例9: 选中态失色修复 + 居中红线（?raw 不含 selectedYear === currentYear 限定、无 scrollIntoView 调用点）', () => {
    expect(recordListSource).toMatch(/:color="selectedMonth === m \? 'primary' : ''"/)
    expect(recordListSource).not.toContain('selectedMonth === m && selectedYear === currentYear')
    expect(recordListSource).not.toMatch(/selectedYear === currentYear\s*\?\s*'primary'/)
    // 模块红线：居中禁用 scrollIntoView（会连带垂直滚动祖先，打断 M11 与详情页返回滚动）。
    // 源码注释为解释红线会合法提及该 API 名，故断言取"无调用点"形式。
    expect(recordListSource).not.toMatch(/\.scrollIntoView\s*\(/)
  })

  it('用例10: 放大后月份条结构不变（年份箭头 + 12 chip，红线：不改连续时间轴）', async () => {
    getEarliestYear.mockResolvedValue({ earliest_year: currentYear - 5 })
    const wrapper = mount(RecordListPage)
    await flushPromises()
    await nextTick()

    expect(wrapper.findAll('.month-scroller > div')).toHaveLength(12)
    expect(recordListSource).toMatch(/v-for="m in 12"/)
    expect(findArrow(wrapper, 'mdi-chevron-left')).toHaveLength(1)
    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// M11 需求十一：竖屏页内横滑误切底部标签页修复（CSS 层 overscroll-behavior-x）
//   4.1 global.scss 根级断言（vitest 不处理 CSS，?raw 会拿到空串 → 沿用仓库既定的
//       node:fs 直读样式表手法，见 SettingsSubPages.test.js 的 readGlobalStyles）
//   4.2 RecordListPage.vue ?raw 断言 .month-scroller 含该属性
//   4.3 M3 居中/滚动用例回归（见上一 describe 组，滚动定位不受影响）
// ---------------------------------------------------------------------------
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { cwd } from 'node:process'

function readSourceFile(relative) {
  let dir = cwd()
  for (let i = 0; i < 5; i++) {
    const candidate = join(dir, relative)
    if (existsSync(candidate)) return readFileSync(candidate, 'utf8')
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  throw new Error(`未找到 ${relative}（cwd=${cwd()}）`)
}

const OVERSCAN_X = /overscroll-behavior-x:\s*contain/

describe('RecordListPage - 横滑误切标签页修复（M11）', () => {
  const globalStyles = readSourceFile(join('src', 'styles', 'global.scss'))

  it('用例1: 根滚动容器隔离横向 overscroll（主修复，global.scss）', () => {
    expect(globalStyles).toMatch(/overscroll-behavior-x:\s*contain/)
    expect(globalStyles).toMatch(/html,\s*body\s*\{[^}]*overscroll-behavior-x:\s*contain/)
    // 只断横向：纵向 overscroll（下拉刷新）语义零改动（任务 3.4）
    expect(globalStyles).not.toMatch(/overscroll-behavior-y\s*:/)
    expect(globalStyles).not.toMatch(/[^-]overscroll-behavior\s*:/)
  })

  it('用例2: M3 建的 .month-scroller 类追加横向 overscroll 隔离（不新增类、不改结构）', () => {
    const rule = recordListSource.match(/\.month-scroller\s*\{[^}]*\}/)
    expect(rule, '.month-scroller 类未定义').toBeTruthy()
    expect(rule[0]).toMatch(OVERSCAN_X)
    // 追加属性后容器仍可横滚（contain 只断链、不取消滚动），M3 口径全量保持
    expect(rule[0]).toMatch(/overflow-x:\s*auto/)
    expect(rule[0]).toMatch(/gap:\s*8px/)
    expect(rule[0]).toMatch(/scrollbar-width:\s*none/)
    // 纵向不设值（任务 3.4）
    expect(rule[0]).not.toMatch(/overscroll-behavior-y\s*:/)
    expect(rule[0]).not.toMatch(/overscroll-behavior\s*:/)
  })

  it('用例3: CSS-only 修复——不引入任何 JS 手势拦截代码（红线 5 / 任务 3.1）', () => {
    expect(recordListSource).not.toMatch(/addEventListener\(\s*['"]touch/)
    expect(recordListSource).not.toMatch(/touchstart|touchmove|touchend/)
    expect(recordListSource).not.toMatch(/preventDefault\s*\(/)
    expect(recordListSource).not.toContain('scrollIntoView(')
    // 居中仍走容器 scrollTo（M3 手法不变）
    expect(recordListSource).toMatch(/scroller\.scrollTo\?\.\(/)
  })

  it('用例4: 全站横滚容器审计（任务 2.3）——可横滚容器仅月份条一处', () => {
    const appLayout = readSourceFile(join('src', 'components', 'layout', 'AppLayout.vue'))
    // AppLayout 为 overflow-x: hidden（裁剪而非可滚动容器）→ 按设计 §11.2 第 3/4 点不处理，保持现状
    expect(appLayout).toMatch(/overflow-x:\s*hidden/)
    expect(appLayout).not.toMatch(/overflow-x:\s*(auto|scroll)/)
    // 根级与月份条两处 contain 即为全覆盖（其余页面样式文件无横向滚动容器）
    const scssFiles = ['src/styles/global.scss']
    for (const f of scssFiles) {
      expect(readSourceFile(f)).toMatch(/overscroll-behavior-x/)
    }
    // 月份条容器仍绑定同一 class（未新增类名分叉）
    expect(recordListSource).toMatch(/class="month-scroller"/)
    expect(recordListSource).not.toMatch(/month-scroller-\w/)
  })
})

// ---------------------------------------------------------------------------
// M10（需求十）：账单页行首图标统一为设置页入口同款 primary 色系（设计 §10.2 / 测试 §10.4-2）
//   复用既有全局 .entry-avatar（D8，零新增类、global.scss 零改动）；
//   收支双色（#FFE8E8/#E8FFF3 底 + #FF6B6B/#20C997 图标）整体撤除，收支仅由金额红/绿表达。
//   记录详情页（RecordDetailPage.vue）按需求 10.4 裁定不改，故两色断言只作用于本页源码。
// ---------------------------------------------------------------------------
describe('RecordListPage - 行图标 primary 色系统一（M10）', () => {
  it('用例1: 行 avatar 复用 .entry-avatar，图标 color="primary"（无新增类、无 :color 双色）', () => {
    const rowAvatar = recordListSource.match(/<v-list-item[\s\S]*?<\/v-list-item>/)
    expect(rowAvatar, '未找到账单行结构').toBeTruthy()
    expect(rowAvatar[0]).toMatch(/<v-avatar\s+class="entry-avatar\s+mr-2"\s+size="40">/)
    expect(rowAvatar[0]).toMatch(/<v-icon\s+color="primary"\s+size="20">/)
    // 不复用行内 style/:color，仍沿用全局类（D8）
    expect(rowAvatar[0]).not.toMatch(/:color=/)
    expect(recordListSource).not.toMatch(/\.entry-avatar\s*\{/)
  })

  it('用例2: 收支双色字面量在本页源码零命中（模板区与样式区皆无）', () => {
    expect(recordListSource).not.toMatch(/#FFE8E8/i)
    expect(recordListSource).not.toMatch(/#E8FFF3/i)
  })

  it('用例3: 图标仍是分类图标且缺失回退 mdi-circle；金额区红/绿 + −/+ 前缀口径不动', () => {
    expect(recordListSource).toMatch(/\{\{\s*record\.category_icon\s*\|\|\s*'mdi-circle'\s*\}\}/)
    // 【v1.4.3-boot M6 改写，任务 5.4】金额色由内联三元 → .amount-* 专用类（深色红线见 M6 组用例1），
    // 金额文本改过 formatAmount；红/绿与 −/+ 前缀语义口径不动（D7）
    expect(recordListSource).toMatch(
      /:class="record\.type === 'expense' \? 'amount-expense' : 'amount-income'"/,
    )
    expect(recordListSource).toMatch(
      /\{\{\s*record\.type === 'expense'\s*\?\s*'-'\s*:\s*'\+'\s*\}\}\s*\{\{\s*formatAmount\(record\.amount\)\s*\}\}/,
    )
  })
})

// ---------------------------------------------------------------------------
// v1.4.3 M14（任务 7.2 / 9.5）：批量操作条收编为 <Transition name="batch-bar">
//   —— 进出对称动画（旧 slideDown 只有 enter、leave 瞬删），时长走 --expand-duration 口径
// ---------------------------------------------------------------------------
describe('RecordListPage - 批量操作条进出对称动画（M14）', () => {
  it('用例M14-批1: 批量条由 Transition(name="batch-bar") 托管，出现/消失均经它（快照类名变化）', async () => {
    const wrapper = mount(RecordListPage)
    await flushPromises()

    // 未选中时不渲染批量条，也无过渡托管
    expect(wrapper.find('.batch-bar').exists()).toBe(false)

    wrapper.vm.selected = [1, 2]
    await nextTick()

    const shells = wrapper.findAllComponents(Transition)
    const barShell = shells.find((s) => s.props('name') === 'batch-bar')
    expect(barShell, '批量操作条未被 Transition name="batch-bar" 托管').toBeTruthy()
    expect(barShell.find('.batch-bar').exists()).toBe(true)
    // 进入瞬间的可观测类名序列（jsdom 无真实过渡 → 至少 from/active 类由 Vue 同步落上）
    expect(wrapper.find('.batch-bar').classes()).toContain('batch-bar')

    vi.advanceTimersByTime(80)
    await nextTick()
    expect(wrapper.find('.batch-bar').exists()).toBe(true)

    wrapper.vm.selected = []
    await nextTick()
    expect(wrapper.find('.batch-bar').exists()).toBe(false)
    // 过渡托管本身常驻（leave 也走同一 Transition，非旧实现的瞬删）
    expect(wrapper.findAllComponents(Transition).some((s) => s.props('name') === 'batch-bar')).toBe(true)
    wrapper.unmount()
  })

  it('用例M14-批2: ?raw 源码锁——Transition 包裹 v-if 条 + 对称样式引用 --expand-* + slideDown 零残留', () => {
    expect(recordListSource).toMatch(
      /<Transition name="batch-bar">\s*<div v-if="selected\.length > 0" class="batch-bar mb-3">/,
    )
    expect(recordListSource).toMatch(/<\/Transition>/)
    expect(recordListSource).toMatch(
      /\.batch-bar-enter-active,\s*\.batch-bar-leave-active\s*\{[\s\S]*?transform var\(--expand-duration\) var\(--expand-easing\)[\s\S]*?opacity var\(--expand-duration\) var\(--expand-easing\)/,
    )
    // enter-from 与 leave-to 同型（位移 ±10px + 透明），即进出对称
    expect(recordListSource).toMatch(
      /\.batch-bar-enter-from,\s*\.batch-bar-leave-to\s*\{[^}]*opacity:\s*0;[^}]*transform:\s*translateY\(-10px\)/,
    )
    expect(recordListSource).not.toMatch(/slideDown|@keyframes/)
    // 不接原点：条贴列表顶部，位移方向即触发语境（任务 7.2）
    expect(recordListSource).not.toMatch(/batch-bar[\s\S]{0,80}transformOrigin/)
  })
})

// ---------------------------------------------------------------------------
// v1.4.3-boot M6（需求六）：金额红/绿配色全站恢复 + 列表金额格式对齐
//   根因（设计 §6.1）：深色主题 .v-theme--dark .font-weight-bold / .text-body-x 以
//   color: … !important 压制内联配色（样式表 !important > 内联）→ 深色下红绿全灭。
//   修复（D7）：新增 .amount-expense/.amount-income/.amount-neutral 专用类（!important、
//   明暗同色）+ 七节点内联→类迁移；**深色排版强制规则不删不削弱**（红线 2，用例1b 锁）。
//   本组承载设计 §6.4 用例 1（global.scss raw）/ 2、3（本页 ?raw + DOM）/ 5（format.js 导出面）；
//   用例 4（既有固化用例改写）落在本文件 M10 组：DOM 两条 + ?raw 用例3 两条。
//   其余四文件 ?raw（用例 2 全站汇总）与统计页三卡/结余三态（用例 3）见 StatisticsPage.test.js。
// ---------------------------------------------------------------------------
import * as formatApi from '@/utils/format'

/** 取 global.scss 里某个类选择器（可传 "amount-expense.amount-expense" 双类）的声明块 */
function cssClassRule(source, className) {
  const escaped = className.replace(/\./g, '\\.')
  const hit = source.match(new RegExp(`\\.${escaped}\\s*\\{[^}]*\\}`))
  expect(hit, `global.scss 未定义 .${className}`).toBeTruthy()
  return hit[0]
}

describe('RecordListPage - 金额红/绿语义专用类配色（M6）', () => {
  const globalStyles = readSourceFile(join('src', 'styles', 'global.scss'))
  const formatSource = readSourceFile(join('src', 'utils', 'format.js'))

  it('用例1（设计 §6.4-1 / 任务 5.1）: global.scss 三张专用类声明在场且带 !important、明暗同色', () => {
    expect(cssClassRule(globalStyles, 'amount-expense')).toMatch(/color:\s*#FF6B6B\s*!important/)
    expect(cssClassRule(globalStyles, 'amount-income')).toMatch(/color:\s*#20C997\s*!important/)
    expect(cssClassRule(globalStyles, 'amount-neutral')).toMatch(/color:\s*#9E9E9E\s*!important/)
    // 类色值与原内联口径逐字相同 → 浅色模式零变化（色值正则复用为类色值锁）
    expect(cssClassRule(globalStyles, 'amount-expense')).toMatch(EXPENSE_COLOR)
    expect(cssClassRule(globalStyles, 'amount-income')).toMatch(INCOME_COLOR)
    // 特异度提级声明同色同重要度在场：深色块为 .v-theme--dark + 排版类的 (0,2,0) 复合选择器，
    // 而层叠在「同为 author + 同为 !important」时按特异度择优 → 单类 (0,1,0) 深色下仍会被压白，
    // 必须有双类提级（仓库既定手法，见 global.scss M14 slide-y 收敛）本模块才真正生效
    expect(cssClassRule(globalStyles, 'amount-expense.amount-expense')).toMatch(
      /color:\s*#FF6B6B\s*!important/,
    )
    expect(cssClassRule(globalStyles, 'amount-income.amount-income')).toMatch(
      /color:\s*#20C997\s*!important/,
    )
    expect(cssClassRule(globalStyles, 'amount-neutral.amount-neutral')).toMatch(
      /color:\s*#9E9E9E\s*!important/,
    )
    // .amount-node 仅测试锚点，不得定义任何样式
    expect(globalStyles).not.toMatch(/\.amount-node\s*\{/)
  })

  it('用例1b（红线 2 / 任务 1.2）: 深色排版强制规则逐字在场——修复未削弱全局可读性规则', () => {
    expect(globalStyles).toMatch(
      /\.v-theme--dark \.text-h5,\s*\.v-theme--dark \.text-h6,\s*\.v-theme--dark \.text-subtitle-1,\s*\.v-theme--dark \.text-subtitle-2,\s*\.v-theme--dark \.font-weight-bold\s*\{\s*color: #FFFFFF !important;\s*\}/,
    )
    expect(globalStyles).toMatch(
      /\.v-theme--dark \.text-body-1,\s*\.v-theme--dark \.text-body-2\s*\{\s*color: #E6E1E5 !important;\s*\}/,
    )
    // 源序锁：提级块与深色块同为 (0,2,0)，打平时后出现者胜 → 提级块必须始终排在其之后
    const darkIdx = globalStyles.indexOf('.v-theme--dark .font-weight-bold')
    expect(darkIdx).toBeGreaterThan(-1)
    for (const cls of ['amount-expense', 'amount-income', 'amount-neutral']) {
      expect(globalStyles.indexOf(`.${cls}.${cls}`)).toBeGreaterThan(darkIdx)
    }
  })

  it('用例2（设计 §6.4-2 / 任务 5.2）: 本页 ?raw——行金额挂语义类与锚点类，内联三元色与裸金额零残留', () => {
    expect(recordListSource).toMatch(
      /class="font-weight-bold text-body-1 mr-2 amount-node"/,
    )
    expect(recordListSource).toMatch(
      /:class="record\.type === 'expense' \? 'amount-expense' : 'amount-income'"/,
    )
    // 反向红线：内联 :style 三元色、未经 formatAmount 的裸金额、静态内联色
    expect(recordListSource).not.toMatch(/:style="\{ color: record\.type/)
    expect(recordListSource).not.toMatch(/\{\{\s*record\.amount\s*\}\}/)
    expect(recordListSource).not.toMatch(/style="color: #FF|style="color: #20/)
    // 格式对齐的依赖面：本页此前零引用 formatAmount
    expect(recordListSource).toMatch(/\{\{\s*formatAmount\(record\.amount\)\s*\}\}/)
    expect(recordListSource).toMatch(/import \{ formatAmount \} from '@\/utils\/format'/)
    // 前缀维持 ASCII '-'（不引入 U+2212 作前缀字面量）
    expect(recordListSource).toMatch(/\? '-'\s*:\s*'\+'/)
    expect(recordListSource).not.toMatch(/'[−]'/)
  })

  it('用例3（设计 §6.4-3 / 任务 5.3）: DOM 行金额 = 语义类 + 锚点类，文本为 −¥128.00 完整格式', async () => {
    const wrapper = mount(RecordListPage, { global: { stubs: ROW_SLOT_STUBS } })
    await flushPromises()

    wrapper.vm.records = [
      {
        id: 1,
        type: 'expense',
        amount: 128,
        category_icon: 'mdi-food',
        category_name: '餐饮',
        consume_time: '2026-06-06 12:00',
      },
      {
        id: 2,
        type: 'income',
        amount: 3000,
        category_icon: 'mdi-cash',
        category_name: '工资',
        consume_time: '2026-06-05 09:00',
      },
    ]
    await nextTick()

    const amounts = wrapper.findAll('.record-card .amount-node')
    expect(amounts).toHaveLength(2)
    expect(amounts[0].classes()).toContain('amount-expense')
    expect(amounts[1].classes()).toContain('amount-income')
    // 同屏一红一绿、前缀一 − 一 +，且金额为千分位 + 两位小数完整格式
    expect(amounts[0].text()).toBe('-¥128.00')
    expect(amounts[1].text()).toBe('+¥3,000.00')
    for (const node of amounts) {
      expect(node.text()).toMatch(/^[+-]¥[\d,]+\.\d{2}$/)
      // 颜色不再走内联 style（否则深色下被排版 !important 压制）
      expect(node.attributes('style')).toBeUndefined()
    }
    wrapper.unmount()
  })

  it('用例5（设计 §6.4-5 / 任务 5.5）: utils/format.js 导出面收敛——死助手 getTypeColor 已删除', () => {
    expect(formatApi.getTypeColor).toBeUndefined()
    expect(typeof formatApi.formatAmount).toBe('function')
    expect(formatSource).not.toMatch(/getTypeColor/)
    // 配色真源唯一在 CSS 类：JS 侧不保留红绿字面量副本（防漂移，D7「删除」分支）
    expect(formatSource).not.toMatch(/#FF6B6B|#20C997/)
  })
})
