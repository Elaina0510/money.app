// v1.4.4 M4 关于页 + 版本单一真值源（REQ-008 / REQ-009）——任务 §4.2 四条编号用例。
//
// 落点裁定（任务审查轮 T2 / 用户 2026-09-27）：**新建本独立文件**，不进 `SettingsSubPages.test.js`
// （该文件由 M1/M2 共写，M4 不向其追加 describe）。
//
// 手法（沿仓库既定范式 + 总 prompt §7.8 vitest 能力边界）：环境未装 Vuetify，全局组件不注册
// → 模板按未知元素渲染（v-list-item 具名插槽内容不出 DOM），故：
//   * 结构与内部状态走 props/vm/类名断言；
//   * 「零硬编码版本字面量」「无网址/外链/部署字样」「核心优势恰 5 条」「入口卡同规格结构」
//     这类渲染不出来的契约一律以 ?raw 源码正则承载，不冒充 DOM 已验证；
//   * 深浅主题目检属真机项（任务 §5.6），本文件不覆盖、已移交人工清单。
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ── Mocks ──────────────────────────────────────────────────────────
// vue-router 只桩掉 composable（页面模板用 $router.back()，另经 global.mocks 注入），
// 保留 createRouter/createWebHashHistory，使本文件能导入真实路由表做 §4.2.1 断言。
const mockPush = vi.fn()
const mockBack = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn() }),
    useRoute: () => ({ path: '/settings/about', meta: {} }),
  }
})

// 版本接口 = 关于页唯一数据源：默认返回与后端真值**不同**的哨兵值，
// 一旦页面里混进硬编码版本，断言立刻变红。
vi.mock('@/api/version', () => ({
  getAppVersion: vi.fn().mockResolvedValue('9.9.9'),
}))

// SettingsPage 的既有数据源（入口卡所在页），与 SettingsSubPages.test.js 同款最小桩
vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/tags', () => ({
  getTags: vi.fn().mockResolvedValue([]),
  getTagsPaged: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
}))
vi.mock('@/api/records', () => ({
  getQuickTemplates: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/stores/useAppStore', () => ({
  useAppStore: () => ({ showToast: vi.fn(), themeMode: 'auto', setThemeMode: vi.fn() }),
}))

import { getAppVersion } from '@/api/version'
import router from '@/router'
import SettingsAboutPage from './SettingsAboutPage.vue'
import SettingsPage from './SettingsPage.vue'
import aboutPageSource from './SettingsAboutPage.vue?raw'
import settingsPageSource from './SettingsPage.vue?raw'
import routerSource from '@/router/index.js?raw'

// stub 环境里 v-list-item 的具名插槽（prepend/append）不渲染 → 用宿主摊平插槽，
// 使入口卡的头像与 chevron 可被 DOM 断言（同 SettingsSubPages.test.js 的 EntrySlotHost 手法）
const EntrySlotHost = {
  template: '<div class="entry-slot-host"><slot name="prepend" /><slot /><slot name="append" /></div>',
}

function mountAbout() {
  return mount(SettingsAboutPage, {
    global: { mocks: { $router: { push: mockPush, back: mockBack } } },
  })
}

function mountSettingsPage() {
  return mount(SettingsPage, {
    global: {
      mocks: { $router: { push: mockPush, back: mockBack } },
      components: { 'v-list-item': EntrySlotHost },
    },
  })
}

describe('v1.4.4 M4 关于页 + 版本单一真值源', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    getAppVersion.mockResolvedValue('9.9.9')
  })

  // ── 任务 §4.2.1 ──────────────────────────────────────────────────
  it('用例4.2.1: /settings/about 路由存在（懒加载·非 public·meta.title 关于）且页面组件挂载渲染四区块', async () => {
    const byPath = {}
    router.getRoutes().forEach((r) => {
      byPath[r.path] = r
    })

    const route = byPath['/settings/about']
    expect(route, '缺少路由 /settings/about').toBeTruthy()
    expect(route.name).toBe('SettingsAboutPage')
    expect(route.meta.title).toBe('关于')
    // 沿用全局登录守卫：**不单设 public**（任务 §2.3）
    expect(route.meta.public).toBeFalsy()
    expect(typeof route.components.default).toBe('function')
    const mod = await route.components.default()
    expect(mod.default).toBeTruthy()
    // 位次（任务 §2.3）：设置系二级页之末、/history 之前
    expect(routerSource).toMatch(/\/settings\/about[\s\S]*?path: '\/history'/)

    const wrapper = mountAbout()
    await flushPromises()
    expect(wrapper.find('.settings-about-page').exists()).toBe(true)
    // 四区块齐备（应用卡 / 核心优势 / 独特功能 / 技术实现），复用全局卡片与区块类
    expect(wrapper.findAll('.page-card')).toHaveLength(4)
    expect(wrapper.findAll('.section-block')).toHaveLength(4)
    const titles = wrapper.findAll('.section-title').map((n) => n.text())
    expect(titles).toEqual(['应用', '核心优势', '独特功能', '技术实现（白话）'])
    // 页头：返回箭头 + 标题「关于」（任务 §3.1）
    expect(wrapper.text()).toContain('关于')
    expect(wrapper.find('v-icon').text()).toBe('mdi-arrow-left')
  })

  // ── 任务 §4.2.2 ──────────────────────────────────────────────────
  it('用例4.2.2: 版本号只用接口值——mock 9.9.9 渲染「版本 9.9.9」，失败时该行不渲染且其余正常', async () => {
    const wrapper = mountAbout()
    await flushPromises()

    expect(getAppVersion).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.version).toBe('9.9.9')
    // 应用卡（首个 page-card）内出现接口给的版本
    expect(wrapper.findAll('.page-card')[0].text()).toContain('版本 9.9.9')

    // 接口 reject → 版本行整行不渲染（不留占位、不留错字），页面其余部分正常
    getAppVersion.mockRejectedValueOnce(new Error('版本接口调用失败'))
    const failed = mountAbout()
    await flushPromises()

    expect(failed.vm.version).toBe('')
    const appCard = failed.findAll('.page-card')[0]
    expect(appCard.text()).not.toContain('版本')
    expect(appCard.text()).toContain('Money App · 个人记账')
    // 页面其余部分不受影响
    expect(failed.find('.settings-about-page').exists()).toBe(true)
    expect(failed.findAll('.page-card')).toHaveLength(4)
    expect(failed.findAll('.section-title')).toHaveLength(4)
    expect(failed.findAll('li')).toHaveLength(11)

    // data 缺字段（异常返回形态）同样归入「不渲染」分支
    getAppVersion.mockResolvedValueOnce(undefined)
    const empty = mountAbout()
    await flushPromises()
    expect(empty.vm.version).toBe('')
    expect(empty.findAll('.page-card')[0].text()).not.toContain('版本')
  })

  // ── 任务 §4.2.3（红线断言）───────────────────────────────────────
  it('用例4.2.3: 关于页源码零硬编码版本字面量、无网址外链、无部署字样', () => {
    // ① 无 x.y.z 版本字面量（全仓真值只在 backend/app/constants.py）
    expect(aboutPageSource).not.toMatch(/\d+\.\d+\.\d+/)
    // ② 无网址
    expect(aboutPageSource).not.toMatch(/http/i)
    expect(aboutPageSource).not.toMatch(/www\./i)
    // ③ 无部署方式/命令字样
    expect(aboutPageSource).not.toMatch(/docker|uvicorn|npm|python/i)
    expect(aboutPageSource).not.toMatch(/部署方式|部署命令/)
    // ④ 无外链锚点（REQ-009「不含网址、不含外链」）
    expect(aboutPageSource).not.toMatch(/<a[\s>]/i)
    expect(aboutPageSource).not.toMatch(/href=|target=/i)
    // ⑤ 复用全局样式体系：卡壳与区块节奏全部走既有类，页面零新增色值
    expect(aboutPageSource).toContain('class="page-card"')
    expect(aboutPageSource).toContain('section-block')
    expect(aboutPageSource).toContain('section-title')
    expect(aboutPageSource).not.toMatch(/#[0-9a-fA-F]{3,8}/)
    expect(aboutPageSource).not.toMatch(/rgba\(/)
    // ⑥ 版本行由 v-if 承载（失败整行不渲染）
    expect(aboutPageSource).toMatch(/<div\s+v-if="version"/)
  })

  // ── 任务 §4.2.4 ──────────────────────────────────────────────────
  it('用例4.2.4: SettingsPage 含 to="/settings/about" 入口卡 + 核心优势恰为 T1 定稿 5 条', async () => {
    // 入口卡（任务 §2.2 同规格结构：entry-avatar + mdi-information-outline + 关于 + 副标题 + chevron）
    expect(settingsPageSource).toContain('to="/settings/about"')
    expect(settingsPageSource).toMatch(
      /<v-list-item to="\/settings\/about"[\s\S]{0,400}mdi-information-outline[\s\S]{0,400}关于[\s\S]{0,400}版本与应用介绍[\s\S]{0,400}mdi-chevron-right/
    )
    const wrapper = mountSettingsPage()
    await flushPromises()
    const aboutItem = wrapper.findAll('[to="/settings/about"]')
    expect(aboutItem).toHaveLength(1)
    expect(aboutItem[0].text()).toContain('关于')
    expect(aboutItem[0].text()).toContain('版本与应用介绍')
    expect(aboutItem[0].find('.entry-avatar v-icon').text()).toBe('mdi-information-outline')

    // 核心优势 **5 条**（任务审查轮 T1：「快速记账模板」并入首条，其余四句逐字独立成条，不扩写）
    const page = mountAbout()
    await flushPromises()
    const items = page.vm.advantages
    expect(items).toHaveLength(5)
    expect(items).toEqual([
      '收支一笔记全（金额/分类/标签/备注/消费时间），相同账单记 2 次自动纳入快速记账模板',
      '预设+自定义分类与标签双维度',
      '月度预算与分类预算盯进度',
      '统计看板（分类柱状、月度趋势、预算概览）',
      '多人各记各的（数据按登录用户隔离）',
    ])
    // DOM 侧同步取到 5 条（核心优势区块的 li 恰为第 1–5 条）
    const lis = page.findAll('li')
    expect(lis).toHaveLength(11) // 5（核心优势）+ 3（独特功能）+ 3（技术实现）
    expect(lis.slice(0, 5).map((n) => n.text())).toEqual(items)
    // 拼接不扩写：区块三 / 区块四各 3 条，与设计 §5.2 原文逐字对应
    expect(page.vm.features).toHaveLength(3)
    expect(page.vm.techNotes).toHaveLength(3)
  })
})
