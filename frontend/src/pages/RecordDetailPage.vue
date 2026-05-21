<template>
  <div class="detail-page">
    <!-- Page Header -->
    <div class="page-header mb-3">
      <div class="d-flex align-center">
        <v-btn icon variant="text" class="mr-2" @click="router.back()">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <div>
          <h1 class="page-title">账单详情</h1>
          <p class="page-subtitle">查看完整账单信息</p>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center pa-8">
      <v-progress-circular indeterminate color="primary" size="32" />
    </div>

    <!-- Not Found -->
    <div v-else-if="!record" class="text-center pa-8">
      <v-icon size="56" color="grey-lighten-1" class="mb-3">mdi-file-search-outline</v-icon>
      <p class="text-grey">账单不存在</p>
    </div>

    <template v-else>
      <!-- Amount Hero -->
      <v-card class="pa-6 mb-4 amount-hero-card text-center" rounded="xl">
        <v-avatar
          :color="record.type === 'expense' ? '#FFE8E8' : '#E8FFF3'"
          size="64"
          class="mb-3"
        >
          <v-icon
            :color="record.type === 'expense' ? '#FF6B6B' : '#20C997'"
            size="32"
          >
            {{ record.type === 'expense' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
          </v-icon>
        </v-avatar>
        <div class="text-caption text-grey mb-1">{{ record.type === 'expense' ? '支出' : '收入' }}</div>
        <div
          class="amount-display font-weight-bold"
          :style="{ color: record.type === 'expense' ? '#FF6B6B' : '#20C997' }"
        >
          {{ record.type === 'expense' ? '-' : '+' }}{{ formatAmount(record.amount) }}
        </div>
      </v-card>

      <!-- Detail Info -->
      <v-card class="pa-4 mb-4" rounded="xl">
        <v-list class="bg-transparent pa-0">
          <!-- Category -->
          <v-list-item class="detail-item px-0">
            <template v-slot:prepend>
              <v-icon color="primary" class="mr-3">mdi-shape</v-icon>
            </template>
            <v-list-item-title class="text-caption text-grey">分类</v-list-item-title>
            <v-list-item-subtitle class="d-flex align-center mt-1">
              <v-avatar size="28" color="rgba(139, 126, 116, 0.15)" class="mr-2">
                <v-icon size="16" color="#8B7E74">{{ record.category_icon || 'mdi-circle' }}</v-icon>
              </v-avatar>
              {{ record.category_name || '未分类' }}
            </v-list-item-subtitle>
          </v-list-item>
          <v-divider class="my-2" />

          <!-- Tag -->
          <v-list-item class="detail-item px-0">
            <template v-slot:prepend>
              <v-icon color="primary" class="mr-3">mdi-tag</v-icon>
            </template>
            <v-list-item-title class="text-caption text-grey">标签</v-list-item-title>
            <v-list-item-subtitle class="mt-1">
              <span v-if="record.tag">{{ record.tag.name }}</span>
              <span v-else class="text-grey-lighten-1">未设置标签</span>
            </v-list-item-subtitle>
          </v-list-item>
          <v-divider class="my-2" />

          <!-- Time -->
          <v-list-item class="detail-item px-0">
            <template v-slot:prepend>
              <v-icon color="primary" class="mr-3">mdi-clock-outline</v-icon>
            </template>
            <v-list-item-title class="text-caption text-grey">消费时间</v-list-item-title>
            <v-list-item-subtitle class="mt-1">
              {{ record.consume_time || '未知' }}
            </v-list-item-subtitle>
          </v-list-item>
          <v-divider class="my-2" />

          <!-- Note -->
          <v-list-item class="detail-item px-0">
            <template v-slot:prepend>
              <v-icon color="primary" class="mr-3">mdi-text</v-icon>
            </template>
            <v-list-item-title class="text-caption text-grey">备注</v-list-item-title>
            <v-list-item-subtitle class="mt-1">
              <span v-if="record.note">{{ record.note }}</span>
              <span v-else class="text-grey-lighten-1">无备注</span>
            </v-list-item-subtitle>
          </v-list-item>
          <v-divider class="my-2" />

          <!-- Created/Updated -->
          <v-list-item class="detail-item px-0">
            <template v-slot:prepend>
              <v-icon color="primary" class="mr-3">mdi-information-outline</v-icon>
            </template>
            <v-list-item-title class="text-caption text-grey">创建时间</v-list-item-title>
            <v-list-item-subtitle class="mt-1">{{ record.created_at }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Action Buttons -->
      <div class="d-flex ga-3">
        <v-btn
          color="primary"
          variant="tonal"
          size="large"
          block
          rounded="xl"
          @click="goToEdit"
        >
          <v-icon start>mdi-pencil</v-icon>
          编辑
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          size="large"
          block
          rounded="xl"
          @click="showDeleteConfirm = true"
        >
          <v-icon start>mdi-delete</v-icon>
          删除
        </v-btn>
      </div>
    </template>

    <!-- Delete Confirm Dialog -->
    <ConfirmDialog
      v-model="showDeleteConfirm"
      title="删除账单"
      message="确定要删除这条记录吗？此操作不可撤销。"
      confirm-text="删除"
      confirm-color="error"
      @confirm="handleDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getRecord, deleteRecord } from '@/api/records'
import { formatAmount } from '@/utils/format'
import { useAppStore } from '@/stores/useAppStore'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const record = ref(null)
const loading = ref(true)
const showDeleteConfirm = ref(false)

async function loadRecord() {
  loading.value = true
  try {
    const id = parseInt(route.params.id)
    record.value = await getRecord(id)
  } catch (e) {
    console.error('Failed to load record:', e)
  } finally {
    loading.value = false
  }
}

function goToEdit() {
  if (record.value) {
    router.push(`/edit/${record.value.id}`)
  }
}

async function handleDelete() {
  try {
    await deleteRecord(record.value.id)
    appStore.showToast('账单已删除')
    router.push('/records')
  } catch (e) {
    // Toast handled by store
  }
}

onMounted(loadRecord)
</script>

<style scoped>
.detail-page {
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

.amount-hero-card {
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.amount-display {
  font-size: 36px;
  line-height: 1.2;
}

.detail-item {
  min-height: 48px;
}
</style>
