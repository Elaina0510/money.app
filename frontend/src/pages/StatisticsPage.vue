<template>
  <div class="statistics-page">
    <!-- Page Header -->
    <div class="page-header mb-3">
      <h1 class="page-title">统计</h1>
      <p class="page-subtitle">收支数据一目了然</p>
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

    <!-- Category Pie Chart -->
    <v-card class="pa-4 mb-3 chart-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <span class="text-subtitle-2 font-weight-bold">分类统计</span>
        <v-chip size="x-small" variant="tonal" color="grey">支出</v-chip>
      </div>
      <div v-if="categoryStats.length === 0" class="text-center pa-6 text-grey text-caption">
        暂无数据
      </div>
      <div v-else>
        <div style="height: 200px;" class="mb-3">
          <Pie :data="categoryChartData" :options="chartOptions" />
        </div>
        <div class="category-list">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSummary, getByCategory, getTrend } from '@/api/statistics'
import { formatAmount } from '@/utils/format'
import dayjs from 'dayjs'
import { Pie, Line } from 'vue-chartjs'
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
} from 'chart.js'

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Title, Filler
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

const categoryChartData = computed(() => ({
  labels: categoryStats.value.map((c) => c.category_name),
  datasets: [{
    data: categoryStats.value.map((c) => c.total),
    backgroundColor: chartColors.slice(0, categoryStats.value.length),
    borderWidth: 0,
  }],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '55%',
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `¥${Number(ctx.raw).toLocaleString()}`,
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

async function loadData() {
  const range = getDateRange()
  try {
    const [s, c, t] = await Promise.all([
      getSummary({ ...range, period: periodType.value }),
      getByCategory(range),
      getTrend({ ...range, period: periodType.value }),
    ])
    summary.value = s
    categoryStats.value = (c || []).filter(item => item.type === 'expense')
    trendData.value = t || []
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

onMounted(loadData)
</script>

<style scoped>
.statistics-page {
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
</style>
