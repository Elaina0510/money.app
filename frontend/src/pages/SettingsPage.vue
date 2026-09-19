<template>
  <div class="settings-page">
    <!-- Page Info -->
    <div class="page-info mb-3">
      <p class="text-caption text-grey">管理分类、标签和数据</p>
    </div>

    <!-- Theme Mode Setting -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex align-center mb-3">
        <v-avatar size="36" color="rgba(139, 126, 116, 0.1)" class="mr-2">
          <v-icon color="primary" size="20">mdi-brightness-6</v-icon>
        </v-avatar>
        <span class="text-subtitle-2 font-weight-bold">外观设置</span>
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
          <v-avatar size="36" color="rgba(103, 80, 164, 0.1)" class="mr-2">
            <v-icon color="primary" size="20">mdi-shape</v-icon>
          </v-avatar>
        </template>
        <v-list-item-title class="text-body-1 font-weight-medium">分类管理</v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          支出 {{ expenseCategories.length }} / 收入 {{ incomeCategories.length }}
        </v-list-item-subtitle>
        <template v-slot:append>
          <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-card>

    <!-- Tags Management (summary entry) -->
    <v-card class="mb-3 settings-card" rounded="xl">
      <v-list-item to="/settings/tags" rounded="xl">
        <template v-slot:prepend>
          <v-avatar size="36" color="rgba(77, 171, 247, 0.1)" class="mr-2">
            <v-icon color="info" size="20">mdi-tag-multiple</v-icon>
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
          <v-avatar size="36" color="rgba(0, 150, 136, 0.1)" class="mr-2">
            <v-icon color="teal" size="20">mdi-lightning-bolt</v-icon>
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

    <!-- Import/Export Section -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex align-center mb-3">
        <v-avatar size="36" color="rgba(33, 150, 243, 0.1)" class="mr-2">
          <v-icon color="blue" size="20">mdi-swap-vertical</v-icon>
        </v-avatar>
        <span class="text-subtitle-2 font-weight-bold">导入导出</span>
      </div>

      <v-list density="compact" class="bg-transparent pa-0">
        <v-list-item @click="handleExportCsv" :disabled="exporting">
          <template v-slot:prepend>
            <v-icon size="20" class="mr-3">mdi-file-delimited-outline</v-icon>
          </template>
          <v-list-item-title class="text-body-2">导出 CSV</v-list-item-title>
          <v-list-item-subtitle class="text-caption">导出账单为 CSV 文件</v-list-item-subtitle>
        </v-list-item>

        <v-list-item @click="triggerCsvImport">
          <template v-slot:prepend>
            <v-icon size="20" class="mr-3">mdi-file-import-outline</v-icon>
          </template>
          <v-list-item-title class="text-body-2">导入 CSV</v-list-item-title>
          <v-list-item-subtitle class="text-caption">从 CSV 文件导入账单</v-list-item-subtitle>
        </v-list-item>

        <v-divider class="my-1" />

        <v-list-item @click="handleExportSql" :disabled="exporting">
          <template v-slot:prepend>
            <v-icon size="20" class="mr-3">mdi-database-export-outline</v-icon>
          </template>
          <v-list-item-title class="text-body-2">导出 SQL</v-list-item-title>
          <v-list-item-subtitle class="text-caption">导出全量数据为 SQL 备份</v-list-item-subtitle>
        </v-list-item>

        <v-list-item @click="triggerSqlImport">
          <template v-slot:prepend>
            <v-icon size="20" class="mr-3">mdi-database-import-outline</v-icon>
          </template>
          <v-list-item-title class="text-body-2">导入 SQL</v-list-item-title>
          <v-list-item-subtitle class="text-caption">从 SQL/SQLite 文件导入数据</v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Data History Entry -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <v-list class="bg-transparent pa-0">
        <v-list-item @click="$router.push('/history')">
          <template v-slot:prepend>
            <v-avatar size="36" color="rgba(255, 152, 0, 0.1)" class="mr-2">
              <v-icon color="orange" size="20">mdi-history</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">数据回溯</v-list-item-title>
          <v-list-item-subtitle class="text-caption">查看操作历史，支持撤销</v-list-item-subtitle>
          <template v-slot:append>
            <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Hidden file inputs -->
    <input
      type="file"
      ref="csvFileInput"
      accept=".csv"
      style="display: none"
      @change="handleCsvFileSelect"
    />
    <input
      type="file"
      ref="sqlFileInput"
      accept=".sql,.db"
      style="display: none"
      @change="handleSqlFileSelect"
    />

    <!-- CSV Mapping Dialog -->
    <CsvMappingDialog
      v-model="showCsvMapping"
      :preview-data="csvPreviewData"
      :categories="categories"
      @confirm="handleCsvImport"
    />

    <!-- SQL Import Preview Dialog -->
    <v-dialog v-model="showSqlConfirm" max-width="400">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-2">确认导入 SQL</v-card-title>
        <v-card-text class="pa-0 mb-4">
          <div class="text-body-2 mb-1">
            文件格式：{{ sqlPreviewData?.format === 'sqlite_binary' ? 'SQLite 数据库' : '文本 SQL' }}
          </div>
          <div class="text-body-2 mb-3">
            数据来源：{{ sqlPreviewData?.is_third_party ? 'Cashew（第三方）' : '本系统' }}
          </div>
          <v-divider class="mb-3" />
          <div class="text-caption text-grey mb-2">数据预览：</div>
          <div v-for="(info, table) in (sqlPreviewData?.tables || {})" :key="table" class="text-body-2">
            {{ table }}：{{ info.count }} 条
          </div>
          <v-divider class="mt-3 mb-2" />
          <div class="text-caption text-grey">
            导入模式：合并（放弃原始 ID，重新分配）
          </div>
        </v-card-text>
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showSqlConfirm = false">取消</v-btn>
          <v-btn color="primary" :loading="importing" @click="handleSqlNext">下一步</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- SQL Mapping Dialog (reuse CsvMappingDialog) -->
    <CsvMappingDialog
      v-model="showSqlMapping"
      :preview-data="sqlPreviewData"
      :categories="categories"
      @confirm="handleSqlImport"
    />

    <!-- Account Section -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex align-center mb-2">
        <v-avatar size="36" color="rgba(255, 152, 0, 0.1)" class="mr-2">
          <v-icon color="warning" size="20">mdi-account</v-icon>
        </v-avatar>
        <span class="text-subtitle-2 font-weight-bold">账号</span>
      </div>

      <div v-if="isLoggedIn" class="d-flex align-center justify-space-between mt-2">
        <div class="d-flex align-center">
          <v-avatar size="36" color="primary" class="mr-2">
            <span class="text-body-2 text-white font-weight-bold">{{ username.charAt(0) }}</span>
          </v-avatar>
          <div>
            <div class="text-body-2 font-weight-medium">{{ username }}</div>
            <div class="text-caption text-grey">已登录</div>
          </div>
        </div>
        <v-btn variant="tonal" color="error" size="small" @click="handleLogoutInSettings">
          <v-icon start size="small">mdi-logout</v-icon>
          退出
        </v-btn>
      </div>

      <div v-else class="mt-2">
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
import dayjs from 'dayjs'
import CsvMappingDialog from '@/components/common/CsvMappingDialog.vue'
import {
  exportCsv,
  exportSql,
  previewCsvImport,
  importCsv,
  previewSqlImport,
  importSql,
} from '@/api/export'

const router = useRouter()

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

// 分类/标签数量直读共享 store（二级页操作后返回即响应式更新）
const { categories, tags } = storeToRefs(categoriesStore)

const expenseCategories = computed(() => categories.value.filter((c) => c.type === 'expense'))
const incomeCategories = computed(() => categories.value.filter((c) => c.type === 'income'))

// 快速记账摘要数量（管理操作已下沉至 /settings/quick-templates）
const quickTemplateCount = ref(0)

// Import/Export state
const exporting = ref(false)
const importing = ref(false)
const csvFileInput = ref(null)
const sqlFileInput = ref(null)
const showCsvMapping = ref(false)
const csvPreviewData = ref(null)
const showSqlConfirm = ref(false)
const showSqlMapping = ref(false)
const sqlPreviewData = ref(null)
const sqlCacheId = ref(null)
const sqlFormat = ref(null)

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

// ── Import/Export ──────────────────────────────────────────────────

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function handleExportCsv() {
  exporting.value = true
  try {
    const blob = await exportCsv()
    const filename = `money_export_${dayjs().format('YYYYMMDD')}.csv`
    downloadBlob(blob, filename)
    appStore.showToast('CSV 导出成功')
  } catch (e) {
    appStore.showToast(e.message || '导出失败', 'error')
  } finally {
    exporting.value = false
  }
}

async function handleExportSql() {
  exporting.value = true
  try {
    const blob = await exportSql()
    const filename = `money_backup_${dayjs().format('YYYYMMDD')}.sql`
    downloadBlob(blob, filename)
    appStore.showToast('SQL 导出成功')
  } catch (e) {
    appStore.showToast(e.message || '导出失败', 'error')
  } finally {
    exporting.value = false
  }
}

function triggerCsvImport() {
  csvFileInput.value?.click()
}

async function handleCsvFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return
  event.target.value = '' // Reset input

  try {
    csvPreviewData.value = await previewCsvImport(file)
    showCsvMapping.value = true
  } catch (e) {
    appStore.showToast(e.message || '文件解析失败', 'error')
  }
}

async function handleCsvImport(mapping) {
  showCsvMapping.value = false
  importing.value = true
  try {
    const result = await importCsv({
      cache_id: csvPreviewData.value.cache_id,
      format: csvPreviewData.value.format,
      category_mapping: mapping.category_mapping,
      tag_mapping: mapping.tag_mapping,
    })
    appStore.showToast(`成功导入 ${result.imported_count} 条记录`)
  } catch (e) {
    appStore.showToast(e.message || '导入失败', 'error')
  } finally {
    importing.value = false
    csvPreviewData.value = null
  }
}

function triggerSqlImport() {
  sqlFileInput.value?.click()
}

async function handleSqlFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return
  event.target.value = '' // Reset input

  try {
    sqlPreviewData.value = await previewSqlImport(file)
    sqlCacheId.value = sqlPreviewData.value.cache_id
    sqlFormat.value = sqlPreviewData.value.format
    showSqlConfirm.value = true
  } catch (e) {
    appStore.showToast(e.message || '文件解析失败', 'error')
  }
}

function handleSqlNext() {
  showSqlConfirm.value = false
  // Show mapping dialog if there are categories/tags to map
  const hasMapping = (sqlPreviewData.value?.categories_in_file?.length > 0) ||
    (sqlPreviewData.value?.tags_in_file?.length > 0)
  if (hasMapping) {
    showSqlMapping.value = true
  } else {
    // No mapping needed, import directly
    handleSqlImport({})
  }
}

async function handleSqlImport(mapping) {
  showSqlMapping.value = false
  importing.value = true
  try {
    const result = await importSql({
      cache_id: sqlCacheId.value,
      format: sqlFormat.value,
      is_third_party: sqlPreviewData.value?.is_third_party || false,
      category_mapping: mapping.category_mapping || null,
      tag_mapping: mapping.tag_mapping || null,
    })
    appStore.showToast(`成功导入 ${result.records_imported} 条记录`)
  } catch (e) {
    appStore.showToast(e.message || '导入失败', 'error')
  } finally {
    importing.value = false
    sqlPreviewData.value = null
    sqlCacheId.value = null
    sqlFormat.value = null
  }
}
</script>

<style scoped>
.settings-page {
  padding-bottom: 20px;
}
</style>
