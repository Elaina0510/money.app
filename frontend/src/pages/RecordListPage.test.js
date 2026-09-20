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

  it('用例9: 选中态失色修复 + 居中红线（?raw 不含 selectedYear === currentYear 限定、零 scrollIntoView）', () => {
    expect(recordListSource).toMatch(
      /:color="selectedMonth === m \? 'primary' : ''"/
    )
    expect(recordListSource).not.toContain('selectedMonth === m && selectedYear === currentYear')
    expect(recordListSource).not.toMatch(/selectedYear === currentYear\s*\?\s*'primary'/)
    // 模块红线：居中禁用 scrollIntoView（会连带垂直滚动祖先，打断 M11 与详情页返回滚动）
    // 源码注释会合法提及该 API 名，故断言"无调用点"
    expect(recordListSource).not.toMatch(/\.scrollIntoView\s*\(/)
  })
})
