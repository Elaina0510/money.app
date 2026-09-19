<template>
  <div class="date-time-fields w-100">
    <!-- 第一行：日期（占满行宽），圆形展开日历弹层 -->
    <ExpandTransition v-model="showPicker" :origin="origin" :max-width="400">
      <template #activator="activatorProps">
        <div v-bind="activatorProps" @click="openPicker">
          <slot name="activator">
            <v-text-field
              :model-value="displayValue"
              :label="label"
              readonly
              hide-details
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-calendar"
              class="w-100"
            />
          </slot>
        </div>
      </template>

      <v-card rounded="xl">
        <v-card-text class="pa-0">
          <v-date-picker
            v-model="selectedDate"
            :show-adjacent-months="false"
            color="primary"
            width="100%"
            @update:model-value="onDateSelected"
          />
        </v-card-text>
      </v-card>
    </ExpandTransition>

    <!-- 第二行：时间（仅 showTime），点击位置圆形展开的表盘时钟 -->
    <ExpandTransition
      v-if="showTime"
      v-model="showTimePicker"
      :origin="timeOrigin"
      :max-width="360"
    >
      <template #activator="activatorProps">
        <div v-bind="activatorProps" @click="openTimePicker">
          <v-text-field
            :model-value="selectedTime"
            readonly
            label="时间"
            hide-details
            variant="outlined"
            density="compact"
            prepend-inner-icon="mdi-clock-outline"
            class="w-100"
          />
        </div>
      </template>

      <v-card rounded="xl" class="time-picker-card">
        <v-card-title class="text-subtitle-1 font-weight-bold pa-4 pb-2">
          选择时间
        </v-card-title>
        <v-card-text class="pa-4 pt-0 d-flex justify-center">
          <v-time-picker
            v-model="pendingTime"
            color="primary"
            format="24hr"
            width="280"
          />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="cancelTime">取消</v-btn>
          <v-btn variant="tonal" color="primary" @click="confirmTime">确定</v-btn>
        </v-card-actions>
      </v-card>
    </ExpandTransition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ExpandTransition from './ExpandTransition.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  modelValueTime: {
    type: String,
    default: '',
  },
  showTime: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: '选择日期',
  },
})

const emit = defineEmits(['update:modelValue', 'update:modelValueTime'])

const showPicker = ref(false)
const origin = ref({ x: 0, y: 0 })
const selectedDate = ref(props.modelValue)
const selectedTime = ref(props.modelValueTime)

// Time picker state
const showTimePicker = ref(false)
const timeOrigin = ref({ x: 0, y: 0 })
const pendingTime = ref('')

const displayValue = computed(() => {
  if (!props.modelValue) return ''
  return props.modelValue
})

function openPicker(event) {
  origin.value = {
    x: event.clientX,
    y: event.clientY,
  }
  showPicker.value = true
}

// Vuetify 3.12 的 v-date-picker 选中后回传 JS Date 对象；
// 直接透传会让 consume_time 拼成 "Tue Sep 15 2026…" 导致后端 422（表现为保存无反应）
function toDateString(d) {
  if (typeof d === 'string' || d == null) return d
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function onDateSelected(date) {
  const normalized = toDateString(date)
  selectedDate.value = normalized
  emit('update:modelValue', normalized)
  showPicker.value = false
}

function openTimePicker(event) {
  // 点击位置 → 圆形展开原点
  timeOrigin.value = {
    x: event.clientX,
    y: event.clientY,
  }
  pendingTime.value = selectedTime.value || '12:00'
  showTimePicker.value = true
}

function cancelTime() {
  // 仅关闭弹层，不回写 selectedTime
  showTimePicker.value = false
}

function confirmTime() {
  selectedTime.value = pendingTime.value
  emit('update:modelValueTime', pendingTime.value)
  showTimePicker.value = false
}
</script>

<style scoped>
:deep(.v-date-picker),
:deep(.v-time-picker) {
  border-radius: 16px;
}

.date-time-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.time-picker-card {
  border: none !important;
}
</style>
