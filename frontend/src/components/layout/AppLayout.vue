<template>
  <v-app :theme="appStore.darkMode ? 'dark' : 'light'">
    <!-- Navigation Drawer (Sidebar) -->
    <v-navigation-drawer
      v-model="drawer"
      :permanent="display.mdAndUp ? !rail : false"
      :temporary="display.mdAndUp ? rail : true"
      :rail="false"

      :width="display.mdAndUp ? 240 : 72"
      class="app-sidebar"
      elevation="0"
    >
      <!-- App Logo Area -->
      <div class="sidebar-header px-2 py-2 d-flex align-center">
        <v-avatar color="primary" size="28" class="mr-1 flex-shrink-0">
          <v-icon color="white" size="16">mdi-wallet</v-icon>
        </v-avatar>
        <div class="sidebar-header-text" style="min-width:0">
          <div class="text-subtitle-2 font-weight-bold text-truncate" style="line-height: 1.2">Money App</div>
          <div class="text-caption text-truncate" style="color: rgba(0,0,0,0.5)">个人记账</div>
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
          :ripple="false"
        >
          <template v-slot:prepend>
            <v-icon :icon="item.icon" size="24" />
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
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
            :ripple="false"
          >
            <template v-slot:prepend>
              <v-icon icon="mdi-cog-outline" size="24" />
            </template>
            <v-list-item-title class="text-body-2 font-weight-medium">
              设置
            </v-list-item-title>
          </v-list-item>

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
      <!-- Top Bar (Mobile + Desktop) -->
      <div class="app-top-bar pa-4 pb-0">
        <div class="d-flex align-center">
          <!-- Hamburger / Expand button -->
          <v-btn
            icon
            variant="text"
            class="mr-2"
            @click="toggleNav()"
          >
            <v-icon>{{ display.mdAndUp ? (rail ? 'mdi-menu' : 'mdi-close') : 'mdi-menu' }}</v-icon>
          </v-btn>
          <div>
            <div class="text-h6 font-weight-bold">{{ currentTitle }}</div>
            <div class="text-caption d-none d-md-block" style="color: rgba(0,0,0,0.45)">{{ currentSubtitle }}</div>
          </div>
          <v-spacer />
          <v-btn
            icon
            variant="text"
            size="small"
            @click="appStore.toggleDarkMode()"
          >
            <v-icon>{{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}</v-icon>
          </v-btn>
        </div>
      </div>

      <!-- Page Content -->
      <div class="content-wrapper">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </v-main>

    <!-- Floating Action Button (FAB) - 右下角常驻加号 -->
    <v-btn
      class="fab-add"
      color="primary"
      size="large"
      icon
      elevation="4"
      @click="goToAddRecord"
    >
      <v-icon size="28">mdi-plus</v-icon>
    </v-btn>

    <ToastNotification />
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { useAppStore } from '@/stores/useAppStore'
import ToastNotification from '../common/ToastNotification.vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()
const display = useDisplay()
const rail = ref(true)  // 默认折叠
const drawer = ref(false)

// 点击菜单按钮切换侧边栏
function toggleNav() {
  if (display.mdAndUp) {
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
  { to: '/budget', title: '预算', icon: 'mdi-piggy-bank-outline' },
]

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

onMounted(() => {
  // Default to light mode regardless of system preference
  appStore.setDarkMode(false)
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

@media (max-width: 959px) {
  .sidebar-header .sidebar-header-text .text-subtitle-2 {
    font-size: 0.7rem !important;
  }
  .sidebar-header .sidebar-header-text .text-caption {
    font-size: 0.55rem !important;
  }
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

@media (max-width: 959px) {
  .sidebar-nav {
    padding-left: 2px !important;
    padding-right: 2px !important;
  }
  .sidebar-nav .v-list-item {
    padding-left: 2px !important;
    padding-right: 2px !important;
    min-height: 36px !important;
  }
  .sidebar-nav .v-list-item-title {
    font-size: 0.7rem !important;
  }
  .app-sidebar :deep(.v-list-item__prepend) {
    width: auto !important;
    min-width: 0 !important;
  }
  .app-sidebar :deep(.v-list-item__prepend > .v-icon) {
    margin-right: 4px !important;
  }
}

.app-top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgb(var(--v-theme-background));
  padding-bottom: 12px;
}

@media (max-width: 959px) {
  .content-wrapper {
    padding: 16px 16px 80px;
  }

  .fab-add {
    bottom: 16px;
    right: 16px;
  }
}

@media (min-width: 960px) {
  .app-top-bar .d-md-none {
    display: block;
  }
}
</style>
