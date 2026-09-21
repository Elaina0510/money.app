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
// v1.4.3-boot M3：toast 文案是用例断言对象，但原工厂每次返回**新** vi.fn() 实例（调用记录不可回收）——
// 参数化为文件级 mockShowToast（沿 M2 把 vue-router mock 参数化为 mockRouteParams 的同一手法）；
// 既有各用例从未断言 showToast，行为零变化
const mockShowToast = vi.fn()

vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({
    showToast: (...args) => mockShowToast(...args),
  }),
}))

// Import component after mocks
import RecordFormPage from './RecordFormPage.vue'
import recordFormSource from './RecordFormPage.vue?raw'
import { searchTags, createTag } from '@/api/tags'
// v1.4.3 M8 §10.4：统一分类列表（收支共用）供记账页九宫格断言
import { getCategories } from '@/api/categories'
// v1.4.3 M4 §5.3：日期弹窗「关闭时才回写」→ 表单 consumeDate/dirty 断言
import DatePickerPopover from '@/components/common/DatePickerPopover.vue'
// v1.4.3-boot M2 §5：加载解耦用例需按用例改写模板/回填两路接口行为
// v1.4.3-boot M3 §5：免回车保存用例需断言落库载荷与新建标签调用
import { getQuickTemplates, getRecord, createRecord, updateRecord } from '@/api/records'
// v1.4.3-boot M4 §6.3/6.4/6.7：锚定结构断言需挂载**真实** Vuetify 组件
// （无 Vuetify 时 v-autocomplete 是未知自定义元素，内部 VMenu/overlay 根本不渲染 → 无从判断挂载点）
// 取包内聚合 ESM 构建而非 'vuetify/components' 分栏：后者每组件 import 兄弟 .css，
// vitest 默认 externalize node_modules → Node 侧 "Unknown file extension .css" 直接炸（样式另有 dist/vuetify.css，测试不需要）。
import {
  createVuetify,
  components as vuetifyComponents,
  directives as vuetifyDirectives,
} from 'vuetify/dist/vuetify.esm.js'

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

// ── v1.4.3-boot M3 标签输入免回车：保存账单即保存标签（需求三，任务 §5 八组）────────
// 痛点：输入新标签文字后不回车直接点保存，文字静默丢失（旧 submit 只读 selectedTagName）。
// 改造：submit 前置「待确认文字」归一三段 ①防抖结果内精确同名 → ②非防抖 searchTags 兜底
//      （**查询失败即中止保存**，D4）→ ③确无同名才 createTag。判定口径红线：真实 id 不采信文字。
// 附录 B 口径处置：既有测试内**不存在**「仅回车/点选才可建标签」的固化用例（全文件 grep「回车」零命中），
//      故无条件式改写可做；本组以 5.1（直接保存）/ 5.7a（点选）/ 5.7b（回车）把新口径
//      「三路径（点选/回车/直接保存）皆可建标签」显式化，旧两条路径各留一条回归用例。
describe('RecordFormPage - M3 标签输入免回车', () => {
  const M3_CATEGORIES = [
    { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
    { id: 2, name: '工资', type: 'income', icon: 'mdi-cash' },
    { id: 3, name: '出行', type: 'expense', icon: 'mdi-bus' },
  ]
  const NEW_TAG_ID = 41 // createTag 桩返回的新标签 id（本组统一，便于断言载荷 tag_id）
  const PAYLOAD_KEYS = ['amount', 'category_id', 'consume_time', 'note', 'tag_id', 'type']

  beforeEach(() => {
    vi.clearAllMocks()
    getCategories.mockResolvedValue(M3_CATEGORIES.map((c) => ({ ...c })))
    getQuickTemplates.mockResolvedValue([])
    getRecord.mockResolvedValue(null)
    searchTags.mockResolvedValue([]) // 默认：兜底查询无任何同名命中
    createTag.mockResolvedValue({ id: NEW_TAG_ID, name: '奶茶', category_id: 1 })
    createRecord.mockResolvedValue({ id: 91 })
    updateRecord.mockResolvedValue({})
  })

  afterEach(() => {
    // 还原文件级默认，绝不泄漏到后续用例组（M4）——沿 M2 组收口手法
    delete mockRouteParams.id
    getCategories.mockResolvedValue([
      { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
      { id: 2, name: '工资', type: 'income', icon: 'mdi-cash' },
    ])
    getQuickTemplates.mockResolvedValue([])
    getRecord.mockResolvedValue(null)
    searchTags.mockResolvedValue([])
    createTag.mockResolvedValue({ id: 1 })
  })

  // 挂载并填成「可保存」态；query 传值即模拟「只在输入框打字、既不点选也不回车」
  async function mountReady({ query, amount = '30', categoryId = 1 } = {}) {
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    wrapper.vm.amount = amount
    wrapper.vm.categoryId = categoryId
    if (query !== undefined) wrapper.vm.tagSearchQuery = query
    await nextTick()
    expect(wrapper.vm.canSubmit).toBe(true)
    return wrapper
  }

  it('用例5.1: 输入新标签名不回车不点选 → 保存即建标签并关联，toast 含「已新建标签「奶茶」」', async () => {
    searchTags.mockResolvedValue([{ id: 7, name: '咖啡' }]) // ②兜底可查但无精确同名
    const wrapper = await mountReady({ query: '奶茶', categoryId: 3 })

    await wrapper.vm.submit()

    // 归一走完③：以输入文字 + 当前分类建标签
    expect(createTag).toHaveBeenCalledTimes(1)
    expect(createTag).toHaveBeenCalledWith({ name: '奶茶', category_id: 3 })
    expect(createRecord).toHaveBeenCalledTimes(1)
    const payload = createRecord.mock.calls[0][0]
    expect(payload.tag_id).toBe(NEW_TAG_ID)
    // 任务 1.7：data 载荷结构零变化（六键不多不少）
    expect(Object.keys(payload).sort()).toEqual(PAYLOAD_KEYS)
    // 需求 3.3：全程无二次确认，toast 合并新建标签提示
    expect(mockShowToast).toHaveBeenCalledWith('记账成功，已新建标签「奶茶」')
    expect(wrapper.vm.isDirty).toBe(false)
    expect(mockPush).toHaveBeenCalledWith('/')
    expect(wrapper.vm.submitting).toBe(false)
  })

  it('用例5.2: 防抖结果内已有精确同名 → 零 createTag、零兜底查询，直接关联既有 id', async () => {
    const wrapper = await mountReady({ query: '奶茶' })
    wrapper.vm.tagSearchResults = [{ id: 8, name: '奶茶' }, { id: 9, name: '咖啡' }]
    await nextTick()

    await wrapper.vm.submit()

    expect(searchTags).not.toHaveBeenCalled() // ① 命中即短路，②不再发查询
    expect(createTag).not.toHaveBeenCalled() // 需求 3.2：同名零创建
    expect(createRecord).toHaveBeenCalledTimes(1)
    expect(createRecord.mock.calls[0][0].tag_id).toBe(8)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功') // 未新建 → 原文案不变
  })

  it('用例5.3: 防抖结果为空（未回）+ 非防抖兜底查到同名 → 不建标签（锁死归一②）', async () => {
    searchTags.mockResolvedValue([{ id: 12, name: '奶茶', category_id: 2 }, { id: 9, name: '咖啡' }])
    const wrapper = await mountReady({ query: '奶茶' })
    expect(wrapper.vm.tagSearchResults).toEqual([]) // 模拟输入后 200ms 内即点保存

    await wrapper.vm.submit()

    expect(searchTags).toHaveBeenCalledTimes(1)
    expect(searchTags).toHaveBeenCalledWith('奶茶')
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord.mock.calls[0][0].tag_id).toBe(12)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功')
  })

  it('用例5.4（= 边界 4.2）: tagId 为真实 id 时不采信搜索框文字，残留/异变一律丢弃', async () => {
    const wrapper = await mountReady()
    wrapper.vm.tagSearchResults = [{ id: 5, name: '健身' }]
    wrapper.vm.onTagSelected(5) // 点选既有标签（真实 id）
    await nextTick()
    expect(wrapper.vm.selectedTagId).toBe(5)

    wrapper.vm.tagSearchQuery = '奶茶' // 选中后又乱敲（误触键盘）
    await nextTick()
    await wrapper.vm.submit()

    // 红线 §2.1-5：不得扩大为「文字优先」——既不查询也不建标签，以已选中为准
    expect(searchTags).not.toHaveBeenCalled()
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord.mock.calls[0][0].tag_id).toBe(5)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功')
  })

  it('用例5.4b（任务 2.2）: ✕ 清除已选标签 → tagSearchQuery 同步清空，残留旧名不被自动确认', async () => {
    const wrapper = await mountReady({ query: '奶茶' })
    wrapper.vm.tagSearchResults = [{ id: 5, name: '奶茶' }]
    wrapper.vm.onTagSelected(5)
    wrapper.vm.tagSearchQuery = '奶茶' // clearable 对 search 重置无强保证：模拟残留
    await nextTick()

    wrapper.vm.onTagSelected(null) // ✕ 清除走 @update:model-value(null)
    await nextTick()
    expect(wrapper.vm.selectedTagId).toBeNull()
    expect(wrapper.vm.selectedTagName).toBe('')
    expect(wrapper.vm.tagSearchQuery).toBe('')

    await wrapper.vm.submit()
    expect(searchTags).not.toHaveBeenCalled()
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord.mock.calls[0][0].tag_id).toBeNull()
    // 清除分支必须含归零语句（源码锁，防后续重构回退）
    expect(recordFormSource).toMatch(
      /function onTagSelected\(tagId\) \{\s*if \(!tagId\) \{[^}]*tagSearchQuery\.value = ''/
    )
  })

  it('用例5.5: 编辑模式同口径 → updateRecord 载荷新 tag_id + toast「账单已更新，已新建标签」', async () => {
    mockRouteParams.id = '42'
    getRecord.mockResolvedValue({
      type: 'expense',
      amount: 12,
      category_id: 2,
      consume_time: '2026-05-06 12:30',
      tag: null,
      note: '编辑态样本',
    })
    searchTags.mockResolvedValue([{ id: 7, name: '咖啡' }])
    const wrapper = mount(RecordFormPage)
    await flushPromises()
    expect(wrapper.vm.isEdit).toBe(true)
    expect(wrapper.vm.categoryId).toBe(2)

    wrapper.vm.tagSearchQuery = '打车' // 编辑页只输文字，不回车不点选
    await nextTick()
    await wrapper.vm.submit()

    expect(createTag).toHaveBeenCalledWith({ name: '打车', category_id: 2 })
    expect(updateRecord).toHaveBeenCalledTimes(1)
    expect(updateRecord.mock.calls[0][0]).toBe(42)
    const payload = updateRecord.mock.calls[0][1]
    expect(payload.tag_id).toBe(NEW_TAG_ID)
    expect(Object.keys(payload).sort()).toEqual(PAYLOAD_KEYS)
    expect(createRecord).not.toHaveBeenCalled()
    expect(mockShowToast).toHaveBeenCalledWith('账单已更新，已新建标签「打车」')
    expect(wrapper.vm.isDirty).toBe(false)
  })

  it('用例5.6: 兜底查询失败 → 中止保存（建标签/落账单零调用）+ toast「标签校验失败」+ dirty 保持 + submitting 复位', async () => {
    searchTags.mockRejectedValue(new Error('网络错误')) // 校验不可用
    const wrapper = await mountReady({ query: '奶茶' })
    expect(wrapper.vm.isDirty).toBe(true)

    await wrapper.vm.submit()

    expect(searchTags).toHaveBeenCalledWith('奶茶')
    // D4 零调用断言：不得降级为「按无匹配创建」
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord).not.toHaveBeenCalled()
    expect(updateRecord).not.toHaveBeenCalled()
    expect(mockShowToast).toHaveBeenCalledWith('标签校验失败，请重试保存')
    expect(wrapper.vm.isDirty).toBe(true) // 未保存成功 → 脏位保持（离开仍走确认）
    expect(wrapper.vm.submitting).toBe(false) // finally 复位
    expect(mockPush).not.toHaveBeenCalled() // 不跳转、停留本页
    expect(wrapper.vm.selectedTagId).toBeNull() // 未回写，重试走同一段归一
  })

  it('用例5.7a: 点选旧路径零回退（搜索 → 点选既有标签 → 保存不建标签）', async () => {
    searchTags.mockResolvedValue([{ id: 8, name: '奶茶', category_id: 1 }])
    const wrapper = await mountReady()

    wrapper.vm.onTagSearch('奶茶') // 真实防抖入口（200ms）
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()
    expect(wrapper.vm.tagSearchResults).toHaveLength(1)
    wrapper.vm.onTagSelected(8)
    await nextTick()
    expect(wrapper.vm.selectedTagId).toBe(8)
    expect(wrapper.vm.selectedTagName).toBe('奶茶')

    await wrapper.vm.submit()
    expect(searchTags).toHaveBeenCalledTimes(1) // 只防抖那一次，无兜底查询
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord.mock.calls[0][0].tag_id).toBe(8)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功')
  })

  it('用例5.7b: 回车旧路径零回退（回车 temp(-1) 仅 UI 确认 → 保存时归一并创建）', async () => {
    const wrapper = await mountReady({ query: '奶茶' })

    await wrapper.vm.onCreateTagFromSearch() // @keydown.enter 处理器
    await nextTick()
    expect(createTag).not.toHaveBeenCalled() // 回车本身不落库（既有语义不变）
    expect(wrapper.vm.selectedTagId).toBe(-1)
    expect(wrapper.vm.selectedTagName).toBe('奶茶')

    await wrapper.vm.submit()
    // temp(-1) 不进①（id !== -1 过滤）→ 走②兜底 → 无同名 → ③创建，与旧行为一致
    expect(searchTags).toHaveBeenCalledWith('奶茶')
    expect(createTag).toHaveBeenCalledTimes(1)
    expect(createTag).toHaveBeenCalledWith({ name: '奶茶', category_id: 1 })
    expect(createRecord.mock.calls[0][0].tag_id).toBe(NEW_TAG_ID)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功，已新建标签「奶茶」')
  })

  it('用例5.8: 未保存即离开 → 仅改标签文字零落库、不置脏、不新增确认拦截', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    wrapper.vm.tagSearchQuery = '奶茶' // 只打字，不提交
    await nextTick()
    expect(wrapper.vm.isDirty).toBe(false) // tagSearchQuery 不入快照（任务 2.3 维持现状）

    wrapper.vm.handleBack()
    expect(wrapper.vm.showLeaveDialog).toBe(false) // 无新确认拦截
    expect(mockBack).toHaveBeenCalledTimes(1)
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord).not.toHaveBeenCalled()
    expect(searchTags).not.toHaveBeenCalled()

    await wrapper.unmount() // 离开即丢弃：归一只发生在 submit() 内
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord).not.toHaveBeenCalled()
  })

  it('边界4.1: 选中后又原样输入同名 → pending 为空 → 直接关联原标签、零创建零查询', async () => {
    const wrapper = await mountReady()
    wrapper.vm.tagSearchResults = [{ id: 6, name: '奶茶' }]
    wrapper.vm.onTagSelected(6)
    wrapper.vm.tagSearchQuery = '奶茶' // 与已选标签名逐字相同
    await nextTick()

    await wrapper.vm.submit()
    expect(searchTags).not.toHaveBeenCalled()
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord.mock.calls[0][0].tag_id).toBe(6)
  })

  it('边界4.3: 输入仅空白 → trim 后为空 → 不触发归一（零查询零创建，tag_id null）', async () => {
    const wrapper = await mountReady({ query: '   ' })

    await wrapper.vm.submit()
    expect(searchTags).not.toHaveBeenCalled()
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord).toHaveBeenCalledTimes(1)
    expect(createRecord.mock.calls[0][0].tag_id).toBeNull()
    expect(mockShowToast).toHaveBeenCalledWith('记账成功')
  })

  it('边界4.4: 回车 temp(-1) 未动直接保存 → 兜底同名即关联，否则创建（语义严格不劣化）', async () => {
    // 分支 A：兜底查到同名 → 关联既有（旧实现此处会建出重复标签）
    searchTags.mockResolvedValueOnce([{ id: 21, name: '奶茶' }])
    const existing = await mountReady({ query: '奶茶' })
    await existing.vm.onCreateTagFromSearch()
    await existing.vm.submit()
    expect(createTag).not.toHaveBeenCalled()
    expect(createRecord.mock.calls[0][0].tag_id).toBe(21)

    // 分支 B：确无同名 → 创建（与旧行为一致）
    searchTags.mockResolvedValueOnce([])
    const fresh = await mountReady({ query: '咖啡' })
    await fresh.vm.onCreateTagFromSearch()
    await fresh.vm.submit()
    expect(createTag).toHaveBeenCalledWith({ name: '咖啡', category_id: 1 })
    expect(createRecord.mock.calls[1][0].tag_id).toBe(NEW_TAG_ID)
  })

  it('边界4.5: 同名判定严格 === —— 大小写/全半角不算同名，一律走创建（不做归一化模糊）', async () => {
    searchTags.mockResolvedValue([{ id: 31, name: 'milktea' }])
    const lower = await mountReady({ query: 'MilkTea' })
    await lower.vm.submit()
    expect(createTag).toHaveBeenCalledTimes(1)
    expect(createTag).toHaveBeenCalledWith({ name: 'MilkTea', category_id: 1 })
    expect(createRecord.mock.calls[0][0].tag_id).toBe(NEW_TAG_ID)

    searchTags.mockResolvedValue([{ id: 33, name: 'coffee' }])
    const fullWidth = await mountReady({ query: 'ｃｏｆｆｅｅ' })
    await fullWidth.vm.submit()
    expect(createTag).toHaveBeenLastCalledWith({ name: 'ｃｏｆｆｅｅ', category_id: 1 })
    expect(createRecord.mock.calls[1][0].tag_id).toBe(NEW_TAG_ID)
  })

  it('用例5.9: 源码红线——归一三段顺序 + 判定口径 + 载荷结构零变化 + 旧路径/模板区域未动', () => {
    // 判定口径（§2.1-5 红线）：仅 null / -1 采信文字，真实 id 一律不采信
    expect(recordFormSource).toMatch(
      /const pending =\s*tagId === -1 \|\| tagId == null\s*\?\s*\(tagSearchQuery\.value \|\| selectedTagName\.value \|\| ''\)\.trim\(\)\s*:\s*''/
    )
    // 三段顺序：①防抖结果内精确同名（排除 temp -1）→ ②非防抖兜底 → ③createTag
    const step1 = recordFormSource.indexOf('tagSearchResults.value.find((t) => t.id !== -1')
    const step2 = recordFormSource.indexOf('const fresh = await searchTags(pending).catch(() => null)')
    const abort = recordFormSource.indexOf("appStore.showToast('标签校验失败，请重试保存')")
    const step3 = recordFormSource.indexOf('const newTag = await createTagData({ name: pending')
    expect(step1).toBeGreaterThan(-1)
    expect(step2).toBeGreaterThan(step1)
    expect(abort).toBeGreaterThan(step2)
    expect(step3).toBeGreaterThan(abort) // 中止分支在创建之前，绝不被绕过
    // 严格 === 判同名，无归一化模糊
    expect(recordFormSource).toMatch(/t\.name === pending/)
    expect(recordFormSource).not.toMatch(/toLowerCase\(\)|normalize\(|fullWidth/)
    // data 载荷六键原样（任务 1.7）
    expect(recordFormSource).toMatch(
      /const data = \{\s*amount: parseFloat\(amount\.value\),\s*type: recordType\.value,\s*category_id: categoryId\.value,\s*consume_time: `\$\{consumeDate\.value\} \$\{consumeTime\.value\}`,\s*tag_id: tagId \|\| null,\s*note: note\.value \|\| null,\s*\}/
    )
    // 需求 3.3：toast 合并新建标签提示，且无二次确认弹窗
    expect(recordFormSource).toMatch(/记账成功，已新建标签「\$\{createdTagName\}」/)
    expect(recordFormSource).toMatch(/账单已更新，已新建标签「\$\{createdTagName\}」/)
    expect(recordFormSource).not.toMatch(/window\.confirm|showTagConfirm|确认新建标签/)
    // 任务 2.3：tagSearchQuery 不入快照、不进 dirty 追踪（维持现状）
    const snap = recordFormSource.slice(
      recordFormSource.indexOf('function takeSnapshot()'),
      recordFormSource.indexOf('function handleBack()')
    )
    expect(snap).toMatch(/selectedTagName: selectedTagName\.value/)
    expect(snap).not.toMatch(/tagSearchQuery/)
    expect(recordFormSource).toMatch(
      /\[recordType, amount, categoryId, consumeDate, consumeTime, selectedTagId, selectedTagName, note\]/
    )
    expect(recordFormSource).not.toMatch(/watch\(\s*\[[^\]]*tagSearchQuery/s)
    // 旧路径绑定点与「按回车创建」提示原文不动；建标签→存账单顺序不变（§3.2.2）
    expect(recordFormSource).toMatch(/@keydown\.enter="onCreateTagFromSearch"/)
    expect(recordFormSource).toMatch(/@update:model-value="onTagSelected"/)
    expect(recordFormSource).toMatch(/无匹配标签，按回车创建「\{\{ tagSearchQuery \}\}」/)
    expect(recordFormSource.indexOf('await createTagData({ name: pending')).toBeLessThan(
      recordFormSource.indexOf('const data = {')
    )
    // M4 交接点（§4.2.2）：本模块不触碰标签浮层模板区域。
    // v1.4.3-boot M4 已按 D5 落地（任务 6.5 回归红线）：原「M4 机制尚未存在」的负向锁
    // （not.toMatch tag-field-anchor|menuProps）随 M4 合入必然为假，改锁为「控件本体绑定不变 +
    // M4 仅新增 wrap/:menu-props」的正向口径——M3 归一逻辑的消费面（selectedTagId/tagSearchQuery）零改名。
    expect(recordFormSource).toMatch(/transition="fab-transition"/)
    expect(recordFormSource).toMatch(/v-model="selectedTagId"/)
    expect(recordFormSource).toMatch(/v-model:search="tagSearchQuery"/)
    expect(recordFormSource).toMatch(/:menu-props="tagMenuProps"/)
  })
})

// ── v1.4.3-boot M4 标签建议浮层锚定输入框正下方（需求四，任务 §6 6.1–6.4 + 6.5 回归红线 + 6.7 D9）──
// 痛点：建议层是 v-autocomplete 内部 VMenu teleport 到 body 的游离浮层（覆盖式定位、与输入框无父子关系），
//      页面滚动/软键盘弹起时漂移。主方案（D5 / 设计 §4.2.1）：标签区外套 .tag-field-anchor(position:relative)
//      + :menu-props 透传 { attach: 容器元素, maxHeight: 240, contentClass: 'tag-suggest-menu' }
//      + scoped !important 锁 left/width。控件本体/v-model/搜索/选中/M3 归一逻辑零改动（§4.2.2 交接点）。
// 断言边界（prompt §7.7）：jsdom 无布局引擎 → 内联 top 参照系与 computed left/width 无真值可测，
//      故用「props 透传断言（6.1）+ ?raw 源码断言（6.2/6.5）+ 真实 Vuetify 挂载结构断言（6.3/6.4/6.7）」组合；
//      几何三点判据之 ②③ 由浏览器实测终判（P4）。
describe('RecordFormPage - M4 标签建议层锚定', () => {
  const M4_CATEGORIES = [
    { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
    { id: 3, name: '出行', type: 'expense', icon: 'mdi-bus' },
  ]
  const NEW_TAG_ID = 51
  const TAGS_MILK = [
    { id: 101, name: '奶茶', category_id: 1 },
    { id: 102, name: '牛奶', category_id: 1 },
  ]

  const live = [] // 真实 Vuetify 用例挂进 document.body，逐用例卸载防串味

  // jsdom 未实现真实浏览器内建的两个观察者 API，而真实 Vuetify 组件（VProgressCircular /
  // VLazyScope 等）构造时即用 → 本组用例的最小替身：ResizeObserver 空转（jsdom 无布局可观测）、
  // IntersectionObserver 恒判「可见」（否则 v-lazy 内容永不渲染）。仅测试侧补齐，零改产品代码与配置。
  if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class StubResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  }
  if (typeof globalThis.IntersectionObserver === 'undefined') {
    globalThis.IntersectionObserver = class StubIntersectionObserver {
      constructor(cb) {
        this.cb = cb
      }

      observe(target) {
        // 真实浏览器异步投递回调：同步回调会在 patch 期间触发响应式更新而打烂 Vue 补丁状态
        setTimeout(() => {
          try {
            this.cb([{ target, isIntersecting: true, intersectionRatio: 1 }], this)
          } catch {
            /* 用例已卸载：丢弃迟到回调 */
          }
        }, 0)
      }

      unobserve() {}
      disconnect() {}
      takeRecords() {
        return []
      }
    }
  }
  // 同上：Vuetify 的 connected 定位策略要监听 visualViewport（软键盘弹起 → 重算几何），
  // jsdom 无 VisualViewport 实现 → 给一个静态视口替身；视口随键盘变化是真机项（任务 7.4 人工）。
  if (typeof globalThis.visualViewport === 'undefined') {
    globalThis.visualViewport = {
      width: 1024,
      height: 768,
      offsetLeft: 0,
      offsetTop: 0,
      scale: 1,
      addEventListener() {},
      removeEventListener() {},
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    getCategories.mockResolvedValue(M4_CATEGORIES.map((c) => ({ ...c })))
    getQuickTemplates.mockResolvedValue([])
    getRecord.mockResolvedValue(null)
    searchTags.mockResolvedValue([]) // 默认：无同名命中
    createTag.mockResolvedValue({ id: NEW_TAG_ID, name: '奶茶', category_id: 1 })
    createRecord.mockResolvedValue({ id: 91 })
    updateRecord.mockResolvedValue({})
  })

  afterEach(async () => {
    // attachTo 的组件由 unmount 自行摘除；不再手动清空 body（会让仍在收尾的 overlay 补丁踩空节点）
    for (const w of live) await w.unmount()
    live.length = 0
    // 还原文件级默认，绝不泄漏到后续用例组（沿 M2/M3 收口手法）
    delete mockRouteParams.id
    getCategories.mockResolvedValue([
      { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food' },
      { id: 2, name: '工资', type: 'income', icon: 'mdi-cash' },
    ])
    getQuickTemplates.mockResolvedValue([])
    getRecord.mockResolvedValue(null)
    searchTags.mockResolvedValue([])
    createTag.mockResolvedValue({ id: 1 })
  })

  // 真实 Vuetify 挂载（attachTo 文档：teleport/attach 定位需真实文档树位置）
  async function mountReal() {
    const wrapper = mount(RecordFormPage, {
      attachTo: document.body,
      global: { plugins: [createVuetify({ components: vuetifyComponents, directives: vuetifyDirectives })] },
    })
    live.push(wrapper)
    await flushPromises()
    return wrapper
  }

  // 200ms 防抖 + overlay 挂载过渡（VMenu 过渡/v-lazy 需要额外帧）
  async function settle(ms = 320) {
    await new Promise((resolve) => setTimeout(resolve, ms))
    await flushPromises()
    await nextTick()
    await flushPromises()
  }

  const anchorOf = (wrapper) => wrapper.find('.tag-field-anchor').element
  const contentOf = (wrapper) => anchorOf(wrapper).querySelector('.v-overlay__content')

  // 在真实输入框里打字并等建议层就绪
  async function typeIntoTagField(wrapper, text) {
    const input = wrapper.find('.tag-field-anchor input')
    expect(input.exists()).toBe(true)
    await input.trigger('click')
    await input.trigger('focus')
    await input.setValue(text)
    await settle()
    return input
  }

  it('用例6.1: menuProps 透传——attach 即锚定容器元素本体（对象同一性）、maxHeight 240、contentClass 含 tag-suggest-menu', async () => {
    const wrapper = mount(RecordFormPage)
    await flushPromises()

    const anchor = wrapper.find('.tag-field-anchor')
    expect(anchor.exists()).toBe(true)
    // ref 挂载后恒可用：attach 必须**就是**那个 DOM 元素（同一性断言，非「形状相似」）
    expect(wrapper.vm.tagMenuProps.attach).toBe(anchor.element)
    expect(wrapper.vm.tagFieldAnchorRef).toBe(anchor.element)
    // 需求 4.3：最大高 + 内滚走 VMenu 原生 prop（不由 CSS 兜、也不新增组件）
    expect(wrapper.vm.tagMenuProps.maxHeight).toBe(240)
    expect(String(wrapper.vm.tagMenuProps.contentClass)).toContain('tag-suggest-menu')
    // 降级回落：ref 未挂载（理论竞态）→ false = body 现状，锁在源码口径上（设计 §4.3）
    expect(recordFormSource).toMatch(/attach:\s*tagFieldAnchorRef\.value\s*\?\?\s*false/)
    // menuProps 经 :menu-props 单一入口透传，且只有标签控件挂锚（其余浮层零改动）
    expect(recordFormSource.match(/:menu-props="tagMenuProps"/g)).toHaveLength(1)
    await wrapper.unmount()
  })

  it('用例6.2: ?raw 源码红线——容器 relative + !important 锁 left/width + max-height 内滚 + fab-transition 保留', () => {
    // 锚定参照系：wrap 必须 relative（overlay absolute 的定位原点）
    expect(recordFormSource).toMatch(/\.tag-field-anchor\s*\{\s*position:\s*relative;\s*\}/)
    // 覆写块：left/width 两条 !important 锁死水平对齐与同宽（非 important 压不住策略写的内联值）
    expect(recordFormSource).toMatch(/\.tag-field-anchor\s+:deep\(\.tag-suggest-menu\)\s*\{/)
    const deep = recordFormSource.slice(
      recordFormSource.indexOf('.tag-field-anchor :deep(.tag-suggest-menu)'),
      recordFormSource.indexOf('.template-chip')
    )
    expect(deep).toMatch(/left:\s*0\s*!important;/)
    expect(deep).toMatch(/width:\s*100%\s*!important;/)
    expect(deep).toMatch(/max-height:\s*240px;/)
    expect(deep).toMatch(/overflow-y:\s*auto;/)
    expect(deep).toMatch(/border-radius:\s*12px;/)
    // §十四 展开动画统一口径红线：沿用调用点 fab-transition，M4 不引入新动画体系
    expect(recordFormSource).toMatch(/transition="fab-transition"/)
    expect(deep).not.toMatch(/transition|animation/)
    expect(recordFormSource).not.toMatch(/tag-suggest-panel|v-text-field[\s\S]{0,80}tag-suggest/)
  })

  it('用例6.3: 真实 Vuetify——输入触发搜索后建议层渲染在 .tag-field-anchor 子树内（teleport-to-element 生效 + v-overlay--absolute 结构侧证）', async () => {
    searchTags.mockResolvedValue(TAGS_MILK.map((t) => ({ ...t })))
    const wrapper = await mountReal()

    await typeIntoTagField(wrapper, '奶')
    expect(searchTags).toHaveBeenCalledWith('奶')
    expect(wrapper.vm.tagSearchResults).toHaveLength(2)

    const anchor = anchorOf(wrapper)
    const overlay = anchor.querySelector('.v-overlay')
    const content = contentOf(wrapper)
    // 判据①的结构侧证：overlay 根节点进了 wrap 容器，且因 attach 翻成 absolute 定位（不再是 body 下的 fixed 游离层）
    expect(overlay).not.toBeNull()
    expect(overlay.classList.contains('v-overlay--absolute')).toBe(true)
    expect(overlay.parentElement).not.toBe(document.body)
    expect(content).not.toBeNull()
    expect(content.classList.contains('tag-suggest-menu')).toBe(true) // contentClass 确实落到 overlay content
    expect(content.closest('.tag-field-anchor')).toBe(anchor) // 父子关系成立 → 随容器滚动吸附
    // maxHeight 走 VMenu 原生 prop 且落到 DOM 内联样式（需求 4.3 内滚 + 最大高，非 JS 对象自嗨）
    expect(content.style.maxHeight).toBe('240px')
    expect(anchor.querySelector('.v-overlay-container .v-overlay--absolute')).toBe(overlay)
    // 建议项在锚定层内可读可点（25 条内滚由 maxHeight 240 保证，见 6.2）
    expect(content.textContent).toContain('奶茶')
    expect(content.textContent).toContain('牛奶')
  })

  it('用例6.4: no-data 空态槽在同一锚定层内展示（「无匹配标签」位于 .tag-field-anchor 子树，零改动）', async () => {
    searchTags.mockResolvedValue([]) // 查无同名
    const wrapper = await mountReal()

    await typeIntoTagField(wrapper, '全新标签')
    const content = contentOf(wrapper)
    expect(content).not.toBeNull()
    expect(content.textContent).toContain('无匹配标签，按回车创建「全新标签」')
    // 空态未外迁成第二块浮层：槽位仍在同一控件模板内（任务 5.5）
    expect(recordFormSource).toMatch(/<template v-slot:no-data>/)
    expect(anchorOf(wrapper).querySelectorAll('.v-overlay__content')).toHaveLength(1)
  })

  it('用例6.5: 回归红线——M4 只加模板/样式，M3 归一链路与控件公开面零改动', async () => {
    searchTags.mockResolvedValue([])
    const wrapper = mount(RecordFormPage) // 与 M3 组同口径（无 Vuetify，纯逻辑面）
    await flushPromises()

    wrapper.vm.amount = '30'
    wrapper.vm.categoryId = 1
    wrapper.vm.tagSearchQuery = '奶茶'
    await nextTick()
    await wrapper.vm.submit()

    // 归一三段照旧：无同名 → ③建标签 → tag_id 入载荷 → 合并 toast
    expect(searchTags).toHaveBeenCalledWith('奶茶')
    expect(createTag).toHaveBeenCalledWith({ name: '奶茶', category_id: 1 })
    expect(createRecord.mock.calls[0][0].tag_id).toBe(NEW_TAG_ID)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功，已新建标签「奶茶」')

    // 被既有测试消费的公开面不得因 M4 改名
    for (const key of [
      'onTagSearch',
      'onTagSelected',
      'onCreateTagFromSearch',
      'tagSearchResults',
      'tagSearching',
      'tagSearchQuery',
      'selectedTagId',
      'selectedTagName',
      'submit',
      'canSubmit',
    ]) {
      expect(wrapper.vm[key]).toBeDefined()
    }
    // 控件本体既有绑定原样在场（浮层改造未吞事件/未换控件）
    expect(recordFormSource).toMatch(/v-model="selectedTagId"/)
    expect(recordFormSource).toMatch(/v-model:search="tagSearchQuery"/)
    expect(recordFormSource).toMatch(/@update:search="onTagSearch"/)
    expect(recordFormSource).toMatch(/@update:model-value="onTagSelected"/)
    expect(recordFormSource).toMatch(/@keydown\.enter="onCreateTagFromSearch"/)
    expect(recordFormSource).toMatch(/:items="tagSearchResults"/)
    // 控件未换成 v-text-field（预案 B 未启用），也无自绘建议层
    expect(recordFormSource).toMatch(/<v-autocomplete/)
    expect(recordFormSource).not.toMatch(/tag-suggest-panel/)
    // 任务 5.4：✕ 与浮层焦点沿用 VMenu 默认（点选即关）——不新增 persistent、不覆写 closeOnContentClick
    expect(recordFormSource).not.toMatch(/persistent|close-on-content-click|closeOnContentClick/)
    await wrapper.unmount()
  })

  // ── 6.7 D9 联合验收链路（M3 + M4 合流的自动化承载；真机链路/软键盘项仍留人工）──────
  it('用例6.7a（D9）: 真实输入 → 锚定建议层出现 → 层内点选 → 点保存：关联既有标签零创建', async () => {
    searchTags.mockResolvedValue(TAGS_MILK.map((t) => ({ ...t })))
    const wrapper = await mountReal()

    await typeIntoTagField(wrapper, '奶')
    const content = contentOf(wrapper)
    expect(content).not.toBeNull()
    const options = Array.from(content.querySelectorAll('.v-list-item'))
    expect(options).toHaveLength(2)

    options[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true })) // 层内点选（非 vm 直调）
    await settle(50)
    expect(wrapper.vm.selectedTagId).toBe(101)
    expect(wrapper.vm.selectedTagName).toBe('奶茶')

    wrapper.vm.amount = '28'
    await nextTick()
    const submitBtn = wrapper.find('button.submit-btn')
    expect(submitBtn.exists()).toBe(true)
    await submitBtn.trigger('click')
    await settle(50)

    expect(createTag).not.toHaveBeenCalled() // 点选路径：零建标签（需求 3.5 旧路径不回退）
    expect(createRecord).toHaveBeenCalledTimes(1)
    expect(createRecord.mock.calls[0][0].tag_id).toBe(101)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功')
  })

  it('用例6.7b（D9）: 真实输入 → 不点选不回车 → 直接点保存：锚定层在位时免回车仍建标签并关联', async () => {
    searchTags.mockResolvedValue([]) // ②兜底亦无同名 → 走 ③创建
    const wrapper = await mountReal()

    await typeIntoTagField(wrapper, '打车')
    expect(wrapper.vm.selectedTagId).toBeNull() // 未点选、未回车
    expect(wrapper.find('.tag-field-anchor').element.contains(contentOf(wrapper))).toBe(true)

    wrapper.vm.amount = '18'
    await nextTick()
    await wrapper.find('button.submit-btn').trigger('click')
    await settle(50)

    expect(createTag).toHaveBeenCalledTimes(1)
    expect(createTag).toHaveBeenCalledWith({ name: '打车', category_id: 1 })
    expect(createRecord.mock.calls[0][0].tag_id).toBe(NEW_TAG_ID)
    expect(mockShowToast).toHaveBeenCalledWith('记账成功，已新建标签「打车」')
    expect(wrapper.vm.submitting).toBe(false)
  })
})
