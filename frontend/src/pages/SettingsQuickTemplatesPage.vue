<template>
  <div class="settings-quick-templates-page">
    <!-- Header: back + 新增 -->
    <div class="d-flex align-center mb-3">
      <v-btn icon variant="text" size="small" class="mr-2" @click="$router.back()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <p class="text-caption text-grey mb-0">常用标签与金额，记一笔时快捷使用</p>
      </div>
      <v-btn
        size="small"
        color="primary"
        variant="tonal"
        @click="showQuickTemplateDialog = true"
      >
        <v-icon start size="small">mdi-plus</v-icon>
        新增
      </v-btn>
    </div>

    <div v-if="quickTemplates.length === 0" class="text-center pa-4 text-grey text-caption">
      暂无快速记账模板
    </div>

    <v-list v-else density="compact" class="bg-transparent pa-0">
      <v-list-item
        v-for="tpl in quickTemplates"
        :key="(tpl.tag_id || '') + '-' + tpl.amount + '-' + tpl.source"
        class="quick-template-item"
      >
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
          :rules="[(v) => !!v || '请选择标签']"
          hide-details="auto"
          class="mb-3"
          variant="outlined"
        />
        <v-text-field
          v-model.number="quickTemplateForm.amount"
          label="金额 *"
          type="number"
          prefix="¥"
          :rules="[(v) => v > 0 || '请输入金额']"
          hide-details="auto"
          class="mb-3"
          variant="outlined"
        />
        <div class="d-flex justify-end ga-2">
          <v-btn variant="text" @click="showQuickTemplateDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingQuickTemplate" @click="saveQuickTemplate"
            >保存</v-btn
          >
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { getQuickTemplates, addQuickTemplate, deleteQuickTemplate } from '@/api/records'

const categoriesStore = useCategoriesStore()

// 弹窗「选择标签」下拉数据源（与迁移前同源）
const { tags } = storeToRefs(categoriesStore)

// Quick template state
const quickTemplates = ref([])
const showQuickTemplateDialog = ref(false)
const savingQuickTemplate = ref(false)
const quickTemplateForm = ref({ tag_id: null, amount: 0 })

async function loadQuickTemplates() {
  try {
    quickTemplates.value = (await getQuickTemplates()) || []
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

async function loadTags() {
  try {
    await categoriesStore.fetchTags()
  } catch (e) {
    console.error('Load tags error:', e)
  }
}

onMounted(async () => {
  await Promise.all([loadQuickTemplates(), loadTags()])
})
</script>

<style scoped>
.settings-quick-templates-page {
  padding-bottom: 20px;
}
</style>
