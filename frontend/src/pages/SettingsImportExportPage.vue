<template>
  <div class="settings-import-export-page">
    <!-- 页头：返回箭头 + 说明文案（与其他二级页同款，参考 HistoryPage.vue 结构） -->
    <div class="d-flex align-center mb-3">
      <v-btn icon variant="text" size="small" class="mr-2" @click="$router.back()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <p class="text-caption text-grey mb-0">导出账单或从备份恢复</p>
      </div>
    </div>

    <!--
      主体（v1.4.3 M5）：原设置页「导入导出」内联卡整体平移至此（剪切非复制，防双份状态），
      CSV/SQL 两组的现有排布与 v-divider 分组原样保留；
      外层改挂 .page-card 统一卡片图层，行距自动继承 M6 疏朗化口径（行高 48 + 行间 4）。
    -->
    <div class="page-card">
      <v-list density="compact" class="bg-transparent pa-0">
        <v-list-item @click="handleExportCsv" :disabled="exporting">
          <template v-slot:prepend>
            <v-avatar size="36" class="entry-avatar mr-2">
              <v-icon color="primary" size="20">mdi-file-delimited-outline</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-1 font-weight-medium">导出 CSV</v-list-item-title>
          <v-list-item-subtitle class="text-caption">导出账单为 CSV 文件</v-list-item-subtitle>
        </v-list-item>

        <v-list-item @click="triggerCsvImport">
          <template v-slot:prepend>
            <v-avatar size="36" class="entry-avatar mr-2">
              <v-icon color="primary" size="20">mdi-file-import-outline</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-1 font-weight-medium">导入 CSV</v-list-item-title>
          <v-list-item-subtitle class="text-caption">从 CSV 文件导入账单</v-list-item-subtitle>
        </v-list-item>

        <v-divider class="my-1" />

        <v-list-item @click="handleExportSql" :disabled="exporting">
          <template v-slot:prepend>
            <v-avatar size="36" class="entry-avatar mr-2">
              <v-icon color="primary" size="20">mdi-database-export-outline</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-1 font-weight-medium">导出 SQL</v-list-item-title>
          <v-list-item-subtitle class="text-caption">导出全量数据为 SQL 备份</v-list-item-subtitle>
        </v-list-item>

        <v-list-item @click="triggerSqlImport">
          <template v-slot:prepend>
            <v-avatar size="36" class="entry-avatar mr-2">
              <v-icon color="primary" size="20">mdi-database-import-outline</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-1 font-weight-medium">导入 SQL</v-list-item-title>
          <v-list-item-subtitle class="text-caption">从 SQL/SQLite 文件导入数据</v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </div>

    <!-- Hidden file inputs（原样平移，reset 逻辑未动） -->
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
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

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

// 映射弹窗的分类候选直读共享 store（与设置页同源，不另建数据通路）
const { categories } = storeToRefs(categoriesStore)

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

onMounted(() => {
  // 直达 /settings/import-export 时分类可能尚未加载（映射弹窗无候选）→ 补一次拉取；
  // 从设置页进入则 store 已 loaded，不重复请求（保持改版前的请求次数口径）
  if (!categoriesStore.loaded) categoriesStore.fetchCategories()
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
.settings-import-export-page {
  padding-bottom: 20px;
}
</style>
