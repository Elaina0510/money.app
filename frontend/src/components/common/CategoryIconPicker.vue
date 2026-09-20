<template>
  <div class="category-icon-picker">
    <!--
      activator：替代原「图标 (mdi-*)」文本框，全流程不再暴露任意文本图标名入口。
      形态沿用 v1.4.2（圆底 32px + 16px 图标 + 只读图标名 + 尾端「▾ 选择图标」）；
      M13 起唯一变化是它**只负责开合居中小弹窗**，并持有 ref 供弹窗关闭后回焦（需求 13.3）。
    -->
    <div
      ref="activatorRef"
      class="icon-activator"
      :class="{ 'icon-activator--open': open }"
      role="button"
      tabindex="0"
      aria-label="选择图标"
      aria-haspopup="dialog"
      :aria-expanded="String(open)"
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

    <!--
      M13（需求十三 / 设计 §13.2）：全端**一条居中独立小弹窗**——
      用户裁定否决「底部面板」与 v1.4.2 的「宽屏内联展开 / 窄屏全屏浮层」双分支，
      故此处不再有窄屏判断、不再有第二份网格容器。
      max-width 取 min(560px, 92vw)（需求示例 90vw，按「具体设计定」条款取 92vw 与内边距节奏统一）；
      卡片 max-height 80vh 保证竖屏不超视口且底部「完成」常驻可见。
      嵌套在「新增分类」对话框之上：Vuetify overlay 默认后开者置上，无需手动 z-index。
      过渡：M14 收编为 AppDialog 原点展开（初版底部上浮过渡已退役，after:leave 透传保回焦）。
    -->
    <AppDialog
      :model-value="open"
      max-width="min(560px, 92vw)"
      @update:model-value="onDialogModelValue"
      @after:leave="onAfterLeave"
    >
      <v-card class="icon-dialog" rounded="xl">
        <div class="icon-dialog__head">
          <div class="icon-dialog__title text-subtitle-1 font-weight-bold">选择图标</div>
          <v-btn
            class="icon-dialog__close"
            icon="mdi-close"
            size="small"
            variant="text"
            aria-label="关闭"
            @click="closePanel"
          />
        </div>

        <!-- 当前选中预览：随点选响应式更新（单段式，无「确定」二段） -->
        <div class="icon-dialog__preview">
          <v-avatar size="48" class="icon-dialog__preview-avatar">
            <v-icon size="24">{{ displayIcon }}</v-icon>
          </v-avatar>
          <span class="icon-dialog__preview-name text-body-2">{{ displayIcon }}</span>
        </div>

        <!-- 网格滚动区：flex:1 + min-height:0 撑满弹窗可用高度（v1.4.2 写死的固定带高已废除） -->
        <div class="icon-grid-scroll">
          <IconGrid :icons="CATEGORY_ICONS" :selected="displayIcon" @pick="pick" />
        </div>

        <div class="icon-dialog__foot">
          <v-btn class="icon-dialog__done" color="primary" variant="tonal" @click="closePanel">完成</v-btn>
        </div>
      </v-card>
    </AppDialog>
  </div>
</template>

<script setup>
import { computed, h, ref, resolveComponent } from 'vue'
import { CATEGORY_ICONS } from '@/constants/categoryIcons'
import AppDialog from './AppDialog.vue'

// 表单默认图标（在精选集内），仅用于 modelValue 为空时的预览兜底
const FALLBACK_ICON = 'mdi-cash'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue'])

// 对外签名冻结：仅 modelValue + update:modelValue（两处调用方零改动是 M13 的设计前提）
const open = ref(false)
const activatorRef = ref(null)

const displayIcon = computed(() => props.modelValue || FALLBACK_ICON)
// 存量兼容：历史手输的非选集图标照常渲染（字体全量），仅提示需改选，不阻断表单其他字段
const notInCollection = computed(() => !CATEGORY_ICONS.includes(displayIcon.value))

/*
 * 图标网格：居中弹窗内唯一一份实现（M13 起不再有「内联/浮层」两分支共用一说）。
 * 单元格结构、选中高亮、点选事件单点定义；以 render 函数定义在组件内，
 * 使本面板保持单文件自包含（不额外新增文件）。配色沿用 v1.4.2（D 裁定：浮层配色不改）。
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

// 「完成」/✕/遮罩/ESC 一律只关闭、不再 emit（点选已即时回抛，保持单段式）
function closePanel() {
  open.value = false
}

// 受控 modelValue：遮罩 / ESC 等浮层自身关闭时同步状态，重复信号幂等、无叠层
function onDialogModelValue(value) {
  open.value = !!value
}

// 需求 13.3：关闭动画播完即回焦 activator，回到分类表单继续编辑其余字段
function onAfterLeave() {
  activatorRef.value?.focus()
}

// 单段式点选：立即回抛，activator 与弹窗顶部预览响应式更新，无「确定」二段
function pick(icon) {
  emit('update:modelValue', icon)
}
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

/* 居中弹窗体：列向 flex，滚动区吃掉剩余高度（卡片 80vh 上限保证竖屏不超视口） */
.icon-dialog {
  display: flex;
  flex-direction: column;
  max-height: 80vh;
  overflow: hidden;
}

.icon-dialog__head {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
  padding: 12px 12px 8px 16px;
}

.icon-dialog__title {
  flex-grow: 1;
  min-width: 0;
}

/* 顶部当前选中预览（48px 大预览 + 图标名），配色沿用主题 primary 半透明底口径 */
.icon-dialog__preview {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 12px;
  padding: 0 16px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.icon-dialog__preview-avatar {
  flex-shrink: 0;
  background: rgba(var(--v-theme-primary), 0.1);
}

.icon-dialog__preview-name {
  min-width: 0;
  overflow: hidden;
  color: rgb(var(--v-theme-on-surface-variant));
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 网格滚动区：撑满弹窗可用高度；M13 起不再写死固定带高（v1.4.2 旧值已废除） */
.icon-grid-scroll {
  flex: 1;
  min-height: 0;
  padding: 12px 16px;
  overflow-y: auto;
}

/* 列数随宽度自适应：auto-fill + 44px 下限（极窄视口仍有 ≥5 列），间隙 8px */
.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
  gap: 8px;
}

.icon-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1 / 1;
  min-height: 44px;
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

.icon-dialog__foot {
  display: flex;
  flex-shrink: 0;
  justify-content: flex-end;
  padding: 8px 12px 12px;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>
