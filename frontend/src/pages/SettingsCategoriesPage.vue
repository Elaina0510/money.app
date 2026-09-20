<template>
  <div class="settings-categories-page">
    <!-- Header: back + actions（恢复默认 / 新增 自设置页下沉至此） -->
    <div class="d-flex align-center mb-3">
      <v-btn icon variant="text" size="small" class="mr-2" @click="$router.back()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <p class="text-caption text-grey mb-0">管理收支共用分类</p>
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

    <!-- 主体内容统一卡片图层（M4）：消除列表透视到页面背景 -->
    <div class="page-card">
      <div v-if="dragList.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无分类
      </div>

      <!-- 单一列表单分组（M8：分类收支共用，原「支出分类 / 收入分类」两组已合并）；
           section-block / section-title 为 M6 全局疏朗化口径类名（定义在 global.scss，本页只挂用） -->
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">全部分类</div>
        <v-list v-if="dragList.length" density="compact" class="bg-transparent pa-0">
          <Draggable
            v-model="dragList"
            :handle="'.drag-handle'"
            :disabled="isOtherLocked(dragList)"
            item-key="id"
            :delay="150"
            :delay-on-touch-only="true"
            :touch-start-threshold="5"
            ghost-class="drag-ghost"
            drag-class="drag-float"
            @start="onDragStart"
            @end="onDragEnd"
          >
            <template #item="{ element: cat }">
              <v-list-item class="category-list-item" rounded="lg">
                <template v-slot:prepend>
                  <v-icon v-if="!isOther(cat)" class="drag-handle mr-1" size="20" color="grey">
                    mdi-drag-vertical
                  </v-icon>
                  <span v-else class="drag-handle-placeholder mr-1" />
                  <!-- M8：行图标统一 .entry-avatar primary 10% 底 + primary 图标，
                       消除同页收支双色暗示（与设置页入口同款） -->
                  <v-avatar size="32" class="entry-avatar mr-2">
                    <v-icon size="16" color="primary">{{ cat.icon || 'mdi-circle' }}</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title class="text-body-2 category-title">
                  <span>{{ cat.name }}</span>
                  <v-chip
                    v-if="cat.is_preset"
                    size="x-small"
                    color="grey"
                    variant="tonal"
                    class="preset-chip"
                  >
                    预设
                  </v-chip>
                </v-list-item-title>
                <template v-slot:append>
                  <div class="d-flex action-btns">
                    <v-btn icon variant="text" size="x-small" @click="editCategory(cat)">
                      <v-icon size="small" color="grey">mdi-pencil</v-icon>
                    </v-btn>
                    <v-btn icon variant="text" size="x-small" @click="confirmDeleteCategory(cat)">
                      <v-icon size="small" color="error">mdi-delete</v-icon>
                    </v-btn>
                  </div>
                </template>
              </v-list-item>
            </template>
          </Draggable>
        </v-list>
      </div>
    </div>

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
        <!-- M8：分类收支共用，弹窗删「类型」下拉（保存载荷仅 {name, icon}） -->
        <div class="mb-3">
          <div class="text-caption text-grey mb-1">图标</div>
          <CategoryIconPicker v-model="categoryForm.icon" />
        </div>
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
          <v-alert type="warning" variant="tonal" class="mb-3"> 此操作不可撤销！ </v-alert>
          <p class="text-body-2">恢复默认分类将：</p>
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
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import Draggable from 'vuedraggable'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import { getRecords } from '@/api/records'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import CategoryIconPicker from '@/components/common/CategoryIconPicker.vue'

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

const { categories } = storeToRefs(categoriesStore)

// Category CRUD
const showCategoryDialog = ref(false)
const savingCategory = ref(false)
const editingCategory = ref(null)
const categoryForm = reactive({
  name: '',
  icon: 'mdi-cash',
})

// Delete category
const showDeleteCategoryDialog = ref(false)
const deletingCategory = ref(null)
const deleteCategoryMessage = ref('')

// Restore defaults
const showRestoreConfirm = ref(false)
const restoring = ref(false)

// ── M3 拖拽排序（M8：收支共用，单一全列表） ─────────────────────────────
// 「其他」判定与后端 category_service 助手对齐：仅按 name（D11 唯一真源）；
// 预设行与其 CoW 用户副本同名，一并命中
const OTHER_CATEGORY_NAME = '其他'

function isOther(cat) {
  return !!cat && cat.name === OTHER_CATEGORY_NAME
}

// 「其他」非末位（异常数据）→ 禁用拖动，避免拖出无法解释的顺序
function isOtherLocked(list) {
  const idx = list.findIndex(isOther)
  return idx >= 0 && idx !== list.length - 1
}

// 单一渲染源：模板只读 dragList；store 的 categories 仅作派生源（预设 CoW 后 id 会变）
const dragList = ref([])

watch(
  categories,
  (list) => {
    dragList.value = [...list]
  },
  { immediate: true }
)

// 拖前快照：保存失败时回滚本地顺序
const preDragSnapshot = ref([])

function onDragStart() {
  preDragSnapshot.value = [...dragList.value]
}

function onDragEnd() {
  const list = dragList.value
  const otherIdx = list.findIndex(isOther)
  // 本地镜像后端「末尾占位」归一化：「其他」被拖到中间 → 移回末位再提交，避免保存后跳变
  if (otherIdx >= 0 && otherIdx !== list.length - 1) {
    dragList.value = [...list.filter((c) => !isOther(c)), list[otherIdx]]
  }
  submitReorder(dragList.value)
}

async function submitReorder(list) {
  try {
    // 一次拖动只发一次 PUT /categories/reorder（原子保存），store 内已重拉对齐
    await categoriesStore.reorderCategories(list.map((c) => c.id))
    appStore.showToast('排序已保存') // 全流程唯一一次 toast
  } catch {
    // 失败回滚：先恢复拖前快照，再静默重拉以后端真值为准
    dragList.value = [...preDragSnapshot.value]
    await loadCategories()
  }
}

function editCategory(cat) {
  editingCategory.value = cat
  Object.assign(categoryForm, {
    name: cat.name,
    icon: cat.icon,
  })
  showCategoryDialog.value = true
}

async function saveCategory() {
  savingCategory.value = true
  try {
    if (editingCategory.value) {
      // 编辑载荷不含 type（M8 起分类无类型语义）与 sort_order（单个 PUT 不改排序）
      await categoriesStore.editCategory(editingCategory.value.id, {
        name: categoryForm.name,
        icon: categoryForm.icon,
      })
    } else {
      // sort_order 由服务端计算：追加到全列表末尾、「其他」之前
      await categoriesStore.addCategory({
        name: categoryForm.name,
        icon: categoryForm.icon,
      })
    }
    showCategoryDialog.value = false
    editingCategory.value = null
    resetCategoryForm()
    await loadCategories()
  } catch {
    // Toast shown by store
  } finally {
    savingCategory.value = false
  }
}

function resetCategoryForm() {
  categoryForm.name = ''
  categoryForm.icon = 'mdi-cash'
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
    } catch {
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

async function loadCategories() {
  try {
    await categoriesStore.fetchCategories()
  } catch (e) {
    console.error('Load categories error:', e)
  }
}

onMounted(async () => {
  await loadCategories()
})
</script>

<style scoped>
.settings-categories-page {
  padding-bottom: 20px;
}

.category-list-item {
  margin: 2px 0;
  transition: all 0.15s ease;
}

.category-list-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.category-title {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
}

.preset-chip {
  flex-shrink: 0;
  font-size: 10px !important;
  height: 18px !important;
}

.category-list-item :deep(.v-list-item__append) {
  margin-left: 8px;
}

.category-list-item :deep(.v-btn--icon.v-btn--size-x-small) {
  width: 24px;
  height: 24px;
}

.action-btns {
  gap: 1px;
}

/* ── M3 拖拽排序态 ───────────────────────────────────────── */
/* touch-action: none 只加在把手上：加整行会杀死列表滚动 */
.drag-handle {
  cursor: grab;
  touch-action: none;
}

.drag-handle:active {
  cursor: grabbing;
}

/* 「其他」不可拖，用同宽占位保持行高与对齐一致 */
.drag-handle-placeholder {
  width: 20px;
  flex-shrink: 0;
}

/* 插入位置指示 */
.drag-ghost {
  opacity: 0.4;
  background: rgba(var(--v-theme-primary), 0.08);
}

/* 拖起浮动态 */
.drag-float {
  transform: scale(1.02);
  box-shadow: var(--shadow-level-3);
}
</style>
