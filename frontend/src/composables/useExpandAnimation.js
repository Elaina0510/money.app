import { unref } from 'vue'

/* v1.4.3 M14（需求十四 / 设计 §14.2.1，D7 · D10）：全站「从触发点展开」动画的单一实现源。
 *
 * 时长/缓动口径与 CSS 侧 **同源互注**（改一处必须同步另一处，防漂移）：
 *   global.scss `:root { --expand-duration: 220ms; --expand-easing: cubic-bezier(0.25, 0.8, 0.5, 1) }`
 *   ←→ 本文件 `EXPAND_DURATION = 220` / `EXPAND_EASING = cubic-bezier(0.25, 0.8, 0.5, 1)`
 * 运行时优先读 `--expand-duration`（因此 `prefers-reduced-motion: reduce` 下的 1ms 一处生效全站），
 * 读不到（如 jsdom 未注入全局样式）回落到 JS 常量。
 */

/** 与 global.scss `--expand-duration` 同源的 JS 侧默认时长（ms） */
export const EXPAND_DURATION = 220

/** 与 global.scss `--expand-easing` 同源的 JS 侧缓动 */
export const EXPAND_EASING = 'cubic-bezier(0.25, 0.8, 0.5, 1)'

/** CSS 展开原点退化值：无触发点 → 中心展开（需求 14.2） */
export const CENTER_ORIGIN = 'center center'

function resolveOption(opt) {
  return typeof opt === 'function' ? opt() : unref(opt)
}

/**
 * 读取 CSS 侧 `--expand-duration`（含 reduced-motion 覆写）；不可用时返回 null。
 * @returns {number|null}
 */
export function readExpandDurationVar() {
  if (typeof document === 'undefined' || !document.documentElement) return null
  const raw = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--expand-duration')
    .trim()
  if (!raw) return null
  const ms = raw.endsWith('ms') ? parseFloat(raw) : raw.endsWith('s') ? parseFloat(raw) * 1000 : parseFloat(raw)
  return Number.isFinite(ms) && ms > 0 ? ms : null
}

/**
 * 点击原点 → transform-origin 百分比（视口坐标减去元素 rect）。
 *
 * 任务 2.2（新增退化规则）：origin 未设 / 非坐标 / 默认 {x:0,y:0} 一律退化为 `center center`。
 * 旧 ExpandTransition 实现在 (0,0) 时会算出负百分比、落点跑到元素外侧左上方，此处收口。
 *
 * @param {Element|null} el 展开内容节点
 * @param {{x:number,y:number}|null|undefined} origin 触发点视口坐标
 */
export function calcExpandOrigin(el, origin) {
  if (!el) return CENTER_ORIGIN

  const point = resolveOption(origin)
  if (!point || typeof point.x !== 'number' || typeof point.y !== 'number') return CENTER_ORIGIN
  // 未设触发点（默认 {0,0} 即「无坐标」语义）→ 退化中心展开
  if (point.x === 0 && point.y === 0) return CENTER_ORIGIN

  const rect = typeof el.getBoundingClientRect === 'function' ? el.getBoundingClientRect() : null
  if (!rect || !rect.width || !rect.height) return CENTER_ORIGIN

  const x = ((point.x - rect.left) / rect.width) * 100
  const y = ((point.y - rect.top) / rect.height) * 100
  return `${x}% ${y}%`
}

/**
 * 展开/收起动画机制（圆形扩散 scale + opacity），自 ExpandTransition.vue 原样迁出。
 *
 * @param {import('vue').Ref<HTMLElement>} contentRef 展开内容节点
 * @param {{origin?: *, duration?: *, easing?: *}} [options] 支持 ref / getter / 字面值
 */
export function useExpandAnimation(contentRef, options = {}) {
  let collapseTimer = null

  function duration() {
    const given = resolveOption(options.duration)
    if (given != null) return given
    return readExpandDurationVar() ?? EXPAND_DURATION
  }

  function easing() {
    return resolveOption(options.easing) ?? EXPAND_EASING
  }

  function origin() {
    return resolveOption(options.origin)
  }

  function transitionValue() {
    const d = duration()
    const e = easing()
    return `transform ${d}ms ${e}, opacity ${d}ms ${e}`
  }

  function calcOrigin(clickX, clickY) {
    return calcExpandOrigin(contentRef.value, { x: clickX, y: clickY })
  }

  function clearCollapseTimer() {
    if (collapseTimer) {
      clearTimeout(collapseTimer)
      collapseTimer = null
    }
  }

  function isCollapsing() {
    return collapseTimer !== null
  }

  // 自触发点圆形扩散展开（Force reflow 后翻转到 scale(1)）
  function applyExpand() {
    const el = contentRef.value
    if (!el) return

    el.style.transformOrigin = calcExpandOrigin(el, origin)
    el.style.transform = 'scale(0)'
    el.style.opacity = '0'
    el.style.transition = 'none'

    // Force reflow（与 ExpandTransition 迁出前一致）
    void el.offsetHeight

    el.style.transition = transitionValue()
    el.style.transform = 'scale(1)'
    el.style.opacity = '1'
  }

  /**
   * 反向收缩回收起原点，播完（duration）才回调 done 真正关闭画面。
   * @param {(Function|void)} [done] 收起动画播完的回调
   */
  function applyCollapse(done) {
    if (collapseTimer) return

    const el = contentRef.value
    if (!el) {
      if (typeof done === 'function') done()
      return
    }

    el.style.transformOrigin = calcExpandOrigin(el, origin)
    el.style.transition = transitionValue()
    el.style.transform = 'scale(0)'
    el.style.opacity = '0'

    collapseTimer = setTimeout(() => {
      collapseTimer = null
      if (typeof done === 'function') done()
    }, duration())
  }

  return {
    applyExpand,
    applyCollapse,
    cancelCollapse: clearCollapseTimer,
    clearCollapseTimer,
    isCollapsing,
    calcOrigin,
    // 供调用方按需读取当前生效口径
    durationOf: duration,
    easingOf: easing,
  }
}

export default useExpandAnimation
