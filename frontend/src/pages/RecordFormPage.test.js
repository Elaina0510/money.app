import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock vue-router
const mockBack = vi.fn()
const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    back: mockBack,
    push: mockPush,
  }),
  useRoute: () => ({
    params: {},
  }),
  onBeforeRouteLeave: vi.fn(),
}))

// Mock API modules
vi.mock('@/api/records', () => ({
  createRecord: vi.fn().mockResolvedValue({ id: 1 }),
  updateRecord: vi.fn().mockResolvedValue({}),
  getRecord: vi.fn().mockResolvedValue(null),
  getQuickTemplates: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue([
    { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
    { id: 2, name: '工资', type: 'income', icon: 'mdi-cash' },
  ]),
}))

vi.mock('@/api/tags', () => ({
  getTags: vi.fn().mockResolvedValue([]),
  searchTags: vi.fn().mockResolvedValue([]),
  createTag: vi.fn().mockResolvedValue({ id: 1 }),
}))

// Mock stores
vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({
    showToast: vi.fn(),
  }),
}))

// Import component after mocks
import RecordFormPage from './RecordFormPage.vue'
import recordFormSource from './RecordFormPage.vue?raw'
import { searchTags } from '@/api/tags'

describe('RecordFormPage - Leave Guard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('should have isDirty initially false', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(wrapper.vm.isDirty).toBe(false)
  })

  it('should show leave dialog when dirty and back button clicked', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // Simulate dirty state
    wrapper.vm.isDirty = true
    await nextTick()

    // Call handleBack method directly
    wrapper.vm.handleBack()

    expect(wrapper.vm.showLeaveDialog).toBe(true)
  })

  it('should call router.back() when not dirty and back button clicked', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // Call handleBack method directly (not dirty)
    wrapper.vm.handleBack()

    expect(mockBack).toHaveBeenCalled()
  })

  it('should call confirmLeave correctly', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // Set up dirty state
    wrapper.vm.isDirty = true
    wrapper.vm.showLeaveDialog = true
    wrapper.vm.pendingNavigation = vi.fn()

    await nextTick()

    // Call confirmLeave
    wrapper.vm.confirmLeave()

    expect(wrapper.vm.isDirty).toBe(false)
    expect(wrapper.vm.showLeaveDialog).toBe(false)
    expect(wrapper.vm.pendingNavigation).toHaveBeenCalled()
  })

  it('should call cancelLeave correctly', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    wrapper.vm.showLeaveDialog = true
    wrapper.vm.pendingNavigation = vi.fn()

    await nextTick()

    wrapper.vm.cancelLeave()

    expect(wrapper.vm.showLeaveDialog).toBe(false)
    expect(wrapper.vm.pendingNavigation).toBeNull()
  })

  it('should clear isDirty on successful submit', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // Set up form data
    wrapper.vm.recordType = 'expense'
    wrapper.vm.amount = '100'
    wrapper.vm.categoryId = 1
    wrapper.vm.isDirty = true

    await nextTick()

    // Submit
    await wrapper.vm.submit()

    expect(wrapper.vm.isDirty).toBe(false)
  })

  it('should have handleBack method', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(typeof wrapper.vm.handleBack).toBe('function')
  })

  it('should have confirmLeave method', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(typeof wrapper.vm.confirmLeave).toBe('function')
  })

  it('should have cancelLeave method', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(typeof wrapper.vm.cancelLeave).toBe('function')
  })

  it('should detect dirty state when form changes', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // Wait for initial snapshot
    await nextTick()

    // Change amount
    wrapper.vm.amount = '999'
    await nextTick()

    expect(wrapper.vm.isDirty).toBe(true)
  })
})

// ── M5 回归：记一笔页标签搜索触达全量（后端解除 20 条上限）──────────────
describe('RecordFormPage - 标签搜索全量回归', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('searchTags 返回 25 条时 tagSearchResults 全量渲染，前端无二次截断', async () => {
    const results = Array.from({ length: 25 }, (_, i) => ({ id: 201 + i, name: `标签${i + 1}` }))
    searchTags.mockResolvedValue(results)

    const wrapper = mount(RecordFormPage)
    await flushPromises()

    wrapper.vm.onTagSearch('标签') // 内部 200ms 防抖
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()

    expect(searchTags).toHaveBeenCalledWith('标签')
    expect(wrapper.vm.tagSearchResults).toHaveLength(25)
    // 第 21+ 条同样可选（旧后端上限下最多只有 20 条）
    expect(wrapper.vm.tagSearchResults[20].name).toBe('标签21')
    expect(wrapper.vm.tagSearchResults[24].name).toBe('标签25')
    expect(wrapper.vm.tagSearching).toBe(false)
    // 渲染源即接口返回的数组：items 直绑 tagSearchResults，无本地 slice
    expect(recordFormSource).toMatch(/:items="tagSearchResults"/)
    expect(recordFormSource).not.toMatch(/tagSearchResults\.value\.slice\(/)
  })
})
