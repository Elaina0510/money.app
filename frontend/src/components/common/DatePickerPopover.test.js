import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock child components: render activator always, dialog content only when open
vi.mock('./ExpandTransition.vue', () => ({
  default: {
    name: 'ExpandTransition',
    props: ['modelValue', 'origin', 'maxWidth'],
    emits: ['update:modelValue'],
    template:
      '<div class="expand-transition-mock">' +
      '<slot name="activator" :props="{}" />' +
      '<div v-if="modelValue" class="expand-transition-content"><slot /></div>' +
      '</div>',
  },
}))

import DatePickerPopover from './DatePickerPopover.vue'

const globalStubs = {
  'v-text-field': {
    name: 'VTextField',
    props: ['modelValue', 'label'],
    template: '<div class="v-text-field-stub" :data-label="label">{{ modelValue }}</div>',
  },
  VTextField: {
    name: 'VTextField',
    props: ['modelValue', 'label'],
    template: '<div class="v-text-field-stub" :data-label="label">{{ modelValue }}</div>',
  },
  'v-date-picker': {
    name: 'VDatePicker',
    props: ['modelValue'],
    template: '<div class="v-date-picker-stub" :data-model-value="String(modelValue)" />',
  },
  'v-time-picker': {
    name: 'VTimePicker',
    props: ['modelValue', 'format'],
    template: '<div class="v-time-picker-stub" :data-format="format" />',
  },
  'v-btn': {
    name: 'VBtn',
    template: '<button class="v-btn-stub"><slot /></button>',
  },
}

function mountPopover(props = {}) {
  return mount(DatePickerPopover, {
    props,
    global: { stubs: globalStubs },
  })
}

function transitionWrappers(wrapper) {
  return wrapper.findAllComponents({ name: 'ExpandTransition' })
}

describe('DatePickerPopover', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ---------- 基础 props / 方法 ----------

  it('should render correctly', () => {
    const wrapper = mountPopover()
    expect(wrapper.exists()).toBe(true)
  })

  it('should have modelValue prop', () => {
    const wrapper = mountPopover()
    expect(wrapper.props('modelValue')).toBe('')
  })

  it('should have modelValueTime prop', () => {
    const wrapper = mountPopover()
    expect(wrapper.props('modelValueTime')).toBe('')
  })

  it('should have showTime prop', () => {
    const wrapper = mountPopover()
    expect(wrapper.props('showTime')).toBe(false)
  })

  it('should have label prop', () => {
    const wrapper = mountPopover()
    expect(wrapper.props('label')).toBe('选择日期')
  })

  it('should accept custom label', () => {
    const wrapper = mountPopover({ label: '消费日期' })
    expect(wrapper.props('label')).toBe('消费日期')
  })

  it('should have showPicker initially false', () => {
    const wrapper = mountPopover()
    expect(wrapper.vm.showPicker).toBe(false)
  })

  it('should have openPicker method', () => {
    const wrapper = mountPopover()
    expect(typeof wrapper.vm.openPicker).toBe('function')
  })

  it('should have onDateSelected method', () => {
    const wrapper = mountPopover()
    expect(typeof wrapper.vm.onDateSelected).toBe('function')
  })

  it('should have openTimePicker method', () => {
    const wrapper = mountPopover()
    expect(typeof wrapper.vm.openTimePicker).toBe('function')
  })

  it('should have confirmTime method', () => {
    const wrapper = mountPopover()
    expect(typeof wrapper.vm.confirmTime).toBe('function')
  })

  it('should have cancelTime method', () => {
    const wrapper = mountPopover()
    expect(typeof wrapper.vm.cancelTime).toBe('function')
  })

  it('should emit update:modelValue on date selection', async () => {
    const wrapper = mountPopover()

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-06-06'])
  })

  it('should emit update:modelValueTime on time confirm', async () => {
    const wrapper = mountPopover({ showTime: true })

    wrapper.vm.pendingTime = '14:30'
    wrapper.vm.confirmTime()
    await nextTick()

    expect(wrapper.emitted('update:modelValueTime')).toBeTruthy()
    expect(wrapper.emitted('update:modelValueTime')[0]).toEqual(['14:30'])
  })

  it('should close picker after date selection', async () => {
    const wrapper = mountPopover()

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.vm.showPicker).toBe(false)
  })

  it('should have displayValue computed', () => {
    const wrapper = mountPopover({ modelValue: '2026-06-06' })
    expect(wrapper.vm.displayValue).toBe('2026-06-06')
  })

  it('should return empty string for displayValue when no modelValue', () => {
    const wrapper = mountPopover()
    expect(wrapper.vm.displayValue).toBe('')
  })

  // ---------- 用例 1：show-time 时渲染两行（日期/时间各一 ExpandTransition） ----------

  it('用例1: show-time renders date & time fields as two stacked rows', () => {
    const wrapper = mountPopover({ showTime: true, label: '消费日期' })

    const container = wrapper.find('.date-time-fields')
    expect(container.exists()).toBe(true)

    // .date-time-fields 下两个直接子块，各为一个 ExpandTransition
    const children = container.element.children
    expect(children.length).toBe(2)
    expect(children[0].classList.contains('expand-transition-mock')).toBe(true)
    expect(children[1].classList.contains('expand-transition-mock')).toBe(true)

    // 日期字段在第一行、时间字段在第二行（不再同一 flex-row）
    const blocks = transitionWrappers(wrapper)
    const dateField = blocks[0].find('.v-text-field-stub')
    const timeField = blocks[1].find('.v-text-field-stub')
    expect(dateField.exists()).toBe(true)
    expect(dateField.attributes('data-label')).toBe('消费日期')
    expect(timeField.exists()).toBe(true)
    expect(timeField.attributes('data-label')).toBe('时间')
    // 每行各自只有一个输入项
    expect(blocks[0].findAll('.v-text-field-stub').length).toBe(1)
    expect(blocks[1].findAll('.v-text-field-stub').length).toBe(1)
  })

  // ---------- 用例 2：未传 show-time → 仅日期字段（账单筛选场景回归） ----------

  it('用例2: without show-time renders only the date row (bill filter regression)', () => {
    const wrapper = mountPopover({ label: '开始日期' })

    const container = wrapper.find('.date-time-fields')
    expect(container.exists()).toBe(true)
    expect(container.element.children.length).toBe(1)
    expect(container.element.children[0].classList.contains('expand-transition-mock')).toBe(true)

    const fields = wrapper.findAll('.v-text-field-stub')
    expect(fields.length).toBe(1)
    expect(fields[0].attributes('data-label')).toBe('开始日期')
    expect(wrapper.text()).not.toContain('时间')
  })

  // ---------- 用例 3：点击时间字段 → 第二个 ExpandTransition 打开，origin 为点击坐标 ----------

  it('用例3: clicking time field opens second ExpandTransition with click origin', async () => {
    const wrapper = mountPopover({ showTime: true })
    const blocks = transitionWrappers(wrapper)

    expect(blocks[1].props('modelValue')).toBe(false)
    expect(blocks[1].text()).not.toContain('取消')

    const timeField = blocks[1].find('.v-text-field-stub')
    await timeField.trigger('click', { clientX: 320, clientY: 450 })

    expect(blocks[1].props('modelValue')).toBe(true)
    expect(blocks[1].props('origin')).toEqual({ x: 320, y: 450 })

    // 弹层为 24 小时制表盘时钟 + 取消/确定
    const content = blocks[1].find('.expand-transition-content')
    expect(content.exists()).toBe(true)
    expect(content.text()).toContain('选择时间')
    expect(content.text()).toContain('取消')
    expect(content.text()).toContain('确定')
    expect(content.find('.v-time-picker-stub').attributes('data-format')).toBe('24hr')

    // 日期弹层不受影响
    expect(blocks[0].props('modelValue')).toBe(false)
  })

  // ---------- 用例 4：确定回抛并关闭；取消不回抛 ----------

  it('用例4: 确定 emits update:modelValueTime, fills selectedTime and closes', async () => {
    const wrapper = mountPopover({ showTime: true, modelValueTime: '09:00' })
    const blocks = transitionWrappers(wrapper)

    await blocks[1].find('.v-text-field-stub').trigger('click', { clientX: 10, clientY: 20 })
    // 打开时预填当前时间
    expect(wrapper.vm.pendingTime).toBe('09:00')

    wrapper.vm.pendingTime = '14:30'
    await nextTick()

    const buttons = blocks[1].findAll('.v-btn-stub')
    expect(buttons.length).toBe(2)
    await buttons[1].trigger('click') // 确定

    expect(wrapper.emitted('update:modelValueTime')).toBeTruthy()
    expect(wrapper.emitted('update:modelValueTime')[0]).toEqual(['14:30'])
    expect(wrapper.vm.selectedTime).toBe('14:30')
    expect(blocks[1].props('modelValue')).toBe(false)
  })

  it('用例4: 取消 closes without emitting and keeps selectedTime', async () => {
    const wrapper = mountPopover({ showTime: true, modelValueTime: '09:00' })
    const blocks = transitionWrappers(wrapper)

    await blocks[1].find('.v-text-field-stub').trigger('click', { clientX: 10, clientY: 20 })
    wrapper.vm.pendingTime = '14:30'
    await nextTick()

    const buttons = blocks[1].findAll('.v-btn-stub')
    await buttons[0].trigger('click') // 取消

    expect(wrapper.emitted('update:modelValueTime')).toBeFalsy()
    expect(wrapper.vm.selectedTime).toBe('09:00')
    expect(blocks[1].props('modelValue')).toBe(false)
  })

  it('用例4: 时间字段无初值时打开弹层默认 12:00', async () => {
    const wrapper = mountPopover({ showTime: true })
    const blocks = transitionWrappers(wrapper)

    await blocks[1].find('.v-text-field-stub').trigger('click', { clientX: 1, clientY: 1 })
    expect(wrapper.vm.pendingTime).toBe('12:00')
  })

  // ---------- 用例 6：日期弹层选日仍即回填并收起 ----------

  it('用例6: date picker still fills value and collapses on select', async () => {
    const wrapper = mountPopover({ label: '消费日期' })
    const blocks = transitionWrappers(wrapper)

    await blocks[0].find('.v-text-field-stub').trigger('click', { clientX: 100, clientY: 200 })
    expect(blocks[0].props('modelValue')).toBe(true)
    expect(blocks[0].props('origin')).toEqual({ x: 100, y: 200 })
    expect(blocks[0].find('.v-date-picker-stub').exists()).toBe(true)

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-06-06'])
    expect(wrapper.vm.selectedDate).toBe('2026-06-06')
    expect(blocks[0].props('modelValue')).toBe(false)
    expect(blocks[0].find('.v-date-picker-stub').exists()).toBe(false)
  })
})
