<template>
  <div class="category-icon-picker">
    <!--
      activator：替代原「图标 (mdi-*)」文本框，全流程不再暴露任意文本图标名入口。
      圆形底 32px + 16px 图标 + 只读图标名 + 尾端「▾ 选择图标」提示。
    -->
    <div
      class="icon-activator"
      :class="{ 'icon-activator--open': open }"
      role="button"
      tabindex="0"
      aria-label="选择图标"
      @click="togglePanel"
      @keydown.enter.prevent="togglePanel"
      @keydown.space.prevent="togglePanel"
    >
      <v-avatar size="32" class="icon-activator__avatar">
        <v-icon size="16">{{ displayIcon }}</v-icon>
      </v-avatar>
      <span class="icon-activator__name text-body-2">{{ displayIcon }}</span>
      <v-chip v-if="notInCollection" class="icon-activator__chip" size="x-small" color="warning" variant="tonal">
        不在精选集，编辑需改选
      </v-chip>
      <span class="icon-activator__hint text-caption">▾ 选择图标</span>
    </div>

    <!-- 宽屏（≥600px）：点击后在本组件下方展开区内渲染网格（D6） -->
    <v-slide-y-transition>
      <div v-if="open && !isNarrow" class="icon-panel">
        <div class="icon-grid-scroll">
          <IconGrid :icons="CATEGORY_ICONS" :selected="displayIcon" @pick="pick" />
        </div>
        <div class="d-flex justify-end mt-2">
          <v-btn size="small" variant="text" @click="closePanel">收起</v-btn>
        </div>
      </div>
    </v-slide-y-transition>

    <!-- 窄屏（<600px）：全屏浮层，内部复用同一 Grid + 顶栏标题 +「收起 / 完成」（D6） -->
    <v-dialog
      :model-value="open && isNarrow"
      fullscreen
      transition="dialog-bottom-transition"
      @update:model-value="onDialogModelValue"
    >
      <v-card class="icon-dialog">
        <div class="icon-dialog__bar d-flex align-center">
          <div class="text-subtitle-1 flex-grow-1">选择图标</div>
          <v-btn size="small" variant="text" @click="closePanel">收起</v-btn>
          <v-btn size="small" variant="text" color="primary" class="ml-2" @click="closePanel">完成</v-btn>
        </div>
        <div class="icon-dialog__body pa-3">
          <div class="icon-grid-scroll">
            <IconGrid :icons="CATEGORY_ICONS" :selected="displayIcon" @pick="pick" />
          </div>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, h, onMounted, onUnmounted, ref, resolveComponent } from 'vue'
import { CATEGORY_ICONS } from '@/constants/categoryIcons'

// 表单默认图标（在精选集内），仅用于 modelValue 为空时的预览兜底
const FALLBACK_ICON = 'mdi-cash'
// 图标面板窄屏分界（D6：本面板按 600px，与全站 960px 分界另计）
const NARROW_BREAKPOINT = 600

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const isNarrow = ref(window.innerWidth < NARROW_BREAKPOINT)

const displayIcon = computed(() => props.modelValue || FALLBACK_ICON)
// 存量兼容：历史手输的非选集图标照常渲染（字体全量），仅提示需改选，不阻断表单其他字段
const notInCollection = computed(() => !CATEGORY_ICONS.includes(displayIcon.value))

/*
 * 图标网格：宽屏内联展开区与窄屏全屏浮层**共用同一份实现**（D6），
 * 单元格结构、选中高亮、点选事件单点定义，避免两个分支行为漂移。
 * 以 render 函数定义在组件内，使本面板保持单文件自包含（不额外新增文件）。
 */
const IconGrid = {
  name: 'CategoryIconGrid',
  props: {
    icons: { type: Array, default: () => [] },
    selected: { type: String, default: '' },
  },
  emits: ['pick'],
  setup(gridProps, { emit: gridEmit }) {
    return () =>
      h(
        'div',
        { class: 'icon-grid' },
        gridProps.icons.map((icon) =>
          h(
            'button',
            {
              key: icon,
              type: 'button',
              class: ['icon-cell', { 'icon-cell--selected': icon === gridProps.selected }],
              title: icon,
              'aria-label': `选择图标 ${icon}`,
              onClick: () => gridEmit('pick', icon),
            },
            [h(resolveComponent('v-icon'), { size: 20 }, { default: () => [icon] })],
          ),
        ),
      )
  },
}

function togglePanel() {
  open.value = !open.value
}

function closePanel() {
  open.value = false
}

// 遮罩 / ESC 等浮层自身关闭时同步状态，保持 activator 箭头形态一致
function onDialogModelValue(value) {
  if (!value) open.value = false
}

// 单段式点选：立即回抛，activator 预览响应式更新，无「确定」二段
function pick(icon) {
  emit('update:modelValue', icon)
}

function onResize() {
  isNarrow.value = window.innerWidth < NARROW_BREAKPOINT
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.icon-activator {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px 10px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.16);
  border-radius: 12px;
  cursor: pointer;
  user-select: none;
  transition: border-color 0.15s ease;
}

.icon-activator:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.icon-activator--open {
  border-color: rgb(var(--v-theme-primary));
}

.icon-activator__avatar {
  flex-shrink: 0;
  background: rgba(var(--v-theme-primary), 0.1);
}

.icon-activator__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-activator__chip {
  flex-shrink: 0;
}

.icon-activator__hint {
  margin-left: auto;
  flex-shrink: 0;
  color: rgba(var(--v-theme-on-surface-variant), 0.7);
}

.icon-panel {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.16);
  border-radius: 12px;
}

/* 展开区与全屏浮层共用的滚动容器 */
.icon-grid-scroll {
  max-height: 240px;
  overflow-y: auto;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
}

.icon-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1 / 1;
  min-height: 40px;
  padding: 0;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
  transition:
    background 0.15s ease,
    outline-color 0.15s ease;
}

.icon-cell:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.icon-cell--selected {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
  background: rgba(var(--v-theme-primary), 0.1);
}

.icon-dialog {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 0 !important;
}

.icon-dialog__bar {
  flex-shrink: 0;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.icon-dialog__body {
  flex-grow: 1;
  overflow-y: auto;
}
</style>
