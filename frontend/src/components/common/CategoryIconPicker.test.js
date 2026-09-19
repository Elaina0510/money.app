import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import CategoryIconPicker from './CategoryIconPicker.vue'
import { CATEGORY_ICONS } from '@/constants/categoryIcons'

// ── Vuetify 组件桩：只关心受控行为与 DOM 结构，不引入真实 Vuetify 实例 ──
const VDialogStub = {
  name: 'VDialog',
  props: { modelValue: Boolean, fullscreen: Boolean, transition: String },
  emits: ['update:modelValue'],
  template:
    '<div class="v-dialog-stub" :data-fullscreen="String(fullscreen)">' +
    '<div v-if="modelValue" class="v-dialog__content"><slot /></div></div>',
}

const globalStubs = {
  'v-dialog': VDialogStub,
  VDialog: VDialogStub,
  'v-avatar': { name: 'VAvatar', props: ['size'], template: '<div class="v-avatar-stub"><slot /></div>' },
  'v-icon': { name: 'VIcon', props: ['size'], template: '<i class="v-icon-stub"><slot /></i>' },
  'v-btn': { name: 'VBtn', template: '<button class="v-btn-stub"><slot /></button>' },
  'v-chip': { name: 'VChip', template: '<span class="v-chip-stub"><slot /></span>' },
  'v-card': { name: 'VCard', template: '<div class="v-card-stub"><slot /></div>' },
  'v-slide-y-transition': { name: 'VSlideYTransition', template: '<div class="v-slide-stub"><slot /></div>' },
}

function setViewport(width) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: width })
}

function mountPicker(props = {}, width = 1280) {
  setViewport(width)
  return mount(CategoryIconPicker, { props, global: { stubs: globalStubs } })
}

function cellTitles(wrapper) {
  return wrapper.findAll('.icon-cell').map((cell) => cell.attributes('title'))
}

afterEach(() => {
  vi.clearAllMocks()
  delete window.innerWidth
})

describe('CategoryIconPicker 分类图标精选网格选择面板', () => {
  // ---------- 4.2.1 activator ----------

  it('用例4.2.1: activator 显示当前 modelValue 的图标名与预览图标', () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })

    const activator = wrapper.find('.icon-activator')
    expect(activator.exists()).toBe(true)
    expect(activator.text()).toContain('mdi-food')
    expect(activator.find('.v-avatar-stub').exists()).toBe(true)
    expect(activator.find('.v-icon-stub').text()).toBe('mdi-food')
    expect(activator.text()).toContain('选择图标')
    // 精选集内图标不带「不在精选集」提示
    expect(activator.text()).not.toContain('不在精选集')
  })

  it('用例4.2.1b: modelValue 为空时 activator 回退展示表单默认图标 mdi-cash', () => {
    const wrapper = mountPicker({ modelValue: '' })
    expect(wrapper.find('.icon-activator__name').text()).toBe('mdi-cash')
    expect(wrapper.find('.icon-activator').text()).not.toContain('不在精选集')
  })

  it('用例4.2.1c: activator 为只读展示，不存在任何图标名文本输入框', () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  // ---------- 4.2.2 宽屏展开网格 ----------

  it('用例4.2.2: 宽屏点击 activator 展开网格，条目数等于 CATEGORY_ICONS 长度', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 1280)

    expect(wrapper.find('.icon-grid').exists()).toBe(false)
    await wrapper.find('.icon-activator').trigger('click')

    const grid = wrapper.find('.icon-grid')
    expect(grid.exists()).toBe(true)
    expect(wrapper.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
    expect(cellTitles(wrapper)).toEqual(CATEGORY_ICONS)
    // 宽屏走内联展开区，不开全屏浮层
    expect(wrapper.find('.icon-panel').exists()).toBe(true)
    expect(wrapper.find('.v-dialog__content').exists()).toBe(false)
    // 滚动容器与网格样式类名齐备（max-height 240px 口径由 CSS 承载）
    expect(wrapper.find('.icon-grid-scroll').exists()).toBe(true)
  })

  it('用例4.2.2b: 再次点击 activator 收起网格', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 1280)
    await wrapper.find('.icon-activator').trigger('click')
    expect(wrapper.find('.icon-grid').exists()).toBe(true)

    await wrapper.find('.icon-activator').trigger('click')
    expect(wrapper.find('.icon-grid').exists()).toBe(false)
  })

  // ---------- 4.2.3 点选即回填 + 选中高亮 ----------

  it('用例4.2.3: 点选第 n 项 emit 对应图标名，选中项带高亮类', async () => {
    const target = CATEGORY_ICONS[41]
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 1280)
    await wrapper.find('.icon-activator').trigger('click')

    await wrapper.findAll('.icon-cell')[41].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([target])
    // 单段式：无「确定」按钮，点选即回抛，面板不自行关闭
    expect(wrapper.text()).not.toContain('确定')
    expect(wrapper.find('.icon-grid').exists()).toBe(true)

    // 回填后（父级 v-model 生效）选中项带高亮类，且原选中项高亮消失
    await wrapper.setProps({ modelValue: target })
    const selected = wrapper.findAll('.icon-cell--selected')
    expect(selected).toHaveLength(1)
    expect(selected[0].attributes('title')).toBe(target)
  })

  it('用例4.2.3b: 当前 modelValue 在展开时即为选中态（预设图标可选中）', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-bag-suitcase' }, 1280)
    await wrapper.find('.icon-activator').trigger('click')

    const selected = wrapper.findAll('.icon-cell--selected')
    expect(selected).toHaveLength(1)
    expect(selected[0].attributes('title')).toBe('mdi-bag-suitcase')
  })

  // ---------- 4.2.4 收起 ----------

  it('用例4.2.4: 展开区「收起」按钮关闭网格回到表单', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 1280)
    await wrapper.find('.icon-activator').trigger('click')
    expect(wrapper.find('.icon-grid').exists()).toBe(true)

    const collapse = wrapper.findAll('.icon-panel .v-btn-stub').find((btn) => btn.text() === '收起')
    expect(collapse).toBeTruthy()
    await collapse.trigger('click')
    await nextTick()

    expect(wrapper.find('.icon-grid').exists()).toBe(false)
    expect(wrapper.find('.icon-panel').exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  // ---------- 4.2.5 存量非选集图标兼容 ----------

  it('用例4.2.5: modelValue 为非选集图标时显示「不在精选集」提示且网格无选中项', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-abacus' }, 1280)

    const activator = wrapper.find('.icon-activator')
    expect(activator.text()).toContain('mdi-abacus')
    expect(activator.text()).toContain('不在精选集，编辑需改选')
    // 照常渲染该图标（字体全量），不阻断表单
    expect(activator.find('.v-icon-stub').text()).toBe('mdi-abacus')

    await activator.trigger('click')
    expect(wrapper.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
    expect(wrapper.findAll('.icon-cell--selected')).toHaveLength(0)
  })

  // ---------- D6 窄屏全屏浮层分支 ----------

  it('用例4.2.6: 窄屏（<600px）点击 activator 打开全屏浮层，内部复用同一网格', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 375)

    await wrapper.find('.icon-activator').trigger('click')
    const dialog = wrapper.find('.v-dialog-stub')
    expect(dialog.exists()).toBe(true)
    expect(dialog.attributes('data-fullscreen')).toBe('true')

    const content = wrapper.find('.v-dialog__content')
    expect(content.exists()).toBe(true)
    expect(content.text()).toContain('选择图标')
    expect(content.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
    expect(content.find('.icon-cell--selected').attributes('title')).toBe('mdi-food')
    // 窄屏不再走内联展开区
    expect(wrapper.find('.icon-panel').exists()).toBe(false)

    // 顶栏「完成」关闭浮层
    const done = content.findAll('.v-btn-stub').find((btn) => btn.text() === '完成')
    await done.trigger('click')
    await nextTick()
    expect(wrapper.find('.v-dialog__content').exists()).toBe(false)
  })

  it('用例4.2.6b: 窄屏浮层点选即时 emit，「收起」同样关闭浮层', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 375)
    await wrapper.find('.icon-activator').trigger('click')

    await wrapper.find('.v-dialog__content').findAll('.icon-cell')[3].trigger('click')
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([CATEGORY_ICONS[3]])

    const collapse = wrapper
      .findAll('.v-dialog__content .v-btn-stub')
      .find((btn) => btn.text() === '收起')
    await collapse.trigger('click')
    await nextTick()
    expect(wrapper.find('.v-dialog__content').exists()).toBe(false)
  })

  it('用例4.2.6c: 视口宽度跨越 600px 时分支随 resize 切换', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 375)
    await wrapper.find('.icon-activator').trigger('click')
    expect(wrapper.find('.v-dialog__content').exists()).toBe(true)

    setViewport(1000)
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(wrapper.find('.v-dialog__content').exists()).toBe(false)
    expect(wrapper.find('.icon-panel').exists()).toBe(true)
    expect(wrapper.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
  })
})
