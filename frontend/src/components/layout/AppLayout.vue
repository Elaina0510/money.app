<template>
  <v-app :theme="appStore.darkMode ? 'dark' : 'light'">
    <!-- Navigation Drawer (Sidebar) -->
    <v-navigation-drawer
      v-model="drawer"
      :permanent="$vuetify.display.mdAndUp"
      :temporary="$vuetify.display.smAndDown"
      :rail="$vuetify.display.mdAndUp && rail"
      rail-width="72"
      width="260"
      class="app-sidebar"
      elevation="0"
    >
      <!-- App Logo Area -->
      <div class="sidebar-header pa-4 d-flex align-center" :class="{ 'justify-center': rail }">
        <v-avatar color="primary" size="40" class="mr-3" v-if="!rail">
          <v-icon color="white" size="24">mdi-wallet</v-icon>
        </v-avatar>
        <v-avatar color="primary" size="40" v-else>
          <v-icon color="white" size="24">mdi-wallet</v-icon>
        </v-avatar>
        <div v-if="!rail">
          <div class="text-h6 font-weight-bold" style="line-height: 1.2">Money App</div>
          <div class="text-caption" style="color: rgba(0,0,0,0.5)">个人记账</div>
        </div>
      </div>

      <v-divider class="mx-3" />

      <!-- Navigation Items -->
      <v-list class="sidebar-nav pa-2" density="comfortable">
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
        <div class="pa-3">
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
          <div class="d-flex align-center pa-3 mt-2" :class="{ 'justify-center': rail }">
            <v-icon size="20" class="mr-2" v-if="!rail">
              {{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}
            </v-icon>
            <v-switch
              v-if="!rail"
              :model-value="appStore.darkMode"
              hide-details
              density="compact"
              color="primary"
              class="theme-switch"
              @update:model-value="appStore.toggleDarkMode()"
            />
            <v-btn v-else icon variant="text" size="small" @click="appStore.toggleDarkMode()">
              <v-icon>{{ appStore.darkMode ? 'mdi-weather-night' : 'mdi-weather-sunny' }}</v-icon>
            </v-btn>
          </div>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- Main Content Area -->
    <v-main class="main-content">
      <!-- Mobile Top Bar -->
      <div class="mobile-top-bar d-md-none pa-4 pb-0">
        <div class="d-flex align-center">
          <v-app-bar-nav-icon variant="text" @click="drawer = !drawer" class="mr-2" />
          <div>
            <div class="text-h6 font-weight-bold">{{ currentTitle }}</div>
            <div class="text-caption" style="color: rgba(0,0,0,0.45)">{{ currentSubtitle }}</div>
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
const rail = ref(true)
const drawer = ref(false)

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
  min-height: 72px;
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
  .content-wrapper {
    padding: 16px 16px 80px;
  }

  .mobile-top-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgb(var(--v-theme-background));
    padding-bottom: 12px;
  }

  .fab-add {
    bottom: 16px;
    right: 16px;
  }
}
</style>
