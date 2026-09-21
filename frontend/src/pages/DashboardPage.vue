<template>
  <div class="dashboard-page">
    <!-- Monthly Hero Card - 需求二：总收支三视图点按切换（初始视图=支出，D5） -->
    <v-card class="monthly-overview-card mb-4" color="primary" rounded="xl">
      <div class="overview-content pa-5">
        <div class="d-flex justify-space-between align-start mb-1">
          <div class="text-subtitle-1 font-weight-medium" style="opacity: 0.9">
            {{ currentMonthLabel }} 总收支
          </div>
          <div class="overview-jump" @click.stop>
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
        </div>

        <!-- 点按区：视图标签 + 大数字 + 三点指示；普通 div click，不参与滚动链。
             v1.4.3-boot M1（需求一）：同区域追加 pointerdown 支持左右横滑切换，点击循环保留 -->
        <div
          class="overview-cycle-area mb-3"
          role="button"
          aria-label="切换收支视图"
          @click="cycleView"
          @pointerdown="onPointerDown"
        >
          <Transition name="amount-switch" mode="out-in">
            <div :key="view">
              <div class="view-label text-caption">{{ currentViewLabel }}</div>
              <div class="monthly-amount">
                <span class="amount-symbol">¥</span>
                <span
                  class="amount-number"
                  :class="{ 'amount-number--negative': showNegativeColor }"
                  >{{ viewAmount }}</span
                >
              </div>
            </div>
          </Transition>
          <div class="view-dots" aria-hidden="true">
            <span
              v-for="v in views"
              :key="v"
              class="view-dot"
              :class="{ 'view-dot--active': v === view }"
            ></span>
          </div>
        </div>

        <div class="d-flex ga-4">
          <div class="stat-item">
            <div class="stat-label">收入</div>
            <div class="stat-value income">+¥{{ formatIncomeStr }}</div>
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
          <div class="text-h6 font-weight-bold amount-node amount-expense">
            {{ formatAmount(summary?.total_expense || 0) }}
          </div>
        </v-card>
      </v-col>
      <v-col cols="6">
        <v-card class="pa-4 text-center today-card" rounded="xl">
          <v-icon color="#20C997" size="28" class="mb-1">mdi-trending-up</v-icon>
          <div class="text-caption text-grey">期间收入</div>
          <div class="text-h6 font-weight-bold amount-node amount-income">
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
          <div class="text-body-2 font-weight-bold amount-node amount-expense">
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
            <v-avatar class="entry-avatar mr-2" size="42">
              <v-icon color="primary" size="20">{{ record.category_icon || 'mdi-circle' }}</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ record.tag?.name || record.category_name || '未分类' }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ record.consume_time?.substring(0, 16) || '' }}
          </v-list-item-subtitle>
          <template v-slot:append>
            <div
              class="font-weight-bold text-body-1 amount-node"
              :class="record.type === 'expense' ? 'amount-expense' : 'amount-income'"
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { getRecords } from '@/api/records'
import { getSummary, getByCategory } from '@/api/statistics'
import { formatAmount, getCurrentMonthRange } from '@/utils/format'
import dayjs from 'dayjs'

const router = useRouter()
const records = ref([])
const summary = ref(null)
const categoryStats = ref([])

const currentMonthLabel = computed(() => dayjs().format('YYYY年MM月'))

// 需求二（D5）：大卡三视图点按循环 expense→balance→income，初始视图=支出
// （与改造前「总支出」卡语义连续）；循环声明序为 收入→支出→结余
const views = ['income', 'expense', 'balance']
const view = ref('expense')
const nextView = { income: 'expense', expense: 'balance', balance: 'income' }
const viewLabel = { income: '收入', expense: '支出', balance: '结余' }

// v1.4.3-boot M1（需求一 · 设计 §1.2.1 / D2 方向映射）：滑动与点击共用 view 单一状态源。
// prevView 是 nextView 的反向映射，循环顺序维持 支出→结余→收入→支出；
// 指示点与 amount-switch 动画仍绑 view，滑动天然联动，零改动。
const prevView = { expense: 'income', balance: 'expense', income: 'balance' }

// dir>0 = 前进（左滑 dx<0 / 点击），dir<0 = 后退（右滑 dx>0）
function stepView(dir) {
  view.value = dir > 0 ? nextView[view.value] : prevView[view.value]
}

function cycleView() {
  // 滑动动作尾巴派发的 click 在窗口内吞掉（D2），不双跳
  if (Date.now() < suppressClickUntil.value) return
  stepView(1)
}

// v1.4.3-boot M1（需求一 · 设计 §1.2.2 / D1）：原生 Pointer Events 三点位手势
// （pointerdown / pointerup / pointercancel）——不监听 move 阶段（判定只在 pointerup
// 发生一次，拖动过程零采样零视觉反馈）、不阻止任何默认行为（不阻断 click 链与键盘
// Enter→cycleView 路径）；触摸 + 鼠标单套代码，零新增依赖。
const SWIPE_THRESHOLD = 48 // px，需求建议 40–50 区间取中（D2）
const drag = { active: false, x0: 0, y0: 0 }
const suppressClickUntil = ref(0)

function onPointerDown(e) {
  // 鼠标仅响应左键；触摸/笔无 button 语义差异
  if (e.pointerType === 'mouse' && e.button !== 0) return
  drag.active = true
  drag.x0 = e.clientX
  drag.y0 = e.clientY
  // up/cancel 挂 window：拖出区域外松手同样兜得住（测试合成事件须 bubbles: true）
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onDragAbort)
}

function onPointerUp(e) {
  // 终点坐标取 pointerup 自身（无需 move 阶段采样）
  const dx = e.clientX - drag.x0
  const dy = e.clientY - drag.y0
  if (Math.abs(dx) > SWIPE_THRESHOLD && Math.abs(dx) > Math.abs(dy)) {
    stepView(dx < 0 ? 1 : -1)
    suppressClickUntil.value = Date.now() + 350 // 吞掉滑动后的尾巴 click（D2）
  }
  onDragAbort()
}

// 幂等清理：复位 active + 摘掉两个 window 监听（正常松手 / pointercancel / 卸载共用）
function onDragAbort() {
  drag.active = false
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onDragAbort)
}

onBeforeUnmount(onDragAbort)

// 金额口径沿用现状：千分位 + 两位小数，负数渲染为 "-1,234.56"
function fmtMoney(val) {
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 结余为纯前端派生（零新增接口）：收入 − 支出
const balance = computed(() => (summary.value?.total_income || 0) - (summary.value?.total_expense || 0))

const currentViewLabel = computed(() => viewLabel[view.value])

const viewAmount = computed(() => {
  const inc = summary.value?.total_income || 0
  const exp = summary.value?.total_expense || 0
  const val = view.value === 'income' ? inc : view.value === 'expense' ? exp : inc - exp
  return fmtMoney(val)
})

// 结余负数色 #FFC7C7（D5）：仅结余视图且结余为负；结余=0 与非负沿用现白
const showNegativeColor = computed(() => view.value === 'balance' && balance.value < 0)

const formatIncomeStr = computed(() => fmtMoney(summary.value?.total_income || 0))

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
      getRecords({ page: 1, page_size: 10, sort_order: 'desc', sort_by: 'consume_time' }),
      getSummary({ start_date: monthRange.startDate, end_date: monthRange.endDate, period: 'month' }),
      getByCategory({ start_date: monthRange.startDate, end_date: monthRange.endDate, type: 'expense' }),
    ])
    records.value = recordsData.items || []
    summary.value = summaryData
    categoryStats.value = (catStats?.items || []).sort((a, b) => b.total - a.total)
  } catch (e) {
    console.error('Dashboard load error:', e)
  }
})
</script>

<style scoped>
.dashboard-page {
  padding-bottom: 20px;
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

/* 需求二：三视图点按区（普通 div click，不参与滚动链） */
.overview-cycle-area {
  position: relative;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  /* 需求一（M1）：纵向滚动交还原生浏览器（不劫持页面滚动，滚动接管致 pointercancel
     → 不误判为滑动）；横向手势归 JS 判定 */
  touch-action: pan-y;
}

.view-label {
  opacity: 0.85;
  margin-bottom: 2px;
}

/* 三点指示：纯装饰，无独立点击语义 */
.view-dots {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.view-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ffffff;
  opacity: 0.4;
}

.view-dot--active {
  opacity: 1;
}

/* 结余负数色（D5）：仅结余视图为负时生效 */
.amount-number--negative {
  color: #FFC7C7;
}

/* 需求二切换动画。M14（任务 7.4 / §2.2.3 预留动作）回填：
   时长/缓动引用全站展开口径变量 --expand-duration / --expand-easing（D10，含 reduced-motion 1ms） */
.amount-switch-enter-active,
.amount-switch-leave-active {
  transition:
    opacity var(--expand-duration) var(--expand-easing),
    transform var(--expand-duration) var(--expand-easing);
}

.amount-switch-enter-from,
.amount-switch-leave-to {
  opacity: 0;
  transform: translateY(6px);
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
