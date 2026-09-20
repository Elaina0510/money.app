import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import CategoryIconPicker from './CategoryIconPicker.vue'
import AppDialog from './AppDialog.vue'
import { CATEGORY_ICONS } from '@/constants/categoryIcons'
// v1.4.3 M13：jsdom 无布局引擎 → 居中弹窗结构/尺寸口径走仓库既定的 ?raw 源码断言（§1.2）
import pickerSource from './CategoryIconPicker.vue?raw'
// 对外签名不变的落地前提：唯一调用方（新增/编辑分类表单）零改动
import categoriesPageSource from '@/pages/SettingsCategoriesPage.vue?raw'

// ── Vuetify 组件桩：只关心受控行为与 DOM 结构，不引入真实 Vuetify 实例 ──
// 关键：**不声明 fullscreen 这个 prop** —— 若组件误传 fullscreen，
// 它会以透传属性形态落到桩根节点上，用例 4.1 即可断言其不存在。
const VDialogStub = {
  name: 'VDialog',
  props: { modelValue: Boolean, maxWidth: String, transition: String },
  emits: ['update:modelValue', 'after:leave'],
  template:
    '<div class="v-dialog-stub">' + '<div v-if="modelValue" class="v-dialog__content"><slot /></div></div>',
}

const globalStubs = {
  'v-dialog': VDialogStub,
  VDialog: VDialogStub,
  'v-avatar': {
    name: 'VAvatar',
    props: ['size'],
    template: '<div class="v-avatar-stub" :data-size="String(size)"><slot /></div>',
  },
  'v-icon': { name: 'VIcon', props: ['size'], template: '<i class="v-icon-stub"><slot /></i>' },
  'v-btn': { name: 'VBtn', template: '<button class="v-btn-stub"><slot /></button>' },
  'v-chip': { name: 'VChip', template: '<span class="v-chip-stub"><slot /></span>' },
  'v-card': { name: 'VCard', template: '<div class="v-card-stub"><slot /></div>' },
}

// v1.4.3 M14：AppDialog 统一壳下「关闭」先播反向收缩、播完才真正卸载画面
// （收起时长走 --expand-duration 口径，jsdom 无全局样式时回落 EXPAND_DURATION=220ms）。
// 断言「已关闭」需等收起动画播完，意图与原「即时卸载」锁一致、不放宽。
async function settleCollapse(wrapper) {
  await new Promise((resolve) => setTimeout(resolve, 320))
  await wrapper.vm.$nextTick()
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

// 居中弹窗唯一一份：桩组件（含嵌套层级）在整个组件树里只应出现一次
function dialogStub(wrapper) {
  return wrapper.find('.v-dialog-stub')
}

function dialogContent(wrapper) {
  return wrapper.find('.v-dialog__content')
}

// 按文案取弹窗底部的「完成」按钮
function doneButton(wrapper) {
  return dialogContent(wrapper)
    .findAll('.icon-dialog__foot .v-btn-stub')
    .find((btn) => btn.text() === '完成')
}

beforeEach(() => {
  // M14：AppDialog 的触发点来源是 appStore.lastClickOrigin → 挂载需活动 Pinia
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.clearAllMocks()
  delete window.innerWidth
})

describe('CategoryIconPicker 分类图标选择独立居中弹窗（M13 重写）', () => {
  // ---------- activator 形态沿用（任务 2.4：保持现状） ----------

  it('用例4.2.1(沿用): activator 显示当前 modelValue 的图标名与预览图标', () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })

    const activator = wrapper.find('.icon-activator')
    expect(activator.exists()).toBe(true)
    expect(activator.text()).toContain('mdi-food')
    expect(activator.find('.v-avatar-stub').exists()).toBe(true)
    expect(activator.find('.v-icon-stub').text()).toBe('mdi-food')
    expect(activator.text()).toContain('▾ 选择图标')
    // 精选集内图标不带「不在精选集」提示
    expect(activator.text()).not.toContain('不在精选集')
    // 弹窗语义（M13 后 activator 是 dialog 的触发器）
    expect(activator.attributes('role')).toBe('button')
    expect(activator.attributes('aria-haspopup')).toBe('dialog')
    expect(activator.attributes('aria-expanded')).toBe('false')
  })

  it('用例4.2.1b(沿用): modelValue 为空时 activator 回退展示表单默认图标 mdi-cash', () => {
    const wrapper = mountPicker({ modelValue: '' })
    expect(wrapper.find('.icon-activator__name').text()).toBe('mdi-cash')
    expect(wrapper.find('.icon-activator').text()).not.toContain('不在精选集')
  })

  it('用例4.2.1c(沿用): activator 为只读展示，不存在任何图标名文本输入框', () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('未打开时不渲染弹窗体（activator 自身即当前选中的实时预览，任务 3.2）', () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })
    expect(dialogContent(wrapper).exists()).toBe(false)
    expect(wrapper.findAll('.icon-cell')).toHaveLength(0)
  })

  // ---------- 任务 4.1：点 activator → 居中弹窗 + 全量条目 ----------

  it('用例4.1: 点击 activator → 渲染唯一居中弹窗，条目数 = CATEGORY_ICONS.length', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })

    await wrapper.find('.icon-activator').trigger('click')
    await nextTick()

    const stub = dialogStub(wrapper)
    expect(stub.exists()).toBe(true)
    expect(wrapper.findAll('.v-dialog-stub')).toHaveLength(1)
    // 居中非全屏：fullscreen 既未声明为 prop，也未以透传属性落到 DOM
    expect(stub.attributes('fullscreen')).toBeUndefined()
    expect(wrapper.find('.icon-dialog').exists()).toBe(true)

    const content = dialogContent(wrapper)
    expect(content.exists()).toBe(true)
    expect(content.text()).toContain('选择图标')
    expect(content.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
    expect(cellTitles(wrapper)).toEqual(CATEGORY_ICONS)

    // 顶部标题 + 当前选中大预览（48px + 图标名）
    expect(content.find('.icon-dialog__preview-name').text()).toBe('mdi-food')
    expect(content.find('.icon-dialog__preview .v-avatar-stub').attributes('data-size')).toBe('48')
    // 底部「完成」+ 头部 ✕ 关闭
    expect(doneButton(wrapper)).toBeTruthy()
    expect(content.find('.icon-dialog__close').exists()).toBe(true)

    // 尺寸口径（设计 §13.2 裁定值 92vw，非需求示例 90vw）
    const dialog = wrapper.findComponent({ name: 'VDialog' })
    expect(dialog.props('maxWidth')).toBe('min(560px, 92vw)')
    // M14 收编（任务 6.7）：外壳换成 AppDialog → v-dialog 自带位移关掉（null），
    // 展开动画由 AppDialog 的原点缩放机制接管（.app-dialog__content 上有内联 transform）
    expect(dialog.props('transition')).toBeNull()
    expect(wrapper.find('.app-dialog__content').exists()).toBe(true)
    expect(dialog.props('modelValue')).toBe(true)
    expect(wrapper.find('.icon-activator').attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.icon-activator').classes()).toContain('icon-activator--open')
  })

  it('用例3.5: 快速连点 activator 幂等开关，弹窗不叠加', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })

    for (let i = 0; i < 6; i += 1) {
      await wrapper.find('.icon-activator').trigger('click')
      await nextTick()
      expect(wrapper.findAll('.v-dialog-stub')).toHaveLength(1)
      // 偶数次点击落在展开态、奇数次落在「反向收缩」进行中（M14：收起播完才卸载），始终只有一份弹窗
      const style = wrapper.find('.app-dialog__content').attributes('style') || ''
      expect(style).toContain(i % 2 === 0 ? 'transform: scale(1)' : 'transform: scale(0)')
    }
    expect(wrapper.find('.icon-activator').classes()).not.toContain('icon-activator--open')
    // 收起动画播完 → 画面真正卸载（重开取消收起机制见 AppDialog/ExpandTransition 用例）
    await settleCollapse(wrapper)
    expect(dialogContent(wrapper).exists()).toBe(false)

    // 遮罩/ESC 的重复关闭信号同样幂等（受控 modelValue，状态不倒挂）
    await wrapper.find('.icon-activator').trigger('click')
    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('update:modelValue', false)
    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('update:modelValue', false)
    await settleCollapse(wrapper)
    expect(dialogContent(wrapper).exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  // ---------- 任务 4.2：点选即回填 + 高亮 + 预览跟新；「完成」仅关闭 ----------

  it('用例4.2: 点选第 n 项 → emit 对应图标名、选中类切换、顶部预览更新、弹窗不自动关', async () => {
    const target = CATEGORY_ICONS[41]
    const wrapper = mountPicker({ modelValue: 'mdi-food' })
    await wrapper.find('.icon-activator').trigger('click')

    await wrapper.findAll('.icon-cell')[41].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[target]])
    // 单段式：点选不关弹窗（可连续改选），也无「确定」二段
    expect(dialogContent(wrapper).exists()).toBe(true)
    expect(dialogContent(wrapper).text()).not.toContain('确定')

    // 父级 v-model 生效 → 高亮描边换到 newly picked、原高亮消失、预览跟新
    await wrapper.setProps({ modelValue: target })
    const selected = wrapper.findAll('.icon-cell--selected')
    expect(selected).toHaveLength(1)
    expect(selected[0].attributes('title')).toBe(target)
    expect(dialogContent(wrapper).find('.icon-dialog__preview-name').text()).toBe(target)

    // 再一次点选：继续即时回抛，无弹窗内二次确认
    await wrapper.findAll('.icon-cell')[3].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[target], [CATEGORY_ICONS[3]]])
  })

  it('用例4.2b: 「完成」只关闭、不再 emit（点选已即时回抛）', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })
    await wrapper.find('.icon-activator').trigger('click')
    await wrapper.findAll('.icon-cell')[7].trigger('click')
    await wrapper.setProps({ modelValue: CATEGORY_ICONS[7] }) // 模拟父级 v-model 落地
    const emitsBefore = wrapper.emitted('update:modelValue').length

    await doneButton(wrapper).trigger('click')
    await settleCollapse(wrapper)

    expect(dialogContent(wrapper).exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toHaveLength(emitsBefore)
    expect(wrapper.find('.icon-activator__name').text()).toBe(CATEGORY_ICONS[7])
  })

  it('用例4.2c: 头部 ✕ 关闭不 emit；关闭后表单预览即所选图标（任务 3.2）', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 375)
    await wrapper.find('.icon-activator').trigger('click')
    await wrapper.setProps({ modelValue: CATEGORY_ICONS[12] })

    await wrapper.find('.icon-dialog__close').trigger('click')
    await settleCollapse(wrapper)

    expect(dialogContent(wrapper).exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    expect(wrapper.find('.icon-activator__name').text()).toBe(CATEGORY_ICONS[12])
    expect(wrapper.find('.icon-activator').classes()).not.toContain('icon-activator--open')
  })

  it('用例4.2d: 遮罩/ESC（dialog 自身回抛 false）→ 同步关闭且不 emit', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' })
    await wrapper.find('.icon-activator').trigger('click')

    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('update:modelValue', false)
    await settleCollapse(wrapper)

    expect(dialogContent(wrapper).exists()).toBe(false)
    expect(wrapper.find('.icon-activator').classes()).not.toContain('icon-activator--open')
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  it('用例4.2e: 打开时当前 modelValue 即为选中态（预设图标可选中）', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-bag-suitcase' })
    await wrapper.find('.icon-activator').trigger('click')

    const selected = wrapper.findAll('.icon-cell--selected')
    expect(selected).toHaveLength(1)
    expect(selected[0].attributes('title')).toBe('mdi-bag-suitcase')
  })

  // ---------- 任务 4.3：宽 / 窄两档同一居中弹窗（双分支已删） ----------

  it('用例4.3: 宽屏 1280 与窄屏 375 渲染同一条居中路径，内联展开区零命中', async () => {
    for (const width of [1280, 960, 375, 320]) {
      const wrapper = mountPicker({ modelValue: 'mdi-food' }, width)
      await wrapper.find('.icon-activator').trigger('click')

      const stub = dialogStub(wrapper)
      expect(stub.exists()).toBe(true)
      expect(stub.attributes('fullscreen')).toBeUndefined()
      expect(wrapper.findComponent({ name: 'VDialog' }).props('maxWidth')).toBe('min(560px, 92vw)')
      // 网格只在弹窗内，不再有表单下方内联展开区（旧 .icon-panel 分支）
      expect(wrapper.find('.icon-panel').exists()).toBe(false)
      expect(wrapper.findAll('.icon-grid')).toHaveLength(1)
      expect(dialogContent(wrapper).find('.icon-grid').exists()).toBe(true)
      expect(wrapper.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
      wrapper.unmount()
    }
  })

  it('用例4.3b: 视口变化不再切换分支（resize 监听已删）', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 375)
    await wrapper.find('.icon-activator').trigger('click')
    expect(dialogContent(wrapper).exists()).toBe(true)

    setViewport(1440)
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    // 同一弹窗仍开着、仍是居中路径，未冒出内联展开区
    expect(dialogContent(wrapper).exists()).toBe(true)
    expect(wrapper.find('.icon-panel').exists()).toBe(false)
    expect(wrapper.findAll('.v-dialog-stub')).toHaveLength(1)
    // M14 收编后：外壳统一走 AppDialog（v-dialog 自带位移关掉），不再有底部上浮过渡
    expect(wrapper.findComponent({ name: 'VDialog' }).props('transition')).toBeNull()
    expect(wrapper.findComponent(AppDialog).exists()).toBe(true)
  })

  // ---------- 任务 4.4：非精选集（存量图标）行为回归 ----------

  it('用例4.4: 非选集 modelValue → 提示 chip 保留、网格无选中项、预览显示原图标、选新即覆盖', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-abacus' })

    const activator = wrapper.find('.icon-activator')
    expect(activator.text()).toContain('mdi-abacus')
    expect(activator.text()).toContain('不在精选集，编辑需改选')
    // 照常渲染该图标（字体全量），不阻断表单
    expect(activator.find('.v-icon-stub').text()).toBe('mdi-abacus')

    await activator.trigger('click')
    expect(wrapper.findAll('.icon-cell')).toHaveLength(CATEGORY_ICONS.length)
    expect(wrapper.findAll('.icon-cell--selected')).toHaveLength(0)
    // 弹窗顶部预览显示原图标（无强制迁移，沿 v1.4.2 D6 语义）
    expect(dialogContent(wrapper).find('.icon-dialog__preview-name').text()).toBe('mdi-abacus')

    // 选新图标即覆盖：chip 随之消失、无选中项落到新图标
    await wrapper.setProps({ modelValue: CATEGORY_ICONS[5] })
    expect(wrapper.find('.v-chip-stub').exists()).toBe(false)
    const selected = wrapper.findAll('.icon-cell--selected')
    expect(selected).toHaveLength(1)
    expect(selected[0].attributes('title')).toBe(CATEGORY_ICONS[5])
    expect(dialogContent(wrapper).find('.icon-dialog__preview-name').text()).toBe(CATEGORY_ICONS[5])
  })

  // ---------- 任务 3.3：关闭回焦 activator ----------

  it('用例3.3: dialog after:leave → 回焦 activator（需求 13.3 关后回表单继续编辑）', async () => {
    const wrapper = mountPicker({ modelValue: 'mdi-food' }, 375)
    const focusSpy = vi.spyOn(wrapper.find('.icon-activator').element, 'focus')

    await wrapper.find('.icon-activator').trigger('click')
    expect(dialogContent(wrapper).exists()).toBe(true)
    expect(focusSpy).not.toHaveBeenCalled()

    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('after:leave')
    await nextTick()
    expect(focusSpy).toHaveBeenCalledTimes(1)

    // 「完成」关闭路径：先置 open=false（原点反向收缩开始），动画结束的 after:leave 才回焦
    focusSpy.mockClear()
    await doneButton(wrapper).trigger('click')
    await settleCollapse(wrapper)
    expect(dialogContent(wrapper).exists()).toBe(false)
    expect(focusSpy).not.toHaveBeenCalled()
    wrapper.findComponent({ name: 'VDialog' }).vm.$emit('after:leave')
    expect(focusSpy).toHaveBeenCalledTimes(1)
    focusSpy.mockRestore()
  })

  it('用例3.2: 挂在真实 v-model 表单里 → 点选即回显到表单，关闭不覆盖所选', async () => {
    const Host = {
      components: { CategoryIconPicker },
      data: () => ({ icon: 'mdi-cash' }),
      template: '<div class="host"><CategoryIconPicker v-model="icon" /></div>',
    }
    const wrapper = mount(Host, { global: { stubs: globalStubs } })
    await wrapper.find('.icon-activator').trigger('click')

    await wrapper.findAll('.icon-cell')[2].trigger('click')
    expect(wrapper.vm.icon).toBe(CATEGORY_ICONS[2])
    expect(wrapper.find('.icon-activator__name').text()).toBe(CATEGORY_ICONS[2])
    expect(wrapper.find('.icon-dialog__preview-name').text()).toBe(CATEGORY_ICONS[2])

    await doneButton(wrapper).trigger('click')
    await settleCollapse(wrapper)
    expect(wrapper.find('.v-dialog__content').exists()).toBe(false)
    expect(wrapper.vm.icon).toBe(CATEGORY_ICONS[2])
  })

  // ---------- 任务 4.5 + 结构口径（?raw 源码断言） ----------

  it('用例4.5: 源码不含 fullscreen / 写死带高，也不含窄屏分支三件套', () => {
    expect(pickerSource).not.toContain('max-height: 240px')
    expect(pickerSource).not.toContain('240px')
    expect(pickerSource).not.toContain('fullscreen')
    // 任务 1.1：删窄屏判定与 resize 监听
    expect(pickerSource).not.toMatch(/\bisNarrow\b/)
    expect(pickerSource).not.toMatch(/NARROW_BREAKPOINT/)
    expect(pickerSource).not.toMatch(/addEventListener\(['"]resize/)
    // 任务 1.2：内联展开分支已删（组件内不再出现 .icon-panel 类与其样式）
    expect(pickerSource).not.toMatch(/icon-panel/)
    expect(pickerSource).not.toMatch(/v-slide-y-transition/)
  })

  it('用例2.x: 居中弹窗尺寸与网格口径落源码（min(560px,92vw) / 80vh / flex:1+min-height:0 / auto-fill 44px / gap 8px）', () => {
    const styleBlock = pickerSource.slice(pickerSource.indexOf('<style scoped>'))

    // 2.1 非全屏 dialog + 裁定宽度值 + 卡片 80vh 上限
    expect(pickerSource).toMatch(/max-width="min\(560px, 92vw\)"/)
    // M14（任务 6.7）：过渡收编为 AppDialog 原点展开，组件内不再自带 dialog 位移过渡
    expect(pickerSource).toMatch(/<AppDialog\b/)
    expect(pickerSource).toMatch(/@after:leave="onAfterLeave"/)
    expect(pickerSource).not.toMatch(/dialog-bottom-transition/)
    expect(pickerSource).not.toMatch(/<v-dialog/)
    expect(styleBlock).toMatch(/\.icon-dialog\s*\{[^}]*max-height:\s*80vh/)
    // 2.2 弹窗体列向 flex
    expect(styleBlock).toMatch(/\.icon-dialog\s*\{[^}]*display:\s*flex;[^}]*flex-direction:\s*column/)
    // 2.3 滚动区撑满可用高度（废除写死带高）
    expect(styleBlock).toMatch(/\.icon-grid-scroll\s*\{[^}]*flex:\s*1;[^}]*min-height:\s*0;[^}]*overflow-y:\s*auto/)
    expect(styleBlock).toMatch(
      /grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(44px,\s*1fr\)\)/,
    )
    expect(styleBlock).toMatch(/\.icon-grid\s*\{[^}]*gap:\s*8px/)
    expect(styleBlock).toMatch(/\.icon-cell\s*\{[^}]*aspect-ratio:\s*1\s*\/\s*1/)
    // 3.1 选中高亮描边样式沿用 v1.4.2
    expect(styleBlock).toMatch(
      /\.icon-cell--selected\s*\{[^}]*outline:\s*2px solid rgb\(var\(--v-theme-primary\)\)/,
    )
    // 3.3 回焦绑定
    expect(pickerSource).toMatch(/@after:leave="onAfterLeave"/)
    expect(pickerSource).toMatch(/activatorRef\.value\?\.focus\(\)/)
  })

  it('对外 props/emits 签名冻结（modelValue + update:modelValue），调用方零改动', () => {
    expect(Object.keys(CategoryIconPicker.props)).toEqual(['modelValue'])
    // M13 未新增任何对外 prop / emit（无 visible、无场景分叉），两处调用方形态原样
    const propsBlock = pickerSource.match(/const props = defineProps\(\{[\s\S]*?\n\}\)/)[0]
    expect(propsBlock.match(/^\s{2}(\w+):/gm)).toEqual(['  modelValue:'])
    expect(pickerSource).toMatch(/defineEmits\(\['update:modelValue'\]\)/)
    // 唯一调用方仍是裸 v-model，形态与 v1.4.2 一致（本模块不改调用方）
    expect(categoriesPageSource).toMatch(/<CategoryIconPicker v-model="categoryForm\.icon" \/>/)
  })
})
