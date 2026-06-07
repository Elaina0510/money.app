import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAppStore } from './useAppStore'

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should have initial state', () => {
    const store = useAppStore()
    expect(store.darkMode).toBe(false)
    expect(store.loading).toBe(false)
    expect(store.toast).toEqual({ show: false, message: '', color: 'success' })
    expect(store.transitionOrigin).toBeNull()
  })

  it('should toggle dark mode', () => {
    const store = useAppStore()
    expect(store.darkMode).toBe(false)

    store.toggleDarkMode()
    expect(store.darkMode).toBe(true)

    store.toggleDarkMode()
    expect(store.darkMode).toBe(false)
  })

  it('should set dark mode', () => {
    const store = useAppStore()

    store.setDarkMode(true)
    expect(store.darkMode).toBe(true)

    store.setDarkMode(false)
    expect(store.darkMode).toBe(false)
  })

  it('should set loading', () => {
    const store = useAppStore()

    store.setLoading(true)
    expect(store.loading).toBe(true)

    store.setLoading(false)
    expect(store.loading).toBe(false)
  })

  it('should show toast', () => {
    const store = useAppStore()

    store.showToast('Test message', 'info')
    expect(store.toast).toEqual({ show: true, message: 'Test message', color: 'info' })
  })

  it('should show toast with default color', () => {
    const store = useAppStore()

    store.showToast('Test message')
    expect(store.toast).toEqual({ show: true, message: 'Test message', color: 'success' })
  })

  it('should hide toast', () => {
    const store = useAppStore()

    store.showToast('Test message')
    expect(store.toast.show).toBe(true)

    store.hideToast()
    expect(store.toast.show).toBe(false)
  })

  it('should set transition origin', () => {
    const store = useAppStore()
    const origin = { x: 100, y: 200 }

    store.setTransitionOrigin(origin)
    expect(store.transitionOrigin).toEqual(origin)
  })

  it('should clear transition origin', () => {
    const store = useAppStore()

    store.setTransitionOrigin({ x: 100, y: 200 })
    expect(store.transitionOrigin).toEqual({ x: 100, y: 200 })

    store.setTransitionOrigin(null)
    expect(store.transitionOrigin).toBeNull()
  })
})
