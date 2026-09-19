# Money App v1.4.2 总体进度

> 基于 v1.4.1 版本，围绕分类管理（图标选择器/排序/拖拽）、设置二级页面容器层级、标签管理分页、快速记账模板删除、统计图表动画及设置页图标视觉统一进行优化与缺陷修复。
> 需求文档：`doc/proposalv1.4.2.md`　详细设计：`doc/detailed-designv1.4.2.md`

---

## 模块清单

- [x] [M1 - 分类图标精选网格选择面板](m1-category-icon-picker.md) —— 需求一
- [x] [M2 - 新增分类默认排序 +「其他」固定置尾](m2-category-default-sort.md) —— 需求二
- [x] [M3 - 分类列表拖拽排序（含批量重排接口）](m3-category-drag-sort.md) —— 需求三
- [x] [M4 - 设置二级页面统一卡片图层容器](m4-settings-page-card-container.md) —— 需求四
- [x] [M5 - 标签解除 20 条上限 + 分页展开](m5-tags-pagination.md) —— 需求五
- [x] [M6 - 快速记账删除模板修复（按签名忽略）](m6-quick-template-delete.md) —— 需求六
- [x] [M7 - 统计页分类柱状图过渡动画](m7-bar-chart-animation.md) —— 需求七
- [x] [M8 - 设置页/统计页入口图标颜色与位置统一](m8-entry-icon-unify.md) —— 需求八

## 开发顺序（设计 §十一）

```
第 1 梯队（可并行）：M4（二级页容器）  M5（标签全栈）  M7（图表动画）  M8（图标统一）
                   M1（分类页弹窗 + 新组件）
第 2 梯队：M2（依赖 M1 完成弹窗字段区改动避免同文件冲突；后端可提前并行）
第 3 梯队：M3（依赖 M2 的「其他」判定助手与创建排序逻辑；前端依赖 M1/M2 后形态）
独立穿插：M6（quick_templates 全栈，仅与 M4 共享 SettingsQuickTemplatesPage.vue，按 M4 → M6 合并）
```

- 每个模块完成后独立执行：后端 `pytest`（涉及后端模块）+ 前端 `vitest run` + 手工验收清单，**通过后再进入下一模块**。

## 文件冲突矩阵（并行开发注意，设计 §0.2）

| 文件 | 涉及模块 | 建议 |
|------|----------|------|
| `SettingsCategoriesPage.vue` | M1（弹窗图标区）、M2（删排序字段）、M3（两列表+moveCategory） | 严格串行 M1 → M2 → M3；M4 后续追加外层卡壳 |
| `category_service.py` | M2（助手/create/update）、M3（reorder） | M2 先行，M3 复用其助手 |
| `SettingsPage.vue` | M5（onMounted）、M8（7 入口模板） | 区域无交叉，可并行 |
| `StatisticsPage.vue` | M7（图表卡+options）、M8（预算卡头） | 区域无交叉，可并行 |
| `SettingsQuickTemplatesPage.vue` | M4（外层卡壳）、M6（删除流程/key/弹窗） | 按 M4 → M6 合并 |
| `global.scss` | M4（`.page-card`）、M8（`.entry-avatar`） | 不同段落追加，可并行 |
| `bg-transparent pa-0` 断言（M3 v-list × M4 卡壳） | M3、M4 | 已裁定口径：`.page-card` 内 Draggable 的 v-list 保留该写法属合法；M4 §2.5/§4.2 断言收敛为"页面无透视"结构性口径，禁止整串字面量 `not.toContain`（设计 §4.3-1 字面写法在此冲突下不可直照） |
| `SettingsSubPages.test.js` | M1-M6 | 各模块只动各自用例块；标签 mock 补 `getTagsPaged` |
| 路由顺序三连 | M3 `PUT /reorder`、M5 `GET /paged`、M6 `DELETE /auto` | 均须声明在 `/{id}` 之前，错位即 422 |

## 已确认设计决策（实现约束，设计 §0.3）

| # | 决策 | 落点 |
|---|------|------|
| D1 | tags 兼容方案：`GET /api/tags` 裸数组去上限 + 新增 `/api/tags/paged` | M5 |
| D2 | 拖拽选型 `vuedraggable@next`（4.1.0，Vue3 线；latest 是 Vue2 勿装错） | M3 |
| D3 | 「其他」判定 = 名称匹配 + 禁止改名 | M2/M3 |
| D4 | 忽略名单存 `quick_templates.kind` 列，附 `migrate_to_v1.4.2.py` | M6 |
| D5 | 摘要真实数走「拉全量数组 + length」最小实现 | M5 |
| D6 | 图标面板宽屏内联展开 / 窄屏全屏浮层 | M1 |
| D7 | 需统一容器的二级页 = 分类/标签/快速记账/数据回溯；外观/导入导出为主页卡区块 | M4 |
| D8 | 旧上移/下移按钮与 `moveCategory` 随 M3 整体移除 | M3 |
| D9 | 签名金额一律 `int(round(元×100))` 分单位，入参用 `amount_cents` | M6 |

## 进度统计

| 模块 | 层 | 状态 | 完成 commit | 备注 |
|------|----|------|-------------|------|
| M1 | 前端 | ✅ 完成 | 2485880 | vitest 171/171 全绿；lint 0 error；build 通过；手工项 2 条待抽检 |
| M2 | 全栈 | ✅ 完成 | f1af0ab | pytest 161/161；vitest 172/172；mypy 基线零新增（107 存量）；ruff 通过；手工项 1 条待抽检 |
| M3 | 全栈 | ✅ 完成 | fffb606 | pytest 172/172；vitest 174/174；mypy 零新增；包体增量实测 **+79.0 kB gzip**（D2 估算 16KB 的约 5 倍，见备注，留待人工裁定）；手工项 2 条 |
| M4 | 前端 | ✅ 完成 | cbb5936 | vitest 177/177（新增 M4 3 例）；lint/build 通过；X 汇合点成立；手工项 2 条 |
| M5 | 全栈 | ✅ 完成 | 0135497 | pytest 183/183；vitest 184/184；mypy 零新增；loadTags 红线 0 命中（主 Agent 亲测）；手工项 1 条 |
| M6 | 全栈 | ✅ 完成 | c26c178 | pytest 197/197；vitest 191/191；mypy 零新增；迁移脚本自测幂等通过；手工项 1 + 部署备忘 1 |
| M7 | 前端 | ✅ 完成 | c2e6e55 | vitest 155/155（M7 新增 5 例）；lint/build 通过；手工项 3 条待抽检 |
| M8 | 前端 | ✅ 完成 | 6c6319f | vitest 189/189（新增 M8 5 例）；lint/build 通过；红线正则零误伤自证；手工项 1 条 |

## 测试结果记录

| 时点 | pytest | vitest | mypy | ruff | lint | build |
|------|--------|--------|------|------|------|-------|
| M1 提交前 | —（纯前端） | 171/171 | — | — | 0 error（CsvMappingDialog 2 存量 warning） | 通过 |
| M7 提交前 | —（纯前端） | 155/155（并行基线不同，含 M1 后为 171 基线） | — | — | 通过 | 通过 |
| M2 提交前 | 161/161 | 172/172 | 基线零新增（107 存量） | 通过 | 通过 | 通过 |
| M3 提交前 | 172/172 | 174/174 | 基线零新增（107 存量） | 通过 | 0 error | 通过 |
| M4 提交前 | —（纯前端） | 177/177 | — | — | 0 error | 通过 |
| M5 提交前 | 183/183 | 184/184 | 基线零新增（107 存量） | 通过 | 通过 | 通过 |
| M8 提交前 | —（纯前端） | 189/189 | — | — | 0 error | 通过 |
| M6 提交前 | 197/197 | 191/191 | 基线零新增（107 存量） | 通过 | 0 error | 通过 |
| **主 Agent 终验** | **197/197** | **191/191（12 files）** | 107 存量零新增 | All checks passed | 0 error（2 存量 warning） | 通过（dist 重建提交 856713c） |

## 待人工抽检清单

### M1（分类图标精选网格选择面板）
- [ ] 5.3 手工走查（375px/1280px × 浅色/深色）：新增/编辑分类点「图标」出网格面板、点选即时预览、保存后列表显示所选图标；预设分类图标在面板中可见且选中态；存量非选集图标分类显示不受影响
- [ ] 5.4 窄屏弹窗内不出现高度挤扁（走全屏浮层分支）

### M7（统计页分类柱状图过渡动画）
- [ ] 6.2 手工验收：8 月（有数据）↔9 月（全 0）来回切换，柱条与 y 轴刻度明显渐变、无瞬间跳变、无 canvas 闪白
- [ ] 6.3 切年视图、预算行下钻、前后翻期同等过渡；动画期间连续快切无报错不卡死
- [ ] 6.4 375px 真机走查帧率观感（单数据集 ≤15 柱条 750ms）

### M2（新增分类默认排序 +「其他」置尾）
- [ ] 7.3 手工验收：新建「宠物」（支出）排在该分组最后、「其他」之前；再建一个继续往后；收入分组独立；任何操作后「其他」仍在分组末尾；编辑已有分类不改位

### M3（分类列表拖拽排序）
- [ ] 8.3 手工验收：桌面鼠标 + 移动触摸均可拖动任意距离；松手刷新/重进顺序保持；「其他」拖不动、别人拖不到它后面；一次拖动仅一次保存请求、无成串 toast、无顺序闪回；支出/收入两组互不可拖
- [ ] 8.4 与 M4 合入时做一次卡壳 × 拖拽样式视觉回归；`bg-transparent pa-0` 断言口径以 M4 §2.5/§4.2（页面无透视，卡内 v-list 合法保留）为准，勿用整串字面量断言

### M4（设置二级页面统一卡片图层容器）
- [ ] 5.2 手工验收四组合（浅色/深色 × 375px/1280px）：分类/标签/快速记账/数据回溯四页，内容与设置主页观感一致——卡片浮于米白背景、四周留白与阴影可见，非文字直压背景
- [ ] 5.3 深色模式下卡片与背景对比清晰、层级同样成立

### M5（标签解除 20 条上限 + 分页展开）
- [ ] 7.3 手工验收（造 30+ 标签）：设置页摘要显示真实数量（未进过任何标签页也正确）；标签页首屏 20 个 +「展开更多」增量加载并更新计数；快速记账弹窗选到第 21+ 个标签；记一笔页按名称搜出任意标签

### M6（快速记账删除模板修复）
- [ ] 8.2 手工验收：删自动模板确认后条目立即消失，刷新/重进不出现，继续记同标签同金额账单也不复活；金额不同的新组合正常自动生成；删手动模板确认后消失且后端已删；删除失败有错误 toast 且列表原状

### M8（设置页/统计页入口图标统一）
- [ ] 6.2 手工验收四组合（浅色/深色 × 375px/1280px）：设置页全入口 + 统计页预算头，同 primary 色系圆底、同 36/20 尺寸、逐行左偏移对齐；深色模式无静态 Material 色残留；导入导出子条目圆底与卡头一致

## 阻塞清单

（暂无）

## 备注

- M1/M7 完成报告 notes 要点：M1 精选集 108 项已逐项比对后端预设 15 图标 + mdi-cash/mdi-circle；用例 2c 为设计点名口径反转改写（icon 由面板回抛）；M7 用 scoped CSS 类替代设计片段内联 style（样式值一致），vue-chartjs 5.3.3 实测对 props 建 watch 自动 update，无需手动调用。
- M2 完成报告 notes 要点：① `_next_sort_order` 以 `min(base+1, other.sort_order-1)` 钳制实现（对设计 §2.2.2 字面式的裁定性偏离——字面式在 other.sort==base+1 时会让「其他」被决胜挤出末位，违反硬约束；已加专项自愈用例固化）；② 用例 2c 再改写为载荷去 sort_order（M1 面板断言全保留），另新增 2c-2 CoW 用例；③ 交接 M3：moveCategory 上移/下移按钮本期保留但后端已忽略单个 PUT 的 sort_order（M3 落地前两按钮实际不生效，属设计后果）；`_visible_categories`/`_is_other_category`/`_is_other_row` 已就位供 reorder 复用；前端 `isOther()` 归 M3。
- M3 完成报告 notes 要点：① **包体增量（对照 D2 估算 gzip ≈16KB，实测约 5 倍，留待人工裁定是否接受；如需回落须改深导入或换库，属设计变更未自行处置）**：分类页 chunk gzip 4.39→65.56 kB（SortableJS 全量落此懒加载分片）；index chunk gzip +17.7 kB（rolldown 分片图重排，不含 vuedraggable 代码）；全站 JS gzip 328.22→407.22 kB（+79.0）。根因：vuedraggable@4.1.0 仅发 CJS/UMD 无 ESM 产物，无法 tree-shake。② 依赖核实：vuedraggable 4.1.0 + sortablejs 1.14.0，lock diff 仅两包；§5.3 未触发。③ 实现偏差：「其他」置尾取「其余保持相对次序+其他落 n」；预设行已在目标位时短路跳过 CoW；额外触碰 schemas/category.py（CategoryReorder，2.1.3 必落点）。④ 测试改写：2b 按 D8 反转为 2b/2b-2/2b-3；用例 6 清单移除 moveCategory（D8 全局删除，另加反向源码断言固化）。
- M4 完成报告 notes 要点：① P2 断言落地：不用整串 not.toContain，改「按 div 深度配对截出 .page-card 卡壳区间」结构口径；分类页卡壳内恰 2 处 bg-transparent 作 M3 Draggable 合法保留正向计数固化。② M3 交接的卡壳×拖拽视觉回归已以结构断言固化在用例 M4-3（2 个 Draggable/6 行/6 个 data-draggable/改序仅一次 reorder PUT）。③ HistoryPage 空态直接挂 page-card（原 pa-8 由卡壳内边距承担）；数据回溯页=HistoryPage 核对项已覆盖，四页均有 .page-card。④ 未跑 prettier --write（基线文件非 prettier-clean，避免越界）。
- M5 完成报告 notes 要点：① 1b 反转为「mount 后 getTags 恰一次 + 摘要即时响应不再新增请求」，用例 1 删手动 fetchTags、用例 3 因 chip 云源改本地 displayedTags 做数据铺垫改写（断言一字未减）；② 任务 5.7 页越界边界在设计原 hasMore 公式下不成立，加本地 pageExhausted 短路（total 仍取服务端真值），用例 M5-4 固化；③ mypy：新函数以 sqlmodel col() 包装避免 7 条新增 union-attr/arg-type，基线 107 零新增；④ SettingsPage 仅 onMounted 4 行，注释避开 loadTags 字面量（6b 红线 0 命中），M8 入口区未触碰。
- M6 完成报告 notes 要点：① 设计偏差（隔离性核查）：QuickTemplate 实际还有 export/import 消费方，已给 export_service 备份查询补 `kind=='manual'`（防忽略行经导入还原成幽灵模板）+ 回归用例；② 「标签不存在」按仓库 error_response 既有约定 HTTP 400+body 40002（设计文字写 404 指业务语义），据实断言；③ 用例 4 反转为签名忽略口径 + 新增 4c/4d；④ 迁移脚本 pytest 内自测（旧表→kind 列全 manual、重跑 SKIP、表不存在 SKIP）+ CLI 冒烟，money.db 未触碰；⑤ quick_templates.amount 为 REAL affinity，整元 25 亦以 Python 分换算比对覆盖；⑥ 范围外遗留（建议入发布备忘）：忽略名单不进 SQL 备份/还原，还原备份后同签名可能重新自动生成（红线 2 明确不做恢复界面）。
- M8 完成报告 notes 要点：① §3.4 唯一实质偏离：三处卡头标题「替换」为 text-body-1 font-weight-medium（Vuetify 工具类按声明序覆盖，加挂无效），按需求八第 3 条择一对齐；深色下标题白 → #E6E1E5 观感并入 6.2 走查；② 红线正则按 §5.1 两类可寻址模式扫描，StatisticsPage 不做整文件 rgba( 扫描，用例 M8-3 零误伤自证（图表语义色全保留）；③ SettingsPage 严口径 not.toContain('rgba(') 成立；④ prepend 槽渲染计数经区块内 EntrySlotHost 实现（沿用 2b 已确立的无 Vuetify 挂载事实），.entry-avatar 计数 11、36/20 尺寸与图标名有序全等。
- 主 Agent 终验（§6.2）：pytest 197/197、mypy 107 存量零新增、ruff 通过、vitest 191/191、lint 0 error、build 通过；无 blocked 模块，无重试；dist 已统一重建提交（856713c，P4 完成）；子 Agent 遗留未跟踪构建产物与临时文件已清理。包体终态：全站 JS gzip ≈ 407 kB（较基线 +79 kB，主因 M3 vuedraggable/SortableJS 落懒加载分片，见 M3 条目人工裁定项）。

## 质量门槛（沿既定口径）

- 后端：`pytest` 相关 + 全量回归；`mypy` 基线零新增；`ruff check` 通过
- 前端：`npm test`（vitest run）、`npm run lint`；M3 后 `npm run build` 复核包体
- `frontend/dist` 不随模块提交，终验统一重建
- UI 改动遵循 `doc/rules/uidesign.md`；竖屏 375px / 宽屏 1280px × 浅色/深色四组合手工走查 M1/M3/M4/M8
- 既有测试口径反转四处（易错点 10）：用例 2b（拖拽+批量重排）、2c（载荷无 sort_order）、4（自动模板按签名忽略）、1b（getTags 次数）——与模块代码同提交

## 范围外红线（本期不做）

- 编辑分类切换「类型」下拉不生效缺陷（`CategoryUpdate` 缺 type 字段）——留待后续版本
- 自动模板忽略名单的查看/恢复管理界面
- 背景图片（壁纸）功能；非选集图标的批量迁移
