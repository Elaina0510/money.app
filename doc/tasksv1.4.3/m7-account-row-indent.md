# M7 - 设置页账号区用户行头像缩进对齐（需求七）

> 对应需求七（设计 §七）。账号区块用户行整体右移 44px（=标题行头像 36px + mr-2 8px），与标题行图标文字起点同列缩进，与导入导出区块内层列表项二级缩进模式统一。
> 涉及文件：`frontend/src/pages/SettingsPage.vue`（账号区 :226-257）。
> 依赖：无。与 M5/M8 同文件区域无交叉，可并行。

---

## 1. 实现（设计 §7.2）

- [x] 1.1 scoped 样式新增：`.account-user-row { padding-left: 44px; }`（注释标注 = 标题行头像 36px + mr-2 8px 同列缩进来源）
- [x] 1.2 模板 :234 登录分支：`<div v-if="isLoggedIn" class="account-user-row d-flex align-center justify-space-between mt-2">`
- [x] 1.3 未登录分支（:250-256「去登录」行）同挂 `account-user-row` 类，两分支缩进一致
- [x] 1.4 头像本身尺寸/配色不动；退出按钮随容器右移，`justify-space-between` 保持行右缘对齐

## 2. 边界自检（设计 §7.3）

- [x] 2.1 宽屏：缩进为定值 px，卡片变宽对齐节奏不变
- [x] 2.2 用户名超长：不改文本溢出行为（超界属既有现状，不在本模块扩大范围）

## 3. 测试

- [x] 3.1 `SettingsPage.vue ?raw` 断言：含 `.account-user-row` 类定义、模板用户行绑定该类、样式含 `padding-left: 44px`

## 4. 验收与质量门槛

- [x] 4.1 `npm test` 全绿；`npm run lint` 通过
- [ ] 4.2 手工自查：账号卡片内用户行头像与标题行图标形成清晰 44px 同列缩进、不再贴左缘；明暗主题 × 竖/宽屏四格
