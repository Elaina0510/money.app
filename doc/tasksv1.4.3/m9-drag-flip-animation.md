# M9 - 分类拖拽排序 flip 让位动画（需求九）

> 对应需求九（设计 §九）。M8 单列表的 Draggable 显式配置 `:animation="180"`（sortablejs flip 让位动画），拖动中其余行连续平滑让位、落点无跳变；保存链路与 v1.4.2 零改动。
> 涉及文件：`frontend/src/pages/SettingsCategoriesPage.vue`（Draggable 配置一处）。
> 依赖：**依赖 M8**（作用于 M8 产出的单列表）。串行序 M8 → M9 → M14。

---

## 1. 实现（设计 §9.2）

- [x] 1.1 M8 单列表的 `<Draggable>` 增加 **`:animation="180"`**（150–200ms 区间取值；独立于展开类动画口径 D10，不引用 `--expand-duration`）
- [x] 1.2 拖起行跟手为 sortablejs 原生行为，现状保持；`ghost-class`/`drag-class`/`delay=150`/`delay-on-touch-only`/`touch-start-threshold=5` 全部维持 v1.4.2 值不改
- [x] 1.3 「其他」无把手不可拖 + 保存端归一化不变 → 确认 `onDragEnd` 本地归一化仅异常数据触发，正常情况 `effective === list` 零闪回
- [x] 1.4 **红线**：保存/回滚/单次 `PUT /api/categories/reorder`/toast 链路零改动（需求 9.3 明确维持 v1.4.2）

## 2. 边界自检（设计 §9.3）

- [x] 2.1 触屏拖动触底自动滚动：sortablejs 原生 scrollSensitivity 保持默认；`touch-action:none` 仍只在把手上（不杀列表滚动）
- [x] 2.2 与 M11 手势修复叠加：把手 `touch-action:none` 优先级高于容器 overscroll，月份条/页面横滑不受影响
- [x] 2.3 保存失败回滚：快照整列替换、无逐行动画（异常路径可接受：恢复瞬间 + toast）

## 3. 测试（设计 §9.4）

- [x] 3.1 vitest：`wrapper.findComponent(Draggable).props('animation') === 180`（单列表实例唯一）
  - 实现期实测：`vuedraggable@4.1.0` 声明面仅 `list/modelValue/itemKey/clone/tag/move/componentData`，`animation` 为非声明属性 → 落 `$attrs` 后透传给 Sortable，`props('animation')` 恒为 `undefined`。用例按本文件 M3 用例2b 既定的 `sortableOptionsOf()`（kebab→camel 归一）口径断言 `$attrs.animation === 180` 且归一后 `=== 180`（数值型），等价于 §9.4 意图；另加 `props()` 不含 `animation` 键的红线快照，上游若改为声明式 prop 即强制同批改断言。
- [x] 3.2 M8 改造后既有保存链路用例（成功单次 PUT / 失败回滚 / 归一化）全部保持通过

## 4. 验收与质量门槛

- [x] 4.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 4.2 **真机必测**：竖屏触摸拖动分类，其余行随拖动位置实时平滑让位、全程无跳变；松手落位顺序保持、刷新不丢
- [ ] 4.3 桌面鼠标路径同测；明暗主题走查
