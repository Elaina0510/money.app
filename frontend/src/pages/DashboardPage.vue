<template>
  <div class="dashboard-page">
    <!-- Page Header -->
    <div class="page-header mb-4">
      <div class="d-flex align-center justify-space-between">
        <div class="d-none d-md-block">
          <h1 class="page-title">首页</h1>
          <p class="page-subtitle">{{ currentDateStr }}</p>
        </div>
      </div>
    </div>

    <!-- Monthly Hero Card - 本月总消费 -->
    <v-card class="monthly-overview-card mb-4" color="primary" rounded="xl">
      <div class="overview-content pa-5">
        <div class="d-flex justify-space-between align-start mb-1">
          <div class="text-subtitle-1 font-weight-medium" style="opacity: 0.9">
            {{ currentMonthLabel }} 总支出
          </div>
          <v-btn
            icon
            variant="text"
            size="small"
            color="white"
            style="opacity: 0.7"
            @click="router.push('/statistics')"
          >
            <v-icon>mdi-chevron-right</v-icon>
          </v-btn>
        </div>
        <div class="monthly-amount mb-3">
          <span class="amount-symbol">¥</span>
          <span class="amount-number">{{ totalMonthExpense }}</span>
        </div>

        <div class="d-flex ga-4">
          <div class="stat-item">
            <div class="stat-label">收入</div>
            <div class="stat-value income">+¥{{ formatIncome }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">笔数</div>

            <div class="stat-value">{{ summary?.transaction_count || 0 }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">日均</div>
            <div class="stat-value">¥{{ dailyAverage }}</div>
          </div>
        </div>
      </div>
    </v-card>

    <!-- Period Summary Cards Row -->
    <v-row class="mb-4" dense>
      <v-col cols="6">
        <v-card class="pa-4 text-center today-card" rounded="xl">
          <v-icon color="#FF6B6B" size="28" class="mb-1">mdi-trending-down</v-icon>
          <div class="text-caption text-grey">期间支出</div>
          <div class="text-h6 font-weight-bold" style="color: #FF6B6B">
            {{ formatAmount(summary?.total_expense || 0) }}
          </div>
        </v-card>
      </v-col>
      <v-col cols="6">
        <v-card class="pa-4 text-center today-card" rounded="xl">
          <v-icon color="#20C997" size="28" class="mb-1">mdi-trending-up</v-icon>
          <div class="text-caption text-grey">期间收入</div>
          <div class="text-h6 font-weight-bold" style="color: #20C997">
            {{ formatAmount(summary?.total_income || 0) }}
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Category Stats (mini preview) -->
    <v-card class="pa-4 mb-4" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <span class="text-subtitle-2 font-weight-bold">分类支出排行</span>
        <v-btn variant="text" size="small" color="primary" @click="router.push('/statistics')">
          详情
          <v-icon end size="small">mdi-chevron-right</v-icon>
        </v-btn>
      </div>
      <div v-if="categoryStats.length === 0" class="text-center pa-3 text-grey text-caption">
        暂无数据
      </div>
      <div v-else>
        <div
          v-for="(item, index) in categoryStats.slice(0, 4)"
          :key="item.category_name"
          class="category-stat-item d-flex align-center mb-2"
        >
          <div class="rank-badge mr-2" :class="'rank-' + (index + 1)">
            {{ index + 1 }}
          </div>
          <v-avatar size="32" :color="item.color + '20'" class="mr-2">
            <v-icon size="small" :color="item.color">{{ item.icon || 'mdi-circle' }}</v-icon>
          </v-avatar>
          <div class="flex-grow-1 text-body-2">{{ item.category_name }}</div>
          <div class="text-body-2 font-weight-bold" style="color: #FF6B6B">
            {{ formatAmount(item.total) }}
          </div>
        </div>
      </div>
    </v-card>

    <!-- Recent Records Section -->
    <div class="section-header d-flex justify-space-between align-center mb-2">
      <span class="text-subtitle-2 font-weight-bold">最近账单</span>
      <v-btn variant="text" size="small" color="primary" @click="router.push('/records')">
        查看全部
        <v-icon end size="small">mdi-chevron-right</v-icon>
      </v-btn>
    </div>

    <div v-if="records.length === 0" class="empty-records-card">
      <v-card class="pa-6 text-center" rounded="xl" variant="outlined">
        <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-book-open-blank-variant</v-icon>
        <p class="text-grey text-body-2 mb-1">还没有记账记录</p>
        <p class="text-grey-lighten-1 text-caption mb-3">点击右下角 + 号开始记账</p>
      </v-card>
    </div>

    <div v-else class="records-list">
      <v-card
        v-for="record in records"
        :key="record.id"
        class="mb-2 record-card"
        rounded="xl"
        @click="router.push(`/edit/${record.id}`)"
      >
        <v-list-item>
          <template v-slot:prepend>
            <v-avatar :color="record.type === 'expense' ? '#FFE8E8' : '#E8FFF3'" size="42" class="mr-2">
              <v-icon :color="record.type === 'expense' ? '#FF6B6B' : '#20C997'" size="20">
                {{ record.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
              </v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ record.category_name || '未分类' }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ formatDate(record.date) }}
            <template v-if="record.tags?.length">
              <v-icon size="x-small" class="mx-1" style="opacity: 0.4">mdi-circle-small</v-icon>
              {{ record.tags.slice(0, 2).join(', ') }}
              <span v-if="record.tags.length > 2" class="text-grey">+{{ record.tags.length - 2 }}</span>
            </template>
          </v-list-item-subtitle>
          <template v-slot:append>
            <div
              class="font-weight-bold text-body-1"
              :style="{ color: record.type === 'expense' ? '#FF6B6B' : '#20C997' }"
            >
              {{ record.type === 'expense' ? '-' : '+' }}{{ formatAmount(record.amount) }}
            </div>
          </template>
        </v-list-item>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getRecords } from '@/api/records'
import { getSummary, getByCategory } from '@/api/statistics'
import { formatAmount, formatDate, getCurrentMonthRange } from '@/utils/format'
import dayjs from 'dayjs'
function recordTypeColor(name) {
  const colors = ['#FFE8E8', '#FFF3E0', '#FFF8E1', '#E8F5E9', '#E0F7FA', '#E3F2FD', '#EDE7F6', '#FCE4EC']
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

const router = useRouter()
const records = ref([])
const summary = ref(null)
const categoryStats = ref([])

const currentMonthLabel = computed(() => dayjs().format('YYYY年MM月'))

const currentDateStr = computed(() => {
  const now = new Date()
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${weekdays[now.getDay()]}`
})

const totalMonthExpense = computed(() => {
  const val = summary.value?.total_expense || 0
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const formatIncomeStr = computed(() => {
  const val = summary.value?.total_income || 0
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const dailyAverage = computed(() => {
  const exp = summary.value?.total_expense || 0
  const day = dayjs().date()
  if (day === 0) return '0.00'
  return (exp / day).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

onMounted(async () => {
  const monthRange = getCurrentMonthRange()
  try {
    const [recordsData, summaryData, catStats] = await Promise.all([
      getRecords({ page: 1, page_size: 10, sort_order: 'desc', sort_by: 'date' }),
      getSummary({ start_date: monthRange.startDate, end_date: monthRange.endDate, period: 'monthly' }),
      getByCategory({ start_date: monthRange.startDate, end_date: monthRange.endDate }),
    ])
    records.value = recordsData.items || recordsData
    summary.value = summaryData
    categoryStats.value = (catStats || []).filter(c => c.type === 'expense').sort((a, b) => b.total - a.total)
  } catch (e) {
    console.error('Dashboard load error:', e)
  }
})
</script>

<style scoped>
.dashboard-page {
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

.monthly-overview-card {
  overflow: hidden;
}

.overview-content {
  position: relative;
}

.monthly-amount {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.amount-symbol {
  font-size: 20px;
  font-weight: 600;
  opacity: 0.8;
}

.amount-number {
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
}

.stat-item {
  flex: 1;
}

.stat-label {
  font-size: 11px;
  opacity: 0.7;
  margin-bottom: 2px;
}

.stat-value {
  font-size: 15px;
  font-weight: 600;
}

.stat-value.income {
  color: #69DB7C;
}

.today-card {
  transition: all 0.2s ease;
}

.today-card:hover {
  transform: translateY(-1px);
}

.rank-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: white;
}

.rank-1 { background: linear-gradient(135deg, #FF6B6B, #EE5A24); }
.rank-2 { background: linear-gradient(135deg, #FFA94D, #FD9644); }
.rank-3 { background: linear-gradient(135deg, #FFD43B, #F0A500); }
.rank-4 { background: rgba(0,0,0,0.1); color: rgba(0,0,0,0.4); }

.category-stat-item:last-child {
  margin-bottom: 0 !important;
}

.record-card {
  transition: all 0.15s ease;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.record-card:hover {
  border-color: rgba(var(--v-theme-primary), 0.2);
  transform: translateX(2px);
}

.section-header {
  padding-top: 4px;
}

@media (max-width: 959px) {
  .amount-number {
    font-size: 32px;
  }
}
</style>
