<template>
  <v-dialog
    :model-value="show"
    :transition="null"
    v-bind="$attrs"
    @update:model-value="onDialogModelValue"
    @after:leave="onAfterLeave"
    @click:outside="onClickOutside"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <slot name="activator" v-bind="activatorProps" />
    </template>
    <Transition appear :css="false" @enter="onEnter">
      <div ref="contentRef" class="app-dialog__content">
        <slot />
      </div>
    </Transition>
  </v-dialog>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useExpandAnimation } from '@/composables/useExpandAnimation'
import { useAppStore } from '@/stores/useAppStore'

/* v1.4.3 M14（需求十四 / 设计 §14.2.1，D7）：全站对话框统一壳。
 * 结构 = v-dialog(:transition="null" 关掉自带位移) > Transition(appear, :css="false") > 内容容器，
 * 展开/收起机制走 useExpandAnimation（与 ExpandTransition 同一实现源）：
 * 自最近一次触发点圆形扩散展开、关闭反向收缩，播完才真正关 v-dialog；
 * 重开取消收起（collapse-cancel）同套机制。
 * max-width / persistent / scrollable 等 v-dialog 属性经 $attrs 原样透传，宿主页面功能零改动。 */
defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  // 触发点视口坐标；未传则取 appStore.lastClickOrigin（pointerdown 捕获），再无则退化中心
  origin: {
    type: Object,
    default: null,
  },
  duration: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'after:leave', 'click:outside'])

const appStore = useAppStore()
const show = ref(props.modelValue)
const contentRef = ref(null)

const { applyExpand, applyCollapse, clearCollapseTimer, isCollapsing } = useExpandAnimation(contentRef, {
  origin: () => props.origin ?? appStore.lastClickOrigin,
  duration: () => props.duration,
})

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      // 程序化/点按打开：收起动画进行中则取消收起，直接回到展开态（重开需重新播展开）
      const resuming = isCollapsing()
      clearCollapseTimer()
      show.value = true
      if (resuming) nextTick(applyExpandOnce)
    } else if (show.value) {
      // 程序化关闭（完成/取消）：先播反向收缩，播完再真正关 dialog
      startCollapse()
    }
  }
)

watch(show, (val) => {
  emit('update:modelValue', val)
  if (val) {
    // appear hook 与 DOM 挂载时序在桩环境下不保证，二者统一走幂等展开
    nextTick(applyExpandOnce)
  }
})

onMounted(() => {
  // 初始即打开（appear 路径）：Transition 的 appear hook 在部分宿主环境不回落 enter，
  // 此处补一次幂等展开，保证「不得瞬现」口径在任何挂载时序下成立。
  if (show.value) nextTick(applyExpandOnce)
})

onBeforeUnmount(() => {
  clearCollapseTimer()
})

// 拦截 v-dialog 的用户交互关闭（遮罩 / ESC）：同样先播反向收缩
function onDialogModelValue(val) {
  if (!val) {
    if (show.value && !isCollapsing()) {
      startCollapse()
    }
  } else {
    const resuming = isCollapsing()
    clearCollapseTimer()
    show.value = true
    if (resuming) nextTick(applyExpandOnce)
  }
}

function startCollapse() {
  applyCollapse(() => {
    show.value = false
  })
}

// 幂等展开：Transition 的 appear hook 与 watch(show) 的 nextTick 兜底只生效一次；
// 收起中途重开时元素停在 scale(0)，条件不成立 → 会重新播展开（不留半程状态）。
function applyExpandOnce() {
  const el = contentRef.value
  if (!el) return
  if (el.style.transform === 'scale(1)' && el.style.opacity === '1') return
  applyExpand()
}

// Transition JS hook：内容节点挂载（含 appear）即自触发点展开
function onEnter(el) {
  if (el && el !== contentRef.value) contentRef.value = el
  applyExpandOnce()
}

function onAfterLeave(...args) {
  emit('after:leave', ...args)
}

function onClickOutside(...args) {
  emit('click:outside', ...args)
}

defineExpose({ show, contentRef, startCollapse })
</script>

<style scoped>
/* 变换只作用于 overlay 内容节点（.v-dialog__content 内层），不新建横向滚动上下文（M11 红线） */
.app-dialog__content {
  transform-origin: center center;
}
</style>
