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
// v1.4.3 M8 §10.4：统一分类列表（收支共用）供记账页九宫格断言
import { getCategories } from '@/api/categories'
// v1.4.3 M4 §5.3：日期弹窗「关闭时才回写」→ 表单 consumeDate/dirty 断言
import DatePickerPopover from '@/components/common/DatePickerPopover.vue'

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

// ── v1.4.3 M8 分类收支共用：记账页九宫格取全量单列表（任务 §10.4）────────────
describe('RecordFormPage - M8 分类收支共用统一列表', () => {
  // 统一后的可见集合：type 列按 D2 保留迁移前原值，前端一律不得读取
  const UNIFIED_CATEGORIES = [
    { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
    { id: 2, name: '出行', type: 'expense', icon: 'mdi-bus' },
    { id: 9, name: '工资', type: 'income', icon: 'mdi-cash' },
    { id: 10, name: '红包', type: 'income', icon: 'mdi-cash-plus' },
    { id: 8, name: '其他', type: 'expense', icon: 'mdi-cash-minus' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    getCategories.mockResolvedValue(UNIFIED_CATEGORIES.map((c) => ({ ...c })))
  })

  it('用例10.4a: 收入/支出切换后九宫格数量恒为全量 5，选中项不被重置', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // 全量单列表：原收入预设 工资/红包 一并渲染
    expect(wrapper.vm.currentCategories).toHaveLength(5)
    expect(wrapper.findAll('.category-chip')).toHaveLength(5)

    // 选中一个「原收入分类」（工资），在支出模式下即可选
    wrapper.vm.recordType = 'expense'
    wrapper.vm.categoryId = 9
    await nextTick()
    expect(wrapper.findAll('.category-chip')[2].classes()).toContain('active-category')

    // 切到收入 → 数量与选中均不变
    wrapper.vm.recordType = 'income'
    await nextTick()
    expect(wrapper.vm.currentCategories).toHaveLength(5)
    expect(wrapper.findAll('.category-chip')).toHaveLength(5)
    expect(wrapper.vm.categoryId).toBe(9)

    // 切回支出 → 同理（原「选中项出组重置」逻辑已随 M8 删除）
    wrapper.vm.recordType = 'expense'
    await nextTick()
    expect(wrapper.vm.currentCategories.map((c) => c.id)).toEqual([1, 2, 9, 10, 8])
    expect(wrapper.vm.categoryId).toBe(9)
  })

  it('用例10.4b: 默认选中取全列表首个非「其他」项', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    expect(wrapper.vm.categoryId).toBe(1)

    // 极端态：全列表仅「其他」→ 兜底仍可选中，不置空
    getCategories.mockResolvedValueOnce([
      { id: 8, name: '其他', type: 'expense', icon: 'mdi-cash-minus' },
    ])
    const onlyOther = mount(RecordFormPage)
    await flushPromises()
    expect(onlyOther.vm.categoryId).toBe(8)
  })

  it('用例10.4c: 源码红线——分类不再按 cat.type 过滤，着色仍随交易 type', () => {
    // 分类侧零 type 依赖
    expect(recordFormSource).not.toMatch(/cats?\.filter\(\(c\)\s*=>\s*c\.type/)
    expect(recordFormSource).not.toMatch(/cat\.type/)
    expect(recordFormSource).toMatch(/const currentCategories = computed\(\(\) => categories\.value\)/)
    // 交易侧语义不变：九宫格/模板色由 recordType（或 tpl.type）驱动
    expect(recordFormSource).toMatch(
      /categoryId === cat\.id \? \(recordType === 'expense' \? '#FF6B6B' : '#20C997'\)/
    )
    // 「其他」不再作为默认选中项（唯一真源常量本地登记）
    expect(recordFormSource).toMatch(/const OTHER_CATEGORY_NAME = '其他'/)
  })
})

// ── v1.4.3 M4 日期弹窗「选后不关、关闭时才回写」：调用方侧口径（任务 §5.3）──────
describe('RecordFormPage - M4 日期弹窗关闭回写', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('DatePickerPopover emit 新日期 → consumeDate 更新 + isDirty=true', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // 初始快照已建立 → 未改动不脏
    expect(wrapper.vm.isDirty).toBe(false)

    const popover = wrapper.findComponent(DatePickerPopover)
    expect(popover.exists()).toBe(true)
    const before = wrapper.vm.consumeDate

    // 组件按 M4 语义只在弹窗关闭时 emit 一次最终日期
    popover.vm.$emit('update:modelValue', '2026-06-06')
    await nextTick()

    expect(wrapper.vm.consumeDate).toBe('2026-06-06')
    expect(wrapper.vm.consumeDate).not.toBe(before)
    expect(wrapper.vm.isDirty).toBe(true)
  })
})
