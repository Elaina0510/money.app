<template>
  <v-dialog
    :model-value="show"
    :width="width"
    :max-width="maxWidth"
    @update:model-value="onDialogModelValue"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <slot name="activator" v-bind="activatorProps" />
    </template>
    <div ref="contentRef" class="expand-content">
      <slot />
    </div>
  </v-dialog>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'

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
let collapseTimer = null

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      // 程序化打开；若收起动画进行中则取消收起，直接回到展开态
      clearCollapseTimer()
      show.value = true
    } else if (show.value) {
      // 程序化关闭（确定/取消/选日）：先播圆形收起动画，播完再真正关闭 dialog
      applyCollapseAnimation()
    }
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

// 拦截 v-dialog 的用户交互关闭（遮罩点击 / ESC）：同样先播圆形收起动画再关闭
function onDialogModelValue(val) {
  if (!val) {
    if (show.value && !collapseTimer) {
      applyCollapseAnimation()
    }
  } else {
    clearCollapseTimer()
    show.value = true
  }
}

function clearCollapseTimer() {
  if (collapseTimer) {
    clearTimeout(collapseTimer)
    collapseTimer = null
  }
}

onBeforeUnmount(() => {
  clearCollapseTimer()
})

function calcOrigin(clickX, clickY) {
  if (!contentRef.value) return 'center center'

  const rect = contentRef.value.getBoundingClientRect()
  if (!rect.width || !rect.height) return 'center center'

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

// 圆形收起：收缩回同一展开原点，动画期间 dialog 留在 DOM 中，播完再关闭
function applyCollapseAnimation() {
  if (collapseTimer) return

  const el = contentRef.value
  if (!el) {
    show.value = false
    return
  }

  el.style.transformOrigin = calcOrigin(props.origin.x, props.origin.y)
  el.style.transition = `transform ${props.duration}ms ease, opacity ${props.duration}ms ease`
  el.style.transform = 'scale(0)'
  el.style.opacity = '0'

  collapseTimer = setTimeout(() => {
    collapseTimer = null
    show.value = false
  }, props.duration)
}
</script>

<style scoped>
.expand-content {
  transform-origin: center center;
}
</style>
