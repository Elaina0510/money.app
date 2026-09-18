import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import ExpandTransition from './ExpandTransition.vue'

// Stub v-dialog: ExpandTransition uses it via template resolution (no direct import),
// so register the stub through global.stubs at mount time.
const VDialogStub = {
  name: 'VDialog',
  props: ['modelValue', 'width', 'maxWidth'],
  emits: ['update:modelValue'],
  template: '<div class="v-dialog"><slot name="activator" :props="{}" /><slot /></div>',
}

function mountET(props = {}) {
  return mount(ExpandTransition, {
    props,
    global: {
      stubs: {
        'v-dialog': VDialogStub,
        VDialog: VDialogStub,
      },
    },
  })
}

describe('ExpandTransition', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', () => {
    const wrapper = mountET()
    expect(wrapper.exists()).toBe(true)
  })

  it('should have modelValue prop', () => {
    const wrapper = mountET()
    expect(wrapper.props('modelValue')).toBe(false)
  })

  it('should have origin prop', () => {
    const wrapper = mountET()
    expect(wrapper.props('origin')).toEqual({ x: 0, y: 0 })
  })

  it('should have duration prop with default', () => {
    const wrapper = mountET()
    expect(wrapper.props('duration')).toBe(250)
  })

  it('should accept custom duration', () => {
    const wrapper = mountET({
      duration: 300,
    })
    expect(wrapper.props('duration')).toBe(300)
  })

  it('should have width prop', () => {
    const wrapper = mountET()
    expect(wrapper.props('width')).toBe('auto')
  })

  it('should have maxWidth prop', () => {
    const wrapper = mountET()
    expect(wrapper.props('maxWidth')).toBe(400)
  })

  it('should emit update:modelValue when show changes', async () => {
    const wrapper = mountET()

    wrapper.vm.show = true
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
  })

  it('should have calcOrigin method', () => {
    const wrapper = mountET()
    expect(typeof wrapper.vm.calcOrigin).toBe('function')
  })

  it('should have applyExpandAnimation method', () => {
    const wrapper = mountET()
    expect(typeof wrapper.vm.applyExpandAnimation).toBe('function')
  })

  it('should have applyCollapseAnimation method', () => {
    const wrapper = mountET()
    expect(typeof wrapper.vm.applyCollapseAnimation).toBe('function')
  })

  it('should apply circular expand animation when opened', async () => {
    const wrapper = mountET({ modelValue: false, origin: { x: 100, y: 50 } })

    await wrapper.setProps({ modelValue: true })
    await nextTick()

    const el = wrapper.find('.expand-content').element
    expect(el.style.transform).toBe('scale(1)')
    expect(el.style.opacity).toBe('1')
    expect(el.style.transition).toContain('250ms')
  })

  // ---------- 用例 5：圆形收起动画（程序化关闭路径） ----------

  describe('collapse animation (fake timers)', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('用例5-programmatic: modelValue false plays collapse style, dialog closes after duration', async () => {
      const wrapper = mountET({ modelValue: true, duration: 250 })
      await nextTick()

      await wrapper.setProps({ modelValue: false })

      const el = wrapper.find('.expand-content').element
      // 先应用收起样式（圆形收缩回原点）
      expect(el.style.transform).toBe('scale(0)')
      expect(el.style.opacity).toBe('0')
      expect(el.style.transition).toContain('250ms')
      // 动画期间 dialog 留在 DOM 中，未真正关闭
      expect(wrapper.vm.show).toBe(true)
      expect(wrapper.find('.v-dialog').exists()).toBe(true)

      vi.advanceTimersByTime(249)
      await nextTick()
      expect(wrapper.vm.show).toBe(true)

      vi.advanceTimersByTime(1)
      await nextTick()
      // duration 之后才真正关闭，并向外回抛 false
      expect(wrapper.vm.show).toBe(false)
      const emits = wrapper.emitted('update:modelValue')
      expect(emits[emits.length - 1]).toEqual([false])
    })

    it('用例5-interactive: dialog-driven close (scrim/ESC) also plays circular collapse', async () => {
      const wrapper = mountET({ modelValue: true, duration: 250 })
      await nextTick()

      const dialog = wrapper.findComponent({ name: 'VDialog' })
      // 用户点击遮罩 / ESC：v-dialog 试图关闭（emit update:modelValue false）
      dialog.vm.$emit('update:modelValue', false)
      await nextTick()

      const el = wrapper.find('.expand-content').element
      expect(el.style.transform).toBe('scale(0)')
      expect(el.style.opacity).toBe('0')
      expect(el.style.transition).toContain('250ms')
      // 拦截生效：动画播放完成前 dialog 仍保持打开
      expect(wrapper.vm.show).toBe(true)
      expect(dialog.props('modelValue')).toBe(true)

      vi.advanceTimersByTime(250)
      await nextTick()
      expect(wrapper.vm.show).toBe(false)
      expect(dialog.props('modelValue')).toBe(false)
      const emits = wrapper.emitted('update:modelValue')
      expect(emits[emits.length - 1]).toEqual([false])
    })

    it('should not double-collapse when both paths fire', async () => {
      const wrapper = mountET({ modelValue: true, duration: 250 })
      await nextTick()

      await wrapper.setProps({ modelValue: false })
      const dialog = wrapper.findComponent({ name: 'VDialog' })
      dialog.vm.$emit('update:modelValue', false)

      vi.advanceTimersByTime(250)
      await nextTick()

      expect(wrapper.vm.show).toBe(false)
      const falseEmits = wrapper.emitted('update:modelValue').filter((e) => e[0] === false)
      expect(falseEmits.length).toBe(1)
    })
  })
})
