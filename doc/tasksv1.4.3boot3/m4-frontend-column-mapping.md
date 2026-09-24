# M4 - 前端列映射向导（需求 A、E）

> 对应设计 §四。目标：让用户看得见「读到了哪些列」、改得了「每列当什么字段」，并在无分类列 / 无收支列两种场景下强制显式表态（设计 D8/D9/D10）。
> 涉及文件：`frontend/src/components/common/CsvMappingDialog.vue`、`frontend/src/pages/SettingsImportExportPage.vue`、`frontend/src/pages/SettingsSubPages.test.js`。
> 依赖：**契约（设计 §1.2.5 + §3.2）冻结后可与后端并行开发**，用 mock `previewData` 驱动。组件名与文件名**必须沿用**（`M5-6` 以 `?raw` 断言字面量，重命名即红）。

---

## 1. 结构约定：单弹窗三区块（不引 `v-stepper`）

- [x] 1.1 沿用 `AppDialog :max-width="480"` 外壳与既有滚动容器；**不引入新 Vuetify 组件**（仓库 `v-stepper` 零先例，设计 D19）
- [x] 1.2 区块一「来源与列」`v-if="previewData?.columns"`——SQL 弹窗复用同组件时无该字段 → 整块隐藏，观感与 v1.4.3 一致（设计 §4.3 红线）
- [x] 1.3 区块二「收支与默认分类」同用 `v-if` 绑 `previewData?.columns`
- [x] 1.4 区块三 = 既有分类/标签映射区（模板 :13-52 与其 computed :99-126 ）**原样保留，零改动**

## 2. 区块一：列角色表与样例

- [x] 2.1 方言标签：`formatLabel` 由两分支扩为六值映射——`native→本系统格式`、`cashew→Cashew 格式`、`cashew_template→Cashew 模板`、`alipay→支付宝账单`、`wechat→微信账单`、`custom→手动映射`，兜底仍 `未知格式`（SQL 侧继续落到兜底，行为不变）
- [x] 2.2 `header_row_index > 0` 时显示中文提示「已忽略 N 行账单说明文字」（N 取 `previewData.header_row_index`）
- [x] 2.3 列角色表：`v-for` over `previewData.columns`，每行 = 原列名（空列名显示为 `第 {{index+1}} 列（空列名）`）+ 角色 `v-select`（选项：不导入 `null` / 金额 / 收/支 / 分类 / 标签 / 时间 / 备注；中文 label + 值用后端同名字符串）+ 该列 `sample` 值（`text-caption`，超长省略号）
- [x] 2.4 初值：`columnRoles.value[c.index] = c.role`（来自后端建议）；用户改动**不回写** `previewData`
- [x] 2.5 样例行表格：`sample_rows` 前 5 行 + 表头行，`overflow-x: auto` 横向滚动、等宽数字（`.text-no-wrap`）；空态显示「无数据行」
- [x] 2.6 同一角色被两列选中时**前端不阻止、不报错**（后端 D3 取靠前列），仅靠样例值让用户自查（设计 §4.3）

## 3. 区块二：收支判定与默认分类

- [x] 3.1 收支 `v-radio-group`：四态 `column(按收/支列) / sign(按金额正负) / all_expense(全部支出) / all_income(全部收入)`；初值 = `previewData.suggested_type_source`
- [x] 3.2 `column` 选项**仅当** `columns` 中存在 `role === "type"` 的列时才出现在选项里（否则不显示，设计 §4.2.1）；若初值为 `column` 但该列被用户改成「不导入」，需回落为 `sign` 并在卡片内提示（不用 toast）
- [x] 3.3 「账单归入」分类 `v-select`：**仅当** `columns` 中无 `category` 角色时显示且必选；候选 = `categories` prop 的 `{label:name, value:id}`，**去掉**「— 跳过 —」与「+ 新建分类」两项（`fallback_category` 必须落到真实分类）
- [x] 3.4 载荷形状：`fallback_category = { action: "map", target_id: <选中 id> }`（对齐 `CategoryMappingItem`）
- [x] 3.5 区块二顶部一行 `text-caption` 中文说明当前口径（例：「金额负数记为支出、正数记为收入」），随选项切换而变

## 4. 禁用条件与确认载荷

- [x] 4.1 新增 computed `missingRequiredCount`：`amount` 或 `consume_time` 角色未指定 +1；无 `category` 角色且未选 `fallback_category` +1
- [x] 4.2 确认按钮 `:disabled="unmappedCount > 0 || missingRequiredCount > 0"`；禁用时在按钮上方显示缺项中文清单（复用 `missingRequired` 明细，不新增 toast，设计 U3）
- [x] 4.3 `unmappedCount`（:117-126）**逻辑零改动**（仍只遍历 `categories_in_file`，用例 10.5 依赖）
- [x] 4.4 `handleConfirm`（:162-167）载荷扩为 `{ category_mapping, tag_mapping, columns, type_source, fallback_category }`
  - `columns` = 用户最终选择的有效角色 → 列索引映射（`role !== null` 才入表）；**始终发送**（比后端推导权威，设计 §3.3 步骤 2）
  - 区块隐藏（SQL 复用）时 `columns`/`type_source`/`fallback_category` 发送 `undefined` 并在页面侧剔除，保证 SQL 请求体一字不变
- [x] 4.5 `watch(previewData)` 的自动同名预映射（:169-179）**零改动**

## 5. 页面接线（`SettingsImportExportPage.vue`）

- [x] 5.1 `handleCsvImport`（:226-243）请求体并入三字段：`columns: mapping.columns`、`type_source: mapping.type_source`、`fallback_category: mapping.fallback_category`
- [x] 5.2 成功 toast 改为 `成功导入 ${imported_count} 条` + （`skipped_count > 0` 时）`，跳过 ${skipped_count} 条` + 首个非零 `skipped_reasons` 的中文短标签（映射表：`invalid_amount→金额无法识别`、`invalid_date→日期无法识别`、`type_ignored→不计收支`、`type_unresolved→收支无法判定`、`category_unresolved→分类未指定`）
- [x] 5.3 失败 toast、`importing` 语义、`csvPreviewData` 复位、`event.target.value = ''` 复位全部不变
- [x] 5.4 `frontend/src/api/export.js` **零改动**（`importCsv` 透传对象）；`handleCsvFileSelect`（:213-224）零改动
- [x] 5.5 **需求 E 的前端半区（设计 §4.2.4，改动面极小）**
  - `accept=".csv"` → **`accept=".csv,.xlsx"`**（实测 :68；:75 的 `.sql,.db` 那一行**不动**）——本模块前端**唯一**的 DOM 改动
  - 若该输入附近已有文件格式说明文案 → 同步为「支持 `.csv` / `.xlsx`」；**没有就不新增**（不扩文案、不改措辞，U3）
  - 失败提示：**原样透出后端中文 `message`**（D27 已在服务端收口 `.xls`/超限/非法 Excel 文案），**前端不得新拼一套错误文案、也不得据扩展名自行预判**
  - 上传链路、状态名、`handleCsvFileSelect`/`handleCsvImport`/`previewCsvImport`/`importCsv` 全部**零改动、不重命名**（红线 12）

## 6. 测试（`frontend/src/pages/SettingsSubPages.test.js`）

- [x] 6.1 **用例 10.5（:1603）与 M14 动画锁（:2587）零改动**——`categoryOptions` label 逐位断言、`{action:'create'}` 无 `type`、预映射断言必须照旧通过
- [x] 6.2 M5-3（:1984）**追加**断言：`importCsv` 入参含 `columns`/`type_source`/`fallback_category` 三字段且形状正确；mock 返回 `skipped_count: 2` 时 toast 文案含「跳过」与中文原因标签
- [x] 6.3 M5-6（:2186）**追加**新 computed / 字段名字面量；被断言的既有 11 状态名 + 10 函数名**一个不改**（含 `handleCsvFileSelect`、`handleCsvImport`、`previewCsvImport`、`importCsv`、`CsvMappingDialog`）
- [x] 6.4 新增用例组「v1.4.3-boot3 CSV 列映射向导」：
  - [x] 6.4.1 mock 含 `columns` 的 `previewData` → 区块一渲染列数 = `columns.length`、角色下拉初值与 `role` 一致、样例行表格存在
  - [x] 6.4.2 `header_row_index = 16` → 提示文本含「16」
  - [x] 6.4.3 无 `category` 角色 → 「账单归入」出现且未选时确认按钮禁用；选定后可点击且载荷含 `fallback_category`
  - [x] 6.4.4 有 `type` 角色 → 四态单选出现「按收/支列」；无 `type` 角色 → 该选项不出现
  - [x] 6.4.5 把 `amount` 列改成「不导入」 → `missingRequiredCount > 0`、确认禁用、缺项提示出现
  - [x] 6.4.6 SQL 复用路径：`previewData` 无 `columns` → 区块一/二 `find` 长度为 0、confirm 载荷三字段缺席
  - [x] 6.4.7 空列名（支付宝尾随逗号）→ 显示 `第 N 列（空列名）`
  - [x] 6.4.8 `?raw` 红线：`CsvMappingDialog.vue` 源码不含 `v-stepper`、不出现 `import.*vuetify` 新增依赖
  - [x] 6.4.9 **容器标识（D29）**：mock `previewData.container === "xlsx"` → 区块一出现中文「Excel 工作表」；**`container` 字段缺席 → 该文案不渲染**（缺席是**长期合法状态**，非过渡期妥协：该字段由 **M6** 落地，M4 与其无派发先后关系；且 SQL 路径响应本来就不带它 → 等价覆盖 D18 向后兼容）。另：§5.5 的 `accept` 属性值以 `.csv,.xlsx` 逐字断言（`?raw` 或属性查询均可，不新增状态名）

## 7. 验收门槛

- [x] 7.1 `vitest` 全量绿（基线 + 本模块新增）；`eslint` 0 error（warning 不新增）
- [x] 7.2 `npm run build` 通过；本模块**不提交** `frontend/dist`（终验统一重建，设计 §0.6）
- [ ] 7.3 明暗主题 × 竖屏(<960px)/宽屏(≥960px) 观感自测一次并截图，**主观观感留人工终判**（子 Agent 不勾选该类条目）
- [x] 7.4 pathspec 精确提交：`CsvMappingDialog.vue`、`SettingsImportExportPage.vue`、`SettingsSubPages.test.js`

**验收标准（设计 §4.4）**：用户能在弹窗里看见读到的列与样例、能改每列角色、无分类列时必须显式选归入分类、缺项时确认按钮禁用且能看懂为什么；SQL 导入弹窗观感与请求体零变化。
