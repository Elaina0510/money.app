import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

// ── Mocks ──────────────────────────────────────────────────────────
// vue-router 只桩掉 composable，保留 createRouter/createWebHashHistory，
// 使同一文件内可导入真实路由表做快照断言（用例5）。
const mockPush = vi.fn()
const mockBack = vi.fn()

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
  deleteCategory: vi.fn().mockResolvedValue({}),
  restoreDefaultCategories: vi.fn().mockResolvedValue({ message: '已恢复默认分类' }),
}))

vi.mock('@/api/tags', () => ({
  getTags: vi.fn().mockResolvedValue([]),
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
    showToast: vi.fn(),
    themeMode: 'auto',
    setThemeMode: vi.fn(),
  }),
}))

import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  restoreDefaultCategories,
} from '@/api/categories'
import { getTags, createTag, deleteTag } from '@/api/tags'
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

describe('M7 设置页三个管理区块改二级页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    // 每次返回副本：store 的 addCategory/addTag 会 push 进数组，避免污染模块级常量
    getCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
    getTags.mockResolvedValue(TAGS.map((t) => ({ ...t })))
    getRecords.mockResolvedValue({ items: [], total: 0 })
    getQuickTemplates.mockResolvedValue(TEMPLATES.map((t) => ({ ...t })))
    createCategory.mockResolvedValue({ id: 4, name: '新分类', type: 'expense' })
    updateCategory.mockResolvedValue({ id: 1, name: '餐饮', type: 'expense' })
    deleteCategory.mockResolvedValue({})
    restoreDefaultCategories.mockResolvedValue({ message: '已恢复默认分类' })
    createTag.mockResolvedValue({ id: 16, name: '新标签', category_id: 1 })
    deleteTag.mockResolvedValue({})
    addQuickTemplate.mockResolvedValue({})
    deleteQuickTemplate.mockResolvedValue({})
  })

  // ── 用例1：设置页摘要卡 ──────────────────────────────────────────
  it('用例1: 设置页渲染三张摘要卡，只含数量与箭头，不含列表条目/新增按钮', async () => {
    const store = useCategoriesStore()
    await store.fetchTags()
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

  it('用例1b: 二级页操作后（共享 store 变更）摘要数量即时响应，无需重新请求', async () => {
    const store = useCategoriesStore()
    await store.fetchTags()
    const wrapper = await mountPage(SettingsPage)
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

  it('用例2b: 上移/下移走 store.editCategory 交换 sort_order', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    // store 内元素为 reactive 代理，需取列表内的同一引用
    const expense = wrapper.vm.expenseCategories
    await wrapper.vm.moveCategory(expense[1], -1)
    await flushPromises()

    expect(updateCategory).toHaveBeenNthCalledWith(1, 2, { sort_order: 0 })
    expect(updateCategory).toHaveBeenNthCalledWith(2, 1, { sort_order: 1 })
    expect(getCategories).toHaveBeenCalledTimes(2) // 初始加载 + 搬移后刷新
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
    expect(createCategory).toHaveBeenCalledWith({
      name: '娱乐',
      type: 'expense',
      icon: 'mdi-gamepad',
      sort_order: 0,
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
    expect(updateCategory).toHaveBeenCalledWith(1, {
      name: '餐饮美食',
      type: 'expense',
      icon: 'mdi-food',
      sort_order: 0,
    })
    expect(wrapper.vm.editingCategory).toBeNull()

    // 源码断言：任意文本图标名入口已移除，改为接入 CategoryIconPicker
    expect(categoriesPageSource).not.toContain('图标 (mdi-*)')
    expect(categoriesPageSource).not.toContain('placeholder="mdi-food"')
    expect(categoriesPageSource).toContain('<CategoryIconPicker')
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
    const wrapper = await mountPage(SettingsTagsPage)
    expect(wrapper.text()).toContain('暂无标签')

    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)

    useCategoriesStore().tags = TAGS
    await nextTick()
    const text = wrapper.text()
    expect(text).not.toContain('暂无标签')
    expect(text).toContain('日常')
    expect(text).toContain('旅行')
    expect(wrapper.findAll('v-chip')).toHaveLength(5)
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
