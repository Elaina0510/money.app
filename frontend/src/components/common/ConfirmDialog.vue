<template>
  <AppDialog v-model="show" max-width="360" persistent>
    <!-- M14（任务 6.1）：内部换壳为 AppDialog 原点展开，对外 props/emits 与全站确认弹窗行为不变 -->
    <v-card>
      <v-card-title class="text-h6 pb-2">{{ title }}</v-card-title>
      <v-card-text class="text-body-2 text-medium-emphasis">
        {{ message }}
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" color="grey" @click="cancel">
          取消
        </v-btn>
        <v-btn
          :color="confirmColor"
          variant="tonal"
          :loading="loading"
          @click="confirm"
        >
          {{ confirmText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </AppDialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import AppDialog from './AppDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '确定要执行此操作吗？' },
  confirmText: { type: String, default: '确定' },
  confirmColor: { type: String, default: 'error' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const show = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  show.value = val
})

watch(show, (val) => {
  emit('update:modelValue', val)
})

function confirm() {
  emit('confirm')
}

function cancel() {
  emit('cancel')
  show.value = false
}
</script>
