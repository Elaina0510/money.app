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

    <!-- 主体内容统一卡片图层（M4）：列表页面级透视写法随之清除 -->
    <div class="page-card">
      <div v-if="quickTemplates.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无快速记账模板
      </div>

      <!-- 单一区块（M6 疏朗化口径）：section-block / section-title 类名定义在 global.scss，
           本页只挂用；density 改回默认——行高由全局 min-height 48px + margin-block 4px 托底 -->
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">全部模板</div>

        <v-list v-if="quickTemplates.length" class="pa-0">
          <v-list-item
            v-for="tpl in quickTemplates"
            :key="`${tpl.source}-${tpl.tag_id}-${Math.round(Number(tpl.amount) * 100)}`"
            class="quick-template-item"
          >
            <template v-slot:prepend>
              <v-avatar
                size="32"
                :color="tpl.type === 'expense' ? '#FFE8E8' : '#E8FFF3'"
                class="mr-2"
              >
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
      </div>
    </div>

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

    <!-- Delete Template Confirm（M6：手动/自动均先确认，文案按来源区分） -->
    <ConfirmDialog
      v-model="showDeleteDialog"
      title="删除模板"
      :message="deleteMessage"
      :loading="deleting"
      confirm-text="删除"
      @confirm="handleDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import { useAppStore } from '@/stores/useAppStore'
import {
  getQuickTemplates,
  addQuickTemplate,
  deleteQuickTemplate,
  ignoreAutoQuickTemplate,
} from '@/api/records'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const categoriesStore = useCategoriesStore()
const appStore = useAppStore()

// 弹窗「选择标签」下拉数据源（与迁移前同源）
const { tags } = storeToRefs(categoriesStore)

// Quick template state
const quickTemplates = ref([])
const showQuickTemplateDialog = ref(false)
const savingQuickTemplate = ref(false)
const quickTemplateForm = ref({ tag_id: null, amount: 0 })

// 删除确认（M6）：手动/自动都先弹确认，自动项按签名忽略而非重拉刷新
const showDeleteDialog = ref(false)
const deletingTemplate = ref(null)
const deleting = ref(false)

const deleteMessage = computed(() => {
  const tpl = deletingTemplate.value
  if (!tpl) return ''
  return tpl.source === 'auto'
    ? `确定删除自动模板「${tpl.tag_name} · ¥${tpl.amount}」吗？该组合今后不再自动出现。`
    : `确定删除模板「${tpl.tag_name} · ¥${tpl.amount}」吗？`
})

async function loadQuickTemplates() {
  try {
    quickTemplates.value = (await getQuickTemplates()) || []
  } catch (e) {
    console.error('Load quick templates error:', e)
    quickTemplates.value = []
  }
}

// 点删除按钮只进确认弹窗（自动模板无 id，不再「不发请求只重拉」）
function removeQuickTemplate(tpl) {
  deletingTemplate.value = tpl
  showDeleteDialog.value = true
}

async function handleDelete() {
  const tpl = deletingTemplate.value
  if (!tpl) return
  deleting.value = true
  try {
    if (tpl.id) {
      // 手动模板：维持现有 DELETE /quick-templates/{id}
      await deleteQuickTemplate(tpl.id)
    } else {
      // 自动模板：按签名忽略（金额换算为分单位整数，与后端去重键同口径 D9）
      await ignoreAutoQuickTemplate({
        tag_id: tpl.tag_id,
        type: tpl.type,
        amount_cents: Math.round(Number(tpl.amount) * 100),
      })
    }
    // 本地即时移除 + 成功反馈，随后后台静默对齐（重排/聚合变化）
    quickTemplates.value = quickTemplates.value.filter((x) => x !== tpl)
    appStore.showToast('模板已删除')
    await loadQuickTemplates()
  } catch (e) {
    // 失败：本地未动过，列表保持原状
    console.error('Remove quick template error:', e)
    appStore.showToast('删除失败', 'error')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
    deletingTemplate.value = null
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
