<template>
  <ExpandTransition v-model="showPicker" :origin="origin" :max-width="400">
    <template #activator="activatorProps">
      <div v-bind="activatorProps" @click="openPicker" class="d-flex align-center ga-2">
        <slot name="activator">
          <v-text-field
            :model-value="displayValue"
            :label="label"
            readonly
            hide-details
            variant="outlined"
            density="compact"
            prepend-inner-icon="mdi-calendar"
            class="flex-grow-1"
          />
        </slot>
        <!-- Time field: same row, right-aligned -->
        <v-text-field
          v-if="showTime"
          :model-value="selectedTime"
          readonly
          label="时间"
          hide-details
          variant="outlined"
          density="compact"
          prepend-inner-icon="mdi-clock-outline"
          class="time-field"
          @click.stop="openTimePicker"
        />
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

  <!-- Independent time picker dialog -->
  <v-dialog v-model="showTimePicker" max-width="340">
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
        <v-btn variant="text" @click="showTimePicker = false">取消</v-btn>
        <v-btn variant="tonal" color="primary" @click="confirmTime">确定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
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

function onDateSelected(date) {
  selectedDate.value = date
  emit('update:modelValue', date)
  showPicker.value = false
}

function openTimePicker() {
  pendingTime.value = selectedTime.value || '12:00'
  showTimePicker.value = true
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

.time-field {
  max-width: 140px;
}

.time-picker-card {
  border: none !important;
}
</style>
