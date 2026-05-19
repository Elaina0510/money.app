<template>
  <div class="form-page">
    <!-- Page Header -->
    <div class="page-header mb-3">
      <div class="d-flex align-center">
        <v-btn icon variant="text" class="mr-2" @click="router.back()">
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
        block
        size="large"
        rounded="xl"
        class="type-btn expense-btn"
        :class="{ 'active-expense': recordType === 'expense' }"
        @click="recordType = 'expense'"
      >
        <v-icon start>mdi-arrow-down</v-icon>
        支出
      </v-btn>
      <v-btn
        :color="recordType === 'income' ? '#20C997' : ''"
        :variant="recordType === 'income' ? 'flat' : 'outlined'"
        block
        size="large"
        rounded="xl"
        class="type-btn income-btn"
        :class="{ 'active-income': recordType === 'income' }"
        @click="recordType = 'income'"
      >
        <v-icon start>mdi-arrow-up</v-icon>
        收入
      </v-btn>
    </div>

    <!-- Amount Input - Big and Bold -->
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
        <v-col
          v-for="cat in currentCategories"
          :key="cat.id"
          cols="3"
          class="text-center"
        >
          <v-btn
            :color="categoryId === cat.id ? recordType === 'expense' ? '#FF6B6B' : '#20C997' : ''"
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
                  :color="categoryId === cat.id ? recordType === 'expense' ? '#FF6B6B' : '#20C997' : 'rgba(0,0,0,0.5)'"
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

    <!-- Date & Tags Row -->
    <v-card class="pa-4 mb-4" rounded="xl">
      <div class="mb-3">
        <div class="text-caption text-grey mb-1">日期</div>
        <v-text-field
          v-model="date"
          type="date"
          hide-details
          variant="plain"
          density="comfortable"
        />
      </div>
      <v-divider class="mb-3" />
      <div>
        <div class="text-caption text-grey mb-1">标签 / 备注</div>
        <v-text-field
          v-model="tagInput"
          placeholder="输入标签，按回车添加"
          hide-details
          variant="plain"
          density="comfortable"
          @keydown.enter.prevent="addTag"
        />
        <div v-if="tags.length" class="mt-2 d-flex flex-wrap">
          <v-chip
            v-for="(tag, i) in tags"
            :key="i"
            size="small"
            closable
            class="mr-1 mb-1"
            variant="tonal"
            @click:close="tags.splice(i, 1)"
          >
            {{ tag }}
          </v-chip>
        </div>
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
          <v-avatar
            :color="tpl.type === 'expense' ? '#FFE8E8' : '#E8FFF3'"
            size="20"
            class="mr-1"
          >
            <v-icon
              size="12"
              :color="tpl.type === 'expense' ? '#FF6B6B' : '#20C997'"
            >
              {{ tpl.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
            </v-icon>
          </v-avatar>
          {{ tpl.category_name }} · {{ formatAmount(tpl.amount) }}
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
import { useRouter, useRoute } from 'vue-router'
import { createRecord, updateRecord, getRecord, getQuickTemplates } from '@/api/records'
import { getCategories } from '@/api/categories'
import { useAppStore } from '@/stores/useAppStore'
import { formatAmount } from '@/utils/format'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const isEdit = computed(() => !!route.params.id)

const recordType = ref('expense')
const amount = ref('')
const categoryId = ref(null)
const date = ref(dayjs().format('YYYY-MM-DD'))
const tags = ref([])
const tagInput = ref('')
const submitting = ref(false)
const categories = ref([])
const templates = ref([])
const recordId = ref(null)

const currentCategories = computed(() =>
  categories.value.filter((c) => c.type === recordType.value)
)

const canSubmit = computed(() => {
  return parseFloat(amount.value) > 0 && categoryId.value !== null
})

function addTag() {
  const text = tagInput.value.trim()
  if (text && !tags.value.includes(text)) {
    tags.value.push(text)
  }
  tagInput.value = ''
}

function fillTemplate(tpl) {
  recordType.value = tpl.type
  amount.value = String(tpl.amount)
  categoryId.value = tpl.category_id
  tags.value = [...tpl.tags]
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const data = {
      amount: parseFloat(amount.value),
      type: recordType.value,
      category_id: categoryId.value,
      date: date.value,
      tags: tags.value,
    }
    if (isEdit.value) {
      await updateRecord(recordId.value, data)
      appStore.showToast('账单已更新')
    } else {
      await createRecord(data)
      appStore.showToast('记账成功')
    }
    router.push('/')
  } catch (e) {
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

onMounted(async () => {
  try {
    const [cats, tpls] = await Promise.all([
      getCategories(),
      getQuickTemplates(),
    ])
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
        date.value = record.date
        tags.value = [...(record.tags || [])]
      }
    }
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

.page-subtitle {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
  margin: 2px 0 0;
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
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
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
