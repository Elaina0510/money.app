import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

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

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue([
    { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
    { id: 2, name: '工资', type: 'income', icon: 'mdi-cash' },
  ]),
}))

// Mock stores
vi.mock('@/stores/useRecordsStore', () => ({
  useRecordsStore: () => ({
    filters: {
      start_date: '',
      end_date: '',
      type: '',
      category_id: null,
    },
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
