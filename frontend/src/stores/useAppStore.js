import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const darkMode = ref(false)
  const loading = ref(false)
  const toast = ref({ show: false, message: '', color: 'success' })

  function toggleDarkMode() {
    darkMode.value = !darkMode.value
  }

  function setDarkMode(val) {
    darkMode.value = val
  }

  function setLoading(val) {
    loading.value = val
  }

  function showToast(message, color = 'success') {
    toast.value = { show: true, message, color }
  }

  function hideToast() {
    toast.value.show = false
  }

  return {
    darkMode,
    loading,
    toast,
    toggleDarkMode,
    setDarkMode,
    setLoading,
    showToast,
    hideToast,
  }
})
