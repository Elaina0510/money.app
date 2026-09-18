# M1 - 登录页沉浸式改造

> 对应需求一：未登录时隐藏底栏/FAB/侧栏，登录页锁定滚动并居中，小屏内容超高时兜底可滚动。
> 涉及文件：`frontend/src/components/layout/AppLayout.vue`（template/script）、`frontend/src/pages/LoginPage.vue`
> 依赖：无。与 M2 同文件但改动区域不交叉（M1 改 template/script，M2 改 `<style>` 宽屏媒体查询）。

---

## 1. AppLayout.vue：登录态隐藏导航元素

### 1.1 新增路由判据

- [x] 在 `<script setup>` 中新增：`const isLoginPage = computed(() => route.path === '/login')`

### 1.2 四处条件修改（template 区）

- [x] 侧边栏抽屉（现 :4-5）：`v-show="isDesktop"` → `v-show="isDesktop && !isLoginPage"`
- [x] 汉堡按钮（现 :116）：`v-if="isDesktop"` → `v-if="isDesktop && !isLoginPage"`
- [x] FAB `.fab-add`（现 :155）：追加 `v-if="!isLoginPage"`
- [x] 底栏 `v-bottom-navigation`（现 :160）：`v-if="!isDesktop"` → `v-if="!isDesktop && !isLoginPage"`
- [x] 顶栏 `.app-top-bar` 保留不动（决策 D6：含标题与暗色切换，非导航入口）

## 2. AppLayout.vue：登录页布局锁定

### 2.1 类绑定（仅登录页挂类，非登录页布局不变）

- [x] `<v-main class="main-content" :class="{ 'main-content--locked': isLoginPage }">`
- [x] `<div class="content-overflow" :class="{ 'content-overflow--locked': isLoginPage }">`
- [x] `<div class="content-wrapper" :class="{ 'content-wrapper--bare': isLoginPage }">`

### 2.2 新增 scoped 样式

- [x] `.main-content--locked`：`height: 100dvh; min-height: 0; display: flex; flex-direction: column; overflow: hidden;`
- [x] `.content-overflow--locked`：`flex: 1; min-height: 0; overflow: hidden;`
- [x] `.content-wrapper--bare`：`height: 100%; max-width: none; margin: 0; padding: 0; zoom: 1 !important;`
  （清掉原 `padding-bottom: 100px`；登录页不参与宽屏 110% 缩放——与 M2 的 zoom 联动点）
  （实现补充：选择器写作复合形式 `.content-wrapper.content-wrapper--bare` 以提升优先级，
  避免被文件后面 `@media (max-width: 959px)` / `@media (min-width: 960px)` 中的 `.content-wrapper` 内边距覆盖；声明内容与设计完全一致）

## 3. LoginPage.vue：居中 + 滚动兜底

### 3.1 模板

- [x] 根节点 `<v-app>` 添加类：`<v-app class="login-root">`

### 3.2 样式（替代现 :233-245 的 .login-main/.login-container）

- [x] `.login-root { height: 100%; }`（承接 `content-wrapper--bare` 的 100%，断开嵌套 v-app 高度链）
- [x] `.login-main`：
  - [x] `height: 100%; min-height: 0 !important;`（断开 Vuetify `v-application__wrap` 默认 `calc(100vh - …)`，否则锁定失效）
  - [x] `overflow-y: auto;`（兜底：内容超高时可滚动）
  - [x] `display: flex; align-items: flex-start; justify-content: center;`（配合子元素 margin:auto 安全居中）
  - [x] `background: rgb(var(--v-theme-background));`
- [x] `.login-container { margin: auto; width: 100%; max-width: 400px; padding: 20px; }`（空间充足居中；超高从顶部滚动不裁切）
- [x] 删除原 `min-height: 100vh`

## 4. 单元测试（vitest）

- [x] 扩展 `AppLayout.test.js`：`route.path === '/login'` 时 FAB（`.fab-add`）、底栏（`.bottom-nav`）、侧栏、汉堡按钮均不渲染
- [x] 非登录路由回归：竖屏渲染底栏 + FAB；宽屏渲染 FAB + 汉堡按钮
- [x] 登录 → 退出 → 再登录循环中条件渲染正确

## 5. 手工验收

- [ ] 竖屏未登录打开应用：只见登录/注册卡片，无底栏、无 + 按钮，页面无法滑动，卡片垂直居中
- [ ] 宽屏未登录：无侧栏、无汉堡、无 FAB，登录卡片居中，观感 100%（不参与 zoom）
- [ ] 极小屏（320x480）切注册 Tab 触发错误提示后，超出屏高内容可滚动到全部控件
- [ ] 顶栏（标题 + 暗色切换）正常显示且可切换主题
- [ ] 登录成功进入主页后，底栏/FAB（竖屏）、侧栏/汉堡/FAB（宽屏）即时恢复

## 6. 质量门槛

- [x] `cd frontend && npm test` 通过
- [x] `npm run lint` 无新增告警
- [x] `npm run build` 构建无报错
