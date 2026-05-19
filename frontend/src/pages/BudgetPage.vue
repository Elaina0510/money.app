<template>
  <div class="budget-page">
    <div class="page-header">
      <h1 class="page-title">预算</h1>
      <p class="page-subtitle">管理你的月度预算</p>
    </div>

    <!-- Monthly budget overview -->
    <v-card class="budget-overview-card mb-4">
      <div class="overview-content text-center pa-5">
        <div class="budget-label mb-1">本月预算</div>
        <div class="budget-amount mb-2">
          <span class="amount-number">¥{{ formatAmount(totalBudget) }}</span>
        </div>
        <v-progress-linear
          :model-value="budgetUsagePercent"
          :color="budgetUsagePercent > 80 ? 'error' : budgetUsagePercent > 50 ? 'warning' : 'success'"
          height="8"
          rounded
          class="mb-2"
        />
        <div class="budget-usage d-flex justify-space-between text-body-2">
          <span>已用 {{ formatAmount(totalSpent) }}</span>
          <span>{{ budgetUsagePercent.toFixed(0) }}%</span>
        </div>
      </div>
    </v-card>

    <!-- Category budgets -->
    <v-card class="pa-4 mb-3">
      <div class="d-flex justify-space-between align-center mb-3">
        <span class="text-subtitle-2 font-weight-bold">分类预算</span>
        <v-btn size="small" color="primary" variant="tonal" @click="showAddDialog = true">
          <v-icon start size="small">mdi-plus</v-icon>
          设置
        </v-btn>
      </div>

      <div v-if="budgets.length === 0" class="text-center pa-6 text-grey text-caption">
        暂无预算设置，点击上方按钮添加分类预算
      </div>

      <div v-for="item in budgets" :key="item.category_id" class="budget-item mb-3">
        <div class="d-flex justify-space-between align-center mb-1">
          <div class="d-flex align-center">
            <v-avatar size="32" :color="item.color + '20'" class="mr-2">
              <v-icon size="small" :color="item.color">{{ item.icon }}</v-icon>
            </v-avatar>
            <span class="text-body-2 font-weight-medium">{{ item.category_name }}</span>
          </div>
          <div class="text-body-2 text-right">
            <span class="font-weight-bold">{{ formatAmount(item.spent) }}</span>
            <span class="text-grey"> / {{ formatAmount(item.budget) }}</span>
          </div>
        </div>
        <v-progress-linear
          :model-value="(item.spent / item.budget) * 100"
          :color="(item.spent / item.budget) > 0.8 ? 'error' : (item.spent / item.budget) > 0.5 ? 'warning' : 'primary'"
          height="6"
          rounded
        />
      </div>
    </v-card>

    <!-- Add budget dialog -->
    <v-dialog v-model="showAddDialog" max-width="400">
      <v-card class="pa-4">
        <v-card-title class="text-h6 pa-0 mb-3">设置分类预算</v-card-title>
        <v-select
          v-model="budgetForm.category_id"
          :items="categories"
          item-title="name"
          item-value="id"
          label="选择分类"
          hide-details
          class="mb-3"
        />
        <v-text-field
          v-model.number="budgetForm.amount"
          label="预算金额"
          type="number"
          prefix="¥"
          hide-details
          class="mb-3"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showAddDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveBudget">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCategories } from '@/api/categories'
import { getByCategory, getSummary } from '@/api/statistics'
import { formatAmount, getCurrentMonthRange } from '@/utils/format'

const showAddDialog = ref(false)
const saving = ref(false)
const categories = ref([])
const categoryStats = ref([])
const summary = ref(null)
const budgets = ref([
  // Sample budget data - in a real app this would come from backend
  { category_id: 1, category_name: '餐饮', icon: 'mdi-food', color: '#FF6B6B', budget: 2000, spent: 1560 },
  { category_id: 2, category_name: '交通', icon: 'mdi-car', color: '#4DABF7', budget: 500, spent: 320 },
  { category_id: 3, category_name: '购物', icon: 'mdi-shopping', color: '#9775FA', budget: 1000, spent: 890 },
])

const budgetForm = ref({
  category_id: null,
  amount: 0,
})

const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.budget, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
const budgetUsagePercent = computed(() => {
  if (totalBudget.value === 0) return 0
  return (totalSpent.value / totalBudget.value) * 100
})

async function saveBudget() {
  saving.value = true
  try {
    // In a real app, would call an API
    showAddDialog.value = false
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const range = getCurrentMonthRange()
    const [cats, stats] = await Promise.all([
      getCategories(),
      getByCategory(range),
    ])
    categories.value = cats
    categoryStats.value = stats || []
  } catch (e) {
    console.error('Budget page load error:', e)
  }
})
</script>

<style scoped>
.budget-page {
  padding-bottom: 80px;
}

.page-header {
  padding: 24px 0 16px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
}

.page-subtitle {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.5);
  margin: 4px 0 0;
}

.budget-overview-card {
  border-radius: 20px !important;
  overflow: hidden;
}

.budget-label {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.5);
}

.budget-amount .amount-number {
  font-size: 36px;
  font-weight: 700;
}

.budget-item:last-child {
  margin-bottom: 0 !important;
}
</style>
