<template>
  <div class="records-page">
    <!-- Page Info -->
    <div class="page-info mb-3">
      <p class="text-caption text-grey">共 {{ totalCount }} 条记录</p>
    </div>

    <!-- Filter Bar -->
    <v-card class="pa-4 mb-3 filter-card" rounded="xl">
      <v-row dense>
        <v-col cols="6" sm="3">
          <DatePickerPopover v-model="filters.start_date" label="开始日期" />
        </v-col>
        <v-col cols="6" sm="3">
          <DatePickerPopover v-model="filters.end_date" label="结束日期" />
        </v-col>
        <v-col cols="6" sm="3">
          <v-select
            v-model="filters.type"
            :items="typeOptions"
            label="类型"
            hide-details
            density="compact"
            variant="outlined"
            clearable
            rounded="lg"
            bg-color="surface"
            prepend-inner-icon="mdi-swap-vertical"
          />
        </v-col>
        <v-col cols="6" sm="3">
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
            rounded="lg"
            bg-color="surface"
            prepend-inner-icon="mdi-shape-outline"
          />
        </v-col>
      </v-row>
    </v-card>

    <!-- Month Switcher -->
    <v-card class="pa-2 mb-3" rounded="xl">
      <div class="d-flex align-center">
        <v-btn
          v-if="selectedYear !== currentYear - 5"
          icon
          variant="text"
          size="x-small"
          class="d-none d-md-flex"
          @click="prevYear"
        >
          <v-icon size="small">mdi-chevron-left</v-icon>
        </v-btn>
        <div class="d-flex ga-1 overflow-x-auto flex-grow-1 pb-1" style="scrollbar-width: none">
          <div v-for="m in 12" :key="m" class="text-center flex-shrink-0" style="min-width: 48px">
            <v-chip
              :color="selectedMonth === m && selectedYear === currentYear ? 'primary' : ''"
              :variant="selectedMonth === m ? 'flat' : 'text'"
              size="small"
              rounded="xl"
              @click="selectMonth(m)"
            >
              {{ m }}月
            </v-chip>
            <div
              v-if="selectedYear !== currentYear"
              class="text-caption text-grey"
              style="font-size: 10px; line-height: 1; margin-top: 2px"
            >
              {{ selectedYear }}
            </div>
          </div>
        </div>
        <v-btn
          v-if="selectedYear < currentYear"
          icon
          variant="text"
          size="x-small"
          class="d-none d-md-flex"
          @click="nextYear"
        >
          <v-icon size="small">mdi-chevron-right</v-icon>
        </v-btn>
      </div>
    </v-card>

    <!-- Batch Actions Bar -->
    <div v-if="selected.length > 0" class="batch-bar mb-3">
      <v-card rounded="xl" class="pa-2">
        <div class="d-flex align-center justify-space-between px-2">
          <v-chip color="primary" size="small" class="mr-2"> 已选 {{ selected.length }} </v-chip>
          <div class="d-flex ga-1">
            <v-btn color="error" variant="tonal" size="small" @click="showDeleteDialog = true">
              <v-icon start size="small">mdi-delete</v-icon>
              删除
            </v-btn>
            <v-btn variant="text" size="small" @click="selected = []"> 取消 </v-btn>
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
          <v-list-item @click="goToDetail($event, record.id)">
            <template v-slot:prepend>
              <v-avatar
                :color="record.type === 'expense' ? '#FFE8E8' : '#E8FFF3'"
                size="40"
                class="mr-2"
              >
                <v-icon :color="record.type === 'expense' ? '#FF6B6B' : '#20C997'" size="20">
                  {{ record.category_icon || 'mdi-circle' }}
                </v-icon>
              </v-avatar>
            </template>
            <v-list-item-title class="text-body-2 font-weight-medium">
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getRecords } from '@/api/records'
import { getCategories } from '@/api/categories'
import { useRecordsStore } from '@/stores/useRecordsStore'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DatePickerPopover from '@/components/common/DatePickerPopover.vue'

const router = useRouter()
const recordsStore = useRecordsStore()
const appStore = useAppStore()

const records = ref([])
const categories = ref([])
const loading = ref(false)
const selected = ref([])
const showDeleteDialog = ref(false)
const hasMore = ref(false)
const totalCount = ref(0)

// Use store's filters so they persist across page navigation
const filters = recordsStore.filters

const typeOptions = [
  { title: '全部', value: '' },
  { title: '支出', value: 'expense' },
  { title: '收入', value: 'income' },
]

const categoryOptions = computed(() => {
  const list = [{ name: '全部分类', id: null }]
  if (filters.type) {
    // Filter categories by selected type
    const filtered = categories.value.filter((c) => c.type === filters.type)
    return list.concat(filtered)
  }
  return list.concat(categories.value)
})

const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())
const currentYear = new Date().getFullYear()

function selectMonth(month) {
  selectedMonth.value = month
  const start = `${selectedYear.value}-${String(month).padStart(2, '0')}-01`
  const endDate = new Date(selectedYear.value, month, 0)
  const end = `${selectedYear.value}-${String(month).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`
  filters.start_date = start
  filters.end_date = end
  search()
}

function prevYear() {
  selectedYear.value--
  selectedMonth.value = null
}
function nextYear() {
  if (selectedYear.value < currentYear) {
    selectedYear.value++
    selectedMonth.value = null
  }
}

function goToDetail(event, id) {
  // Get the click position for expand animation
  const rect = event.currentTarget.getBoundingClientRect()
  const x = rect.left + rect.width / 2
  const y = rect.top + rect.height / 2
  appStore.setTransitionOrigin({ x, y })
  router.push(`/detail/${id}`)
}

async function search() {
  loading.value = true
  try {
    const params = { page: 1, page_size: 20 }
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date
    if (filters.type) params.type = filters.type
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

// 筛选条件变化时自动触发搜索（防抖 300ms）
let searchDebounceTimer = null
watch(
  () => [filters.start_date, filters.end_date, filters.type, filters.category_id],
  () => {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = setTimeout(() => {
      search()
    }, 300)
  }
)

// When type changes, clear selected category
watch(
  () => filters.type,
  () => {
    filters.category_id = null
  }
)

async function handleBatchDelete() {
  try {
    await recordsStore.batchDelete(selected.value)
    selected.value = []
    showDeleteDialog.value = false
    await search()
  } catch {
    // Toast shown by store
  }
}

onMounted(async () => {
  try {
    categories.value = await getCategories()
    selectMonth(new Date().getMonth() + 1)
  } catch (e) {
    console.error('List load error:', e)
  }
})
</script>

<style scoped>
.records-page {
  padding-bottom: 20px;
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
