<template>
  <div class="settings-page">
    <!-- Page Header -->
    <div class="page-header mb-3">
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">管理分类、标签和数据</p>
    </div>

    <!-- Category Management -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <div class="d-flex align-center">
          <v-avatar size="36" color="rgba(103, 80, 164, 0.1)" class="mr-2">
            <v-icon color="primary" size="20">mdi-shape</v-icon>
          </v-avatar>
          <span class="text-subtitle-2 font-weight-bold">分类管理</span>
        </div>
        <div class="d-flex ga-2">
          <v-btn size="small" color="warning" variant="tonal" @click="showRestoreConfirm = true">
            <v-icon start size="small">mdi-restore</v-icon>
            恢复默认
          </v-btn>
          <v-btn size="small" color="primary" variant="tonal" @click="showCategoryDialog = true">
            <v-icon start size="small">mdi-plus</v-icon>
            新增
          </v-btn>
        </div>
      </div>

      <div v-if="categories.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无分类
      </div>

      <!-- Expense Categories -->
      <div class="mb-2">
        <div class="text-caption text-grey font-weight-medium mb-1">支出分类</div>
        <v-list v-if="expenseCategories.length" density="compact" class="bg-transparent pa-0">
          <v-list-item v-for="cat in expenseCategories" :key="cat.id" class="category-list-item" rounded="lg">
            <template v-slot:prepend>
              <v-avatar size="32" color="#FFE8E8" class="mr-2">
                <v-icon size="16" color="#FF6B6B">{{ cat.icon || 'mdi-circle' }}</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title class="text-body-2">
              {{ cat.name }}
              <v-chip v-if="cat.is_preset" size="x-small" color="grey" variant="tonal" class="ml-1">
                预设
              </v-chip>
            </v-list-item-title>
            <template v-slot:append>
              <div class="d-flex ga-1">
                <v-btn
                  v-if="expenseCategories.indexOf(cat) > 0"
                  icon variant="text" size="x-small"
                  @click="moveCategory(cat, -1)"
                >
                  <v-icon size="small" color="grey">mdi-chevron-up</v-icon>
                </v-btn>
                <v-btn
                  v-if="expenseCategories.indexOf(cat) < expenseCategories.length - 1"
                  icon variant="text" size="x-small"
                  @click="moveCategory(cat, 1)"
                >
                  <v-icon size="small" color="grey">mdi-chevron-down</v-icon>
                </v-btn>
                <v-btn icon variant="text" size="x-small" @click="editCategory(cat)">
                  <v-icon size="small" color="grey">mdi-pencil</v-icon>
                </v-btn>
                <v-btn
                  icon
                  variant="text"
                  size="x-small"
                  @click="confirmDeleteCategory(cat)"
                >
                  <v-icon size="small" color="error">mdi-delete</v-icon>
                </v-btn>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <!-- Income Categories -->
      <div>
        <div class="text-caption text-grey font-weight-medium mb-1">收入分类</div>
        <v-list v-if="incomeCategories.length" density="compact" class="bg-transparent pa-0">
          <v-list-item v-for="cat in incomeCategories" :key="cat.id" class="category-list-item" rounded="lg">
            <template v-slot:prepend>
              <v-avatar size="32" color="#E8FFF3" class="mr-2">
                <v-icon size="16" color="#20C997">{{ cat.icon || 'mdi-circle' }}</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title class="text-body-2">
              {{ cat.name }}
              <v-chip v-if="cat.is_preset" size="x-small" color="grey" variant="tonal" class="ml-1">
                预设
              </v-chip>
            </v-list-item-title>
            <template v-slot:append>
              <div class="d-flex ga-1">
                <v-btn
                  v-if="incomeCategories.indexOf(cat) > 0"
                  icon variant="text" size="x-small"
                  @click="moveCategory(cat, -1)"
                >
                  <v-icon size="small" color="grey">mdi-chevron-up</v-icon>
                </v-btn>
                <v-btn
                  v-if="incomeCategories.indexOf(cat) < incomeCategories.length - 1"
                  icon variant="text" size="x-small"
                  @click="moveCategory(cat, 1)"
                >
                  <v-icon size="small" color="grey">mdi-chevron-down</v-icon>
                </v-btn>
                <v-btn icon variant="text" size="x-small" @click="editCategory(cat)">
                  <v-icon size="small" color="grey">mdi-pencil</v-icon>
                </v-btn>
                <v-btn
                  icon
                  variant="text"
                  size="x-small"
                  @click="confirmDeleteCategory(cat)"
                >
                  <v-icon size="small" color="error">mdi-delete</v-icon>
                </v-btn>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </div>
    </v-card>

    <!-- Category Dialog -->
    <v-dialog v-model="showCategoryDialog" max-width="400" transition="dialog-bottom-transition">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-4">
          {{ editingCategory ? '编辑分类' : '新增分类' }}
        </v-card-title>
        <v-text-field
          v-model="categoryForm.name"
          label="名称"
          hide-details
          class="mb-3"
          variant="outlined"
        />
        <v-select
          v-model="categoryForm.type"
          :items="typeOptions"
          label="类型"
          hide-details
          class="mb-3"
          variant="outlined"
        />
        <v-text-field
          v-model="categoryForm.icon"
          label="图标 (mdi-*)"
          placeholder="mdi-food"
          hide-details
          class="mb-3"
          variant="outlined"
        />
        <v-text-field
          v-model.number="categoryForm.sort_order"
          label="排序"
          type="number"
          hide-details
          class="mb-4"
          variant="outlined"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showCategoryDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingCategory" @click="saveCategory" variant="tonal">
            {{ editingCategory ? '更新' : '创建' }}
          </v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Delete Category Confirm -->
    <ConfirmDialog
      v-model="showDeleteCategoryDialog"
      title="删除分类"
      :message="deleteCategoryMessage"
      confirm-text="删除"
      @confirm="handleDeleteCategory"
    />

    <!-- Restore Defaults Confirm Dialog -->
    <v-dialog v-model="showRestoreConfirm" max-width="400">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-2">恢复默认分类</v-card-title>
        <v-card-text class="pa-0 mb-4">
          <v-alert type="warning" variant="tonal" class="mb-3">
            此操作不可撤销！
          </v-alert>
          <p class="text-body-2">
            恢复默认分类将：
          </p>
          <ul class="text-body-2 text-medium-emphasis">
            <li>删除所有自定义分类</li>
            <li>自定义分类下的账单记录将被保留，但失去分类关联</li>
            <li>重置预设分类为默认排序</li>
          </ul>
        </v-card-text>
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showRestoreConfirm = false">取消</v-btn>
          <v-btn color="warning" @click="handleRestoreDefaults" :loading="restoring">
            确认恢复
          </v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Tags Management -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <div class="d-flex align-center">
          <v-avatar size="36" color="rgba(77, 171, 247, 0.1)" class="mr-2">
            <v-icon color="info" size="20">mdi-tag-multiple</v-icon>
          </v-avatar>
          <span class="text-subtitle-2 font-weight-bold">标签管理</span>
        </div>
        <v-btn size="small" color="primary" variant="tonal" @click="showTagDialog = true">
          <v-icon start size="small">mdi-plus</v-icon>
          新增
        </v-btn>
      </div>

      <div v-if="tags.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无标签
      </div>

      <div v-else class="d-flex flex-wrap ga-1">
        <v-chip
          v-for="tag in tags"
          :key="tag.id"
          size="small"
          variant="tonal"
          class="mb-1"
        >
          <v-icon start size="x-small">mdi-tag</v-icon>
          {{ tag.name }}
          <template v-slot:append>
            <v-icon size="x-small" class="ml-1 tag-delete-icon" @click.stop="confirmDeleteTag(tag)">
              mdi-close
            </v-icon>
          </template>
        </v-chip>
      </div>
    </v-card>

    <!-- Tag Dialog -->
    <v-dialog v-model="showTagDialog" max-width="360" transition="dialog-bottom-transition">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-4">新增标签</v-card-title>
        <v-text-field
          v-model="tagForm.name"
          label="标签名称"
          hide-details
          class="mb-3"
          variant="outlined"
          @keydown.enter="saveTag"
        />
        <v-select
          v-model="tagForm.category_id"
          :items="categories"
          item-title="name"
          item-value="id"
          label="所属分类 *"
          :rules="[v => !!v || '请选择分类']"
          hide-details="auto"
          class="mb-3"
          variant="outlined"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showTagDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingTag" @click="saveTag" variant="tonal">创建</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Delete Tag Confirm -->
    <ConfirmDialog
      v-model="showDeleteTagDialog"
      title="删除标签"
      :message="`确定要删除标签「${deletingTag?.name}」吗？`"
      confirm-text="删除"
      @confirm="handleDeleteTag"
    />

    <!-- Budget Management -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <div class="d-flex align-center">
          <v-avatar size="36" color="rgba(156, 39, 176, 0.1)" class="mr-2">
            <v-icon color="purple" size="20">mdi-piggy-bank-outline</v-icon>
          </v-avatar>
          <span class="text-subtitle-2 font-weight-bold">预算管理</span>
        </div>
        <v-btn size="small" color="primary" variant="tonal" @click="openBudgetAddDialog">
          <v-icon start size="small">mdi-plus</v-icon>
          设置
        </v-btn>
      </div>

      <!-- 月度预算概览 -->
      <v-card variant="tonal" class="pa-4 mb-3" rounded="lg">
        <div class="text-caption text-grey mb-1">本月预算</div>
        <div class="text-h5 font-weight-bold mb-2">¥{{ formatAmount(totalBudget) }}</div>
        <v-progress-linear
          :model-value="budgetUsagePercent"
          :color="budgetUsagePercent > 80 ? 'error' : budgetUsagePercent > 50 ? 'warning' : 'success'"
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

      <div v-for="(item, index) in enrichedBudgets" :key="item.category_id" class="budget-item mb-3">
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
              <v-btn icon size="x-small" variant="text" color="primary" @click="saveBudgetEdit(item)" :loading="savingBudget">
                <v-icon size="small">mdi-check</v-icon>
              </v-btn>
              <v-btn icon size="x-small" variant="text" @click="cancelBudgetEdit">
                <v-icon size="small">mdi-close</v-icon>
              </v-btn>
            </template>
            <template v-else>
              <span class="text-body-2 font-weight-bold">{{ formatAmount(item.spent) }}</span>
              <span class="text-grey"> / {{ formatAmount(item.amount) }}</span>
              <v-btn icon size="x-small" variant="text" class="ml-1" @click="startBudgetEdit(item)">
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

    <!-- Budget Add Dialog -->
    <v-dialog v-model="showBudgetAddDialog" max-width="400">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-3">设置分类预算</v-card-title>
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

    <!-- Quick Template Management -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex justify-space-between align-center mb-3">
        <div class="d-flex align-center">
          <v-avatar size="36" color="rgba(0, 150, 136, 0.1)" class="mr-2">
            <v-icon color="teal" size="20">mdi-lightning-bolt</v-icon>
          </v-avatar>
          <span class="text-subtitle-2 font-weight-bold">快速记账</span>
        </div>
        <v-btn size="small" color="primary" variant="tonal" @click="showQuickTemplateDialog = true">
          <v-icon start size="small">mdi-plus</v-icon>
          新增
        </v-btn>
      </div>

      <div v-if="quickTemplates.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无快速记账模板
      </div>

      <v-list v-else density="compact" class="bg-transparent pa-0">
        <v-list-item v-for="tpl in quickTemplates" :key="(tpl.tag_id || '') + '-' + tpl.amount + '-' + tpl.source" class="quick-template-item">
          <template v-slot:prepend>
            <v-avatar size="32" :color="tpl.type === 'expense' ? '#FFE8E8' : '#E8FFF3'" class="mr-2">
              <v-icon size="16" :color="tpl.type === 'expense' ? '#FF6B6B' : '#20C997'">
                {{ tpl.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
              </v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2">
            {{ tpl.tag_name }} · ¥{{ tpl.amount }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ tpl.category_name }}{{ tpl.count > 0 ? ` · 使用 ${tpl.count} 次` : '' }}
          </v-list-item-subtitle>
          <template v-slot:append>
            <v-btn icon variant="text" size="x-small" @click="removeQuickTemplate(tpl)">
              <v-icon size="small" color="error">mdi-delete</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Quick Template Add Dialog -->
    <v-dialog v-model="showQuickTemplateDialog" max-width="400">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-4">新增快速记账</v-card-title>
        <v-select
          v-model="quickTemplateForm.tag_id"
          :items="tags"
          item-title="name"
          item-value="id"
          label="选择标签 *"
          :rules="[v => !!v || '请选择标签']"
          hide-details="auto"
          class="mb-3"
          variant="outlined"
        />
        <v-text-field
          v-model.number="quickTemplateForm.amount"
          label="金额 *"
          type="number"
          prefix="¥"
          :rules="[v => v > 0 || '请输入金额']"
          hide-details="auto"
          class="mb-3"
          variant="outlined"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showQuickTemplateDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingQuickTemplate" @click="saveQuickTemplate">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- Account Section -->
    <v-card class="pa-4 mb-3 settings-card" rounded="xl">
      <div class="d-flex align-center mb-2">
        <v-avatar size="36" color="rgba(255, 152, 0, 0.1)" class="mr-2">
          <v-icon color="warning" size="20">mdi-account</v-icon>
        </v-avatar>
        <span class="text-subtitle-2 font-weight-bold">账号</span>
      </div>

      <div v-if="isLoggedIn" class="d-flex align-center justify-space-between mt-2">
        <div class="d-flex align-center">
          <v-avatar size="36" color="primary" class="mr-2">
            <span class="text-body-2 text-white font-weight-bold">{{ username.charAt(0) }}</span>
          </v-avatar>
          <div>
            <div class="text-body-2 font-weight-medium">{{ username }}</div>
            <div class="text-caption text-grey">已登录</div>
          </div>
        </div>
        <v-btn variant="tonal" color="error" size="small" @click="handleLogoutInSettings">
          <v-icon start size="small">mdi-logout</v-icon>
          退出
        </v-btn>
      </div>

      <div v-else class="mt-2">
        <div class="text-body-2 text-grey mb-3">未登录，部分功能可能受限</div>
        <v-btn color="primary" variant="tonal" @click="goToLogin">
          <v-icon start>mdi-login</v-icon>
          去登录
        </v-btn>
      </div>
    </v-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import { getRecords, getQuickTemplates, addQuickTemplate, deleteQuickTemplate } from '@/api/records'
import { getBudgets, batchSetBudgets } from '@/api/budgets'
import { formatAmount } from '@/utils/format'
import dayjs from 'dayjs'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

const { categories } = storeToRefs(categoriesStore)
const tags = ref([])

const expenseCategories = computed(() => categories.value.filter(c => c.type === 'expense'))
const incomeCategories = computed(() => categories.value.filter(c => c.type === 'income'))

// Category CRUD
const showCategoryDialog = ref(false)
const savingCategory = ref(false)
const editingCategory = ref(null)
const categoryForm = reactive({
  name: '',
  type: 'expense',
  icon: 'mdi-cash',
  sort_order: 0,
})
const typeOptions = [
  { title: '支出', value: 'expense' },
  { title: '收入', value: 'income' },
]

// Delete category
const showDeleteCategoryDialog = ref(false)
const deletingCategory = ref(null)
const deleteCategoryMessage = ref('')

// Restore defaults
const showRestoreConfirm = ref(false)
const restoring = ref(false)

// Tag CRUD
const showTagDialog = ref(false)
const savingTag = ref(false)

const tagForm = reactive({ name: '', category_id: null })

// Budget state
const budgets = ref([])
const showBudgetAddDialog = ref(false)
const savingBudget = ref(false)
const editingBudget = ref(null)
const editBudgetAmount = ref(0)
const budgetForm = ref({ category_id: null, amount: 0 })
const currentMonth = dayjs().format('YYYY-MM')

const BUDGET_COLORS = [
  '#FF6B6B', '#4DABF7', '#9775FA', '#51CF66', '#FF922B',
  '#22B8CF', '#F06595', '#845EF7', '#20C997', '#FD7E14',
]

const totalBudget = computed(() => budgets.value.reduce((sum, b) => sum + b.amount, 0))
const totalSpent = computed(() => budgets.value.reduce((sum, b) => sum + b.spent, 0))
const budgetUsagePercent = computed(() => {
  if (totalBudget.value === 0) return 0
  return (totalSpent.value / totalBudget.value) * 100
})

const enrichedBudgets = computed(() => {
  return budgets.value.map(b => {
    const cat = categories.value.find(c => c.id === b.category_id)
    return { ...b, icon: cat?.icon || 'mdi-cash' }
  })
})

const availableBudgetCategories = computed(() => {
  const budgetCategoryIds = budgets.value.map(b => b.category_id)
  return categories.value.filter(c => c.type === 'expense' && !budgetCategoryIds.includes(c.id))
})

// Quick template state
const quickTemplates = ref([])
const showQuickTemplateDialog = ref(false)
const savingQuickTemplate = ref(false)
const quickTemplateForm = ref({ tag_id: null, amount: 0 })

// 账号状态
const isLoggedIn = computed(() => !!localStorage.getItem('token'))
const username = computed(() => localStorage.getItem('username') || '')

function goToLogin() {
  router.push('/login')
}

function handleLogoutInSettings() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('userId')
  appStore.showToast('已退出登录', 'info')
  // 刷新页面让路由守卫重新检查
  router.push('/login')
}

// Delete tag
const showDeleteTagDialog = ref(false)
const deletingTag = ref(null)

async function moveCategory(cat, direction) {
  const list = cat.type === 'expense' ? expenseCategories.value : incomeCategories.value
  const idx = list.indexOf(cat)
  const target = list[idx + direction]
  if (!target) return
  try {
    const tempOrder = cat.sort_order
    await categoriesStore.editCategory(cat.id, { sort_order: target.sort_order })
    await categoriesStore.editCategory(target.id, { sort_order: tempOrder })
    await loadCategories()
  } catch (e) {
    // Toast shown by store
  }
}

function editCategory(cat) {
  editingCategory.value = cat
  Object.assign(categoryForm, {
    name: cat.name,
    type: cat.type,
    icon: cat.icon,
    sort_order: cat.sort_order,
  })
  showCategoryDialog.value = true
}

async function saveCategory() {
  savingCategory.value = true
  try {
    const data = { ...categoryForm }
    if (editingCategory.value) {
      await categoriesStore.editCategory(editingCategory.value.id, data)
    } else {
      await categoriesStore.addCategory(data)
    }
    showCategoryDialog.value = false
    editingCategory.value = null
    resetCategoryForm()
    await loadCategories()
  } catch (e) {
    // Toast shown by store
  } finally {
    savingCategory.value = false
  }
}

function resetCategoryForm() {
  categoryForm.name = ''
  categoryForm.type = 'expense'
  categoryForm.icon = 'mdi-cash'
  categoryForm.sort_order = 0
}

async function confirmDeleteCategory(cat) {
  deletingCategory.value = cat
  try {
    const result = await getRecords({ category_id: cat.id, page_size: 1 })
    const count = result.total || 0
    if (count > 0) {
      deleteCategoryMessage.value = `「${cat.name}」下有 ${count} 条账单记录，删除分类将同时删除所有关联账单，确认删除？`
    } else {
      deleteCategoryMessage.value = `确定要删除「${cat.name}」吗？`
    }
  } catch {
    deleteCategoryMessage.value = `确定要删除「${cat.name}」吗？`
  }
  showDeleteCategoryDialog.value = true
}

async function handleDeleteCategory() {
  if (deletingCategory.value) {
    try {
      await categoriesStore.removeCategory(deletingCategory.value.id)
      await loadCategories()
    } catch (e) {
      // Toast shown by store
    }
  }
  showDeleteCategoryDialog.value = false
  deletingCategory.value = null
}

async function handleRestoreDefaults() {
  restoring.value = true
  try {
    const result = await categoriesStore.restoreDefaults()
    appStore.showToast(result.message || '已恢复默认分类')
    showRestoreConfirm.value = false
  } catch (e) {
    appStore.showToast(e.message || '恢复失败', 'error')
  } finally {
    restoring.value = false
  }
}

async function saveTag() {
  if (!tagForm.name.trim() || !tagForm.category_id) return
  savingTag.value = true
  try {
    await categoriesStore.addTag({ name: tagForm.name.trim(), category_id: tagForm.category_id })
    showTagDialog.value = false
    tagForm.name = ''
    tagForm.category_id = null
    await loadTags()
  } catch (e) {
    // Toast shown by store
  } finally {
    savingTag.value = false
  }
}

function confirmDeleteTag(tag) {
  deletingTag.value = tag
  showDeleteTagDialog.value = true
}

async function handleDeleteTag() {
  if (deletingTag.value) {
    try {
      await categoriesStore.removeTag(deletingTag.value.id)
      await loadTags()
    } catch (e) {
      // Toast shown by store
    }
  }
  showDeleteTagDialog.value = false
  deletingTag.value = null
}

function getBudgetColor(index) {
  return BUDGET_COLORS[index % BUDGET_COLORS.length]
}

async function loadBudgets() {
  try {
    budgets.value = await getBudgets({ month: currentMonth }) || []
  } catch (e) {
    console.error('Load budgets error:', e)
    budgets.value = []
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
      month: currentMonth,
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
      month: currentMonth,
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

async function loadQuickTemplates() {
  try {
    quickTemplates.value = await getQuickTemplates() || []
  } catch (e) {
    console.error('Load quick templates error:', e)
    quickTemplates.value = []
  }
}

async function removeQuickTemplate(tpl) {
  try {
    // Manual templates have an 'id' field, auto templates don't
    if (tpl.id) {
      await deleteQuickTemplate(tpl.id)
    }
    await loadQuickTemplates()
  } catch (e) {
    console.error('Remove quick template error:', e)
  }
}

async function saveQuickTemplate() {
  if (!quickTemplateForm.value.tag_id || quickTemplateForm.value.amount <= 0) return
  savingQuickTemplate.value = true
  try {
    await addQuickTemplate({
      tag_id: quickTemplateForm.value.tag_id,
      amount: quickTemplateForm.value.amount,
    })
    showQuickTemplateDialog.value = false
    quickTemplateForm.value = { tag_id: null, amount: 0 }
    await loadQuickTemplates()
  } catch (e) {
    console.error('Save quick template error:', e)
  } finally {
    savingQuickTemplate.value = false
  }
}

async function loadCategories() {
  try {
    await categoriesStore.fetchCategories()
  } catch (e) {
    console.error('Load categories error:', e)
  }
}

async function loadTags() {
  try {
    await categoriesStore.fetchTags()
    tags.value = categoriesStore.tags
  } catch (e) {
    console.error('Load tags error:', e)
  }
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadTags(), loadBudgets(), loadQuickTemplates()])
})
</script>

<style scoped>
.settings-page {
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

.settings-card {
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.category-list-item {
  margin: 2px 0;
  transition: all 0.15s ease;
}

.category-list-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.tag-delete-icon {
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.15s ease;
}
.tag-delete-icon:hover {
  opacity: 1;
  color: rgb(var(--v-theme-error));
}
</style>
