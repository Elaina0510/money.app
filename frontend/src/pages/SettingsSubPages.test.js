import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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
  // M6：自动模板按签名忽略（DELETE /records/quick-templates/auto）
  ignoreAutoQuickTemplate: vi.fn().mockResolvedValue({}),
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
  ignoreAutoQuickTemplate,
} from '@/api/records'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import router from '@/router'
import SettingsPage from './SettingsPage.vue'
import SettingsCategoriesPage from './SettingsCategoriesPage.vue'
import CategoryIconPicker from '@/components/common/CategoryIconPicker.vue'
import SettingsTagsPage from './SettingsTagsPage.vue'
import SettingsQuickTemplatesPage from './SettingsQuickTemplatesPage.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
// v1.4.3 M8 §10.5：CSV 映射弹窗去 type 后缀
import CsvMappingDialog from '@/components/common/CsvMappingDialog.vue'
import settingsPageSource from './SettingsPage.vue?raw'
import categoriesPageSource from './SettingsCategoriesPage.vue?raw'
import csvMappingSource from '@/components/common/CsvMappingDialog.vue?raw'
import tagsPageSource from './SettingsTagsPage.vue?raw'
import quickTemplatesPageSource from './SettingsQuickTemplatesPage.vue?raw'
import historyPageSource from './HistoryPage.vue?raw'
// M8 入口图标统一：统计页预算卡头红线断言所需（仅追加，不动既有导入）
import statisticsPageSource from './StatisticsPage.vue?raw'
// v1.4.3 M5：导入导出改设置二级页——新页组件 + ?raw 源码（M8-2 迁出计数改锁所需）
// + @/api/export 六函数（走本文件顶部既有 vi.mock 桩）
import SettingsImportExportPage from './SettingsImportExportPage.vue'
import importExportPageSource from './SettingsImportExportPage.vue?raw'
import routerSource from '@/router/index.js?raw'
import {
  exportCsv,
  exportSql,
  previewCsvImport,
  importCsv,
  previewSqlImport,
  importSql,
} from '@/api/export'
// v1.4.3 M13：图标选择改独立居中弹窗——组件 ?raw 源码锁 + 精选集条目数（仅追加，不动既有导入）
import categoryIconPickerSource from '@/components/common/CategoryIconPicker.vue?raw'
import { CATEGORY_ICONS } from '@/constants/categoryIcons'

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

// ── M3 拖拽排序 + v1.4.3 M8 统一分类：含唯一「其他」置末的全量可见集合 ──────
// type 列按 D2 保留迁移前的原值（收支共用后前端一律不读取），
// 工资/红包 仍带 legacy 'income' 值却必须与其余行同列渲染 —— 即「忽略 type」的回归载体
const REORDER_CATEGORIES = [
  { id: 1, name: '餐饮', type: 'expense', icon: 'mdi-food', sort_order: 1, is_preset: 1 },
  { id: 2, name: '出行', type: 'expense', icon: 'mdi-bus', sort_order: 2, is_preset: 1 },
  { id: 3, name: '购物', type: 'expense', icon: 'mdi-cart', sort_order: 3, is_preset: 0 },
  { id: 9, name: '工资', type: 'income', icon: 'mdi-wallet', sort_order: 4, is_preset: 1 },
  { id: 10, name: '红包', type: 'income', icon: 'mdi-cash-plus', sort_order: 5, is_preset: 1 },
  { id: 8, name: '其他', type: 'expense', icon: 'mdi-cash-minus', sort_order: 99, is_preset: 1 },
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
    ignoreAutoQuickTemplate.mockResolvedValue({})
  })

  // ── 用例1：设置页摘要卡 ──────────────────────────────────────────
  it('用例1: 设置页渲染四张摘要卡，只含数量与箭头，不含列表条目/新增按钮', async () => {
    // M5：不再手动预拉标签——摘要数量应由 onMounted 自身的 fetchTags 提供
    const wrapper = await mountPage(SettingsPage)

    // 四张摘要卡的跳转目标（v1.4.3 M5：导入导出内联卡迁出为二级页，设置页只留入口行）
    const entries = wrapper
      .findAll('v-list-item')
      .filter((node) => node.attributes('to'))
      .map((node) => node.attributes('to'))
    expect(entries).toEqual([
      '/settings/categories',
      '/settings/tags',
      '/settings/quick-templates',
      '/settings/import-export',
    ])

    const text = wrapper.text()
    expect(text).toContain('分类管理')
    expect(text).toContain('标签管理')
    expect(text).toContain('快速记账')
    // 数量摘要（M8：分类收支共用 → 单一「N 个分类」，不再分列支出/收入）
    expect(text).toContain('4 个分类')
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
    expect(wrapper.text()).toContain('4 个分类')
    expect(wrapper.text()).toContain('5 个')

    store.categories = [...CATEGORIES, { id: 4, name: '娱乐', type: 'expense' }]
    store.tags = []
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('5 个分类')
    expect(text).toContain('0 个')
    // 数量更新未触发对设置页的重新请求
    expect(getTags).toHaveBeenCalledTimes(1)
  })

  // ── 用例2：分类管理二级页 ────────────────────────────────────────
  it('用例2: 分类二级页返回按钮触发 router.back，渲染收支共用单一列表', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)

    const text = wrapper.text()
    // M8：原「支出分类 / 收入分类」两组标题已删，改为单一「全部分类」块
    expect(text).not.toContain('支出分类')
    expect(text).not.toContain('收入分类')
    expect(text).toContain('全部分类')
    expect(text).toContain('餐饮')
    // 收支共用：原收入预设「工资」与支出同类同列可见（前端不再按 type 过滤）
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
    // M8：收支两组并为一组 → 把手/占位各恰一处
    expect(categoriesPageSource.match(/mdi-drag-vertical/g)).toHaveLength(1)
    expect(categoriesPageSource.match(/class="drag-handle mr-1"/g)).toHaveLength(1)
    expect(categoriesPageSource.match(/class="drag-handle-placeholder mr-1"/g)).toHaveLength(1)
    expect(categoriesPageSource).toMatch(/v-if="!isOther\(cat\)"/)
    // 样式红线：touch-action: none 只加把手，未污染整行（加整行会杀死列表滚动）
    expect(categoriesPageSource).toMatch(/\.drag-handle \{[^}]*touch-action: none/)
    expect(categoriesPageSource).not.toMatch(/\.category-list-item \{[^}]*touch-action/)
    expect(categoriesPageSource).toMatch(/\.drag-handle-placeholder \{[^}]*width: 20px/)

    // M8：单一 Draggable 实例承载全量单列表（原支出/收入两个实例已合并）
    const draggables = wrapper.findAllComponents(Draggable)
    expect(draggables).toHaveLength(1)
    const options = sortableOptionsOf(draggables[0])
    expect(options.handle).toBe('.drag-handle')
    expect(options.delay).toBe(150)
    expect(options.delayOnTouchOnly).toBe(true)
    expect(options.touchStartThreshold).toBe(5)
    expect(options.ghostClass).toBe('drag-ghost')
    expect(options.dragClass).toBe('drag-float')
    expect(options.disabled).toBe(false)
    expect(draggables[0].props('itemKey')).toBe('id')

    // REORDER 夹具：6 行（含原收入类）全在一列；行渲染与 Sortable 命中集一一对应
    // （[data-draggable] 缺失即整列表拖不动，属真实渲染断言）
    expect(wrapper.findAll('.category-list-item')).toHaveLength(6)
    expect(wrapper.findAll('[data-draggable]')).toHaveLength(6)

    // jsdom 不真实驱动 sortable：vm 直改 dragList 后手动调 onDragEnd
    expect(wrapper.vm.dragList.map((c) => c.name)).toEqual([
      '餐饮',
      '出行',
      '购物',
      '工资',
      '红包',
      '其他',
    ])
    const list = wrapper.vm.dragList
    wrapper.vm.onDragStart()
    expect(wrapper.vm.preDragSnapshot.map((c) => c.id)).toEqual([1, 2, 3, 9, 10, 8])
    wrapper.vm.dragList = [list[1], list[0], list[2], list[3], list[4], list[5]]
    wrapper.vm.onDragEnd()
    await flushPromises()

    expect(reorderCategories).toHaveBeenCalledTimes(1)
    // M8：body 仅 { ids }，且为「全量」可见集合（跨原收支语义的 工资/红包 一并提交）
    expect(reorderCategories).toHaveBeenCalledWith({ ids: [2, 1, 3, 9, 10, 8] })
    // 全流程唯一一次 toast：store 成功路径不再附加「更新成功」类提示
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('排序已保存')
  })

  it('用例2b-2:「其他」被拖到中间 → 本地与提交 ids 均归一化回末位；isOther/isOtherLocked 口径', async () => {
    const wrapper = await mountReorderPage()
    const list = wrapper.vm.dragList
    const [food, trip, shopping, salary, redpack, other] = list

    wrapper.vm.onDragStart()
    wrapper.vm.dragList = [food, other, trip, shopping, salary, redpack]
    wrapper.vm.onDragEnd()
    // 本地镜像后端「末尾占位」归一化（同步生效，避免保存后跳变）——作用域为全列表
    expect(wrapper.vm.dragList.map((c) => c.name)).toEqual([
      '餐饮',
      '出行',
      '购物',
      '工资',
      '红包',
      '其他',
    ])
    await flushPromises()
    expect(reorderCategories).toHaveBeenCalledWith({ ids: [1, 2, 3, 9, 10, 8] })

    // M8/D11：isOther 仅按 name 判定（唯一真源「其他」）；
    // v1.4.2 的「其他支出/其他收入」双别名迁移后已不存在，不再命中
    expect(wrapper.vm.isOther(other)).toBe(true)
    expect(wrapper.vm.isOther({ name: '其他' })).toBe(true)
    expect(wrapper.vm.isOther({ name: '其他', type: 'income' })).toBe(true)
    expect(wrapper.vm.isOther({ name: '其他支出', type: 'expense' })).toBe(false)
    expect(wrapper.vm.isOther({ name: '其他收入', type: 'income' })).toBe(false)
    expect(wrapper.vm.isOther({ name: '餐饮', type: 'expense' })).toBe(false)
    expect(wrapper.vm.isOther(null)).toBe(false)

    // isOtherLocked: 非末位「其他」（异常数据）→ 禁用拖动
    expect(wrapper.vm.isOtherLocked([other, food, trip])).toBe(true)
    expect(wrapper.vm.isOtherLocked([food, trip, other])).toBe(false)
    expect(wrapper.vm.isOtherLocked([])).toBe(false)
    expect(sortableOptionsOf(wrapper.findAllComponents(Draggable)[0]).disabled).toBe(false)
  })

  it('用例2b-3: 保存失败 → 回滚拖前快照 + 错误 toast，并静默重拉对齐后端真值', async () => {
    const wrapper = await mountReorderPage()
    reorderCategories.mockRejectedValue(new Error('排序列表与当前分类不一致'))
    // 重拉同样失败：证明列表恢复来自快照回滚而非重新请求
    getCategories.mockRejectedValue(new Error('network down'))

    const list = wrapper.vm.dragList
    wrapper.vm.onDragStart()
    // 整表左旋一位 →「其他」落到首位，归一化后回末位，提交 ids = [2,3,9,10,1,8]
    wrapper.vm.dragList = [list[1], list[2], list[3], list[4], list[5], list[0]]
    wrapper.vm.onDragEnd()
    await flushPromises()

    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ ids: [2, 3, 9, 10, 1, 8] })
    expect(wrapper.vm.dragList.map((c) => c.id)).toEqual([1, 2, 3, 9, 10, 8])
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
    // M2：新增载荷不携带 sort_order（排序由服务端计算：追加列表末、「其他」之前）
    // M8：分类收支共用 → 载荷仅 {name, icon}，不再有 type
    expect(createCategory).toHaveBeenCalledWith({
      name: '娱乐',
      icon: 'mdi-gamepad',
    })
    expect(updateCategory).not.toHaveBeenCalled()

    // 编辑：表单项回填、标题切换为「编辑分类」，面板选中态同步为原图标
    const target = wrapper.vm.dragList[0]
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
    // M2：编辑载荷不含 type（M8 起无类型语义）也不含 sort_order（单个 PUT 不改排序）
    expect(updateCategory).toHaveBeenCalledWith(1, {
      name: '餐饮美食',
      icon: 'mdi-food',
    })
    expect(wrapper.vm.editingCategory).toBeNull()

    // 表单状态与模板均不再持有「排序」，也不再持有「类型」（M8）
    expect(Object.keys(wrapper.vm.categoryForm).sort()).toEqual(['icon', 'name'])
    expect(categoriesPageSource).not.toContain('label="排序"')
    expect(categoriesPageSource).not.toContain('label="类型"')
    expect(categoriesPageSource).not.toMatch(/\btypeOptions\b/)
    expect(categoriesPageSource).not.toMatch(/categoryForm\.type/)

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

  // ── 用例4：快速记账二级页（M6 口径反转：自动模板按签名忽略 + 删除确认弹窗） ──
  it('用例4: 模板列表渲染；删除先弹确认，自动项按签名忽略、手动项按 id 删', async () => {
    // 模拟后端语义：忽略/删除后的签名不再出现在 GET 结果里（每次返回新副本，
    // 使「本地即时移除 + 后台静默重拉」可被分别断言）
    const cents = (v) => Math.round(Number(v) * 100)
    let serverTemplates = TEMPLATES.map((t) => ({ ...t }))
    getQuickTemplates.mockImplementation(() =>
      Promise.resolve(serverTemplates.map((t) => ({ ...t })))
    )
    ignoreAutoQuickTemplate.mockImplementation((params) => {
      serverTemplates = serverTemplates.filter(
        (t) => !(t.source === 'auto' && cents(t.amount) === params.amount_cents)
      )
      return Promise.resolve({})
    })
    deleteQuickTemplate.mockImplementation((id) => {
      serverTemplates = serverTemplates.filter((t) => t.id !== id)
      return Promise.resolve({})
    })

    const wrapper = await mountPage(SettingsQuickTemplatesPage)

    const text = wrapper.text()
    expect(text).toContain('日常 · ¥25')
    expect(text).toContain('餐饮 · 使用 8 次')
    expect(text).toContain('打车 · ¥30')
    // §6.2.1 列表 key 与后端手动/自动去重键同口径（分单位整数签名，D9 三处同口径）
    expect(quickTemplatesPageSource).toContain(
      ':key="`${tpl.source}-${tpl.tag_id}-${Math.round(Number(tpl.amount) * 100)}`"'
    )

    // 自动模板点删除：只进确认弹窗（旧「无 id 不请求只刷新」口径作废）
    const autoTpl = wrapper.vm.quickTemplates.find((t) => t.source === 'auto')
    await wrapper.vm.removeQuickTemplate(autoTpl)
    expect(wrapper.vm.showDeleteDialog).toBe(true)
    expect(wrapper.vm.deletingTemplate).toBe(autoTpl)
    expect(wrapper.vm.deleteMessage).toContain('该组合今后不再自动出现')
    expect(ignoreAutoQuickTemplate).not.toHaveBeenCalled()
    expect(deleteQuickTemplate).not.toHaveBeenCalled()

    // 确认 → 按签名忽略恰一次；条目即时消失 + 一次成功 toast + 后台静默重拉
    await wrapper.vm.handleDelete()
    await flushPromises()
    expect(ignoreAutoQuickTemplate).toHaveBeenCalledTimes(1)
    expect(ignoreAutoQuickTemplate).toHaveBeenCalledWith({
      tag_id: 11,
      type: 'expense',
      amount_cents: 2500,
    })
    expect(deleteQuickTemplate).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('日常 · ¥25')
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('模板已删除')
    expect(getQuickTemplates).toHaveBeenCalledTimes(2)
    expect(wrapper.vm.showDeleteDialog).toBe(false)
    expect(wrapper.vm.deletingTemplate).toBe(null)
    expect(wrapper.vm.deleting).toBe(false)

    // 手动模板：确认后仍走 deleteQuickTemplate(id)，忽略接口不再被调
    const manualTpl = wrapper.vm.quickTemplates.find((t) => t.source === 'manual')
    await wrapper.vm.removeQuickTemplate(manualTpl)
    expect(wrapper.vm.deleteMessage).not.toContain('自动模板')
    await wrapper.vm.handleDelete()
    await flushPromises()
    expect(deleteQuickTemplate).toHaveBeenCalledTimes(1)
    expect(deleteQuickTemplate).toHaveBeenCalledWith(21)
    expect(ignoreAutoQuickTemplate).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).not.toContain('打车 · ¥30')
    expect(wrapper.vm.quickTemplates).toHaveLength(0)
    expect(mockShowToast).toHaveBeenCalledTimes(2)
    expect(getQuickTemplates).toHaveBeenCalledTimes(3)

    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)
  })

  // M6 §7.3.2：取消不做任何请求
  it('用例4c: 删除确认弹窗点取消 → 两接口均未调、列表原状', async () => {
    const wrapper = await mountPage(SettingsQuickTemplatesPage)
    const before = wrapper.vm.quickTemplates.slice()

    await wrapper.vm.removeQuickTemplate(wrapper.vm.quickTemplates[1])
    const dialog = wrapper.findComponent(ConfirmDialog)
    expect(dialog.exists()).toBe(true)
    expect(dialog.props('title')).toBe('删除模板')
    expect(dialog.props('confirmText')).toBe('删除')

    const cancelBtn = dialog.findAll('v-btn').find((node) => node.text() === '取消')
    expect(cancelBtn, '确认弹窗取消按钮未渲染').toBeTruthy()
    await cancelBtn.trigger('click')
    await flushPromises()

    expect(deleteQuickTemplate).not.toHaveBeenCalled()
    expect(ignoreAutoQuickTemplate).not.toHaveBeenCalled()
    expect(mockShowToast).not.toHaveBeenCalled()
    expect(wrapper.vm.showDeleteDialog).toBe(false)
    expect(wrapper.vm.quickTemplates).toEqual(before)
    expect(wrapper.text()).toContain('打车 · ¥30')
  })

  // M6 §7.3.3：失败保持原状 + 错误 toast
  it('用例4d: 忽略请求失败 → 错误 toast、列表保持原状、状态复位', async () => {
    const wrapper = await mountPage(SettingsQuickTemplatesPage)
    const before = wrapper.vm.quickTemplates.slice()
    ignoreAutoQuickTemplate.mockRejectedValueOnce(new Error('network down'))

    await wrapper.vm.removeQuickTemplate(wrapper.vm.quickTemplates[0])
    await wrapper.vm.handleDelete()
    await flushPromises()

    expect(ignoreAutoQuickTemplate).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('删除失败', 'error')
    // 本地未动过：列表原状、无静默重拉
    expect(wrapper.vm.quickTemplates).toEqual(before)
    expect(wrapper.text()).toContain('日常 · ¥25')
    expect(getQuickTemplates).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.deleting).toBe(false)
    expect(wrapper.vm.showDeleteDialog).toBe(false)
    expect(wrapper.vm.deletingTemplate).toBe(null)
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
      // M8：原 expenseCategories / incomeCategories / typeOptions 随收支共用一并删除，
      // 换为单列表渲染源与统一「其他」真源、单块标题
      'dragList',
      'OTHER_CATEGORY_NAME',
      '全部分类',
      'showCategoryDialog',
      'categoryForm',
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
    // M6 口径反转（D10 疏朗化）：卡片内衬 16px → 20px，容器其余规范不变
    expect(styles).toMatch(/\.page-card \{[^}]*padding: 20px/)
    expect(styles).toMatch(/\.page-card \{[^}]*margin-bottom: 12px/)
    // §1.2 深色不加分支（--v-theme-surface 运行时随主题切换）
    expect(styles).not.toMatch(/\.v-theme--dark[^{]*\.page-card/)
    // §1.3 钩子类 .settings-card 不另行赋样式，样式统一由 .page-card 承载
    expect(styles).not.toMatch(/\.settings-card\s*\{/)

    const pages = [
      // M8：分类页两组并一，组标题改单块「全部分类」（收入/支出标题已删）
      ['分类页', categoriesPageSource, ['全部分类', '暂无分类']],
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

    // M8：分类页并为一块（原两块 mb-4 间距口径由单块 section-block 取代，
    //     section-block/section-title 类名挂载在分类页，定义归 M6 全局疏朗化）
    const categoriesCard = splitByPageCard(categoriesPageSource).card
    expect(categoriesCard.match(/class="section-block"/g)).toHaveLength(1)
    expect(categoriesCard).toMatch(/class="section-title[^"]*">全部分类/)
    // 标签页 chip 云入卡（§2.3，M5 分页控件同卡位由 M5 承接）
    expect(splitByPageCard(tagsPageSource).card).toContain('flex-wrap')

    // §3.1 数据回溯页空态包卡
    expect(historyPageSource).toMatch(/class="page-card text-center"[\s\S]*?暂无操作记录/)
    // M6 口径反转（需求六 3）：主体列表由裸 v-card 统一改挂 .page-card（v-else 移至 div）
    expect(historyPageSource).toMatch(/<div v-else class="page-card">/)
  })

  // 任务 §4.2（P2 收敛后的「页面级无透视」结构性口径）
  it('用例M4-2: 卡壳之外无列表透明直贴页面背景；卡内 Draggable 的 bg-transparent 合法保留', () => {
    const categories = splitByPageCard(categoriesPageSource)
    expect(categories.outside).not.toContain('bg-transparent')
    // M8：两组并一组 → 卡内 Draggable 的 v-list 恰一处保留 bg-transparent（卡内合法，非页面级透视）
    expect(categories.card.match(/bg-transparent/g)).toHaveLength(1)

    const templates = splitByPageCard(quickTemplatesPageSource)
    expect(templates.outside).not.toContain('bg-transparent')
    // 模板页原页面级透视列表（§2.5 点名）彻底去除透明写法
    expect(templates.card).not.toContain('bg-transparent')

    const tags = splitByPageCard(tagsPageSource)
    expect(tags.outside).not.toContain('bg-transparent')

    // 数据回溯页唯一 bg-transparent 在卡壳内（展开明细列表），页面级无裸列表
    // （M6：外层裸 v-card 已统一改挂 .page-card，锚点随之换形）
    expect(historyPageSource).toMatch(/<div v-else class="page-card">[\s\S]*?bg-transparent/)
  })

  // 任务 §4.3（渲染快照）+ M3 交接的卡壳 × 拖拽回归 + M8 单列表并组
  it('用例M4-3: 分类页单块「全部分类」渲染在 .page-card 内，卡壳不影响拖拽与批量重排', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)
    const cards = wrapper.findAll('.page-card')
    expect(cards).toHaveLength(1)
    const card = cards[0]

    const text = card.text()
    // M8：单块标题，原「支出分类 / 收入分类」双标题不再渲染
    expect(text).toContain('全部分类')
    expect(text).not.toContain('支出分类')
    expect(text).not.toContain('收入分类')
    expect(text).toContain('餐饮')
    expect(text).toContain('其他')
    // 页头操作按钮留卡外
    expect(text).not.toContain('恢复默认')
    expect(wrapper.text()).toContain('恢复默认')
    // M8：并为一块（无原两块间的 mb-4 间距节点）
    expect(card.findAll('.mb-4')).toHaveLength(0)
    expect(card.findAll('.section-block')).toHaveLength(1)
    // §5.2：行图标统一 .entry-avatar（收支双色底已消除）。
    // 头像在 v-list-item 具名 slot 内，本文件不装 Vuetify 故不落 DOM → ?raw 源码口径
    expect(categoriesPageSource.match(/class="entry-avatar mr-2"/g)).toHaveLength(1)
    expect(categoriesPageSource).not.toMatch(/#FFE8E8|#E8FFF3/)
    expect(categoriesPageSource).not.toMatch(/#FF6B6B|#20C997/)

    // 卡壳未吃掉 M3 拖拽结构：单组一个 Draggable 实例、行渲染源一一对应
    expect(card.findAllComponents(Draggable)).toHaveLength(1)
    expect(card.findAll('.category-list-item')).toHaveLength(6)
    expect(card.findAll('[data-draggable]')).toHaveLength(6)

    // 拖拽改序仍走一次批量重排（视觉结构未回归破坏）
    const list = wrapper.vm.dragList
    wrapper.vm.onDragStart()
    wrapper.vm.dragList = [list[1], list[0], list[2], list[3], list[4], list[5]]
    wrapper.vm.onDragEnd()
    await flushPromises()
    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ ids: [2, 1, 3, 9, 10, 8] })
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

// 截出设置页「数据回溯」卡区间：§5.4 定点断言，避免误伤外观/导入导出/账号三张卡头
// （v1.4.3 M5 口径反转：结束锚点原为已迁出的 `<!-- Hidden file inputs -->`，改锁下一区块 Account Section）
function sliceHistoryCard(source) {
  const start = source.indexOf('<!-- Data History Entry -->')
  const end = source.indexOf('<!-- Account Section -->')
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
    // M4 段落零污染（M6 仅把内衬 16px 提到 20px，容器规范本身未动）
    expect(styles).toMatch(/\.page-card \{[^}]*padding: 20px/)
  })

  // 任务 §5.1 + §5.2 + §2.1~§2.3 + §4.1
  // 【v1.4.3 M5 口径反转改写】原「7 卡头 + 导入导出 4 子条目 = 11 处」中的 4 子条目
  // 随导入导出迁出设置主页（非放宽）：主页计数改 7，迁出的 4 处同规格改锁新页源文件。
  it('用例M8-2: 两页零内联 rgba 头像底与静态 Material 图标色，7+4+1 处同规格', () => {
    for (const src of [settingsPageSource, statisticsPageSource, importExportPageSource]) {
      expect(src).not.toMatch(AVATAR_INLINE_RGBA)
      expect(src).not.toMatch(STATIC_ICON_COLOR)
    }
    // §5.2 SettingsPage 严口径：整文件零 rgba（原 7 处 v-avatar 内联底色已全部收敛到类）
    expect(settingsPageSource).not.toContain('rgba(')
    // §5.1 正向断言：入口头像类已落地
    expect(settingsPageSource).toContain('entry-avatar')
    expect(statisticsPageSource).toContain('entry-avatar')
    // §2.3：外观/分类/标签/快速记账/导入导出（M5 入口行）/数据回溯/账号 7 处同规格
    expect(settingsPageSource.match(ENTRY_AVATAR_TPL)).toHaveLength(7)
    // M5：迁入二级页的 4 个子条目（导出/导入 CSV、导出/导入 SQL）同规格不降级
    expect(importExportPageSource.match(ENTRY_AVATAR_TPL)).toHaveLength(4)
    // §4.1：统计页仅预算卡头一处（M8 范围收敛）
    expect(statisticsPageSource.match(ENTRY_AVATAR_TPL)).toHaveLength(1)
    // §3.1：裸 v-icon（无圆底）写法已消除
    expect(settingsPageSource).not.toMatch(/<v-icon size="20" class="mr-3">/)
  })

  // 任务 §4.2 红线（易错点 9）：数据可视化语义色不入清理范围
  // 【v1.4.3 M12 口径反转改写】原两条「预算行头像动态语义色」锁定断言（`const BUDGET_COLORS =`
  // + `<v-avatar size="32" :color="getBudgetColor(index) + '20'">` / `<v-icon ... :color="getBudgetColor(index)">`）
  // 随 m12 任务 5.1/5.6 删除「每分类一条预算」行内列表而整体消失（改预算卡片列表，色档走
  // Vuetify 语义色档函数），非放宽：改锁色档函数与其阈值分支，零误伤意图与正则收敛自证保持。
  it('用例M8-3: 统计页图表/预算行语义色零误伤，红线正则可寻址收敛', () => {
    expect(statisticsPageSource).toContain('const chartColors =')
    expect(statisticsPageSource).toContain('const balanceColor = computed(')
    // 预算卡进度色档仍是数据可视化语义色档（>80% error / >50% warning / 其余 primary），
    // 未被改成写死静态色，也不残留旧行内列表的动态色
    expect(statisticsPageSource).toMatch(/function budgetBarColor\(budget\) \{/)
    expect(statisticsPageSource).toMatch(/if \(pct > 80\) return 'error'/)
    expect(statisticsPageSource).not.toMatch(/BUDGET_COLORS|getBudgetColor/)
    // 收敛性自证：图表配置里的合法 rgba 确实存在，却不被两类可寻址红线命中
    // （反证「不得整文件扫 rgba(」的必要性）
    expect(statisticsPageSource).toContain("grid: { color: 'rgba(0,0,0,0.04)' }")
    expect(statisticsPageSource).not.toMatch(AVATAR_INLINE_RGBA)
    expect(statisticsPageSource).not.toMatch(STATIC_ICON_COLOR)
    // M7 图表卡与动画零污染（本模块未触碰）
    expect(statisticsPageSource).toContain('chart-card')
  })

  // 任务 §5.3（渲染）+ 需求 5 条（文案/顺序/功能不变）
  // 【v1.4.3 M5 口径反转改写】导入导出四行（导出/导入 CSV、导出/导入 SQL）已迁出为
  // /settings/import-export 二级页 → 原「≥ 11 且含 4 子条目」改锁 7 入口 + 四行零残留，
  // 迁出后的四行渲染断言随 M5 新用例组承接（用例M5-1），非放宽。
  it('用例M8-4: 挂载后 .entry-avatar 计数 = 7 且其内图标均为 primary 色', async () => {
    const wrapper = mount(SettingsPage, {
      global: {
        mocks: { $router: { push: mockPush, back: mockBack } },
        components: { 'v-list-item': EntrySlotHost },
      },
    })
    await flushPromises()

    const avatars = wrapper.findAll('.entry-avatar')
    expect(avatars).toHaveLength(7)
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
    // 7 个入口图标齐全且无游离头像（顺序即模板顺序，需求 5 条不改文案与顺序）
    expect(avatars.map((node) => node.find('v-icon').text())).toEqual([
      'mdi-brightness-6',
      'mdi-shape',
      'mdi-tag-multiple',
      'mdi-lightning-bolt',
      'mdi-swap-vertical',
      'mdi-history',
      'mdi-account',
    ])
    // 文案与摘要功能未受影响
    const text = wrapper.text()
    ;['外观设置', '分类管理', '标签管理', '快速记账', '导入导出', '数据回溯', '账号'].forEach(
      (title) => expect(text).toContain(title)
    )
    // M5 红线：四个操作行不再在设置主页渲染（行名 + 副标题双口径零残留）
    const rowTitles = wrapper.findAll('v-list-item-title').map((node) => node.text())
    ;['导出 CSV', '导入 CSV', '导出 SQL', '导入 SQL'].forEach((title) =>
      expect(rowTitles).not.toContain(title)
    )
    ;['导出账单为 CSV 文件', '从 CSV 文件导入账单', '导出全量数据为 SQL 备份'].forEach((sub) =>
      expect(text).not.toContain(sub)
    )
    expect(text).toContain('导出 CSV/SQL，导入备份文件')
    expect(text).toContain('4 个分类')
    expect(text).toContain('5 个')
    expect(text).toContain('2 个模板')
  })

  // 任务 §3.2 / §3.3 / §3.4 / §5.4（结构性修复；§3.5 骨架不归一 = 两类并存）
  // 【v1.4.3 M5 口径反转改写】导入导出由「pa-4 区块卡 + 4 子条目」降为摘要入口行 →
  // 摘要类 4→5、区块类 3→2、字阶标题 8→5（迁入新页的 4 行由用例M5-5 同口径锁定），非放宽。
  it('用例M8-5: 数据回溯卡去 pa-4 叠加、左偏移两类基线与字阶统一', () => {
    const history = sliceHistoryCard(settingsPageSource)
    // §5.4：不再出现 pa-4 卡壳与 v-list 的双层 padding 叠加写法
    expect(history).not.toContain('class="pa-4 mb-3 settings-card"')
    // §3.2：去 pa-4 后与摘要入口同构；v-list 的 bg-transparent pa-0 保留（深色白底已消除）
    expect(history).toContain('<v-card class="mb-3 settings-card" rounded="xl">')
    expect(history).toMatch(/<v-list class="bg-transparent pa-0">/)
    expect(history).toMatch(/<v-list-item-title class="text-body-1 font-weight-medium">数据回溯/)
    // §3.3：摘要类 5 入口（分类/标签/快速记账/导入导出[M5 入口行]/数据回溯）
    //      统一 v-card 无 pa + 默认内衬
    expect(settingsPageSource.match(/<v-card class="mb-3 settings-card" rounded="xl">/g)).toHaveLength(5)
    // §3.3/§3.5：区块类 2 卡头（外观/账号）flex pa-4 保持原骨架
    //（M5：导入导出区块卡已迁出，其原「pa-4 卡头 + d-flex」骨架随之内联卡一并消失）
    expect(settingsPageSource.match(/<v-card class="pa-4 mb-3 settings-card" rounded="xl">/g)).toHaveLength(2)
    expect(settingsPageSource.match(/<div class="d-flex align-center mb-[23]">/g)).toHaveLength(2)
    expect(settingsPageSource).not.toMatch(/<span class="text-body-1 font-weight-medium">导入导出/)
    // §3.4：字阶统一取 text-body-1 font-weight-medium（卡头原 text-subtitle-2 已覆盖升级）
    expect(settingsPageSource).not.toContain('text-subtitle-2')
    expect(
      settingsPageSource.match(/<v-list-item-title class="text-body-1 font-weight-medium">/g)
    ).toHaveLength(5)
    expect(settingsPageSource).toMatch(/<span class="text-body-1 font-weight-medium">外观设置/)
    expect(settingsPageSource).toMatch(
      /<v-list-item-title class="text-body-1 font-weight-medium">导入导出/
    )
    expect(settingsPageSource).toMatch(/<span class="text-body-1 font-weight-medium">账号/)
    expect(settingsPageSource).toMatch(/<div class="text-body-1 font-weight-medium">\{\{ username \}\}/)
  })
})

// ── v1.4.3 M8 分类收支共用统一标签（前端消费方，任务 §10） ───────────────────
describe('v1.4.3 M8 分类收支共用统一标签（前端）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    // 统一后的服务端可见集合：单列表、唯一「其他」恒末位、type 列仅存遗留值
    getCategories.mockResolvedValue(reorderCopy())
    reorderCategories.mockResolvedValue(reorderCopy())
    createCategory.mockResolvedValue({ id: 11, name: '娱乐', type: 'expense' })
    getTags.mockResolvedValue([])
    useSlicedPagedMock([])
    getQuickTemplates.mockResolvedValue([])
  })

  function mountSlots(component) {
    return mount(component, {
      global: {
        mocks: { $router: { push: mockPush, back: mockBack } },
        components: { 'v-list-item': EntrySlotHost },
      },
    })
  }

  // 任务 §10.1（+ §5.1/§5.4 渲染快照）
  it('用例10.1: 单列表渲染——无收支分组标题、「其他」行无把手且恒末位', async () => {
    const wrapper = mountSlots(SettingsCategoriesPage)
    await flushPromises()
    await nextTick()

    const text = wrapper.text()
    expect(text).not.toContain('支出分类')
    expect(text).not.toContain('收入分类')
    expect(text).toContain('全部分类')
    // 单一列表：6 行全部同列（原收入预设 工资/红包 与支出类混排）
    // 注：EntrySlotHost 替换了 v-list-item 本体，行容器 class 不再落 DOM → 按标题节点计数
    const titles = wrapper.findAll('.category-title')
    expect(titles).toHaveLength(6)
    expect(titles.map((node) => node.text().replace(/\s+/g, ' ').trim())).toEqual([
      '餐饮 预设',
      '出行 预设',
      '购物',
      '工资 预设',
      '红包 预设',
      '其他 预设',
    ])

    // 恰一个 Draggable 实例承载全量单列表
    expect(wrapper.findAllComponents(Draggable)).toHaveLength(1)

    // 「其他」无把手（占位同宽保对齐），其余 5 行各一把手。
    // EntrySlotHost 将每行 prepend/default/append 摊平为兄弟节点 → 按文档序配对行序
    const handles = wrapper.findAll('.drag-handle, .drag-handle-placeholder')
    expect(handles).toHaveLength(6)
    expect(handles[5].classes()).toContain('drag-handle-placeholder')
    expect(handles[5].classes()).not.toContain('drag-handle')
    handles
      .slice(0, 5)
      .forEach((node) => expect(node.classes()).toContain('drag-handle'))

    // 行图标全部走 .entry-avatar（收支双色底已消除）
    expect(wrapper.findAll('.entry-avatar')).toHaveLength(6)
    expect(wrapper.findAll('.entry-avatar v-icon').map((n) => n.attributes('color'))).toEqual(
      Array(6).fill('primary')
    )
  })

  // 任务 §10.2（+ §5.3 弹窗载荷）
  it('用例10.2: 弹窗无「类型」下拉；保存载荷仅 {name, icon}', async () => {
    const wrapper = await mountPage(SettingsCategoriesPage)

    wrapper.vm.showCategoryDialog = true
    wrapper.vm.categoryForm.name = '娱乐'
    wrapper.vm.categoryForm.icon = 'mdi-gamepad'
    await nextTick()

    // DOM 口径：弹窗内不再有 label="类型" 的选择器，也不再渲染 v-select 类型项
    const selects = wrapper.findAll('v-select')
    expect(selects.filter((node) => node.attributes('label') === '类型')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('支出')
    expect(wrapper.text()).not.toContain('收入')

    await wrapper.vm.saveCategory()
    await flushPromises()
    expect(createCategory).toHaveBeenCalledTimes(1)
    expect(createCategory).toHaveBeenCalledWith({ name: '娱乐', icon: 'mdi-gamepad' })
    // 载荷键集恰为 name/icon（既无 type 也无 sort_order）
    expect(Object.keys(createCategory.mock.calls[0][0]).sort()).toEqual(['icon', 'name'])
  })

  // 任务 §10.3（+ §6.4 store 签名收敛）
  it('用例10.3: store.reorderCategories(ids) 以纯 ids 调批量重排接口', async () => {
    const store = useCategoriesStore()
    await store.fetchCategories()

    await store.reorderCategories([2, 1, 3, 9, 10, 8])
    await flushPromises()

    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ ids: [2, 1, 3, 9, 10, 8] })
    // 全量单列表：一次提交覆盖原收支两类共 6 个 id，body 无 type 键
    expect(Object.keys(reorderCategories.mock.calls[0][0])).toEqual(['ids'])
    // 成功路径不附加 toast（唯一提示由页面发「排序已保存」）
    expect(mockShowToast).not.toHaveBeenCalled()
    // 按 type 过滤的两个 computed 已从 store 移除
    expect(store.expenseCategories).toBeUndefined()
    expect(store.incomeCategories).toBeUndefined()
    // 排序后整体重拉以对齐后端真值（预设 CoW 会换 id）
    expect(getCategories).toHaveBeenCalledTimes(2)
  })

  // 任务 §10.5（+ §6.3 CSV 映射弹窗）
  it('用例10.5: CsvMappingDialog 选项 label 无「(支出/收入)」后缀、新建不带 type', async () => {
    const preview = {
      format: 'native',
      row_count: 3,
      categories_in_file: ['餐饮', '报销', '自定义X'],
      tags_in_file: [],
    }
    const wrapper = mount(CsvMappingDialog, {
      props: { modelValue: true, previewData: preview, categories: reorderCopy() },
    })
    await flushPromises()

    const labels = wrapper.vm.categoryOptions.map((o) => o.label)
    expect(labels).toEqual(['— 跳过 —', '餐饮', '出行', '购物', '工资', '红包', '其他', '+ 新建分类'])
    labels.forEach((label) => {
      expect(label).not.toContain('(支出)')
      expect(label).not.toContain('(收入)')
      expect(label).not.toMatch(/[（(](支出|收入)[）)]/)
    })
    // 源码级红线：不再拼接 type 后缀
    expect(csvMappingSource).not.toMatch(/支出.*:.*收入/)
    expect(csvMappingSource).not.toMatch(/cat\.type/)

    // 新建映射载荷不带 type（后端 CategoryCreate 已删该字段）
    wrapper.vm.setCategoryMapping('自定义X', 'create')
    await nextTick()
    await wrapper.vm.handleConfirm()
    const payload = wrapper.emitted('confirm')[0][0]
    expect(payload.category_mapping['自定义X']).toEqual({ action: 'create' })
    expect(payload.category_mapping['自定义X']).not.toHaveProperty('type')
    // 同名即映射：按 name 命中，与 type 无关
    expect(payload.category_mapping['餐饮']).toEqual({ action: 'map', target_id: 1 })
  })

  // 任务 §10.6（+ §6.2 设置页摘要）
  it('用例10.6: 设置页分类摘要为「N 个分类」，不再分列支出/收入', async () => {
    const wrapper = await mountPage(SettingsPage)
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('6 个分类')
    expect(text).not.toMatch(/支出 \d+ \/ 收入 \d+/)

    // 响应式：共享 store 变更后摘要数量随之变化（不重新请求）
    const store = useCategoriesStore()
    store.categories = [
      ...REORDER_CATEGORIES.map((c) => ({ ...c })),
      { id: 11, name: '娱乐', type: 'expense', icon: 'mdi-gamepad' },
    ]
    await nextTick()
    expect(wrapper.text()).toContain('7 个分类')
    expect(getCategories).toHaveBeenCalledTimes(1)
  })
})

// ── v1.4.3 M6 二级页面内部间距疏朗化（需求六 / D10 全局口径）───────────────
// 手法：jsdom 无布局引擎，间距值不可测 → 按 §1.2 约定用 ?raw / 样式表原文源码断言
//      （vitest 不处理 CSS，global.scss 的 ?raw 为空串 → 沿用 readGlobalStyles 直读原文）
const M6_SECTION_START = 'v1.4.3 M6 二级页面内部间距疏朗化'

// 截出 M6 段落（自段落标题注释起、至下一段 `.entry-avatar` 注释前）并剥除注释，
// 供区间内规则结构与「纯间距零色彩」断言使用
function m6StylesSegment(styles) {
  const start = styles.indexOf(M6_SECTION_START)
  if (start < 0) throw new Error('未找到 M6 疏朗化段落（global.scss）')
  const end = styles.indexOf('入口头像统一底色', start)
  if (end < 0) throw new Error('M6 段落结束锚点未找到')
  return styles.slice(start, end).replace(/\/\*[\s\S]*?\*\//g, '')
}

describe('v1.4.3 M6 二级页面间距疏朗化', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(reorderCopy())
    getTags.mockResolvedValue(TAGS.map((t) => ({ ...t })))
    useSlicedPagedMock(TAGS)
    getQuickTemplates.mockResolvedValue(TEMPLATES.map((t) => ({ ...t })))
  })

  // 任务 §4.1（+ §1.1/§1.2/§1.3/§1.4）
  it('用例M6-1: global.scss D10 量化口径齐备（20px 内衬 / 行 48+4 / 标题 8·12 / 块间 20）', () => {
    const styles = readGlobalStyles()
    // §1.1 卡片内衬 16px → 20px
    expect(styles).toMatch(/\.page-card \{[^}]*padding: 20px/)
    // §1.2 行高下限 + 行间垂直间距（同一规则块内成对出现）
    expect(styles).toMatch(
      /\.page-card \.v-list-item \{[^}]*min-height: 48px[^}]*margin-block: 4px/
    )
    // §1.3 列表自带 8px 上下内衬归零（卡壳已有 20px，避免双重留白）
    expect(styles).toMatch(/\.page-card \.v-list \{[^}]*padding: 0/)
    // §1.4 新区块标题类 + 区块间距类（M8 分类页已挂用的类名至此「有类名亦有规则」）
    expect(styles).toMatch(/\.section-title \{[^}]*margin: 8px 0 12px/)
    expect(styles).toMatch(
      /\.section-block \+ \.section-block \{[^}]*margin-top: 20px/
    )
    // 挂用类名的两页文案标题（分类页由 M8 落，标签/模板页由 M6 落）
    expect(categoriesPageSource).toMatch(/class="section-title[^"]*">全部分类/)

    // §1.6 作用域自检：行高/行间距只在 .page-card 之内，
    // 设置主页等未挂 .page-card 的列表不被全局规则命中（无裸 .v-list-item 全局覆写）
    const section = m6StylesSegment(styles)
    // 结构性口径：段内所有设 min-height / margin-block 的规则，选择器一律带 .page-card 前缀
    // （裸 .v-list-item 全局覆写会波及未挂 .page-card 的列表，必须为零）
    const rules = [...section.matchAll(/([^{}]*)\{([^}]*)\}/g)].map(([, sel, body]) => ({
      sel: sel.trim(),
      body,
    }))
    expect(rules.length).toBeGreaterThanOrEqual(4)
    rules
      .filter((r) => /min-height|margin-block/.test(r.body))
      .forEach((r) => expect(r.sel, `越界作用域规则：${r.sel}`).toMatch(/^\.page-card \.v-list-item$/))
    expect(rules.some((r) => r.sel === '.section-title')).toBe(true)
    expect(rules.some((r) => r.sel === '.section-block + .section-block')).toBe(true)
    // 设置主页卡片确实未挂 .page-card → 规则天然不作用于它
    expect(settingsPageSource).not.toContain('class="page-card"')
    expect(styles).not.toMatch(/\.settings-card[^{]*\{[^}]*min-height/)

    // §3.2 深色模式零风险自检：本段落纯间距，零色彩/零阴影声明
    expect(section).not.toMatch(/(^|\s)(color|background|box-shadow|border)\s*:/)
  })

  // 任务 §4.2（+ §2.3）
  it('用例M6-2: 数据回溯主体列表统一改挂 .page-card，裸 v-card 写法消除', () => {
    // 统一容器落地：v-else 分支条件移至 div，内部 v-list 原样保留
    expect(historyPageSource).toMatch(/<div v-else class="page-card">\s*<v-list class="pa-0">/)
    // 改版前写法字面量不再出现（需求六 3「去除裸 v-card 写法」）
    expect(historyPageSource).not.toContain('<v-card v-else rounded="xl" class="mb-4">')
    expect(historyPageSource).not.toMatch(/<v-card\b[^>]*v-else/)
    // 空态分支（v1.4.2 M4 已包卡）零改动
    expect(historyPageSource).toMatch(/<div v-else-if="items\.length === 0" class="page-card text-center">/)
    // §3.1 边界自检：卡壳内不再自带压缩行高覆写（48px 为下限，不压缩既有高度）
    expect(historyPageSource).not.toMatch(/\.detail-record-item \{[^}]*min-height/)
  })

  // 任务 §4.3（+ §2.1/§2.2）
  it('用例M6-3: 标签页 / 快速记账页挂用 section-block + section-title，模板列表去 compact', () => {
    for (const [name, source] of [
      ['标签页', tagsPageSource],
      ['快速记账页', quickTemplatesPageSource],
    ]) {
      const card = splitByPageCard(source).card
      // 区块标题 + 单块容器成对挂在卡壳之内（与分类页 M8 落地写法同款）
      expect(card, `${name} 未挂 section-block`).toContain('<div class="section-block">')
      expect(card, `${name} 未挂 section-title`).toMatch(
        /<div class="section-title text-caption text-grey font-weight-medium">[^<]+<\/div>/
      )
    }
    expect(tagsPageSource).toContain('>全部标签<')
    expect(quickTemplatesPageSource).toContain('>全部模板<')
    // §2.2 行高由全局 min-height 48px 托底 → 模板列表不再声明 compact
    expect(quickTemplatesPageSource).not.toMatch(/density="compact"/)
    // 标签页主体为 chip 云，无列表行可施 min-height（分页展开区归 M5 结构，不入本次断言）
    expect(tagsPageSource).not.toMatch(/<v-list\b/)
    // 三页页头提示文案与操作按钮未动（疏朗化只改间距不改语义）
    expect(tagsPageSource).toContain('管理标签，点击标签右侧 × 可删除')
    expect(quickTemplatesPageSource).toContain('常用标签与金额，记一笔时快捷使用')
  })

  // M6 对 M8 已落分类页的口径对齐：页内不再以同特异性 margin 覆写全局行间 4px
  it('用例M6-3b: 分类页行间距由全局口径承载（页内窄间距覆写已消除）', () => {
    expect(categoriesPageSource).toMatch(/<div class="section-block">/)
    expect(categoriesPageSource).not.toMatch(/\.category-list-item \{[^}]*margin:/)
    // 卡壳唯一、区块唯一（四页节奏一致）
    expect(categoriesPageSource.match(/class="page-card"/g)).toHaveLength(1)
    expect(splitByPageCard(categoriesPageSource).card.match(/class="section-block"/g)).toHaveLength(1)
  })

  // 渲染快照：两页标题节点落在 .page-card 内且在列表之前
  it('用例M6-4: 标签/模板页挂载后 .page-card 内渲染 .section-title 且先于内容', async () => {
    const tags = await mountPage(SettingsTagsPage)
    const tagsCard = tags.find('.page-card')
    expect(tagsCard.exists()).toBe(true)
    const tagsTitle = tagsCard.find('.section-title')
    expect(tagsTitle.text()).toBe('全部标签')
    // 标题在 chip 云之前（DOM 序）
    const tagsHtml = tagsCard.html()
    expect(tagsHtml.indexOf('全部标签')).toBeLessThan(tagsHtml.indexOf('日常'))
    expect(tagsHtml).toContain('section-block')

    const templates = await mountPage(SettingsQuickTemplatesPage)
    const tplCard = templates.find('.page-card')
    const tplTitle = tplCard.find('.section-title')
    expect(tplTitle.text()).toBe('全部模板')
    const tplHtml = tplCard.html()
    expect(tplHtml.indexOf('全部模板')).toBeLessThan(tplHtml.indexOf('日常 · ¥25'))
    expect(tplHtml).toContain('section-block')

    // 空态不渲染标题之外的旧写法残留：两页卡壳仍恰一处（未重复定义容器）
    expect(tagsHtml.match(/class="page-card"/g)).toHaveLength(1)
    expect(tplHtml.match(/class="page-card"/g)).toHaveLength(1)
  })
})

// ── v1.4.3 M9 分类拖拽排序 flip 让位动画（需求九 / D10 animation:180 独立口径）──
// 总 prompt §7.3 裁定：只断言 Draggable 的 animation 配置，jsdom 不真实驱动 sortable；
// 让位平滑度与落点观感属真机项（任务 §4.2/§4.3）。
describe('v1.4.3 M9 分类拖拽 flip 让位动画', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(reorderCopy())
    reorderCategories.mockResolvedValue(reorderCopy())
    getTags.mockResolvedValue([])
    useSlicedPagedMock([])
    getQuickTemplates.mockResolvedValue([])
  })

  // 任务 §3.1（设计 §9.4）+ §1.1
  it('用例M9-1: 单列表唯一 Draggable 实例显式配置 animation = 180', async () => {
    const wrapper = await mountReorderPage()
    const draggables = wrapper.findAllComponents(Draggable)

    // M8 单列表：承载 flip 动画的 Draggable 实例唯一（无第二列表各自为政）
    expect(draggables).toHaveLength(1)
    const draggable = draggables[0]

    // 设计 §9.4 的 animation=180 口径落点：vuedraggable@4.1.0 声明面只有
    // list/modelValue/itemKey/clone/tag/move/componentData，animation 属非声明属性 →
    // 实测落 $attrs 并由其透传给 Sortable（props() 内无该键，见下一行快照红线）。
    // 故按本文件 M3 用例2b 既定的 sortableOptionsOf（kebab → camel）归一口径断言。
    expect(draggable.vm.$attrs.animation).toBe(180)
    expect(sortableOptionsOf(draggable).animation).toBe(180)
    // 数值口径（非字符串 "180"）：sortablejs 以 ms 数值消费
    expect(typeof sortableOptionsOf(draggable).animation).toBe('number')
    // 上游若改为声明式 prop，本条即变 → 需同批改上面两条断言（防静默漂移）
    expect(draggable.props()).not.toHaveProperty('animation')
  })

  // 任务 §1.1 D10 独立口径 + §1.2 其余参数零改动
  it('用例M9-2: animation 以字面量 180 挂在单一列表；其余拖拽参数维持 v1.4.2 值', async () => {
    const wrapper = await mountReorderPage()
    const draggable = wrapper.findAllComponents(Draggable)[0]
    const options = sortableOptionsOf(draggable)

    // 源码级：显式绑定字面量 180（150–200 区间），且为 D10 独立口径 ——
    // animation 只吃数值字面量，不复用展开类动画的时长变量（两处口径互不牵扯）
    expect(categoriesPageSource).not.toMatch(/:animation="[^"]*var\(/)
    // animation 只此一处（无第二列表 / 无重复绑定）；限定属性位，避开页内 M9 说明注释的字面量
    expect(categoriesPageSource.match(/\n\s+:animation="180"/g)).toHaveLength(1)

    // §1.2 红线：v1.4.2 既有拖拽参数一字不改
    expect(options.handle).toBe('.drag-handle')
    expect(options.delay).toBe(150)
    expect(options.delayOnTouchOnly).toBe(true)
    expect(options.touchStartThreshold).toBe(5)
    expect(options.ghostClass).toBe('drag-ghost')
    expect(options.dragClass).toBe('drag-float')
    // 把手 touch-action 仍只在把手上（拖动可行走、列表滚动不被杀死 —— 真机项 2.1 的前置）
    expect(categoriesPageSource).toMatch(/\.drag-handle \{[^}]*touch-action: none/)
    expect(categoriesPageSource).not.toMatch(/\.category-list-item \{[^}]*touch-action/)
  })

  // 任务 §1.3 + §3.2：正常路径零闪回、保存链路零改动
  it('用例M9-3: 正常落位不触发本地归一化（零闪回），保存仍为单次 PUT + 唯一 toast', async () => {
    const wrapper = await mountReorderPage()
    const list = wrapper.vm.dragList

    wrapper.vm.onDragStart()
    // 交换首两行、「其他」恒末位 → 归一化条件不成立
    const dropped = [list[1], list[0], ...list.slice(2)]
    wrapper.vm.dragList = dropped
    const droppedIds = dropped.map((c) => c.id)
    wrapper.vm.onDragEnd()
    // 零闪回（同步即可判）：onDragEnd 未写回归一化列表，落点即视觉落点、行数不变
    expect(wrapper.vm.dragList.map((c) => c.id)).toEqual(droppedIds)
    expect(wrapper.vm.dragList).toHaveLength(6)
    await flushPromises()

    // 单次 PUT（全量 ids）+ 全流程唯一 toast：动画不新增请求、不改回滚链路
    expect(reorderCategories).toHaveBeenCalledTimes(1)
    expect(reorderCategories).toHaveBeenCalledWith({ ids: [2, 1, 3, 9, 10, 8] })
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('排序已保存')
  })
})

// ── v1.4.3 M5 导入导出改为设置二级页面（需求五 / 设计 §五） ──────────────────
// 任务 §5.1~§5.3：功能整体从设置页内联卡平移而来（组件复用、业务不重写），
// 故本组既锁「新页四功能行为不变」，也锁「设置主页零残留」（防双份状态）。
describe('v1.4.3 M5 导入导出二级页', () => {
  // blob 下载与 file input / anchor click 的浏览器侧行为在 jsdom 缺失，按任务 §5.1 桩替
  let downloads
  let inputClicks

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
    getTags.mockResolvedValue(TAGS.map((t) => ({ ...t })))
    getQuickTemplates.mockResolvedValue(TEMPLATES.map((t) => ({ ...t })))

    downloads = []
    inputClicks = []
    URL.createObjectURL = vi.fn(() => 'blob:mock-object-url')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(window.HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      downloads.push({ download: this.download, href: String(this.href) })
    })
    vi.spyOn(window.HTMLInputElement.prototype, 'click').mockImplementation(function () {
      inputClicks.push(this.getAttribute('accept'))
    })

    exportCsv.mockResolvedValue({ __blob: 'csv' })
    exportSql.mockResolvedValue({ __blob: 'sql' })
    previewCsvImport.mockResolvedValue({})
    importCsv.mockResolvedValue({ imported_count: 0 })
    previewSqlImport.mockResolvedValue({})
    importSql.mockResolvedValue({ records_imported: 0 })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete URL.createObjectURL
    delete URL.revokeObjectURL
  })

  const rowByTitle = (wrapper, title) =>
    wrapper.findAll('v-list-item').find((node) => node.text().includes(title))

  const csvPreviewFixture = () => ({
    cache_id: 'csv-cache-1',
    format: 'native',
    row_count: 3,
    categories_in_file: ['餐饮', '未知类'],
    tags_in_file: [],
  })

  const sqlPreviewFixture = (overrides = {}) => ({
    cache_id: 'sql-cache-1',
    format: 'sqlite_binary',
    is_third_party: true,
    tables: { records: { count: 5 }, categories: { count: 3 } },
    categories_in_file: ['餐饮'],
    tags_in_file: [],
    ...overrides,
  })

  // 任务 §5.1（导出 CSV/SQL → exportCsv/exportSql + blob 下载）+ §2.4（文件名口径不变）
  it('用例M5-1: 导出 CSV/SQL 调用 @/api/export 并触发 blob 下载，文件名与 toast 不变', async () => {
    const wrapper = await mountPage(SettingsImportExportPage)

    await rowByTitle(wrapper, '导出 CSV').trigger('click')
    await flushPromises()

    expect(exportCsv).toHaveBeenCalledTimes(1)
    expect(URL.createObjectURL).toHaveBeenCalledWith({ __blob: 'csv' })
    expect(downloads).toHaveLength(1)
    expect(downloads[0].download).toMatch(/^money_export_\d{8}\.csv$/)
    expect(downloads[0].href).toContain('blob:')
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('CSV 导出成功')
    expect(wrapper.vm.exporting).toBe(false)

    await rowByTitle(wrapper, '导出 SQL').trigger('click')
    await flushPromises()

    expect(exportSql).toHaveBeenCalledTimes(1)
    expect(downloads).toHaveLength(2)
    expect(downloads[1].download).toMatch(/^money_backup_\d{8}\.sql$/)
    expect(mockShowToast).toHaveBeenLastCalledWith('SQL 导出成功')
    expect(wrapper.vm.exporting).toBe(false)
  })

  // 设计 §5.3：导出失败口径与迁移前一致（错误 toast + exporting 复位，不卡死入口）
  it('用例M5-2: 导出失败 → 错误 toast、exporting 复位、未触发下载', async () => {
    exportCsv.mockRejectedValueOnce(new Error('服务不可用'))
    const wrapper = await mountPage(SettingsImportExportPage)

    await rowByTitle(wrapper, '导出 CSV').trigger('click')
    await flushPromises()

    expect(mockShowToast).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith('服务不可用', 'error')
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    expect(downloads).toHaveLength(0)
    expect(wrapper.vm.exporting).toBe(false)
  })

  // 任务 §5.1（导入 CSV：点击触发隐藏 input → 预览 → CsvMappingDialog confirm 走 importCsv）
  it('用例M5-3: 导入 CSV 触发隐藏 input、change 走预览并打开映射弹窗，confirm 提交 importCsv', async () => {
    const wrapper = await mountPage(SettingsImportExportPage)

    // 两个隐藏 file input（accept 与迁移前一致），初始不显示
    const inputs = wrapper.findAll('input[type="file"]')
    expect(inputs).toHaveLength(2)
    expect(inputs[0].attributes('accept')).toBe('.csv')
    expect(inputs[1].attributes('accept')).toBe('.sql,.db')

    await rowByTitle(wrapper, '导入 CSV').trigger('click')
    expect(inputClicks).toEqual(['.csv'])

    previewCsvImport.mockResolvedValueOnce(csvPreviewFixture())
    const file = new window.File(['a,b\n1,2'], 'records.csv', { type: 'text/csv' })
    Object.defineProperty(inputs[0].element, 'files', { value: [file], configurable: true })
    await inputs[0].trigger('change')
    await flushPromises()

    expect(previewCsvImport).toHaveBeenCalledTimes(1)
    expect(previewCsvImport).toHaveBeenCalledWith(file)
    // 原样平移的 reset 逻辑：读文件后清空 value，允许重复选同一文件
    expect(inputs[0].element.value).toBe('')
    expect(wrapper.vm.showCsvMapping).toBe(true)
    expect(wrapper.vm.csvPreviewData.cache_id).toBe('csv-cache-1')

    // CSV 映射弹窗（第一个实例）拿预览数据与 store 分类
    const dialogs = wrapper.findAllComponents(CsvMappingDialog)
    expect(dialogs).toHaveLength(2)
    const csvDialog = dialogs[0]
    expect(csvDialog.props('modelValue')).toBe(true)
    expect(csvDialog.props('previewData')).toMatchObject({ cache_id: 'csv-cache-1', row_count: 3 })
    expect(csvDialog.props('categories').map((c) => c.name)).toEqual(['餐饮', '出行', '购物', '工资'])

    importCsv.mockResolvedValueOnce({ imported_count: 3 })
    csvDialog.vm.$emit('confirm', {
      category_mapping: { 未知类: { action: 'map', target_id: 3 } },
      tag_mapping: {},
    })
    await flushPromises()

    expect(importCsv).toHaveBeenCalledWith({
      cache_id: 'csv-cache-1',
      format: 'native',
      category_mapping: { 未知类: { action: 'map', target_id: 3 } },
      tag_mapping: {},
    })
    expect(mockShowToast).toHaveBeenCalledWith('成功导入 3 条记录')
    expect(wrapper.vm.showCsvMapping).toBe(false)
    expect(wrapper.vm.csvPreviewData).toBe(null)
    expect(wrapper.vm.importing).toBe(false)
  })

  // CSV 预览失败：错误 toast 且不弹映射框（行为与迁移前一致）
  it('用例M5-3b: CSV 预览失败 → 错误 toast、映射弹窗不打开', async () => {
    previewCsvImport.mockRejectedValueOnce(new Error('文件格式不支持'))
    const wrapper = await mountPage(SettingsImportExportPage)

    await wrapper.vm.handleCsvFileSelect({
      target: { files: [new window.File(['x'], 'bad.csv')], value: 'C:\\fakepath\\bad.csv' },
    })
    await flushPromises()

    expect(mockShowToast).toHaveBeenCalledWith('文件格式不支持', 'error')
    expect(wrapper.vm.showCsvMapping).toBe(false)
    expect(wrapper.findAllComponents(CsvMappingDialog)[0].props('modelValue')).toBe(false)
  })

  // 任务 §2.3/§5.1（SQL 两段式：确认弹窗 → 映射弹窗 → importSql）
  it('用例M5-4: 导入 SQL 先出确认弹窗（格式/来源/预览计数），下一步进映射并成功导入', async () => {
    const wrapper = await mountPage(SettingsImportExportPage)

    await rowByTitle(wrapper, '导入 SQL').trigger('click')
    expect(inputClicks).toEqual(['.sql,.db'])

    previewSqlImport.mockResolvedValueOnce(sqlPreviewFixture())
    const sqlInput = wrapper.findAll('input[type="file"]')[1]
    const file = new window.File(['--'], 'backup.sqlite')
    Object.defineProperty(sqlInput.element, 'files', { value: [file], configurable: true })
    await sqlInput.trigger('change')
    await flushPromises()

    expect(previewSqlImport).toHaveBeenCalledWith(file)
    expect(sqlInput.element.value).toBe('')
    expect(wrapper.vm.showSqlConfirm).toBe(true)
    expect(wrapper.vm.sqlCacheId).toBe('sql-cache-1')
    expect(wrapper.vm.sqlFormat).toBe('sqlite_binary')
    // 确认弹窗文案：SQLite 二进制 / 第三方来源 / 逐表计数（原样平移）
    const text = wrapper.text()
    expect(text).toContain('文件格式：SQLite 数据库')
    expect(text).toContain('数据来源：Cashew（第三方）')
    expect(text).toContain('records：5 条')
    expect(text).toContain('categories：3 条')

    const nextBtn = wrapper.findAll('v-btn').find((node) => node.text() === '下一步')
    expect(nextBtn, 'SQL 确认弹窗「下一步」未渲染').toBeTruthy()
    await nextBtn.trigger('click')
    await flushPromises()

    expect(wrapper.vm.showSqlConfirm).toBe(false)
    expect(wrapper.vm.showSqlMapping).toBe(true)

    importSql.mockResolvedValueOnce({ records_imported: 5 })
    wrapper.findAllComponents(CsvMappingDialog)[1].vm.$emit('confirm', {
      category_mapping: { 餐饮: { action: 'map', target_id: 1 } },
      tag_mapping: {},
    })
    await flushPromises()

    expect(importSql).toHaveBeenCalledWith({
      cache_id: 'sql-cache-1',
      format: 'sqlite_binary',
      is_third_party: true,
      category_mapping: { 餐饮: { action: 'map', target_id: 1 } },
      tag_mapping: {},
    })
    expect(mockShowToast).toHaveBeenCalledWith('成功导入 5 条记录')
    expect(wrapper.vm.showSqlMapping).toBe(false)
    expect(wrapper.vm.sqlPreviewData).toBe(null)
    expect(wrapper.vm.sqlCacheId).toBe(null)
    expect(wrapper.vm.sqlFormat).toBe(null)
    expect(wrapper.vm.importing).toBe(false)
  })

  // 设计 §5.2：文件内无待映射分类/标签 → 下一步直接导入（mapping 传 null）
  it('用例M5-4b: SQL 无需映射时「下一步」直接导入，category/tag_mapping 为 null', async () => {
    const wrapper = await mountPage(SettingsImportExportPage)
    // 文件内无 categories_in_file / tags_in_file → 无需映射，「下一步」直入 importSql
    previewSqlImport.mockResolvedValueOnce(
      sqlPreviewFixture({
        format: 'text_sql',
        is_third_party: false,
        categories_in_file: [],
        tags_in_file: [],
      })
    )
    await wrapper.vm.handleSqlFileSelect({
      target: {
        files: [new window.File(['sql'], 'backup.sql')],
        value: 'C:\\fakepath\\backup.sql',
      },
    })
    await flushPromises()
    expect(wrapper.vm.showSqlConfirm).toBe(true)
    expect(wrapper.vm.sqlFormat).toBe('text_sql')

    importSql.mockResolvedValueOnce({ records_imported: 2 })
    wrapper.vm.handleSqlNext()
    await flushPromises()

    expect(wrapper.vm.showSqlMapping).toBe(false)
    expect(importSql).toHaveBeenCalledTimes(1)
    expect(importSql).toHaveBeenCalledWith({
      cache_id: 'sql-cache-1',
      format: 'text_sql',
      is_third_party: false,
      category_mapping: null,
      tag_mapping: null,
    })
    expect(mockShowToast).toHaveBeenCalledWith('成功导入 2 条记录')
  })

  // 任务 §2.1/§2.2（页头同款 + 主体唯一 .page-card + 四行与 v-divider 排布原样）
  it('用例M5-5: 页头返回与说明文案在卡外，四行与 v-divider 整体迁入唯一 .page-card', async () => {
    const { card, outside } = splitByPageCard(importExportPageSource)
    // §2.1 页头：返回箭头 + $router.back() + text-caption text-grey 说明（参考 HistoryPage 结构）
    expect(outside).toContain('mdi-arrow-left')
    expect(outside).toContain('$router.back()')
    expect(outside).toContain('导出账单或从备份恢复')
    // 每页恰一个卡壳（容器复用不重复定义，自动继承 M6 疏朗化口径）
    expect(importExportPageSource.match(/class="page-card"/g)).toHaveLength(1)
    // §2.2 CSV/SQL 两组现有排布原样迁移：4 行 + 中间一条 v-divider 分组
    // （正则排除 v-list-item-title/subtitle 前缀连带命中）
    expect(card.match(/<v-list-item(?![\w-])/g)).toHaveLength(4)
    expect(card.match(/<v-divider class="my-1" \/>/g)).toHaveLength(1)
    ;['导出 CSV', '导入 CSV', '导出 SQL', '导入 SQL'].forEach((t) => expect(card).toContain(t))
    ;[
      '导出账单为 CSV 文件',
      '从 CSV 文件导入账单',
      '导出全量数据为 SQL 备份',
      '从 SQL/SQLite 文件导入数据',
    ].forEach((s) => expect(card).toContain(s))
    ;[
      'mdi-file-delimited-outline',
      'mdi-file-import-outline',
      'mdi-database-export-outline',
      'mdi-database-import-outline',
    ].forEach((i) => expect(card).toContain(i))
    // 卡壳之外无页面级透明列表（M4 口径）
    expect(outside).not.toContain('bg-transparent')

    // 渲染快照：返回按钮为页头首个 v-btn，点击走 $router.back()（与其他二级页一致）
    const wrapper = await mountPage(SettingsImportExportPage)
    expect(wrapper.findAll('.page-card')).toHaveLength(1)
    const cardNode = wrapper.find('.page-card')
    ;['导出 CSV', '导入 CSV', '导出 SQL', '导入 SQL'].forEach((t) =>
      expect(cardNode.text()).toContain(t)
    )
    await wrapper.findAll('v-btn')[0].trigger('click')
    expect(mockBack).toHaveBeenCalledTimes(1)
  })

  // 任务 §2.4（剪切非复制）+ §3.3 红线 + §5.2
  it('用例M5-6: 状态与函数完整平移，SettingsPage 零残留且含 import-export 入口', () => {
    const moved = [
      // 状态
      'exporting',
      'importing',
      'csvFileInput',
      'sqlFileInput',
      'showCsvMapping',
      'csvPreviewData',
      'showSqlConfirm',
      'showSqlMapping',
      'sqlPreviewData',
      'sqlCacheId',
      'sqlFormat',
      // 函数
      'downloadBlob',
      'handleExportCsv',
      'handleExportSql',
      'triggerCsvImport',
      'handleCsvFileSelect',
      'handleCsvImport',
      'triggerSqlImport',
      'handleSqlFileSelect',
      'handleSqlNext',
      'handleSqlImport',
      // 依赖与模板骨架
      'CsvMappingDialog',
      '@/api/export',
      'exportCsv',
      'exportSql',
      'previewCsvImport',
      'importCsv',
      'previewSqlImport',
      'importSql',
      'dayjs',
      'type="file"',
      '确认导入 SQL',
      '导入模式：合并（放弃原始 ID，重新分配）',
    ]
    moved.forEach((id) => expect(importExportPageSource, `新页缺「${id}」`).toContain(id))
    // 新页自身仍是 api/export 唯一消费方（toast 走 appStore.showToast，与设计 §5.2.2 一致）
    expect(importExportPageSource).toContain("from '@/api/export'")
    expect(importExportPageSource).toContain('appStore.showToast')
    // 四行文案的唯一副本：新页有、设置页无（防双份状态残留）
    moved.forEach((id) => expect(settingsPageSource, `SettingsPage 残留「${id}」`).not.toContain(id))
    // 任务 §5.2 三条 ?raw 断言
    expect(settingsPageSource).not.toContain('CsvMappingDialog')
    expect(settingsPageSource).not.toMatch(/<input[^>]*type="file"/)
    expect(settingsPageSource).toContain('to="/settings/import-export"')
    // 任务 §3.3 红线字面量（csvMapping|sqlPreview|exportCsv）大小写两型皆零命中
    expect(settingsPageSource).not.toMatch(/csvMapping|sqlPreview|exportCsv/i)
  })

  // 任务 §5.3（路由表用例，:710 风格）+ §4.2 直达 URL 走全局守卫
  it('用例M5-7: /settings/import-export 路由存在、懒加载、meta.title 正确且非 public', async () => {
    const expected = [['/settings/import-export', 'SettingsImportExport', '导入导出']]
    const byPath = {}
    router.getRoutes().forEach((r) => {
      byPath[r.path] = r
    })

    for (const [path, name, title] of expected) {
      const route = byPath[path]
      expect(route, `缺少路由 ${path}`).toBeTruthy()
      expect(route.name).toBe(name)
      expect(route.meta.title).toBe(title)
      expect(typeof route.components.default).toBe('function')
      const mod = await route.components.default()
      expect(mod.default).toBeTruthy()
      expect(route.meta.public).toBeFalsy()
    }
    // 追加位置口径（任务 §1.1）：quick-templates 之后、/history 之前
    // （M1 随后在本文件只改 Dashboard 的 meta.title，不动本区块）
    expect(routerSource).toMatch(
      /\/settings\/quick-templates[\s\S]*?\/settings\/import-export[\s\S]*?path: '\/history'/
    )
  })

  // 任务 §4.1/§4.2 边界：直达本页补拉分类（映射弹窗候选）；中途返回卸载不炸
  it('用例M5-8: 直达本页时补拉分类供映射候选，store 已加载则不重复请求；卸载后回调不触达', async () => {
    const store = useCategoriesStore()
    expect(store.loaded).toBe(false)

    const wrapper = await mountPage(SettingsImportExportPage)
    await flushPromises()
    expect(getCategories).toHaveBeenCalledTimes(1)
    expect(wrapper.findAllComponents(CsvMappingDialog)[0].props('categories')).toHaveLength(4)

    // store 已 loaded（从设置页进入的常态）→ 不再新增请求
    const store2 = useCategoriesStore()
    store2.loaded = true
    const again = await mountPage(SettingsImportExportPage)
    await flushPromises()
    expect(getCategories).toHaveBeenCalledTimes(1)
    expect(again.vm.csvFileInput).toBeTruthy()

    // 导入进行中返回设置页：页面卸载，后续回调仅写入已卸载实例（无 DOM 崩溃、无多余 toast）
    let resolvePreview
    previewCsvImport.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePreview = resolve
      })
    )
    const pending = await mountPage(SettingsImportExportPage)
    const input = pending.findAll('input[type="file"]')[0]
    Object.defineProperty(input.element, 'files', {
      value: [new window.File(['a'], 'x.csv')],
      configurable: true,
    })
    await input.trigger('change')
    pending.unmount()
    resolvePreview(csvPreviewFixture())
    await flushPromises()

    expect(pending.vm.showCsvMapping).toBe(true) // 状态写在已卸载实例上，不影响全局
    expect(mockShowToast).not.toHaveBeenCalled()
  })
})

// ── v1.4.3 M7 设置页账号区用户行头像缩进对齐（需求七 / 设计 §七）────────────
// 手法：jsdom 无布局引擎，44px 缩进数学不可测 → 按 §1.2 约定用 SettingsPage.vue ?raw 源码断言
describe('v1.4.3 M7 账号区用户行头像缩进对齐', () => {
  // 任务 §3.1：含 .account-user-row 类定义 + 模板用户行绑定该类 + 样式含 padding-left: 44px
  it('用例M7-1: scoped 样式定义 .account-user-row{padding-left:44px}，登录/未登录两分支用户行同挂该类', () => {
    // §1.1 类定义在 <style scoped> 内，缩进值为定值 px（§2.1 宽屏卡片变宽节奏不变）
    const styleBlock = settingsPageSource.slice(settingsPageSource.indexOf('<style scoped>'))
    expect(styleBlock).toMatch(/\.account-user-row\s*\{[^}]*padding-left:\s*44px[^}]*\}/)
    // §1.2 登录分支：挂类且原布局类序完整（justify-space-between 保持行右缘对齐，§1.4）
    expect(settingsPageSource).toMatch(
      /<div v-if="isLoggedIn" class="account-user-row d-flex align-center justify-space-between mt-2">/
    )
    // §1.3 未登录分支（「去登录」行）同挂该类，两分支缩进一致
    expect(settingsPageSource).toMatch(/<div v-else class="account-user-row mt-2">/)
    // 模板内该类仅账号区两分支挂载（登录 + 未登录 = 恰 2 处），不波及其他区块
    expect(settingsPageSource.match(/class="account-user-row/g)).toHaveLength(2)
    // §1.4 头像本身尺寸/配色不动（首字母头像仍为 36px primary，与标题行头像同径）
    expect(settingsPageSource).toMatch(/<v-avatar size="36" color="primary" class="mr-2">/)
  })
})

// ── v1.4.3 M13 分类图标选择改独立居中弹窗（需求十三 / 设计 §十三）──────────────
// 手法：分类表单挂载真实 CategoryIconPicker，只桩 v-dialog 以便分辨「外层分类对话框」与
// 「组件自带居中弹窗」两层；jsdom 无布局 → 尺寸/网格口径另走 ?raw 源码锁（§1.2 既定手法）。
describe('v1.4.3 M13 分类图标选择独立居中弹窗', () => {
  // 声明 fullscreen prop：组件不传时桩上读到 false，用于「非全屏」侧证
  const DialogStub = {
    name: 'VDialog',
    props: { modelValue: Boolean, fullscreen: Boolean, maxWidth: String, transition: String },
    emits: ['update:modelValue'],
    template:
      '<div class="m13-dialog-stub" :data-fullscreen="String(fullscreen)" :data-max-width="String(maxWidth)">' +
      '<div v-if="modelValue" class="m13-dialog-content"><slot /></div></div>',
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    getCategories.mockResolvedValue(CATEGORIES.map((c) => ({ ...c })))
  })

  async function mountCategories() {
    const wrapper = mount(SettingsCategoriesPage, {
      global: {
        mocks: { $router: { push: mockPush, back: mockBack } },
        stubs: { 'v-dialog': DialogStub, VDialog: DialogStub },
      },
    })
    await flushPromises()
    wrapper.vm.showCategoryDialog = true
    await nextTick()
    return wrapper
  }

  function outerDialog(wrapper) {
    return wrapper.findAllComponents(DialogStub).find((d) => d.props('maxWidth') === '400')
  }

  // ---------- 任务 4.3 / 2.1：居中弹窗形态（宽屏两档同一路径） ----------

  for (const width of [1280, 375]) {
    it(`用例M13-1(${width}px): 图标网格落在组件自带居中弹窗，外层分类对话框无内联展开区`, async () => {
      Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: width })
      const wrapper = await mountCategories()
      const picker = wrapper.findComponent(CategoryIconPicker)
      expect(picker.exists()).toBe(true)
      expect(picker.props('modelValue')).toBe('mdi-cash')

      const outer = outerDialog(wrapper)
      expect(outer).toBeTruthy()
      // 未点 activator：全页无网格（v1.4.2 宽屏内联展开分支已删 → 外层不再被撑大）
      expect(wrapper.findAll('.icon-grid')).toHaveLength(0)
      expect(wrapper.findAll('.icon-panel')).toHaveLength(0)

      await picker.find('.icon-activator').trigger('click')

      // 组件内恰一份弹窗、非全屏、裁定宽度口径 92vw、初版过渡 dialog-bottom-transition
      const inner = picker.findAllComponents(DialogStub)
      expect(inner).toHaveLength(1)
      expect(inner[0].props('fullscreen')).toBe(false)
      expect(inner[0].element.getAttribute('data-fullscreen')).toBe('false')
      expect(inner[0].props('maxWidth')).toBe('min(560px, 92vw)')
      expect(inner[0].props('transition')).toBe('dialog-bottom-transition')
      expect(inner[0].props('modelValue')).toBe(true)

      // 全量精选图标落在这一层弹窗里；内联展开区两档均零命中
      const cells = inner[0].findAll('.icon-cell')
      expect(cells).toHaveLength(CATEGORY_ICONS.length)
      expect(inner[0].find('.icon-dialog__preview-name').text()).toBe('mdi-cash')
      expect(wrapper.findAll('.icon-panel')).toHaveLength(0)
      // 外层分类对话框自身尺寸口径不受图标弹窗开合影响（撑出现象根因消除）
      expect(outer.props('maxWidth')).toBe('400')
      expect(outer.props('modelValue')).toBe(true)
      // 网格归属组件自己的弹窗层，而非外层对话框内的直接展开区
      const gridHost = outer.find('.icon-grid').element.closest('.m13-dialog-content')
      expect(gridHost).toBe(inner[0].find('.m13-dialog-content').element)
      expect(outer.findAll('.icon-panel')).toHaveLength(0)
      delete window.innerWidth
    })
  }

  // ---------- 任务 3.1 / 3.2：单段式点选 + 关闭不再回抛 ----------

  it('用例M13-2: 点选即回抛 v-model 供表单实时预览，「完成」仅收起内层弹窗', async () => {
    const wrapper = await mountCategories()
    const picker = wrapper.findComponent(CategoryIconPicker)
    await picker.find('.icon-activator').trigger('click')

    const target = CATEGORY_ICONS[4]
    await picker.findAll('.icon-cell').find((c) => c.attributes('title') === target).trigger('click')
    // 调用方零改动：仍靠 update:modelValue 单向回填 categoryForm.icon
    expect(wrapper.vm.categoryForm.icon).toBe(target)
    expect(picker.find('.icon-activator__name').text()).toBe(target)
    // 弹窗不自动关（可连续改选），高亮描边落到所选
    expect(picker.find('.m13-dialog-content').exists()).toBe(true)
    expect(picker.findAll('.icon-cell--selected').map((c) => c.attributes('title'))).toEqual([target])

    const done = picker.find('.icon-dialog__done')
    expect(done.exists()).toBe(true)
    expect(done.text()).toBe('完成')
    await done.trigger('click')
    await nextTick()

    expect(picker.find('.m13-dialog-content').exists()).toBe(false)
    // 关闭路径不再产生第二次回抛、外层表单对话框仍开着（回编辑路径不变）
    expect(wrapper.vm.categoryForm.icon).toBe(target)
    expect(wrapper.vm.showCategoryDialog).toBe(true)
    expect(outerDialog(wrapper).props('modelValue')).toBe(true)
  })

  // ---------- 任务 4.4：存量非选集图标在表单侧的行为回归 ----------

  it('用例M13-3: 编辑存量非选集图标分类 → 提示 chip 保留、网格无选中项、选新即覆盖', async () => {
    const wrapper = await mountCategories()
    wrapper.vm.categoryForm.icon = 'mdi-abacus' // 历史手输、精选集外
    await nextTick()

    const picker = wrapper.findComponent(CategoryIconPicker)
    expect(picker.find('.icon-activator').text()).toContain('不在精选集，编辑需改选')

    await picker.find('.icon-activator').trigger('click')
    expect(picker.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
    expect(picker.findAll('.icon-cell--selected')).toHaveLength(0)
    expect(picker.find('.icon-dialog__preview-name').text()).toBe('mdi-abacus')

    await picker.findAll('.icon-cell')[0].trigger('click')
    expect(wrapper.vm.categoryForm.icon).toBe(CATEGORY_ICONS[0])
    expect(picker.find('.icon-activator').text()).not.toContain('不在精选集')
  })

  // ---------- 任务 4.5 / 2.3：源码口径锁（含交给 M14 的收编锚点） ----------

  it('用例M13-4: ?raw 源码锁——双分支/写死带高已删，居中尺寸与单层弹窗就绪', () => {
    // 删除项：全屏分支、写死滚动带高、窄屏判定与 resize 监听、内联展开区
    expect(categoryIconPickerSource).not.toContain('fullscreen')
    expect(categoryIconPickerSource).not.toContain('max-height: 240px')
    expect(categoryIconPickerSource).not.toMatch(/\bisNarrow\b|NARROW_BREAKPOINT/)
    expect(categoryIconPickerSource).not.toMatch(/addEventListener\(['"]resize/)
    expect(categoryIconPickerSource).not.toMatch(/icon-panel/)
    expect(categoryIconPickerSource).not.toMatch(/v-slide-y-transition/)

    // 保留项：居中 dialog（非全屏）+ 92vw 裁定值 + 卡片 80vh + 网格撑满可用高度
    const styleBlock = categoryIconPickerSource.slice(categoryIconPickerSource.indexOf('<style scoped>'))
    expect(categoryIconPickerSource).toMatch(/max-width="min\(560px, 92vw\)"/)
    expect(categoryIconPickerSource).toMatch(/transition="dialog-bottom-transition"/)
    expect(styleBlock).toMatch(/\.icon-dialog\s*\{[^}]*max-height:\s*80vh/)
    expect(styleBlock).toMatch(/\.icon-grid-scroll\s*\{[^}]*flex:\s*1;[^}]*min-height:\s*0;[^}]*overflow-y:\s*auto/)
    expect(styleBlock).toMatch(/grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(44px,\s*1fr\)\)/)

    // M14 收编清单：本组件恰一处 <v-dialog（原点点开替换点，过渡为初版 dialog-bottom-transition）
    expect(categoryIconPickerSource.match(/<v-dialog/g)).toHaveLength(1)
    expect(categoryIconPickerSource.match(/dialog-bottom-transition/g)).toHaveLength(2) // 属性 + 注释

    // 对外签名与调用方零改动：表单侧仍是裸 v-model，未新增可见态/场景 prop
    expect(categoriesPageSource).toMatch(/<CategoryIconPicker v-model="categoryForm\.icon" \/>/)
    expect(categoriesPageSource.match(/<CategoryIconPicker/g)).toHaveLength(1)
  })
})

// ── v1.4.3 M1：顶栏标题「首页」统一为「主页」（需求一，设计 §1.4）───────────
// 仅在本文件末尾追加本块：上方各模块区块与 :225、:566 处「分页接口第一页」语义注释
// 保持原文（任务 1.3 红线，顺手改即误义）。
describe('v1.4.3 M1 顶栏标题统一为「主页」', () => {
  // 任务 2.1：路由表 `/` 的 meta.title === '主页'
  // 单点生效链：AppLayout.vue currentTitle = route.meta?.title → 顶栏文本
  it('用例M1-1: 根路由 / 的 meta.title 为「主页」，name/icon/nav 与登录守卫保持不动', () => {
    const byPath = {}
    router.getRoutes().forEach((r) => {
      byPath[r.path] = r
    })

    const home = byPath['/']
    expect(home, '缺少根路由 /').toBeTruthy()
    expect(home.name).toBe('Dashboard')
    expect(home.meta.title).toBe('主页')
    // 只改标题取词：icon 与 bottom nav 标记不动（bottom nav / 侧栏本就为「主页」）
    expect(home.meta.icon).toBe('mdi-view-dashboard-outline')
    expect(home.meta.nav).toBe(true)
    expect(home.meta.public).toBeFalsy()
  })

  // 任务 2.2：?raw 源码扫描——路由表全文再无用户可见「首页」字样
  it('用例M1-2: ?raw 源码断言 router/index.js 不含「首页」，且根路由结构未受影响', () => {
    expect(routerSource).not.toContain('首页')
    // 反向锁：path / name / component 懒加载原样保留，仅 title 换字
    expect(routerSource).toMatch(
      /path: '\/',\s*\n\s*name: 'Dashboard',\s*\n\s*component: \(\) => import\('@\/pages\/DashboardPage\.vue'\),\s*\n\s*meta: \{ title: '主页'/
    )
    expect(routerSource).toContain("meta: { title: '主页', icon: 'mdi-view-dashboard-outline', nav: true }")
  })
})
