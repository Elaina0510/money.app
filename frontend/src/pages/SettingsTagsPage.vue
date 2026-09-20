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
      <div v-if="displayedTags.length === 0" class="text-center pa-4 text-grey text-caption">
        暂无标签
      </div>

      <!-- 单一区块（M6 疏朗化口径）：section-block / section-title 类名定义在 global.scss，
           本页只挂用（与分类页 M8 落地的单块写法同款） -->
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">全部标签</div>

        <div v-if="displayedTags.length" class="d-flex flex-wrap ga-1">
          <v-chip v-for="tag in displayedTags" :key="tag.id" size="small" variant="tonal" class="mb-1">
            <v-icon start size="x-small">mdi-tag</v-icon>
            {{ tag.name }}
            <template v-slot:append>
              <v-icon size="x-small" class="ml-1 tag-delete-icon" @click.stop="confirmDeleteTag(tag)">
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
</style>
