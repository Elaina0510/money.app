<template>
  <div class="settings-page">
    <!-- Page Info -->
    <div class="page-info mb-3">
      <p class="text-caption text-grey">管理分类、标签和数据</p>
    </div>

    <!-- Theme Mode Setting -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex align-center mb-3">
        <v-avatar size="36" class="entry-avatar mr-2">
          <v-icon color="primary" size="20">mdi-brightness-6</v-icon>
        </v-avatar>
        <span class="text-body-1 font-weight-medium">外观设置</span>
      </div>

      <v-btn-toggle
        :model-value="appStore.themeMode"
        mandatory
        rounded="xl"
        density="compact"
        color="primary"
        class="w-100"
        @update:model-value="appStore.setThemeMode"
      >
        <v-btn value="auto" class="flex-grow-1">
          <v-icon start>mdi-brightness-auto</v-icon>
          自动
        </v-btn>
        <v-btn value="light" class="flex-grow-1">
          <v-icon start>mdi-weather-sunny</v-icon>
          浅色
        </v-btn>
        <v-btn value="dark" class="flex-grow-1">
          <v-icon start>mdi-weather-night</v-icon>
          深色
        </v-btn>
      </v-btn-toggle>
    </v-card>

    <!-- Category Management (summary entry) -->
    <v-card class="mb-3 settings-card" rounded="xl">
      <v-list-item to="/settings/categories" rounded="xl">
        <template v-slot:prepend>
          <v-avatar size="36" class="entry-avatar mr-2">
            <v-icon color="primary" size="20">mdi-shape</v-icon>
          </v-avatar>
        </template>
        <v-list-item-title class="text-body-1 font-weight-medium">分类管理</v-list-item-title>
        <v-list-item-subtitle class="text-caption">{{ categories.length }} 个分类</v-list-item-subtitle>
        <template v-slot:append>
          <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-card>

    <!-- Tags Management (summary entry) -->
    <v-card class="mb-3 settings-card" rounded="xl">
      <v-list-item to="/settings/tags" rounded="xl">
        <template v-slot:prepend>
          <v-avatar size="36" class="entry-avatar mr-2">
            <v-icon color="primary" size="20">mdi-tag-multiple</v-icon>
          </v-avatar>
        </template>
        <v-list-item-title class="text-body-1 font-weight-medium">标签管理</v-list-item-title>
        <v-list-item-subtitle class="text-caption">{{ tags.length }} 个</v-list-item-subtitle>
        <template v-slot:append>
          <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-card>

    <!-- Quick Template Management (summary entry) -->
    <v-card class="mb-3 settings-card" rounded="xl">
      <v-list-item to="/settings/quick-templates" rounded="xl">
        <template v-slot:prepend>
          <v-avatar size="36" class="entry-avatar mr-2">
            <v-icon color="primary" size="20">mdi-lightning-bolt</v-icon>
          </v-avatar>
        </template>
        <v-list-item-title class="text-body-1 font-weight-medium">快速记账</v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          {{ quickTemplateCount }} 个模板
        </v-list-item-subtitle>
        <template v-slot:append>
          <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-card>

    <!-- Import/Export (summary entry, M5: 功能已迁至 /settings/import-export) -->
    <v-card class="mb-3 settings-card" rounded="xl">
      <v-list-item to="/settings/import-export" rounded="xl">
        <template v-slot:prepend>
          <v-avatar size="36" class="entry-avatar mr-2">
            <v-icon color="primary" size="20">mdi-swap-vertical</v-icon>
          </v-avatar>
        </template>
        <v-list-item-title class="text-body-1 font-weight-medium">导入导出</v-list-item-title>
        <v-list-item-subtitle class="text-caption">导出 CSV/SQL，导入备份文件</v-list-item-subtitle>
        <template v-slot:append>
          <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-card>

    <!-- Data History Entry -->
    <v-card class="mb-3 settings-card" rounded="xl">
      <v-list class="bg-transparent pa-0">
        <v-list-item @click="$router.push('/history')">
          <template v-slot:prepend>
            <v-avatar size="36" class="entry-avatar mr-2">
              <v-icon color="primary" size="20">mdi-history</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-1 font-weight-medium">数据回溯</v-list-item-title>
          <v-list-item-subtitle class="text-caption">查看操作历史，支持撤销</v-list-item-subtitle>
          <template v-slot:append>
            <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Account Section -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex align-center mb-2">
        <v-avatar size="36" class="entry-avatar mr-2">
          <v-icon color="primary" size="20">mdi-account</v-icon>
        </v-avatar>
        <span class="text-body-1 font-weight-medium">账号</span>
      </div>

      <div v-if="isLoggedIn" class="account-user-row d-flex align-center justify-space-between mt-2">
        <div class="d-flex align-center">
          <v-avatar size="36" color="primary" class="mr-2">
            <span class="text-body-2 text-white font-weight-bold">{{ username.charAt(0) }}</span>
          </v-avatar>
          <div>
            <div class="text-body-1 font-weight-medium">{{ username }}</div>
            <div class="text-caption text-grey">已登录</div>
          </div>
        </div>
        <v-btn variant="tonal" color="error" size="small" @click="handleLogoutInSettings">
          <v-icon start size="small">mdi-logout</v-icon>
          退出
        </v-btn>
      </div>

      <div v-else class="account-user-row mt-2">
        <div class="text-body-2 text-grey mb-3">未登录，部分功能可能受限</div>
        <v-btn color="primary" variant="tonal" @click="goToLogin">
          <v-icon start>mdi-login</v-icon>
          去登录
        </v-btn>
      </div>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import { getQuickTemplates } from '@/api/records'

const router = useRouter()

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

// 分类/标签数量直读共享 store（二级页操作后返回即响应式更新）
// v1.4.3 M8：分类收支共用，原按 type 过滤的 expenseCategories / incomeCategories 已删除
const { categories, tags } = storeToRefs(categoriesStore)

// 快速记账摘要数量（管理操作已下沉至 /settings/quick-templates）
const quickTemplateCount = ref(0)

// 账号状态
const isLoggedIn = computed(() => !!localStorage.getItem('token'))
const username = computed(() => localStorage.getItem('username') || '')

function goToLogin() {
  router.push('/login')
}

function handleLogoutInSettings() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('userId')
  appStore.showToast('已退出登录', 'info')
  // 刷新页面让路由守卫重新检查
  router.push('/login')
}

async function loadQuickTemplates() {
  try {
    const templates = (await getQuickTemplates()) || []
    quickTemplateCount.value = templates.length
  } catch (e) {
    console.error('Load quick templates error:', e)
    quickTemplateCount.value = 0
  }
}

async function loadCategories() {
  try {
    await categoriesStore.fetchCategories()
  } catch (e) {
    console.error('Load categories error:', e)
  }
}

onMounted(async () => {
  // 标签摘要真实数量来源：进入即拉全量标签数组（后端已解除 20 条上限）。
  // store 的标签拉取内部已 try/catch 不外抛 → fire-and-forget 安全；
  // 红线：不新增本地同名薄包装函数，直接调 store 方法（用例 6b 零命中断言）
  categoriesStore.fetchTags()
  await Promise.all([loadCategories(), loadQuickTemplates()])
})
</script>

<style scoped>
.settings-page {
  padding-bottom: 20px;
}

/* v1.4.3 M7 账号区用户行与标题行图标文字起点同列缩进：
   44px = 标题行头像 36px + mr-2 8px（与导入导出区块内层列表项二级缩进模式统一） */
.account-user-row {
  padding-left: 44px;
}
</style>
