<template>
  <div class="history-page">
    <div class="d-flex align-center mb-3">
      <v-btn
        icon
        variant="text"
        size="small"
        class="mr-2"
        @click="$router.back()"
      >
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div>
        <p class="text-caption text-grey mb-0">最近 30 条操作记录</p>
      </div>
    </div>

    <div v-if="loading" class="text-center pa-8">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <div v-else-if="items.length === 0" class="text-center pa-8">
      <v-icon size="64" color="grey-lighten-1">mdi-history</v-icon>
      <p class="text-body-2 text-grey mt-2">暂无操作记录</p>
    </div>

    <v-card v-else rounded="xl" class="mb-4">
      <v-list class="pa-0">
        <template v-for="(item, index) in items" :key="item.id">
          <v-list-item
            class="history-item"
            @click="toggleDetail(item)"
          >
            <template v-slot:prepend>
              <v-avatar size="36" :color="getOperationColor(item.operation_type) + '20'" class="mr-3">
                <v-icon size="20" :color="getOperationColor(item.operation_type)">
                  {{ getOperationIcon(item.operation_type) }}
                </v-icon>
              </v-avatar>
            </template>

            <v-list-item-title class="text-body-2">
              {{ item.description }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ item.created_at }} · 影响 {{ item.affected_count }} 条
            </v-list-item-subtitle>

            <template v-slot:append>
              <v-btn
                size="small"
                variant="tonal"
                color="warning"
                @click.stop="confirmRollback(item)"
              >
                回溯
              </v-btn>
            </template>
          </v-list-item>

          <!-- Expanded detail -->
          <v-expand-transition>
            <div v-if="expandedId === item.id && detail" class="pa-4 pt-0">
              <v-divider class="mb-3" />
              <div class="text-caption text-grey mb-2">涉及账单：</div>
              <v-list density="compact" class="bg-transparent pa-0">
                <v-list-item
                  v-for="(record, idx) in getDetailRecords(item)"
                  :key="idx"
                  class="detail-record-item"
                >
                  <template v-slot:prepend>
                    <span
                      class="text-body-2 font-weight-bold mr-2"
                      :class="record.type === 'income' ? 'text-success' : 'text-error'"
                    >
                      {{ record.type === 'income' ? '+' : '-' }}¥{{ record.amount }}
                    </span>
                  </template>
                  <v-list-item-title class="text-body-2">
                    分类 #{{ record.category_id }}
                    <span v-if="record.tag_id" class="text-grey ml-1">标签 #{{ record.tag_id }}</span>
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    {{ record.consume_time }}
                    <span v-if="record.note" class="ml-1">{{ record.note }}</span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </v-expand-transition>

          <v-divider v-if="index < items.length - 1" />
        </template>
      </v-list>
    </v-card>

    <!-- Rollback Confirm Dialog -->
    <ConfirmDialog
      v-model="showRollbackConfirm"
      title="确认回溯"
      :message="rollbackMessage"
      confirm-text="确认回溯"
      @confirm="handleRollback"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '@/stores/useAppStore'
import { getHistoryList, getHistoryDetail, rollbackHistory } from '@/api/history'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const appStore = useAppStore()

const loading = ref(false)
const items = ref([])
const expandedId = ref(null)
const detail = ref(null)

// Rollback
const showRollbackConfirm = ref(false)
const rollingBackItem = ref(null)
const rollbackMessage = ref('')

const operationIcons = {
  create: { icon: 'mdi-plus-circle-outline', color: 'success' },
  update: { icon: 'mdi-pencil-outline', color: 'info' },
  delete: { icon: 'mdi-delete-outline', color: 'error' },
  batch_delete: { icon: 'mdi-delete-sweep-outline', color: 'error' },
  csv_import: { icon: 'mdi-file-import-outline', color: 'primary' },
  sql_import: { icon: 'mdi-database-import-outline', color: 'primary' },
}

function getOperationIcon(type) {
  return operationIcons[type]?.icon || 'mdi-help-circle-outline'
}

function getOperationColor(type) {
  return operationIcons[type]?.color || 'grey'
}

async function loadHistory() {
  loading.value = true
  try {
    const data = await getHistoryList({ page: 1, page_size: 30 })
    items.value = data.items || []
  } catch (e) {
    appStore.showToast(e.message || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

async function toggleDetail(item) {
  if (expandedId.value === item.id) {
    expandedId.value = null
    detail.value = null
    return
  }
  expandedId.value = item.id
  try {
    detail.value = await getHistoryDetail(item.id)
  } catch (e) {
    appStore.showToast(e.message || '加载详情失败', 'error')
    detail.value = null
  }
}

function getDetailRecords(item) {
  if (!detail.value) return []
  // For create/csv_import/sql_import, show snapshot_after
  if (['create', 'csv_import', 'sql_import'].includes(item.operation_type)) {
    return detail.value.snapshot_after || []
  }
  // For delete/batch_delete/update, show snapshot_before
  return detail.value.snapshot_before || []
}

function confirmRollback(item) {
  rollingBackItem.value = item
  rollbackMessage.value = `确定要回溯「${item.description}」吗？此操作将撤销该操作。`
  showRollbackConfirm.value = true
}

async function handleRollback() {
  if (!rollingBackItem.value) return
  try {
    await rollbackHistory(rollingBackItem.value.id)
    appStore.showToast('回溯成功')
    showRollbackConfirm.value = false
    rollingBackItem.value = null
    expandedId.value = null
    detail.value = null
    await loadHistory()
  } catch (e) {
    appStore.showToast(e.message || '回溯失败', 'error')
  }
}

onMounted(loadHistory)
</script>

<style scoped>
.history-page {
  padding-bottom: 20px;
}

.history-item {
  cursor: pointer;
  transition: background 0.15s ease;
}

.history-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.detail-record-item {
  min-height: 36px;
}
</style>
