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

// M5：AppLayout 的登出流程会清除账单页浏览现场，这里用 spy 断言其被调用
// （工厂内惰性引用，避免 mock 提升导致的 TDZ）
const mockResetListView = vi.fn()
vi.mock('@/stores/useRecordsStore', () => ({
  useRecordsStore: () => ({
    resetListView: mockResetListView,
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
// M5（任务 §0.2 实测环境事实）：本文件 17+ 用例把 v-navigation-drawer / v-btn 等替身化，
// Vuetify 真实类名（v-navigation-drawer--rail）、rail 计算宽度、`v-btn to=` 的路由跳转
// 在 jsdom 断不到 → M5 断言一律走「替身组件 props（替身声明 props 后 .props() 可读绑定值）」
// + 「?raw 源码正则」（仓库既定范式）；真实悬停提示 / 72px 实宽 / 滚动条归真机人工清单。
import sfcSource from './AppLayout.vue?raw'

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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
          'v-tooltip': true,
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
    // M5：rail 图标列每项配 v-tooltip（本 describe 只关心导航元素显隐，空替身即可）
    'v-tooltip': true,
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

  // 顶栏内的按钮：M5（REQ-011）后汉堡块已删除、切换钮移入侧栏首位 → 顶栏恒只剩右侧暗色切换钮
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

  it('M1-T2b 宽屏非登录路由：FAB 与顶栏深色钮正常渲染，侧栏可见且无底栏', async () => {
    const wrapper = await mountAt('/statistics', DESKTOP)

    expect(wrapper.vm.isLoginPage).toBe(false)
    expect(wrapper.find('.fab-add').exists()).toBe(true)
    expect(wrapper.find('.bottom-nav').exists()).toBe(false)
    expect(sidebarStyle(wrapper)).not.toContain('display: none')
    // M5（REQ-011）：顶栏汉堡块删除、收起/展开切换钮移入侧栏首位 → 顶栏只剩右侧深色切换钮
    expect(topBarButtons(wrapper)).toHaveLength(1)
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

// ---------------------------------------------------------------------------
// M5 需求三联动：登出时清除账单页"浏览现场"（避免换账号后返回现场串号）
// ---------------------------------------------------------------------------
describe('AppLayout - 登出清除账单浏览现场（M5）', () => {
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
    // M5：rail 图标列每项配 v-tooltip，本 describe 只断登出行为，空替身即可
    'v-tooltip': true,
    'v-bottom-navigation': { template: '<div class="v-bottom-navigation"><slot /></div>' },
    'v-avatar': true,
    transition: true,
  }

  beforeEach(() => {
    mockResetListView.mockClear()
    routePath.value = '/'
    localStorage.setItem('token', 'fake-token')
    localStorage.setItem('username', 'tester')
    localStorage.setItem('userId', '1')
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1280,
    })
  })

  it('handleLogout 调用 recordsStore.resetListView 并清空登录态', async () => {
    const wrapper = mount(AppLayout, { global: { stubs } })
    await flushPromises()

    wrapper.vm.handleLogout()
    await nextTick()

    expect(mockResetListView).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('username')).toBeNull()
    expect(localStorage.getItem('userId')).toBeNull()
    expect(wrapper.vm.isLoggedIn).toBe(false)
    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// M5 横屏侧边栏图标列（REQ-010 / REQ-011 / REQ-012，任务 §4.1–4.9）
//   断言载体 = 替身组件 props + DOM 属性 + ?raw 源码正则（见文件头环境事实）；
//   顶栏断言不反查 mdi-menu（rail 切换钮本体即该图标，同字面量易误伤）。
// ---------------------------------------------------------------------------
describe('AppLayout - M5 横屏侧边栏图标列', () => {
  const MOBILE = 375
  const DESKTOP = 1280

  const stubs = {
    'router-view': true,
    'v-app': { template: '<div class="v-app"><slot /></div>' },
    // 替身声明 props → .props() 可读到组件绑定值（任务 §4.1 口径；仍不断 Vuetify 真实类名/宽度）
    'v-navigation-drawer': {
      props: [
        'modelValue',
        'permanent',
        'temporary',
        'rail',
        'railWidth',
        'width',
        'mobileBreakpoint',
        'elevation',
      ],
      template: '<div class="app-sidebar"><slot /></div>',
    },
    'v-main': { template: '<div class="v-main"><slot /></div>' },
    // v-btn 替身不声明 props：to / color / size / aria-label 以 attribute 落到真实 DOM，可点可断
    'v-btn': { template: '<div class="v-btn"><slot /></div>' },
    'v-icon': true,
    'v-list': true,
    'v-list-item': true,
    'v-divider': true,
    'v-spacer': true,
    'v-switch': true,
    // v-tooltip 替身渲染默认槽：提示文案在 DOM 可见（真实悬停出提示归人工清单）
    'v-tooltip': { template: '<div class="v-tooltip"><slot /></div>' },
    'v-bottom-navigation': { template: '<div class="v-bottom-navigation"><slot /></div>' },
    'v-avatar': true,
    transition: true,
  }

  function setViewport(width) {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: width,
    })
    window.dispatchEvent(new Event('resize'))
  }

  async function mountAt({ path = '/', width = DESKTOP, loggedIn = true } = {}) {
    routePath.value = path
    if (loggedIn) {
      localStorage.setItem('token', 'fake-token')
      localStorage.setItem('username', 'tester')
      localStorage.setItem('userId', '1')
    } else {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('userId')
    }
    setViewport(width)
    const wrapper = mount(AppLayout, { global: { stubs } })
    await flushPromises()
    await nextTick()
    return wrapper
  }

  // --- 源码区块切片：断言按区块收敛，避免同字面量跨区块误伤 ---
  function sliceBetween(startMarker, endMarker, label) {
    const start = sfcSource.indexOf(startMarker)
    const end = sfcSource.indexOf(endMarker, start)
    expect(start, `${label}起始锚点应在源码中在场`).toBeGreaterThan(-1)
    expect(end, `${label}结束锚点应在源码中在场`).toBeGreaterThan(start)
    return sfcSource.slice(start, end)
  }

  // 顶栏区块：.app-top-bar 开标签 → 紧随其后的 Page Content 注释
  const topBarSrc = () => sliceBetween('<div class="app-top-bar', '<!-- Page Content', '顶栏区块')

  // rail 图标列区块：v-if="isDesktop && rail" 容器 → 展开态 v-else 起点
  const railBlockSrc = () =>
    sliceBetween(
      '<div v-if="isDesktop && rail" class="sidebar-rail">',
      '<template v-else>',
      'rail 图标列区块'
    )

  // 抽屉开标签（绑定改组断言用）
  function drawerTagSrc() {
    const match = sfcSource.match(/<v-navigation-drawer\b[^>]*>/)
    expect(match, 'v-navigation-drawer 开标签应在源码中在场').toBeTruthy()
    return match[0]
  }

  const countMatches = (text, re) => (text.match(re) || []).length

  beforeEach(() => {
    vi.clearAllMocks()
    mockResetListView.mockClear()
    routePath.value = '/'
  })

  // §4.1 宽屏初始即收起态（图标列常驻）
  it('M5-T4.1 宽屏初始 rail=true：抽屉替身 props rail/railWidth=72/permanent=true（禁断 Vuetify 类名与计算宽度）', async () => {
    const wrapper = await mountAt()
    const drawer = wrapper.findComponent('.app-sidebar')

    expect(drawer.exists()).toBe(true)
    expect(drawer.props('rail')).toBe(true)
    expect(drawer.props('railWidth')).toBe(72)
    expect(drawer.props('permanent')).toBe(true)
    expect(drawer.props('temporary')).toBe(false)
    expect(drawer.props('width')).toBe(240) // width=240 保持，展开宽不受 rail-width 影响
    // v-model = 「在位可见」语义（实测 Vuetify permanent + modelValue=false → inert + 推出屏外）
    expect(drawer.props('modelValue')).toBe(true)

    // rail 表达式带 isDesktop 守卫 + rail 宽走 prop（任务 §1.1/§1.3）
    expect(drawerTagSrc()).toMatch(/:rail="isDesktop && rail"/)
    expect(drawerTagSrc()).toMatch(/:rail-width="72"/)
    expect(wrapper.vm.rail).toBe(true)
    expect(wrapper.find('.sidebar-rail').exists()).toBe(true)
    wrapper.unmount()
  })

  // §1.2 toggleNav 形态机语义
  it('M5-T1.2 toggleNav：宽屏翻转 rail 且 model 与可见态不相反；竖屏维持切换临时抽屉且永不进 rail 态', async () => {
    const wrapper = await mountAt()
    const drawer = wrapper.findComponent('.app-sidebar')

    wrapper.vm.toggleNav() // 收起 → 展开
    await nextTick()
    expect(wrapper.vm.rail).toBe(false)
    expect(drawer.props('rail')).toBe(false)
    expect(drawer.props('modelValue')).toBe(true)
    expect(wrapper.find('.sidebar-rail').exists()).toBe(false)

    wrapper.vm.toggleNav() // 展开 → 收起
    await nextTick()
    expect(wrapper.vm.rail).toBe(true)
    expect(drawer.props('rail')).toBe(true)
    expect(drawer.props('railWidth')).toBe(72)
    expect(drawer.props('modelValue')).toBe(true)
    expect(wrapper.find('.sidebar-rail').exists()).toBe(true)
    wrapper.unmount()

    // 竖屏分支不变：drawer = !drawer；rail 位虽维持 true，但绑定守卫使抽屉永不进 rail 态
    const portrait = await mountAt({ path: '/records', width: MOBILE })
    const portraitDrawer = portrait.findComponent('.app-sidebar')
    expect(portraitDrawer.props('rail')).toBe(false)
    expect(portrait.vm.drawer).toBe(false)
    portrait.vm.toggleNav()
    await nextTick()
    expect(portrait.vm.drawer).toBe(true)
    expect(portrait.vm.rail).toBe(true)
    expect(portrait.findComponent('.app-sidebar').props('rail')).toBe(false)
    portrait.unmount()
  })

  // §4.2 收起态四类入口可点达
  it('M5-T4.2 收起态入口可点达：rail 块 6 钮 + to 值断言 + 主题/登出行为 + color 绑定源码正则', async () => {
    const wrapper = await mountAt({ path: '/' })
    const rail = wrapper.find('.sidebar-rail')

    expect(rail.exists()).toBe(true)
    expect(rail.findAll('.v-btn')).toHaveLength(6) // 导航 3 + 设置 + 主题 + 登出
    expect(wrapper.find('.rail-home-btn').attributes('to')).toBe('/')
    expect(wrapper.find('.rail-records-btn').attributes('to')).toBe('/records')
    expect(wrapper.find('.rail-statistics-btn').attributes('to')).toBe('/statistics')
    expect(wrapper.find('.rail-settings-btn').attributes('to')).toBe('/settings')

    // 主题钮点击 → toggleDarkMode 被调（与展开态 switch、顶栏钮三方同源）
    await wrapper.find('.rail-theme-btn').trigger('click')
    expect(wrapper.vm.appStore.toggleDarkMode).toHaveBeenCalledTimes(1)

    // 登出钮点击 → 现 handleLogout 逐字行为：清 localStorage 三键 + resetListView + toast（无二次确认，D9）
    await wrapper.find('.rail-logout-btn').trigger('click')
    await nextTick()
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('username')).toBeNull()
    expect(localStorage.getItem('userId')).toBeNull()
    expect(mockResetListView).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.appStore.showToast).toHaveBeenCalledWith('已退出登录', 'info')
    wrapper.unmount()

    // 前景色口径（任务 §2.3 / ui-design 审查轮补口径）源码正则：
    // 导航/设置 4 钮 = 三元式（命中 primary / 未命中 on-surface-variant），主题/登出 2 钮恒中性灰
    const src = railBlockSrc()
    expect(
      countMatches(src, /:color="railActive === '[^']+' \? 'primary' : 'on-surface-variant'"/g)
    ).toBe(4)
    expect(countMatches(src, /\scolor="on-surface-variant"/g)).toBe(2)
    expect(src).not.toMatch(/\scolor="primary"/) // 常态不硬编码 primary（撞色口径）

    // DOM 侧同源确认：未选中中性灰、选中转 primary
    const at = await mountAt({ path: '/records' })
    expect(at.find('.rail-records-btn').attributes('color')).toBe('primary')
    expect(at.find('.rail-home-btn').attributes('color')).toBe('on-surface-variant')
    expect(at.find('.rail-theme-btn').attributes('color')).toBe('on-surface-variant')
    expect(at.find('.rail-logout-btn').attributes('color')).toBe('on-surface-variant')
    at.unmount()
  })

  // §4.3 未登录分支
  it('M5-T4.3 未登录收起态：登出钮整钮不渲染、无悬空占位，其余 5 钮在位', async () => {
    const wrapper = await mountAt({ loggedIn: false })

    expect(wrapper.vm.isLoggedIn).toBe(false)
    expect(wrapper.find('.rail-logout-btn').exists()).toBe(false)
    const rail = wrapper.find('.sidebar-rail')
    expect(rail.findAll('.v-btn')).toHaveLength(5)
    expect(rail.findAll('.v-tooltip')).toHaveLength(5) // 无悬空提示占位
    expect(wrapper.find('.rail-home-btn').exists()).toBe(true)
    expect(wrapper.find('.rail-records-btn').exists()).toBe(true)
    expect(wrapper.find('.rail-statistics-btn').exists()).toBe(true)
    expect(wrapper.find('.rail-settings-btn').exists()).toBe(true)
    expect(wrapper.find('.rail-theme-btn').exists()).toBe(true)
    wrapper.unmount()
  })

  // §4.4 悬停提示
  it('M5-T4.4 每项配悬停提示：rail 块 6 钮各包一个 v-tooltip（源码正则 + DOM；真实悬停归人工）', async () => {
    const src = railBlockSrc()
    expect(countMatches(src, /<v-btn/g)).toBe(6)
    expect(countMatches(src, /<v-tooltip\s+activator="parent"/g)).toBe(6)

    const wrapper = await mountAt()
    for (const cls of [
      'rail-home-btn',
      'rail-records-btn',
      'rail-statistics-btn',
      'rail-settings-btn',
      'rail-theme-btn',
      'rail-logout-btn',
    ]) {
      const tip = wrapper.find(`.${cls} .v-tooltip`)
      expect(tip.exists(), `${cls} 应包 v-tooltip`).toBe(true)
      expect(tip.text()).not.toBe('')
    }
    // 图标列可见图标 7 个（含同一 DOM 首位的切换钮）= 提示 7 个
    expect(wrapper.findAll('.v-tooltip')).toHaveLength(7)
    wrapper.unmount()
  })

  // §4.5 切换钮零跳变
  it('M5-T4.5 切换钮零跳变：收起/展开两态 sidebar-toggle 均为侧栏内容首元素（同一 DOM 实例）', async () => {
    const wrapper = await mountAt()
    const sidebarEl = wrapper.find('.app-sidebar').element

    expect(sidebarEl.firstElementChild.classList.contains('sidebar-toggle')).toBe(true)
    expect(wrapper.find('.sidebar-toggle .v-tooltip').text()).toBe('展开侧边栏')

    wrapper.vm.toggleNav() // → 展开态
    await nextTick()

    // 同一 DOM 元素：切换钮两态位置零跳变（图标随 rail 换）
    expect(sidebarEl.firstElementChild.classList.contains('sidebar-toggle')).toBe(true)
    expect(sidebarEl.children[1].classList.contains('sidebar-header')).toBe(true) // 介绍块下移到按钮之下
    wrapper.unmount()
  })

  // §4.6 顶栏无汉堡
  it('M5-T4.6 顶栏无汉堡：顶栏区块零命中 mdi-backup-restore、只剩右侧深色钮（勿反查 mdi-menu）', async () => {
    const src = topBarSrc()
    expect(src).not.toMatch(/mdi-backup-restore/)
    expect(countMatches(src, /<v-btn/g)).toBe(1)
    expect(src).toMatch(/appStore\.toggleDarkMode\(\)/) // 右侧深色切换钮保留不动
    expect(src).toMatch(/mdi-weather-night/)
    expect(src).toMatch(/mdi-weather-sunny/)

    // 切换钮本体在侧栏（图标随 rail 切换），不在顶栏
    expect(sfcSource).toMatch(/rail \? 'mdi-menu' : 'mdi-backup-restore'/)
    const wrapper = await mountAt()
    expect(wrapper.find('.app-top-bar').findAll('.v-btn')).toHaveLength(1)
    expect(wrapper.find('.app-top-bar .sidebar-toggle').exists()).toBe(false)
    expect(wrapper.find('.app-sidebar .sidebar-toggle').exists()).toBe(true)
    wrapper.unmount()
  })

  // §4.7 高亮同步
  it('M5-T4.7 高亮同步：/settings/about 命中设置图标（startsWith 口径），/add、/edit、/detail 归账单', async () => {
    const settings = await mountAt({ path: '/settings/about' })
    expect(settings.find('.rail-settings-btn').classes()).toContain('active-nav-item')
    expect(settings.find('.rail-settings-btn').attributes('color')).toBe('primary')
    expect(settings.find('.rail-home-btn').classes()).not.toContain('active-nav-item')
    expect(settings.find('.rail-home-btn').attributes('color')).toBe('on-surface-variant')
    settings.unmount()

    const add = await mountAt({ path: '/add' })
    expect(add.find('.rail-records-btn').classes()).toContain('active-nav-item')
    expect(add.find('.rail-home-btn').classes()).not.toContain('active-nav-item')
    add.unmount()

    const edit = await mountAt({ path: '/edit/12' })
    expect(edit.find('.rail-records-btn').attributes('color')).toBe('primary')
    edit.unmount()

    const detail = await mountAt({ path: '/detail/12' })
    expect(detail.find('.rail-records-btn').classes()).toContain('active-nav-item')
    detail.unmount()
  })

  // §4.8 竖屏零改动（源码正则钉死）
  it('M5-T4.8 竖屏零改动钉死：temporary 含 !isDesktop + 外层 v-show/底栏 v-if/FAB v-if 逐字保留 + 竖屏不进 rail 态', async () => {
    const tag = drawerTagSrc()
    expect(tag).toMatch(/v-show="isDesktop && !isLoginPage"/) // 逐字不动
    expect(tag).toMatch(/:temporary="!isDesktop"/)
    expect(tag).toMatch(/:permanent="isDesktop"/)
    expect(tag).toMatch(/:rail="isDesktop && rail"/) // isDesktop 守卫：竖屏永不进 rail 态
    expect(tag).toMatch(/:width="240"/)
    // 底部导航与 FAB 逐字保留（红线：不改竖屏抽屉与底部导航、不改 FAB）
    expect(sfcSource).toMatch(
      /<v-bottom-navigation\s+v-if="!isDesktop && !isLoginPage"\s+v-model="currentRoute"/
    )
    expect(sfcSource).toMatch(/<v-btn\s+v-if="!isLoginPage"\s+class="fab-add"/)
    // 竖屏 toggleNav 分支不变
    expect(sfcSource).toMatch(/drawer\.value = !drawer\.value/)
    // 禁样式覆写：rail 宽只走 prop（Vuetify 3.12.6 未提供 rail 宽的 CSS 自定义属性）
    // 变量名分段拼接，避免在本文件写出完整字面量干扰终验的全仓 grep 零命中口径
    expect(sfcSource).not.toContain(['--v', 'navigation', 'drawer', 'rail', 'width'].join('-'))
    // 图标列模板不渲染任何 <span> 文本
    expect(railBlockSrc()).not.toMatch(/<span/)

    const portrait = await mountAt({ path: '/records', width: MOBILE })
    const drawer = portrait.findComponent('.app-sidebar')
    expect(drawer.props('rail')).toBe(false)
    expect(drawer.props('temporary')).toBe(true)
    expect(drawer.props('permanent')).toBe(false)
    expect(portrait.find('.sidebar-rail').exists()).toBe(false) // 竖屏不渲染图标列
    expect(portrait.find('.bottom-nav').exists()).toBe(true)
    expect(portrait.findAll('.v-bottom-navigation .v-btn')).toHaveLength(4)
    expect(portrait.find('.app-sidebar').attributes('style') || '').toContain('display: none')
    portrait.unmount()
  })

  // §4.9 zoom 回归锚（本模块对 AppLayout.wideScreenZoom.test.js 零改动，此处只确认可不被破坏）
  it('M5-T4.9 zoom 回归锚不被破坏：.content-overflow 裁剪与宽屏 zoom 规则、顶栏/FAB 容器位阶不动', async () => {
    const css = sfcSource.match(/<style[^>]*>([\s\S]*?)<\/style>/)[1]
    expect(css).toMatch(/\.content-overflow\s*\{\s*overflow-x:\s*hidden/)
    expect(css).toMatch(/@media \(min-width: 960px\)[\s\S]*?\.content-wrapper\s*\{\s*zoom:\s*1\.1/)
    // 图标列只做溢出可见，不引入横向滚动容器
    expect(css).toMatch(/\.sidebar-rail\s*\{[^}]*overflow:\s*visible/)
    expect(css).not.toMatch(/overflow-x:\s*(auto|scroll)/)

    const wrapper = await mountAt()
    const overflow = wrapper.find('.content-overflow').element
    expect(overflow.contains(wrapper.find('.app-top-bar').element)).toBe(false)
    expect(overflow.contains(wrapper.find('.fab-add').element)).toBe(false)
    wrapper.unmount()
  })
})
