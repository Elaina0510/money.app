<template>
  <div class="form-page">
    <!-- Leave Confirmation Dialog -->
    <ConfirmDialog
      v-model="showLeaveDialog"
      title="未保存的更改"
      message="您有未保存的更改，确定要离开吗？"
      confirm-text="确定放弃"
      confirm-color="error"
      @confirm="confirmLeave"
      @cancel="cancelLeave"
    />

    <!-- Back Button -->
    <div class="mb-3">
      <v-btn icon variant="text" @click="handleBack()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
    </div>

    <!-- Type Toggle -->
    <div class="d-flex mb-4 ga-2">
      <v-btn
        :color="recordType === 'expense' ? '#FF6B6B' : ''"
        :variant="recordType === 'expense' ? 'flat' : 'outlined'"
        size="large"
        rounded="xl"
        class="type-btn expense-btn flex-grow-1"
        :class="{ 'active-expense': recordType === 'expense' }"
        @click="recordType = 'expense'"
      >
        <v-icon start>mdi-arrow-down</v-icon>
        支出
      </v-btn>
      <v-btn
        :color="recordType === 'income' ? '#20C997' : ''"
        :variant="recordType === 'income' ? 'flat' : 'outlined'"
        size="large"
        rounded="xl"
        class="type-btn income-btn flex-grow-1"
        :class="{ 'active-income': recordType === 'income' }"
        @click="recordType = 'income'"
      >
        <v-icon start>mdi-arrow-up</v-icon>
        收入
      </v-btn>
    </div>

    <!-- Amount Input -->
    <v-card class="pa-5 mb-4 amount-card" rounded="xl">
      <div class="text-caption text-grey mb-1 text-center">金额</div>
      <v-text-field
        v-model="amount"
        placeholder="0.00"
        type="number"
        step="0.01"
        min="0.01"
        class="amount-input"
        hide-details
        variant="plain"
        autofocus
      />
    </v-card>

    <!-- Category Grid Selector -->
    <v-card class="pa-4 mb-4" rounded="xl">
      <div class="text-subtitle-2 font-weight-bold mb-3">选择分类</div>

      <!-- v1.4.3-boot M2 三态（需求 2.2/2.3）：加载 → 错误（可重试）→ 空（引导）→ 正常九宫格；
           错误态分支必须在空态之前，两者永不同时出现 -->
      <div v-if="categoriesLoading" class="category-state pa-6 text-center">
        <v-progress-circular indeterminate color="primary" size="28" />
      </div>

      <div v-else-if="categoriesError" class="category-state pa-6 text-center">
        <v-icon size="40" color="error" class="mb-2">mdi-alert-circle-outline</v-icon>
        <div class="text-body-2 mb-3">分类加载失败，请检查网络后重试</div>
        <v-btn variant="tonal" color="primary" size="small" @click="retryLoadCategories">重试</v-btn>
      </div>

      <div v-else-if="categories.length === 0" class="category-state pa-6 text-center">
        <v-icon size="40" color="grey" class="mb-2">mdi-shape-outline</v-icon>
        <div class="text-body-2 text-grey">暂无分类，请先到 设置 → 分类管理 添加分类</div>
      </div>

      <v-row v-else dense>
        <v-col v-for="cat in currentCategories" :key="cat.id" cols="3" class="text-center">
          <v-btn
            :color="categoryId === cat.id ? (recordType === 'expense' ? '#FF6B6B' : '#20C997') : ''"
            :variant="categoryId === cat.id ? 'flat' : 'text'"
            size="small"
            class="category-chip"
            :class="{ 'active-category': categoryId === cat.id }"
            block
            @click="categoryId = cat.id"
          >
            <div class="d-flex flex-column align-center pa-1">
              <v-avatar
                size="40"
                :color="categoryId === cat.id ? 'white' : 'rgba(0,0,0,0.04)'"
                class="mb-1"
              >
                <v-icon
                  :color="
                    categoryId === cat.id
                      ? recordType === 'expense'
                        ? '#FF6B6B'
                        : '#20C997'
                      : 'rgba(0,0,0,0.5)'
                  "
                  size="20"
                >
                  {{ cat.icon || 'mdi-circle' }}
                </v-icon>
              </v-avatar>
              <span
                class="text-caption mt-1"
                :class="categoryId === cat.id ? 'font-weight-bold' : ''"
              >
                {{ cat.name }}
              </span>
            </div>
          </v-btn>
        </v-col>
      </v-row>
    </v-card>

    <!-- Consume Time (Date + Time) & Tag Selector & Note -->
    <v-card class="pa-4 mb-4" rounded="xl">
      <!-- Consume Time -->
      <div class="mb-3">
        <div class="text-caption text-grey mb-1">消费时间</div>
        <div>
          <DatePickerPopover
            v-model="consumeDate"
            v-model:model-value-time="consumeTime"
            :show-time="true"
            label="消费日期"
          />
        </div>
      </div>
      <v-divider class="mb-3" />

      <!-- Tag Input (Search Autocomplete) -->
      <div class="mb-3">
        <div class="text-caption text-grey mb-1">标签</div>
        <v-autocomplete
          v-model="selectedTagId"
          v-model:search="tagSearchQuery"
          transition="fab-transition"
          :items="tagSearchResults"
          item-title="name"
          item-value="id"
          placeholder="输入标签名称搜索"
          hide-details
          variant="outlined"
          density="compact"
          clearable
          no-filter
          :loading="tagSearching"
          @update:search="onTagSearch"
          @update:model-value="onTagSelected"
          @keydown.enter="onCreateTagFromSearch"
        >
          <template v-slot:no-data>
            <v-list-item v-if="tagSearchQuery && tagSearchQuery.length >= 1">
              <v-list-item-title class="text-caption text-grey">
                无匹配标签，按回车创建「{{ tagSearchQuery }}」
              </v-list-item-title>
            </v-list-item>
          </template>
        </v-autocomplete>
      </div>
      <v-divider class="mb-3" />

      <!-- Note -->
      <div>
        <div class="text-caption text-grey mb-1">备注（可选）</div>
        <v-textarea
          v-model="note"
          placeholder="添加备注..."
          hide-details
          variant="outlined"
          density="compact"
          rows="2"
          auto-grow
        />
      </div>
    </v-card>

    <!-- Quick Templates -->
    <v-card v-if="templates.length" class="pa-4 mb-4" rounded="xl">
      <div class="text-subtitle-2 font-weight-bold mb-2">快速记账</div>
      <div class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="tpl in templates.slice(0, 5)"
          :key="tpl.id"
          size="small"
          variant="tonal"
          @click="fillTemplate(tpl)"
          class="template-chip"
        >
          <v-avatar :color="tpl.type === 'expense' ? '#FFE8E8' : '#E8FFF3'" size="20" class="mr-1">
            <v-icon size="12" :color="tpl.type === 'expense' ? '#FF6B6B' : '#20C997'">
              {{ tpl.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
            </v-icon>
          </v-avatar>
          {{ tpl.tag_name || tpl.category_name }} · ¥{{ tpl.amount }}
        </v-chip>
      </div>
    </v-card>

    <!-- Submit Button -->
    <v-btn
      :color="recordType === 'expense' ? '#FF6B6B' : '#20C997'"
      size="x-large"
      block
      rounded="xl"
      :disabled="!canSubmit"
      :loading="submitting"
      @click="submit"
      class="submit-btn"
    >
      <v-icon start size="22">mdi-check</v-icon>
      {{ isEdit ? '更新账单' : '保存账单' }}
    </v-btn>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { createRecord, updateRecord, getRecord, getQuickTemplates } from '@/api/records'
import { getCategories } from '@/api/categories'
import { searchTags, createTag as createTagData } from '@/api/tags'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DatePickerPopover from '@/components/common/DatePickerPopover.vue'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

// Leave guard state
const isDirty = ref(false)
const showLeaveDialog = ref(false)
const pendingNavigation = ref(null)
let initialSnapshot = ''

const isEdit = computed(() => !!route.params.id)

const recordType = ref('expense')
const amount = ref('')
const categoryId = ref(null)
const consumeDate = ref(dayjs().format('YYYY-MM-DD'))
const consumeTime = ref(dayjs().format('HH:mm'))
const selectedTagId = ref(null)
const selectedTagName = ref('')
const note = ref('')
const submitting = ref(false)
const categories = ref([])
const templates = ref([])
const recordId = ref(null)
// v1.4.3-boot M2：分类加载独立状态（loading 初值 true——首帧不闪空态；error 驱动重试入口）
const categoriesLoading = ref(true)
const categoriesError = ref(false)

// Tag search state
const tagSearchQuery = ref('')
const tagSearchResults = ref([])
const tagSearching = ref(false)
let searchDebounceTimer = null

// v1.4.3 M8：分类收支共用，全量单列表即记账可选分类（不再按交易 type 过滤）；
// 九宫格图标/选中色继续按**交易** type 着色（records.type 语义不变）
const OTHER_CATEGORY_NAME = '其他'

const currentCategories = computed(() => categories.value)

const canSubmit = computed(() => {
  return parseFloat(amount.value) > 0 && categoryId.value !== null
})

// Leave guard functions
function takeSnapshot() {
  return JSON.stringify({
    recordType: recordType.value,
    amount: amount.value,
    categoryId: categoryId.value,
    consumeDate: consumeDate.value,
    consumeTime: consumeTime.value,
    selectedTagId: selectedTagId.value,
    selectedTagName: selectedTagName.value,
    note: note.value,
  })
}

function handleBack() {
  if (isDirty.value) {
    showLeaveDialog.value = true
  } else {
    router.back()
  }
}

function confirmLeave() {
  isDirty.value = false
  showLeaveDialog.value = false
  if (pendingNavigation.value) {
    pendingNavigation.value()
  } else {
    router.back()
  }
}

function cancelLeave() {
  showLeaveDialog.value = false
  pendingNavigation.value = null
}

// Leave guard - intercept navigation when form is dirty
try {
  onBeforeRouteLeave((to, from, next) => {
    if (isDirty.value) {
      showLeaveDialog.value = true
      pendingNavigation.value = () => next()
    } else {
      next()
    }
  })
} catch {
  // Ignore if not in router context (e.g., during tests)
}

async function onTagSearch(query) {
  if (!query || query.length < 1) {
    // When search clears, retain the currently selected tag so v-autocomplete displays its name
    if (selectedTagId.value) {
      const currentItem = tagSearchResults.value.find((t) => t.id === selectedTagId.value)
      tagSearchResults.value = currentItem ? [currentItem] : []
    } else {
      tagSearchResults.value = []
    }
    return
  }
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(async () => {
    tagSearching.value = true
    try {
      const results = await searchTags(query)
      tagSearchResults.value = results || []
    } catch (e) {
      console.error('Tag search error:', e)
    } finally {
      tagSearching.value = false
    }
  }, 200)
}

function onTagSelected(tagId) {
  if (!tagId) {
    selectedTagId.value = null
    selectedTagName.value = ''
    return
  }
  const tag = tagSearchResults.value.find((t) => t.id === tagId)
  if (tag) {
    selectedTagName.value = tag.name
    if (tag.category_id) {
      categoryId.value = tag.category_id
    }
  }
  selectedTagId.value = tagId
}

async function onCreateTagFromSearch() {
  if (!tagSearchQuery.value || tagSearchQuery.value.length < 1) return
  // Only select if exact match found
  const exactMatch = tagSearchResults.value.find((t) => t.name === tagSearchQuery.value)
  if (exactMatch) {
    selectedTagId.value = exactMatch.id
    selectedTagName.value = exactMatch.name
    if (exactMatch.category_id) {
      categoryId.value = exactMatch.category_id
    }
    return
  }
  // New tag: confirm on UI only, don't save to DB yet
  selectedTagName.value = tagSearchQuery.value.trim()
  // Add as temp item so v-autocomplete can display the name
  const tempTag = {
    id: -1, // temp ID, not saved
    name: selectedTagName.value,
    category_id: categoryId.value,
  }
  tagSearchResults.value = [tempTag]
  selectedTagId.value = -1
}

function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  consumeDate.value = dayjs().format('YYYY-MM-DD')
  consumeTime.value = dayjs().format('HH:mm')
  selectedTagId.value = tpl.tag_id || tpl.tag?.id || null
  selectedTagName.value = tpl.tag_name || tpl.tag?.name || ''
  tagSearchQuery.value = selectedTagName.value
  // Seed tagSearchResults so v-autocomplete can display the tag name immediately
  if (selectedTagId.value && selectedTagName.value) {
    tagSearchResults.value = [{ id: selectedTagId.value, name: selectedTagName.value }]
  }
  note.value = ''
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    // If tag name is entered but no matching tag exists (or temp ID), create it first
    let tagId = selectedTagId.value
    if (selectedTagName.value && (!tagId || tagId === -1)) {
      const newTag = await createTagData({
        name: selectedTagName.value.trim(),
        category_id: categoryId.value,
      })
      tagId = newTag.id
    }

    const data = {
      amount: parseFloat(amount.value),
      type: recordType.value,
      category_id: categoryId.value,
      consume_time: `${consumeDate.value} ${consumeTime.value}`,
      tag_id: tagId || null,
      note: note.value || null,
    }
    if (isEdit.value) {
      await updateRecord(recordId.value, data)
      appStore.showToast('账单已更新')
    } else {
      await createRecord(data)
      appStore.showToast('记账成功')
    }
    isDirty.value = false
    router.push('/')
  } catch {
    // Toast already shown by store
  } finally {
    submitting.value = false
  }
}

// v1.4.3 M8：切换支出/收入不再改变可选分类集合（全量单列表），
// 原「选中项出组即重置为组内首项」的 watch(recordType) 已随之删除

// Watch form fields for dirty state
watch(
  [recordType, amount, categoryId, consumeDate, consumeTime, selectedTagId, selectedTagName, note],
  () => {
    if (initialSnapshot) {
      isDirty.value = takeSnapshot() !== initialSnapshot
    }
  },
  { deep: true }
)

// ── v1.4.3-boot M2 加载解耦（需求 2.2 / 设计 §2.2.1）─────────────────────────
// 三个加载器各自吞异常，任何一路失败都不再牵连其他两路（旧 Promise.all 连坐已废）

async function loadCategories() {
  categoriesLoading.value = true
  categoriesError.value = false
  try {
    const cats = await getCategories()
    categories.value = cats || []
    // M8：默认分类取全列表首个非「其他」项（「其他」是末尾兜底位，不做默认选中）。
    // 守卫写在**默认选中时刻**（非 onMounted 末尾）：编辑回填可能先于分类到达，
    // 此时 categoryId 已有值，不得被默认补选覆盖（两序皆收敛到正确终态）。
    if (categoryId.value === null) {
      const defaultCat =
        categories.value.find((c) => c.name !== OTHER_CATEGORY_NAME) || categories.value[0]
      if (defaultCat) {
        categoryId.value = defaultCat.id
      }
    }
  } catch (e) {
    console.error('Categories load error:', e)
    categories.value = []
    categoriesError.value = true // 可见错误态 + 重试入口，不再静默留白（需求 2.2）
  } finally {
    categoriesLoading.value = false
  }
}

async function loadTemplates() {
  try {
    templates.value = (await getQuickTemplates()) || []
  } catch (e) {
    // 模板缺失非阻断信息：只清空（模板卡 v-if="templates.length" 自然隐藏），静默降级
    console.error('Templates load error:', e)
    templates.value = []
  }
}

async function loadRecordForEdit() {
  try {
    recordId.value = parseInt(route.params.id)
    const record = await getRecord(recordId.value)
    if (!record) return
    recordType.value = record.type
    amount.value = String(record.amount)
    categoryId.value = record.category_id
    if (record.consume_time) {
      consumeDate.value = record.consume_time.substring(0, 10)
      consumeTime.value = record.consume_time.substring(11, 16)
    }
    if (record.tag) {
      selectedTagId.value = record.tag.id
      selectedTagName.value = record.tag.name
      tagSearchQuery.value = record.tag.name
      // Seed tagSearchResults so v-autocomplete displays the tag name immediately
      tagSearchResults.value = [{ id: record.tag.id, name: record.tag.name }]
    }
    note.value = record.note || ''
  } catch (e) {
    // 失败只提示不空白：表单保持新建态可供用户自行补录，分类与快照均已不受影响
    console.error('Record load error:', e)
    appStore.showToast('账单加载失败', 'error')
  }
}

// 错误态「重试」入口：成功即撤错误态，并把系统补选的默认分类并入基线——
// isDirty 不因重试翻真（与「加载完成即定快照」的既有语义同源）
async function retryLoadCategories() {
  await loadCategories()
  if (!categoriesError.value) {
    initialSnapshot = takeSnapshot()
    await nextTick() // 等 dirty watch 落定后按新基线回算
    isDirty.value = takeSnapshot() !== initialSnapshot
  }
}

onMounted(async () => {
  // v1.4.3-boot M2：三 loader 互不牵连（需求 2.2「加载解耦」）——
  // 旧实现单 try + Promise.all 让模板接口 500 连坐掉分类赋值，九宫格恒久空白且无任何提示。
  const tasks = [loadCategories(), loadTemplates()]
  if (isEdit.value) tasks.push(loadRecordForEdit())
  await Promise.allSettled(tasks)
  // 快照恒定落定：dirty 追踪不再被任一加载失败废掉（消解旧 :482 的第三处连坐）
  initialSnapshot = takeSnapshot()
})
</script>

<style scoped>
.form-page {
  padding-bottom: 20px;
}

.type-btn {
  height: 48px !important;
  font-weight: 600;
}

.active-expense {
  color: white !important;
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
}

.active-income {
  color: white !important;
  box-shadow: 0 2px 8px rgba(32, 201, 151, 0.3);
}

.amount-card {
  background: rgba(var(--v-theme-primary), 0.03) !important;
}

.amount-input :deep(input) {
  font-size: 2.5rem !important;
  font-weight: 700 !important;
  text-align: center;
  height: 60px;
}

/* v1.4.3-boot M2 分类卡三态（加载/错误/空）：纯居中排布，竖屏与宽屏一致；
   文字不写死色值，随主题继承，明暗两模式均可读 */
.category-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 132px;
}

.category-chip {
  height: auto !important;
  padding: 6px 0 !important;
  border-radius: 12px !important;
  transition: all 0.15s ease;
}

.category-chip:hover {
  transform: scale(1.02);
}

.active-category {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.template-chip {
  margin: 2px;
}

.submit-btn {
  height: 52px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  color: white !important;
  margin-top: 8px;
}
</style>
