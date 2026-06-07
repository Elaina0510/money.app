<template>
  <v-dialog v-model="show" :width="width" :max-width="maxWidth">
    <template v-slot:activator="{ props: activatorProps }">
      <slot name="activator" v-bind="activatorProps" />
    </template>
    <div ref="contentRef" class="expand-content">
      <slot />
    </div>
  </v-dialog>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  origin: {
    type: Object,
    default: () => ({ x: 0, y: 0 }),
  },
  duration: {
    type: Number,
    default: 250,
  },
  width: {
    type: [String, Number],
    default: 'auto',
  },
  maxWidth: {
    type: [String, Number],
    default: 400,
  },
})

const emit = defineEmits(['update:modelValue'])

const show = ref(props.modelValue)
const contentRef = ref(null)

watch(
  () => props.modelValue,
  (val) => {
    show.value = val
  }
)

watch(show, (val) => {
  emit('update:modelValue', val)
  if (val) {
    nextTick(() => {
      applyExpandAnimation()
    })
  }
})

function calcOrigin(clickX, clickY) {
  if (!contentRef.value) return 'center center'

  const rect = contentRef.value.getBoundingClientRect()
  const x = ((clickX - rect.left) / rect.width) * 100
  const y = ((clickY - rect.top) / rect.height) * 100

  return `${x}% ${y}%`
}

function applyExpandAnimation() {
  if (!contentRef.value) return

  const el = contentRef.value
  const origin = calcOrigin(props.origin.x, props.origin.y)

  el.style.transformOrigin = origin
  el.style.transform = 'scale(0)'
  el.style.opacity = '0'
  el.style.transition = 'none'

  // Force reflow
  el.offsetHeight

  el.style.transition = `transform ${props.duration}ms ease, opacity ${props.duration}ms ease`
  el.style.transform = 'scale(1)'
  el.style.opacity = '1'
}
</script>

<style scoped>
.expand-content {
  transform-origin: center center;
}
</style>
