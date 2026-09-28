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
        <v-btn size="small" color="warning" variant="tonal" @click="openRestoreDialog">
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
          <!-- M9：:animation="180" 为 sortablejs flip 让位动画时长（拖动中其余行连续平滑让位、
               落点无跳变）；150–200ms 区间取值，属 D10 独立口径，不引用展开类动画的 --expand-duration。
               其余拖拽参数（delay / delay-on-touch-only / touch-start-threshold / ghost-class / drag-class）
               与保存回滚链路维持 v1.4.2 值不变。
               v1.4.3-boot2 M1（D1）：原「『其他』非末位即整列表禁用」的 disabled 绑定已删除——
               「其他」家族由 onDragEnd 与后端 reorder 归一化强制置尾，任何数据态拖拽永远可用 -->
          <Draggable
            v-model="dragList"
            :handle="'.drag-handle'"
            item-key="id"
            :delay="150"
            :delay-on-touch-only="true"
            :touch-start-threshold="5"
            :animation="180"
            ghost-class="drag-ghost"
            drag-class="drag-float"
            @start="onDragStart"
            @end="onDragEnd"
          >
            <template #item="{ element: cat }">
              <v-list-item class="category-list-item" rounded="lg">
                <template v-slot:prepend>
                  <!-- v1.4.3-boot2 M1（D7）：把手条件按「其他」本名收口，**不是** isOtherFamily——
                       旧名「其他支出 / 其他收入」两行属 M2 迁移前过渡态，照常给把手、可拖
                       （保存时被名次归一化推到尾部）；仅「其他」一行无把手、用同宽占位 -->
                  <v-icon
                    v-if="cat.name !== OTHER_CATEGORY_NAME"
                    class="drag-handle mr-1"
                    size="20"
                    color="grey"
                  >
                    mdi-drag-vertical
                  </v-icon>
                  <span v-else-if="isOther(cat)" class="drag-handle-placeholder mr-1" />
                  <!-- M8：行图标统一 .entry-avatar primary 10% 底 + primary 图标，
                       消除同页收支双色暗示（与设置页入口同款） -->
                  <v-avatar size="32" class="entry-avatar mr-2">
                    <v-icon size="16" color="primary">{{ cat.icon || 'mdi-circle' }}</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title class="text-body-2 category-title">
                  <span>{{ cat.name }}</span>
                  <!-- v1.4.4 M2（REQ-003 / D3 / 任务 7.2）：徽章改读**出身**列 `source`——
                       预设派生的用户副本 is_preset=0 而 source=1，改名/换图标/拖序后徽章不丢；
                       用户自建恒 source=0 无徽章（REQ-004）。is_preset 语义未动。 -->
                  <v-chip
                    v-if="cat.source === 1"
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
                    <!-- v1.4.4 M2（D8 / 任务 5.3）：预设派生副本**不可单删**（后端同口径 403），
                         反悔只能「恢复默认」全量丢弃；编辑/拖拽照旧，保存即 CoW -->
                    <v-btn
                      v-if="cat.source === 0"
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
            </template>
          </Draggable>
        </v-list>
      </div>
    </div>

    <!-- Category Dialog -->
    <AppDialog v-model="showCategoryDialog" max-width="400">
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
    </AppDialog>

    <!-- Delete Category Confirm -->
    <ConfirmDialog
      v-model="showDeleteCategoryDialog"
      title="删除分类"
      :message="deleteCategoryMessage"
      confirm-text="删除"
      @confirm="handleDeleteCategory"
    />

    <!-- Restore Defaults Confirm Dialog（v1.4.4 M2 / D6：确认前预告 N/M 数字） -->
    <AppDialog v-model="showRestoreConfirm" max-width="400">
      <v-card class="pa-4" rounded="xl">
        <v-card-title class="text-h6 pa-0 mb-2">恢复默认分类</v-card-title>
        <v-card-text class="pa-0 mb-4">
          <p class="text-body-2">恢复默认分类将：</p>
          <!-- presets 接口成功 → 三条带数字文案（逐字口径，任务 7.4）；
               失败 → 退化两条无数字版（任务 7.5），主流程不阻塞 -->
          <ul v-if="restorePreview" class="text-body-2 text-medium-emphasis">
            <li>
              删除 {{ restorePreview.customCount }} 个自定义分类（其下账单改挂「其他」）
            </li>
            <li>
              丢弃 {{ restorePreview.discardCount }} 个预设分类的定制（名称/图标/排序回到系统默认）
            </li>
            <li>账单总数不变，此操作不可撤销</li>
          </ul>
          <ul v-else class="text-body-2 text-medium-emphasis">
            <li>删除所有自定义分类，账单改挂「其他」</li>
            <li>预设分类恢复默认，定制将被丢弃</li>
          </ul>
        </v-card-text>
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showRestoreConfirm = false">取消</v-btn>
          <v-btn color="warning" @click="handleRestoreDefaults" :loading="restoring">
            确认恢复
          </v-btn>
        </div>
      </v-card>
    </AppDialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import Draggable from 'vuedraggable'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import { getRecords } from '@/api/records'
import { getPresetCategories } from '@/api/categories'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import CategoryIconPicker from '@/components/common/CategoryIconPicker.vue'
import AppDialog from '@/components/common/AppDialog.vue'

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
// v1.4.4 M2（D6 / 任务 7.2）：弹窗打开前的 N/M 预告；null = presets 接口失败 → 无数字概览版
const restorePreview = ref(null)

// ── v1.4.4 M2（§3.4 定制判据 / §8.2.3）：与后端
// category_service.compute_discarded_customizations **逐字同源**的前端镜像。
// 输入 list = store 已加载的可见列表（sort_order, id 升序），
// presets = GET /categories/presets 的 [{name, icon, sort_order}]（其顺序即默认排序）。
// 判据两腿，一行至多计一次（M 计「预设分类的条数」，非破坏属性数）：
//   1) 名/图标破坏 → 计 1 并 continue（不再进第二腿）；
//   2) 序尾记：剩余 source===1 行的预设下标按可见序排成一列，自上而下贪心匹配
//      presets 序，严格大于游标者前进，否则该行为破坏者计 1；「其他家族」行剔除
//      （其置尾名次由 OTHER_FAMILY_RANK 归一化强制决定，不是用户定制）。
// 用例表 §8.1.10 = §8.2.3 逐字复制、同表同期望；不一致即缺陷，以**后端返回值为准**。
function computeRestoreCounts(list, presets) {
  const indexOf = new Map(presets.map((p, pos) => [p.name, pos]))
  const iconOf = new Map(presets.map((p) => [p.name, p.icon]))

  let broken = 0
  const orderMarks = []
  for (const cat of list) {
    if (cat.source !== 1) continue // 自建行不属于「预设定制」口径
    const pos = indexOf.get(cat.name)
    if (pos === undefined || cat.icon !== iconOf.get(cat.name)) {
      broken += 1
      continue
    }
    if (Object.hasOwn(OTHER_FAMILY_RANK, cat.name)) continue
    orderMarks.push(pos)
  }

  let tail = 0
  let cursor = -1
  for (const pos of orderMarks) {
    if (pos > cursor) {
      cursor = pos
    } else {
      tail += 1
    }
  }
  return broken + tail
}

// 点「恢复默认分类」：先算 N（将被删除的自定义分类数）/ M（将被丢弃的预设定制数）再开弹窗。
// presets 拉取失败不阻塞主流程，退化为 §3.5 的无数字两行版。
async function openRestoreDialog() {
  restorePreview.value = null
  try {
    const presets = await getPresetCategories()
    const list = categories.value
    restorePreview.value = {
      customCount: list.filter((c) => c.source === 0).length,
      discardCount: computeRestoreCounts(list, presets),
    }
  } catch {
    restorePreview.value = null
  }
  showRestoreConfirm.value = true
}

// ── M3 拖拽排序（M8：收支共用，单一全列表） ─────────────────────────────
// 「其他」判定与后端 category_service 助手对齐：仅按 name（D11 唯一真源）；
// 预设行与其 CoW 用户副本同名，一并命中
const OTHER_CATEGORY_NAME = '其他'
// v1.4.3-boot2（D2/D6）「其他家族」：M2 迁移脚本执行前现场库仍并存旧名行，
// 判据放宽为三名集合。名次表必须与后端 category_service.OTHER_FAMILY_RANK
// **同规则、同名次、同稳定排序语义**（前端提交序 = 后端落库序，杜绝「保存后二次跳变」）。
const LEGACY_OTHER_NAMES = ['其他支出', '其他收入']
// 置尾名次固定：其他支出(0) < 其他收入(1) < 其他(2)——「其他」恒最后
const OTHER_FAMILY_RANK = Object.fromEntries(
  [...LEGACY_OTHER_NAMES, OTHER_CATEGORY_NAME].map((name, rank) => [name, rank])
)

function isOther(cat) {
  return !!cat && cat.name === OTHER_CATEGORY_NAME
}

// 「其他家族」判定（置尾归一化用）：三名任一即命中
function isOtherFamily(cat) {
  return !!cat && Object.hasOwn(OTHER_FAMILY_RANK, cat.name)
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

// 本地镜像后端 reorder 的置尾归一化（逐位一致）：非家族保序 + 家族按名次稳定排序置尾。
// 过渡态观感（D7）：M2 迁移前拖动其它行松手后，家族行可能「跳回」尾部——
// 这与后端落库序完全一致，保存后不再有第二次跳变；重进页面顺序即松手时的顺序。
function normalizeTail(list) {
  const normal = list.filter((c) => !isOtherFamily(c))
  const family = list
    .filter(isOtherFamily)
    .sort((a, b) => OTHER_FAMILY_RANK[a.name] - OTHER_FAMILY_RANK[b.name])
  return [...normal, ...family]
}

function onDragEnd() {
  dragList.value = normalizeTail(dragList.value)
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
      // sort_order 由服务端计算：追加到全列表末尾、「其他家族」之前
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

// v1.4.4 M2（§3.5）：成功提示文案与后端 routers/categories.py 的组装口径逐字一致。
// 响应拦截器只回传 data（§0.5 外壳的 message 到不了页面），故优先用后端 message、
// 缺失时按五键本地拼装——与仓库既有范式（importResultMessage 页内组文案）同构。
function restoreResultMessage(result) {
  if (result?.message) return result.message
  const segments = []
  if (result?.deleted_categories) segments.push(`删除 ${result.deleted_categories} 个自定义分类`)
  if (result?.discarded_customizations) segments.push(`${result.discarded_customizations} 个预设定制已复原`)
  if (result?.affected_records) segments.push(`${result.affected_records} 条记录归入「其他」`)
  return segments.length ? `已恢复默认分类：${segments.join('，')}` : '已恢复默认分类'
}

async function handleRestoreDefaults() {
  restoring.value = true
  try {
    const result = await categoriesStore.restoreDefaults()
    appStore.showToast(restoreResultMessage(result))
    showRestoreConfirm.value = false
    restorePreview.value = null
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

/* M6 口径对齐：行间垂直间距由 global.scss `.page-card .v-list-item { margin-block: 4px }`
   统一承载（同特异性的页内 margin 覆写会让本页比其余三页更窄，故删除） */
.category-list-item {
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
