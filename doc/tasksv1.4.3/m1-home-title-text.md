# M1 - 顶栏标题「首页」统一为「主页」（需求一）

> 对应需求一（设计 §一）。路由 meta 标题改「主页」单点生效；全站用户可见文案无「首页」残留。
> 涉及文件：`frontend/src/router/index.js`（仅此一处代码改动）。
> 依赖：无。批 1 可并行。

---

## 1. 源头改动与检索核实

- [x] 1.1 `router/index.js:14`：路由 `/` 的 `meta.title` 由 `'首页'` 改为 `'主页'`（icon / bottom nav / 侧栏文案本就为「主页」，不动）
- [x] 1.2 全库检索「首页」，确认用户可见文案（顶栏、页面提示、空态、对话框标题）除 1.1 外无其他残留；命中项逐条登记处置结论
- [x] 1.3 **红线**：`SettingsSubPages.test.js:204、524` 注释中的「首页」为"分页接口第一页"语义，**严禁顺手改**（设计 §1.2 实现红线，改即误义）
- [x] 1.4 确认顶栏渲染（`AppLayout.vue` `currentTitle`）与 document.title 逻辑均从 meta 取词，无需额外改动（经核实项目当前未写 document.title）

## 2. 测试

- [x] 2.1 vitest：路由表 `/` 的 `meta.title === '主页'`（就近扩展现有路由断言用例）
- [x] 2.2 vitest `?raw` 断言：`router/index.js` 源码内容不含「首页」字样

## 3. 验收与质量门槛

- [x] 3.1 `cd frontend && npm test` 全绿；`npm run lint` 通过
- [ ] 3.2 手工自查：顶栏 / bottom nav / 桌面侧栏三处同显「主页」；明暗主题无差异（纯文本改动）
