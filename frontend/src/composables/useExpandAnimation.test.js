import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import fs from 'node:fs'
import path from 'node:path'
import { cwd } from 'node:process'

import {
  useExpandAnimation,
  calcExpandOrigin,
  readExpandDurationVar,
  EXPAND_DURATION,
  EXPAND_EASING,
  CENTER_ORIGIN,
} from './useExpandAnimation'

// 同源互注防漂移：JS 常量必须与 global.scss :root 的 CSS 变量同值。
// （?raw 对 .scss 会被样式管线吃掉返回空串 → 按仓库既定的源码锁手法直接读文件文本）
const globalStyleSource = fs.readFileSync(path.resolve(cwd(), 'src/styles/global.scss'), 'utf8')

function makeEl(rect = { left: 0, top: 0, width: 0, height: 0 }) {
  const el = {
    style: {},
    offsetHeight: 1,
    getBoundingClientRect: () => rect,
  }
  return el
}

describe('useExpandAnimation（M14 全站展开动画单一实现源）', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ---------- 任务 9.1 ①：origin 退化规则（含新增的 {0,0} 收口） ----------

  it('用例M14-1a: origin 未设 / 非坐标 → center center（不再算出负百分比落点）', () => {
    const el = makeEl({ left: 100, top: 50, width: 250, height: 200 })
    expect(calcExpandOrigin(el, undefined)).toBe(CENTER_ORIGIN)
    expect(calcExpandOrigin(el, null)).toBe(CENTER_ORIGIN)
    expect(calcExpandOrigin(el, {})).toBe(CENTER_ORIGIN)
    expect(calcExpandOrigin(el, { x: '10', y: 20 })).toBe(CENTER_ORIGIN)
  })

  it('用例M14-1b: origin 为默认 {x:0,y:0}（无触发点语义）→ center center', () => {
    // 现实现（迁出前）以视口坐标减 rect 求百分比，(0,0) 会算出负百分比、落点在元素外侧左上方
    const el = makeEl({ left: 100, top: 50, width: 250, height: 200 })
    const origin = calcExpandOrigin(el, { x: 0, y: 0 })
    expect(origin).toBe('center center')
    expect(origin).not.toMatch(/-/i)
  })

  it('用例M14-1c: 元素缺失或零尺寸（jsdom 无布局）→ center center，不抛错', () => {
    expect(calcExpandOrigin(null, { x: 10, y: 10 })).toBe(CENTER_ORIGIN)
    expect(calcExpandOrigin(makeEl(), { x: 10, y: 10 })).toBe(CENTER_ORIGIN)
  })

  // ---------- 任务 9.1 ②：坐标 → transform-origin 百分比映射数学 ----------

  it('用例M14-2: 真实触发点按 rect 映射为百分比原点（左上 0% 0% / 中心 50% 50% / 右下 100% 100%）', () => {
    const rect = { left: 100, top: 50, width: 250, height: 200 }
    const el = makeEl(rect)
    expect(calcExpandOrigin(el, { x: 100, y: 50 })).toBe('0% 0%')
    expect(calcExpandOrigin(el, { x: 225, y: 150 })).toBe('50% 50%')
    expect(calcExpandOrigin(el, { x: 350, y: 250 })).toBe('100% 100%')
    // 非对称点：(200-100)/250=40%，(150-50)/200=50%
    expect(calcExpandOrigin(el, { x: 200, y: 150 })).toBe('40% 50%')
    // 触发点在元素之外仍按线性映射（不钳制，展开方向正确即可）
    expect(calcExpandOrigin(el, { x: 0, y: 0 + 1 })).toBe('-40% -24.5%')
  })

  // ---------- 任务 9.1 ③：展开应用的内联样式 ----------

  it('用例M14-3: applyExpand 写入原点 + scale(1)/opacity(1) 与统一时长缓动', () => {
    const el = makeEl({ left: 100, top: 50, width: 250, height: 200 })
    const contentRef = ref(el)
    const { applyExpand } = useExpandAnimation(contentRef, { origin: { x: 200, y: 150 }, duration: 200 })
    applyExpand()

    expect(el.style.transformOrigin).toBe('40% 50%')
    expect(el.style.transform).toBe('scale(1)')
    expect(el.style.opacity).toBe('1')
    expect(el.style.transition).toBe('transform 200ms ' + EXPAND_EASING + ', opacity 200ms ' + EXPAND_EASING)
  })

  it('用例M14-3b: 无 ref 内容时 applyExpand 静默返回（不抛错）', () => {
    const contentRef = ref(null)
    const { applyExpand } = useExpandAnimation(contentRef, {})
    expect(() => applyExpand()).not.toThrow()
  })

  // ---------- 任务 9.1 ④：collapse 计时与 cancel ----------

  describe('收起计时与取消（fake timers）', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('用例M14-4: applyCollapse 反向收缩回同一原点，duration 播完才回调 done', () => {
      const el = makeEl({ left: 100, top: 50, width: 250, height: 200 })
      const contentRef = ref(el)
      const done = vi.fn()
      const { applyCollapse, isCollapsing } = useExpandAnimation(contentRef, {
        origin: { x: 200, y: 150 },
        duration: 200,
      })

      applyCollapse(done)
      expect(el.style.transform).toBe('scale(0)')
      expect(el.style.opacity).toBe('0')
      expect(el.style.transformOrigin).toBe('40% 50%')
      expect(isCollapsing()).toBe(true)
      expect(done).not.toHaveBeenCalled()

      vi.advanceTimersByTime(199)
      expect(done).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1)
      expect(done).toHaveBeenCalledTimes(1)
      expect(isCollapsing()).toBe(false)
    })

    it('用例M14-5: cancelCollapse（重开取消收起）→ done 永不触发，收起计时器归零', () => {
      const el = makeEl({ left: 0, top: 0, width: 200, height: 100 })
      const contentRef = ref(el)
      const done = vi.fn()
      const { applyCollapse, cancelCollapse, isCollapsing } = useExpandAnimation(contentRef, {
        duration: 200,
      })

      applyCollapse(done)
      cancelCollapse()
      vi.advanceTimersByTime(500)

      expect(done).not.toHaveBeenCalled()
      expect(isCollapsing()).toBe(false)
    })

    it('用例M14-6: 收起进行中重复 applyCollapse 不叠加第二个计时器（天然去重）', () => {
      const el = makeEl({ left: 0, top: 0, width: 200, height: 100 })
      const contentRef = ref(el)
      const done = vi.fn()
      const { applyCollapse } = useExpandAnimation(contentRef, { duration: 200 })

      applyCollapse(done)
      applyCollapse(done)
      vi.advanceTimersByTime(200)

      expect(done).toHaveBeenCalledTimes(1)
    })

    it('用例M14-6b: 内容节点已卸载时 applyCollapse 立即回调 done（不卡关闭）', () => {
      const contentRef = ref(null)
      const done = vi.fn()
      const { applyCollapse } = useExpandAnimation(contentRef, { duration: 200 })
      applyCollapse(done)
      expect(done).toHaveBeenCalledTimes(1)
    })
  })

  // ---------- 任务 1.3 / 1.2：时长与 CSS 变量同源 ----------

  it('用例M14-7: EXPAND_DURATION / EXPAND_EASING 与 global.scss :root 变量同源（注释互注防漂移）', () => {
    expect(EXPAND_DURATION).toBe(220)
    expect(EXPAND_EASING).toBe('cubic-bezier(0.25, 0.8, 0.5, 1)')
    expect(globalStyleSource).toMatch(/--expand-duration:\s*220ms/)
    expect(globalStyleSource).toMatch(/--expand-easing:\s*cubic-bezier\(0\.25,\s*0\.8,\s*0\.5,\s*1\)/)
    expect(globalStyleSource).toMatch(
      /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?--expand-duration:\s*1ms/,
    )
  })

  it('用例M14-8: 未显式传 duration 时读 --expand-duration（reduced-motion 的 1ms 一处生效全站）', () => {
    const spy = vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: (k) => (k === '--expand-duration' ? '1ms' : ''),
    })
    const contentRef = ref(makeEl())
    const { durationOf } = useExpandAnimation(contentRef, {})
    expect(readExpandDurationVar()).toBe(1)
    expect(durationOf()).toBe(1)
    spy.mockRestore()

    // 读不到变量（jsdom 无全局样式）→ 回落 JS 常量，两者同值
    const empty = vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: () => '',
    })
    expect(readExpandDurationVar()).toBeNull()
    expect(durationOf()).toBe(EXPAND_DURATION)
    empty.mockRestore()
  })

  it('用例M14-9: options 支持 ref / getter（响应式原点与时长随调用方变化）', () => {
    const rect = { left: 100, top: 50, width: 250, height: 200 }
    const el = makeEl(rect)
    const contentRef = ref(el)
    const origin = ref({ x: 100, y: 50 })
    const { calcOrigin, applyExpand } = useExpandAnimation(contentRef, {
      origin: () => origin.value,
      duration: () => 120,
    })

    expect(calcOrigin(225, 150)).toBe('50% 50%')
    origin.value = { x: 350, y: 250 }
    applyExpand()
    expect(el.style.transformOrigin).toBe('100% 100%')
    expect(el.style.transition).toContain('120ms')
  })
})
