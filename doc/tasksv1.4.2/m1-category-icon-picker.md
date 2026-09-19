# M1 - 分类图标精选网格选择面板

> 对应需求一（设计 §一）。分类新增/编辑弹窗的图标字段改为精选记账图标网格选择面板，移除 mdi-xxx 手动文本输入。
> 涉及文件：新增 `frontend/src/constants/categoryIcons.js`、`frontend/src/components/common/CategoryIconPicker.vue`、两个测试文件；修改 `SettingsCategoriesPage.vue`、`SettingsSubPages.test.js`。
> 依赖：无。与 M2/M3 同文件（SettingsCategoriesPage.vue），按 M1 → M2 → M3 串行，本模块只改弹窗图标字段区（现 :154-161）。

---

## 1. 精选图标常量 `frontend/src/constants/categoryIcons.js`

- [x] 1.1 新建文件，导出扁平数组 `CATEGORY_ICONS`（不分组、不设 Tab），数量 90–110 之间
- [x] 1.2 文件头注释写明硬性约束（供后续维护者遵守）：
  - [x] 必须包含全部 15 个预设分类图标（`backend/app/main.py:44-82`）：`mdi-food、mdi-bus、mdi-cart、mdi-gamepad、mdi-hospital-box、mdi-home、mdi-cellphone、mdi-briefcase、mdi-bag-suitcase、mdi-receipt-text、mdi-cash-minus、mdi-wallet、mdi-gift、mdi-finance、mdi-cash-plus`
  - [x] 必须包含表单默认与全局回退图标 `mdi-cash`、`mdi-circle`
  - [x] 所有条目为 @mdi/font 7.x 中存在的合法 `mdi-*` 名
- [x] 1.3 按场景清单覆盖选图：餐饮、交通、购物、居住、日用、娱乐、医疗、教育、通讯、人情、旅行、工资、理财、副业、退款、通用票据等
- [x] 1.4 逐项核对上述硬性约束全部满足（对照 main.py 实际读取，不凭记忆）

## 2. 新组件 `frontend/src/components/common/CategoryIconPicker.vue`

### 2.1 骨架

- [x] 2.1.1 Props：`modelValue`（当前图标名）；Emits：`update:modelValue`
- [x] 2.1.2 activator 行（替代原文本框）：圆形底 32px + 16px 图标 + 图标名只读文案 + 尾端「▾ 选择图标」提示

### 2.2 展开形态（决策 D6，按屏宽分支）

- [x] 2.2.1 宽屏（≥600px）：点击 activator 在本组件下方展开区内渲染网格（`v-slide-y-transition`）
- [x] 2.2.2 窄屏（<600px）：打开全屏 `v-dialog fullscreen`，内部复用同一 Grid + 顶栏标题 +「收起/完成」
- [x] 2.2.3 Grid 样式：`grid-template-columns: repeat(8, 1fr); gap: 4px`，单元格约 40px；滚动容器 `max-height: 240px; overflow-y: auto`（展开区与全屏浮层共用）

### 2.3 选择行为

- [x] 2.3.1 点选即 `emit('update:modelValue', icon)`（单段式，无「确定」按钮），activator 预览响应式更新
- [x] 2.3.2 选中项高亮：`outline: 2px solid rgb(var(--v-theme-primary))` + 浅底；hover 有底色反馈
- [x] 2.3.3 展开区提供「收起」按钮回到表单

### 2.4 存量兼容（非选集图标）

- [x] 2.4.1 `modelValue` 不在选集时 activator 照常渲染该图标 + 尾注 chip「不在精选集，编辑需改选」
- [x] 2.4.2 不阻断表单其他字段；网格中无选中项

## 3. SettingsCategoriesPage.vue 接入

- [x] 3.1 弹窗表单图标字段（现 :154-161 的 `v-text-field`）替换为：
  ```html
  <div class="mb-3">
    <div class="text-caption text-grey mb-1">图标</div>
    <CategoryIconPicker v-model="categoryForm.icon" />
  </div>
  ```
- [x] 3.2 删除原文本输入框——全流程不再有任何任意文本图标名入口
- [x] 3.3 确认表单默认值 `mdi-cash` 不变（在选集内）；`editCategory(cat)` 回填 `cat.icon`（可能非选集，走 2.4 分支）

## 4. 测试

### 4.1 新增 `frontend/src/constants/categoryIcons.test.js`（常量守护）

- [x] 4.1.1 长度为数组、90–110 之间、无重复项
- [x] 4.1.2 覆盖清单：预设 15 图标 + `mdi-cash` + `mdi-circle` 逐项断言 ∈ 选集
- [x] 4.1.3 所有条目匹配 `/^mdi-[a-z0-9-]+$/`

### 4.2 新增 `CategoryIconPicker.test.js`（组件用例）

- [x] 4.2.1 渲染 activator 显示当前 modelValue 图标名
- [x] 4.2.2 点击 activator（宽屏）→ 网格出现、条目数 = CATEGORY_ICONS 长度
- [x] 4.2.3 点选第 n 项 → emit 对应图标名、选中项带高亮类
- [x] 4.2.4 「收起」→ 网格隐藏
- [x] 4.2.5 modelValue 为非选集名 → activator 显示「不在精选集」提示、网格无选中项

### 4.3 改写 `SettingsSubPages.test.js` 用例 2c（图标部分）

- [x] 4.3.1 `icon` 字段来源改为面板回填（不再经文本框）
- [x] 4.3.2 源码断言：`categoriesPageSource` 不再含 `图标 (mdi-\*)`

## 5. 验收与质量门槛

- [x] 5.1 `cd frontend && npm test` 全绿
- [x] 5.2 `cd frontend && npm run lint` 通过
- [ ] 5.3 手工走查（375px/1280px × 浅色/深色）：新增/编辑分类点「图标」出网格面板、点选即时预览、保存后列表显示所选图标；预设分类图标在面板中可见且选中态；存量非选集图标分类显示不受影响
- [ ] 5.4 窄屏弹窗内不出现高度挤扁（走全屏浮层分支）
