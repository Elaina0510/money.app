import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// Mock child components: render activator always, dialog content only when open.
// v1.4.3 M4：mock 与真实 ExpandTransition 同构（内部 show 态 + 关闭单回声）——
// 父级置 false（「完成」）与遮罩/ESC（真实组件在此拦截归一）都播完收起动画后
// 回抛**一次** `update:modelValue false`；M4 的关闭回写就挂在这个回声上。
vi.mock('./ExpandTransition.vue', async () => {
  const { ref, watch } = await import('vue')
  return {
    default: {
      name: 'ExpandTransition',
      props: ['modelValue', 'origin', 'maxWidth'],
      emits: ['update:modelValue'],
      setup(props, { emit }) {
        const show = ref(props.modelValue)
        watch(
          () => props.modelValue,
          (val) => {
            if (val) show.value = true
            else if (show.value) collapse() // 程序化关闭：播完收起动画再真正关
          }
        )
        watch(show, (val) => emit('update:modelValue', val))
        function collapse() {
          show.value = false // jsdom 无动画 → 收起即完成
        }
        // 遮罩点击 / ESC：真实组件拦截 v-dialog 的关闭并归一为同一条路径
        function dialogRequestClose(val) {
          if (!val && show.value) collapse()
        }
        return { show, dialogRequestClose }
      },
      template:
        '<div class="expand-transition-mock">' +
        '<slot name="activator" :props="{}" />' +
        '<div v-if="show" class="expand-transition-content"><slot /></div>' +
        '</div>',
    },
  }
})

import DatePickerPopover from './DatePickerPopover.vue'
// jsdom 无布局、scoped 样式不落 DOM → D6/结构类断言走仓库既定的 ?raw 源码口径
import popoverSource from './DatePickerPopover.vue?raw'
// 红线 6 / 任务 2.7·3.1：两处调用点与账单页 300ms 防抖 watch 零改动——只读源码上锁，不改调用方
import recordListSource from '@/pages/RecordListPage.vue?raw'
import recordFormSource from '@/pages/RecordFormPage.vue?raw'
// 任务 5.2：main.js locale 注册段
import mainSource from '@/main.js?raw'

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

async function openDatePopover(wrapper, clientX = 100, clientY = 200) {
  const block = transitionWrappers(wrapper)[0]
  await block.find('.v-text-field-stub').trigger('click', { clientX, clientY })
  return block
}

// 模拟在日历里点选一天：Vuetify 3.12 真实回传 JS Date 对象
async function clickDay(block, year, month, day) {
  block.findComponent({ name: 'VDatePicker' }).vm.$emit('update:modelValue', new Date(year, month - 1, day))
  await nextTick()
}

// 模拟遮罩点击 / ESC：dialog 自身关闭 → ExpandTransition 拦截归一 → 收起动画播完回抛 false
async function emitDialogClosed(block) {
  block.vm.dialogRequestClose(false)
  await nextTick()
}

function displayRow(block) {
  return block.find('.selected-date-display')
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

  it('should have closeAndCommit method（M4 关闭回写单出口）', () => {
    const wrapper = mountPopover()
    expect(typeof wrapper.vm.closeAndCommit).toBe('function')
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

  // 任务 2.6：时间弹层保持「取消/确定」语义，本用例不改
  it('should emit update:modelValueTime on time confirm', async () => {
    const wrapper = mountPopover({ showTime: true })

    wrapper.vm.pendingTime = '14:30'
    wrapper.vm.confirmTime()
    await nextTick()

    expect(wrapper.emitted('update:modelValueTime')).toBeTruthy()
    expect(wrapper.emitted('update:modelValueTime')[0]).toEqual(['14:30'])
  })

  // 改写（原「should emit update:modelValue on date selection」）：
  // M4 口径反转——点选只写内部态 picked，不再即时 emit（回写延后到弹窗关闭时）
  it('点选仅写内部态 picked，不即时 emit（原「选日即 emit」用例改写）', async () => {
    const wrapper = mountPopover()
    await openDatePopover(wrapper)

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    expect(wrapper.vm.picked).toBe('2026-06-06')
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  // 改写（原「normalizes Date object emitted by v-date-picker to YYYY-MM-DD」）：
  // v1.4.1 热修口径原样保留（Date → YYYY-MM-DD 归一），仅回写时机改到关闭时
  it('normalizes Date object to YYYY-MM-DD and commits the normalized value on close', async () => {
    const wrapper = mountPopover()
    const block = await openDatePopover(wrapper)

    wrapper.vm.onDateSelected(new Date(2026, 8, 15))
    await nextTick()
    expect(wrapper.vm.picked).toBe('2026-09-15')
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()

    await emitDialogClosed(block)
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-09-15'])
  })

  // 改写（原「should close picker after date selection」，任务 5.1 点名两处之一）：M4 选后不关
  it('选后不关：点选日期后 dialog 保持打开（原「选后即关」用例改写）', async () => {
    const wrapper = mountPopover()
    const block = await openDatePopover(wrapper)

    await clickDay(block, 2026, 6, 6)

    expect(wrapper.vm.showPicker).toBe(true)
    expect(block.props('modelValue')).toBe(true)
    expect(block.find('.v-date-picker-stub').exists()).toBe(true)
  })

  it('should have displayValue computed', () => {
    const wrapper = mountPopover({ modelValue: '2026-06-06' })
    expect(wrapper.vm.displayValue).toBe('2026-06-06')
  })

  it('should return empty string for displayValue when no modelValue', () => {
    const wrapper = mountPopover()
    expect(wrapper.vm.displayValue).toBe('')
  })

  // ---------- 红线 6：对外签名冻结 ----------

  it('对外 props/emits 签名不变（账单页/记一笔两调用方零改动的前提）', () => {
    expect(Object.keys(DatePickerPopover.props).sort()).toEqual([
      'label',
      'modelValue',
      'modelValueTime',
      'showTime',
    ])
    expect(popoverSource).toMatch(/defineEmits\(\['update:modelValue', 'update:modelValueTime'\]\)/)
    // 不为两场景做 prop 分叉（需求 4.4 全站统一）：无新增场景类 prop
    expect(popoverSource).not.toMatch(/scenario|closeOnSelect/)
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

  // ---------- 用例 4：确定回抛并关闭；取消不回抛（任务 2.6：时间弹层语义不改） ----------

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

  // ---------- M4 任务 5.1：选后不关 + 实时展示行 + 关闭时才回写 ----------

  it('用例5.1-1: 点选日历日 → dialog 不关、不 emit、展示行显示「YYYY年M月D日」', async () => {
    const wrapper = mountPopover({ label: '开始日期' })
    const block = await openDatePopover(wrapper)

    await clickDay(block, 2026, 6, 6)

    // 不关
    expect(block.props('modelValue')).toBe(true)
    expect(block.find('.expand-transition-content').exists()).toBe(true)
    // 不 emit
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    // 展示行随点选即时更新为中文格式
    expect(displayRow(block).exists()).toBe(true)
    expect(displayRow(block).text()).toBe('2026年6月6日')
    // 外部回显（输入框）仍是关闭前的值：关闭时才写入
    expect(wrapper.find('.v-text-field-stub').text()).toBe('')
  })

  it('用例5.1-2: 再点另一日 → 展示行更新；点「完成」→ emit 最终日一次 + dialog 关', async () => {
    const wrapper = mountPopover({ label: '开始日期' })
    const block = await openDatePopover(wrapper)

    await clickDay(block, 2026, 6, 6)
    expect(displayRow(block).text()).toBe('2026年6月6日')

    await clickDay(block, 2026, 6, 20)
    expect(displayRow(block).text()).toBe('2026年6月20日')
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()

    const done = block.findAll('.v-btn-stub')
    expect(done.length).toBe(1)
    expect(done[0].text()).toBe('完成')
    await done[0].trigger('click')
    await flushPromises()

    // 一次关闭只回写一次，且回写的是最后一次点选
    expect(wrapper.emitted('update:modelValue')).toEqual([['2026-06-20']])
    expect(wrapper.vm.showPicker).toBe(false)
    expect(block.props('modelValue')).toBe(false)
    expect(block.find('.v-date-picker-stub').exists()).toBe(false)
  })

  it('用例5.1-3: 模拟遮罩关闭路径 → 同样回写最终值', async () => {
    const wrapper = mountPopover({ modelValue: '2026-06-01', label: '开始日期' })
    const block = await openDatePopover(wrapper)

    // 打开时与外部值同步
    expect(wrapper.vm.picked).toBe('2026-06-01')
    expect(displayRow(block).text()).toBe('2026年6月1日')

    await clickDay(block, 2026, 7, 3)
    expect(displayRow(block).text()).toBe('2026年7月3日')

    await emitDialogClosed(block)

    expect(wrapper.emitted('update:modelValue')).toEqual([['2026-07-03']])
    expect(wrapper.vm.showPicker).toBe(false)
    expect(block.props('modelValue')).toBe(false)
  })

  it('用例5.1-3b: ESC 关闭路径与遮罩同源（ExpandTransition 拦截归一）→ 回写最终值', async () => {
    const wrapper = mountPopover({ label: '结束日期' })
    const block = await openDatePopover(wrapper)

    await clickDay(block, 2026, 8, 8)
    await emitDialogClosed(block)

    expect(wrapper.emitted('update:modelValue')).toEqual([['2026-08-08']])
    expect(wrapper.vm.showPicker).toBe(false)
  })

  it('用例5.1-4: 未选打开 → 展示行「请选择日期」', async () => {
    const wrapper = mountPopover({ label: '开始日期' })
    const block = await openDatePopover(wrapper)

    expect(wrapper.vm.picked).toBe('')
    expect(displayRow(block).text()).toBe('请选择日期')
    await emitDialogClosed(block)
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  it('边界4.1: 打开后未改选直接关（遮罩 / 完成）→ 不 emit、不触发查询', async () => {
    const wrapper = mountPopover({ modelValue: '2026-06-01' })
    const block = await openDatePopover(wrapper)

    await emitDialogClosed(block)
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()

    const wrapper2 = mountPopover({ modelValue: '2026-06-01' })
    const block2 = await openDatePopover(wrapper2)
    await block2.findAll('.v-btn-stub')[0].trigger('click') // 完成
    await flushPromises()
    expect(wrapper2.emitted('update:modelValue')).toBeFalsy()
    expect(wrapper2.vm.showPicker).toBe(false)
  })

  it('边界4.2: 连续改选多日 → 展示行实时跟新，仅最后一次点选被回写一次', async () => {
    const wrapper = mountPopover({ label: '开始日期' })
    const block = await openDatePopover(wrapper)

    await clickDay(block, 2026, 6, 1)
    expect(displayRow(block).text()).toBe('2026年6月1日')
    await clickDay(block, 2026, 6, 2)
    expect(displayRow(block).text()).toBe('2026年6月2日')
    await clickDay(block, 2026, 6, 3)
    expect(displayRow(block).text()).toBe('2026年6月3日')

    await emitDialogClosed(block)
    expect(wrapper.emitted('update:modelValue')).toEqual([['2026-06-03']])
  })

  it('边界4.3: 开始/结束两弹窗并排 → 各自独立实例、行为一致（需求 4.5）', async () => {
    const Parent = {
      components: { DatePickerPopover },
      data: () => ({ start: '', end: '' }),
      template:
        '<div class="two-filters">' +
        '<DatePickerPopover v-model="start" label="开始日期" />' +
        '<DatePickerPopover v-model="end" label="结束日期" />' +
        '</div>',
    }
    const wrapper = mount(Parent, { global: { stubs: globalStubs } })
    await flushPromises()

    expect(wrapper.findAllComponents(DatePickerPopover)).toHaveLength(2)
    const blocks = transitionWrappers(wrapper)

    const first = blocks[0]
    await first.find('.v-text-field-stub').trigger('click', { clientX: 1, clientY: 1 })
    await clickDay(first, 2026, 6, 6)

    const second = blocks[1]
    await second.find('.v-text-field-stub').trigger('click', { clientX: 2, clientY: 2 })
    await clickDay(second, 2026, 7, 7)

    // 两实例互不污染
    expect(displayRow(first).text()).toBe('2026年6月6日')
    expect(displayRow(second).text()).toBe('2026年7月7日')

    await emitDialogClosed(first)
    await emitDialogClosed(second)
    await nextTick()
    expect(wrapper.vm.start).toBe('2026-06-06')
    expect(wrapper.vm.end).toBe('2026-07-07')

    // 关闭后重复的关闭信号不再二次回写（picked 已与外部值相等）
    await emitDialogClosed(first)
    expect(wrapper.vm.start).toBe('2026-06-06')
  })

  it('边界2.8: 重开时 picked 与外部值重同步（收起动画期间未回写的点选不带出）', async () => {
    const wrapper = mountPopover({ modelValue: '2026-06-01' })
    const block = await openDatePopover(wrapper)

    await clickDay(block, 2026, 6, 6) // 改了但尚未回写
    // 再次点击 activator（重开）→ picked 重同步为外部值
    await block.find('.v-text-field-stub').trigger('click', { clientX: 5, clientY: 6 })

    expect(wrapper.vm.showPicker).toBe(true)
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    expect(wrapper.vm.picked).toBe('2026-06-01')
    expect(displayRow(block).text()).toBe('2026年6月1日')
  })

  // ---------- D6 / 结构（?raw 源码断言） ----------

  it('D6: 隐藏内置 header + 自绘只读实时展示行 + 单个「完成」按钮（源码结构断言）', () => {
    // header 行为内置文本区、非可编辑输入框 → 隐藏，月份翻页在 controls 行，不受影响
    expect(popoverSource).toMatch(/:deep\(\.v-date-picker-header\)\s*\{\s*\n?\s*display:\s*none;/)
    // 自绘只读展示行：中文「YYYY年M月D日」/「请选择日期」
    expect(popoverSource).toMatch(/class="selected-date-display"/)
    expect(popoverSource).toMatch(/format\('YYYY年M月D日'\)/)
    expect(popoverSource).toMatch(/return '请选择日期'/)
    // 底部单个「完成」按钮（tonal primary）
    expect(popoverSource).toMatch(
      /<v-card-actions class="pa-3 pt-1">[\s\S]*?<v-btn variant="tonal" color="primary" @click="closePicker">完成<\/v-btn>[\s\S]*?<\/v-card-actions>/
    )
    // 选后不关：onDateSelected 体内只有归一 + 存内部态（无 emit、无关闭）
    const onDateSelectedBody = popoverSource.match(
      /function onDateSelected\(date\) \{[\s\S]*?\n\}/
    )[0]
    expect(onDateSelectedBody).toMatch(/picked\.value = toDateString\(date\)/)
    expect(onDateSelectedBody).not.toMatch(/emit\(/)
    expect(onDateSelectedBody).not.toMatch(/showPicker/)
    // 三路径单出口：回写只挂在 ExpandTransition 的 update:modelValue 处理里
    expect(popoverSource).toMatch(/@update:model-value="closeAndCommit"/)
    expect(popoverSource).toMatch(/function closeAndCommit\(val\) \{/)
    // Date 归一口径（v1.4.1 热修）原样保留
    expect(popoverSource).toMatch(/function toDateString\(d\) \{/)
  })

  it('红线 6：两处调用点与账单页 300ms 防抖 watch 零改动（源码锁）', () => {
    // RecordListPage.vue:12/:15 —— 无场景 prop 分叉（需求 4.4 全站统一）
    expect(recordListSource).toMatch(
      /<DatePickerPopover v-model="filters\.start_date" label="开始日期" \/>/
    )
    expect(recordListSource).toMatch(
      /<DatePickerPopover v-model="filters\.end_date" label="结束日期" \/>/
    )
    expect(recordListSource).not.toMatch(/<DatePickerPopover[^>]*scenario/)
    // 任务 3.1：300ms 防抖 watch 与同参去重原样保留、不引入新机制
    expect(recordListSource).toMatch(/searchDebounceTimer = setTimeout\(\(\) => search\(\), 300\)/)
    expect(recordListSource).toMatch(/if \(!force && key === lastQueryKey\) return/)
    // RecordFormPage.vue:116-121（consumeDate）
    expect(recordFormSource).toMatch(/<DatePickerPopover\s+v-model="consumeDate"/)
  })

  // ---------- 任务 5.2：Vuetify zhHans locale 注册 ----------

  it('main.js 注册 zhHans locale（?raw 源码断言：日历标题/星期/月份等内置文案全中文）', async () => {
    expect(mainSource).toMatch(/import \{ zhHans \} from 'vuetify\/locale'/)
    expect(mainSource).toMatch(/locale: \{/)
    expect(mainSource).toMatch(/locale: 'zhHans'/)
    expect(mainSource).toMatch(/messages: \{ zhHans \}/)
    // 零新增依赖：仅取包内 vuetify/locale，不引外部语言包
    expect(mainSource).not.toMatch(/zh-Hans|vue-i18n/)

    // 任务 1.3 可自动化的部分①：注册进 createVuetify 的那份语言包内置键确为中文
    const { zhHans } = await import('vuetify/locale')
    expect(zhHans.datePicker.title).toBe('选择日期')
    expect(zhHans.datePicker.header).toBe('输入日期') // 旧英文「Enter date」——M4 已由自绘行取代
    expect(zhHans.datePicker.input.placeholder).toBe('输入日期')
    expect(zhHans.datePicker.ariaLabel.previousMonth).toBe('上个月')
    expect(zhHans.datePicker.ariaLabel.nextMonth).toBe('下个月')
    // 站内未用到的含文案组件（v-pagination）注册后天然受益
    expect(zhHans.pagination.ariaLabel.next).toBe('下一页')

    // 任务 1.3 可自动化的部分②：locale 标签可被 Intl 接受，
    // 日历星期/月份名走 Intl 而非翻译键 → 表头不是英文残留
    const probe = new Intl.DateTimeFormat('zhHans', { month: 'long', weekday: 'short' })
    const label = probe.format(new Date(2026, 8, 15))
    expect(label).toMatch(/月/)
    expect(label).not.toMatch(/Sep|Tue/i)
  })

  // ---------- 用例 6（任务 5.1 点名的第二处旧口径用例，改写为新交互） ----------

  it('用例6（改写）: 日期弹层打开带 origin/picked 同步，选后不关，关闭时才回写并收起', async () => {
    const wrapper = mountPopover({ label: '消费日期', modelValue: '2026-05-05' })
    const blocks = transitionWrappers(wrapper)

    await blocks[0].find('.v-text-field-stub').trigger('click', { clientX: 100, clientY: 200 })
    expect(blocks[0].props('modelValue')).toBe(true)
    expect(blocks[0].props('origin')).toEqual({ x: 100, y: 200 })
    expect(blocks[0].find('.v-date-picker-stub').exists()).toBe(true)
    // 打开时 picked 同步外部已选值，日历与展示行同态
    expect(wrapper.vm.picked).toBe('2026-05-05')
    expect(blocks[0].find('.v-date-picker-stub').attributes('data-model-value')).toBe('2026-05-05')
    expect(displayRow(blocks[0]).text()).toBe('2026年5月5日')

    wrapper.vm.onDateSelected('2026-06-06')
    await nextTick()

    // 旧断言「即时回填 + 立即收起」按 M4 口径反转：不 emit、不收起，展示行跟新
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    expect(wrapper.vm.showPicker).toBe(true)
    expect(blocks[0].props('modelValue')).toBe(true)
    expect(displayRow(blocks[0]).text()).toBe('2026年6月6日')

    await emitDialogClosed(blocks[0])
    expect(wrapper.emitted('update:modelValue')).toEqual([['2026-06-06']])
    expect(wrapper.vm.showPicker).toBe(false)
    expect(blocks[0].find('.v-date-picker-stub').exists()).toBe(false)
  })
})
