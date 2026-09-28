<template>
  <div class="settings-tags-page">
    <!-- Header: back + 多选 | 新增 + 清空（v1.4.4 M1 D7 位次） -->
    <div class="d-flex align-center mb-3">
      <v-btn icon variant="text" size="small" class="mr-2" @click="$router.back()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <p class="text-caption text-grey mb-0">{{ headerHint }}</p>
      </div>
      <v-btn size="small" color="primary" variant="tonal" class="mr-2" @click="toggleMultiSelect">
        <v-icon start size="small">mdi-checkbox-marked-outline</v-icon>
        多选
      </v-btn>
      <v-btn size="small" color="primary" variant="tonal" @click="showTagDialog = true">
        <v-icon start size="small">mdi-plus</v-icon>
        新增
      </v-btn>
      <!-- 清空（REQ-001）：弱色口径 = variant="text" 且不传 color（继承前景色，禁点 error/warning 彩色）；
           total === 0 禁用；多选态下整钮不渲染，避免与批量「删除」双入口 -->
      <v-btn
        v-if="!multiSelect"
        size="small"
        variant="text"
        class="ml-2"
        :disabled="total === 0"
        @click="confirmClearAll"
      >
        清空
      </v-btn>
    </div>

    <!-- 主体内容统一卡片图层（M4）：chip 云不再直贴页面背景 -->
    <div class="page-card">
      <div v-if="displayedTags.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无标签
      </div>

      <!-- 多选操作条（REQ-002）：已选 ≥1 才浮出，复用账单页 Transition name="batch-bar" 动效类与版式 -->
      <Transition name="batch-bar">
        <div v-if="multiSelect && selectedIds.length > 0" class="batch-bar mb-3">
          <v-card rounded="xl" class="pa-2">
            <div class="d-flex align-center justify-space-between px-2">
              <v-chip color="primary" size="small" class="mr-2">已选 {{ selectedIds.length }} 个</v-chip>
              <div class="d-flex ga-1">
                <v-btn color="error" variant="tonal" size="small" @click="confirmBatchDelete">
                  <v-icon start size="small">mdi-delete</v-icon>
                  删除
                </v-btn>
                <v-btn variant="text" size="small" @click="exitMultiSelect">取消</v-btn>
              </div>
            </div>
          </v-card>
        </div>
      </Transition>

      <!-- 单一区块（M6 疏朗化口径）：section-block / section-title 类名定义在 global.scss，
           本页只挂用（与分类页 M8 落地的单块写法同款） -->
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">全部标签</div>

        <div v-if="displayedTags.length" class="d-flex flex-wrap ga-1">
          <!-- 多选态（REQ-002）：勾选图标同系 filled 配对（未选 mdi-checkbox-blank-circle / 已选
               mdi-checkbox-marked，ui-design 0.8 图标系别一致），点 chip 主体切换选中；
               此态下单 chip ✕ 不渲染（避免与批量「删除」双入口） -->
          <v-chip
            v-for="tag in displayedTags"
            :key="tag.id"
            size="small"
            variant="tonal"
            class="mb-1"
            :class="{ 'tag-chip-selected': isSelected(tag.id) }"
            @click="onChipClick(tag)"
          >
            <v-icon start size="x-small">{{ chipLeadingIcon(tag.id) }}</v-icon>
            {{ tag.name }}
            <template v-slot:append>
              <v-icon
                v-if="!multiSelect"
                size="x-small"
                class="ml-1 tag-delete-icon"
                @click.stop="confirmDeleteTag(tag)"
              >
                mdi-close
              </v-icon>
            </template>
          </v-chip>
        </div>

        <!-- 分页展开区（M5）：标签数 ≤ PAGE_SIZE 时整块不渲染，页面与改版前一致 -->
        <div v-if="total > PAGE_SIZE" class="d-flex flex-column align-center mt-2" style="gap: 4px">
          <v-btn
            v-if="hasMore"
            variant="text"
            color="primary"
            size="small"
            :loading="loadingMore"
            @click="loadMore"
          >
            展开更多
          </v-btn>
          <p class="text-caption text-grey mb-0">已显示 {{ displayedTags.length }} / 共 {{ total }} 个</p>
        </div>
      </div>
    </div>

    <!-- Tag Dialog -->
    <AppDialog v-model="showTagDialog" max-width="360">
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
          transition="fab-transition"
          :items="categories"
          item-title="name"
          item-value="id"
          label="所属分类 *"
          :rules="[(v) => !!v || '请选择分类']"
          hide-details="auto"
          class="mb-3"
          variant="outlined"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showTagDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingTag" @click="saveTag" variant="tonal">创建</v-btn>
        </div>
      </v-card>
    </AppDialog>

    <!-- Delete Tag Confirm -->
    <ConfirmDialog
      v-model="showDeleteTagDialog"
      title="删除标签"
      :message="`确定要删除标签「${deletingTag?.name}」吗？`"
      confirm-text="删除"
      @confirm="handleDeleteTag"
    />

    <!-- 清空全部标签 Confirm（REQ-001 / 任务 5.2：未确认零请求零副作用） -->
    <ConfirmDialog
      v-model="showClearAllDialog"
      title="清空全部标签"
      :message="`将删除全部 ${total} 个标签，账单上的标签标记同步移除，此操作不可撤销`"
      confirm-text="清空"
      :loading="clearing"
      @confirm="onConfirmClearAll"
    />

    <!-- 批量删除已选标签 Confirm（REQ-002 / 任务 5.5） -->
    <ConfirmDialog
      v-model="showBatchDeleteDialog"
      title="批量删除标签"
      :message="`确定删除已选的 ${selectedIds.length} 个标签？账单上的标签标记同步移除，此操作不可撤销`"
      confirm-text="删除"
      :loading="batchDeleting"
      @confirm="onConfirmBatchDelete"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { getTagsPaged } from '@/api/tags'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import AppDialog from '@/components/common/AppDialog.vue'

const categoriesStore = useCategoriesStore()

// categories 供弹窗下拉（共享 store）；chip 云渲染源改为本地分页列表 displayedTags，
// store.tags 仅作跨页共享缓存与全量计数（本页不再直读）
const { categories } = storeToRefs(categoriesStore)

// 分页展开（M5）：首屏一页，其余靠「展开更多」增量加载
const displayedTags = ref([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 20
const loadingMore = ref(false)
// 越界页短路标记：某次增量拿到空 items（多端并发删除使末页前移）时置真，
// 避免「展开更多」停在原地反复请求；resetPaging 重查时复位
const pageExhausted = ref(false)
const hasMore = computed(() => !pageExhausted.value && displayedTags.value.length < total.value)

// Tag CRUD
const showTagDialog = ref(false)
const savingTag = ref(false)

const tagForm = reactive({ name: '', category_id: null })

// Delete tag
const showDeleteTagDialog = ref(false)
const deletingTag = ref(null)

// ── v1.4.4 M1：清空（REQ-001）+ 多选批量删除（REQ-002）两态流 ────────────────
// 多选态：选中范围 = 已加载 displayedTags（未「展开更多」部分不含，需求既裁定）；
// 不持久化、不跨页——退出多选即清空，组件卸载自然归零
const multiSelect = ref(false)
const selectedIds = ref([])
const showBatchDeleteDialog = ref(false)
const batchDeleting = ref(false)

// 清空态
const showClearAllDialog = ref(false)
const clearing = ref(false)

// 页头提示随态切换；普通态文案逐字保留（M6 既有断言锚）
const headerHint = computed(() =>
  multiSelect.value
    ? '多选模式：点击标签选中，已选 1 个以上可批量删除'
    : '管理标签，点击标签右侧 × 可删除'
)

function isSelected(id) {
  return selectedIds.value.includes(id)
}

// 勾选图标同系 filled 配对（ui-design 审查轮补口径）：未选 blank-circle / 已选 marked
function chipLeadingIcon(id) {
  if (!multiSelect.value) return 'mdi-tag'
  return isSelected(id) ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-circle'
}

function toggleMultiSelect() {
  multiSelect.value = !multiSelect.value
  if (!multiSelect.value) selectedIds.value = []
}

// 「取消」/操作条取消：清选中回普通态，零请求
function exitMultiSelect() {
  multiSelect.value = false
  selectedIds.value = []
}

// 多选态下点 chip 主体切换选中；普通态零动作（删除仍走 append ✕）
function onChipClick(tag) {
  if (!multiSelect.value) return
  const idx = selectedIds.value.indexOf(tag.id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(tag.id)
}

// 清空流（任务 5.2）：入口只开确认弹窗，取消零请求零副作用
function confirmClearAll() {
  if (total.value === 0) return
  showClearAllDialog.value = true
}

async function onConfirmClearAll() {
  clearing.value = true
  try {
    await categoriesStore.clearTags()
    await loadTags()
    await resetPaging()
    showClearAllDialog.value = false
  } catch {
    // Toast shown by store
  } finally {
    clearing.value = false
  }
}

// 多选流（任务 5.5）：删除前先弹确认，未经确认零请求
function confirmBatchDelete() {
  if (selectedIds.value.length === 0) return
  showBatchDeleteDialog.value = true
}

async function onConfirmBatchDelete() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  batchDeleting.value = true
  try {
    await categoriesStore.batchRemoveTags(ids)
    // 成功：回普通态 + 重查首屏（未选标签与其账单关联不受影响）
    selectedIds.value = []
    multiSelect.value = false
    showBatchDeleteDialog.value = false
    await loadTags()
    await resetPaging()
  } catch {
    // 失败（含后端整单 400）：保留选中态与多选模式可重试，toast 由 store 弹
  } finally {
    batchDeleting.value = false
  }
}

// 重查第 1 页：进入页面 / 新增 / 删除后调用（列表回到首屏）
async function resetPaging() {
  try {
    const res = await getTagsPaged({ page: 1, page_size: PAGE_SIZE })
    displayedTags.value = res.items || []
    total.value = res.total || 0
    page.value = 1
    pageExhausted.value = false
  } catch (e) {
    console.error('Load tags page error:', e)
  }
}

// 展开更多：追加下一页；失败时已显示列表不变（错误 toast 由请求拦截器统一弹）
async function loadMore() {
  loadingMore.value = true
  try {
    const res = await getTagsPaged({ page: page.value + 1, page_size: PAGE_SIZE })
    const items = res.items || []
    total.value = res.total || 0
    if (items.length === 0) {
      // 越界页（末页已前移）：不追加、不推进页码，隐藏按钮避免反复空请求
      pageExhausted.value = true
      return
    }
    displayedTags.value = [...displayedTags.value, ...items]
    page.value += 1
  } catch (e) {
    console.error('Load more tags error:', e)
  } finally {
    loadingMore.value = false
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
    await resetPaging()
  } catch {
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
      await resetPaging()
    } catch {
      // Toast shown by store
    }
  }
  showDeleteTagDialog.value = false
  deletingTag.value = null
}

async function loadTags() {
  try {
    await categoriesStore.fetchTags()
  } catch (e) {
    console.error('Load tags error:', e)
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
  await Promise.all([loadTags(), loadCategories(), resetPaging()])
})
</script>

<style scoped>
.settings-tags-page {
  padding-bottom: 20px;
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

/* 多选态选中 chip 的第二信号（除勾选图标外）：主题色描边提亮，不引入新色板 */
.tag-chip-selected {
  outline: 1px solid rgba(var(--v-theme-primary), 0.45);
  outline-offset: 1px;
}

/* 批量操作条进出对称动画（与账单页 batch-bar 同源：时长/缓动引用全站展开口径变量） */
.batch-bar-enter-active,
.batch-bar-leave-active {
  transition:
    transform var(--expand-duration) var(--expand-easing),
    opacity var(--expand-duration) var(--expand-easing);
}

.batch-bar-enter-from,
.batch-bar-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
