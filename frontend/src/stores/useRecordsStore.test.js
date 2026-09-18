import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// M4 只隐藏账单页的类型/分类筛选入口：store 字段与后端能力必须原样保留
vi.mock('@/api/records', () => ({
  getRecords: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, total_pages: 1 }),
  getRecord: vi.fn().mockResolvedValue({}),
  createRecord: vi.fn().mockResolvedValue({}),
  updateRecord: vi.fn().mockResolvedValue({}),
  deleteRecord: vi.fn().mockResolvedValue({}),
  batchDeleteRecords: vi.fn().mockResolvedValue({}),
  getQuickTemplates: vi.fn().mockResolvedValue([]),
}))

import { useRecordsStore } from './useRecordsStore'

describe('useRecordsStore - 筛选字段保留（M4 回归红线）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('filters 仍包含 type/category_id/tag_id/keyword 字段（仅前端隐藏入口）', () => {
    const store = useRecordsStore()
    expect(Object.keys(store.filters).sort()).toEqual(
      ['category_id', 'end_date', 'keyword', 'start_date', 'tag_id', 'type'].sort()
    )
    expect(store.filters).toMatchObject({
      start_date: '',
      end_date: '',
      category_id: null,
      type: '',
      tag_id: null,
      keyword: '',
    })
  })

  it('setFilters 写入 type/category_id 后字段仍可取回（后端能力未被前端删除）', () => {
    const store = useRecordsStore()
    store.setFilters({ start_date: '2026-09-01', end_date: '2026-09-30', type: 'expense' })
    expect(store.filters.type).toBe('expense')
    expect(store.filters.start_date).toBe('2026-09-01')
    expect(store.filters.end_date).toBe('2026-09-30')
    expect('category_id' in store.filters).toBe(true)
    expect('tag_id' in store.filters).toBe(true)
    expect('keyword' in store.filters).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// M5 需求三：账单页"浏览现场"内存级存取（一次性消费语义）
// ---------------------------------------------------------------------------
describe('useRecordsStore - 账单浏览现场（M5）', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useRecordsStore()
  })

  it('初始无现场：consumeListView 返回 null（正常进入账单页走默认当前月）', () => {
    expect(store.listView).toBeNull()
    expect(store.consumeListView()).toBeNull()
  })

  it('用例4 相关: rememberListView 存入 { year, month, scrollTop } 快照（浅拷贝，隔离调用方对象）', () => {
    const snapshot = { year: 2025, month: 3, scrollTop: 240 }
    store.rememberListView(snapshot)
    expect(store.consumeListView()).toEqual({ year: 2025, month: 3, scrollTop: 240 })

    // 快照为拷贝：调用方后续复用同一对象不会串改进场
    const mutable = { year: 2025, month: 6, scrollTop: 10 }
    store.rememberListView(mutable)
    mutable.month = 9
    mutable.scrollTop = 999
    expect(store.listView).toEqual({ year: 2025, month: 6, scrollTop: 10 })
  })

  it('年份视图现场：month 允许为 null', () => {
    store.rememberListView({ year: 2024, month: null, scrollTop: 0 })
    expect(store.consumeListView()).toEqual({ year: 2024, month: null, scrollTop: 0 })
  })

  it('用例3: consumeListView 幂等——首次返回快照，第二次返回 null 且状态清空', () => {
    store.rememberListView({ year: 2025, month: 3, scrollTop: 320 })
    const first = store.consumeListView()
    expect(first).toEqual({ year: 2025, month: 3, scrollTop: 320 })
    expect(store.listView).toBeNull()
    expect(store.consumeListView()).toBeNull()
    expect(store.consumeListView()).toBeNull() // 反复调用仍是 null
  })

  it('用例5: resetListView 清空现场（登出/换账号路径）', () => {
    store.rememberListView({ year: 2025, month: 3, scrollTop: 320 })
    store.resetListView()
    expect(store.listView).toBeNull()
    expect(store.consumeListView()).toBeNull()
  })

  it('红线：现场存取不触碰 filters（跨导航全局保留能力不变）', () => {
    store.setFilters({ start_date: '2025-03-01', end_date: '2025-03-31', keyword: '午餐' })
    store.rememberListView({ year: 2025, month: 3, scrollTop: 120 })
    store.consumeListView()
    store.resetListView()
    expect(store.filters).toMatchObject({
      start_date: '2025-03-01',
      end_date: '2025-03-31',
      keyword: '午餐',
    })
  })
})
