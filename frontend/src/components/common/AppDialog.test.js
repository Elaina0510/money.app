import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import AppDialog from './AppDialog.vue'
import { useAppStore } from '@/stores/useAppStore'
import { EXPAND_DURATION, EXPAND_EASING } from '@/composables/useExpandAnimation'
import appDialogSource from './AppDialog.vue?raw'
import mainSource from '@/main.js?raw'

// v-dialog 桩：受控 modelValue 决定内容是否挂载（AppDialog 的收起拦截正是延后这个 false）
const VDialogStub = {
  name: 'VDialog',
  props: {
    modelValue: Boolean,
    width: { type: [String, Number], default: undefined },
    maxWidth: { type: [String, Number], default: undefined },
    transition: { type: [String, Object, Boolean], default: undefined },
    persistent: Boolean,
  },
  emits: ['update:modelValue', 'after:leave', 'click:outside'],
  template:
    '<div class="v-dialog-stub">' +
    '<slot name="activator" :props="{}" />' +
    '<div v-if="modelValue" class="v-dialog__content"><slot /></div>' +
    '</div>',
}

function mountDialog(props = {}, slots = { default: '<div class="payload">内容</div>' }) {
  return mount(AppDialog, {
    props,
    global: {
      stubs: { 'v-dialog': VDialogStub, VDialog: VDialogStub },
    },
    slots,
  })
}

function contentStyle(wrapper) {
  const el = wrapper.find('.app-dialog__content').element
  return el.style
}

// 视口 rect 桩：jsdom 无布局 → 原点映射走「调用参数断言」（§7.3 既定手法）
function stubRect() {
  return vi.spyOn(window.HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
    () =>
      /** @type {DOMRect} */ ({
        left: 100,
        top: 50,
        width: 250,
        height: 200,
        right: 350,
        bottom: 250,
        x: 100,
        y: 50,
        toJSON: () => ({}),
      }),
  )
}

describe('AppDialog（M14 全站对话框统一壳）', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // ---------- 任务 9.2 ①：打开即应用展开内联样式 ----------

  it('用例M14-1: 打开后内容节点带展开内联样式（transformOrigin 非空 + scale(1) + 统一时长缓动）', async () => {
    const wrapper = mountDialog()
    await wrapper.setProps({ modelValue: true })
    await nextTick()

    const style = contentStyle(wrapper)
    expect(style.transformOrigin).toBeTruthy()
    expect(style.transform).toBe('scale(1)')
    expect(style.opacity).toBe('1')
    // 全站展开口径 220ms（D10）+ 统一缓动，且无逐处硬编码
    expect(style.transition).toContain(`${EXPAND_DURATION}ms`)
    expect(style.transition).toContain(EXPAND_EASING)
    wrapper.unmount()
  })

  it('用例M14-1b: 初始即打开（appear 路径）同样应用展开样式', async () => {
    const wrapper = mountDialog({ modelValue: true })
    await nextTick()
    await nextTick()
    expect(contentStyle(wrapper).transform).toBe('scale(1)')
    wrapper.unmount()
  })

  // ---------- 任务 4 / 5.2：origin 来源优先级（调用参数断言） ----------

  it('用例M14-2: 未传 origin → 取 appStore.lastClickOrigin（pointerdown 捕获的最近点击）', async () => {
    const rectSpy = stubRect()
    useAppStore().setLastClickOrigin({ x: 200, y: 150 })

    const wrapper = mountDialog()
    await wrapper.setProps({ modelValue: true })
    await nextTick()

    // (200-100)/250 = 40%，(150-50)/200 = 50%
    expect(contentStyle(wrapper).transformOrigin).toBe('40% 50%')
    rectSpy.mockRestore()
    wrapper.unmount()
  })

  it('用例M14-2b: props.origin 显式传入时优先于 appStore.lastClickOrigin', async () => {
    const rectSpy = stubRect()
    useAppStore().setLastClickOrigin({ x: 200, y: 150 })

    const wrapper = mountDialog({ origin: { x: 350, y: 250 } })
    await wrapper.setProps({ modelValue: true })
    await nextTick()

    expect(contentStyle(wrapper).transformOrigin).toBe('100% 100%')
    rectSpy.mockRestore()
    wrapper.unmount()
  })

  it('用例M14-2c: 无任何触发点（键盘打开，lastClickOrigin 为 null）→ 退化中心，不瞬现也不错位', async () => {
    const rectSpy = stubRect()
    const wrapper = mountDialog()
    await wrapper.setProps({ modelValue: true })
    await nextTick()

    expect(contentStyle(wrapper).transformOrigin).toBe('center center')
    expect(contentStyle(wrapper).transform).toBe('scale(1)')
    rectSpy.mockRestore()
    wrapper.unmount()
  })

  // ---------- 任务 5.3：关闭 = 反向收缩播完才真正关 dialog ----------

  describe('收起与重开（fake timers）', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    it('用例M14-3: modelValue→false 先播 scale(0) 收缩，dialog 延时到 duration 之后才关', async () => {
      const wrapper = mountDialog({ modelValue: true })
      await nextTick()

      await wrapper.setProps({ modelValue: false })

      const style = contentStyle(wrapper)
      expect(style.transform).toBe('scale(0)')
      expect(style.opacity).toBe('0')
      // 收缩期间 v-dialog 仍挂载（未真正关闭），也未向外回抛 false
      expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(true)
      const emitted = wrapper.emitted('update:modelValue') || []
      expect(emitted.some((e) => e[0] === false)).toBe(false)

      vi.advanceTimersByTime(EXPAND_DURATION - 1)
      await nextTick()
      expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(true)

      vi.advanceTimersByTime(1)
      await nextTick()
      expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(false)
      expect(wrapper.find('.app-dialog__content').exists()).toBe(false)
      const after = wrapper.emitted('update:modelValue')
      expect(after[after.length - 1]).toEqual([false])
      wrapper.unmount()
    })

    it('用例M14-4: 遮罩/ESC（v-dialog 回抛 false）同样先播反向收缩再关', async () => {
      const wrapper = mountDialog({ modelValue: true })
      await nextTick()

      const dialog = wrapper.findComponent({ name: 'VDialog' })
      dialog.vm.$emit('update:modelValue', false)
      await nextTick()

      expect(contentStyle(wrapper).transform).toBe('scale(0)')
      expect(dialog.props('modelValue')).toBe(true)

      vi.advanceTimersByTime(EXPAND_DURATION)
      await nextTick()
      expect(dialog.props('modelValue')).toBe(false)
      wrapper.unmount()
    })

    it('用例M14-5: 收缩动画中重开 → 取消收起并重新展开，不报错、无叠加', async () => {
      const wrapper = mountDialog({ modelValue: true })
      await nextTick()

      await wrapper.setProps({ modelValue: false })
      expect(contentStyle(wrapper).transform).toBe('scale(0)')

      await wrapper.setProps({ modelValue: true })
      await nextTick()
      expect(() => vi.advanceTimersByTime(EXPAND_DURATION * 3)).not.toThrow()
      await nextTick()

      // 收起计时被取消后不得把已重开的画面关掉
      expect(wrapper.findComponent({ name: 'VDialog' }).props('modelValue')).toBe(true)
      expect(contentStyle(wrapper).transform).toBe('scale(1)')
      expect(wrapper.findAll('.app-dialog__content')).toHaveLength(1)
      wrapper.unmount()
    })

    it('用例M14-5b: 重复关闭信号只播一次收起（天然去重，只回抛一次 false）', async () => {
      const wrapper = mountDialog({ modelValue: true })
      await nextTick()

      const dialog = wrapper.findComponent({ name: 'VDialog' })
      await wrapper.setProps({ modelValue: false })
      dialog.vm.$emit('update:modelValue', false)

      vi.advanceTimersByTime(EXPAND_DURATION)
      await nextTick()

      const falseEmits = (wrapper.emitted('update:modelValue') || []).filter((e) => e[0] === false)
      expect(falseEmits).toHaveLength(1)
      wrapper.unmount()
    })
  })

  // ---------- 任务 5.1 / 5.4：$attrs 透传与 after:leave 回焦链 ----------

  it('用例M14-6: max-width / persistent 等 v-dialog 属性经 $attrs 原样透传（宿主功能零改动）', () => {
    const withAttrs = mount(AppDialog, {
      props: { modelValue: true },
      attrs: { 'max-width': '480', persistent: true },
      global: { stubs: { 'v-dialog': VDialogStub, VDialog: VDialogStub } },
      slots: { default: '<b class="x">x</b>' },
    })
    const d = withAttrs.findComponent({ name: 'VDialog' })
    expect(d.props('maxWidth')).toBe('480')
    expect(d.props('persistent')).toBe(true)
    // 自带位移由壳内关掉：展开动画统一由 useExpandAnimation 承载
    expect(d.props('transition')).toBeNull()
    expect(withAttrs.find('.x').exists()).toBe(true)
    withAttrs.unmount()
  })

  it('用例M14-7: v-dialog 的 after:leave 透传给宿主（M13 关闭回焦链时序不变）', async () => {
    const wrapper = mountDialog({ modelValue: true })
    await nextTick()

    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('after:leave')
    await nextTick()
    expect(wrapper.emitted('after:leave')).toHaveLength(1)

    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('click:outside')
    await nextTick()
    expect(wrapper.emitted('click:outside')).toHaveLength(1)
    wrapper.unmount()
  })

  it('用例M14-8: 源码结构锁——壳内为 v-dialog(:transition="null") > Transition(appear,:css=false) > 内容容器', () => {
    expect(appDialogSource.match(/<v-dialog/g)).toHaveLength(1)
    expect(appDialogSource).toMatch(/:transition="null"/)
    expect(appDialogSource).toMatch(/<Transition\b[^>]*appear[^>]*:css="false"/)
    expect(appDialogSource).toMatch(/@enter="onEnter"/)
    expect(appDialogSource).toMatch(/v-bind="\$attrs"/)
    expect(appDialogSource).toMatch(/defineOptions\(\{ inheritAttrs: false \}\)/)
    expect(appDialogSource).toMatch(/props\.origin \?\? appStore\.lastClickOrigin/)
    expect(appDialogSource).toMatch(/class="app-dialog__content"/)
    // 全站收编口径：壳内不再出现任何 Vuetify 位移过渡字面量
    expect(appDialogSource).not.toMatch(/dialog-bottom-transition/)
    // 任务 7.1：main.js 的 VMenu defaults 已落
    expect(mainSource).toMatch(/defaults:\s*\{[\s\S]*?VMenu:\s*\{[\s\S]*?transition:\s*'fab-transition'/)
  })
})
