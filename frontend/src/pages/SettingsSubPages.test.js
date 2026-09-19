import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { cwd } from 'node:process'

// ── Mocks ──────────────────────────────────────────────────────────
// vue-router 只桩掉 composable，保留 createRouter/createWebHashHistory，
// 使同一文件内可导入真实路由表做快照断言（用例5）。
const mockPush = vi.fn()
const mockBack = vi.fn()
// useAppStore 每次调用返回新对象，故 toast spy 提升到模块级供页面与 store 共享断言
const mockShowToast = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn() }),
    useRoute: () => ({ path: '/settings', meta: {} }),
  }
})

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue([]),
  createCategory: vi.fn().mockResolvedValue({}),
  updateCategory: vi.fn().mockResolvedValue({}),
  reorderCategories: vi.fn().mockResolvedValue([]),
  deleteCategory: vi.fn().mockResolvedValue({}),
  restoreDefaultCategories: vi.fn().mockResolvedValue({ message: '已恢复默认分类' }),
}))

vi.mock('@/api/tags', () => ({
  getTags: vi.fn().mockResolvedValue([]),
  // M5：标签二级页分页数据源；默认空分页，具体用例内按需覆盖
  getTagsPaged: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  searchTags: vi.fn().mockResolvedValue([]),
  createTag: vi.fn().mockResolvedValue({}),
  deleteTag: vi.fn().mockResolvedValue({}),
}))

vi.mock('@/api/records', () => ({
  getRecords: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getQuickTemplates: vi.fn().mockResolvedValue([]),
  addQuickTemplate: vi.fn().mockResolvedValue({}),
  deleteQuickTemplate: vi.fn().mockResolvedValue({}),
}))

vi.mock('@/api/export', () => ({
  exportCsv: vi.fn().mockResolvedValue({}),
  exportSql: vi.fn().mockResolvedValue({}),
  previewCsvImport: vi.fn().mockResolvedValue({}),
  importCsv: vi.fn().mockResolvedValue({}),
  previewSqlImport: vi.fn().mockResolvedValue({}),
  importSql: vi.fn().mockResolvedValue({}),
}))

vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({
    showToast: mockShowToast,
    themeMode: 'auto',
    setThemeMode: vi.fn(),
  }),
}))

import {
  getCategories,
  createCategory,
  updateCategory,
  reorderCategories,
  deleteCategory,
  restoreDefaultCategories,
} from '@/api/categories'
import { getTags, getTagsPaged, createTag, deleteTag } from '@/api/tags'
import Draggable from 'vuedraggable'
import {
  getRecords,
  getQuickTemplates,
  addQuickTemplate,
  deleteQuickTemplate,
} from '@/api/records'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import router from '@/router'
import SettingsPage from './SettingsPage.vue'
import SettingsCategoriesPage from './SettingsCategoriesPage.vue'
import CategoryIconPicker from '@/components/common/CategoryIconPicker.vue'
import SettingsTagsPage from './SettingsTagsPage.vue'
import SettingsQuickTemplatesPage from './SettingsQuickTemplatesPage.vue'
import settingsPageSource from './SettingsPage.vue?raw'
import categoriesPageSource from './SettingsCategoriesPage.vue?raw'
import tagsPageSource from './SettingsTagsPage.vue?raw'
import quickTemplatesPageSource from './SettingsQuickTemplatesPage.vue?raw'
import historyPageSource from './HistoryPage.vue?raw'
// M8 入口图标统一：统计页预算卡头红线断言所需（仅追加，不动既有导入）
import statisticsPageSource from './StatisticsPage.vue?raw'

// ── 测试数据 ────────────────────────────────────────────────────────
const CATEGORIES = [
  { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food', sort_order: 0, is_preset: true },
  { id: 2, name: '出行', type: 'expense', icon: 'mdi-bus', sort_order: 1, is_preset: true },
  { id: 3, name: '购物', type: 'expense', icon: 'mdi-cart', sort_order: 2 },
  { id: 9, name: '工资', type: 'income', icon: 'mdi-wallet', sort_order: 0 },
]

const TAGS = [
  { id: 11, name: '日常', category_id: 1 },
  { id: 12, name: '打车', category_id: 2 },
  { id: 13, name: '衣服', category_id: 3 },
  { id: 14, name: '报销', category_id: 9 },
  { id: 15, name: '旅行', category_id: 3 },
]

// ── M5 分页夹具：等价后端 GET /api/tags/paged 的切片语义 ────────────────
const MANY_TAGS = Array.from({ length: 30 }, (_, i) => ({
  id: 101 + i,
  name: `标签${String(i + 1).padStart(2, '0')}`,
  category_id: 1,
}))

function pagedOf(all, page = 1, pageSize = 20) {
  return {
    items: all.slice((page - 1) * pageSize, page * pageSize).map((t) => ({ ...t })),
    total: all.length,
    page,
    page_size: pageSize,
  }
}

// 让 getTagsPaged 按入参真实分页（越界页自然返回空 items、total 不变）
function useSlicedPagedMock(all) {
  getTagsPaged.mockImplementation((params) =>
    Promise.resolve(pagedOf(all, params?.page ?? 1, params?.page_size ?? 20))
  )
}

const TEMPLATES = [
  {
    tag_id: 11,
    tag_name: '日常',
    amount: 25,
    type: 'expense',
    category_name: '餐饮',
    count: 8,
    source: 'auto',
  },
  {
    id: 21,
    tag_id: 12,
    tag_name: '打车',
    amount: 30,
    type: 'expense',
    category_name: '出行',
    count: 0,
    source: 'manual',
  },
]

async function mountPage(component) {
  const wrapper = mount(component, { global: { mocks: { $router: { push: mockPush, back: mockBack } } } })
  await flushPromises()
  return wrapper
}

// ── M3 拖拽排序：含「其他」的可见集合（等价于后端 GET 的排序真值） ──────
const REORDER_CATEGORIES = [
  { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food', sort_order: 1, is_preset: 1 },
  { id: 2, name: '出行', type: 'expense', icon: 'mdi-bus', sort_order: 2, is_preset: 1 },
  { id: 3, name: '购物', type: 'expense', icon: 'mdi-cart', sort_order: 3, is_preset: 0 },
  { id: 8, name: '其他支出', type: 'expense', icon: 'mdi-cash-minus', sort_order: 99, is_preset: 1 },
  { id: 9, name: '工资', type: 'income', icon: 'mdi-wallet', sort_order: 1, is_preset: 1 },
  { id: 10, name: '其他收入', type: 'income', icon: 'mdi-cash-plus', sort_order: 99, is_preset: 1 },
]

const reorderCopy = () => REORDER_CATEGORIES.map((c) => ({ ...c }))

async function mountReorderPage() {
  getCategories.mockResolvedValue(reorderCopy())
  reorderCategories.mockResolvedValue(reorderCopy())
  return mountPage(SettingsCategoriesPage)
}

// vuedraggable 把非声明属性按 kebab → camel 透传给 Sortable，这里同口径归一
function sortableOptionsOf(node) {
  const out = {}
  Object.entries(node.vm.$attrs).forEach(([key, value]) => {
    out[key.replace(/-([a-z])/g, (_, ch) => ch.toUpperCase())] = value
  })
  return out
}

describe('M7 设置页三个管理区块改二级页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    // 每次返回副本：store 的 addCategory/addTag 会 push 进数组，避免污染模块级常量
    getCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
    getTags.mockResolvedValue(TAGS.map((t) => ({ ...t })))
    // M5：标签二级页 chip 源为分页接口首页数据（默认全量落在第 1 页，≤20 条无展开区）
    useSlicedPagedMock(TAGS)
    getRecords.mockResolvedValue({ items: [], total: 0 })
    getQuickTemplates.mockResolvedValue(TEMPLATES.map((t) => ({ ...t })))
    createCategory.mockResolvedValue({ id: 4, name: '新分类', type: 'expense' })
    updateCategory.mockResolvedValue({ id: 1, name: '餐饮', type: 'expense' })
    reorderCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
    deleteCategory.mockResolvedValue({})
    restoreDefaultCategories.mockResolvedValue({ message: '已恢复默认分类' })
    createTag.mockResolvedValue({ id: 16, name: '新标签', category_id: 1 })
    deleteTag.mockResolvedValue({})
    addQuickTemplate.mockResolvedValue({})
    deleteQuickTemplate.mockResolvedValue({})
  })

  // ── 用例1：设置页摘要卡 ──────────────────────────────────────────
  it('用例1: 设置页渲染三张摘要卡，只含数量与箭头，不含列表条目/新增按钮', async () => {
    // M5：不再手动预拉标签——摘要数量应由 onMounted 自身的 fetchTags 提供
    const wrapper = await mountPage(SettingsPage)

    // 三张摘要卡的跳转目标
    const entries = wrapper
      .findAll('v-list-item')
      .filter((node) => node.attributes('to'))
      .map((node) => node.attributes('to'))
    expect(entries).toEqual(['/settings/categories', '/settings/tags', '/settings/quick-templates'])

    const text = wrapper.text()
    expect(text).toContain('分类管理')
    expect(text).toContain('标签管理')
    expect(text).toContain('快速记账')
    // 数量摘要
    expect(text).toContain('支出 3 / 收入 1')
    expect(text).toContain('5 个')
    expect(text).toContain('2 个模板')
    // 摘要卡不展示任何详细条目与新增按钮
    expect(text).not.toContain('餐饮')
    expect(text).not.toContain('日常')
    expect(text).not.toContain('预设')
    expect(text).not.toContain('新增')
    expect(text).not.toContain('恢复默认')
    expect(wrapper.findAll('v-chip')).toHaveLength(0)
    expect(wrapper.findAll('.category-list-item')).toHaveLength(0)
  })

  // 口径反转改写（M5 易错点 10）：旧断言「设置页不请求 getTags」→ 新断言
  // 「mount 后 getTags 恰一次（进入即拉真实总数），此后改 store.tags 不再新增请求」
  it('用例1b: 进入设置页拉一次全量标签，共享 store 变更后摘要即时响应且不再新增请求', async () => {
    const store = useCategoriesStore()
    const wrapper = await mountPage(SettingsPage)

    // 未进过任何标签页也拿到真实数量（后端已解除 20 条上限 → 全量数组 length）
    expect(getTags).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('支出 3 / 收入 1')
    expect(wrapper.text()).toContain('5 个')

    store.categories = [...CATEGORIES, { id: 4, name: '娱乐', type: 'expense' }]
    store.tags = []
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('支出 4 / 收入 1')
    expect(text).toContain('0 个')
    // 数量更新未触发对设置页的重新请求
    expect(getTags).toHaveBeenCalledTimes(1)
  })

  // ── 用例2：分类管理二级页 ────────────────────────────────────────
  it('用例2: 分类二级页返回按钮触发 router.back，渲染支出/收入两组列表', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)

    const text = wrapper.text()
    expect(text).toContain('支出分类')
    expect(text).toContain('收入分类')
    expect(text).toContain('餐饮')
    expect(text).toContain('工资')
    expect(wrapper.findAll('.category-list-item')).toHaveLength(4)
    expect(getCategories).toHaveBeenCalledTimes(1)
  })

  it('用例2b: 拖拽把手替换上下按钮，松手一次批量重排 PUT + 唯一「排序已保存」toast', async () => {
    const wrapper = await mountReorderPage()

    // 本文件挂载不装 Vuetify 插件，v-list-item 的具名 slot（把手所在）不落 DOM，
    // 故把手/占位/上下按钮移除按仓库既定的 ?raw 源码口径断言
    // D8：旧上移/下移按钮与 moveCategory 整体移除（单个 PUT 已不改排序）
    expect(categoriesPageSource).not.toContain('mdi-chevron')
    expect(categoriesPageSource).not.toMatch(/\bmoveCategory\b/)
    expect(categoriesPageSource.match(/mdi-drag-vertical/g)).toHaveLength(2)
    expect(categoriesPageSource.match(/class="drag-handle mr-1"/g)).toHaveLength(2)
    expect(categoriesPageSource.match(/class="drag-handle-placeholder mr-1"/g)).toHaveLength(2)
    expect(categoriesPageSource).toMatch(/v-if="!isOther\(cat\)"/)
    // 样式红线：touch-action: none 只加把手，未污染整行（加整行会杀死列表滚动）
    expect(categoriesPageSource).toMatch(/\.drag-handle \{[^}]*touch-action: none/)
    expect(categoriesPageSource).not.toMatch(/\.category-list-item \{[^}]*touch-action/)
    expect(categoriesPageSource).toMatch(/\.drag-handle-placeholder \{[^}]*width: 20px/)

    // 支出/收入各一个独立 Draggable 实例（天然不可跨组拖）
    const draggables = wrapper.findAllComponents(Draggable)
    expect(draggables).toHaveLength(2)
    const options = sortableOptionsOf(draggables[0])
    expect(options.handle).toBe('.drag-handle')
    expect(options.delay).toBe(150)
    expect(options.delayOnTouchOnly).toBe(true)
    expect(options.touchStartThreshold).toBe(5)
    expect(options.ghostClass).toBe('drag-ghost')
    expect(options.dragClass).toBe('drag-float')
    expect(options.disabled).toBe(false)
    expect(draggables[0].props('itemKey')).toBe('id')

    // REORDER 夹具：支出 4 行 + 收入 2 行；行渲染与 Sortable 命中集一一对应
    // （[data-draggable] 缺失即整列表拖不动，属真实渲染断言）
    expect(wrapper.findAll('.category-list-item')).toHaveLength(6)
    expect(wrapper.findAll('[data-draggable]')).toHaveLength(6)

    // jsdom 不真实驱动 sortable：vm 直改 dragList 后手动调 onDragEnd
    expect(wrapper.vm.expenseDragList.map((c) => c.name)).toEqual([
      '餐饮',
      '出行',
      '购物',
      '其他支出',
    ])
    const list = wrapper.vm.expenseDragList
    wrapper.vm.onDragStart('expense')
    expect(wrapper.vm.preDragSnapshot.expense.map((c) => c.id)).toEqual([1, 2, 3, 8])
    wrapper.vm.expenseDragList = [list[1], list[0], list[2], list[3]]
    wrapper.vm.onDragEnd('expense')
    await flushPromises()

    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ type: 'expense', ids: [2, 1, 3, 8] })
    // 全流程唯一一次 toast：store 成功路径不再附加「更新成功」类提示
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('排序已保存')
  })

  it('用例2b-2:「其他」被拖到中间 → 本地与提交 ids 均归一化回末位；isOther/isOtherLocked 口径', async () => {
    const wrapper = await mountReorderPage()
    const list = wrapper.vm.expenseDragList
    const [food, trip, shopping, other] = list

    wrapper.vm.onDragStart('expense')
    wrapper.vm.expenseDragList = [food, other, trip, shopping]
    wrapper.vm.onDragEnd('expense')
    // 本地镜像后端「末尾占位」归一化（同步生效，避免保存后跳变）
    expect(wrapper.vm.expenseDragList.map((c) => c.name)).toEqual([
      '餐饮',
      '出行',
      '购物',
      '其他支出',
    ])
    await flushPromises()
    expect(reorderCategories).toHaveBeenCalledWith({ type: 'expense', ids: [1, 2, 3, 8] })

    // isOther: name + type 双判（与后端助手对齐），错类型同名不算「其他」
    expect(wrapper.vm.isOther(other)).toBe(true)
    expect(wrapper.vm.isOther({ name: '其他支出', type: 'income' })).toBe(false)
    expect(wrapper.vm.isOther({ name: '其他收入', type: 'income' })).toBe(true)
    expect(wrapper.vm.isOther({ name: '餐饮', type: 'expense' })).toBe(false)

    // isOtherLocked: 非末位「其他」（异常数据）→ 禁用本组拖动
    expect(wrapper.vm.isOtherLocked([other, food, trip])).toBe(true)
    expect(wrapper.vm.isOtherLocked([food, trip, other])).toBe(false)
    expect(wrapper.vm.isOtherLocked([])).toBe(false)
    expect(sortableOptionsOf(wrapper.findAllComponents(Draggable)[1]).disabled).toBe(false)
  })

  it('用例2b-3: 保存失败 → 回滚拖前快照 + 错误 toast，并静默重拉对齐后端真值', async () => {
    const wrapper = await mountReorderPage()
    reorderCategories.mockRejectedValue(new Error('排序列表与当前分类不一致'))
    // 重拉同样失败：证明列表恢复来自快照回滚而非重新请求
    getCategories.mockRejectedValue(new Error('network down'))

    const list = wrapper.vm.expenseDragList
    wrapper.vm.onDragStart('expense')
    // 出行↑ 购物↑ 其他↑ 餐饮↓ →「其他」在中间，归一化后提交 ids = [2,3,1,8]
    wrapper.vm.expenseDragList = [list[1], list[2], list[3], list[0]]
    wrapper.vm.onDragEnd('expense')
    await flushPromises()

    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ type: 'expense', ids: [2, 3, 1, 8] })
    expect(wrapper.vm.expenseDragList.map((c) => c.id)).toEqual([1, 2, 3, 8])
    expect(getCategories).toHaveBeenCalledTimes(2) // 初始加载 + 失败后静默对齐
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('排序保存失败', 'error')
  })

  it('用例2c: 新增/编辑分类共用 Category Dialog，icon 由精选面板回填（无文本输入框），保存分别走 create/update', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    // 弹窗图标字段的唯一入口是精选面板，默认值 mdi-cash（在精选集内）
    wrapper.vm.showCategoryDialog = true
    wrapper.vm.categoryForm.name = '娱乐'
    await nextTick()
    const picker = wrapper.findComponent(CategoryIconPicker)
    expect(picker.exists()).toBe(true)
    expect(picker.props('modelValue')).toBe('mdi-cash')

    // 面板点选回填：categoryForm.icon 仅能由 update:modelValue 改变
    picker.vm.$emit('update:modelValue', 'mdi-gamepad')
    await nextTick()
    expect(wrapper.vm.categoryForm.icon).toBe('mdi-gamepad')

    await wrapper.vm.saveCategory()
    await flushPromises()
    // M2：新增载荷不再携带 sort_order（排序由服务端计算：追加组末、「其他」之前）
    expect(createCategory).toHaveBeenCalledWith({
      name: '娱乐',
      type: 'expense',
      icon: 'mdi-gamepad',
    })
    expect(updateCategory).not.toHaveBeenCalled()

    // 编辑：表单项回填、标题切换为「编辑分类」，面板选中态同步为原图标
    const target = wrapper.vm.expenseCategories[0]
    wrapper.vm.editCategory(target)
    await nextTick()
    expect(wrapper.vm.showCategoryDialog).toBe(true)
    expect({ ...wrapper.vm.editingCategory }).toEqual(CATEGORIES[0])
    expect(wrapper.vm.categoryForm.name).toBe('餐饮')
    expect(wrapper.vm.categoryForm.icon).toBe('mdi-food')
    expect(picker.props('modelValue')).toBe('mdi-food')

    wrapper.vm.categoryForm.name = '餐饮美食'
    await wrapper.vm.saveCategory()
    await flushPromises()
    // M2：编辑载荷不含 type（编辑不改类型）也不含 sort_order（单个 PUT 不改排序）
    expect(updateCategory).toHaveBeenCalledWith(1, {
      name: '餐饮美食',
      icon: 'mdi-food',
    })
    expect(wrapper.vm.editingCategory).toBeNull()

    // 表单状态与模板均不再持有「排序」
    expect(Object.keys(wrapper.vm.categoryForm).sort()).toEqual(['icon', 'name', 'type'])
    expect(categoriesPageSource).not.toContain('label="排序"')

    // 源码断言：任意文本图标名入口已移除，改为接入 CategoryIconPicker
    expect(categoriesPageSource).not.toContain('图标 (mdi-*)')
    expect(categoriesPageSource).not.toContain('placeholder="mdi-food"')
    expect(categoriesPageSource).toContain('<CategoryIconPicker')
  })

  it('用例2c-2: 编辑预设分类返回 CoW 副本（id 变化）时 store 不原地替换，避免双份', async () => {
    const store = useCategoriesStore()
    await store.fetchCategories()
    expect(store.categories.map((c) => c.id)).toContain(1)

    // 预设「餐饮」被服务端 CoW，响应为新建的用户副本（id 101 ≠ 1）
    updateCategory.mockResolvedValueOnce({
      id: 101,
      name: '餐饮美食',
      type: 'expense',
      icon: 'mdi-food',
      sort_order: 0,
    })
    const updated = await store.editCategory(1, { name: '餐饮美食' })
    expect(updated.id).toBe(101)

    // 旧 id 的原地替换被跳过：列表长度不变、不出现「餐饮/餐饮美食」双份
    expect(store.categories).toHaveLength(CATEGORIES.length)
    expect(store.categories.find((c) => c.id === 1).name).toBe('餐饮')
    expect(store.categories.some((c) => c.id === 101)).toBe(false)

    // id 未变（用户自有分类）时仍走原地替换
    updateCategory.mockResolvedValueOnce({ id: 3, name: '购物消费', type: 'expense' })
    await store.editCategory(3, { name: '购物消费' })
    expect(store.categories.find((c) => c.id === 3).name).toBe('购物消费')
    expect(store.categories).toHaveLength(CATEGORIES.length)
  })

  it('用例2d: 删除分类先查关联账单数并弹确认框，确认后走 store.removeCategory', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    getRecords.mockResolvedValue({ items: [], total: 7 })
    await wrapper.vm.confirmDeleteCategory(CATEGORIES[0])
    expect(getRecords).toHaveBeenCalledWith({ category_id: 1, page_size: 1 })
    expect(wrapper.vm.showDeleteCategoryDialog).toBe(true)
    expect(wrapper.vm.deleteCategoryMessage).toContain('下有 7 条账单记录')

    await wrapper.vm.handleDeleteCategory()
    await flushPromises()
    expect(deleteCategory).toHaveBeenCalledWith(1)
    expect(wrapper.vm.showDeleteCategoryDialog).toBe(false)

    // 无关联账单时的文案分支
    getRecords.mockResolvedValue({ items: [], total: 0 })
    await wrapper.vm.confirmDeleteCategory(CATEGORIES[2])
    expect(wrapper.vm.deleteCategoryMessage).toBe('确定要删除「购物」吗？')
  })

  it('用例2e: 恢复默认走 store.restoreDefaults 并重新拉取分类', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    wrapper.vm.showRestoreConfirm = true
    await wrapper.vm.handleRestoreDefaults()
    await flushPromises()

    expect(restoreDefaultCategories).toHaveBeenCalledTimes(1)
    expect(getCategories).toHaveBeenCalledTimes(2)
    expect(wrapper.vm.showRestoreConfirm).toBe(false)
    expect(wrapper.vm.restoring).toBe(false)
    expect(wrapper.text()).toContain('恢复默认分类')
  })

  // ── 用例3：标签管理二级页 ────────────────────────────────────────
  it('用例3: 标签二级页空态文案，chip 云渲染全部标签且返回按钮可用', async () => {
    getTags.mockResolvedValue([])
    getTagsPaged.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    const wrapper = await mountPage(SettingsTagsPage)
    expect(wrapper.text()).toContain('暂无标签')

    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)

    // M5：chip 云渲染源为本地分页列表（首页数据来自 /tags/paged），断言条目与改版前一致
    getTagsPaged.mockResolvedValue(pagedOf(TAGS))
    await wrapper.vm.resetPaging()
    await nextTick()
    const text = wrapper.text()
    expect(text).not.toContain('暂无标签')
    expect(text).toContain('日常')
    expect(text).toContain('旅行')
    expect(wrapper.findAll('v-chip')).toHaveLength(5)
    // 5 ≤ PAGE_SIZE → 分页展开区不渲染（用例 M5-2 详断言）
    expect(text).not.toContain('展开更多')
  })

  it('用例3b: 新增标签走 store.addTag（名称去空格），删除标签走 store.removeTag', async () => {
    const wrapper = await mountPage(SettingsTagsPage)

    wrapper.vm.showTagDialog = true
    wrapper.vm.tagForm.name = '  日常  '
    wrapper.vm.tagForm.category_id = 1
    await wrapper.vm.saveTag()
    await flushPromises()

    expect(createTag).toHaveBeenCalledWith({ name: '日常', category_id: 1 })
    expect(wrapper.vm.showTagDialog).toBe(false)
    expect(wrapper.vm.tagForm.name).toBe('')
    expect(wrapper.vm.tagForm.category_id).toBeNull()

    wrapper.vm.confirmDeleteTag(TAGS[1])
    expect(wrapper.vm.showDeleteTagDialog).toBe(true)
    await wrapper.vm.handleDeleteTag()
    await flushPromises()
    expect(deleteTag).toHaveBeenCalledWith(12)
    expect(wrapper.vm.showDeleteTagDialog).toBe(false)
  })

  it('用例3c: 标签弹窗「所属分类」下拉来自共享 categories store', async () => {
    const wrapper = await mountPage(SettingsTagsPage)
    expect(getCategories).toHaveBeenCalledTimes(1)
    expect(useCategoriesStore().categories).toHaveLength(4)
    expect(wrapper.vm.categories.map((c) => c.id)).toEqual([1, 2, 3, 9])
  })

  // ── 用例4：快速记账二级页 ────────────────────────────────────────
  it('用例4: 模板二级页渲染列表与来源展示，删除按钮调用 deleteQuickTemplate', async () => {
    const wrapper = await mountPage(SettingsQuickTemplatesPage)

    const text = wrapper.text()
    expect(text).toContain('日常 · ¥25')
    expect(text).toContain('餐饮 · 使用 8 次')
    expect(text).toContain('打车 · ¥30')
    // 自动模板无 id：不请求删除接口，只刷新列表
    await wrapper.vm.removeQuickTemplate(TEMPLATES[0])
    await flushPromises()
    expect(deleteQuickTemplate).not.toHaveBeenCalled()
    expect(getQuickTemplates).toHaveBeenCalledTimes(2)

    // 手动模板：走 deleteQuickTemplate(id)
    await wrapper.vm.removeQuickTemplate(TEMPLATES[1])
    await flushPromises()
    expect(deleteQuickTemplate).toHaveBeenCalledWith(21)
    expect(getQuickTemplates).toHaveBeenCalledTimes(3)

    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)
  })

  it('用例4b: 模板列表为空时显示空态；新增模板走 addQuickTemplate', async () => {
    getQuickTemplates.mockResolvedValue([])
    const wrapper = await mountPage(SettingsQuickTemplatesPage)
    expect(wrapper.text()).toContain('暂无快速记账模板')

    wrapper.vm.showQuickTemplateDialog = true
    wrapper.vm.quickTemplateForm = { tag_id: 11, amount: 25 }
    await wrapper.vm.saveQuickTemplate()
    await flushPromises()

    expect(addQuickTemplate).toHaveBeenCalledWith({ tag_id: 11, amount: 25 })
    expect(wrapper.vm.showQuickTemplateDialog).toBe(false)
    expect(wrapper.vm.quickTemplateForm).toEqual({ tag_id: null, amount: 0 })
    // 弹窗「选择标签」下拉数据同源
    expect(getTags).toHaveBeenCalledTimes(1)
  })

  // ── 用例5：路由表 ────────────────────────────────────────────────
  it('用例5: 三条二级路由存在、懒加载、meta.title 正确且受登录守卫保护', async () => {
    const expected = [
      ['/settings/categories', 'SettingsCategories', '分类管理'],
      ['/settings/tags', 'SettingsTags', '标签管理'],
      ['/settings/quick-templates', 'SettingsQuickTemplates', '快速记账'],
    ]
    const byPath = {}
    router.getRoutes().forEach((r) => {
      byPath[r.path] = r
    })

    for (const [path, name, title] of expected) {
      const route = byPath[path]
      expect(route, `缺少路由 ${path}`).toBeTruthy()
      expect(route.name).toBe(name)
      expect(route.meta.title).toBe(title)
      // 懒加载：组件为返回 import() 的函数
      expect(typeof route.components.default).toBe('function')
      const mod = await route.components.default()
      expect(mod.default).toBeTruthy()
      // 非 public 路由由现有 beforeEach 统一校验 token
      expect(route.meta.public).toBeFalsy()
    }
  })

  // ── 用例6：搬移完整性 + 设置页零残留（回归红线） ──────────────────
  it('用例6: 三个区块的函数与状态完整搬移到对应二级页', () => {
    const movedToCategories = [
      'expenseCategories',
      'incomeCategories',
      'showCategoryDialog',
      'categoryForm',
      'typeOptions',
      'editingCategory',
      'savingCategory',
      // 'moveCategory' 随 M3 决策 D8 整体移除（拖拽把手口径见用例 2b）
      'editCategory',
      'saveCategory',
      'resetCategoryForm',
      'confirmDeleteCategory',
      'handleDeleteCategory',
      'showDeleteCategoryDialog',
      'deletingCategory',
      'deleteCategoryMessage',
      'handleRestoreDefaults',
      'showRestoreConfirm',
      'restoring',
      'ConfirmDialog',
    ]
    const movedToTags = [
      'tagForm',
      'savingTag',
      'showTagDialog',
      'confirmDeleteTag',
      'handleDeleteTag',
      'showDeleteTagDialog',
      'deletingTag',
      '暂无标签',
      'ConfirmDialog',
    ]
    const movedToTemplates = [
      'quickTemplates',
      'showQuickTemplateDialog',
      'quickTemplateForm',
      'savingQuickTemplate',
      'loadQuickTemplates',
      'removeQuickTemplate',
      'saveQuickTemplate',
      'addQuickTemplate',
      'deleteQuickTemplate',
      '暂无快速记账模板',
    ]

    movedToCategories.forEach((id) => expect(categoriesPageSource).toContain(id))
    movedToTags.forEach((id) => expect(tagsPageSource).toContain(id))
    movedToTemplates.forEach((id) => expect(quickTemplatesPageSource).toContain(id))
  })

  it('用例6b: SettingsPage 无三个区块的残留标识符', () => {
    const residues = [
      'showCategoryDialog',
      'categoryForm',
      'typeOptions',
      'editingCategory',
      'savingCategory',
      'moveCategory',
      'editCategory',
      'saveCategory',
      'resetCategoryForm',
      'confirmDeleteCategory',
      'handleDeleteCategory',
      'showDeleteCategoryDialog',
      'deletingCategory',
      'deleteCategoryMessage',
      'handleRestoreDefaults',
      'showRestoreConfirm',
      'restoring',
      'tagForm',
      'savingTag',
      'showTagDialog',
      'confirmDeleteTag',
      'handleDeleteTag',
      'showDeleteTagDialog',
      'deletingTag',
      'loadTags',
      'quickTemplateForm',
      'showQuickTemplateDialog',
      'savingQuickTemplate',
      'removeQuickTemplate',
      'saveQuickTemplate',
      'addQuickTemplate',
      'deleteQuickTemplate',
      'ConfirmDialog',
      'category-list-item',
      'preset-chip',
      'tag-delete-icon',
    ]
    residues.forEach((id) => expect(settingsPageSource).not.toContain(id))

    // 三个区块的关键标识符逐项零命中（词边界）
    residues.forEach((id) => expect(settingsPageSource).not.toMatch(new RegExp(`\\b${id}\\b`)))
  })
})

// ── M4 设置二级页面统一卡片图层容器 ─────────────────────────────────
const PAGE_CARD_OPEN = '<div class="page-card">'

// vitest 默认不处理 CSS（?raw 会拿到空串），故沿用 categoryIcons.test.js 手法直读样式表原文
function readGlobalStyles() {
  const relative = join('src', 'styles', 'global.scss')
  let dir = cwd()
  for (let i = 0; i < 5; i++) {
    const candidate = join(dir, relative)
    if (existsSync(candidate)) return readFileSync(candidate, 'utf8')
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  throw new Error(`未找到 global.scss（cwd=${cwd()}）`)
}

// 按 div 深度配对截出卡壳区间，返回 { card, outside }
// P2 收敛口径（设计 §4.3-1 字面写法不可直照）：M4 清除对象是「页面级透视」，
// 故断言取结构性写法——截出卡壳之外片段再断言，而非整串 not.toContain
function splitByPageCard(source) {
  const start = source.indexOf(PAGE_CARD_OPEN)
  if (start < 0) throw new Error('未找到 .page-card 容器')
  const divTags = /<\/?div\b[^>]*>/g
  divTags.lastIndex = start
  let depth = 0
  let match
  while ((match = divTags.exec(source)) !== null) {
    if (match[0].startsWith('</')) depth -= 1
    else if (!match[0].endsWith('/>')) depth += 1
    if (depth === 0) {
      return {
        card: source.slice(start, divTags.lastIndex),
        outside: source.slice(0, start) + source.slice(divTags.lastIndex),
      }
    }
  }
  throw new Error('.page-card 容器未闭合')
}

describe('M4 设置二级页面统一卡片图层容器', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(reorderCopy())
    reorderCategories.mockResolvedValue(reorderCopy())
  })

  // 任务 §4.1（含 §1.1/§1.2/§1.3、§2.1、§3.1/§3.2）
  it('用例M4-1: 四个二级页主体内容入 page-card，全局容器规范齐备且不改挂 settings-card', () => {
    const styles = readGlobalStyles()
    expect(styles).toMatch(/\.page-card \{[^}]*background: rgb\(var\(--v-theme-surface\)\)/)
    expect(styles).toMatch(/\.page-card \{[^}]*border-radius: 16px/)
    expect(styles).toMatch(/\.page-card \{[^}]*box-shadow: var\(--shadow-level-1\)/)
    expect(styles).toMatch(/\.page-card \{[^}]*padding: 16px/)
    expect(styles).toMatch(/\.page-card \{[^}]*margin-bottom: 12px/)
    // §1.2 深色不加分支（--v-theme-surface 运行时随主题切换）
    expect(styles).not.toMatch(/\.v-theme--dark[^{]*\.page-card/)
    // §1.3 钩子类 .settings-card 不另行赋样式，样式统一由 .page-card 承载
    expect(styles).not.toMatch(/\.settings-card\s*\{/)

    const pages = [
      ['分类页', categoriesPageSource, ['支出分类', '收入分类', '暂无分类']],
      ['标签页', tagsPageSource, ['暂无标签']],
      ['快速记账页', quickTemplatesPageSource, ['暂无快速记账模板']],
    ]
    pages.forEach(([name, source, markers]) => {
      expect(source, `${name} 未接 .page-card`).toContain(PAGE_CARD_OPEN)
      // 每页恰一个卡壳（容器复用不重复定义），空态与主体内容均在卡内
      expect(source.match(/class="page-card"/g), `${name} 卡壳应恰一处}`).toHaveLength(1)
      const { card, outside } = splitByPageCard(source)
      markers.forEach((m) => expect(card, `${name}「${m}」未入卡`).toContain(m))
      // §2.1 页头（返回 + 操作按钮）留在卡外
      expect(outside).toContain('mdi-arrow-left')
      expect(outside).toContain('$router.back()')
    })

    // 分类页两块同卡分区（§2.2：块间距 mb-4）；快速记账页模板列表入卡（§2.4）
    expect(splitByPageCard(categoriesPageSource).card).toContain('class="mb-4"')
    // 标签页 chip 云入卡（§2.3，M5 分页控件同卡位由 M5 承接）
    expect(splitByPageCard(tagsPageSource).card).toContain('flex-wrap')

    // §3.1 数据回溯页空态包卡；§3.2 既有列表 v-card 保持不重构
    expect(historyPageSource).toMatch(/class="page-card text-center"[\s\S]*?暂无操作记录/)
    expect(historyPageSource).toMatch(/<v-card v-else rounded="xl" class="mb-4">/)
  })

  // 任务 §4.2（P2 收敛后的「页面级无透视」结构性口径）
  it('用例M4-2: 卡壳之外无列表透明直贴页面背景；卡内 Draggable 的 bg-transparent 合法保留', () => {
    const categories = splitByPageCard(categoriesPageSource)
    expect(categories.outside).not.toContain('bg-transparent')
    // M3 合入后两个 Draggable 的 v-list 位于卡壳内部，不再产生透视 → 不入清除范围（易错点 6）
    expect(categories.card.match(/bg-transparent/g)).toHaveLength(2)

    const templates = splitByPageCard(quickTemplatesPageSource)
    expect(templates.outside).not.toContain('bg-transparent')
    // 模板页原页面级透视列表（§2.5 点名）彻底去除透明写法
    expect(templates.card).not.toContain('bg-transparent')

    const tags = splitByPageCard(tagsPageSource)
    expect(tags.outside).not.toContain('bg-transparent')

    // 数据回溯页唯一 bg-transparent 在既有 v-card 内（展开明细列表），页面级无裸列表
    expect(historyPageSource).toMatch(/<v-card v-else rounded="xl"[\s\S]*?bg-transparent/)
  })

  // 任务 §4.3（渲染快照）+ M3 交接的卡壳 × 拖拽回归
  it('用例M4-3: 分类页支出/收入标题渲染在 .page-card 内，卡壳不影响拖拽与批量重排', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)
    const cards = wrapper.findAll('.page-card')
    expect(cards).toHaveLength(1)
    const card = cards[0]

    const text = card.text()
    expect(text).toContain('支出分类')
    expect(text).toContain('收入分类')
    expect(text).toContain('餐饮')
    expect(text).toContain('其他收入')
    // 页头操作按钮留卡外
    expect(text).not.toContain('恢复默认')
    expect(wrapper.text()).toContain('恢复默认')
    // 卡内两块分区，支出块 mb-4 生效一处
    expect(card.findAll('.mb-4')).toHaveLength(1)

    // 卡壳未吃掉 M3 拖拽结构：两组各一个 Draggable 实例、行渲染源一一对应
    expect(card.findAllComponents(Draggable)).toHaveLength(2)
    expect(card.findAll('.category-list-item')).toHaveLength(6)
    expect(card.findAll('[data-draggable]')).toHaveLength(6)

    // 拖拽改序仍走一次批量重排（视觉结构未回归破坏）
    const list = wrapper.vm.expenseDragList
    wrapper.vm.onDragStart('expense')
    wrapper.vm.expenseDragList = [list[1], list[0], list[2], list[3]]
    wrapper.vm.onDragEnd('expense')
    await flushPromises()
    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ type: 'expense', ids: [2, 1, 3, 8] })
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('排序已保存')
  })
})

// ── M5 标签解除 20 条上限 + 分页展开 ─────────────────────────────────
describe('M5 标签分页展开', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
    getQuickTemplates.mockResolvedValue(TEMPLATES.map((t) => ({ ...t })))
    createTag.mockResolvedValue({ id: 131, name: '新标签', category_id: 1 })
    deleteTag.mockResolvedValue({})
  })

  const expandBtn = (wrapper) =>
    wrapper.findAll('v-btn').find((node) => node.text() === '展开更多')

  // 任务 §5.1-§5.5 + 用例 6.2.1
  it('用例M5-1: 30 条标签首屏渲染 20 个 chip + 展开更多 + 计数文案，点击后追加至 30 并隐藏按钮', async () => {
    getTags.mockResolvedValue(MANY_TAGS.map((t) => ({ ...t })))
    useSlicedPagedMock(MANY_TAGS)
    const wrapper = await mountPage(SettingsTagsPage)

    expect(getTagsPaged).toHaveBeenCalledTimes(1)
    expect(getTagsPaged).toHaveBeenCalledWith({ page: 1, page_size: 20 })
    expect(wrapper.findAll('v-chip')).toHaveLength(20)
    expect(wrapper.text()).toContain('已显示 20 / 共 30 个')
    // 首屏只到第 20 条，第 21 条靠「展开更多」触达
    expect(wrapper.text()).toContain('标签20')
    expect(wrapper.text()).not.toContain('标签21')
    // M4 交接：分页控件与 chip 云同处唯一 .page-card 内
    const card = wrapper.findAll('.page-card')[0]
    expect(card.text()).toContain('已显示 20 / 共 30 个')
    expect(expandBtn(card)).toBeTruthy()

    await expandBtn(wrapper).trigger('click')
    await flushPromises()

    expect(getTagsPaged).toHaveBeenCalledTimes(2)
    expect(getTagsPaged).toHaveBeenLastCalledWith({ page: 2, page_size: 20 })
    expect(wrapper.findAll('v-chip')).toHaveLength(30)
    expect(wrapper.text()).toContain('标签21')
    expect(wrapper.text()).toContain('标签30')
    expect(wrapper.text()).toContain('已显示 30 / 共 30 个')
    expect(expandBtn(wrapper)).toBeUndefined()
    expect(wrapper.vm.loadingMore).toBe(false)
    expect(wrapper.vm.page).toBe(2)
  })

  // 任务 §5.7 边界一 + 用例 6.2.2
  it('用例M5-2: 总数 ≤ PAGE_SIZE（恰 20 条与 5 条）时按钮与计数文案均不渲染', async () => {
    const exactly20 = MANY_TAGS.slice(0, 20).map((t) => ({ ...t }))
    getTags.mockResolvedValue(exactly20.map((t) => ({ ...t })))
    useSlicedPagedMock(exactly20)
    const wrapper = await mountPage(SettingsTagsPage)

    expect(wrapper.findAll('v-chip')).toHaveLength(20)
    const text = wrapper.text()
    expect(text).not.toContain('展开更多')
    expect(text).not.toContain('已显示')
    // 卡壳内无任何分页控件（页头「新增」按钮在卡外，不受影响）
    const card = wrapper.findAll('.page-card')[0]
    expect(card.findAll('v-btn')).toHaveLength(0)
    expect(wrapper.text()).toContain('新增')

    // 少量标签同样零冗余渲染
    getTags.mockResolvedValue(TAGS.map((t) => ({ ...t })))
    useSlicedPagedMock(TAGS)
    const small = await mountPage(SettingsTagsPage)
    expect(small.findAll('v-chip')).toHaveLength(5)
    expect(small.text()).not.toContain('展开更多')
    expect(small.text()).not.toContain('已显示')
  })

  // 任务 §5.6 + 用例 6.2.3
  it('用例M5-3: 新增/删除标签后保留 store 流程并 fetchTags + resetPaging 回到第 1 页', async () => {
    getTags.mockResolvedValue(MANY_TAGS.map((t) => ({ ...t })))
    useSlicedPagedMock(MANY_TAGS)
    const wrapper = await mountPage(SettingsTagsPage)

    // 先展开到第 2 页，才能证明「新增后回到第 1 页」
    await expandBtn(wrapper).trigger('click')
    await flushPromises()
    expect(wrapper.findAll('v-chip')).toHaveLength(30)

    getTags.mockClear()
    getTagsPaged.mockClear()
    wrapper.vm.showTagDialog = true
    wrapper.vm.tagForm.name = '新标签'
    wrapper.vm.tagForm.category_id = 1
    await wrapper.vm.saveTag()
    await flushPromises()

    expect(createTag).toHaveBeenCalledWith({ name: '新标签', category_id: 1 })
    expect(getTags).toHaveBeenCalledTimes(1)
    expect(getTagsPaged).toHaveBeenCalledTimes(1)
    expect(getTagsPaged).toHaveBeenCalledWith({ page: 1, page_size: 20 })
    expect(wrapper.findAll('v-chip')).toHaveLength(20)
    expect(wrapper.vm.page).toBe(1)

    getTags.mockClear()
    getTagsPaged.mockClear()
    wrapper.vm.confirmDeleteTag(wrapper.vm.displayedTags[0])
    await wrapper.vm.handleDeleteTag()
    await flushPromises()
    expect(deleteTag).toHaveBeenCalledTimes(1)
    expect(getTags).toHaveBeenCalledTimes(1)
    expect(getTagsPaged).toHaveBeenCalledTimes(1)
    expect(getTagsPaged).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  // 任务 §5.7 边界二（设计 §5.4 page 越界）
  it('用例M5-4: 增量拿到越界空页 → 不追加、隐藏按钮、total 文案不失真', async () => {
    getTags.mockResolvedValue(MANY_TAGS.map((t) => ({ ...t })))
    getTagsPaged.mockResolvedValue(pagedOf(MANY_TAGS))
    const wrapper = await mountPage(SettingsTagsPage)
    expect(wrapper.findAll('v-chip')).toHaveLength(20)

    getTagsPaged.mockResolvedValue({ items: [], total: 30, page: 2, page_size: 20 })
    await expandBtn(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.findAll('v-chip')).toHaveLength(20)
    expect(wrapper.vm.hasMore).toBe(false)
    expect(expandBtn(wrapper)).toBeUndefined()
    expect(wrapper.text()).toContain('已显示 20 / 共 30 个')
    expect(wrapper.vm.loadingMore).toBe(false)
    expect(wrapper.vm.page).toBe(1)
  })

  // 任务 §5.7 边界三（设计 §5.4 请求失败）
  it('用例M5-5: 「展开更多」请求失败 → 已显示列表不变、loadingMore 复位、按钮可重试', async () => {
    getTags.mockResolvedValue(MANY_TAGS.map((t) => ({ ...t })))
    useSlicedPagedMock(MANY_TAGS)
    const wrapper = await mountPage(SettingsTagsPage)

    getTagsPaged.mockRejectedValueOnce(new Error('网络异常'))
    await expandBtn(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.findAll('v-chip')).toHaveLength(20)
    expect(wrapper.vm.loadingMore).toBe(false)
    expect(wrapper.vm.page).toBe(1)
    expect(wrapper.text()).toContain('已显示 20 / 共 30 个')

    const retry = expandBtn(wrapper)
    expect(retry).toBeTruthy()
    await retry.trigger('click')
    await flushPromises()
    expect(wrapper.findAll('v-chip')).toHaveLength(30)
  })

  // 用例 6.2.5 回归：快速记账弹窗标签下拉触达全量（前端零改动）
  it('用例M5-6: 快速记账「选择标签」数据源为 store 全量，>20 条不截断', async () => {
    getTags.mockResolvedValue(MANY_TAGS.map((t) => ({ ...t })))
    const wrapper = await mountPage(SettingsQuickTemplatesPage)

    expect(getTags).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.tags).toHaveLength(30)
    expect(useCategoriesStore().tags).toHaveLength(30)
    // 弹窗下拉与 store 同源：解除后端上限即全量可选
    expect(quickTemplatesPageSource).toMatch(/:items="tags"[\s\S]*?label="选择标签 \*"/)
  })
})

// ── M8 设置页/统计页入口图标颜色与位置统一 ────────────────────────────
// 任务 §5.1 红线收敛口径（易错点 9 / 全局 §7.3）：**不整文件扫 `rgba(`**——
// StatisticsPage 的图表网格线/趋势填充/scoped 样式合法使用 rgba，属 M7 与红线外区域；
// 故只扫「入口头像内联底色」与「v-icon 静态 Material 色名」两类可寻址模式。
// `[^>]*` 禁止跨标签命中，`s` 允许单标签内属性换行。
const AVATAR_INLINE_RGBA = /<v-avatar[^>]*color="rgba\(/s
const STATIC_ICON_COLOR = /<v-icon[^>]*color="(teal|blue|orange|warning|info|purple)"/s
// §2.1/§2.2 统一模板规范：v-avatar size=36 + .entry-avatar + mr-2，内层 v-icon primary/20
const ENTRY_AVATAR_TPL =
  /<v-avatar size="36" class="entry-avatar mr-2">\s*<v-icon color="primary" size="20">/g

// 本文件挂载不装 Vuetify 插件，未知元素的**具名槽不落 DOM**（用例 2b 已确立同一事实），
// 入口头像恰在 v-list-item 的 prepend 槽内 → 桩一个「具名槽也渲染」的宿主组件，
// 使 §5.3 的 .entry-avatar 成为真实的渲染计数断言（fragment 根，无需 runtime template 编译）
const EntrySlotHost = {
  name: 'v-list-item',
  // fragment 根无法自动继承透传属性 → 显式关闭并声明事件，避免本用例产生 dev 告警噪音
  inheritAttrs: false,
  emits: ['click'],
  setup(props, { slots }) {
    return () => [
      ...(slots.prepend ? slots.prepend() : []),
      ...(slots.default ? slots.default() : []),
      ...(slots.append ? slots.append() : []),
    ]
  },
}

// 截出设置页「数据回溯」卡区间：§5.4 定点断言，避免误伤外观/导入导出/账号三张 pa-4 卡头
function sliceHistoryCard(source) {
  const start = source.indexOf('<!-- Data History Entry -->')
  const end = source.indexOf('<!-- Hidden file inputs -->')
  if (start < 0 || end < 0 || end < start) throw new Error('未定位到数据回溯卡区间')
  return source.slice(start, end)
}

describe('M8 设置页/统计页入口图标统一', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
    getTags.mockResolvedValue(TAGS.map((t) => ({ ...t })))
    getQuickTemplates.mockResolvedValue(TEMPLATES.map((t) => ({ ...t })))
  })

  // 任务 §1.1 / §1.2 / §1.3（全局工具类）+ §6.3
  it('用例M8-1: 全局 .entry-avatar 承载主题 primary 10% 透明底，明暗自动跟随', () => {
    const styles = readGlobalStyles()
    // §1.1/§1.3：半透明主题底一律走 CSS 类（Vuetify color props 不支持 alpha 后缀）
    expect(styles).toMatch(
      /\.entry-avatar \{[^}]*background: rgba\(var\(--v-theme-primary\), 0\.1\)/
    )
    // §1.2：基准 = 外观入口原 rgba(139,126,116,.1)（light primary #8B7E74 的 10%），
    // 故新类不得回退成写死的静态色字面量
    expect(styles).not.toMatch(/\.entry-avatar[^{]*\{[^}]*(#8B7E74|139, *126, *116)/)
    // 深色模式无需分支（--v-theme-primary 运行时随主题切换，与 M4 .page-card 同口径）
    expect(styles).not.toMatch(/\.v-theme--dark[^{]*\.entry-avatar/)
    // M4 段落零污染
    expect(styles).toMatch(/\.page-card \{[^}]*padding: 16px/)
  })

  // 任务 §5.1 + §5.2 + §2.1~§2.3 + §4.1
  it('用例M8-2: 两页零内联 rgba 头像底与静态 Material 图标色，11+1 处同规格', () => {
    for (const src of [settingsPageSource, statisticsPageSource]) {
      expect(src).not.toMatch(AVATAR_INLINE_RGBA)
      expect(src).not.toMatch(STATIC_ICON_COLOR)
    }
    // §5.2 SettingsPage 严口径：整文件零 rgba（原 7 处 v-avatar 内联底色已全部收敛到类）
    expect(settingsPageSource).not.toContain('rgba(')
    // §5.1 正向断言：入口头像类已落地
    expect(settingsPageSource).toContain('entry-avatar')
    expect(statisticsPageSource).toContain('entry-avatar')
    // §2.3：外观/分类/标签/快速记账/导入导出/数据回溯/账号 7 卡头
    //      + §3.1 导入导出 4 子条目 = 11 处完全同规格（36 圆底 + primary/20 图标）
    expect(settingsPageSource.match(ENTRY_AVATAR_TPL)).toHaveLength(11)
    // §4.1：统计页仅预算卡头一处（M8 范围收敛）
    expect(statisticsPageSource.match(ENTRY_AVATAR_TPL)).toHaveLength(1)
    // §3.1：裸 v-icon（无圆底）写法已消除
    expect(settingsPageSource).not.toMatch(/<v-icon size="20" class="mr-3">/)
  })

  // 任务 §4.2 红线（易错点 9）：数据可视化语义色不入清理范围
  it('用例M8-3: 统计页图表/预算行语义色零误伤，红线正则可寻址收敛', () => {
    expect(statisticsPageSource).toContain('const chartColors =')
    expect(statisticsPageSource).toContain('const BUDGET_COLORS =')
    expect(statisticsPageSource).toContain('const balanceColor = computed(')
    // 预算行头像仍是动态语义色（未被误改成 primary 圆底）
    expect(statisticsPageSource).toMatch(
      /<v-avatar size="32" :color="getBudgetColor\(index\) \+ '20'"/
    )
    expect(statisticsPageSource).toMatch(
      /<v-icon size="small" :color="getBudgetColor\(index\)">/
    )
    // 收敛性自证：图表配置里的合法 rgba 确实存在，却不被两类可寻址红线命中
    // （反证「不得整文件扫 rgba(」的必要性）
    expect(statisticsPageSource).toContain("grid: { color: 'rgba(0,0,0,0.04)' }")
    expect(statisticsPageSource).not.toMatch(AVATAR_INLINE_RGBA)
    expect(statisticsPageSource).not.toMatch(STATIC_ICON_COLOR)
    // M7 图表卡与动画零污染（本模块未触碰）
    expect(statisticsPageSource).toContain('chart-card')
  })

  // 任务 §5.3（渲染）+ 需求 5 条（文案/顺序/功能不变）
  it('用例M8-4: 挂载后 .entry-avatar 计数 ≥ 11 且其内图标均为 primary 色', async () => {
    const wrapper = mount(SettingsPage, {
      global: {
        mocks: { $router: { push: mockPush, back: mockBack } },
        components: { 'v-list-item': EntrySlotHost },
      },
    })
    await flushPromises()

    const avatars = wrapper.findAll('.entry-avatar')
    expect(avatars.length).toBeGreaterThanOrEqual(11)
    avatars.forEach((node) => {
      // §2.1 容器与左偏移：36 圆底 + mr-2（卡头与子条目同规格）
      expect(node.attributes('size')).toBe('36')
      expect(node.attributes('class')).toBe('entry-avatar mr-2')
      // 图标一律 primary / size 20
      const icon = node.find('v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.attributes('color')).toBe('primary')
      expect(icon.attributes('size')).toBe('20')
    })
    // 11 个入口图标齐全且无游离头像（顺序即模板顺序，需求 5 条不改文案与顺序）
    expect(avatars.map((node) => node.find('v-icon').text())).toEqual([
      'mdi-brightness-6',
      'mdi-shape',
      'mdi-tag-multiple',
      'mdi-lightning-bolt',
      'mdi-swap-vertical',
      'mdi-file-delimited-outline',
      'mdi-file-import-outline',
      'mdi-database-export-outline',
      'mdi-database-import-outline',
      'mdi-history',
      'mdi-account',
    ])
    // 文案与摘要功能未受影响
    const text = wrapper.text()
    ;['外观设置', '分类管理', '标签管理', '快速记账', '导入导出', '数据回溯', '账号'].forEach(
      (title) => expect(text).toContain(title)
    )
    ;['导出 CSV', '导入 CSV', '导出 SQL', '导入 SQL'].forEach((title) =>
      expect(text).toContain(title)
    )
    expect(text).toContain('支出 3 / 收入 1')
    expect(text).toContain('5 个')
    expect(text).toContain('2 个模板')
  })

  // 任务 §3.2 / §3.3 / §3.4 / §5.4（结构性修复；§3.5 骨架不归一 = 两类并存）
  it('用例M8-5: 数据回溯卡去 pa-4 叠加、左偏移两类基线与字阶统一', () => {
    const history = sliceHistoryCard(settingsPageSource)
    // §5.4：不再出现 pa-4 卡壳与 v-list 的双层 padding 叠加写法
    expect(history).not.toContain('class="pa-4 mb-3 settings-card"')
    // §3.2：去 pa-4 后与摘要入口同构；v-list 的 bg-transparent pa-0 保留（深色白底已消除）
    expect(history).toContain('<v-card class="mb-3 settings-card" rounded="xl">')
    expect(history).toMatch(/<v-list class="bg-transparent pa-0">/)
    expect(history).toMatch(/<v-list-item-title class="text-body-1 font-weight-medium">数据回溯/)
    // §3.3：摘要类 4 入口（分类/标签/快速记账/数据回溯）统一 v-card 无 pa + 默认内衬
    expect(settingsPageSource.match(/<v-card class="mb-3 settings-card" rounded="xl">/g)).toHaveLength(4)
    // §3.3/§3.5：区块类 3 卡头（外观/导入导出/账号）flex pa-4 保持原骨架
    expect(settingsPageSource.match(/<v-card class="pa-4 mb-3 settings-card" rounded="xl">/g)).toHaveLength(3)
    expect(settingsPageSource.match(/<div class="d-flex align-center mb-[23]">/g)).toHaveLength(3)
    // §3.4：字阶统一取 text-body-1 font-weight-medium（卡头原 text-subtitle-2 已覆盖升级）
    expect(settingsPageSource).not.toContain('text-subtitle-2')
    expect(settingsPageSource.match(/<v-list-item-title class="text-body-1 font-weight-medium">/g)).toHaveLength(8)
    expect(settingsPageSource).toMatch(/<span class="text-body-1 font-weight-medium">外观设置/)
    expect(settingsPageSource).toMatch(/<span class="text-body-1 font-weight-medium">导入导出/)
    expect(settingsPageSource).toMatch(/<span class="text-body-1 font-weight-medium">账号/)
    expect(settingsPageSource).toMatch(/<div class="text-body-1 font-weight-medium">\{\{ username \}\}/)
  })
})
