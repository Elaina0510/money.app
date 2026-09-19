---
name: ui-design
description: "审查或生成符合项目 UI 设计规范（基于 Material Design 3 / M3 Expressive 修改）的 Vue 组件和样式代码"
user_invocable: true
auto_trigger:
  - "**/*.vue"
  - "**/*.css"
  - "**/*.scss"
  - "**/*.less"
  - "**/*.styl"
  - "**/*.ts"
  - "**/*.js"
---

# UI 设计规范 Skill

当用户调用 `/ui-design` 或涉及 Vue 组件、样式、布局相关任务时，使用此 skill。

## 你的角色

你是一个遵循项目 UI 设计规范、并理解 Material Design 3（M3）设计语言的前端开发助手。你的职责是：
1. **代码审查**：检查现有 Vue/CSS 代码是否符合规范，指出违规项并给出修改建议
2. **代码生成**：根据规范生成新的 Vue 组件和样式代码

规范以本文档的**项目 token 值为准**（审查、生成都按项目值执行）；M3 原始规范作为设计依据和演进参考，见第〇章与各章节中的「MD3 参照」。

## 设计哲学

- **清晰优先**：界面清晰是最高优先级，信息层级分明，用户一眼能看懂
- **克制用色**：大面积使用中性背景色，强调色仅用于关键交互元素，坚决避免过度装饰
- **舒适间距**：元素之间保持充足呼吸空间，宁可留白也不拥挤
- **一致体验**：全局统一视觉语言，减少用户的认知负担
- **响应式适配**：以移动端为主要场景，同时兼顾宽屏体验
- **角色化用色**（源自 M3）：颜色按"用途角色"配对使用，禁止随意组合；每一对 前景/背景 角色都保证对比度达标
- **层级靠色差**（源自 M3）：表面分离优先用色调整（tonal difference），阴影只在必要时点缀，scrim 遮罩用于模态层

---

## 〇、MD3 设计语言速览（学习自 m3.material.io，2026-09）

M3 是 Google 当前开源设计体系，2025 年 5 月发布 **M3 Expressive** 大更新，2026 年 Google I/O 持续演进。核心概念：

### 0.1 色彩：色调板 + 角色

- 一个源色经算法生成 **5 个关键色**（primary / secondary / tertiary / neutral / neutral-variant）→ 各自的**色调板**（tone 0–100，含 95/98/99），颜色以 **HCT**（色相/彩度/明度）定义。
- 组件不直接用色值，而是用**颜色角色**（标准 26 个 + 附加角色共 45 个）。命名语法：
  | 词素 | 含义 |
  |---|---|
  | `surface` | 背景与大块低强调区域 |
  | `primary/secondary/tertiary` | 强调角色：主操作用 primary；低强调（chip、选中导航）用 secondary；需特别强调的小元素（徽章、通知）用 tertiary |
  | `*-container` | 前景元素的填充色（如按钮底），**绝不用于文字** |
  | `on-*` | 叠在对应父色之上的文字/图标色 |
  | `*-variant` | 低强调替代 |
- **角色必须成对使用**（`primary` + `on-primary`），混搭（如 primary 文字 + primary-container 底）在动态色/对比度等级切换时会失效。
- surface 有 5 级容器色阶：`surface-container-lowest / low / (默认) / high / highest`，用于层级与嵌套容器。2023 年 2 月起 **surface 色不再与海拔绑定**（废除旧的 elevation overlay）。
- **error 在动态色方案中默认保持静态**，但随明暗主题变化。
- 附加角色（多数产品不需要）：`*-fixed / *-fixed-dim / *-fixed-light`（明暗主题下色调不变，注意对比风险）、`surface-dim / surface-bright`。
- **对比度等级**（2025-05 新增，token 化，明暗主题自动套用）：Standard（默认，混合层级）/ Medium（最低 3:1）/ High（7:1，作用于卡片内容而非卡片容器）。文字底线：**大字 3:1、小字 4.5:1**；禁用态豁免。

### 0.2 状态层（State Layers）

交互状态不用"变色"实现，而是在元素上叠一层半透明的 `on-color`：

| 状态 | 叠加不透明度 |
|---|---|
| Hover | 8% |
| Focus | 12% |
| Pressed | 10%（涟漪/波纹仍为主要按下反馈） |
| Dragged | 16% |
| Disabled 容器 | 12% |
| Disabled 内容（文字/图标） | 38% |

### 0.3 海拔（Elevation）

- 6 个级别：level 0=0dp、1=1dp、2=3dp、3=6dp、4=8dp、5=12dp。
- **静止态只允许 0~3 级**；+4/+5 保留给 hover、拖拽等交互态。**hover/focus 通常抬升 1 级**，同类元素抬升规则必须一致。
- 表达层级三种手段，按优先级：**色差（tonal difference，M3 默认）> 阴影（背景复杂或需引导交互时）> scrim（模态层之下，`scrim` 角色 32% 不透明度）**。
- 官方提示：surface tint（阴影叠主色染色）已弃用，改用海拔等级 token + surface-container 色阶。
- 少即是多：整个 UI 只应有少数几个海拔级别，级别越多注意力引导越弱。

### 0.4 形状（Shape）

- 圆角刻度 **10 档**：none 0 · extra-small 4 · small 8 · medium 12 · large 16 · **large-increased 20** · extra-large 28 · **extra-large-increased 32** · **extra-extra-large 48** · full（完全圆角，Expressive 起定义为"全圆"而非 50% 尺寸）。加粗为 Expressive 新增。
- **内圆角公式（嵌套必用）**：`inner radius = outer radius − padding`，嵌套容器禁止复用父级圆角，否则视觉失衡。
- Expressive 另提供 **35 种装饰形状库**（cookie、clover、burst…）与形状变形动画，面向 hero 场景，Web 暂不可用。

### 0.5 排版（Type Scale）

- 5 角色 × 3 尺寸 = **15 档基线样式**；Expressive 又新增 15 档 **emphasized**（同字号行高，仅加粗重与字距：display/headline/title-large/body → Medium 字重，title-medium/small 与全部 label → Bold）。
- 刻度比率 Major Second（1.125），基准 14sp；大字行高约 1.2×，小字约 1.5×。
- **频繁变化的数字/表格必须用等宽数字（tabular figures）**，防抖动、保对齐。
- 组件默认不使用 emphasized 样式，按需换 token；emphasized 适合选中态、主操作、未读数等强调场景。
- 字体槽分 **brand**（display/headline 等大字，重表达）与 **plain**（body/label，重可读），默认均为 Roboto；回退链 Roboto Flex → Roboto → Noto Sans。

### 0.6 动效（Motion）

- Expressive 起用**弹簧物理系统**替代"缓动+时长"：`spring = stiffness + damping + initial velocity`，两套方案（expressive 有回弹 / standard 近乎无弹）× 三档速度（fast/default/slow）× 两类属性。
- **核心规则**：空间属性（位移/旋转/尺寸/圆角）走 spatial 弹簧，可回弹；**颜色、不透明度永远走 effects（damping=1.0，绝不回弹）**——把弹跳用在透明度上是最高频动效错误。
- 多数产品选**单一方案**；本项目属 utilitarian，参照 standard 方案气质（克制、无回弹）。
- Web 无原生弹簧时的官方换算（cubic-bezier + 时长）：
  | 弹簧 | cubic-bezier | 时长 |
  |---|---|---|
  | Standard fast spatial | (0.27, 1.06, 0.18, 1.00) | 350ms |
  | Standard default spatial | (0.27, 1.06, 0.18, 1.00) | 500ms |
  | Standard fast effects | (0.31, 0.94, 0.34, 1.00) | 150ms |
  | Standard default effects | (0.34, 0.80, 0.34, 1.00) | 200ms |
  | Standard slow effects | (0.34, 0.88, 0.34, 1.00) | 300ms |
  | Expressive default spatial（回弹，仅用于庆祝/hero 时刻） | (0.38, 1.21, 0.22, 1.00) | 500ms |
- 旧缓动体系仍在过渡规范中使用：emphasized/standard `cubic-bezier(0.2, 0, 0, 1)`、emphasized decelerate `(0.05, 0.7, 0.1, 1)`、emphasized accelerate `(0.3, 0, 0.8, 0.15)`、legacy `(0.4, 0, 0.2, 1)`；时长 short1–4=50/100/150/200ms、medium1–4=250~400ms、long1–4=450~600ms。

### 0.7 间距（Spacing）

- M3 主刻度为 **8dp 线性体系**（`space100 = 8dp`，倍率命名：space125=10、space200=16、space300=24、space400=32、space600=48），并正式定义 2/4/6/10dp **嵌套子刻度**。
- 优先级：**先用父容器的 padding 与 gap，再考虑子元素的 margin**；Material 组件极少用 margin。
- 项目 4px 基准网格（4/8/12/16/24/32/48）与 M3 刻度值域完全重合，继续沿用。

### 0.8 图标（Material Symbols）

- 可变字体图标集，2000+ 符号，四条调节轴：**weight**（100–700，24dp 图标最低 200）、**fill**（0→1 表达选中态）、**grade**（-25 抵消深底视觉膨胀）、**optical size**（20/24/40/48）。
- 24dp 标准尺寸：live area 20dp + 四周 2dp padding；默认描边 2dp、圆角 2dp。
- **图标与文字同光重视觉重量**；图标基线下移约文字尺寸的 11.5%。
- 24dp 图标的触控目标必须 48×48dp；<20dp 的复杂图标必须配文字标签。

### 0.9 设计 token 体系

- 三层：**reference（`md.ref.*` 原始值）→ system（`md.sys.*` 角色与主题发生处）→ component（`md.comp.*` 组件属性）**；解析链末端永远指向 token 而非硬编码。
- 上下文（context）：深色主题、设备形态、密度、RTL 等以"打标签覆盖"的方式换值。
- 对本项目的意义：**CSS 变量即 system token**，组件样式只引用变量，不写死色值（见审查清单）。

### 0.10 Expressive 新增组件（2025）

button groups（标准/连接式）、split buttons、FAB menu、loading indicator（按钮内形变加载）、toolbar、side sheets、carousels 增强、badge 新配色映射。

### 0.11 本项目采纳策略

| MD3 概念 | 采纳情况 |
|---|---|
| 色彩角色配对、on-/container 语法 | ✅ 采纳（第一章各表「MD3 角色参照」列 + 1.2 配对规则） |
| 状态层百分比 | ✅ 采纳（按钮/列表 hover 等） |
| 海拔 6 级、静止 0~3、hover +1、scrim 32% | ✅ 采纳思想；阴影实现保留项目 3 档 |
| 8dp 间距、48dp 触控目标、3:1/4.5:1 对比 | ✅ 采纳 |
| M3 15 档字阶、等宽数字、emphasized 强调思路 | ✅ 映射采纳（项目 7 档为准） |
| standard 弹簧方案 / 曲线换算表 | ✅ 用于弹窗等空间动效；颜色/透明度绝不回弹 |
| 动态取色（壁纸取色）、baseline 紫色板 | ❌ 不采纳，保留 Google 蓝品牌色 |
| 35 装饰形状库、回弹式 spatial、48dp 大圆角、大面积彩色容器 | ❌ 不采纳，与"克制"哲学冲突 |
| surface-container 五级色阶 | ⚠️ 简化为项目三级中性背景 |

---

## 一、色彩系统

### 1.1 背景色（全局中性背景）

所有页面统一使用中性灰色背景，取消大面积彩色区块。

| Token | 值 | 用途 | MD3 角色参照 |
|---|---|---|---|
| `--color-bg` | `#FAFAFA` | 全局页面背景 | surface |
| `--color-bg-secondary` | `#FFFFFF` | 卡片、弹窗、内容区块背景 | surface-container-low / 默认 |
| `--color-bg-tertiary` | `#F5F5F5` | 输入框、标签栏等内部元素背景 | surface-container-high |

**禁止**：禁止在卡片、弹窗、标签栏等区块中使用大面积 `primary`、`surface` 等彩色背景。彩色仅用于强调色。

### 1.2 主题强调色

强调色仅用于：按钮、链接、图标、选中态边框/指示器。

| Token | 值 | 说明 | MD3 角色参照 |
|---|---|---|---|
| `--color-primary` | `#1A73E8` | 主操作按钮、链接、关键交互 | primary |
| `--color-primary-light` | `#E8F0FE` | 浅色徽章、标签、hover 背景 | primary-container |
| `--color-on-primary` | `#FFFFFF` | 强调色上的文字 | on-primary |

**角色配对规则**（源自 M3）：`primary` 底必须配 `on-primary` 文字；`primary-light` 底必须配 `primary` 文字。禁止 `primary` 文字 + `primary` 底、或 `primary-light` 上放白字等破坏对比的组合。

### 1.3 文字色

| Token | 值 | 用途 | MD3 角色参照 |
|---|---|---|---|
| `--color-text-primary` | `#202124` | 标题、主要内容 | on-surface |
| `--color-text-secondary` | `#5F6368` | 副标题、描述、时间戳 | on-surface-variant |
| `--color-text-tertiary` | `#9AA0A6` | 占位符、禁用态文字 | 约 on-surface-variant @38% |
| `--color-text-on-primary` | `#FFFFFF` | 按钮上的文字 | on-primary |
| `--color-text-link` | `#1A73E8` | 可点击文字链接 | primary（链接必须带下划线） |

### 1.4 功能色

| Token | 值 | 用途 |
|---|---|---|
| `--color-success` | `#34A853` | 成功提示、收入标签 |
| `--color-error` | `#EA4335` | 错误提示、删除操作、支出标签 |
| `--color-warning` | `#FBBC04` | 警告提示 |
| `--color-info` | `#4285F4` | 信息提示 |

功能语义色保持静态、不随主题漂移（对齐 M3 中 error 静态化的设计）。

### 1.5 边框与分割线

| Token | 值 | 用途 | MD3 角色参照 |
|---|---|---|---|
| `--color-border` | `#E0E0E0` | 输入框边框等**重要边界** | outline |
| `--color-border-light` | `#EEEEEE` | 卡片分割线、轻量分隔 | outline-variant |

**规则**（源自 M3）：`outline`（深）只给单元素边界（输入框）；分割线、卡片这类**含多个元素的容器**边界用 `outline-variant`（浅）。需要视觉层级或标识可点击范围时用 `outline` 或保证 3:1 对比，不得用更浅的线充当。

### 1.6 禁止用色清单

- 禁止使用大面积 `primary`、`secondary`、`tertiary` 色作为背景
- 禁止使用大面积 `surface` 色作为区块背景
- 卡片、弹窗、标签栏、表单区域等区块背景只允许使用 `#FFFFFF`、`#FAFAFA`、`#F5F5F5` 三种中性色
- `surface`、`primary`、`secondary`、`tertiary` 仅用于强调色、图标、按钮、选中态等小面积元素
- 禁止硬编码色值，一切颜色引用 CSS 变量（token 即 system token）

### 1.7 状态层（交互反馈统一实现）

hover/focus/pressed/disabled 一律按 0.2 节状态层百分比叠加（深色 UI 元素上可用 `#FFFFFF` 叠加，浅色元素上叠加 `#000000`）：

| 状态 | 叠加 |
|---|---|
| Hover | 8% |
| Focus | 12% + 可见焦点环（见 14.可访问性） |
| Pressed | 10%（+ 可选波纹） |
| Disabled | 容器 12%、内容 38% |

---

## 二、字体排版

### 2.1 字体栈

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
```

对应 M3 回退链思想：系统字体 → Roboto → Noto Sans 兜底中文。

### 2.2 字号规范

| Token | 值 | 字重 | 用途 | MD3 字阶参照 |
|---|---|---|---|---|
| `--font-size-display` | 28px | 500 | 金额大数字 | headline-medium (28/36) |
| `--font-size-headline` | 22px | 500 | 二级标题（月度总额） | title-large (22/28) |
| `--font-size-title` | 18px | 500 | 三级标题（模块标题） | title-large 缩小 |
| `--font-size-subtitle` | 16px | 500 | 列表主标题 | title-medium (16/24) |
| `--font-size-body` | 15px | 400 | 正文、表单输入 | body-large (16/24) 微调 |
| `--font-size-caption` | 13px | 400 | 辅助说明、标签 | body-small/label-medium 之间 |
| `--font-size-overline` | 12px | 500 | 小标签、角标 | label-medium (12/16) |

**MD3 参照**：完整 15 档基线字阶 + 15 档 emphasized 见 0.5 节。项目采用精简 7 档；缩减时保持档位间足够的尺寸反差，避免相邻两档只差 1–2px。

### 2.3 行高

- 标题行高：1.3（M3 大字约 1.2×）
- 正文行高：1.5（M3 小字约 1.5×）

### 2.4 排版规则

- 标题禁止使用全大写
- 数字使用等宽字体或 `font-variant-numeric: tabular-nums` 保证对齐——**金额、余额、日期等一切会变化/需对齐的数字必须等宽**（M3 明确要求，防刷新抖动）
- 中英文混排时，英文与中文之间加 1/4 em 空格
- 强调场景（选中态、未读、关键数字）可临时升一档字重（500→700，模拟 M3 emphasized），但同一区块内保持模式一致

---

## 三、间距与圆角

### 3.1 间距系统（4px 基准网格）

| Token | 值 | 用途 | MD3 刻度参照 |
|---|---|---|---|
| `--space-xxs` | 4px | 图标与文字间距 | 嵌套子刻度 0.5x |
| `--space-xs` | 8px | 紧凑元素间距 | space100 |
| `--space-s` | 12px | 列表项内间距 | space150 |
| `--space-m` | 16px | 区块内间距、卡片内边距 | space200 |
| `--space-l` | 24px | 区块间距 | space300 |
| `--space-xl` | 32px | 页面区块分隔 | space400 |
| `--space-xxl` | 48px | 页面上下边距 | space600 |

**优先用父容器 `padding` + `gap` 控制间距，避免给子元素写 margin**（源自 M3）。

### 3.2 圆角规范

| Token | 值 | 用途 | MD3 形状刻度参照 |
|---|---|---|---|
| `--radius-s` | 8px | 标签、小按钮、输入框 | small |
| `--radius-m` | 12px | 卡片、弹窗 | medium |
| `--radius-l` | 16px | 底部弹窗顶部 | large |
| `--radius-full` | 9999px | 圆形头像、药丸按钮 | full |

**规则**：
- 项目为信息密集型记账应用，卡片保持 `radius-m`，**禁止给卡片/列表等密集组件套 28dp+ 大圆角**（M3 同样反对——大圆角会裁切内容与图片）。
- **嵌套圆角必须用内圆角公式**：`inner radius = outer radius − padding`（如卡片 12px 圆角、16px 内边距，其内部贴边元素的圆角不可再取 12px 或更大）。

### 3.3 间距规则

- 父容器内边距：`padding: 16px`
- 子元素间距：`gap: 12px`
- 卡片内边距：`padding: 16px`
- 卡片之间的间距：`gap: 12px`
- 宁可留白，不可拥挤

---

## 四、海拔与阴影

### 4.1 项目阴影（三档）

| Token | 值 | 用途 | 约当 MD3 海拔 |
|---|---|---|---|
| `--shadow-s` | `0 1px 3px rgba(0,0,0,0.08)` | 按钮、输入框 | level 1 (1dp) |
| `--shadow-m` | `0 2px 8px rgba(0,0,0,0.1)` | 卡片、下拉菜单 | level 2 (3dp) |
| `--shadow-l` | `0 4px 16px rgba(0,0,0,0.12)` | 弹窗、模态框 | level 3~5（M3 模态弹窗为 level 3） |

**MD3 参照**：level1 阴影为 `0px 1px 2px rgba(0,0,0,.3), 0px 1px 3px 1px rgba(0,0,0,.15)`，逐级变宽变柔。

### 4.2 使用规则

- **层级表达优先级：色差 > 阴影 > 遮罩**。相邻表面优先靠背景色阶（#FAFAFA→#FFFFFF）区分，其次才是阴影；阴影只在内容背景杂乱或需要引导点击时添加。
- 卡片默认带 `shadow-m`，hover 时阴影增强一档（对应 M3"hover 抬升 1 级"），**同类元素抬升行为必须一致**。
- 弹窗/抽屉用 `shadow-l` + 下方 scrim：`rgba(0,0,0,0.32)`（M3 scrim 即 `scrim` 角色 @32%）。
- 页面整体保持扁平克制；静止元素海拔不超过"level 3"档，全页同时可见的阴影层级种类尽量少。
- **阴影颜色不掺主色**（M3 已弃用 surface tint，禁止 `box-shadow` 使用彩色）。唯一例外：9.6 底部导航中间主操作按钮的品牌蓝投影，为既定设计。

---

## 五、按钮

### 5.1 按钮类型

对齐 M3 五等强调层级，项目采用其中四档：

| 类型 | 背景 | 文字 | 用途 | MD3 对应 |
|---|---|---|---|---|
| Filled | `primary` | `on-primary` | 主操作（记一笔、保存） | Filled button |
| Tonal | `primary-light` | `primary` | 次要操作 | Filled tonal |
| Outlined | 透明/白色 + 1px `border` | `primary` | 辅助操作 | Outlined |
| Text | 透明 | `primary` | 低优先级操作 | Text button |

**强调度选择**（源自 M3）：一个界面同屏最多一个高强调（Filled）主操作；多个按钮并排时按重要性递减 Filled → Tonal/Outlined → Text；app bar 内不放 Filled/Tonal 以上强调按钮，用 icon button 替代。

**MD3 参照**：M3 另有 Elevated（白底 + 主色文字 + 海拔），本项目不使用，避免彩色阴影歧义。

### 5.2 按钮尺寸

| 高度 | 圆角 | 字号 | 内边距 |
|---|---|---|---|
| 40px | `radius-s` (8px) | 15px | 0 20px |
| 32px | `radius-s` (8px) | 13px | 0 12px |

- 按钮宽度随文字伸缩，不得窄于文字 + 左右内边距；图标与文字整体不换行。
- 一个按钮内最多一个图标，图标与标签视为不可拆分的整体。
- **触控目标**：32px 小按钮须用 padding/伪元素把可点击区域撑到 ≥44px（M3 目标 48dp，Web 底线 44px）。

### 5.3 状态（统一用状态层，见 1.7）

- **Hover**：叠 8% 状态层
- **Focus**：叠 12% + 焦点环
- **Pressed**：叠 10%
- **Disabled**：背景 12% 叠加（等效 `#E0E0E0` 观感），文字 38%（等效 `#9AA0A6`）
- 状态切换用颜色过渡完成（effects 类动效，**不回弹**，150–200ms）

### 5.4 按钮间距

- 多个按钮间距：`gap: 12px`
- 按钮内图标与文字间距：`gap: 8px`
- 按钮优先横向成组摆放，避免纵向堆叠（空间足够时）

---

## 六、卡片

### 6.1 默认样式

```css
background: #FFFFFF;
border-radius: 12px;
padding: 16px;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
border: 1px solid #EEEEEE; /* 可选，用于强调 */
```

### 6.2 MD3 三种卡片变体参照

| 变体 | 构成 | 项目使用建议 |
|---|---|---|
| Elevated | 较高 surface 色阶 + level1 阴影 | ≈ 项目默认（白底+shadow-m） |
| Filled | surface-container 色阶，无阴影 | 灰底区块（#F5F5F5） |
| Outlined | 1px `outline-variant` 描边，无阴影 | 列表内低强调卡片 |

**规则**：同一区域内只用一种卡片变体；边框与阴影不重复强调同一层级（有清晰色差时可去边框）。

### 6.3 状态

- **默认**：白底 + 浅阴影 + 浅灰边框
- **Hover**：阴影增强一档（海拔抬升思想），微微上移 1px（可选）
- **按下/选中**：边框变为 `primary`

### 6.4 规则

- 卡片内部用 `border-bottom: 1px solid #EEEEEE` 分隔列表项（即 outline-variant 用法）
- 最后一个列表项不加分隔线
- 卡片是"单一主题的内容与操作"容器：不要在卡片里再套同层级卡片

---

## 七、表单与输入框

### 7.1 输入框样式

```css
height: 40px;
padding: 0 12px;
border: 1px solid #E0E0E0;
border-radius: 8px;
background: #F5F5F5;
font-size: 15px;
color: #202124;
transition: border-color 0.2s;
```

### 7.2 状态

- **Focus**：边框变为 `primary`，背景变白，带 2px `primary-light` 光晕
- **Error**：边框变为 `error`，下方出现 12–13px 错误文字（错误信息不得只靠红色传达，必须有文字）
- **Disabled**：背景 `#EEEEEE`、文字 `#9AA0A6`（对应 M3 状态层 disabled 思想：容器 12%、内容 38%）
- **Hover（非聚焦）**：叠 8% 状态层

### 7.3 标签

- 标签在输入框上方，`margin-bottom: 8px`
- 标签字号 15px，字重 500
- 必填项用红色 `*` 标注，放在标签后；辅助说明文字用 `text-secondary` 13px 置于输入框下方

### 7.4 表单布局

- 垂直堆叠，间距 `margin-bottom: 16px`
- 标签和输入框组合的间距为 `8px`
- 表单区域与按钮区域的间距为 `24px`
- 相邻输入框 ≥8dp 间距，减少误触（M3 目标间距规则）

---

## 八、列表与单元格

### 8.1 单元格高度（对齐 M3 列表标准）

| 高度 | 用途 | MD3 对应 |
|---|---|---|
| 56px | 单行列表 | one-line list item |
| 72px | 双行列表 | two-line list item |
| 88px | 三行列表 | three-line list item |

### 8.2 单元格内边距

```css
padding: 16px;
```

### 8.3 头像/图标区

- 尺寸：40px
- 圆角：`radius-full`（圆形）
- 与内容间距：`12px`

### 8.4 内容区

- 主标题：16px，字重 500，颜色 `text-primary`
- 副标题：13px，字重 400，颜色 `text-secondary`
- 右侧辅助文字：15px，字重 500，颜色 `text-primary`（金额加 `tabular-nums`）

### 8.5 列表单元格间距

- 列表项之间的间距：`gap: 4px`
- 列表区域内边距：`padding: 0 8px`

### 8.6 状态

- 可点击列表项 hover 叠 8% 状态层（或 `background: #F5F5F5`），过渡 150ms
- 选中态：左侧指示条/文字变色 + 可选 emphasized 字重（见 2.4）

---

## 九、底部导航栏

### 9.1 结构

底部导航栏 5 个入口：账单、统计、记账、预算、更多。

### 9.2 高度与背景

```css
height: 56px;
background: #FFFFFF;
border-top: 1px solid #EEEEEE;
box-shadow: 0 -1px 3px rgba(0, 0, 0, 0.08);
```

### 9.3 图标

- 图标尺寸：24px
- 选中态图标颜色：`primary`
- 未选中态图标颜色：`#9AA0A6`
- 图标风格统一（同源图标集）；选中/未选中可用同图标 fill 0→1 表达（Material Symbols 思路）

### 9.4 文字

- 选中态字号：13px，字重 500，颜色 `primary`
- 未选中态字号：12px，字重 400，颜色 `#9AA0A6`

### 9.5 间距

- 标签栏内左右 padding：`16px`
- 图标与文字间距：`4px`
- 每个入口触控区域 ≥ 48×48px

### 9.6 中间按钮

- 尺寸：48px
- 颜色：`primary`
- 阴影：`0 4px 12px rgba(26, 115, 232, 0.3)`
- 位置：向上凸出 8px
- 语义：主操作入口（记一笔），相当于 FAB 角色，全页唯一高强调按钮

**MD3 参照**：标准 Navigation bar 高 80dp、底色 `surface-container`、选中项套 32dp 高 `secondary-container` 胶囊指示器。本项目采用 56px 紧凑版 + `primary` 着色是既定裁剪；若未来强化选中态，可只引入**胶囊指示器**这一项。

---

## 十、弹窗与对话框

### 10.1 尺寸

| 类型 | 宽度 | 圆角 |
|---|---|---|
| 紧凑型 | 280px | 12px |
| 标准型 | 320px | 12px |
| 宽松型 | 560px | 12px |

### 10.2 背景

```css
background: #FFFFFF;
border-radius: 12px;
padding: 24px;
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
```

### 10.3 遮罩层

```css
background: rgba(0, 0, 0, 0.32); /* M3 scrim：scrim 角色 @32% */
backdrop-filter: blur(2px);
```

### 10.4 内容区域间距

| 元素 | 间距规则 |
|---|---|
| 图标区 | `margin-bottom: 16px` |
| 标题区 | `margin-bottom: 12px` |
| 正文区 | `margin-bottom: 16px` |
| 操作按钮区 | `margin-top: 24px` |

### 10.5 操作按钮

- 两个按钮间距：`gap: 12px`
- 按钮右对齐；低强调（取消=Text）在左，高强调（确认=Filled）在右
- 打开时焦点移入对话框、关闭后焦点归还触发元素（见 14.可访问性）

**MD3 参照**：标准 Dialog 圆角 28dp、标题用 headline-small(24/400)。项目维持 12px 圆角 + 18px 标题，保持克制观感；高度超过屏 80% 的确认类弹窗应改为底部抽屉。

---

## 十一、标签与徽章

### 11.1 标签

```css
padding: 4px 8px;
border-radius: 8px;
font-size: 12px;
font-weight: 500;
```

### 11.2 标签颜色（角色配对示范）

| 类型 | 背景 | 文字 |
|---|---|---|
| 主要标签 | `primary-light` | `primary` |
| 成功标签 | `#E6F4EA` | `success` |
| 错误标签 | `#FCE8E6` | `error` |
| 警告标签 | `#FEF7E0` | `warning` |

浅色容器 + 深色文字，是 M3 `*-container` + `on-*-container` 配对思想的项目落地；新增语义标签必须按同模式成对补充 token。

### 11.3 徽章

- 最小尺寸：18px
- 圆角：`radius-full`
- 字号：12px
- 字重：500
- 位置固定于宿主元素右上，不得与其他元素碰撞遮挡；导航栏徽章在选中后消失（M3 规则）
- 小徽章（纯点）表状态变化，大徽章（数字）表数量，≤4 字符，超出截断

---

## 十二、Toast 提示

### 12.1 布局

```css
position: fixed;
bottom: 80px;
left: 50%;
transform: translateX(-50%);
max-width: calc(100% - 32px);
width: fit-content;
z-index: 1000;
```

### 12.2 内边距

```css
padding: 12px 16px;
```

### 12.3 样式

- 成功背景：`#E6F4EA`，文字：`#202124`，图标：`#34A853`
- 错误背景：`#FCE8E6`，文字：`#202124`，图标：`#EA4335`
- 警告背景：`#FEF7E0`，文字：`#202124`，图标：`#FBBC04`
- 信息背景：`#E8F0FE`，文字：`#202124`，图标：`#4285F4`

**MD3 参照**：标准 Snackbar 用反色面 `inverse-surface`（深色底 + 反色文字 + inverse-primary 动作按钮）。项目浅色底方案为既定裁剪；若需与页面强对比的提示，可增设深色变体对齐 Snackbar。Toast 不打断操作、不显示在另一 Toast 之上；带操作时操作按钮用 Text button。

### 12.4 动画

- 出现：从下方 20px 淡入，时长 0.3s，缓出（decelerate 类曲线）
- 消失：向上淡出，时长 0.3s，缓入（accelerate 类曲线）
- 自动关闭：3 秒后自动消失（含操作的 Toast 适当延长）

---

## 十三、动画与过渡

### 13.1 缓动与时长

- 默认过渡曲线：`cubic-bezier(0.4, 0, 0.2, 1)`（M3 legacy standard，项目全局基线）
- **推荐演进**：空间位移类改用 M3 standard/emphasized 曲线 `cubic-bezier(0.2, 0, 0, 1)` 或 0.6 节的 standard spatial 换算表
- 时长档位（对齐 M3 duration scale）：
  - 微反馈（颜色/透明度）：`--transition-fast` 0.15s
  - 常规过渡：`--transition-normal` 0.2s
  - 弹窗、页面级：`--transition-slow` 0.3s（medium1–2 区间）
  - 大面积/全屏转场：0.45–0.6s（long 区间）

### 13.2 属性分类铁律（源自 M3 弹簧体系）

- **几何属性**（位移/尺寸/圆角）：可用 spatial 曲线，允许轻微过冲，仅在"记一笔成功"这类庆祝时刻使用回弹
- **非几何属性**（颜色、不透明度、阴影）：**永远 effects 类曲线，禁止任何回弹**——透明度弹跳会被感知为故障

### 13.3 具体场景

- 弹窗出现：从下方 20px 滑入并淡入，0.3s，滑入减速收尾（emphasized decelerate `(0.05, 0.7, 0.1, 1)`）
- 标签栏切换：指示/颜色渐变 0.2s
- 按钮按下：背景色变化 0.15s
- 涟漪（可选）：从触点扩散 ~450ms 消散 350ms
- 尊重 `prefers-reduced-motion`：开启时去除位移、保留 ≤0.15s 的淡入淡出

---

## 十四、可访问性（MD3 基础要求）

- **触控目标**：可点击区域 ≥48×48px（视觉尺寸可以更小，用 padding 撑开）；指针设备（桌面）≥44×44px；相邻目标间距 ≥8px
- **对比度**：正文小字 ≥4.5:1；大字（18px+ 或 14px bold+）、图标、组件容器 ≥3:1；禁用态豁免；成组元素（一排按钮）每个都须与背景达 3:1
- **焦点可见**：键盘聚焦必须显示焦点环（2px `primary` 外描边 + 2px 偏移），不得 `outline: none` 裸删
- **链接**：必须带下划线，不只靠颜色
- **状态不只靠颜色**：错误/选中需同时有文字、图标或字重变化
- **标签**：纯图标按钮必须有 aria-label，描述**用途**而非形状（"搜索" 而非 "放大镜"）；装饰性图标 `aria-hidden`
- **语义优先**：使用原生 button/输入控件与正确标题层级（H1–H6 不跳级），屏幕阅读器按 DOM 顺序朗读
- **金额可读**：数字+单位组合提供 aria-label 完整读法

---

## 十五、响应式布局

### 15.1 断点

| 名称 | 宽度 | 布局 | MD3 窗口尺寸类别 |
|---|---|---|---|
| 手机 | < 600px | 单列，固定宽 100% | Compact |
| 小平板 | 600-905px | 单列，内容区最大宽度 600px，居中 | Medium |
| 平板 | 905-1240px | 双列（左侧列表 360px，右侧详情） | Expanded |
| 桌面 | ≥ 1240px | 三列（左侧列表 360px，中间详情 flex:1，右侧 320px），容器最大 1440px | Expanded |

**MD3 规则**：同一布局区域在各窗口尺寸下**色彩映射保持不变**（正文区永远 `--color-bg`，导航区永远白底），宽屏只增加层级色阶，不换色系。

### 15.2 布局规则

- 内容区水平居中：`margin: 0 auto`
- 宽屏容器最大宽度：`1440px`
- 宽屏内容区域需要有左右 `padding`：`16px`
- 左侧列表区域宽度：`360px`
- 右侧工具栏宽度：`320px`

### 15.3 宽屏列表项

```css
background: #FFFFFF;
border-radius: 12px;
padding: 12px 16px;
margin: 0 8px;
margin-bottom: 4px;
box-shadow: none;
transition: background-color 0.2s ease;
```

**Hover 态**：`background-color: #F5F5F5`

### 15.4 规则

- 手机端隐藏右侧工具栏，统计面板折叠或底部弹窗显示
- 平板端隐藏右侧工具栏，统计面板底部弹窗显示
- 桌面端三列布局完整展示
- 底部弹窗（bottom sheet）移动端全宽、顶部圆角 `radius-l`、含拖拽把手；宽屏时改为居中对话框或侧栏（side sheet 思路）

---

## 十六、垂直节奏与层级

### 16.1 垂直节奏

- 区块标题与内容：`margin-bottom: 12px`
- 区块之间：`margin-bottom: 24px`
- 页面上下边距：`padding-top/bottom: 24px`

### 16.2 垂直间距规则

- 列表项间距：`gap: 4px`
- 表单元素间距：`margin-bottom: 16px`
- 标签与输入框间距：`margin-bottom: 8px`
- 弹窗内元素间距：`margin-bottom: 16px`

### 16.3 层级（z-index / 海拔对应）

| 层级 | 元素 | MD3 静止海拔 |
|---|---|---|
| 1 | 页面背景 | 0 |
| 2 | 卡片、内容区块 | 0~1 |
| 3 | 按钮、输入框 | 0~1 |
| 4 | 下拉菜单、Tooltip | 2 |
| 5 | 弹窗、Toast | 3~5 + scrim |

海拔语义仅用于组件间前后关系；交互抬升遵循 4.2 节"hover +1 档"。

---

## 十七、免责声明与支付页

### 17.1 免责声明

- 位置：列表页面底部
- 样式：13px，颜色 `#9AA0A6`，居中对齐
- 与列表间距：`margin-top: 24px`
- 与页面底部间距：`margin-bottom: 16px`

### 17.2 支付页面布局

- 左右两侧 padding：`16px`
- 内容区域最大宽度：`600px`，居中
- 支付详情卡片与功能入口卡片间距：`16px`
- 功能入口卡片与支付记录卡片间距：`24px`

---

## 审查清单

当审查代码时，逐项检查：

**色彩**
- [ ] 背景色是否使用中性灰（#FAFAFA / #FFFFFF / #F5F5F5），无大面积彩色背景
- [ ] 强调色是否仅用于按钮、链接、选中态等小面积元素
- [ ] 颜色是否按角色配对使用（primary 底 + on-primary 字），无混搭低对比组合
- [ ] 是否存在硬编码颜色值（应使用 CSS 变量）
- [ ] 分割线是否用浅色 `border-light`（outline-variant），输入框边框用 `border`（outline）

**排版与数字**
- [ ] 字号是否符合规范（标题 18px、正文 15px、说明 13px）
- [ ] 金额/日期等变动数字是否 `tabular-nums`
- [ ] 链接是否带下划线、状态是否有颜色之外的第二信号

**组件**
- [ ] 卡片样式是否符合规范（白底、圆角 12px、padding 16px、shadow-m；同区单一变体）
- [ ] 输入框样式是否符合规范（高度 40px、圆角 8px、灰底 #F5F5F5）
- [ ] 按钮样式是否符合规范（主操作 filled 且同屏唯一、圆角 8px、高度 40px）
- [ ] 弹窗样式是否符合规范（白底、圆角 12px、padding 24px、scrim 32%）
- [ ] 底部导航栏是否符合规范（5 个入口、高度 56px、图标 24px）
- [ ] 列表单元格高度是否符合（56/72/88px）
- [ ] 嵌套圆角是否遵守 `inner = outer − padding`，卡片未滥加大圆角

**间距与层级**
- [ ] 间距是否遵循 4px 基准网格，且优先 padding/gap 而非子元素 margin
- [ ] 表单布局是否垂直堆叠，间距 16px
- [ ] 列表项间距是否合适（gap: 4px）
- [ ] 阴影是否克制（色差优先、hover 抬升一档、无彩色阴影）

**交互与动效**
- [ ] hover/focus/pressed 是否用状态层百分比（8/12/10%），disabled 是否 12%/38%
- [ ] 触控目标是否 ≥44px（推荐 48px），相邻目标间距 ≥8px
- [ ] 动画过渡是否使用标准缓动函数和时长档位
- [ ] 颜色/透明度动画是否无回弹；位移/尺寸动画是否仅几何属性
- [ ] 键盘焦点是否可见，禁用 `outline: none` 不留替代

**响应式**
- [ ] 响应式布局是否正确处理各断点，区域色彩映射跨尺寸一致

---

## CSS 变量定义模板

生成代码时，确保在全局样式中定义以下变量：

```css
:root {
  /* 背景色（surface / surface-container 三级简化） */
  --color-bg: #FAFAFA;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #F5F5F5;

  /* 强调色 */
  --color-primary: #1A73E8;
  --color-primary-light: #E8F0FE;
  --color-on-primary: #FFFFFF;

  /* 文字色 */
  --color-text-primary: #202124;
  --color-text-secondary: #5F6368;
  --color-text-tertiary: #9AA0A6;
  --color-text-on-primary: #FFFFFF;
  --color-text-link: #1A73E8;

  /* 功能色 */
  --color-success: #34A853;
  --color-error: #EA4335;
  --color-warning: #FBBC04;
  --color-info: #4285F4;

  /* 边框色（outline / outline-variant） */
  --color-border: #E0E0E0;
  --color-border-light: #EEEEEE;

  /* 状态层（MD3 state layers） */
  --state-hover: rgba(0, 0, 0, 0.08);
  --state-focus: rgba(0, 0, 0, 0.12);
  --state-pressed: rgba(0, 0, 0, 0.1);
  --state-disabled-container: rgba(0, 0, 0, 0.12);
  --state-disabled-content: rgba(0, 0, 0, 0.38);
  --scrim: rgba(0, 0, 0, 0.32);

  /* 间距 */
  --space-xxs: 4px;
  --space-xs: 8px;
  --space-s: 12px;
  --space-m: 16px;
  --space-l: 24px;
  --space-xl: 32px;
  --space-xxl: 48px;

  /* 圆角（MD3 shape scale 裁剪子集） */
  --radius-s: 8px;
  --radius-m: 12px;
  --radius-l: 16px;
  --radius-full: 9999px;

  /* 字号 */
  --font-size-display: 28px;
  --font-size-headline: 22px;
  --font-size-title: 18px;
  --font-size-subtitle: 16px;
  --font-size-body: 15px;
  --font-size-caption: 13px;
  --font-size-overline: 12px;

  /* 阴影（约当 MD3 海拔 1 / 2~3 / 4~5） */
  --shadow-s: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-m: 0 2px 8px rgba(0, 0, 0, 0.1);
  --shadow-l: 0 4px 16px rgba(0, 0, 0, 0.12);

  /* 过渡 */
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  /* MD3 标准曲线（新代码空间动效可选用） */
  --ease-m3-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-m3-decelerate: cubic-bezier(0.05, 0.7, 0.1, 1);
  --ease-m3-accelerate: cubic-bezier(0.3, 0, 0.8, 0.15);
}

/* 键盘焦点环（可访问性基线） */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* 减弱动画 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
```

---

## 参考资料

- Material Design 3 官网：https://m3.material.io （Foundations: color roles / elevation / shape / typography / motion / spacing / icons / design tokens）
- M3 Expressive 更新：https://m3.material.io/blog/building-with-m3-expressive ；I/O 2026 动态：https://m3.material.io/blog/whats-new-at-io26
- Token 数值交叉核对：androidx.compose.material3.tokens（ShapeTokens / TypeScaleTokens / ExpressiveMotionTokens）与 material-foundation/material-color-utilities
