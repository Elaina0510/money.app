import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock Vuetify components
vi.mock('vuetify/components', () => ({
  VDialog: {
    name: 'VDialog',
    props: ['modelValue', 'width', 'maxWidth'],
    emits: ['update:modelValue'],
    template: '<div class="v-dialog"><slot name="activator" :props="{}" /><slot /></div>',
  },
}))

import ExpandTransition from './ExpandTransition.vue'

describe('ExpandTransition', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', () => {
    const wrapper = mount(ExpandTransition)
    expect(wrapper.exists()).toBe(true)
  })

  it('should have modelValue prop', () => {
    const wrapper = mount(ExpandTransition)
    expect(wrapper.props('modelValue')).toBe(false)
  })

  it('should have origin prop', () => {
    const wrapper = mount(ExpandTransition)
    expect(wrapper.props('origin')).toEqual({ x: 0, y: 0 })
  })

  it('should have duration prop with default', () => {
    const wrapper = mount(ExpandTransition)
    expect(wrapper.props('duration')).toBe(250)
  })

  it('should accept custom duration', () => {
    const wrapper = mount(ExpandTransition, {
      props: {
        duration: 300,
      },
    })
    expect(wrapper.props('duration')).toBe(300)
  })

  it('should have width prop', () => {
    const wrapper = mount(ExpandTransition)
    expect(wrapper.props('width')).toBe('auto')
  })

  it('should have maxWidth prop', () => {
    const wrapper = mount(ExpandTransition)
    expect(wrapper.props('maxWidth')).toBe(400)
  })

  it('should emit update:modelValue when show changes', async () => {
    const wrapper = mount(ExpandTransition)

    wrapper.vm.show = true
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
  })

  it('should have calcOrigin method', () => {
    const wrapper = mount(ExpandTransition)
    expect(typeof wrapper.vm.calcOrigin).toBe('function')
  })

  it('should have applyExpandAnimation method', () => {
    const wrapper = mount(ExpandTransition)
    expect(typeof wrapper.vm.applyExpandAnimation).toBe('function')
  })
})
