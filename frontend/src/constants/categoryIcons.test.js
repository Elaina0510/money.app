import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { cwd } from 'node:process'
import { CATEGORY_ICONS } from './categoryIcons'

// 预设分类图标（与 backend/app/main.py 的 PRESET_CATEGORIES 逐项对齐，15 个）
const PRESET_ICONS = [
  'mdi-food',
  'mdi-bus',
  'mdi-cart',
  'mdi-gamepad',
  'mdi-hospital-box',
  'mdi-home',
  'mdi-cellphone',
  'mdi-briefcase',
  'mdi-bag-suitcase',
  'mdi-receipt-text',
  'mdi-cash-minus',
  'mdi-wallet',
  'mdi-gift',
  'mdi-finance',
  'mdi-cash-plus',
]

// 表单默认图标 + 全局回退图标
const SPECIAL_ICONS = ['mdi-cash', 'mdi-circle']

// 从运行目录逐级向上定位已安装的 @mdi/font 样式表（vitest 下 import.meta.url 非 file: 协议）
function findMdiCss() {
  const relative = join('node_modules', '@mdi', 'font', 'css', 'materialdesignicons.css')
  let dir = cwd()
  for (let i = 0; i < 5; i++) {
    const candidate = join(dir, relative)
    if (existsSync(candidate)) return candidate
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  throw new Error(`未找到 @mdi/font 样式表（cwd=${cwd()}）`)
}

describe('categoryIcons 精选图标常量守护', () => {
  it('用例4.1.1: 为数组、数量在 90–110 之间、无重复项', () => {
    expect(Array.isArray(CATEGORY_ICONS)).toBe(true)
    expect(CATEGORY_ICONS.length).toBeGreaterThanOrEqual(90)
    expect(CATEGORY_ICONS.length).toBeLessThanOrEqual(110)
    expect(new Set(CATEGORY_ICONS).size).toBe(CATEGORY_ICONS.length)
  })

  it('用例4.1.2: 覆盖清单 —— 预设 15 图标 + mdi-cash + mdi-circle 逐项在选集内', () => {
    ;[...PRESET_ICONS, ...SPECIAL_ICONS].forEach((icon) => {
      expect(CATEGORY_ICONS, `选集缺少 ${icon}`).toContain(icon)
    })
  })

  it('用例4.1.3: 所有条目匹配 /^mdi-[a-z0-9-]+$/', () => {
    CATEGORY_ICONS.forEach((icon) => {
      expect(typeof icon).toBe('string')
      expect(icon).toMatch(/^mdi-[a-z0-9-]+$/)
    })
  })

  // 全量字体类名兜底：@mdi/font 7.x 的 CSS 里必须真实存在该图标（防手误写出字体库无此项的名字）
  it('额外守护: 每个条目在 @mdi/font 样式表中有对应 ::before 规则', () => {
    // vitest 默认不处理 CSS（?raw 会拿到空串），故直接读已安装的样式表原文
    const source = readFileSync(findMdiCss(), 'utf8')
    expect(source.length).toBeGreaterThan(1000)
    CATEGORY_ICONS.forEach((icon) => {
      expect(source, `${icon} 不存在于 @mdi/font`).toContain(`.${icon}::before`)
    })
  })
})
