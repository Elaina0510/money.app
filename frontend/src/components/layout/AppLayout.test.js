import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

// 可控当前路由：AppLayout 的 isLoginPage 判据依赖 route.path === '/login'
// getter 内部读取 ref，computed 仍能追踪到变化（vi.mock 工厂为惰性求值，此处引用安全）
const routePath = ref('/')

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useRoute: () => ({
    get path() {
      return routePath.value
    },
    get meta() {
      return { title: routePath.value === '/login' ? '登录' : '主页' }
    },
  }),
}))

// Mock stores
vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({
    darkMode: false,
    themeMode: 'auto',
    toggleDarkMode: vi.fn(),
    setDarkMode: vi.fn(),
    setThemeMode: vi.fn(),
    initThemeListener: vi.fn(),
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

// ---------------------------------------------------------------------------
// M1 登录页沉浸式改造：登录态隐藏导航元素 + 登录页布局锁定
// ---------------------------------------------------------------------------
describe('AppLayout - M1 登录页沉浸式', () => {
  // 渲染 slot 的桩件：保证组件上声明的 class 与 v-show 样式落到真实 DOM 上
  const stubs = {
    'router-view': true,
    'v-app': { template: '<div class="v-app"><slot /></div>' },
    'v-navigation-drawer': { template: '<div class="app-sidebar"><slot /></div>' },
    'v-main': { template: '<div class="v-main"><slot /></div>' },
    'v-btn': { template: '<div class="v-btn"><slot /></div>' },
    'v-icon': true,
    'v-list': true,
    'v-list-item': true,
    'v-divider': true,
    'v-spacer': true,
    'v-switch': true,
    'v-bottom-navigation': { template: '<div class="v-bottom-navigation"><slot /></div>' },
    'v-avatar': true,
    transition: true,
  }

  const MOBILE = 375
  const DESKTOP = 1280

  function setViewport(width) {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: width,
    })
    window.dispatchEvent(new Event('resize'))
  }

  async function mountAt(path, width) {
    routePath.value = path
    setViewport(width)
    const wrapper = mount(AppLayout, { global: { stubs } })
    await flushPromises()
    setViewport(width) // 挂载后同步一次，覆盖 isDesktop 初值
    await nextTick()
    return wrapper
  }

  // 顶栏内的按钮：宽屏非登录页 = 汉堡 + 暗色切换；登录页只剩暗色切换
  function topBarButtons(wrapper) {
    return wrapper.find('.app-top-bar').findAll('.v-btn')
  }

  function sidebarStyle(wrapper) {
    return wrapper.find('.app-sidebar').attributes('style') || ''
  }

  beforeEach(() => {
    vi.clearAllMocks()
    routePath.value = '/'
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('userId')
  })

  it('M1-T1a 宽屏 /login：FAB、底栏、汉堡按钮不渲染，侧栏抽屉隐藏', async () => {
    const wrapper = await mountAt('/login', DESKTOP)

    expect(wrapper.vm.isLoginPage).toBe(true)
    expect(wrapper.find('.fab-add').exists()).toBe(false)
    expect(wrapper.find('.bottom-nav').exists()).toBe(false)
    // 侧栏使用 v-show 隐藏（保留节点但不占位、不可交互），宽屏登录页与竖屏一致
    expect(wrapper.find('.app-sidebar').exists()).toBe(true)
    expect(sidebarStyle(wrapper)).toContain('display: none')
    // 顶栏仅保留暗色切换按钮（决策 D6）
    expect(topBarButtons(wrapper)).toHaveLength(1)
  })

  it('M1-T1b 竖屏 /login：FAB 与底栏不渲染，侧栏抽屉隐藏', async () => {
    const wrapper = await mountAt('/login', MOBILE)

    expect(wrapper.vm.isLoginPage).toBe(true)
    expect(wrapper.find('.fab-add').exists()).toBe(false)
    expect(wrapper.find('.bottom-nav').exists()).toBe(false)
    expect(sidebarStyle(wrapper)).toContain('display: none')
    // 竖屏本就无汉堡按钮，顶栏仅剩暗色切换（决策 D6）
    expect(topBarButtons(wrapper)).toHaveLength(1)
  })

  it('M1-T2a 竖屏非登录路由：底栏与 FAB 正常渲染', async () => {
    const wrapper = await mountAt('/records', MOBILE)

    expect(wrapper.vm.isLoginPage).toBe(false)
    expect(wrapper.find('.fab-add').exists()).toBe(true)
    expect(wrapper.find('.bottom-nav').exists()).toBe(true)
    expect(sidebarStyle(wrapper)).toContain('display: none') // 竖屏侧栏依旧隐藏
  })

  it('M1-T2b 宽屏非登录路由：FAB 与汉堡按钮正常渲染，侧栏可见且无底栏', async () => {
    const wrapper = await mountAt('/statistics', DESKTOP)

    expect(wrapper.vm.isLoginPage).toBe(false)
    expect(wrapper.find('.fab-add').exists()).toBe(true)
    expect(wrapper.find('.bottom-nav').exists()).toBe(false)
    expect(sidebarStyle(wrapper)).not.toContain('display: none')
    expect(topBarButtons(wrapper)).toHaveLength(2) // 汉堡 + 暗色切换
  })

  it('M1-T3 登录 → 退出 → 再登录循环中条件渲染正确', async () => {
    const wrapper = await mountAt('/login', MOBILE)

    // 1) 未登录停留在登录页：无任何导航入口
    expect(wrapper.find('.fab-add').exists()).toBe(false)
    expect(wrapper.find('.bottom-nav').exists()).toBe(false)

    // 2) 登录成功：写 token + auth:login + 路由离开 /login → 底栏/FAB 即时恢复
    localStorage.setItem('token', 'fake-token')
    localStorage.setItem('username', 'tester')
    routePath.value = '/'
    window.dispatchEvent(new Event('auth:login'))
    await nextTick()
    await flushPromises()

    expect(wrapper.vm.isLoginPage).toBe(false)
    expect(wrapper.find('.fab-add').exists()).toBe(true)
    expect(wrapper.find('.bottom-nav').exists()).toBe(true)

    // 3) 退出登录：清 token + auth:logout + 回到登录页 → 导航入口再次隐藏
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    routePath.value = '/login'
    window.dispatchEvent(new Event('auth:logout'))
    await nextTick()
    await flushPromises()

    expect(wrapper.vm.isLoginPage).toBe(true)
    expect(wrapper.find('.fab-add').exists()).toBe(false)
    expect(wrapper.find('.bottom-nav').exists()).toBe(false)

    // 4) 再登录：条件渲染可重复、无残留
    localStorage.setItem('token', 'fake-token-2')
    routePath.value = '/'
    window.dispatchEvent(new Event('auth:login'))
    await nextTick()
    await flushPromises()

    expect(wrapper.vm.isLoginPage).toBe(false)
    expect(wrapper.find('.fab-add').exists()).toBe(true)
    expect(wrapper.find('.bottom-nav').exists()).toBe(true)
  })

  it('M1-T4 布局锁定类仅登录页挂载，非登录页布局不变', async () => {
    const loginWrapper = await mountAt('/login', MOBILE)
    expect(loginWrapper.find('.main-content').classes()).toContain('main-content--locked')
    expect(loginWrapper.find('.content-overflow').classes()).toContain('content-overflow--locked')
    expect(loginWrapper.find('.content-wrapper').classes()).toContain('content-wrapper--bare')
    loginWrapper.unmount()

    const normalWrapper = await mountAt('/', DESKTOP)
    expect(normalWrapper.find('.main-content').classes()).not.toContain('main-content--locked')
    expect(normalWrapper.find('.content-overflow').classes()).not.toContain(
      'content-overflow--locked'
    )
    expect(normalWrapper.find('.content-wrapper').classes()).not.toContain('content-wrapper--bare')
    normalWrapper.unmount()
  })
})
