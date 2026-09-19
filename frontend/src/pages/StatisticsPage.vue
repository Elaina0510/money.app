<template>
  <div class="statistics-page">
    <!-- Page Info -->
    <div class="page-info mb-3">
      <p class="text-caption text-grey">收支数据一目了然</p>
    </div>

    <!-- Period Selector -->
    <v-card class="pa-3 mb-3 period-selector" rounded="xl">
      <div class="d-flex align-center ga-2">
        <v-btn variant="text" icon size="small" @click="prevPeriod">
          <v-icon>mdi-chevron-left</v-icon>
        </v-btn>
        <div class="flex-grow-1 text-center font-weight-bold text-body-1">
          {{ periodLabel }}
        </div>
        <v-btn variant="text" icon size="small" @click="nextPeriod">
          <v-icon>mdi-chevron-right</v-icon>
        </v-btn>
        <v-divider vertical class="mx-1" />
        <v-btn
          :color="periodType === 'monthly' ? 'primary' : ''"
          size="small"
          variant="tonal"
          class="period-tab"
          rounded="xl"
          @click="switchPeriod('monthly')"
        >
          月
        </v-btn>
        <v-btn
          :color="periodType === 'yearly' ? 'primary' : ''"
          size="small"
          variant="tonal"
          class="period-tab"
          rounded="xl"
          @click="switchPeriod('yearly')"
        >
          年
        </v-btn>
      </div>
    </v-card>

    <!-- Summary Cards -->
    <v-row class="mb-3" dense>
      <v-col cols="4">
        <v-card class="pa-3 text-center summary-card" rounded="xl">
          <v-icon color="#FF6B6B" size="24" class="mb-1">mdi-trending-down</v-icon>
          <div class="text-caption text-grey">支出</div>
          <div class="text-body-1 font-weight-bold" style="color: #FF6B6B">
            {{ formatAmount(summary?.total_expense || 0) }}
          </div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card class="pa-3 text-center summary-card" rounded="xl">
          <v-icon color="#20C997" size="24" class="mb-1">mdi-trending-up</v-icon>
          <div class="text-caption text-grey">收入</div>
          <div class="text-body-1 font-weight-bold" style="color: #20C997">
            {{ formatAmount(summary?.total_income || 0) }}
          </div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card class="pa-3 text-center summary-card" rounded="xl">
          <v-icon :color="balanceColor" size="24" class="mb-1">mdi-wallet</v-icon>
          <div class="text-caption text-grey">结余</div>
          <div class="text-body-1 font-weight-bold" :style="{ color: balanceColor }">
            {{ formatAmount(balance) }}
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Category Bar Chart -->
    <v-card class="pa-4 mb-3 chart-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <span class="text-subtitle-2 font-weight-bold">分类统计</span>
        <v-chip size="x-small" variant="tonal" color="grey">支出</v-chip>
      </div>
      <!-- v1.4.2 M7：Bar 常驻（外层无 v-if），空态改覆盖层，消除 canvas 重建闪白 -->
      <div class="chart-holder">
        <Bar :data="categoryBarData" :options="barChartOptions" />
        <div v-if="categoryStats.length === 0" class="chart-empty-overlay">
          <span class="text-caption text-grey">暂无数据</span>
        </div>
      </div>
      <div v-if="categoryStats.length" class="category-list">
        <div
          v-for="(item, index) in categoryStats"
          :key="item.category_name"
          class="d-flex align-center pa-2 category-list-item"
        >
          <div
            class="color-dot mr-2"
            :style="{ backgroundColor: chartColors[index % chartColors.length] }"
          />
          <div class="flex-grow-1 text-body-2">{{ item.category_name }}</div>
          <div class="text-body-2 font-weight-medium mr-2">{{ formatAmount(item.total) }}</div>
          <div class="text-caption text-grey" style="width: 40px; text-align: right;">
            {{ ((item.total / categoryTotal) * 100).toFixed(1) }}%
          </div>
        </div>
      </div>
    </v-card>

    <!-- Trend Chart -->
    <v-card class="pa-4 mb-3 chart-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <span class="text-subtitle-2 font-weight-bold">收支趋势</span>
        <v-chip size="x-small" variant="tonal" color="grey">
          {{ periodType === 'monthly' ? '每日' : '每月' }}
        </v-chip>
      </div>
      <div v-if="trendData.length === 0" class="text-center pa-6 text-grey text-caption">
        暂无数据
      </div>
      <div v-else style="height: 240px;">
        <Line :data="trendChartData" :options="trendChartOptions" />
      </div>
    </v-card>

    <!-- Budget Management（v1.4.1 M6：由设置页迁入，跟随周期选择器） -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <div class="d-flex align-center">
          <v-avatar size="36" color="rgba(156, 39, 176, 0.1)" class="mr-2">
            <v-icon color="purple" size="20">mdi-piggy-bank-outline</v-icon>
          </v-avatar>
          <span class="text-subtitle-2 font-weight-bold">预算管理</span>
        </div>
        <v-btn
          v-if="periodType === 'monthly'"
          size="small"
          color="primary"
          variant="tonal"
          :disabled="budgetLoading"
          @click="openBudgetAddDialog"
        >
          <v-icon start size="small">mdi-plus</v-icon>
          设置
        </v-btn>
      </div>

      <!-- ─── 月视图：管理所选月（等价迁移自设置页）─── -->
      <template v-if="periodType === 'monthly'">
        <!-- 月度预算概览 -->
        <v-card variant="tonal" class="pa-4 mb-3" rounded="lg">
          <div class="text-caption text-grey mb-1">{{ budgetMonthLabel }} 预算</div>
          <div class="text-h5 font-weight-bold mb-2">¥{{ formatAmount(totalBudget) }}</div>
          <v-progress-linear
            :model-value="budgetUsagePercent"
            :color="
              budgetUsagePercent > 80 ? 'error' : budgetUsagePercent > 50 ? 'warning' : 'success'
            "
            height="8"
            rounded
            class="mb-2"
          />
          <div class="d-flex justify-space-between text-caption">
            <span>已用 ¥{{ formatAmount(totalSpent) }}</span>
            <span>{{ budgetUsagePercent.toFixed(0) }}%</span>
          </div>
        </v-card>

        <!-- 分类预算列表 -->
        <div v-if="budgets.length === 0" class="text-center pa-4 text-grey text-caption">
          暂无预算设置，点击上方按钮添加分类预算
        </div>

        <div
          v-for="(item, index) in enrichedBudgets"
          :key="item.category_id"
          class="budget-item mb-3"
        >
          <div class="d-flex justify-space-between align-center mb-1">
            <div class="d-flex align-center">
              <v-avatar size="32" :color="getBudgetColor(index) + '20'" class="mr-2">
                <v-icon size="small" :color="getBudgetColor(index)">{{ item.icon }}</v-icon>
              </v-avatar>
              <span class="text-body-2 font-weight-medium">{{ item.category_name }}</span>
            </div>
            <div class="d-flex align-center">
              <template v-if="editingBudget === item.category_id">
                <v-text-field
                  v-model.number="editBudgetAmount"
                  type="number"
                  density="compact"
                  hide-details
                  variant="outlined"
                  prefix="¥"
                  style="width: 120px"
                  class="mr-1"
                  autofocus
                  @keyup.enter="saveBudgetEdit(item)"
                  @keyup.escape="cancelBudgetEdit"
                />
                <v-btn
                  icon
                  size="x-small"
                  variant="text"
                  color="primary"
                  @click="saveBudgetEdit(item)"
                  :loading="savingBudget"
                >
                  <v-icon size="small">mdi-check</v-icon>
                </v-btn>
                <v-btn icon size="x-small" variant="text" @click="cancelBudgetEdit">
                  <v-icon size="small">mdi-close</v-icon>
                </v-btn>
              </template>
              <template v-else>
                <span class="text-body-2 font-weight-bold">{{ formatAmount(item.spent) }}</span>
                <span class="text-grey"> / {{ formatAmount(item.amount) }}</span>
                <v-btn
                  icon
                  size="x-small"
                  variant="text"
                  class="ml-1"
                  @click="startBudgetEdit(item)"
                >
                  <v-icon size="small" color="grey">mdi-pencil</v-icon>
                </v-btn>
                <v-btn
                  icon
                  size="x-small"
                  variant="text"
                  class="ml-1"
                  title="删除预算"
                  @click="confirmDeleteBudget(item)"
                >
                  <v-icon size="small" color="grey">mdi-delete-outline</v-icon>
                </v-btn>
              </template>
            </div>
          </div>
          <v-progress-linear
            :model-value="item.amount > 0 ? (item.spent / item.amount) * 100 : 0"
            :color="
              item.amount > 0 && item.spent / item.amount > 0.8
                ? 'error'
                : item.amount > 0 && item.spent / item.amount > 0.5
                  ? 'warning'
                  : 'primary'
            "
            height="6"
            rounded
          />
        </div>
      </template>

      <!-- ─── 年视图：逐月概览 + 点击下钻（决策 D2）─── -->
      <template v-else>
        <div class="text-caption text-grey mb-2">
          {{ budgetYear }}年 · 预算 {{ formatAmount(yearTotalBudget) }} · 已用
          {{ formatAmount(yearTotalSpent) }}
        </div>

        <div v-if="!yearHasBudget" class="text-center pa-4 text-grey text-caption">
          该年暂无预算设置
        </div>

        <template v-else>
          <div
            v-for="entry in yearMonths"
            :key="entry.month"
            class="budget-month-row d-flex align-center py-2"
            :class="{ 'budget-month-row--link': entry.total_amount > 0 }"
            @click="drillDownToMonth(entry.month)"
          >
            <span class="text-body-2 font-weight-medium budget-month-label">
              {{ getBudgetMonthLabel(entry.month) }}
            </span>
            <template v-if="entry.total_amount > 0">
              <v-progress-linear
                :model-value="(entry.total_spent / entry.total_amount) * 100"
                :color="
                  entry.total_spent / entry.total_amount > 0.8
                    ? 'error'
                    : entry.total_spent / entry.total_amount > 0.5
                      ? 'warning'
                      : 'primary'
                "
                height="6"
                rounded
                class="flex-grow-1 mx-2"
              />
              <span class="text-body-2 text-no-wrap">
                <span class="font-weight-bold">{{ formatAmount(entry.total_spent) }}</span>
                <span class="text-grey"> / {{ formatAmount(entry.total_amount) }}</span>
              </span>
              <v-icon size="x-small" color="grey" class="ml-1">mdi-chevron-right</v-icon>
            </template>
            <span v-else class="text-caption text-grey">暂无预算</span>
          </div>
        </template>
      </template>
    </v-card>

    <!-- Budget Add Dialog -->
    <v-dialog v-model="showBudgetAddDialog" max-width="400">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-3">设置分类预算</v-card-title>
        <div class="text-caption text-grey mb-2">{{ budgetMonthLabel }}</div>
        <v-select
          v-model="budgetForm.category_id"
          :items="availableBudgetCategories"
          item-title="name"
          item-value="id"
          label="选择分类"
          hide-details
          class="mb-3"
          variant="outlined"
        />
        <v-text-field
          v-model.number="budgetForm.amount"
          label="预算金额"
          type="number"
          prefix="¥"
          hide-details
          class="mb-3"
          variant="outlined"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showBudgetAddDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingBudget" @click="saveBudget">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Delete Budget Confirm -->
    <ConfirmDialog
      v-model="showDeleteBudgetDialog"
      title="删除预算"
      :message="`确定要删除「${deletingBudget?.category_name}」的预算吗？`"
      confirm-text="删除"
      @confirm="handleDeleteBudget"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSummary, getByCategory, getTrend } from '@/api/statistics'
import {
  getBudgets,
  getBudgetYearSummary,
  batchSetBudgets,
  deleteBudget,
} from '@/api/budgets'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { formatAmount } from '@/utils/format'
import dayjs from 'dayjs'
import { Bar, Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Filler,
  BarElement,
  BarController,
} from 'chart.js'

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Title, Filler,
  BarElement, BarController
)

const chartColors = ['#FF6B6B', '#FFA94D', '#FFD43B', '#69DB7C', '#38D9A9', '#4DABF7', '#748FFC', '#9775FA', '#F783AC']

const periodType = ref('monthly')
const periodOffset = ref(0)
const summary = ref(null)
const categoryStats = ref([])
const trendData = ref([])

const periodLabel = computed(() => {
  if (periodType.value === 'monthly') {
    return dayjs().add(periodOffset.value, 'month').format('YYYY年MM月')
  }
  return dayjs().add(periodOffset.value, 'year').format('YYYY年')
})

const balance = computed(() => {
  const inc = summary.value?.total_income || 0
  const exp = summary.value?.total_expense || 0
  return inc - exp
})

const balanceColor = computed(() => {
  const b = balance.value
  if (b > 0) return '#20C997'
  if (b < 0) return '#FF6B6B'
  return '#9E9E9E'
})

const categoryTotal = computed(() => {
  return categoryStats.value.reduce((sum, c) => sum + c.total, 0)
})

const categoryBarData = computed(() => ({
  labels: categoryStats.value.map((c) => c.category_name),
  datasets: [{
    label: '金额',
    data: categoryStats.value.map((c) => c.total),
    backgroundColor: chartColors.slice(0, categoryStats.value.length),
    borderRadius: 6,
    borderSkipped: false,
  }],
}))

// v1.4.2 M7：柱状图过渡动画配置（仅作用于 barChartOptions，不外溢全局 defaults）
const CHART_ANIMATION = {
  duration: 750,
  easing: 'easeOutQuart',
}

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: CHART_ANIMATION,
  transitions: { active: CHART_ANIMATION },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: { label: (ctx) => `¥${Number(ctx.raw).toLocaleString()}` },
    },
  },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 10 } } },
    y: {
      grid: { color: 'rgba(0,0,0,0.04)' },
      beginAtZero: true,
      ticks: {
        font: { size: 10 },
        callback: (val) => `¥${val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val}`,
      },
    },
  },
}

const trendChartData = computed(() => {
  const labels = trendData.value.map((t) => t.period)
  return {
    labels,
    datasets: [
      {
        label: '支出',
        data: trendData.value.map((t) => t.expense || 0),
        borderColor: '#FF6B6B',
        backgroundColor: 'rgba(255, 107, 107, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
        pointBackgroundColor: '#FF6B6B',
      },
      {
        label: '收入',
        data: trendData.value.map((t) => t.income || 0),
        borderColor: '#20C997',
        backgroundColor: 'rgba(32, 201, 151, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
        pointBackgroundColor: '#20C997',
      },
    ],
  }
})

const trendChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: { boxWidth: 12, padding: 10, font: { size: 11 } },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ¥${Number(ctx.raw).toLocaleString()}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 10 } },
    },
    y: {
      grid: { color: 'rgba(0,0,0,0.04)' },
      beginAtZero: true,
      ticks: {
        font: { size: 10 },
        callback: (val) => `¥${val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val}`,
      },
    },
  },
}

function getDateRange() {
  if (periodType.value === 'monthly') {
    const d = dayjs().add(periodOffset.value, 'month')
    return {
      start_date: d.startOf('month').format('YYYY-MM-DD'),
      end_date: d.endOf('month').format('YYYY-MM-DD'),
    }
  }
  const d = dayjs().add(periodOffset.value, 'year')
  return {
    start_date: d.startOf('year').format('YYYY-MM-DD'),
    end_date: d.endOf('year').format('YYYY-MM-DD'),
  }
}

// ── 预算管理（v1.4.1 M6：由设置页迁移，跟随周期选择器）────────────────
// 易错点：新增/编辑写入的月份 = 当前所选月 budgetMonth，而非系统当前月
const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

const budgets = ref([])
const yearMonths = ref([])
const budgetLoading = ref(false)
const showBudgetAddDialog = ref(false)
const savingBudget = ref(false)
const editingBudget = ref(null)
const editBudgetAmount = ref(0)
const budgetForm = ref({ category_id: null, amount: 0 })
const showDeleteBudgetDialog = ref(false)
const deletingBudget = ref(null)

const BUDGET_COLORS = [
  '#FF6B6B',
  '#4DABF7',
  '#9775FA',
  '#51CF66',
  '#FF922B',
  '#22B8CF',
  '#F06595',
  '#845EF7',
  '#20C997',
  '#FD7E14',
]

const budgetMonth = computed(() => dayjs().add(periodOffset.value, 'month').format('YYYY-MM'))
const budgetYear = computed(() => dayjs().add(periodOffset.value, 'year').format('YYYY'))
const budgetMonthLabel = computed(() => dayjs(`${budgetMonth.value}-01`).format('YYYY年M月'))

const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
const budgetUsagePercent = computed(() => {
  if (totalBudget.value === 0) return 0
  return (totalSpent.value / totalBudget.value) * 100
})

const enrichedBudgets = computed(() => {
  return budgets.value.map((b) => {
    const cat = categoriesStore.categories.find((c) => c.id === b.category_id)
    return { ...b, icon: cat?.icon || 'mdi-cash' }
  })
})

const availableBudgetCategories = computed(() => {
  const budgetCategoryIds = budgets.value.map((b) => b.category_id)
  return categoriesStore.categories.filter(
    (c) => c.type === 'expense' && !budgetCategoryIds.includes(c.id)
  )
})

// 年视图摘要（Σ yearMonths totals）
const yearTotalBudget = computed(() =>
  yearMonths.value.reduce((sum, m) => sum + (m.total_amount || 0), 0)
)
const yearTotalSpent = computed(() =>
  yearMonths.value.reduce((sum, m) => sum + (m.total_spent || 0), 0)
)
const yearHasBudget = computed(() => yearMonths.value.some((m) => (m.budgets || []).length > 0))

function getBudgetColor(index) {
  return BUDGET_COLORS[index % BUDGET_COLORS.length]
}

function getBudgetMonthLabel(month) {
  return dayjs(`${month}-01`).format('M月')
}

async function loadCategories() {
  if (categoriesStore.loaded) return
  try {
    await categoriesStore.fetchCategories()
  } catch (e) {
    console.error('Load categories error:', e)
  }
}

async function loadBudgets() {
  budgetLoading.value = true
  try {
    if (periodType.value === 'monthly') {
      budgets.value = (await getBudgets({ month: budgetMonth.value })) || []
    } else {
      const data = await getBudgetYearSummary({ year: budgetYear.value })
      yearMonths.value = data?.months || []
    }
  } catch (e) {
    console.error('Budget load error:', e)
  } finally {
    budgetLoading.value = false
  }
}

function startBudgetEdit(item) {
  editingBudget.value = item.category_id
  editBudgetAmount.value = item.amount
}

function cancelBudgetEdit() {
  editingBudget.value = null
  editBudgetAmount.value = 0
}

async function saveBudgetEdit(item) {
  if (editBudgetAmount.value <= 0) return
  savingBudget.value = true
  try {
    await batchSetBudgets({
      month: budgetMonth.value,
      budgets: [{ category_id: item.category_id, amount: editBudgetAmount.value }],
    })
    editingBudget.value = null
    await loadBudgets()
  } catch (e) {
    console.error('Save budget error:', e)
  } finally {
    savingBudget.value = false
  }
}

function openBudgetAddDialog() {
  budgetForm.value = { category_id: null, amount: 0 }
  showBudgetAddDialog.value = true
}

async function saveBudget() {
  if (!budgetForm.value.category_id || budgetForm.value.amount <= 0) return
  savingBudget.value = true
  try {
    await batchSetBudgets({
      month: budgetMonth.value,
      budgets: [{ category_id: budgetForm.value.category_id, amount: budgetForm.value.amount }],
    })
    showBudgetAddDialog.value = false
    budgetForm.value = { category_id: null, amount: 0 }
    await loadBudgets()
  } catch (e) {
    console.error('Save budget error:', e)
  } finally {
    savingBudget.value = false
  }
}

function confirmDeleteBudget(item) {
  deletingBudget.value = item
  showDeleteBudgetDialog.value = true
}

async function handleDeleteBudget() {
  const item = deletingBudget.value
  if (!item) {
    showDeleteBudgetDialog.value = false
    return
  }
  savingBudget.value = true
  try {
    await deleteBudget(item.id)
    await loadBudgets()
    appStore.showToast('预算已删除')
  } catch (e) {
    console.error('Delete budget error:', e)
    appStore.showToast(e.message || '删除失败', 'error')
  } finally {
    savingBudget.value = false
    showDeleteBudgetDialog.value = false
    deletingBudget.value = null
  }
}

// 年视图行点击下钻：切回月视图并把偏移指向该月（budgetMonth 的逆运算）
function drillDownToMonth(month) {
  periodType.value = 'monthly'
  periodOffset.value = dayjs(`${month}-01`).diff(dayjs().startOf('month'), 'month')
  loadData()
}

async function loadData() {
  const range = getDateRange()
  try {
    const groupBy = periodType.value === 'monthly' ? 'day' : 'month'
    const [s, c, t] = await Promise.all([
      getSummary({ ...range, period: periodType.value === 'monthly' ? 'month' : 'year' }),
      getByCategory({ ...range, type: 'expense' }),
      getTrend({ ...range, group_by: groupBy }),
      loadBudgets(),
    ])
    summary.value = s
    categoryStats.value = c?.items || []
    trendData.value = t?.items || []
  } catch (e) {
    console.error('Statistics load error:', e)
  }
}

function prevPeriod() {
  periodOffset.value--
  loadData()
}

function nextPeriod() {
  periodOffset.value++
  loadData()
}

function switchPeriod(type) {
  periodType.value = type
  periodOffset.value = 0
  loadData()
}

onMounted(async () => {
  await Promise.all([loadData(), loadCategories()])
})
</script>

<style scoped>
.statistics-page {
  padding-bottom: 20px;
}

.period-selector {
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.period-tab {
  min-width: 36px !important;
}

.summary-card {
  transition: all 0.15s ease;
}

.summary-card:hover {
  transform: translateY(-1px);
}

.chart-card {
  border: 1px solid rgba(0, 0, 0, 0.04);
}

/* v1.4.2 M7：canvas 常驻容器 + 空态覆盖层（明/暗均以 surface 底遮盖） */
.chart-holder {
  position: relative;
  height: 200px;
  margin-bottom: 12px;
}

.chart-empty-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(var(--v-theme-surface));
}

.category-list-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.category-list-item:last-child {
  border-bottom: none;
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.budget-month-label {
  width: 48px;
  flex-shrink: 0;
}

.budget-month-row {
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.budget-month-row:last-child {
  border-bottom: none;
}

.budget-month-row--link {
  cursor: pointer;
}

.budget-month-row--link:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}
</style>
