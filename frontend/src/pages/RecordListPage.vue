<template>
  <div class="records-page">
    <!-- Page Header -->
    <div class="page-header mb-3">
      <h1 class="page-title">账单</h1>
      <p class="page-subtitle">共 {{ totalCount }} 条记录</p>
    </div>

    <!-- Filter Bar -->
    <v-card class="pa-3 mb-3 filter-card" rounded="xl">
      <div class="d-flex align-center ga-2">
        <v-text-field
          v-model="filters.start_date"
          type="date"
          label="开始"
          hide-details
          density="compact"
          variant="outlined"
          class="flex-grow-1"
        />
        <span class="text-grey">-</span>
        <v-text-field
          v-model="filters.end_date"
          type="date"
          label="结束"
          hide-details
          density="compact"
          variant="outlined"
          class="flex-grow-1"
        />
      </div>
      <div class="d-flex align-center ga-2 mt-2">
        <v-select
          v-model="filters.type"
          :items="typeOptions"
          label="类型"
          hide-details
          density="compact"
          variant="outlined"
          clearable
          class="flex-grow-1"
        />
        <v-select
          v-model="filters.category_id"
          :items="categoryOptions"
          item-title="name"
          item-value="id"
          label="分类"
          hide-details
          density="compact"
          variant="outlined"
          clearable
          class="flex-grow-1"
        />
        <v-btn color="primary" variant="tonal" size="small" @click="search" class="search-btn">
          <v-icon>mdi-magnify</v-icon>
        </v-btn>
      </div>
    </v-card>

    <!-- Batch Actions Bar -->
    <div v-if="selected.length > 0" class="batch-bar mb-3">
      <v-card rounded="xl" class="pa-2">
        <div class="d-flex align-center justify-space-between px-2">
          <v-chip color="primary" size="small" class="mr-2">
            已选 {{ selected.length }}
          </v-chip>
          <div class="d-flex ga-1">
            <v-btn color="error" variant="tonal" size="small" @click="showDeleteDialog = true">
              <v-icon start size="small">mdi-delete</v-icon>
              删除
            </v-btn>
            <v-btn variant="text" size="small" @click="selected = []">
              取消
            </v-btn>
          </div>
        </div>
      </v-card>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center pa-8">
      <v-progress-circular indeterminate color="primary" size="32" />
    </div>

    <!-- Records List -->
    <div v-else-if="records.length === 0" class="empty-state-wrapper">
      <v-card class="pa-8 text-center" rounded="xl" variant="outlined">
        <v-icon size="56" color="grey-lighten-1" class="mb-3">mdi-format-list-bulleted</v-icon>
        <p class="text-grey text-body-1 mb-1">暂无账单</p>
        <p class="text-grey-lighten-1 text-caption mb-4">开始记录你的第一笔账单吧</p>
      </v-card>
    </div>

    <div v-else>
      <div v-for="record in records" :key="record.id" class="mb-2">
        <v-card rounded="xl" class="record-card">
          <v-list-item @click="goToDetail(record.id)">
            <template v-slot:prepend>
              <v-avatar
                :color="record.type === 'expense' ? '#FFE8E8' : '#E8FFF3'"
                size="40"
                class="mr-2"
              >
                <v-icon :color="record.type === 'expense' ? '#FF6B6B' : '#20C997'" size="18">
                  {{ record.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
                </v-icon>
              </v-avatar>
            </template>
            <v-list-item-title class="text-body-2 font-weight-medium">
              <v-avatar size="24" color="rgba(139, 126, 116, 0.12)" class="mr-1">
                <v-icon size="14" color="#8B7E74">{{ record.category_icon || 'mdi-circle' }}</v-icon>
              </v-avatar>
              {{ record.tag?.name || record.category_name || '未分类' }}
            </v-list-item-title>
            <v-list-item-subtitle class="d-flex align-center text-caption mt-1">
              <span>{{ record.consume_time?.substring(0, 16) || '' }}</span>
              <v-icon v-if="record.attachment_ids?.length" size="x-small" class="ml-1">
                mdi-paperclip
              </v-icon>
            </v-list-item-subtitle>
            <template v-slot:append>
              <div class="d-flex align-center">
                <div
                  class="font-weight-bold text-body-1 mr-2"
                  :style="{ color: record.type === 'expense' ? '#FF6B6B' : '#20C997' }"
                >
                  {{ record.type === 'expense' ? '-' : '+' }}{{ record.amount }}
                </div>
                <v-icon size="small" color="grey-lighten-1">mdi-chevron-right</v-icon>
              </div>
            </template>
          </v-list-item>
        </v-card>
      </div>

      <!-- Load More -->
      <div v-if="hasMore" class="text-center pa-4">
        <v-btn variant="tonal" color="primary" :loading="loading" @click="loadMore" rounded="xl">
          加载更多
        </v-btn>
      </div>
    </div>

    <!-- Delete Confirm Dialog -->
    <ConfirmDialog
      v-model="showDeleteDialog"
      title="批量删除"
      :message="`确定要删除选中的 ${selected.length} 条记录吗？此操作不可撤销。`"
      confirm-text="删除"
      confirm-color="error"
      @confirm="handleBatchDelete"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getRecords } from '@/api/records'
import { getCategories } from '@/api/categories'
import { useRecordsStore } from '@/stores/useRecordsStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const recordsStore = useRecordsStore()

const records = ref([])
const categories = ref([])
const loading = ref(false)
const selected = ref([])
const showDeleteDialog = ref(false)
const hasMore = ref(false)
const totalCount = ref(0)

const filters = reactive({
  start_date: '',
  end_date: '',
  type: '',
  category_id: null,
})

const typeOptions = [
  { title: '全部', value: '' },
  { title: '支出', value: 'expense' },
  { title: '收入', value: 'income' },
]

const categoryOptions = computed(() => {
  const list = [{ name: '全部分类', id: null }]
  return list.concat(categories.value)
})

function goToDetail(id) {
  router.push(`/detail/${id}`)
}

async function search() {
  loading.value = true
  try {
    const params = { page: 1, page_size: 20 }
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date
    if (filters.type) params.type_filter = filters.type
    if (filters.category_id) params.category_id = filters.category_id
    const result = await getRecords(params)
    records.value = result.items
    totalCount.value = result.total
    hasMore.value = result.page < result.total_pages
  } catch (e) {
    console.error('Search error:', e)
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  await search()
}

async function handleBatchDelete() {
  try {
    await recordsStore.batchDelete(selected.value)
    selected.value = []
    showDeleteDialog.value = false
    await search()
  } catch (e) {
    // Toast shown by store
  }
}

onMounted(async () => {
  try {
    categories.value = await getCategories()
    await search()
  } catch (e) {
    console.error('List load error:', e)
  }
})
</script>

<style scoped>
.records-page {
  padding-bottom: 20px;
}

.page-header {
  padding: 0;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
}

.page-subtitle {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
  margin: 2px 0 0;
}

.filter-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.search-btn {
  min-width: 40px !important;
  height: 40px !important;
}

.record-card {
  transition: all 0.15s ease;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.record-card:hover {
  border-color: rgba(var(--v-theme-primary), 0.2);
  transform: translateX(2px);
  cursor: pointer;
}

.batch-bar {
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-state-wrapper {
  padding-top: 40px;
}
</style>
