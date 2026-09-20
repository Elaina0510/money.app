import { defineStore } from 'pinia'
import { ref } from 'vue'

const THEME_KEY = 'money-app-theme-mode'

export const useAppStore = defineStore('app', () => {
  const themeMode = ref(localStorage.getItem(THEME_KEY) || 'auto')
  const darkMode = ref(false)
  const loading = ref(false)
  const toast = ref({ show: false, message: '', color: 'success' })
  const transitionOrigin = ref(null)
  // v1.4.3 M14（任务 4.1 / D7）：最近一次 pointerdown 的视口坐标——全站展开画面的触发点来源。
  // 由 AppLayout.vue onMounted 的 document pointerdown 捕获监听写入（键盘触发无 pointer 时
  // 维持上一次，AppDialog 内再按「未设/{0,0} → 中心」退化）。
  const lastClickOrigin = ref(null)

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

  function setLastClickOrigin(origin) {
    lastClickOrigin.value = origin
  }

  return {
    darkMode,
    themeMode,
    loading,
    toast,
    transitionOrigin,
    lastClickOrigin,
    toggleDarkMode,
    setDarkMode,
    setThemeMode,
    initThemeListener,
    setLoading,
    showToast,
    hideToast,
    setTransitionOrigin,
    setLastClickOrigin,
  }
})
