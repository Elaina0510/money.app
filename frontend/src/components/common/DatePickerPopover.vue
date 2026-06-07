<template>
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

      <div v-if="showTime" class="px-4 pb-4">
        <v-text-field
          v-model="selectedTime"
          type="time"
          label="时间"
          hide-details
          variant="outlined"
          density="compact"
          @update:model-value="onTimeSelected"
        />
      </div>
    </v-card>
  </ExpandTransition>
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
  if (!props.showTime) {
    showPicker.value = false
  }
}

function onTimeSelected(time) {
  selectedTime.value = time
  emit('update:modelValueTime', time)
}
</script>

<style scoped>
:deep(.v-date-picker) {
  border-radius: 16px;
}
</style>
