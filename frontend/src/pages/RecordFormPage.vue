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

    <!-- Page Header -->
    <div class="page-header mb-3">
      <div class="d-flex align-center">
        <v-btn icon variant="text" class="mr-2" @click="handleBack()">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <div>
          <h1 class="page-title">{{ isEdit ? '编辑账单' : '记一笔' }}</h1>
          <p class="page-subtitle">{{ isEdit ? '修改账单信息' : '记录你的每一笔收支' }}</p>
        </div>
      </div>
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
      <v-row dense>
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
        <div class="d-flex ga-2">
          <DatePickerPopover
            v-model="consumeDate"
            v-model:model-value-time="consumeTime"
            :show-time="true"
            label="消费日期"
            class="flex-grow-1"
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
import { ref, computed, onMounted, watch } from 'vue'
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

// Tag search state
const tagSearchQuery = ref('')
const tagSearchResults = ref([])
const tagSearching = ref(false)
let searchDebounceTimer = null

const currentCategories = computed(() =>
  categories.value.filter((c) => c.type === recordType.value)
)

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

watch(recordType, () => {
  const cats = currentCategories.value
  if (cats.length && !cats.find((c) => c.id === categoryId.value)) {
    categoryId.value = cats[0]?.id || null
  }
})

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

onMounted(async () => {
  try {
    const [cats, tpls] = await Promise.all([getCategories(), getQuickTemplates()])
    categories.value = cats
    templates.value = tpls || []

    const expenseCats = cats.filter((c) => c.type === 'expense')
    if (expenseCats.length) {
      categoryId.value = expenseCats[0].id
    }

    if (isEdit.value) {
      recordId.value = parseInt(route.params.id)
      const record = await getRecord(recordId.value)
      if (record) {
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
      }
    }
    // Save initial snapshot for dirty tracking
    initialSnapshot = takeSnapshot()
  } catch (e) {
    console.error('Form load error:', e)
  }
})
</script>

<style scoped>
.form-page {
  padding-bottom: 20px;
}

.page-header {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
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
