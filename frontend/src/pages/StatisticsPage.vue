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
          <div class="text-body-1 font-weight-bold amount-node amount-expense">
            {{ formatAmount(summary?.total_expense || 0) }}
          </div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card class="pa-3 text-center summary-card" rounded="xl">
          <v-icon color="#20C997" size="24" class="mb-1">mdi-trending-up</v-icon>
          <div class="text-caption text-grey">收入</div>
          <div class="text-body-1 font-weight-bold amount-node amount-income">
            {{ formatAmount(summary?.total_income || 0) }}
          </div>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card class="pa-3 text-center summary-card" rounded="xl">
          <v-icon :color="balanceColor" size="24" class="mb-1">mdi-wallet</v-icon>
          <div class="text-caption text-grey">结余</div>
          <div
            class="text-body-1 font-weight-bold amount-node"
            :class="balance > 0 ? 'amount-income' : balance < 0 ? 'amount-expense' : 'amount-neutral'"
          >
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
          <v-avatar size="36" class="entry-avatar mr-2">
            <v-icon color="primary" size="20">mdi-piggy-bank-outline</v-icon>
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
          新增预算
        </v-btn>
      </div>

      <!-- ─── 月视图：管理所选月的多条命名预算（v1.4.3 M12）─── -->
      <template v-if="periodType === 'monthly'">
        <!-- 月度预算概览（total = Σ 各预算，口径 D4） -->
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

        <!-- 预算卡片列表：同月可多条，纵向堆叠，key=id（同月同名两条亦各自成卡） -->
        <div v-if="budgets.length === 0" class="text-center pa-4 text-grey text-caption">
          暂无预算，点击右上角「新增预算」为该月创建第一条命名预算
        </div>

        <v-card
          v-for="budget in budgets"
          :key="budget.id"
          variant="tonal"
          rounded="lg"
          class="pa-3 mb-3 budget-card"
        >
          <div class="d-flex justify-space-between align-center mb-1">
            <div class="d-flex align-center ga-2 budget-card-title">
              <span class="text-body-2 font-weight-medium budget-name">{{ budget.name }}</span>
              <v-chip
                size="x-small"
                variant="tonal"
                :color="budget.scope_mode === 'exclude' ? 'warning' : 'primary'"
                class="budget-scope-chip"
              >
                {{ budget.scope_mode === 'exclude' ? '排除' : '包含' }}
              </v-chip>
            </div>
            <div class="d-flex align-center">
              <span class="text-body-2 font-weight-bold budget-spent">
                {{ formatAmount(budget.spent) }}
              </span>
              <span class="text-grey budget-amount"> / {{ formatAmount(budget.amount) }}</span>
              <v-btn
                icon
                size="x-small"
                variant="text"
                class="ml-1 budget-edit-btn"
                title="编辑预算"
                @click="openBudgetEditDialog(budget)"
              >
                <v-icon size="small" color="grey">mdi-pencil</v-icon>
              </v-btn>
              <v-btn
                icon
                size="x-small"
                variant="text"
                class="ml-1 budget-delete-btn"
                title="删除预算"
                @click="confirmDeleteBudget(budget)"
              >
                <v-icon size="small" color="grey">mdi-delete-outline</v-icon>
              </v-btn>
            </div>
          </div>
          <v-progress-linear
            :model-value="budgetPercent(budget)"
            :color="budgetBarColor(budget)"
            height="6"
            rounded
          />
          <!-- 卡片副行：覆盖简述（纯函数 scopeSummary）+ 已用百分比 -->
          <div class="d-flex justify-space-between align-center mt-1">
            <span class="text-caption text-grey budget-scope">
              覆盖：{{ scopeSummary(budget, categories) }}
            </span>
            <span class="text-caption text-grey budget-percent">{{ budgetPercentText(budget) }}</span>
          </div>
          <!-- 语义提示恒呈现一次（需求 12.3） -->
          <div class="text-caption text-grey budget-scope-hint">{{ scopeHint(budget) }}</div>

          <!-- 展开明细：仅列计入分类（include 含 0 花费项 / exclude 仅有花费的未排除项） -->
          <div v-if="budget.details && budget.details.length" class="mt-1">
            <v-btn
              size="x-small"
              variant="text"
              class="budget-detail-toggle"
              @click="toggleBudgetDetails(budget.id)"
            >
              {{ isBudgetExpanded(budget.id) ? '收起明细' : '展开明细' }}
              <v-icon size="x-small" class="ml-1">
                {{ isBudgetExpanded(budget.id) ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
              </v-icon>
            </v-btn>
            <v-slide-y-transition>
              <div v-if="isBudgetExpanded(budget.id)" class="budget-detail-list">
                <div
                  v-for="row in budget.details"
                  :key="row.category_id"
                  class="d-flex align-center py-1 budget-detail-row"
                >
                  <v-icon size="x-small" color="grey" class="mr-2">{{ row.icon }}</v-icon>
                  <span class="text-body-2 flex-grow-1">{{ row.category_name }}</span>
                  <span class="text-body-2">{{ formatAmount(row.spent) }}</span>
                </div>
              </div>
            </v-slide-y-transition>
          </div>
        </v-card>
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

    <!-- 新增/编辑命名预算对话框（v1.4.3 M12：两态共用同对话框回填全部字段） -->
    <!-- M14（任务 6.6）：外壳收编为 AppDialog（原点展开），M12 的表单字段与保存链路零改动 -->
    <AppDialog v-model="showBudgetDialog" max-width="480">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-1">
          {{ budgetForm.id ? '编辑预算' : '新增预算' }}
        </v-card-title>
        <div class="text-caption text-grey mb-3 budget-dialog-month">
          {{ budgetFormMonthLabel }}{{ budgetForm.id ? '（编辑不改所属月份）' : '' }}
        </div>

        <v-text-field
          v-model="budgetForm.name"
          label="预算名称"
          maxlength="50"
          placeholder="如 日常开销"
          hide-details
          variant="outlined"
          class="mb-3 budget-name-field"
        />
        <v-text-field
          v-model.number="budgetForm.amount"
          label="预算金额"
          type="number"
          prefix="¥"
          hide-details
          variant="outlined"
          class="mb-3 budget-amount-field"
        />

        <div class="text-caption text-grey mb-1">统计范围</div>
        <v-btn-toggle
          v-model="budgetForm.scope_mode"
          mandatory
          density="compact"
          class="mb-2 budget-scope-toggle"
        >
          <v-btn value="include" size="small">包含</v-btn>
          <v-btn value="exclude" size="small">排除</v-btn>
        </v-btn-toggle>

        <v-select
          v-model="budgetForm.category_ids"
          transition="fab-transition"
          :items="budgetCategoryOptions"
          item-title="name"
          item-value="id"
          :label="budgetForm.scope_mode === 'exclude' ? '排除分类（可留空）' : '包含分类'"
          multiple
          chips
          closable-chips
          clearable
          density="compact"
          variant="outlined"
          hide-details
          class="mb-2 budget-category-select"
        />
        <div class="text-caption text-grey mb-2 budget-dialog-hint">{{ budgetScopeTip }}</div>
        <div v-if="budgetScopeError" class="text-caption text-error mb-2 budget-dialog-error">
          {{ budgetScopeError }}
        </div>

        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showBudgetDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :loading="savingBudget"
            :disabled="!budgetFormValid"
            class="budget-save-btn"
            @click="saveBudget"
          >
            保存
          </v-btn>
        </div>
      </v-card>
    </AppDialog>

    <!-- Delete Budget Confirm -->
    <ConfirmDialog
      v-model="showDeleteBudgetDialog"
      title="删除预算"
      :message="`确定要删除「${deletingBudget?.name}」预算吗？`"
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
  createBudget,
  updateBudget,
  deleteBudget,
} from '@/api/budgets'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import AppDialog from '@/components/common/AppDialog.vue'
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

// ── 预算管理（v1.4.1 M6 由设置页迁入；v1.4.3 M12 改「每月多条命名预算」）──────
// 易错点：新增写入的月份 = 当前所选月 budgetMonth，而非系统当前月；编辑不改月份（PUT 契约）
const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

const UNKNOWN_CATEGORY_NAME = '未知分类'

const budgets = ref([])
const yearMonths = ref([])
const budgetLoading = ref(false)
const showBudgetDialog = ref(false)
const savingBudget = ref(false)
const budgetForm = ref({ id: null, month: '', name: '', amount: 0, scope_mode: 'include', category_ids: [] })
const showDeleteBudgetDialog = ref(false)
const deletingBudget = ref(null)
const expandedBudgetIds = ref([])

const categories = computed(() => categoriesStore.categories || [])

const budgetMonth = computed(() => dayjs().add(periodOffset.value, 'month').format('YYYY-MM'))
const budgetYear = computed(() => dayjs().add(periodOffset.value, 'year').format('YYYY'))
const budgetMonthLabel = computed(() => dayjs(`${budgetMonth.value}-01`).format('YYYY年M月'))

// 月度总览 = Σ 各预算（决策 D4：范围重叠时逐预算直加，属预期口径）
const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
const budgetUsagePercent = computed(() => {
  if (totalBudget.value === 0) return 0
  return (totalSpent.value / totalBudget.value) * 100
})

// 对话框分类候选：M8 起分类收支共用单套全量列表——不按 type 过滤、不排除已设预算的分类
// （同月可多条预算，同一分类可被多条预算覆盖）
const budgetCategoryOptions = computed(() =>
  categories.value.map((c) => ({ id: c.id, name: c.name }))
)

const budgetFormMonthLabel = computed(() =>
  budgetForm.value.month ? dayjs(`${budgetForm.value.month}-01`).format('YYYY年M月') : ''
)
const budgetNameMissing = computed(() => !budgetForm.value.name || !budgetForm.value.name.trim())
const budgetAmountInvalid = computed(() => !(Number(budgetForm.value.amount) > 0))
// 1.3 / 6.2 校验联动：include → 至少 1 类；exclude 允许 0 选（= 全部分类）
const budgetIncludeEmpty = computed(
  () =>
    budgetForm.value.scope_mode === 'include' &&
    (budgetForm.value.category_ids || []).length === 0
)
const budgetFormValid = computed(
  () => !budgetNameMissing.value && !budgetAmountInvalid.value && !budgetIncludeEmpty.value
)
const budgetScopeTip = computed(() =>
  budgetForm.value.scope_mode === 'exclude'
    ? '选中分类不计入本预算；一个都不选即统计全部分类支出'
    : '仅计入所选分类的支出'
)
const budgetScopeError = computed(() =>
  budgetIncludeEmpty.value ? '包含模式至少需要选择 1 个分类' : ''
)

// 年视图摘要（Σ yearMonths totals）
const yearTotalBudget = computed(() =>
  yearMonths.value.reduce((sum, m) => sum + (m.total_amount || 0), 0)
)
const yearTotalSpent = computed(() =>
  yearMonths.value.reduce((sum, m) => sum + (m.total_spent || 0), 0)
)
const yearHasBudget = computed(() => yearMonths.value.some((m) => (m.budgets || []).length > 0))

function getBudgetMonthLabel(month) {
  return dayjs(`${month}-01`).format('M月')
}

// 进度色档沿用现口径（三处同型 >80% error / >50% warning / 其余 primary），无 100% 独立档
function budgetPercent(budget) {
  const amt = Number(budget?.amount) || 0
  if (amt <= 0) return 0
  return ((Number(budget?.spent) || 0) / amt) * 100
}

function budgetBarColor(budget) {
  const pct = budgetPercent(budget)
  if (pct > 80) return 'error'
  if (pct > 50) return 'warning'
  return 'primary'
}

function budgetPercentText(budget) {
  return `${budgetPercent(budget).toFixed(1)}%`
}

// 覆盖简述（需求 12.3 无歧义口径，纯函数）：
//   include ≤2 类全列；>2 类前 2 + 计数；exclude 空集 = 全部分类、非空 = 除 X 外全部支出
function resolveScopeNames(budget, categoryList) {
  const ids = Array.isArray(budget?.category_ids) ? budget.category_ids : []
  const fromApi = budget?.category_names
  if (Array.isArray(fromApi) && fromApi.length === ids.length) return [...fromApi]
  const list = Array.isArray(categoryList) ? categoryList : []
  return ids.map(
    (id) => list.find((c) => c.id === id)?.name || UNKNOWN_CATEGORY_NAME
  )
}

function scopeSummary(budget, categoryList) {
  const names = resolveScopeNames(budget, categoryList)
  if (budget?.scope_mode === 'exclude') {
    return names.length ? `除 ${names.join('、')} 外全部支出` : '全部分类'
  }
  if (!names.length) return UNKNOWN_CATEGORY_NAME
  if (names.length <= 2) return names.join('、')
  return `${names.slice(0, 2).join('、')}等 ${names.length} 类`
}

// 语义提示：恒在卡片副行呈现一次
function scopeHint(budget) {
  return budget?.scope_mode === 'exclude' ? '选中分类不计入本预算' : '仅计入所选分类'
}

function isBudgetExpanded(id) {
  return expandedBudgetIds.value.includes(id)
}

function toggleBudgetDetails(id) {
  const idx = expandedBudgetIds.value.indexOf(id)
  if (idx >= 0) {
    expandedBudgetIds.value.splice(idx, 1)
  } else {
    expandedBudgetIds.value.push(id)
  }
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

function resetBudgetForm() {
  budgetForm.value = {
    id: null,
    month: budgetMonth.value,
    name: '',
    amount: 0,
    scope_mode: 'include',
    category_ids: [],
  }
}

function openBudgetAddDialog() {
  resetBudgetForm()
  showBudgetDialog.value = true
}

// 编辑复用同对话框，回填全部字段（month 只读展示、不入 PUT 载荷）
function openBudgetEditDialog(budget) {
  budgetForm.value = {
    id: budget.id,
    month: budget.month,
    name: budget.name,
    amount: budget.amount,
    scope_mode: budget.scope_mode || 'include',
    category_ids: [...(budget.category_ids || [])],
  }
  showBudgetDialog.value = true
}

async function saveBudget() {
  if (!budgetFormValid.value) return
  const form = budgetForm.value
  const payload = {
    name: form.name.trim(),
    amount: Number(form.amount),
    scope_mode: form.scope_mode,
    category_ids: Array.from(new Set(form.category_ids || [])),
  }
  savingBudget.value = true
  try {
    if (form.id) {
      await updateBudget(form.id, payload)
    } else {
      await createBudget({ month: form.month, ...payload })
    }
    showBudgetDialog.value = false
    await loadBudgets()
    appStore.showToast('预算已保存')
  } catch (e) {
    console.error('Save budget error:', e)
    appStore.showToast(e.message || '保存失败', 'error')
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

/* v1.4.3 M12：预算卡片列表（每月多条命名预算，纵向堆叠） */
.budget-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.budget-card-title {
  min-width: 0;
}

.budget-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.budget-detail-row + .budget-detail-row {
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

/* 明细展开动画口径统一（M14 任务 7.3）：时长/缓动由 global.scss 一处 slide-y 覆写承载
   （`--expand-duration` / `--expand-easing`），本页不再逐组件配置——M12 时期的
   220ms 字面量双类 !important 覆写已上收全局。 */

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
