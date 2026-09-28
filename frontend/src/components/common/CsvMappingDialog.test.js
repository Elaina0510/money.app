import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import CsvMappingDialog from './CsvMappingDialog.vue'
import csvDialogSource from './CsvMappingDialog.vue?raw'

// ─────────────────────────────────────────────────────────────────────────────
// v1.4.4 M3（REQ-006 / REQ-007）组件自带测试——该组件此前无测试文件（设计 §4.3 已核验）。
// 断言口径与 `SettingsSubPages.test.js` 的 boot3 describe 同源：
//   jsdom 不加载 Vuetify → `v-*` 解析成自定义元素，故样式/结构类断言走 `?raw` 源码正则，
//   文本与禁用态走 attribute/element 三型并取。
// 本文件只**新增**，不替换、不放宽既有 boot3 用例（红线：既有测试零删零松）。
// ─────────────────────────────────────────────────────────────────────────────

// 可见分类（与 boot3 夹具同形：预设 + 一条自建 + 链尾「其他」）
const CATEGORIES = [
  { id: 1, name: '餐饮', icon: 'mdi-food', sort_order: 1, is_preset: 1, source: 1 },
  { id: 2, name: '出行', icon: 'mdi-bus', sort_order: 2, is_preset: 1, source: 1 },
  { id: 3, name: '购物', icon: 'mdi-cart', sort_order: 3, is_preset: 0, source: 0 },
  { id: 8, name: '其他', icon: 'mdi-cash-minus', sort_order: 99, is_preset: 1, source: 1 },
]

// 最小可用预览载荷：字段名逐字取设计 §1.2.5 冻结契约；两个必需列（金额 / 时间）就位，
// 使「确认导入」的禁用态在下面的用例里只可能由 M3 的新建名报错引起。
const preview = (overrides = {}) => ({
  cache_id: 'csv-m3-1',
  format: 'cashew_template',
  row_count: 2,
  categories_in_file: ['外卖'],
  categories_suggested: {},
  tags_in_file: [],
  headers: ['Date', 'Amount', 'Category'],
  header_row_index: 0,
  columns: [
    { index: 0, header: 'Date', role: 'consume_time', sample: '2026-09-24 11:07:54' },
    { index: 1, header: 'Amount', role: 'amount', sample: '-50' },
    { index: 2, header: 'Category', role: 'category', sample: '外卖' },
  ],
  suggested_type_source: 'sign',
  encoding: 'utf-8-sig',
  sample_rows: [['2026-09-24 11:07:54', '-50', '外卖']],
  warnings: [],
  container: 'csv',
  ...overrides,
})

const mountDialog = async (previewData, categories = CATEGORIES) => {
  const wrapper = mount(CsvMappingDialog, {
    props: { modelValue: true, previewData, categories },
  })
  await flushPromises()
  return wrapper
}

const flat = (wrapper) => wrapper.text().replace(/\s+/g, '')
const confirmBtn = (wrapper) => wrapper.findAll('v-btn').find((node) => node.text() === '确认导入')
// 桩环境下 Vue 把 :disabled 落自定义元素成 attribute（含字符串 'false'）→ 三型并取
const confirmDisabled = (wrapper) => {
  const btn = confirmBtn(wrapper)
  expect(btn, '确认按钮未渲染').toBeTruthy()
  const attr = btn.attributes('disabled')
  return btn.element.disabled === true || (attr != null && attr !== 'false')
}

// ── ?raw 源码解析助手 ────────────────────────────────────────────────────────
const styleCss = () => {
  const block = csvDialogSource.match(/<style scoped>([\s\S]*?)<\/style>/)
  expect(block, '组件缺 <style scoped> 段').toBeTruthy()
  // 注释里也写着 min-height / overflow 等口径词 → 断言前先剥注释，只留真声明
  return block[1].replace(/\/\*[\s\S]*?\*\//g, '')
}
const ruleBody = (selector) => {
  const css = styleCss()
  const start = css.indexOf(`${selector} {`)
  expect(start, `样式缺 \`${selector}\` 规则`).toBeGreaterThan(-1)
  return css.slice(start, css.indexOf('}', start))
}
// `<div class="mapping-body">` 与其配对 `</div>` 的源码区间（模板内 div 无自闭合 → 逐层计数）
const mappingBodySpan = () => {
  const start = csvDialogSource.indexOf('<div class="mapping-body"')
  expect(start, '模板缺 .mapping-body 中段').toBeGreaterThan(-1)
  const re = /<div\b|<\/div\s*>/g
  re.lastIndex = start
  let depth = 0
  let match
  while ((match = re.exec(csvDialogSource))) {
    depth += match[0].startsWith('</') ? -1 : 1
    if (depth === 0) return [start, re.lastIndex]
  }
  throw new Error('.mapping-body 未闭合')
}

beforeEach(() => {
  setActivePinia(createPinia())
})

// ══ 设计 §4.3 前端用例 1（REQ-006 / D5 三段式钳高，源码级红线）════════════════
describe('v1.4.4 M3 REQ-006 弹窗三段式钳高（?raw 源码锁）', () => {
  it('用例M3-1: .mapping-card flex column + max-height 90vh；.mapping-body 唯一纵向滚动段（§6.1）', () => {
    const card = ruleBody('.mapping-card')
    expect(card).toContain('display: flex')
    expect(card).toContain('flex-direction: column')
    expect(card).toContain('max-height: 90vh')

    const body = ruleBody('.mapping-body')
    expect(body).toContain('flex: 1 1 auto')
    expect(body).toContain('min-height: 0')
    expect(body).toContain('overflow-y: auto')

    // 90vh 是卡片定值：样式段里只出现一次，不留第二处钳高来源
    expect((styleCss().match(/90vh/g) || [])).toHaveLength(1)
    // 壳口径：AppDialog 维持 max-width="480"、**不加** scrollable（钳高在卡片自身）
    expect(csvDialogSource).toContain('<AppDialog :model-value="modelValue" max-width="480"')
    expect(csvDialogSource).not.toContain('scrollable')
  })

  it('用例M3-2: 头固定 / 底部操作区在 .mapping-body 之外 / 滚动容器 tabindex="0" 且无其他样式类（§6.1）', () => {
    const [bodyStart, bodyEnd] = mappingBodySpan()

    // 卡片：pa-4 保留，rounded="xl" 作为遗留属性不移除（ui-design 审查裁定）
    expect(csvDialogSource).toContain('<v-card class="mapping-card pa-4" rounded="xl">')
    // 中段容器：唯一允许的类是 mapping-body + 键盘可达的 tabindex="0"
    expect(csvDialogSource).toContain('<div class="mapping-body" tabindex="0">')
    expect(csvDialogSource.match(/class="[^"]*mapping-body[^"]*"/g)).toHaveLength(1)

    // ① 标题区在中段之前（固定不滚）
    const title = csvDialogSource.indexOf('<v-card-title')
    expect(title).toBeGreaterThan(-1)
    expect(title).toBeLessThan(bodyStart)
    expect(csvDialogSource.indexOf('格式：{{ formatLabel }}')).toBeLessThan(bodyStart)

    // ③ 底部操作区在中段闭合之后、`</v-card>` 之前 → 不参与滚动、固定恒见
    const actions = csvDialogSource.indexOf('<div class="d-flex justify-end ga-2">')
    expect(actions).toBeGreaterThan(bodyEnd)
    expect(actions).toBeLessThan(csvDialogSource.indexOf('</v-card>'))
    // 全部映射内容（区块一/二 + 分类映射 + 标签映射 + 未映射计数 + 缺项清单）都在中段内
    // 取「渲染出的区块标题/计数」字面量定位（裸词也出现在中段上方的说明注释里）
    for (const marker of [
      '来源与列</div>',
      '收支与默认分类</div>',
      '分类映射</div>',
      '标签映射</div>',
      '未映射：',
    ]) {
      const at = csvDialogSource.indexOf(marker)
      expect(at, `源码缺「${marker}」`).toBeGreaterThan(-1)
      expect(at > bodyStart && at < bodyEnd, `「${marker}」应在 .mapping-body 之内`).toBe(true)
    }
  })

  it('用例M3-3: 样例行横向滚动 / mb-4 间距 / SQL 复用两处 v-if / 禁用条件字面量——全部不回归（回归锚）', () => {
    expect(ruleBody('.sample-scroll')).toContain('overflow-x: auto')
    expect(csvDialogSource).toContain('<div class="sample-scroll mb-1">')
    // SQL 弹窗复用同组件：区块一/二一律绑 previewData?.columns，次数恰为 2（boot3 同口径）
    expect(csvDialogSource.match(/v-if="previewData\?\.columns"/g)).toHaveLength(2)
    // 禁用条件表达式逐字不动：M3 的新建名报错折进 missingRequiredCount，不并列第四个数
    expect(csvDialogSource).toContain(':disabled="unmappedCount > 0 || missingRequiredCount > 0"')
    // 既有函数名/组件用法未重命名（红线 12）
    for (const name of ['handleConfirm', 'unmappedCount', 'setCategoryMapping', 'categoryOptions']) {
      expect(csvDialogSource).toContain(name)
    }
    expect(csvDialogSource.match(/<AppDialog\b/g)).toHaveLength(1)
  })
})

// ══ 设计 §4.3 前端用例 2–5（REQ-007 / D10 新建分类自定义名）═══════════════════
describe('v1.4.4 M3 REQ-007 新建分类自定义名称（行内输入与载荷）', () => {
  it('用例M3-4: 选「+ 新建分类」→ 行下输入框出现且预填文件内原分类名；未编辑直接确认 → 载荷无 name（§6.2）', async () => {
    const wrapper = await mountDialog(preview())
    wrapper.vm.setCategoryMapping('外卖', 'create')
    await nextTick()

    const input = wrapper.find('input.create-name-input')
    expect(input.exists(), 'create 行下方未出现名称输入框').toBe(true)
    expect(input.element.value).toBe('外卖') // 预填 = 文件内原分类名
    expect(input.attributes('placeholder')).toBe('外卖')
    // 本地态带 name + _touched=false，两者都不直接出网
    expect(wrapper.vm.categoryMapping['外卖']).toEqual({ action: 'create', name: '外卖', _touched: false })

    await wrapper.vm.handleConfirm()
    const payload = wrapper.emitted('confirm')[0][0]
    // 与旧版载荷逐字一致（boot3 用例 10.5 同形断言，是 M3 的向后兼容锚）
    expect(payload.category_mapping['外卖']).toEqual({ action: 'create' })
    expect(payload.category_mapping['外卖']).not.toHaveProperty('name')
    expect(payload.category_mapping['外卖']).not.toHaveProperty('_touched')
    expect(payload.category_mapping['外卖']).not.toHaveProperty('type')
  })

  it('用例M3-5: 输入已有分类名「餐饮」→ 行内 text-error + 确认置灰；改合法名 → 报错消失、按钮恢复、载荷带新名（§6.3）', async () => {
    const wrapper = await mountDialog(preview())
    wrapper.vm.setCategoryMapping('外卖', 'create')
    await flushPromises()

    await wrapper.find('input.create-name-input').setValue('餐饮')
    // 报错键 = 文件内原分类名（行匹配键），值 = 中文三态文案之一
    expect(wrapper.vm.createNameErrors['外卖']).toBe('分类「餐饮」已存在，请换一个名称')
    const error = wrapper.find('.create-name-row .text-error')
    expect(error.exists(), '重名报错未在行下渲染').toBe(true)
    expect(flat(error)).toBe('分类「餐饮」已存在，请换一个名称')
    expect(wrapper.vm.missingRequiredCount).toBe(1)
    expect(wrapper.vm.unmappedCount).toBe(0) // create 行仍算已映射（§4.2）
    expect(confirmDisabled(wrapper)).toBe(true)

    await wrapper.find('input.create-name-input').setValue('买菜')
    expect(wrapper.find('.create-name-row .text-error').exists()).toBe(false)
    expect(wrapper.vm.missingRequiredCount).toBe(0)
    expect(confirmDisabled(wrapper)).toBe(false)

    await wrapper.vm.handleConfirm()
    const payload = wrapper.emitted('confirm')[0][0]
    expect(payload.category_mapping['外卖']).toEqual({ action: 'create', name: '买菜' })
    expect(JSON.stringify(payload.category_mapping)).not.toContain('_touched')
  })

  it('用例M3-6: 输入清空（含全空白）→ 不报错、按钮可用、载荷不带 name，按预填原分类名建类（§6.4）', async () => {
    const wrapper = await mountDialog(preview())
    wrapper.vm.setCategoryMapping('外卖', 'create')
    await flushPromises()

    await wrapper.find('input.create-name-input').setValue('   ')
    expect(wrapper.find('.create-name-row .text-error').exists()).toBe(false)
    expect(wrapper.vm.createNameErrors).toEqual({})
    expect(wrapper.vm.missingRequiredCount).toBe(0)
    expect(confirmDisabled(wrapper)).toBe(false)
    const payload = (await confirmPayload(wrapper)).category_mapping['外卖']
    expect(payload).toEqual({ action: 'create' })
    expect(payload).not.toHaveProperty('name')

    // 清空成真空串同样口径
    await wrapper.find('input.create-name-input').setValue('')
    await wrapper.vm.handleConfirm()
    expect(wrapper.emitted('confirm')[1][0].category_mapping['外卖']).toEqual({ action: 'create' })
  })

  it('用例M3-7: 本批两行新建同一名称 → 后一行中文报错且确认置灰；改掉其一即双双解禁（§6.5）', async () => {
    const wrapper = await mountDialog(
      preview({ categories_in_file: ['外卖', '夜宵'], columns: preview().columns })
    )
    wrapper.vm.setCategoryMapping('外卖', 'create')
    wrapper.vm.setCategoryMapping('夜宵', 'create')
    await flushPromises()

    const inputs = wrapper.findAll('input.create-name-input')
    expect(inputs).toHaveLength(2)
    await inputs[0].setValue('买菜')
    expect(wrapper.vm.missingRequiredCount).toBe(0) // 单行新名，与既有分类不撞
    await inputs[1].setValue('买菜')

    // 后一行报错（两侧同显，用户看得清是哪两行撞了）+ 计入禁用条件
    expect(flat(wrapper.findAll('.create-name-row')[1])).toContain('与本次新建的其他分类重名')
    expect(wrapper.vm.createNameErrors['夜宵']).toBe('与本次新建的其他分类重名')
    expect(wrapper.vm.missingRequiredCount).toBe(2)
    expect(confirmDisabled(wrapper)).toBe(true)

    await inputs[1].setValue('水果')
    expect(wrapper.vm.createNameErrors).toEqual({})
    expect(confirmDisabled(wrapper)).toBe(false)
    await wrapper.vm.handleConfirm()
    const payload = wrapper.emitted('confirm')[0][0]
    expect(payload.category_mapping).toEqual({
      外卖: { action: 'create', name: '买菜' },
      夜宵: { action: 'create', name: '水果' },
    })
  })

  it('用例M3-8: map 行载荷与 SQL 复用路径的请求体键集不变；name 原样出网（清洗归服务层）', async () => {
    // ① map 行逐字沿用旧形状（不因为 name 字段上线而多出键）
    const mapped = await mountDialog(preview({ categories_in_file: ['餐饮'] }))
    await flushPromises()
    expect(mapped.vm.categoryMapping['餐饮']).toEqual({ action: 'map', target_id: 1 }) // 同名即预映射
    await mapped.vm.handleConfirm()
    expect(mapped.emitted('confirm')[0][0].category_mapping['餐饮']).toEqual({
      action: 'map',
      target_id: 1,
    })

    // ② SQL 复用（响应无 columns）：请求体仍只有两字段，M3 不新增键（设计 §4.4）
    const sql = await mountDialog({
      cache_id: 'sql-m3-1',
      format: 'sqlite_binary',
      row_count: 5,
      categories_in_file: ['外卖'],
      tags_in_file: [],
    })
    sql.vm.setCategoryMapping('外卖', 'create')
    await flushPromises()
    await sql.find('input.create-name-input').setValue('买菜')
    await sql.vm.handleConfirm()
    const sqlPayload = sql.emitted('confirm')[0][0]
    expect(Object.keys(sqlPayload).sort()).toEqual(['category_mapping', 'tag_mapping'])
    expect(sqlPayload.category_mapping['外卖']).toEqual({ action: 'create', name: '买菜' })

    // ③ 首尾空白原样发出：后端 `_clean_create_name` 负责去空白 / 空即回退预填值
    const blank = await mountDialog(preview())
    blank.vm.setCategoryMapping('外卖', 'create')
    await flushPromises()
    await blank.find('input.create-name-input').setValue('  买菜  ')
    expect(blank.vm.missingRequiredCount).toBe(0) // 「  买菜  」与「买菜」两侧去空白才比较
    await blank.vm.handleConfirm()
    expect(blank.emitted('confirm')[0][0].category_mapping['外卖']).toEqual({
      action: 'create',
      name: '  买菜  ',
    })
  })
})

// handleConfirm 是同步 emit，但载荷断言统一走这里，避免各用例重复 nextTick
async function confirmPayload(wrapper) {
  await wrapper.vm.handleConfirm()
  const emitted = wrapper.emitted('confirm')
  return emitted[emitted.length - 1][0]
}
