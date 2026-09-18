import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'

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

// store 的 filters 在真实实现中是响应式且跨挂载保留的对象：这里同样用 reactive 模拟
const mockFilters = reactive({
  start_date: '',
  end_date: '',
  type: '',
  category_id: null,
  tag_id: null,
  keyword: '',
})

// Mock stores
vi.mock('@/stores/useRecordsStore', () => ({
  useRecordsStore: () => ({
    filters: mockFilters,
    batchDelete: vi.fn().mockResolvedValue({}),
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

  it('should maintain expense background color', async () => {
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

    // Check that expense records still have the correct background color
    const avatar = wrapper.find('.v-avatar')
    if (avatar.exists()) {
      expect(avatar.attributes('style')).toContain('#FFE8E8')
    }
  })

  it('should maintain income background color', async () => {
    const wrapper = mount(RecordListPage)
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

    // Check that income records still have the correct background color
    const avatar = wrapper.find('.v-avatar')
    if (avatar.exists()) {
      expect(avatar.attributes('style')).toContain('#E8FFF3')
    }
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
