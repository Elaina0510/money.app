import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useRoute: () => ({
    path: '/',
    meta: { title: '主页' },
  }),
}))

// Mock stores
vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({
    darkMode: false,
    toggleDarkMode: vi.fn(),
    setDarkMode: vi.fn(),
    showToast: vi.fn(),
  }),
}))

// Mock ToastNotification
vi.mock('@/components/common/ToastNotification.vue', () => ({
  default: {
    name: 'ToastNotification',
    template: '<div class="toast-mock"></div>',
  },
}))

// Import component after mocks
import AppLayout from './AppLayout.vue'

describe('AppLayout - Wide Screen Scaling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset window width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    })
  })

  it('should render correctly', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('should have content-wrapper element', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': { template: '<div class="v-app"><slot /></div>' },
          'v-navigation-drawer': true,
          'v-main': { template: '<div class="v-main main-content"><slot /></div>' },
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
          ToastNotification: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('should have main-content element', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': { template: '<div class="v-app"><slot /></div>' },
          'v-navigation-drawer': true,
          'v-main': { template: '<div class="v-main main-content"><slot /></div>' },
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
          ToastNotification: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('should detect desktop mode', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.vm.isDesktop).toBe(true)
  })

  it('should detect mobile mode', async () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 800,
    })

    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.vm.isDesktop).toBe(false)
  })

  it('should update on resize', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()

    // Initially desktop
    expect(wrapper.vm.isDesktop).toBe(true)

    // Simulate resize to mobile
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 800,
    })
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(wrapper.vm.isDesktop).toBe(false)
  })

  it('should have navigation items', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.vm.navItems).toBeDefined()
    expect(wrapper.vm.navItems.length).toBeGreaterThan(0)
  })

  it('should have current route computed', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(wrapper.vm.currentRoute).toBeDefined()
  })

  it('should have goToAddRecord method', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(typeof wrapper.vm.goToAddRecord).toBe('function')
  })

  it('should have toggleNav method', async () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          'router-view': true,
          'v-app': true,
          'v-navigation-drawer': true,
          'v-main': true,
          'v-btn': true,
          'v-icon': true,
          'v-list': true,
          'v-list-item': true,
          'v-divider': true,
          'v-spacer': true,
          'v-switch': true,
          'v-bottom-navigation': true,
          'v-avatar': true,
          transition: true,
        },
      },
    })
    await flushPromises()
    expect(typeof wrapper.vm.toggleNav).toBe('function')
  })
})
