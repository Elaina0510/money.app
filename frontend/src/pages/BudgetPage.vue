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
        <v-btn size="small" color="primary" variant="tonal" @click="openAddDialog">
          <v-icon start size="small">mdi-plus</v-icon>
          设置
        </v-btn>
      </div>

      <div v-if="budgets.length === 0" class="text-center pa-6 text-grey text-caption">
        暂无预算设置，点击上方按钮添加分类预算
      </div>

      <div v-for="(item, index) in enrichedBudgets" :key="item.category_id" class="budget-item mb-3">
        <div class="d-flex justify-space-between align-center mb-1">
          <div class="d-flex align-center">
            <v-avatar size="32" :color="getColor(index) + '20'" class="mr-2">
              <v-icon size="small" :color="getColor(index)">{{ item.icon }}</v-icon>
            </v-avatar>
            <span class="text-body-2 font-weight-medium">{{ item.category_name }}</span>
          </div>
          <div class="d-flex align-center">
            <template v-if="editingBudget === item.category_id">
              <v-text-field
                v-model.number="editAmount"
                type="number"
                density="compact"
                hide-details
                variant="outlined"
                prefix="¥"
                style="width: 120px"
                class="mr-1"
                autofocus
                @keyup.enter="saveEdit(item)"
                @keyup.escape="cancelEdit"
              />
              <v-btn icon size="x-small" variant="text" color="primary" @click="saveEdit(item)" :loading="saving">
                <v-icon size="small">mdi-check</v-icon>
              </v-btn>
              <v-btn icon size="x-small" variant="text" @click="cancelEdit">
                <v-icon size="small">mdi-close</v-icon>
              </v-btn>
            </template>
            <template v-else>
              <span class="text-body-2 font-weight-bold">{{ formatAmount(item.spent) }}</span>
              <span class="text-grey"> / {{ formatAmount(item.amount) }}</span>
              <v-btn icon size="x-small" variant="text" class="ml-1" @click="startEdit(item)">
                <v-icon size="small" color="grey">mdi-pencil</v-icon>
              </v-btn>
            </template>
          </div>
        </div>
        <v-progress-linear
          :model-value="item.amount > 0 ? (item.spent / item.amount) * 100 : 0"
          :color="item.amount > 0 && (item.spent / item.amount) > 0.8 ? 'error' : item.amount > 0 && (item.spent / item.amount) > 0.5 ? 'warning' : 'primary'"
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
          :items="availableCategories"
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
import dayjs from 'dayjs'
import { getBudgets, batchSetBudgets } from '@/api/budgets'
import { getCategories } from '@/api/categories'
import { formatAmount } from '@/utils/format'

const COLOR_PALETTE = [
  '#FF6B6B', '#4DABF7', '#9775FA', '#51CF66', '#FF922B',
  '#22B8CF', '#F06595', '#845EF7', '#20C997', '#FD7E14',
]

function getColor(index) {
  return COLOR_PALETTE[index % COLOR_PALETTE.length]
}

const showAddDialog = ref(false)
const saving = ref(false)
const categories = ref([])
const budgets = ref([])
const editingBudget = ref(null)
const editAmount = ref(0)

const currentMonth = dayjs().format('YYYY-MM')

const budgetForm = ref({
  category_id: null,
  amount: 0,
})

const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
const budgetUsagePercent = computed(() => {
  if (totalBudget.value === 0) return 0
  return (totalSpent.value / totalBudget.value) * 100
})

// Merge budget data with category icon for display
const enrichedBudgets = computed(() => {
  return budgets.value.map(b => {
    const cat = categories.value.find(c => c.id === b.category_id)
    return {
      ...b,
      icon: cat?.icon || 'mdi-cash',
    }
  })
})

// Filter categories to only show expense categories that don't already have a budget
const availableCategories = computed(() => {
  const budgetCategoryIds = budgets.value.map(b => b.category_id)
  return categories.value.filter(c => c.type === 'expense' && !budgetCategoryIds.includes(c.id))
})

async function loadBudgets() {
  try {
    budgets.value = await getBudgets({ month: currentMonth }) || []
  } catch (e) {
    console.error('Load budgets error:', e)
    budgets.value = []
  }
}

async function loadCategories() {
  try {
    categories.value = await getCategories() || []
  } catch (e) {
    console.error('Load categories error:', e)
    categories.value = []
  }
}

function startEdit(item) {
  editingBudget.value = item.category_id
  editAmount.value = item.amount
}

function cancelEdit() {
  editingBudget.value = null
  editAmount.value = 0
}

async function saveEdit(item) {
  if (editAmount.value <= 0) return
  saving.value = true
  try {
    await batchSetBudgets({
      month: currentMonth,
      budgets: [{ category_id: item.category_id, amount: editAmount.value }],
    })
    editingBudget.value = null
    await loadBudgets()
  } catch (e) {
    console.error('Save budget error:', e)
  } finally {
    saving.value = false
  }
}

function openAddDialog() {
  budgetForm.value = { category_id: null, amount: 0 }
  showAddDialog.value = true
}

async function saveBudget() {
  if (!budgetForm.value.category_id || budgetForm.value.amount <= 0) return
  saving.value = true
  try {
    await batchSetBudgets({
      month: currentMonth,
      budgets: [{ category_id: budgetForm.value.category_id, amount: budgetForm.value.amount }],
    })
    showAddDialog.value = false
    budgetForm.value = { category_id: null, amount: 0 }
    await loadBudgets()
  } catch (e) {
    console.error('Save budget error:', e)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadBudgets(), loadCategories()])
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
