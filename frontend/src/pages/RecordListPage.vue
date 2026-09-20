<template>
  <div class="records-page">
    <!-- Page Info -->
    <div class="page-info mb-3">
      <p class="text-caption text-grey">共 {{ totalCount }} 条记录</p>
    </div>

    <!-- Filter Bar：需求八——仅保留日期两项，类型/分类筛选入口已下线（store 字段与后端参数保留） -->
    <v-card class="pa-4 mb-3 filter-card" rounded="xl">
      <v-row dense>
        <v-col cols="6">
          <DatePickerPopover v-model="filters.start_date" label="开始日期" />
        </v-col>
        <v-col cols="6">
          <DatePickerPopover v-model="filters.end_date" label="结束日期" />
        </v-col>
      </v-row>
    </v-card>

    <!-- Month Switcher：需求三——整体放大 + 选中月滚动居中（居中逻辑见 centerSelectedMonth） -->
    <v-card class="pa-3 mb-3" rounded="xl">
      <div class="d-flex align-center">
        <v-btn
          v-if="selectedYear > minYear"
          icon
          variant="text"
          size="small"
          @click="prevYear"
        >
          <v-icon size="20">mdi-chevron-left</v-icon>
        </v-btn>
        <div ref="monthScroller" class="month-scroller">
          <div
            v-for="m in 12"
            :key="m"
            :ref="(el) => (chipRefs[m - 1] = el)"
            class="text-center flex-shrink-0"
            style="min-width: 64px"
          >
            <v-chip
              :color="selectedMonth === m ? 'primary' : ''"
              :variant="selectedMonth === m ? 'flat' : 'text'"
              class="text-subtitle-2 font-weight-medium"
              size="default"
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
          size="small"
          @click="nextYear"
        >
          <v-icon size="20">mdi-chevron-right</v-icon>
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

    <!-- Refreshing：已有列表时仅顶部细进度条，列表内容不闪没 -->
    <v-progress-linear
      v-if="refreshing"
      indeterminate
      color="primary"
      height="2"
      rounded
      class="mb-2"
    />

    <!-- Loading State：仅首屏（无数据）整块 spinner -->
    <div v-if="loading && records.length === 0" class="text-center pa-8">
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
        <v-btn variant="tonal" color="primary" :loading="refreshing" rounded="xl" @click="loadMore">
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
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getRecords, getEarliestYear } from '@/api/records'
import { useRecordsStore } from '@/stores/useRecordsStore'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DatePickerPopover from '@/components/common/DatePickerPopover.vue'

const router = useRouter()
const recordsStore = useRecordsStore()
const appStore = useAppStore()

const records = ref([])
const loading = ref(false) // 首屏：无列表时的整块 spinner
const refreshing = ref(false) // 已有列表时的后台刷新：仅顶部细进度条
const selected = ref([])
const showDeleteDialog = ref(false)
const hasMore = ref(false)
const totalCount = ref(0)
const pageNum = ref(1)

// 同参数去重键：一次筛选变化被显式调用与 watch 防抖重复触发时只发一次请求
let lastQueryKey = ''

// Use store's filters so they persist across page navigation
const filters = recordsStore.filters

const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())
const currentYear = new Date().getFullYear()
const minYear = ref(null) // null = 未加载；加载后为当前用户最早记录年份

// 需求三：选中月滚动居中。monthScroller = 月份条横滚容器，chipRefs[m-1] = 第 m 个月的外层 wrapper
const monthScroller = ref(null)
const chipRefs = ref([])

// 居中只作用于月份条容器自身。红线：不用 scrollIntoView——它会连带垂直滚动祖先一起滚，
// 打断详情页返回现场滚动恢复；scrollTo 可选调用兼容无布局环境（jsdom 未实现 Element.scrollTo）
async function centerSelectedMonth({ smooth = true } = {}) {
  const scroller = monthScroller.value
  if (!scroller) return
  const behavior = smooth ? 'smooth' : 'auto'
  if (selectedMonth.value == null) {
    // 翻年后无选中月（全年视图）：条回卷左端，显示 1 月侧
    scroller.scrollTo?.({ left: 0, behavior })
    return
  }
  await nextTick()
  const chip = chipRefs.value[selectedMonth.value - 1]
  if (!chip) return
  const left = chip.offsetLeft - (scroller.clientWidth - chip.offsetWidth) / 2
  scroller.scrollTo?.({ left: Math.max(left, 0), behavior })
}

// 年份可往前翻到的边界 = 用户最早有记录的年份（无记录则为当前年）
async function loadEarliestYear() {
  try {
    const result = await getEarliestYear()
    // 无记录用户：minYear = 当前年 → 上一年箭头隐藏
    minYear.value = result?.earliest_year ?? currentYear
  } catch {
    minYear.value = currentYear // 接口异常兜底：退化为"仅当前年"，不阻塞账单浏览
  }
}

// 只写日期区间：请求由防抖 watch 统一驱动（同参再被去重兜底），避免一次点击两次请求
async function selectMonth(month, { smooth = true } = {}) {
  selectedMonth.value = month
  const start = `${selectedYear.value}-${String(month).padStart(2, '0')}-01`
  const endDate = new Date(selectedYear.value, month, 0)
  const end = `${selectedYear.value}-${String(month).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`
  filters.start_date = start
  filters.end_date = end
  await centerSelectedMonth({ smooth })
}

async function prevYear() {
  if (minYear.value !== null && selectedYear.value - 1 < minYear.value) return
  selectedYear.value--
  selectedMonth.value = null
  await centerSelectedMonth() // 无选中月 → 回卷左端显示 1 月侧
}
async function nextYear() {
  if (selectedYear.value < currentYear) {
    selectedYear.value++
    selectedMonth.value = null
    await centerSelectedMonth() // 同上：翻年即全年视图，条回卷左端
  }
}

function goToDetail(event, id) {
  // Get the click position for expand animation
  const rect = event.currentTarget.getBoundingClientRect()
  const x = rect.left + rect.width / 2
  const y = rect.top + rect.height / 2
  appStore.setTransitionOrigin({ x, y })
  // 需求三：仅"点进详情"这条路径记录浏览现场（返回时恢复年月与滚动位置）；
  // 不用 onBeforeUnmount，避免跳去记一笔/编辑或切底栏离开时也记住现场
  recordsStore.rememberListView({
    year: selectedYear.value,
    month: selectedMonth.value,
    scrollTop: window.scrollY,
  })
  router.push(`/detail/${id}`)
}

// 请求参数：页码 + 页大小 + 两个日期（需求八：不再携带 type/category_id）
function buildQuery() {
  const params = { page: pageNum.value, page_size: 20 }
  if (filters.start_date) params.start_date = filters.start_date
  if (filters.end_date) params.end_date = filters.end_date
  return params
}

async function search({ append = false, force = false } = {}) {
  if (!append) pageNum.value = 1
  const params = buildQuery()
  const key = JSON.stringify(params) // 去重键含页码，避免加载更多被同参吞掉
  if (!force && key === lastQueryKey) return // 去重：显式调用与 watch 防抖同参只发一次
  lastQueryKey = key
  // 加载态分流：无列表→整块 spinner；已有列表→仅顶部细进度条（消除整块闪没）
  if (append || records.value.length > 0) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  try {
    const result = await getRecords(params)
    records.value = append ? [...records.value, ...result.items] : result.items
    totalCount.value = result.total
    hasMore.value = result.page < result.total_pages
  } catch (e) {
    console.error('Search error:', e)
    lastQueryKey = '' // 失败清空去重键，否则同参重试会被去重吞掉
    if (append) pageNum.value -= 1 // 追加失败回退页码，避免下次加载更多跳页
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

// 加载更多：页码递增后以 append + force 追加，不参与去重跳过
async function loadMore() {
  pageNum.value += 1
  await search({ append: true, force: true })
}

// 日期筛选变化时自动触发搜索（防抖 300ms）；依赖数组仅两个日期字段，不监听整个 filters
let searchDebounceTimer = null
watch(
  () => [filters.start_date, filters.end_date],
  () => {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = setTimeout(() => search(), 300)
  }
)

async function handleBatchDelete() {
  try {
    await recordsStore.batchDelete(selected.value)
    selected.value = []
    showDeleteDialog.value = false
    await search({ force: true }) // 服务端数据已变：绕过同参去重强制重查
  } catch {
    // Toast shown by store
  }
}

onMounted(async () => {
  loadEarliestYear() // 与下方首屏加载并行发起；内部已兜底，失败不阻塞账单浏览
  const saved = recordsStore.consumeListView()
  if (saved) {
    // 需求三：从详情页返回——只恢复年月，不重置也不重写 filters（其值就是离开时的区间），
    // 否则会触发 M4 的日期防抖 watch → 双请求 / 闪回当前月（回归缺陷）
    selectedYear.value = saved.year
    selectedMonth.value = saved.month
    await search() // 本次挂载唯一一次请求；同参时由去重兜底
    await nextTick()
    // 列表撑开前 scrollTo 会被钳制，故等一帧再恢复滚动位置
    window.requestAnimationFrame(() => window.scrollTo({ top: saved.scrollTop }))
    // 需求三：返回现场同样居中（首屏语义 → 即时定位，不播放滚动动画）
    await centerSelectedMonth({ smooth: false })
  } else {
    // 需求三：首屏即时定位到当前月（smooth:false → 进入页面不出现"自己滑过去"）
    await selectMonth(new Date().getMonth() + 1, { smooth: false })
    // 首屏显式一次：filters 恰好同值时 watch 不触发；与 watch 的防抖调用同参 → 去重合并为一次请求
    await search()
  }
})
</script>

<style scoped>
.records-page {
  padding-bottom: 20px;
}

/* 需求三：月份条横滚容器（收敛原 flex/间距/横滚/底部留白工具类与内联 scrollbar-width）。
   需求十一：追加横向 overscroll 隔离——横滑到左右边缘不再把滚动链交给文档，
   阻断 Chromium 历史滑动导航（竖屏误切底部标签页）；只断链，月份条自身横滑与居中不受影响。 */
.month-scroller {
  display: flex;
  flex-grow: 1;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  gap: 8px;
  padding-bottom: 8px;
  scrollbar-width: none;
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
