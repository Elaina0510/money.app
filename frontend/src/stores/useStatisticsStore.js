import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSummary, getByCategory, getByTag, getTrend } from '@/api/statistics'

export const useStatisticsStore = defineStore('statistics', () => {
  const summary = ref(null)
  const categoryStats = ref([])
  const tagStats = ref([])
  const trendData = ref([])

  async function fetchSummary(params) {
    try {
      summary.value = await getSummary(params)
    } catch (e) {
      console.error('Failed to fetch summary:', e)
    }
  }

  async function fetchByCategory(params) {
    try {
      categoryStats.value = await getByCategory(params)
    } catch (e) {
      console.error('Failed to fetch by-category:', e)
    }
  }

  async function fetchByTag(params) {
    try {
      tagStats.value = await getByTag(params)
    } catch (e) {
      console.error('Failed to fetch by-tag:', e)
    }
  }

  async function fetchTrend(params) {
    try {
      trendData.value = await getTrend(params)
    } catch (e) {
      console.error('Failed to fetch trend:', e)
    }
  }

  return {
    summary,
    categoryStats,
    tagStats,
    trendData,
    fetchSummary,
    fetchByCategory,
    fetchByTag,
    fetchTrend,
  }
})
