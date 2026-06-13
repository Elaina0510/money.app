<template>
  <v-dialog :model-value="modelValue" max-width="480" @update:model-value="$emit('update:modelValue', $event)">
    <v-card class="pa-4" rounded="xl">
      <v-card-title class="text-h6 pa-0 mb-2">CSV 导入映射</v-card-title>

      <div class="text-caption text-grey mb-4">
        格式：{{ formatLabel }} · 共 {{ previewData?.row_count || 0 }} 条记录
      </div>

      <!-- Category Mapping -->
      <div class="mb-4">
        <div class="text-subtitle-2 font-weight-bold mb-2">分类映射</div>
        <div v-for="catName in (previewData?.categories_in_file || [])" :key="catName" class="mb-2">
          <div class="d-flex align-center">
            <span class="text-body-2 mr-2" style="min-width: 80px">{{ catName }}</span>
            <v-icon size="small" class="mr-2">mdi-arrow-right</v-icon>
            <v-select
              :model-value="getCategoryMapping(catName)"
              :items="categoryOptions"
              item-title="label"
              item-value="value"
              density="compact"
              hide-details
              variant="outlined"
              @update:model-value="setCategoryMapping(catName, $event)"
            />
          </div>
        </div>
      </div>

      <!-- Tag Mapping -->
      <div v-if="(previewData?.tags_in_file || []).length > 0" class="mb-4">
        <div class="text-subtitle-2 font-weight-bold mb-2">标签映射</div>
        <div v-for="tagName in (previewData?.tags_in_file || [])" :key="tagName" class="mb-2">
          <div class="d-flex align-center">
            <span class="text-body-2 mr-2" style="min-width: 80px">{{ tagName }}</span>
            <v-icon size="small" class="mr-2">mdi-arrow-right</v-icon>
            <v-select
              :model-value="getTagMapping(tagName)"
              :items="tagOptions"
              item-title="label"
              item-value="value"
              density="compact"
              hide-details
              variant="outlined"
              @update:model-value="setTagMapping(tagName, $event)"
            />
          </div>
        </div>
      </div>

      <!-- Unmapped count -->
      <div class="text-caption text-grey mb-4">
        <span v-if="unmappedCount > 0" class="text-error">
          未映射：{{ unmappedCount }} 项
        </span>
        <span v-else class="text-success">全部已映射</span>
      </div>

      <!-- Actions -->
      <div class="d-flex justify-end ga-2">
        <v-btn variant="text" @click="$emit('update:modelValue', false)">取消</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="unmappedCount > 0"
          @click="handleConfirm"
        >
          确认导入
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  previewData: Object,
  categories: Array,
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const categoryMapping = ref({})
const tagMapping = ref({})

const formatLabel = computed(() => {
  if (props.previewData?.format === 'native') return '本系统格式'
  if (props.previewData?.format === 'cashew') return 'Cashew 格式'
  return '未知格式'
})

const categoryOptions = computed(() => {
  const options = [{ label: '— 跳过 —', value: null }]
  for (const cat of (props.categories || [])) {
    options.push({ label: `${cat.name} (${cat.type === 'expense' ? '支出' : '收入'})`, value: cat.id })
  }
  options.push({ label: '+ 新建分类', value: 'create' })
  return options
})

const tagOptions = computed(() => {
  const options = [{ label: '— 跳过 —', value: null }]
  for (const cat of (props.categories || [])) {
    options.push({ label: `新建于「${cat.name}」`, value: cat.id })
  }
  return options
})

const unmappedCount = computed(() => {
  let count = 0
  for (const catName of (props.previewData?.categories_in_file || [])) {
    const mapping = categoryMapping.value[catName]
    if (!mapping || (!mapping.target_id && mapping.action !== 'create')) {
      count++
    }
  }
  return count
})

function getCategoryMapping(catName) {
  const m = categoryMapping.value[catName]
  if (!m) return null
  if (m.action === 'create') return 'create'
  return m.target_id
}

function setCategoryMapping(catName, value) {
  if (value === null) {
    delete categoryMapping.value[catName]
  } else if (value === 'create') {
    categoryMapping.value[catName] = { action: 'create', type: 'expense' }
  } else {
    categoryMapping.value[catName] = { action: 'map', target_id: value }
  }
}

function getTagMapping(tagName) {
  const m = tagMapping.value[tagName]
  if (!m) return null
  if (m.action === 'create') return m.category_id
  return m.target_id || null
}

function setTagMapping(tagName, value) {
  if (value === null) {
    delete tagMapping.value[tagName]
  } else {
    // value is a category_id, use action='create' to create tag under that category
    tagMapping.value[tagName] = { action: 'create', category_id: value }
  }
}

function handleConfirm() {
  emit('confirm', {
    category_mapping: { ...categoryMapping.value },
    tag_mapping: { ...tagMapping.value },
  })
}

// Auto-match categories by name
watch(() => props.previewData, (data) => {
  if (!data) return
  const cats = props.categories || []
  for (const catName of (data.categories_in_file || [])) {
    const match = cats.find((c) => c.name === catName)
    if (match) {
      categoryMapping.value[catName] = { action: 'map', target_id: match.id }
    }
  }
}, { immediate: true })
</script>
