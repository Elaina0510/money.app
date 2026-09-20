<template>
  <div class="date-time-fields w-100">
    <!-- 第一行：日期（占满行宽），圆形展开日历弹层 -->
    <ExpandTransition
      :model-value="showPicker"
      :origin="origin"
      :max-width="400"
      @update:model-value="closeAndCommit"
    >
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
        <!-- D6：内置 header（「输入日期」文本行）隐藏，改自绘只读展示行，随每次点选即时更新 -->
        <div class="selected-date-display">{{ pickedDisplay }}</div>
        <v-card-text class="pa-0">
          <v-date-picker
            :model-value="picked"
            :show-adjacent-months="false"
            color="primary"
            width="100%"
            @update:model-value="onDateSelected"
          />
        </v-card-text>
        <v-card-actions class="pa-3 pt-1">
          <v-spacer />
          <v-btn variant="tonal" color="primary" @click="closePicker">完成</v-btn>
        </v-card-actions>
      </v-card>
    </ExpandTransition>

    <!-- 第二行：时间（仅 showTime），点击位置圆形展开的表盘时钟；保持「取消/确定」语义（2.6） -->
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
import dayjs from 'dayjs'
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
// 选后不关：点选的日期先存内部态 picked，只在弹窗真正关闭时回写一次
const picked = ref(props.modelValue)
const selectedTime = ref(props.modelValueTime)

// Time picker state
const showTimePicker = ref(false)
const timeOrigin = ref({ x: 0, y: 0 })
const pendingTime = ref('')

const displayValue = computed(() => {
  if (!props.modelValue) return ''
  return props.modelValue
})

// D6：只读实时展示行——已选「YYYY年M月D日」/未选「请选择日期」
const pickedDisplay = computed(() => {
  if (!picked.value) return '请选择日期'
  return dayjs(picked.value).format('YYYY年M月D日')
})

function openPicker(event) {
  origin.value = {
    x: event.clientX,
    y: event.clientY,
  }
  // 每次打开与外部值同步（含收起动画进行中重开的 cancel-collapse 场景）
  picked.value = props.modelValue
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
  // 仅归一后存内部态：不即时 emit、不关闭（展示行随 computed 即时跟新）
  picked.value = toDateString(date)
}

// 「完成」按钮：只请求关闭；真正回写统一发生在 dialog 收起动画播完之后
function closePicker() {
  showPicker.value = false
}

// 统一回写出口：「完成」/遮罩点击/ESC 三路径都经 ExpandTransition 的
// `update:modelValue false`（收起动画播完、dialog 真正关闭）走到这里，一次关闭最多回写一次
function closeAndCommit(val) {
  showPicker.value = val
  if (val) return
  const next = picked.value ?? ''
  if (next !== props.modelValue) {
    emit('update:modelValue', next)
  }
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
/* D6：隐藏内置 header（该行为「输入日期」文本区、非可编辑输入框），由上方自绘展示行取代 */
:deep(.v-date-picker-header) {
  display: none;
}

.selected-date-display {
  padding: 12px 16px 8px;
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  color: rgb(var(--v-theme-on-surface));
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

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
