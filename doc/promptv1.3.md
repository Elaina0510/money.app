# Money App v1.3 VibeCoding Prompt

> 自动生成，用于指导 AI Agent 完成 v1.3 版本的全部开发工作

---

## 项目概述

**项目名称：** Money App v1.3
**项目类型：** 前端 Vue 3 单页应用
**目标：** 实现 6 个 UI/UX 优化模块，提升视觉表现力和交互体验
**工作目录：** `h:\code\money.app`

### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5.34 | 前端框架（Composition API + `<script setup>`） |
| Vuetify | 3.12.6 | Material Design 组件库 |
| Vite | 8 | 构建工具 |
| Pinia | 3 | 状态管理 |
| dayjs | - | 日期处理 |
| Chart.js / vue-chartjs | - | 图表 |

### 代码规范

- **语言：** 纯 JavaScript（非 TypeScript），所有文件后缀为 `.js` / `.vue`
- **测试框架：** Vitest
- **代码检测：** ESLint + Prettier
- **所有新增和修改的代码必须：**
  1. 有完整的 Vitest 单元测试覆盖
  2. 通过 ESLint 检测（零 warning，零 error）
  3. 通过 Prettier 格式化检查

---

## 开发任务清单

### 建议开发顺序：1 → 4 → 6 → 2 → 3 → 5

| 序号 | 模块 | 优先级 | 复杂度 | 涉及文件 |
|------|------|--------|--------|----------|
| 1 | 记账页返回时未保存提醒 | 高 | 低 | `RecordFormPage.vue` |
| 4 | 分类图标替代收支图标 | 低 | 低 | `RecordListPage.vue` |
| 6 | 宽屏适配 110% 放大 | 低 | 低 | `AppLayout.vue` |
| 2 | 日历组件风格升级与动画 | 中 | 中 | 新增 `ExpandTransition.vue`、`DatePickerPopover.vue`，修改 `RecordFormPage.vue`、`RecordListPage.vue` |
| 3 | 账单详情展开动画 | 中 | 中 | `useAppStore.js`、`AppLayout.vue`、`RecordListPage.vue`、`RecordDetailPage.vue`、`global.scss`（可选） |
| 5 | 页面滑动模糊渐变 | 中 | 中 | `AppLayout.vue`、`global.scss` |

---

## 模块详细需求

### 模块 1：记账页返回时未保存提醒

**需求：** 用户在记账页修改过字段后，点击返回时弹出确认对话框。未修改时直接退出。

**实现要点：**
1. 新增 `isDirty`、`showLeaveDialog`、`pendingNavigation` 三个 ref
2. 实现 `takeSnapshot()` 函数，序列化当前表单字段为 JSON 字符串
3. 在 `onMounted` 中保存初始快照 `initialSnapshot`
4. 使用 `watch` 监听所有表单字段深层变化，与快照对比更新 `isDirty`
5. 使用 Vue Router 的 `onBeforeRouteLeave` 守卫拦截导航
6. 修改页面返回按钮为 `handleBack()` 方法
7. 复用现有 `ConfirmDialog.vue` 组件，配置 `confirm-text="确定放弃"`、`confirm-color="error"`
8. 提交成功后清除 `isDirty` 状态

**验收标准：**
- 未修改时返回直接退出
- 修改后返回弹出确认框
- 取消留当前页，确定放弃退出
- 编辑模式改回原始值后返回直接退出（快照对比）
- 兼容浏览器物理返回键

---

### 模块 2：日历组件风格升级与动画

**需求：** 日历弹出组件视觉风格与 Material Design 一致，打开时从点击位置以 expand 动画展开至画面中心。

**实现要点：**
1. **新增 `ExpandTransition.vue`：**
   - Props：`modelValue`(Boolean)、`origin`({x,y})、`duration`(默认 250)
   - 使用 `v-dialog` 作为容器
   - 实现 `calcOrigin()` 计算 transform-origin 百分比
   - CSS：`scale(0)→scale(1)` + `opacity` 过渡

2. **新增 `DatePickerPopover.vue`：**
   - Props：`modelValue`(日期)、`modelValueTime`(时间)、`showTime`(Boolean)
   - 封装 Vuetify `v-date-picker` + `ExpandTransition`
   - 通过 `#activator` 插槽暴露触发元素

3. **修改 `RecordFormPage.vue`：** 替换日期/时间为 `DatePickerPopover`
4. **修改 `RecordListPage.vue`：** 替换筛选日期为 `DatePickerPopover`

**验收标准：**
- 日历从点击位置 expand 动画展开
- 记账页和账单页均呈现新风格
- 动画时长 200-300ms，流畅 ≥ 60fps

---

### 模块 3：账单详情展开动画

**需求：** 点击账单条目后，从该条目位置以 expand 动画逐渐扩大至完整的详情页画面。

**实现要点：**
1. **扩展 `useAppStore.js`：** 新增 `transitionOrigin` ref 和 `setTransitionOrigin()` 方法
2. **修改 `RecordListPage.vue`：** `goToDetail()` 中通过 `getBoundingClientRect()` 获取条目坐标
3. **修改 `AppLayout.vue`：**
   - 实现 `getTransitionName(route)`：`/detail/*` 且有 origin 时返回 `'expand'`
   - 实现 JavaScript 钩子：`onBeforeEnter`、`onEnter`、`onLeave`
   - 将 `<transition>` 改为动态 `:name` + JS 钩子
4. **修改 `RecordDetailPage.vue`：** 返回时清除 `transitionOrigin`
5. **（可选）修改 `global.scss`：** 新增 `.expand-enter-active` / `.expand-leave-active` CSS 类备用

**验收标准：**
- 从条目位置展开至详情页
- 返回时使用默认过渡
- 直接访问详情页使用默认过渡
- 动画流畅无卡顿

---

### 模块 4：分类图标替代收支图标

**需求：** 账单列表中每条记录的前端图标从统一的收入/支出箭头，改为显示该记录所属分类的图标。

**实现要点：**
1. 将 `v-slot:prepend` 中的 `mdi-arrow-down` / `mdi-arrow-up` 替换为 `record.category_icon || 'mdi-circle'`
2. 图标 size 从 18 调整为 20
3. 背景色保持不变（`#FFE8E8` / `#E8FFF3`），仍区分收支
4. 移除 `v-list-item-title` 中重复的小号分类图标

**验收标准：**
- 各条目显示对应分类图标
- 无分类图标时显示 `mdi-circle` 兜底
- 收支通过背景色和金额正负号区分

---

### 模块 5：页面滑动模糊渐变

**需求：** 垂直滑动时，在固定标题栏下方和页面底部边缘添加模糊渐变效果。

**实现要点：**
1. **顶部标题栏下方：**
   - `.app-top-bar::after` 伪元素
   - `mask-image: linear-gradient(to bottom, black, transparent)`
   - 添加 `-webkit-mask-image` 兼容 Safari
   - `pointer-events: none; z-index: 99`

2. **页面底部：**
   - `.content-wrapper::after` 伪元素
   - `position: fixed; bottom: 0`
   - 宽度 `min(100%, 640px)` 响应式适配
   - `pointer-events: none; z-index: 50`

3. **主题适配：** 使用 `rgb(var(--v-theme-background))` 跟随 light/dark 主题

**验收标准：**
- 标题栏下方出现模糊过渡
- 底部可见模糊渐变
- 深色模式渐变颜色跟随主题
- 移动端和桌面端均正常
- 渐变区域不阻挡点击事件

---

### 模块 6：宽屏适配 110% 放大

**需求：** 桌面端（≥960px）使用 CSS `transform: scale(1.1)` 对整体内容放大。

**实现要点：**
1. `@media (min-width: 960px)` 媒体查询
2. `.content-wrapper` 设置 `transform: scale(1.1); transform-origin: top center`
3. 补偿底部间距：`padding-bottom: calc(100px * 1.1)`
4. `.main-content` 添加 `overflow-x: hidden` 防止水平溢出

**验收标准：**
- 移动端不受影响
- 桌面端统一放大 110%
- 无水平滚动条
- 点击、滚动、输入均正常
- 侧边栏布局不受影响

---

## Agent 架构

### 主 Agent（Orchestrator）

**职责：**
1. 跟踪整体开发进度
2. 按顺序调度子 Agent 执行各模块
3. 确保模块间的依赖关系正确处理
4. 汇总各模块的测试结果
5. 最终验证所有代码通过 ESLint + Prettier 检查

**工作流程：**
```
1. 初始化项目环境（安装 Vitest、ESLint、Prettier 依赖）
2. 按顺序 1 → 4 → 6 → 2 → 3 → 5 调度子 Agent
3. 每个模块完成后：
   - 运行该模块的 Vitest 测试
   - 运行 ESLint 检查
   - 运行 Prettier 检查
   - 记录完成状态
4. 所有模块完成后，运行全量测试
5. 生成最终报告
```

### 子 Agent（Module Implementer）

**每个子 Agent 职责：**
1. 阅读模块详细设计文档（`doc/tasksv1.3/` 目录下对应文件）
2. 实现模块功能代码
3. 编写完整的 Vitest 单元测试
4. 确保代码通过 ESLint + Prettier 检测
5. 更新任务清单中的完成状态

**子 Agent 列表：**

| Agent | 负责模块 | 输入文件 |
|-------|----------|----------|
| agent-1 | 记账页返回提醒 | `doc/tasksv1.3/record-form-leave-guard.md` |
| agent-4 | 分类图标 | `doc/tasksv1.3/category-icon.md` |
| agent-6 | 宽屏放大 | `doc/tasksv1.3/wide-screen-scale.md` |
| agent-2 | 日历动画 | `doc/tasksv1.3/calendar-upgrade.md` |
| agent-3 | 详情动画 | `doc/tasksv1.3/record-detail-animation.md` |
| agent-5 | 模糊渐变 | `doc/tasksv1.3/scroll-blur-gradient.md` |

---

## 测试要求

### Vitest 单元测试规范

1. **测试文件位置：** 与被测文件同目录，命名为 `*.test.js` 或 `*.spec.js`

   **目录结构示例：**
   ```
   frontend/src/
   ├── pages/
   │   ├── RecordFormPage.vue
   │   ├── RecordFormPage.test.js      # 测试文件
   │   ├── RecordListPage.vue
   │   └── RecordListPage.test.js
   ├── components/
   │   ├── common/
   │   │   ├── ExpandTransition.vue
   │   │   ├── ExpandTransition.test.js
   │   │   ├── DatePickerPopover.vue
   │   │   └── DatePickerPopover.test.js
   │   └── layout/
   │       ├── AppLayout.vue
   │       └── AppLayout.test.js
   └── stores/
       ├── useAppStore.js
       └── useAppStore.test.js
   ```

2. **测试覆盖率要求：** 核心逻辑覆盖率 ≥ 80%
3. **测试内容必须包括：**
   - 组件渲染测试
   - 用户交互测试（点击、输入等）
   - 状态变更测试
   - 边界条件测试

4. **测试示例结构：**
```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ComponentName from './ComponentName.vue'

describe('ComponentName', () => {
  beforeEach(() => {
    // 初始化设置
  })

  it('should render correctly', () => {
    const wrapper = mount(ComponentName)
    expect(wrapper.exists()).toBe(true)
  })

  it('should handle user interaction', async () => {
    // 交互测试
  })
})
```

5. **Mock 策略：**
   - Vue Router：使用 `vi.mock('vue-router')`
   - Pinia Store：使用 `vi.mock('@/stores/xxx')` 或 `createTestingPinia()`
   - Vuetify 组件：使用 `shallowMount` 或 mock 子组件

### ESLint 配置要求

项目需配置 ESLint 规则，确保：
- 使用 `eslint-plugin-vue` 进行 Vue 文件检测
- 使用 `eslint-config-prettier` 避免与 Prettier 冲突
- 零 warning，零 error

### Prettier 配置要求

项目需配置 `.prettierrc`：
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

---

## 环境初始化

在开始开发前，主 Agent 需要执行以下初始化：

### 1. 安装依赖

```bash
# 进入前端目录
cd frontend

# 安装测试依赖
npm install -D vitest @vue/test-utils jsdom

# 安装代码检测依赖
npm install -D eslint @eslint/js eslint-plugin-vue eslint-config-prettier prettier
```

### 2. 更新 Vite 配置

在 `frontend/vite.config.js` 中添加 Vitest 配置：

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // 新增 Vitest 配置
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.{js,ts}'],
  },
  // 保持原有服务器配置
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### 3. 创建 ESLint 配置文件

创建 `frontend/eslint.config.js`：

```javascript
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import eslintConfigPrettier from 'eslint-config-prettier'

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  eslintConfigPrettier,
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
]
```

### 4. 创建 Prettier 配置文件

创建 `frontend/.prettierrc`：

```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

### 5. 更新 package.json 脚本

在 `frontend/package.json` 的 `scripts` 中添加：

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "lint": "eslint src --ext .js,.vue",
    "lint:fix": "eslint src --ext .js,.vue --fix",
    "format": "prettier --check src",
    "format:fix": "prettier --write src"
  }
}
```

---

## 完成标准

每个模块完成必须满足：

1. ✅ 功能代码实现完成
2. ✅ Vitest 单元测试全部通过
3. ✅ ESLint 检测零 warning 零 error
4. ✅ Prettier 格式化检查通过
5. ✅ 任务清单中对应子任务全部勾选

整体完成标准：

1. ✅ 所有 6 个模块开发完成
2. ✅ 全量 Vitest 测试通过
3. ✅ 全量 ESLint + Prettier 检查通过
4. ✅ `doc/tasksv1.3/progress.md` 中所有模块标记为已完成

---

## 参考文档

- **需求文档：** `doc/proposalv1.3.md`
- **详细设计：** `doc/detailed-designv1.3.md`
- **任务清单：** `doc/tasksv1.3/` 目录下各模块文件
- **总进度：** `doc/tasksv1.3/progress.md`

---

## 主 Agent 验证清单

主 Agent 在调度子 Agent 前后，需逐项验证：

### 环境初始化验证

- [ ] `frontend/node_modules/vitest` 已安装
- [ ] `frontend/node_modules/@vue/test-utils` 已安装
- [ ] `frontend/node_modules/jsdom` 已安装
- [ ] `frontend/node_modules/eslint` 已安装
- [ ] `frontend/node_modules/prettier` 已安装
- [ ] `frontend/vite.config.js` 已添加 `test` 配置
- [ ] `frontend/eslint.config.js` 已创建
- [ ] `frontend/.prettierrc` 已创建
- [ ] `frontend/package.json` 已添加 test/lint/format 脚本
- [ ] `npm run test` 可执行（即使无测试文件也不报错）
- [ ] `npm run lint` 可执行
- [ ] `npm run format` 可执行

### 每个模块完成后的验证

- [ ] 功能代码已实现
- [ ] 测试文件已创建（`*.test.js` 或 `*.spec.js`）
- [ ] `npm run test` 全部通过
- [ ] `npm run lint` 零 warning 零 error
- [ ] `npm run format` 检查通过
- [ ] 任务清单中对应子任务已勾选

### 最终验证

- [ ] 所有 6 个模块已完成
- [ ] `npm run test` 全量测试通过
- [ ] `npm run lint` 全量检查通过
- [ ] `npm run format` 全量检查通过
- [ ] `doc/tasksv1.3/progress.md` 所有模块标记为已完成

---

## 注意事项

1. **项目语言为纯 JavaScript**，不要使用 TypeScript 语法
2. **所有 `.vue` 文件使用 `<script setup>` 语法**
3. **复用现有组件**，特别是 `ConfirmDialog.vue`
4. **颜色硬编码保持现状**，本版本不重构颜色管理
5. **浏览器兼容性**：`mask-image` 需要 `-webkit-` 前缀
6. **每个模块独立开发**，但需注意公共依赖（如 `ExpandTransition.vue`）
7. **提交前必须运行测试和检测**，确保代码质量
