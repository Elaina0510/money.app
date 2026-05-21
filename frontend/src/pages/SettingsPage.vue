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
        <v-btn size="small" color="primary" variant="tonal" @click="showCategoryDialog = true">
          <v-icon start size="small">mdi-plus</v-icon>
          新增
        </v-btn>
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
                <v-btn icon variant="text" size="x-small" @click="editCategory(cat)">
                  <v-icon size="small" color="grey">mdi-pencil</v-icon>
                </v-btn>
                <v-btn
                  v-if="!cat.is_preset"
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
                <v-btn icon variant="text" size="x-small" @click="editCategory(cat)">
                  <v-icon size="small" color="grey">mdi-pencil</v-icon>
                </v-btn>
                <v-btn
                  v-if="!cat.is_preset"
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
      :message="`确定要删除「${deletingCategory?.name}」吗？`"
      confirm-text="删除"
      @confirm="handleDeleteCategory"
    />

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
          closable
          size="small"
          variant="tonal"
          class="mb-1"
          @click:close="confirmDeleteTag(tag)"
        >
          <v-icon start size="x-small">mdi-tag</v-icon>
          {{ tag.name }}
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
          class="mb-4"
          variant="outlined"
          @keydown.enter="saveTag"
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

const categories = ref([])
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

// Tag CRUD
const showTagDialog = ref(false)
const savingTag = ref(false)

const tagForm = reactive({ name: '', category_id: null })

// Delete tag
const showDeleteTagDialog = ref(false)
const deletingTag = ref(null)

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

function confirmDeleteCategory(cat) {
  deletingCategory.value = cat
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

async function saveTag() {
  if (!tagForm.name.trim()) return
  savingTag.value = true
  try {
    await categoriesStore.addTag({ name: tagForm.name.trim() })
    showTagDialog.value = false
    tagForm.name = ''
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

async function loadCategories() {
  try {
    categories.value = await categoriesStore.fetchCategories() || []
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
  await Promise.all([loadCategories(), loadTags()])
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

.page-subtitle {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
  margin: 2px 0 0;
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
</style>
