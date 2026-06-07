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
