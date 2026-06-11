<template>
  <v-app :theme="appStore.darkMode ? 'dark' : 'light'">
    <!-- Navigation Drawer (Sidebar) - Desktop only -->
    <v-navigation-drawer
      v-show="isDesktop"
      v-model="drawer"
      :permanent="!rail"
      :temporary="rail"
      :rail="false"
      :width="240"
      :mobile-breakpoint="0"
      class="app-sidebar"
      elevation="0"
    >
      <!-- App Logo Area -->
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

      <template v-slot:append>
        <div class="pa-2">
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
    <v-main class="main-content">
      <!-- Top Bar - sticky, must stay outside overflow container -->
      <div class="app-top-bar pa-4 pb-0">
        <div class="d-flex align-center">
          <!-- Hamburger button - Desktop only -->
          <v-btn v-if="isDesktop" icon variant="text" class="mr-2" @click="toggleNav()">
            <v-icon>{{ rail ? 'mdi-menu' : 'mdi-close' }}</v-icon>
          </v-btn>
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

      <!-- Page Content - overflow-x:hidden clips scale(1.1) without affecting sticky top bar -->
      <div class="content-overflow">
        <div class="content-wrapper">
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

    <!-- Floating Action Button (FAB) - 右下角常驻加号 -->
    <v-btn class="fab-add" color="primary" size="large" icon elevation="4" @click="goToAddRecord">
      <v-icon size="28">mdi-plus</v-icon>
    </v-btn>

    <!-- Bottom Navigation Bar - Mobile only -->
    <v-bottom-navigation v-if="!isDesktop" v-model="currentRoute" grow class="bottom-nav">
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
import ToastNotification from '../common/ToastNotification.vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()
const rail = ref(true) // 默认折叠
const drawer = ref(false)

// 响应式屏幕宽度检测（960px 为桌面/移动端分界线）
const BREAKPOINT = 960
const isDesktop = ref(window.innerWidth >= BREAKPOINT)

function onResize() {
  isDesktop.value = window.innerWidth >= BREAKPOINT
}

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

onMounted(() => {
  checkLogin()
  authLogoutHandler = () => handleAuthLogout()
  authLoginHandler = () => handleAuthLogin()
  window.addEventListener('auth:logout', authLogoutHandler)
  window.addEventListener('auth:login', authLoginHandler)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('auth:logout', authLogoutHandler)
  window.removeEventListener('auth:login', authLoginHandler)
  window.removeEventListener('resize', onResize)
})

// 点击菜单按钮切换侧边栏
function toggleNav() {
  if (isDesktop.value) {
    // 宽屏：如果当前折叠(rail=true)，切换为展开并显示；如果展开(rail=false)，切换为折叠
    if (rail.value) {
      // 折叠→展开：设为 permanent 显示
      rail.value = false
      drawer.value = true
    } else {
      // 展开→折叠：设为 temporary 隐藏
      rail.value = true
      drawer.value = false
    }
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

/* Overflow container: clips horizontal overflow from scale(1.1) on wide screens */
.content-overflow {
  overflow-x: hidden;
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

/* Wide screen 110% scaling */
@media (min-width: 960px) {
  .content-wrapper {
    transform: scale(1.1);
    transform-origin: top center;
    padding-bottom: calc(100px * 1.1);
  }
}
</style>
