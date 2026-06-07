import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock child components
vi.mock('./ExpandTransition.vue', () => ({
  default: {
    name: 'ExpandTransition',
    props: ['modelValue', 'origin', 'maxWidth'],
    emits: ['update:modelValue'],
    template:
      '<div class="expand-transition-mock"><slot name="activator" :props="{}" /><slot /></div>',
  },
}))

import DatePickerPopover from './DatePickerPopover.vue'

describe('DatePickerPopover', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.exists()).toBe(true)
  })

  it('should have modelValue prop', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.props('modelValue')).toBe('')
  })

  it('should have modelValueTime prop', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.props('modelValueTime')).toBe('')
  })

  it('should have showTime prop', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.props('showTime')).toBe(false)
  })

  it('should have label prop', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.props('label')).toBe('选择日期')
  })

  it('should accept custom label', () => {
    const wrapper = mount(DatePickerPopover, {
      props: {
        label: '消费日期',
      },
    })
    expect(wrapper.props('label')).toBe('消费日期')
  })

  it('should have showPicker initially false', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.vm.showPicker).toBe(false)
  })

  it('should have openPicker method', () => {
    const wrapper = mount(DatePickerPopover)
    expect(typeof wrapper.vm.openPicker).toBe('function')
  })

  it('should have onDateSelected method', () => {
    const wrapper = mount(DatePickerPopover)
    expect(typeof wrapper.vm.onDateSelected).toBe('function')
  })

  it('should have onTimeSelected method', () => {
    const wrapper = mount(DatePickerPopover)
    expect(typeof wrapper.vm.onTimeSelected).toBe('function')
  })

  it('should emit update:modelValue on date selection', async () => {
    const wrapper = mount(DatePickerPopover)

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-06-06'])
  })

  it('should emit update:modelValueTime on time selection', async () => {
    const wrapper = mount(DatePickerPopover, {
      props: {
        showTime: true,
      },
    })

    wrapper.vm.onTimeSelected('14:30')
    await nextTick()

    expect(wrapper.emitted('update:modelValueTime')).toBeTruthy()
    expect(wrapper.emitted('update:modelValueTime')[0]).toEqual(['14:30'])
  })

  it('should close picker after date selection when showTime is false', async () => {
    const wrapper = mount(DatePickerPopover)

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.vm.showPicker).toBe(false)
  })

  it('should not close picker after date selection when showTime is true', async () => {
    const wrapper = mount(DatePickerPopover, {
      props: {
        showTime: true,
      },
    })

    wrapper.vm.showPicker = true
    await nextTick()

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.vm.showPicker).toBe(true)
  })

  it('should have displayValue computed', () => {
    const wrapper = mount(DatePickerPopover, {
      props: {
        modelValue: '2026-06-06',
      },
    })
    expect(wrapper.vm.displayValue).toBe('2026-06-06')
  })

  it('should return empty string for displayValue when no modelValue', () => {
    const wrapper = mount(DatePickerPopover)
    expect(wrapper.vm.displayValue).toBe('')
  })
})
