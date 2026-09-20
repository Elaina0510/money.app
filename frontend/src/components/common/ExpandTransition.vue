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
import { useExpandAnimation } from '@/composables/useExpandAnimation'

/* v1.4.3 M14（任务 3.1）：内部机制已抽至 useExpandAnimation（单一实现源），
 * 本组件**对外 props / emits / 行为不变**（既有 ExpandTransition.test.js 全量保持是重构红线）。
 * 继续服务 DatePickerPopover（其 activator 本就传真实 click 坐标）。
 * duration 默认值沿用对外 API 的 250（旧口径被红线用例锁定），
 * 全站 220ms 统一口径由 --expand-duration / EXPAND_DURATION 承载（AppDialog 走该默认）。 */
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

const {
  applyExpand,
  applyCollapse,
  clearCollapseTimer,
  isCollapsing,
  calcOrigin,
} = useExpandAnimation(contentRef, {
  origin: () => props.origin,
  duration: () => props.duration,
})

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
      // 幂等展开：元素停在 scale(0)（收起中途重开）时重新播展开，已在展开态则跳过
      const el = contentRef.value
      if (el && el.style.transform === 'scale(1)' && el.style.opacity === '1') return
      applyExpandAnimation()
    })
  }
})

// 拦截 v-dialog 的用户交互关闭（遮罩点击 / ESC）：同样先播圆形收起动画再关闭
function onDialogModelValue(val) {
  if (!val) {
    if (show.value && !isCollapsing()) {
      applyCollapseAnimation()
    }
  } else {
    clearCollapseTimer()
    show.value = true
  }
}

onBeforeUnmount(() => {
  clearCollapseTimer()
})

function applyExpandAnimation() {
  applyExpand()
}

// 圆形收起：收缩回同一展开原点，动画期间 dialog 留在 DOM 中，播完再关闭
function applyCollapseAnimation() {
  applyCollapse(() => {
    show.value = false
  })
}

// 对外可观测面保持迁出前一致（既有红线用例按此访问；composable 抽出的 calcOrigin 在此继续暴露）
defineExpose({
  show,
  contentRef,
  calcOrigin,
  applyExpandAnimation,
  applyCollapseAnimation,
})
</script>

<style scoped>
.expand-content {
  transform-origin: center center;
}
</style>
