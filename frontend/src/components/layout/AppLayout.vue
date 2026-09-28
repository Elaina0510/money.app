<template>
  <v-app :theme="appStore.darkMode ? 'dark' : 'light'">
    <!-- Navigation Drawer (Sidebar) - Desktop only -->
    <v-navigation-drawer
      v-show="isDesktop && !isLoginPage"
      v-model="drawer"
      :permanent="isDesktop"
      :temporary="!isDesktop"
      :rail="isDesktop && rail"
      :rail-width="72"
      :width="240"
      :mobile-breakpoint="0"
      class="app-sidebar"
      elevation="0"
    >
      <!-- 收起/展开切换钮（REQ-011）：rail 态与展开态共用同一 DOM 首位，图标随 rail 切换零跳变 -->
      <v-btn
        icon
        variant="text"
        size="48"
        class="sidebar-toggle"
        :class="{ 'sidebar-toggle--rail': isDesktop && rail }"
        aria-label="切换侧边栏"
        @click="toggleNav()"
      >
        <v-icon>{{ rail ? 'mdi-menu' : 'mdi-backup-restore' }}</v-icon>
        <v-tooltip activator="parent" location="end">
          {{ rail ? '展开侧边栏' : '收起侧边栏' }}
        </v-tooltip>
      </v-btn>

      <!-- 收起态图标列（REQ-010）：宽 = Vuetify rail-width prop（72px），禁样式覆写；
           前景色一律显式传主题色名（未选中 on-surface-variant / 选中 primary）；不渲染任何文本 -->
      <div v-if="isDesktop && rail" class="sidebar-rail">
        <v-btn
          to="/"
          icon
          variant="text"
          size="48"
          class="rail-btn nav-item rail-home-btn"
          :class="{ 'active-nav-item': railActive === '/' }"
          :color="railActive === '/' ? 'primary' : 'on-surface-variant'"
          aria-label="主页"
        >
          <v-icon icon="mdi-view-dashboard-outline" size="24" />
          <v-tooltip activator="parent" location="end">主页</v-tooltip>
        </v-btn>

        <v-btn
          to="/records"
          icon
          variant="text"
          size="48"
          class="rail-btn nav-item rail-records-btn"
          :class="{ 'active-nav-item': railActive === '/records' }"
          :color="railActive === '/records' ? 'primary' : 'on-surface-variant'"
          aria-label="账单"
        >
          <v-icon icon="mdi-format-list-bulleted" size="24" />
          <v-tooltip activator="parent" location="end">账单</v-tooltip>
        </v-btn>

        <v-btn
          to="/statistics"
          icon
          variant="text"
          size="48"
          class="rail-btn nav-item rail-statistics-btn"
          :class="{ 'active-nav-item': railActive === '/statistics' }"
          :color="railActive === '/statistics' ? 'primary' : 'on-surface-variant'"
          aria-label="统计"
        >
          <v-icon icon="mdi-chart-box-outline" size="24" />
          <v-tooltip activator="parent" location="end">统计</v-tooltip>
        </v-btn>

        <v-btn
          to="/settings"
          icon
          variant="text"
          size="48"
          class="rail-btn nav-item rail-settings-btn"
          :class="{ 'active-nav-item': railActive === '/settings' }"
          :color="railActive === '/settings' ? 'primary' : 'on-surface-variant'"
          aria-label="设置"
        >
          <v-icon icon="mdi-cog-outline" size="24" />
          <v-tooltip activator="parent" location="end">设置</v-tooltip>
        </v-btn>

        <v-btn
          icon
          variant="text"
          size="48"
          class="rail-btn rail-theme-btn"
          color="on-surface-variant"
          :aria-label="appStore.darkMode ? '切换为浅色模式' : '切换为深色模式'"
          @click="appStore.toggleDarkMode()"
        >
          <v-icon size="24">{{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}</v-icon>
          <v-tooltip activator="parent" location="end">
            {{ appStore.darkMode ? '浅色模式' : '深色模式' }}
          </v-tooltip>
        </v-btn>

        <!-- 未登录整钮不渲染、无悬空占位（D9） -->
        <v-btn
          v-if="isLoggedIn"
          icon
          variant="text"
          size="48"
          class="rail-btn rail-logout-btn"
          color="on-surface-variant"
          aria-label="退出登录"
          @click="handleLogout"
        >
          <v-icon icon="mdi-logout" size="24" />
          <v-tooltip activator="parent" location="end">退出登录</v-tooltip>
        </v-btn>
      </div>

      <template v-else>
        <!-- App Logo Area（REQ-011：介绍块下移至切换钮之下） -->
        <div class="sidebar-header px-2 py-2 d-flex align-center">
          <v-avatar color="primary" size="28" class="mr-1 flex-shrink-0">
            <v-icon color="white" size="16">mdi-wallet</v-icon>
          </v-avatar>
          <div class="sidebar-header-text" style="min-width: 0" v-show="isDesktop">
            <div class="text-subtitle-2 font-weight-bold text-truncate" style="line-height: 1.2">
              Money App
            </div>
            <div class="text-caption text-truncate page-subtitle">个人记账</div>
          </div>
        </div>

        <v-divider class="mx-2" />

        <!-- Navigation Items -->
        <v-list class="sidebar-nav pa-1" density="compact">
          <v-list-item
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            :active="route.path === item.to"
            :class="{ 'active-nav-item': route.path === item.to }"
            rounded="xl"
            class="nav-item mb-1"
          >
            <template v-slot:prepend>
              <v-icon :icon="item.icon" size="24" />
            </template>
            <v-list-item-title
              class="text-body-2 font-weight-medium"
              :class="{ 'd-none': !isDesktop }"
            >
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </template>

      <template v-slot:append>
        <!-- 收起态不渲染展开态尾部（图标列已含设置/主题/登出，避免文字残留） -->
        <div class="pa-2" v-if="!(isDesktop && rail)">
          <v-list-item
            to="/settings"
            :active="route.path === '/settings'"
            :class="{ 'active-nav-item': route.path === '/settings' }"
            rounded="xl"
            class="nav-item mb-1"
          >
            <template v-slot:prepend>
              <v-icon icon="mdi-cog-outline" size="24" />
            </template>
            <v-list-item-title
              class="text-body-2 font-weight-medium"
              :class="{ 'd-none': !isDesktop }"
            >
              设置
            </v-list-item-title>
          </v-list-item>

          <!-- User info area -->
          <!-- 登录状态显示 -->
          <div class="pa-2 mt-1" v-if="isLoggedIn">
            <v-divider class="mb-2" />
            <div class="d-flex align-center pa-1">
              <v-avatar size="28" color="primary" class="mr-2">
                <span class="text-caption text-white font-weight-bold">{{
                  username.charAt(0)
                }}</span>
              </v-avatar>
              <div class="flex-grow-1 text-truncate">
                <div class="text-caption font-weight-medium text-truncate">{{ username }}</div>
              </div>
              <v-btn icon variant="text" size="x-small" @click="handleLogout" title="退出登录">
                <v-icon size="16">mdi-logout</v-icon>
              </v-btn>
            </div>
          </div>

          <!-- Dark mode toggle -->
          <div class="d-flex align-center pa-1 mt-1">
            <v-icon size="20" class="mr-2">
              {{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}
            </v-icon>
            <v-switch
              :model-value="appStore.darkMode"
              hide-details
              density="compact"
              color="primary"
              class="theme-switch"
              @update:model-value="appStore.toggleDarkMode()"
            />
          </div>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- Main Content Area -->
    <v-main class="main-content" :class="{ 'main-content--locked': isLoginPage }">
      <!-- Top Bar - sticky, must stay outside overflow container -->
      <div class="app-top-bar pa-4 pb-0">
        <div class="d-flex align-center">
          <!-- M5（REQ-011）：原汉堡按钮块已删除，收起/展开切换钮恒在侧栏顶部首位；顶栏右侧深色钮保留 -->
          <div>
            <div class="text-h6 font-weight-bold">{{ currentTitle }}</div>
            <div class="text-caption d-none d-md-block page-subtitle">{{ currentSubtitle }}</div>
          </div>
          <v-spacer />
          <v-btn icon variant="text" size="small" @click="appStore.toggleDarkMode()">
            <v-icon>{{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}</v-icon>
          </v-btn>
        </div>
      </div>

      <!-- Page Content - overflow-x:hidden clips zoom(1.1) without affecting sticky top bar -->
      <div class="content-overflow" :class="{ 'content-overflow--locked': isLoginPage }">
        <div class="content-wrapper" :class="{ 'content-wrapper--bare': isLoginPage }">
          <router-view v-slot="{ Component, route }">
            <!-- Expand transition for detail page -->
            <transition
              v-if="route.path.startsWith('/detail') && appStore.transitionOrigin"
              name="expand"
              mode="out-in"
              @before-enter="onBeforeEnter"
              @enter="onEnter"
              @leave="onLeave"
            >
              <component :is="Component" :key="route.path" />
            </transition>
            <!-- Normal page transition -->
            <transition v-else name="page" mode="out-in">
              <component :is="Component" :key="route.path" />
            </transition>
          </router-view>
        </div>
      </div>
    </v-main>

    <!-- Floating Action Button (FAB) - 右下角常驻加号（登录页隐藏） -->
    <v-btn
      v-if="!isLoginPage"
      class="fab-add"
      color="primary"
      size="large"
      icon
      elevation="4"
      @click="goToAddRecord"
    >
      <v-icon size="28">mdi-plus</v-icon>
    </v-btn>

    <!-- Bottom Navigation Bar - Mobile only（登录页隐藏） -->
    <v-bottom-navigation
      v-if="!isDesktop && !isLoginPage"
      v-model="currentRoute"
      grow
      class="bottom-nav"
    >
      <v-btn value="/" to="/">
        <v-icon>mdi-view-dashboard-outline</v-icon>
        <span>主页</span>
      </v-btn>
      <v-btn value="/records" to="/records">
        <v-icon>mdi-format-list-bulleted</v-icon>
        <span>账单</span>
      </v-btn>
      <v-btn value="/statistics" to="/statistics">
        <v-icon>mdi-chart-box-outline</v-icon>
        <span>统计</span>
      </v-btn>
      <v-btn value="/settings" to="/settings">
        <v-icon>mdi-cog-outline</v-icon>
        <span>设置</span>
      </v-btn>
    </v-bottom-navigation>

    <ToastNotification />
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore'
import { useRecordsStore } from '@/stores/useRecordsStore'
import ToastNotification from '../common/ToastNotification.vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

// 响应式屏幕宽度检测（960px 为桌面/移动端分界线）
const BREAKPOINT = 960
const isDesktop = ref(window.innerWidth >= BREAKPOINT)

const rail = ref(true) // 宽屏默认收起 = 常驻图标列（进页即见）
// v-model 语义 = 抽屉「在位可见」：宽屏 permanent 恒 true（实测 Vuetify 3.12.6，
// permanent + modelValue=false 会给抽屉根挂 inert 并 translateX(-宽) 推出屏外 →
// 收起态图标列将既不可见也不可点，违背 REQ-010「全部可点达」）；
// 竖屏 temporary 维持改版前的「默认关闭」。收起/展开由 rail 切换，模型与可见态不相反。
const drawer = ref(isDesktop.value)

function onResize() {
  isDesktop.value = window.innerWidth >= BREAKPOINT
}

// 登录页判据：以当前路由为 /login 为准（路由守卫保证未登录只会停留在登录页）
// 用于隐藏侧栏/汉堡/FAB/底栏等导航入口，并锁定登录页滚动
const isLoginPage = computed(() => route.path === '/login')

// 登录状态
const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')
const isLoggedIn = computed(() => !!token.value)

// 检查登录状态
function checkLogin() {
  token.value = localStorage.getItem('token') || ''
  username.value = localStorage.getItem('username') || ''
}

// 退出登录
function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('userId')
  // 需求三：清除账单页浏览现场（内存级），避免切换账号后返回现场串号
  useRecordsStore().resetListView()
  checkLogin()
  appStore.showToast('已退出登录', 'info')
}

// 监听外部登出事件（比如 token 过期）
function handleAuthLogout() {
  checkLogin()
  // 不强制跳转，用户可继续浏览但操作会失败
}

function handleAuthLogin() {
  checkLogin()
}

let authLogoutHandler
let authLoginHandler

// v1.4.3 M14（任务 4.2 / D7）：全站展开画面的触发点来源——document 捕获阶段记录最近一次
// pointerdown 坐标，所有对话框（含路由级/程序化打开）天然取到「那一次点击」。
// passive 只读不改事件流；capture 保证内层 stopPropagation 也不丢点。
function onPointerDownCapture(e) {
  appStore.setLastClickOrigin({ x: e.clientX, y: e.clientY })
}

onMounted(() => {
  checkLogin()
  authLogoutHandler = () => handleAuthLogout()
  authLoginHandler = () => handleAuthLogin()
  window.addEventListener('auth:logout', authLogoutHandler)
  window.addEventListener('auth:login', authLoginHandler)
  window.addEventListener('resize', onResize)
  document.addEventListener('pointerdown', onPointerDownCapture, { capture: true, passive: true })
})

onUnmounted(() => {
  window.removeEventListener('auth:logout', authLogoutHandler)
  window.removeEventListener('auth:login', authLoginHandler)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('pointerdown', onPointerDownCapture, { capture: true })
})

// 点击菜单按钮切换侧边栏
function toggleNav() {
  if (isDesktop.value) {
    // 宽屏：rail 图标列 ⇄ 240px 展开；permanent 抽屉始终在位可见 → v-model 同步为 true
    // （收起/展开只由 rail 决定，模型不再与可见态相反）
    rail.value = !rail.value
    drawer.value = true
  } else {
    // 竖屏：切换临时抽屉
    drawer.value = !drawer.value
  }
}

const navItems = [
  { to: '/', title: '主页', icon: 'mdi-view-dashboard-outline' },
  { to: '/records', title: '账单', icon: 'mdi-format-list-bulleted' },
  { to: '/statistics', title: '统计', icon: 'mdi-chart-box-outline' },
]

const currentRoute = computed(() => {
  const path = route.path
  if (path === '/') return '/'
  if (path.startsWith('/records') || path.startsWith('/detail')) return '/records'
  if (path.startsWith('/statistics')) return '/statistics'
  if (path.startsWith('/settings')) return '/settings'
  return '/'
})

// 收起态图标列高亮判据（设计 §6.2）：复用 currentRoute 的前缀判，/add、/edit 同归账单；
// currentRoute 本体不动 —— 竖屏底部导航高亮维持改版前现状（红线：不改底栏）。
const railActive = computed(() => {
  const path = route.path
  if (path.startsWith('/add') || path.startsWith('/edit')) return '/records'
  return currentRoute.value
})

const currentTitle = computed(() => route.meta?.title || 'Money App')

const currentSubtitle = computed(() => {
  const now = new Date()
  const month = now.getMonth() + 1
  const day = now.getDate()
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  const weekday = weekdays[now.getDay()]
  return `${month}月${day}日 星期${weekday}`
})

function goToAddRecord() {
  router.push('/add')
}

// Transition helpers for expand animation
function onBeforeEnter(el) {
  if (appStore.transitionOrigin) {
    const origin = appStore.transitionOrigin
    const rect = el.getBoundingClientRect()
    const x = ((origin.x - rect.left) / rect.width) * 100
    const y = ((origin.y - rect.top) / rect.height) * 100
    el.style.transformOrigin = `${x}% ${y}%`
    el.style.transform = 'scale(0.1)'
    el.style.opacity = '0'
    el.style.transition = 'none'
  }
}

function onEnter(el, done) {
  if (appStore.transitionOrigin) {
    // Force reflow
    el.offsetHeight
    el.style.transition = 'transform 250ms cubic-bezier(0.4, 0, 0.2, 1), opacity 250ms ease'
    el.style.transform = 'scale(1)'
    el.style.opacity = '1'
    el.addEventListener('transitionend', done, { once: true })
  } else {
    // For normal transitions, clear any inline styles and let CSS handle it
    el.style.transform = ''
    el.style.opacity = ''
    el.style.transition = ''
    done()
  }
}

function onLeave(el, done) {
  if (appStore.transitionOrigin) {
    el.style.transition = 'transform 200ms ease, opacity 200ms ease'
    el.style.transform = 'scale(0.95)'
    el.style.opacity = '0'
    el.addEventListener(
      'transitionend',
      () => {
        appStore.setTransitionOrigin(null)
        done()
      },
      { once: true }
    )
  } else {
    // For normal transitions, clear any inline styles and let CSS handle it
    el.style.transform = ''
    el.style.opacity = ''
    el.style.transition = ''
    done()
  }
}

onMounted(() => {
  appStore.initThemeListener()
})
</script>

<style scoped>
.app-sidebar {
  border-right: 1px solid rgba(0, 0, 0, 0.06) !important;
  background: rgb(var(--v-theme-surface)) !important;
}

.sidebar-header {
  min-height: 64px;
}

/* --- M5 收起态图标列（REQ-010）---
   宽度只由 Vuetify :rail-width="72" prop 决定：Vuetify 3.12.6 并未提供 rail 宽对应的
   CSS 自定义属性（实测 lib/components/VNavigationDrawer/_variables.scss 无该变量），
   禁止任何样式覆写路径（审查轮落定 ①）。此处只做单列排布与残留控制。 */
.sidebar-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 4px 0 8px;
  overflow: visible;
}

.rail-btn {
  flex-shrink: 0;
}

/* 收起/展开切换钮（REQ-011 同一 DOM 首位）：展开态靠左上，rail 态水平居中 */
.sidebar-toggle {
  margin: 8px 0 0 8px;
}

.sidebar-toggle--rail {
  display: flex;
  margin: 8px auto 0;
}

.nav-item {
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.06);
}

.nav-item.active-nav-item {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.nav-item.active-nav-item .v-icon {
  color: rgb(var(--v-theme-primary));
}

.main-content {
  min-height: 100vh;
  position: relative;
}

.content-wrapper {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 20px 100px;
  position: relative;
}

/* Overflow container: clips horizontal overflow from zoom(1.1) on wide screens */
.content-overflow {
  overflow-x: hidden;
}

/* --- 登录页沉浸式（M1）：仅在 /login 挂类，非登录页布局完全不变 --- */

/* 登录页：视口高度内锁死，顶栏占自然高度，内容区 flex 撑满剩余空间 */
.main-content--locked {
  height: 100dvh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-overflow--locked {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 登录页不参与宽屏缩放，且不再为底栏/FAB 预留 padding-bottom
   （复合选择器提升优先级，避免被下方媒体查询中的 .content-wrapper 内边距覆盖） */
.content-wrapper.content-wrapper--bare {
  height: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
  zoom: 1 !important;
}

/* Bottom blur gradient */
.content-wrapper::after {
  content: '';
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: min(100%, 640px);
  height: 40px;
  background: linear-gradient(to bottom, transparent, rgb(var(--v-theme-background)));
  pointer-events: none;
  z-index: 50;
}

/* FAB - Floating Action Button */
.fab-add {
  position: fixed !important;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  width: 56px !important;
  height: 56px !important;
  border-radius: 16px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
  transition: all 0.2s ease !important;
}

.fab-add:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2) !important;
}

.theme-switch {
  margin-left: 8px;
}

.app-top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgb(var(--v-theme-background));
  padding-bottom: 12px;
}

/* Top bar blur gradient */
.app-top-bar::after {
  content: '';
  position: absolute;
  bottom: -24px;
  left: 0;
  right: 0;
  height: 24px;
  background: rgb(var(--v-theme-background));
  mask-image: linear-gradient(to bottom, black, transparent);
  -webkit-mask-image: linear-gradient(to bottom, black, transparent);
  pointer-events: none;
  z-index: 99;
}

/* Bottom navigation bar */
.bottom-nav {
  border-top: 1px solid rgba(0, 0, 0, 0.06) !important;
}

.v-theme--dark .bottom-nav {
  border-top-color: rgba(255, 255, 255, 0.06) !important;
}

@media (max-width: 959px) {
  .content-wrapper {
    padding: 16px 16px 100px;
  }

  .fab-add {
    bottom: 80px;
    right: 16px;
  }

  /* 确保移动端侧边栏完全隐藏 */
  .app-sidebar {
    display: none !important;
    transform: translateX(-100%) !important;
    visibility: hidden !important;
  }
}

/* Wide screen 110% scaling
   用 zoom 实现缩放：zoom 参与布局计算，scrollHeight 真实，
   修复宽屏进入页面后首次向下滚动卡住（v1.4.1 需求四 / 决策 D3）。
   zoom 以左上角为原点等比放大，视觉与改前等比一致。 */
@media (min-width: 960px) {
  .content-wrapper {
    zoom: 1.1;
    /* padding-bottom 不再需要乘 1.1：zoom 会把 padding 一并计入布局 */
    padding-bottom: 100px;
  }
}
</style>
