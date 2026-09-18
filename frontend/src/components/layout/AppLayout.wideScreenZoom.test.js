import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

// ---------------------------------------------------------------------------
// M2 宽屏首次滚动卡顿修复（需求四 / 决策 D3）
// zoom 的真实滚动行为无法在 jsdom 中断言（设计 §2.4：以真机手工验收为准），
// 因此样式类断言按任务文件要求以「源码规则」方式实现 —— 直接解析 AppLayout.vue
// 的 <style> 区块，逐条核对 @media (min-width: 960px) 内规则与联动确认项；
// 结构 / 动画语义类断言用真实挂载（DOM 类绑定、动画回调坐标）验证。
// ---------------------------------------------------------------------------

const routePath = ref('/')

// 可控 appStore 桩：详情页展开动画回调读取 transitionOrigin
const appStoreState = {
  darkMode: false,
  themeMode: 'auto',
  transitionOrigin: null,
  toggleDarkMode: vi.fn(),
  setDarkMode: vi.fn(),
  setThemeMode: vi.fn(),
  initThemeListener: vi.fn(),
  showToast: vi.fn(),
  setTransitionOrigin: vi.fn(),
}

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({
    get path() {
      return routePath.value
    },
    get meta() {
      return { title: routePath.value === '/login' ? '登录' : '主页' }
    },
  }),
}))

vi.mock('@/stores/useAppStore', () => ({
  // 工厂只返回引用，实际读取发生在组件 setup 阶段（惰性求值）
  useAppStore: () => appStoreState,
}))

vi.mock('@/components/common/ToastNotification.vue', () => ({
  default: {
    name: 'ToastNotification',
    template: '<div class="toast-mock"></div>',
  },
}))

import AppLayout from './AppLayout.vue'
// Vite 原生 ?raw 导入：拿到 SFC 源码字符串，用于样式规则的源码级断言
import sfcSource from './AppLayout.vue?raw'

// --- <style> 区块解析工具 ---------------------------------------------------

function stripComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, '')
}

function scopedCss() {
  const styleBlock = sfcSource.match(/<style[^>]*>([\s\S]*?)<\/style>/)
  expect(styleBlock, 'AppLayout.vue 应包含 <style> 区块').toBeTruthy()
  // 去注释 + 压缩空白，便于按单行做规则/声明断言（注释不参与残留判定）
  return stripComments(styleBlock[1]).replace(/\s+/g, ' ').trim()
}

// 取出某个 @media 条件块内部文本（含嵌套规则）；不存在返回 null
function mediaBlock(css, condition) {
  const start = css.indexOf(`@media ${condition}`)
  if (start === -1) return null
  const open = css.indexOf('{', start)
  let depth = 0
  for (let i = open; i < css.length; i += 1) {
    if (css[i] === '{') depth += 1
    if (css[i] === '}') {
      depth -= 1
      if (depth === 0) return css.slice(open + 1, i).trim()
    }
  }
  return null
}

// 取出某选择器的声明文本；不存在返回 null
function ruleBody(css, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  return match ? match[1].trim() : null
}

function declValue(rule, prop) {
  if (!rule) return undefined
  const match = rule.match(new RegExp(`(?:^|;)\\s*${prop}\\s*:\\s*([^;]+)`, 'i'))
  return match ? match[1].trim() : undefined
}

const WIDE_QUERY = '(min-width: 960px)'
const PORTRAIT_QUERY = '(max-width: 959px)'

// --- 挂载工具 ---------------------------------------------------------------

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

// --- 1. 样式修复（任务 §1.1） ----------------------------------------------

describe('AppLayout - M2 宽屏缩放样式修复（zoom）', () => {
  let css

  beforeEach(() => {
    vi.clearAllMocks()
    routePath.value = '/'
    appStoreState.transitionOrigin = null
    css = scopedCss()
  })

  it('M2-T1 宽屏媒体查询内 .content-wrapper 使用 zoom: 1.1（决策 D3）', () => {
    const wide = mediaBlock(css, WIDE_QUERY)
    expect(wide, `应存在 @media ${WIDE_QUERY} 区段`).toBeTruthy()

    const rule = ruleBody(wide, '.content-wrapper')
    expect(rule, '宽屏媒体查询内应存在 .content-wrapper 规则').toBeTruthy()
    expect(declValue(rule, 'zoom')).toBe('1.1')
  })

  it('M2-T2 宽屏媒体查询内已无 transform / transform-origin（根因消除）', () => {
    const rule = ruleBody(mediaBlock(css, WIDE_QUERY), '.content-wrapper')

    expect(declValue(rule, 'transform')).toBeUndefined()
    expect(declValue(rule, 'transform-origin')).toBeUndefined()
    expect(css).not.toContain('scale(1.1)')
    expect(css).not.toContain('transform-origin: top center')
  })

  it('M2-T3 宽屏 padding-bottom 回到 100px（zoom 已把 padding 计入布局）', () => {
    const rule = ruleBody(mediaBlock(css, WIDE_QUERY), '.content-wrapper')

    expect(declValue(rule, 'padding-bottom')).toBe('100px')
    expect(rule).not.toContain('calc(100px * 1.1)')
  })

  it('M2-T4 缩放只作用于宽屏媒体查询与登录页豁免（易错点 5）', () => {
    // 竖屏：无 zoom、无任何缩放，仅内边距/FAB/侧栏规则
    const portrait = mediaBlock(css, PORTRAIT_QUERY)
    expect(portrait, '竖屏媒体查询应保留').toBeTruthy()
    expect(portrait).not.toContain('zoom')
    expect(portrait).not.toContain('scale(')

    // 基础规则不得带 zoom，避免全局误加缩放
    expect(declValue(ruleBody(css, '.content-wrapper'), 'zoom')).toBeUndefined()

    // 全文 zoom 只出现在两处：登录页豁免（M1）与宽屏缩放（M2）
    const zoomDecls = css.match(/zoom\s*:[^;]+/g) || []
    expect(zoomDecls).toHaveLength(2)
    expect(zoomDecls[0]).toContain('1 !important')
    expect(zoomDecls[1]).toContain('1.1')
  })
})

// --- 1.2 联动确认 + 2. 连带核查（任务 §1.2 / §2） ---------------------------

describe('AppLayout - M2 联动与连带核查', () => {
  let css

  beforeEach(() => {
    vi.clearAllMocks()
    routePath.value = '/'
    css = scopedCss()
  })

  it('M2-T5 登录页豁免保留：.content-wrapper--bare 显式 zoom: 1 !important（M1 联动）', () => {
    const bareRule = ruleBody(css, '.content-wrapper.content-wrapper--bare')
    expect(bareRule, 'M1 的登录页豁免规则应保留').toBeTruthy()
    expect(declValue(bareRule, 'zoom')).toBe('1 !important')
  })

  it('M2-T6 横向裁剪容器保留：.content-overflow { overflow-x: hidden }', () => {
    const overflowRule = ruleBody(css, '.content-overflow')
    expect(overflowRule, '.content-overflow 规则应保留').toBeTruthy()
    expect(declValue(overflowRule, 'overflow-x')).toBe('hidden')
  })

  it('M2-T7 合法 transform 残留未被误改（FAB hover、渐变遮罩位移）', () => {
    const fabHover = ruleBody(css, '.fab-add:hover')
    expect(fabHover, '.fab-add:hover 规则应保留').toBeTruthy()
    expect(declValue(fabHover, 'transform')).toBe('scale(1.05)')
    expect(ruleBody(css, '.content-wrapper::after')).toContain('transform: translateX(-50%)')
  })

  it('M2-T8 顶栏 sticky、底部渐变遮罩与 FAB fixed 语义不变', () => {
    expect(declValue(ruleBody(css, '.app-top-bar'), 'position')).toBe('sticky')
    expect(declValue(ruleBody(css, '.content-wrapper::after'), 'position')).toBe('fixed')
    expect(declValue(ruleBody(css, '.fab-add'), 'position')).toContain('fixed')
  })

  it('M2-T9 顶栏与 FAB 位于缩放容器（.content-overflow）之外', async () => {
    const wrapper = await mountAt('/', DESKTOP)

    const contentOverflow = wrapper.find('.content-overflow').element
    expect(contentOverflow.contains(wrapper.find('.app-top-bar').element)).toBe(false)
    expect(contentOverflow.contains(wrapper.find('.fab-add').element)).toBe(false)
    wrapper.unmount()
  })
})

// --- 挂载态与动画坐标语义（任务 §2） ----------------------------------------

describe('AppLayout - M2 宽屏缩放挂载语义', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routePath.value = '/'
    appStoreState.transitionOrigin = null
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('userId')
  })

  it('M2-T10 宽屏非登录页命中缩放容器，登录页命中豁免容器，竖屏不参与缩放', async () => {
    const normal = await mountAt('/', DESKTOP)
    expect(normal.vm.isDesktop).toBe(true)
    const normalWrapper = normal.find('.content-wrapper')
    expect(normalWrapper.exists()).toBe(true)
    expect(normalWrapper.classes()).not.toContain('content-wrapper--bare')
    normal.unmount()

    const login = await mountAt('/login', DESKTOP)
    expect(login.find('.content-wrapper').classes()).toContain('content-wrapper--bare')
    login.unmount()

    const portrait = await mountAt('/records', MOBILE)
    expect(portrait.vm.isDesktop).toBe(false)
    expect(portrait.find('.content-wrapper').classes()).not.toContain('content-wrapper--bare')
    portrait.unmount()
  })

  it('M2-T11 详情页展开动画坐标基于 getBoundingClientRect，zoom 下语义不变', async () => {
    const wrapper = await mountAt('/detail/1', DESKTOP)
    appStoreState.transitionOrigin = { x: 200, y: 300 }

    // 视觉坐标（rect 与 clientX/Y 同一坐标系）：命中元素中心 → 50% 50%
    const el = {
      style: {},
      getBoundingClientRect: () => ({ left: 100, top: 100, width: 400, height: 400 }),
    }
    wrapper.vm.onBeforeEnter(el)
    expect(el.style.transformOrigin).toBe('25% 50%')
    expect(el.style.transform).toBe('scale(0.1)')

    // 无 transitionOrigin 时不写动画内联样式（普通页面切换路径）
    appStoreState.transitionOrigin = null
    const plainEl = { style: {}, getBoundingClientRect: () => ({}) }
    wrapper.vm.onBeforeEnter(plainEl)
    expect(plainEl.style.transformOrigin).toBeUndefined()
    wrapper.unmount()
  })
})
