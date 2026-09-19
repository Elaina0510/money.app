# Money App v1.4.2 总体进度

> 基于 v1.4.1 版本，围绕分类管理（图标选择器/排序/拖拽）、设置二级页面容器层级、标签管理分页、快速记账模板删除、统计图表动画及设置页图标视觉统一进行优化与缺陷修复。
> 需求文档：`doc/proposalv1.4.2.md`　详细设计：`doc/detailed-designv1.4.2.md`

---

## 模块清单

- [x] [M1 - 分类图标精选网格选择面板](m1-category-icon-picker.md) —— 需求一
- [x] [M2 - 新增分类默认排序 +「其他」固定置尾](m2-category-default-sort.md) —— 需求二
- [ ] [M3 - 分类列表拖拽排序（含批量重排接口）](m3-category-drag-sort.md) —— 需求三
- [ ] [M4 - 设置二级页面统一卡片图层容器](m4-settings-page-card-container.md) —— 需求四
- [ ] [M5 - 标签解除 20 条上限 + 分页展开](m5-tags-pagination.md) —— 需求五
- [ ] [M6 - 快速记账删除模板修复（按签名忽略）](m6-quick-template-delete.md) —— 需求六
- [x] [M7 - 统计页分类柱状图过渡动画](m7-bar-chart-animation.md) —— 需求七
- [ ] [M8 - 设置页/统计页入口图标颜色与位置统一](m8-entry-icon-unify.md) —— 需求八

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
| M3 | 全栈 | ☐ 未开始 | | 新增依赖，build 包体增量待记录 |
| M4 | 前端 | ☐ 未开始 | | |
| M5 | 全栈 | ☐ 未开始 | | |
| M6 | 全栈 | ☐ 未开始 | | 附迁移脚本，发布备忘需登记 |
| M7 | 前端 | ✅ 完成 | c2e6e55 | vitest 155/155（M7 新增 5 例）；lint/build 通过；手工项 3 条待抽检 |
| M8 | 前端 | ☐ 未开始 | | |

## 测试结果记录

| 时点 | pytest | vitest | mypy | ruff | lint | build |
|------|--------|--------|------|------|------|-------|
| M1 提交前 | —（纯前端） | 171/171 | — | — | 0 error（CsvMappingDialog 2 存量 warning） | 通过 |
| M7 提交前 | —（纯前端） | 155/155（并行基线不同，含 M1 后为 171 基线） | — | — | 通过 | 通过 |
| M2 提交前 | 161/161 | 172/172 | 基线零新增（107 存量） | 通过 | 通过 | 通过 |

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

## 阻塞清单

（暂无）

## 备注

- M1/M7 完成报告 notes 要点：M1 精选集 108 项已逐项比对后端预设 15 图标 + mdi-cash/mdi-circle；用例 2c 为设计点名口径反转改写（icon 由面板回抛）；M7 用 scoped CSS 类替代设计片段内联 style（样式值一致），vue-chartjs 5.3.3 实测对 props 建 watch 自动 update，无需手动调用。
- M2 完成报告 notes 要点：① `_next_sort_order` 以 `min(base+1, other.sort_order-1)` 钳制实现（对设计 §2.2.2 字面式的裁定性偏离——字面式在 other.sort==base+1 时会让「其他」被决胜挤出末位，违反硬约束；已加专项自愈用例固化）；② 用例 2c 再改写为载荷去 sort_order（M1 面板断言全保留），另新增 2c-2 CoW 用例；③ 交接 M3：moveCategory 上移/下移按钮本期保留但后端已忽略单个 PUT 的 sort_order（M3 落地前两按钮实际不生效，属设计后果）；`_visible_categories`/`_is_other_category`/`_is_other_row` 已就位供 reorder 复用；前端 `isOther()` 归 M3。
- 工作区遗留（未跟踪、不影响提交）：`frontend/dist/assets/` 下 21 个 build 新 hash 产物 + `frontend/mdi-valid-names.txt`（M1 核对临时文件）。清理命令被权限系统拦截，留待终验 dist 重建（P4）时一并处置。

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
