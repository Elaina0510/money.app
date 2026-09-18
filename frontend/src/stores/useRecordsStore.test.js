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
