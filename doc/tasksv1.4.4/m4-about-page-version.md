# M4 - 关于页 + 版本单一真值源（REQ-008 / REQ-009）

> 对应设计 §五（决策 D4 版本真值）。目标：版本号唯一定义于 `backend/app/constants.py::APP_VERSION="1.4.4"`，经无鉴权 `GET /api/version` 返回；设置页新增「关于」入口卡 + 二级页 `/settings/about`（应用卡+核心优势+独特功能+技术实现白话），前端零硬编码版本字面量。
> 涉及文件：新增 `backend/app/constants.py`、`backend/app/routers/version.py`、`backend/tests/test_version.py`、`frontend/src/api/version.js`、`frontend/src/pages/SettingsAboutPage.vue`、**`frontend/src/pages/__tests__/SettingsAboutPage.test.js`（用户裁定 2026-09-27：新建独立文件，设计给的「或追加 SettingsSubPages.test.js」两可作废——M4 不触碰 M1/M2 在途共用文件）**；改 `backend/app/main.py`（单行 import + include_router + version 参数替换，**M2 之后合入**，§0.2 注）、`frontend/src/router/index.js`、`frontend/src/pages/SettingsPage.vue`。
> 依赖：**M2 先合**（main.py 串行）；其余零文件交叉，可与 M1/M3/M5 并行。
> 行号为设计快照参考位，开工以 grep 定位为准。

---

## 1. 后端：真值源与端点（D4）

- [x] 1.1 新文件 `backend/app/constants.py`：`APP_VERSION: str = "1.4.4"`——**全仓唯一定义点**，前端不镜像
- [x] 1.2 新文件 `backend/app/routers/version.py`：`router = APIRouter(prefix="/api/version", tags=["版本"])`；`@router.get("")` 返回 `success_response(data={"version": APP_VERSION}, message="ok")`；**无鉴权**（只读公开信息，「关于」页未登录可达场景不白屏）
- [x] 1.3 `main.py`：`include_router(version.router)`；约 :102 `version="1.1.0"` → `version=APP_VERSION`
- [x] 1.4 `main.py` 约 :167 无 dist 兜底响应**删除** `"version": "1.0.0"` 键（前端零消费方，删键即消歧）
- [x] 1.5 `frontend/package.json` 版本字段**不动**（`0.0.0` 为脚手架字段，§0.6 红线）

## 2. 前端：API 与入口

- [x] 2.1 新文件 `frontend/src/api/version.js`：`getAppVersion()` → `request.get('/version')` 解包 `data.version`（沿既有 api 文件同款写法——拦截器已解 `{code,data}` 外壳）
- [x] 2.2 `SettingsPage.vue` 账号卡之后新增「关于」入口卡（与既有入口卡同款结构：`entry-avatar` + `mdi-information-outline` + 标题「关于」+ 副标题「版本与应用介绍」+ `mdi-chevron-right`），`v-list-item to="/settings/about"`
- [x] 2.3 `router/index.js` 新路由 `{ path: '/settings/about', name: 'SettingsAboutPage', component: SettingsAboutPage.vue, meta: { title: '关于' } }`；沿用全局登录守卫，**不单设 public**

## 3. 前端：`SettingsAboutPage.vue`（新页面）

- [x] 3.1 页头：返回箭头 `$router.back()` + 标题「关于」；四个 `page-card` 区块，复用全局 `section-block`/`section-title` 类，**不新增样式体系**
- [x] 3.2 区块一·应用卡：`Money App · 个人记账`；版本号 `v-if="version"` 显示 `版本 {{ version }}`，onMounted 调 `getAppVersion()`；**失败 → 整行不渲染，不留占位错字**；页面内**无任何硬编码版本字面量**
- [x] 3.3 区块二·核心优势（**5 条定稿，用户裁定 2026-09-27**：设计 §5.2 六句中「快速记账模板」并入首条，其余四句逐字独立成条）：
  1. 收支一笔记全（金额/分类/标签/备注/消费时间），相同账单记 2 次自动纳入快速记账模板
  2. 预设+自定义分类与标签双维度
  3. 月度预算与分类预算盯进度
  4. 统计看板（分类柱状、月度趋势、预算概览）
  5. 多人各记各的（数据按登录用户隔离）
  - 措辞以设计 §5.2 原文为源只做拼接，**不做扩写**；README Features:17-23 仅溯源参考
- [x] 3.4 区块三·独特功能：多来源账单导入——CSV/Excel/SQL 直传，支付宝/微信/Cashew 导出文件自动识别格式，识别不了可逐列手动指认；分类对不上有兜底链「映射→归入→自动匹配→其他」，一行不丢；数据回溯可撤销
- [x] 3.5 区块四·技术实现（白话）：数据存在你自己部署的服务器上，不经过任何第三方；导入不怕格式不对（认不出来就手动指认，实在对不上归类兜底不丢账）；全应用单文件数据库，备份即拷一个文件
- [x] 3.6 全局口径：文案全部本地静态；**无网址、无外链、无部署命令**（REQ-009 验收）；深浅主题走既有 `--v-theme-*` 语义色，不新增色值

## 4. 测试

### 4.1 后端（新 `backend/tests/test_version.py`）

- [x] 4.1.1 `GET /api/version` → 200、`code==0`、`data.version == constants.APP_VERSION` 逐字等
- [x] 4.1.2 未登录（无 token）→ 200（无鉴权口径）
- [x] 4.1.3 `FastAPI().version == APP_VERSION`（openapi 元数据同源）

### 4.2 前端（新文件 `SettingsAboutPage.test.js`，用户裁定落点）

- [x] 4.2.1 路由 `/settings/about` 渲染页面组件存在
- [x] 4.2.2 mock `getAppVersion` 返回 `"9.9.9"` → 页面显示「版本 9.9.9」（接口源唯一断言）；reject → 版本行不渲染、页面其余部分正常
- [x] 4.2.3 源码正则：`SettingsAboutPage.vue` 不含 `\d+\.\d+\.\d+` 字面量、不含 `http`、不含 `docker|uvicorn|npm|python` 部署字样
- [x] 4.2.4 `SettingsPage.vue` 含 `to="/settings/about"` 入口

## 5. 验收门槛

- [x] 5.1 本模块前后端测试全绿；全量 `pytest` / `npx vitest run` 绿（对向泳道在途红灯按 E3 归属登记）
- [x] 5.2 mypy 基线零新增；ruff clean；eslint 基线零新增
- [x] 5.3 红线自查：`frontend/package.json` 未动；main.py 改动仅 §1.3/1.4 所列单行级；全仓 grep `"1.1.0"|"1.0.0"`（后端范围）确认版本字面量只剩 constants.py 一处真值 + 无关语义命中（notes 抄录命中清单）
- [x] 5.4 pathspec 精确提交：§「涉及文件」全清单 + 本任务文件；不 push
- [ ] 5.5 **收尾顺带项登记进 progress.md 终验**（不在本模块改 README）：README 版本政策处加一句「版本号唯一定义于 `backend/app/constants.py`」
- [ ] 5.6 真机项不勾选、抄入人工清单：关于页深浅两主题截图；设置页进出返回路径通畅

**验收标准（REQ-008/009）**：「关于」页版本与后端真值逐字一致、改常量即全站生效前端零改动；正文无部署命令无外链；深浅主题渲染正常。
