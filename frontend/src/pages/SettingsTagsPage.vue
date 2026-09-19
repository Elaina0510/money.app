<template>
  <div class="settings-tags-page">
    <!-- Header: back + 新增 -->
    <div class="d-flex align-center mb-3">
      <v-btn icon variant="text" size="small" class="mr-2" @click="$router.back()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <p class="text-caption text-grey mb-0">管理标签，点击标签右侧 × 可删除</p>
      </div>
      <v-btn size="small" color="primary" variant="tonal" @click="showTagDialog = true">
        <v-icon start size="small">mdi-plus</v-icon>
        新增
      </v-btn>
    </div>

    <!-- 主体内容统一卡片图层（M4）：chip 云不再直贴页面背景 -->
    <div class="page-card">
      <div v-if="tags.length === 0" class="text-center pa-4 text-grey text-caption">暂无标签</div>

      <div v-else class="d-flex flex-wrap ga-1">
        <v-chip v-for="tag in tags" :key="tag.id" size="small" variant="tonal" class="mb-1">
          <v-icon start size="x-small">mdi-tag</v-icon>
          {{ tag.name }}
          <template v-slot:append>
            <v-icon size="x-small" class="ml-1 tag-delete-icon" @click.stop="confirmDeleteTag(tag)">
              mdi-close
            </v-icon>
          </template>
        </v-chip>
      </div>
    </div>

    <!-- Tag Dialog -->
    <v-dialog v-model="showTagDialog" max-width="360" transition="dialog-bottom-transition">
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
import { ref, reactive, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCategoriesStore } from '@/stores/useCategoriesStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const categoriesStore = useCategoriesStore()

// 数据全部走共享 store：tags 直读、categories 供弹窗下拉
const { tags, categories } = storeToRefs(categoriesStore)

// Tag CRUD
const showTagDialog = ref(false)
const savingTag = ref(false)

const tagForm = reactive({ name: '', category_id: null })

// Delete tag
const showDeleteTagDialog = ref(false)
const deletingTag = ref(null)

async function saveTag() {
  if (!tagForm.name.trim() || !tagForm.category_id) return
  savingTag.value = true
  try {
    await categoriesStore.addTag({ name: tagForm.name.trim(), category_id: tagForm.category_id })
    showTagDialog.value = false
    tagForm.name = ''
    tagForm.category_id = null
    await loadTags()
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
  await Promise.all([loadTags(), loadCategories()])
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
</style>
