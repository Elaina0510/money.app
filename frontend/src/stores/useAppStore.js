import { defineStore } from 'pinia'
import { ref } from 'vue'

const THEME_KEY = 'money-app-theme-mode'

export const useAppStore = defineStore('app', () => {
  const themeMode = ref(localStorage.getItem(THEME_KEY) || 'auto')
  const darkMode = ref(false)
  const loading = ref(false)
  const toast = ref({ show: false, message: '', color: 'success' })
  const transitionOrigin = ref(null)

  function resolveDarkMode() {
    if (themeMode.value === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return themeMode.value === 'dark'
  }

  function setThemeMode(mode) {
    themeMode.value = mode
    localStorage.setItem(THEME_KEY, mode)
    darkMode.value = resolveDarkMode()
  }

  function initThemeListener() {
    darkMode.value = resolveDarkMode()
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', (e) => {
      if (themeMode.value === 'auto') {
        darkMode.value = e.matches
      }
    })
  }

  function toggleDarkMode() {
    setThemeMode(darkMode.value ? 'light' : 'dark')
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

  function setTransitionOrigin(origin) {
    transitionOrigin.value = origin
  }

  return {
    darkMode,
    themeMode,
    loading,
    toast,
    transitionOrigin,
    toggleDarkMode,
    setDarkMode,
    setThemeMode,
    initThemeListener,
    setLoading,
    showToast,
    hideToast,
    setTransitionOrigin,
  }
})
