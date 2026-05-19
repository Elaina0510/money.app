import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getRecords,
  getRecord,
  createRecord,
  updateRecord,
  deleteRecord,
  batchDeleteRecords,
  getQuickTemplates,
} from '@/api/records'
import { useAppStore } from './useAppStore'

export const useRecordsStore = defineStore('records', () => {
  const records = ref([])
  const currentRecord = ref(null)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  const filters = ref({
    start_date: '',
    end_date: '',
    category_id: null,
    type: '',
    keyword: '',
  })
  const templates = ref([])
  const loading = ref(false)

  const hasMore = computed(() => page.value < totalPages.value)

  async function fetchRecords(params = {}) {
    const app = useAppStore()
    loading.value = true
    try {
      const query = {
        page: page.value,
        page_size: pageSize.value,
        ...filters.value,
        ...params,
      }
      // Remove empty filters
      Object.keys(query).forEach((k) => {
        if (query[k] === '' || query[k] === null || query[k] === undefined) {
          delete query[k]
        }
      })
      const result = await getRecords(query)
      if (params.page && params.page > 1) {
        records.value = [...records.value, ...result.items]
      } else {
        records.value = result.items
      }
      total.value = result.total
      totalPages.value = result.total_pages
      page.value = result.page
    } catch (e) {
      console.error('Failed to fetch records:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchRecord(id) {
    try {
      currentRecord.value = await getRecord(id)
      return currentRecord.value
    } catch (e) {
      console.error('Failed to fetch record:', e)
      return null
    }
  }

  async function addRecord(data) {
    const app = useAppStore()
    try {
      const record = await createRecord(data)
      app.showToast('记账成功')
      return record
    } catch (e) {
      app.showToast(e.message || '记账失败', 'error')
      throw e
    }
  }

  async function editRecord(id, data) {
    const app = useAppStore()
    try {
      const record = await updateRecord(id, data)
      const idx = records.value.findIndex((r) => r.id === id)
      if (idx >= 0) records.value[idx] = record
      app.showToast('更新成功')
      return record
    } catch (e) {
      app.showToast(e.message || '更新失败', 'error')
      throw e
    }
  }

  async function removeRecord(id) {
    const app = useAppStore()
    try {
      await deleteRecord(id)
      records.value = records.value.filter((r) => r.id !== id)
      total.value--
      app.showToast('删除成功')
    } catch (e) {
      app.showToast(e.message || '删除失败', 'error')
      throw e
    }
  }

  async function batchDelete(ids) {
    const app = useAppStore()
    try {
      await batchDeleteRecords(ids)
      records.value = records.value.filter((r) => !ids.includes(r.id))
      total.value -= ids.length
      app.showToast(`已删除 ${ids.length} 条记录`)
    } catch (e) {
      app.showToast(e.message || '批量删除失败', 'error')
      throw e
    }
  }

  async function fetchTemplates() {
    try {
      templates.value = await getQuickTemplates()
    } catch (e) {
      console.error('Failed to fetch templates:', e)
    }
  }

  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
  }

  function resetFilters() {
    filters.value = {
      start_date: '',
      end_date: '',
      category_id: null,
      type: '',
      keyword: '',
    }
    page.value = 1
  }

  function loadMore() {
    if (hasMore.value) {
      page.value++
      fetchRecords()
    }
  }

  return {
    records,
    currentRecord,
    total,
    page,
    pageSize,
    totalPages,
    filters,
    templates,
    loading,
    hasMore,
    fetchRecords,
    fetchRecord,
    addRecord,
    editRecord,
    removeRecord,
    batchDelete,
    fetchTemplates,
    setFilters,
    resetFilters,
    loadMore,
  }
})
