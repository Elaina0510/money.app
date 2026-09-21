import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock vue-router
const mockBack = vi.fn()
const mockPush = vi.fn()
// v1.4.3-boot M2：编辑态（route.params.id）用例需可控路由参数——
// 既有各用例读到的仍是同一个空对象，行为零变化；M2 组内按需写入/清除 id
const mockRouteParams = {}

vi.mock('vue-router', () => ({
  useRouter: () => ({
    back: mockBack,
    push: mockPush,
  }),
  useRoute: () => ({
    params: mockRouteParams,
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
// v1.4.3-boot M2 §5：加载解耦用例需按用例改写模板/回填两路接口行为
import { getQuickTemplates, getRecord } from '@/api/records'

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

// ── v1.4.3-boot M2 加载解耦与三态（需求二，任务 §5）────────────────────────────
// 现场取证结论（详见 progress.md 的 M2 复现登记）：/api/categories 200 + /api/records/quick-templates 500
// → 旧 `Promise.all([getCategories(), getQuickTemplates()])` 单 try 连坐 → 分类恒久空白、无任何提示。
describe('RecordFormPage - M2 加载解耦与三态', () => {
  // 全量单列表（含末位「其他」）：4 条足以验证九宫格不被截断
  const M2_CATEGORIES = [
    { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
    { id: 2, name: '出行', type: 'expense', icon: 'mdi-bus' },
    { id: 3, name: '购物', type: 'expense', icon: 'mdi-cart' },
    { id: 4, name: '其他', type: 'expense', icon: 'mdi-cash-minus' },
  ]
  const dup = () => M2_CATEGORIES.map((c) => ({ ...c }))
  const SANDBOX_500 = () => new Error('服务器内部错误')

  beforeEach(() => {
    vi.clearAllMocks()
    getCategories.mockResolvedValue(dup())
    getQuickTemplates.mockResolvedValue([
      { id: 11, tag_id: 5, tag_name: '地铁', type: 'expense', amount: 6, category_id: 2 },
    ])
    getRecord.mockResolvedValue(null)
  })

  afterEach(() => {
    // 还原文件级默认，绝不泄漏到后续用例组（M3/M4）
    delete mockRouteParams.id
    getCategories.mockResolvedValue([
      { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
      { id: 2, name: '工资', type: 'income', icon: 'mdi-cash' },
    ])
    getQuickTemplates.mockResolvedValue([])
    getRecord.mockResolvedValue(null)
  })

  it('用例5.1: 模板接口 500 → 九宫格全量渲染 + 默认选中 + 模板卡隐藏 + 无错误态（连坐已消灭）', async () => {
    getQuickTemplates.mockRejectedValue(SANDBOX_500())
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // 两路各自独立发出，模板失败不再牵制分类赋值
    expect(getCategories).toHaveBeenCalledTimes(1)
    expect(getQuickTemplates).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.categories).toHaveLength(4)
    expect(wrapper.vm.currentCategories).toHaveLength(4)
    expect(wrapper.findAll('.category-chip')).toHaveLength(4)
    // 默认选中取首个非「其他」（既有 M8 语义不变）
    expect(wrapper.vm.categoryId).toBe(1)
    expect(wrapper.findAll('.category-chip')[0].classes()).toContain('active-category')
    // 模板卡 v-if="templates.length" 自然隐藏；分类侧无错误/空态
    expect(wrapper.vm.templates).toEqual([])
    expect(wrapper.text()).not.toContain('快速记账')
    expect(wrapper.vm.categoriesError).toBe(false)
    expect(wrapper.vm.categoriesLoading).toBe(false)
    expect(wrapper.findAll('.category-state')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('分类加载失败')
    expect(wrapper.text()).not.toContain('暂无分类')
  })

  it('用例5.2: 分类接口 500 → 错误态文案 + 重试按钮在场；重试成功 → 分类渲染 + 默认选中 + isDirty===false', async () => {
    getCategories.mockRejectedValueOnce(SANDBOX_500())
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    expect(wrapper.vm.categoriesError).toBe(true)
    expect(wrapper.vm.categoriesLoading).toBe(false)
    expect(wrapper.vm.categories).toEqual([])
    expect(wrapper.vm.categoryId).toBeNull()
    expect(wrapper.text()).toContain('分类加载失败，请检查网络后重试')
    // 不再静默留白：错误态与空态互斥（分支顺序锁在 5.7）
    const states = wrapper.findAll('.category-state')
    expect(states).toHaveLength(1)
    expect(states[0].text()).toContain('重试')
    expect(states[0].text()).not.toContain('暂无分类')
    // 分类为空 → canSubmit 口径未动，保存按钮自然禁存
    expect(wrapper.vm.canSubmit).toBe(false)
    expect(getQuickTemplates).toHaveBeenCalledTimes(1) // 模板一路未受牵连

    // 点错误态里的重试按钮（mock 已转成功：Once 只吃掉首调用）
    const retryBtn = states[0].find('v-btn')
    expect(retryBtn.exists()).toBe(true)
    await retryBtn.trigger('click')
    await flushPromises()

    expect(wrapper.vm.categoriesError).toBe(false)
    expect(wrapper.findAll('.category-chip')).toHaveLength(4)
    expect(wrapper.vm.categoryId).toBe(1)
    expect(wrapper.findAll('.category-state')).toHaveLength(0)
    // 系统补选的默认分类并入基线：重试不得把表单判成「用户改过」
    expect(wrapper.vm.isDirty).toBe(false)
    // 重试后真实编辑仍要能转脏（基线可解释，不是把 dirty 关掉）
    wrapper.vm.amount = '88'
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(true)
    wrapper.vm.amount = ''
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(false)
  })

  it('用例5.2b: 重试幂等——连续重试不叠加状态、不制造脏位', async () => {
    getCategories.mockRejectedValueOnce(SANDBOX_500())
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(wrapper.vm.categoriesError).toBe(true)

    await wrapper.vm.retryLoadCategories()
    await flushPromises()
    await wrapper.vm.retryLoadCategories()
    await flushPromises()

    expect(getCategories).toHaveBeenCalledTimes(3)
    expect(wrapper.vm.categories).toHaveLength(4)
    expect(wrapper.findAll('.category-chip')).toHaveLength(4)
    expect(wrapper.vm.categoriesError).toBe(false)
    expect(wrapper.vm.categoriesLoading).toBe(false)
    expect(wrapper.vm.isDirty).toBe(false)
  })

  it('用例5.3: 分类返回空数组 → 空态引导文案渲染（不渲染无信息空白）', async () => {
    getCategories.mockResolvedValue([])
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    expect(wrapper.vm.categories).toEqual([])
    expect(wrapper.vm.categoriesError).toBe(false) // 空列表不是错误
    expect(wrapper.findAll('.category-chip')).toHaveLength(0)
    const states = wrapper.findAll('.category-state')
    expect(states).toHaveLength(1)
    expect(states[0].text()).toContain('暂无分类，请先到 设置 → 分类管理 添加分类')
    // 空态无重试入口（错误态专属），且保存仍被 categoryId===null 拦住
    expect(states[0].text()).not.toContain('重试')
    expect(wrapper.vm.categoryId).toBeNull()
    expect(wrapper.vm.canSubmit).toBe(false)
    expect(wrapper.vm.isDirty).toBe(false)
  })

  it('用例5.2c: 两路全失败 → 各自状态独立成立（分类错误态 + 模板静默降级）（任务 4.3）', async () => {
    getCategories.mockRejectedValue(SANDBOX_500())
    getQuickTemplates.mockRejectedValue(SANDBOX_500())
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // 分类侧：错误态 + 重试
    expect(wrapper.vm.categories).toEqual([])
    expect(wrapper.vm.categoriesError).toBe(true)
    expect(wrapper.text()).toContain('分类加载失败，请检查网络后重试')
    expect(wrapper.findAll('.category-state')).toHaveLength(1)
    // 模板侧：清空 + 卡片隐藏，且不给分类侧添乱（无 toast、无第二块状态区）
    expect(wrapper.vm.templates).toEqual([])
    expect(wrapper.text()).not.toContain('快速记账')
    expect(wrapper.findAll('.template-chip')).toHaveLength(0)
    // 快照照常落定（两路皆失败也判不出脏）
    expect(wrapper.vm.isDirty).toBe(false)
    expect(wrapper.vm.canSubmit).toBe(false)
  })

  it('用例5.4: 分类 resolve 后 initialSnapshot 恒定落定 → 改任意字段 isDirty===true（锁死旧 :482 连坐）', async () => {
    // 模板一路同批失败——旧实现正是这里把快照一起废掉，导致 dirty 追踪失灵
    getQuickTemplates.mockRejectedValue(SANDBOX_500())
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    expect(wrapper.vm.isDirty).toBe(false)

    wrapper.vm.amount = '999'
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(true)

    wrapper.vm.amount = ''
    await nextTick()
    wrapper.vm.recordType = 'income'
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(true)
  })

  it('用例5.5: 编辑态 getRecord 500 → 分类仍完整渲染、不空白表单', async () => {
    mockRouteParams.id = '42'
    getRecord.mockRejectedValue(SANDBOX_500())
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    expect(wrapper.vm.isEdit).toBe(true)
    expect(wrapper.vm.recordId).toBe(42)
    expect(getRecord).toHaveBeenCalledWith(42)
    // 回填失败不再连坐分类：九宫格完整 + 默认选中 + 无错误态
    expect(wrapper.findAll('.category-chip')).toHaveLength(4)
    expect(wrapper.vm.categoryId).toBe(1)
    expect(wrapper.vm.categoriesError).toBe(false)
    expect(wrapper.text()).not.toContain('分类加载失败')
    // 失败有可见提示（toast 文案在源码断言里锁：mock store 的 showToast 每次新实例）
    expect(recordFormSource).toMatch(/账单加载失败/)
    // 快照照常落定，用户自行补录即视为改动
    expect(wrapper.vm.isDirty).toBe(false)
    wrapper.vm.amount = '20'
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(true)
  })

  it('用例5.5b: 编辑态分类失败 + 记录成功 → categoryId 取记录分类且可保存（更新不依赖列表展示）（任务 4.4）', async () => {
    mockRouteParams.id = '9'
    getCategories.mockRejectedValue(SANDBOX_500())
    getRecord.mockResolvedValue({
      type: 'expense',
      amount: 58.5,
      category_id: 77,
      consume_time: '2026-05-06 12:30',
      tag: null,
      note: '分类挂了也要能改',
    })
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    expect(wrapper.vm.categoriesError).toBe(true)
    expect(wrapper.vm.categories).toEqual([])
    expect(wrapper.findAll('.category-chip')).toHaveLength(0)
    // 记录携带的分类仍在选中位，保存按钮可用（错误态区域与「已选分类」语义不冲突）
    expect(wrapper.vm.categoryId).toBe(77)
    expect(wrapper.vm.amount).toBe('58.5')
    expect(wrapper.vm.canSubmit).toBe(true)
    expect(wrapper.vm.isDirty).toBe(false)
    // 默认补选未把 categoryId 抢回列表首项（守卫在补选时刻，列表为空时更不动）
    expect(wrapper.text()).toContain('分类加载失败，请检查网络后重试')
  })

  it('用例5.6: 竞态——分类慢 resolve + 记录快 resolve → 终态 categoryId === record.category_id', async () => {
    mockRouteParams.id = '7'
    let releaseCategories
    getCategories.mockImplementation(
      () =>
        new Promise((resolve) => {
          releaseCategories = resolve
        })
    )
    getRecord.mockResolvedValue({
      type: 'income',
      amount: 128.5,
      category_id: 3,
      consume_time: '2026-03-04 09:30',
      tag: null,
      note: '竞态样本',
    })

    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // 记录先到并已回填；分类仍在加载中 → 既不闪空态也不给重试按钮（分支互斥，任务 4.6）
    expect(wrapper.vm.categoryId).toBe(3)
    expect(wrapper.vm.categoriesLoading).toBe(true)
    expect(wrapper.findAll('.category-chip')).toHaveLength(0)
    expect(wrapper.findAll('v-progress-circular')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('分类加载失败')
    expect(wrapper.text()).not.toContain('暂无分类')
    expect(wrapper.text()).not.toContain('重试')
    expect(wrapper.vm.isDirty).toBe(false) // 快照未落定前不判脏

    releaseCategories(dup())
    await flushPromises()

    // 后到的默认补选被 categoryId===null 守卫拦住 → 终态收敛到记录分类
    expect(wrapper.findAll('.category-chip')).toHaveLength(4)
    expect(wrapper.vm.categoryId).toBe(3)
    expect(wrapper.vm.recordType).toBe('income')
    expect(wrapper.vm.amount).toBe('128.5')
    expect(wrapper.vm.isDirty).toBe(false)

    wrapper.vm.note = '竞态样本-改'
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(true)
  })

  it('用例5.6b: 竞态反序——分类快 resolve + 记录慢 resolve → 终态仍等于 record.category_id', async () => {
    mockRouteParams.id = '8'
    let releaseRecord
    getRecord.mockImplementation(
      () =>
        new Promise((resolve) => {
          releaseRecord = resolve
        })
    )
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    // 分类先到：默认补选照常生效（非编辑回填态不应等记录）
    expect(wrapper.vm.categoriesLoading).toBe(false)
    expect(wrapper.findAll('.category-chip')).toHaveLength(4)
    expect(wrapper.vm.categoryId).toBe(1)

    releaseRecord({
      type: 'expense',
      amount: 12,
      category_id: 3,
      consume_time: '2026-02-03 04:05',
      tag: null,
      note: '',
    })
    await flushPromises()

    // 记录后到 → 覆盖为记录分类；两序皆收敛（设计 §2.2.1 竞态口径）
    expect(wrapper.vm.categoryId).toBe(3)
    expect(wrapper.vm.amount).toBe('12')
    expect(wrapper.vm.isDirty).toBe(false) // 快照在 allSettled 之后落定
    wrapper.vm.note = '改一笔'
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(true)
  })

  it('用例5.7: 源码红线——Promise.all([getCategories 零命中 + allSettled 在场 + 三态顺序 + 既有公开面未改名', () => {
    // 解耦完成判据
    expect(recordFormSource).not.toMatch(/Promise\.all\(\[getCategories/)
    expect(recordFormSource).toMatch(/Promise\.allSettled\(/)
    // 三 loader + 重试包装齐备，且快照在 allSettled 之后
    expect(recordFormSource).toMatch(/async function loadCategories\(\)/)
    expect(recordFormSource).toMatch(/async function loadTemplates\(\)/)
    expect(recordFormSource).toMatch(/async function loadRecordForEdit\(\)/)
    expect(recordFormSource).toMatch(/async function retryLoadCategories\(\)/)
    expect(recordFormSource).toMatch(/categoryId\.value === null/) // 默认补选守卫
    const settled = recordFormSource.indexOf('await Promise.allSettled(tasks)')
    const snapshot = recordFormSource.lastIndexOf('initialSnapshot = takeSnapshot()')
    expect(settled).toBeGreaterThan(-1)
    expect(snapshot).toBeGreaterThan(settled)
    // 三态分支顺序：加载 → 错误 → 空 → 九宫格（错误态在空态之前）
    const iLoading = recordFormSource.indexOf('v-if="categoriesLoading"')
    const iError = recordFormSource.indexOf('v-else-if="categoriesError"')
    const iEmpty = recordFormSource.indexOf('v-else-if="categories.length === 0"')
    const iGrid = recordFormSource.indexOf('<v-row v-else dense>')
    expect(iLoading).toBeGreaterThan(-1)
    expect(iError).toBeGreaterThan(iLoading)
    expect(iEmpty).toBeGreaterThan(iError)
    expect(iGrid).toBeGreaterThan(iEmpty)
    expect(recordFormSource).toMatch(/@click="retryLoadCategories"/)
    // canSubmit 口径不动（任务 2.7）
    expect(recordFormSource).toMatch(
      /parseFloat\(amount\.value\) > 0 && categoryId\.value !== null/
    )
    // 既有公开面回归红线（任务 2.8）：误伤即红灯
    expect(recordFormSource).toMatch(/const currentCategories = computed\(\(\) => categories\.value\)/)
    expect(recordFormSource).toMatch(/class="category-chip"/)
    expect(recordFormSource).toMatch(/'active-category'/)
    expect(recordFormSource).toMatch(/@update:search="onTagSearch"/)
    expect(recordFormSource).toMatch(/:items="tagSearchResults"/)
    expect(recordFormSource).toMatch(/:loading="tagSearching"/)
    // 任务 4.7：401 走 request.js 全局登出链路，本页零特化（不得自行处理）
    expect(recordFormSource).not.toMatch(/401|auth:logout/)
  })
})
