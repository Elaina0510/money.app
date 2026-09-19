import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getCategories, createCategory, updateCategory, reorderCategories as reorderCategoriesApi, deleteCategory, restoreDefaultCategories } from '@/api/categories'
import { getTags, createTag, deleteTag } from '@/api/tags'
import { useAppStore } from './useAppStore'

export const useCategoriesStore = defineStore('categories', () => {
  const categories = ref([])
  const tags = ref([])
  const loaded = ref(false)

  const expenseCategories = computed(() =>
    categories.value.filter((c) => c.type === 'expense')
  )

  const incomeCategories = computed(() =>
    categories.value.filter((c) => c.type === 'income')
  )

  async function fetchCategories() {
    try {
      categories.value = await getCategories()
      loaded.value = true
    } catch (e) {
      console.error('Failed to fetch categories:', e)
    }
  }

  async function fetchTags() {
    try {
      tags.value = await getTags()
    } catch (e) {
      console.error('Failed to fetch tags:', e)
    }
  }

  async function addCategory(data) {
    const app = useAppStore()
    try {
      const cat = await createCategory(data)
      categories.value.push(cat)
      app.showToast('分类创建成功')
      return cat
    } catch (e) {
      app.showToast(e.message || '创建失败', 'error')
      throw e
    }
  }

  async function editCategory(id, data) {
    const app = useAppStore()
    try {
      const cat = await updateCategory(id, data)
      // 预设分类 CoW 后响应 id 与原 id 不同（旧 id 已不在可见集合），
      // 跳过原地替换以免出现双份；由调用方 fetchCategories() 统一对齐
      if (cat && cat.id === id) {
        const idx = categories.value.findIndex((c) => c.id === id)
        if (idx >= 0) categories.value[idx] = cat
      }
      app.showToast('分类更新成功')
      return cat
    } catch (e) {
      app.showToast(e.message || '更新失败', 'error')
      throw e
    }
  }

  async function reorderCategories(type, ids) {
    const app = useAppStore()
    try {
      const result = await reorderCategoriesApi({ type, ids })
      // 唯一对齐手段：整体重拉（预设行 CoW 后 id 会变，不原地替换）；不弹附加成功 toast
      await fetchCategories()
      return result
    } catch (e) {
      app.showToast('排序保存失败', 'error')
      throw e
    }
  }

  async function removeCategory(id) {
    const app = useAppStore()
    try {
      await deleteCategory(id)
      categories.value = categories.value.filter((c) => c.id !== id)
      app.showToast('分类已删除')
    } catch (e) {
      app.showToast(e.message || '删除失败', 'error')
      throw e
    }
  }

  async function addTag(data) {
    const app = useAppStore()
    try {
      const tag = await createTag(data)
      tags.value.push(tag)
      app.showToast('标签创建成功')
      return tag
    } catch (e) {
      app.showToast(e.message || '创建失败', 'error')
      throw e
    }
  }

  async function removeTag(id) {
    const app = useAppStore()
    try {
      await deleteTag(id)
      tags.value = tags.value.filter((t) => t.id !== id)
      app.showToast('标签已删除')
    } catch (e) {
      app.showToast(e.message || '删除失败', 'error')
      throw e
    }
  }

  async function restoreDefaults() {
    const result = await restoreDefaultCategories()
    await fetchCategories()
    return result
  }

  return {
    categories,
    tags,
    loaded,
    expenseCategories,
    incomeCategories,
    fetchCategories,
    fetchTags,
    addCategory,
    editCategory,
    reorderCategories,
    removeCategory,
    addTag,
    removeTag,
    restoreDefaults,
  }
})
