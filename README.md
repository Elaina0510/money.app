# Money App 💰 — 个人记账程序

一个基于 **Vue 3 + FastAPI** 的全栈个人记账应用，支持收支记录管理、分类标签体系、预算监控、数据统计看板与多用户数据隔离。

## Tech Stack

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 (Composition API) + Vuetify 3 + Pinia + Vue Router + Chart.js |
| **后端** | Python 3.12 + FastAPI + SQLModel (async) + SQLite |
| **认证** | JWT (python-jose) + bcrypt 密码哈希 |
| **质量** | pytest + Vitest + mypy strict + Ruff + ESLint + Prettier |
| **构建** | Vite + npm |

## Features

### 核心功能

- **收支记录** — 记录每一笔收入与支出，支持金额、分类、标签、备注、消费时间
- **分类与标签** — 预设分类 + 用户自定义，自由组合管理记账维度
- **预算管理** — 设置月度总预算和各分类预算，实时监控消费进度
- **统计看板** — 总览统计、分类柱状图、月度趋势折线图、预算概览
- **快速记账** — 基于历史记录的智能模板，相同账单记录 2 次后自动纳入
- **多用户数据隔离** — JWT 认证，每个用户独立管理自己的数据

### UI/UX 特性 (v1.3)

- **未保存提醒** — 记账页修改后返回时弹出确认对话框，防止数据丢失
- **日历选择器** — Material Design 风格的日历弹出组件，从点击位置展开动画
- **详情展开动画** — 点击账单条目后从该位置展开至详情页的流畅过渡
- **分类图标** — 账单列表显示各分类的专属图标，直观区分收支类型
- **模糊渐变** — 顶部标题栏和页面底部的滑动模糊渐变效果
- **宽屏适配** — 桌面端自动放大 110%，优化大屏阅读体验



## Screenshots

<p align="center">
  <img src="screenshots/首页（展开左侧边栏）.png" width="30%" alt="首页（展开左侧边栏）" />
  <img src="screenshots/深色模式首页.png" width="30%" alt="深色模式首页" />
  <img src="screenshots/登录页.png" width="30%" alt="登录页" />
</p>
<p align="center">
  <img src="screenshots/记账页.png" width="30%" alt="记账页" />
  <img src="screenshots/账单页.png" width="30%" alt="账单页" />
  <img src="screenshots/账单详情页.png" width="30%" alt="账单详情页" />
</p>
<p align="center">
  <img src="screenshots/预算页.png" width="30%" alt="预算页" />
  <img src="screenshots/设置页.png" width="30%" alt="设置页" />
</p>

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- npm

### 一键启动

```bash
# Windows (Git Bash)
bash start.sh

# 或手动启动
cd frontend && npm install && npx vite build && cd ..
cd backend && python -m venv venv && source venv/Scripts/activate && pip install -r requirements.txt && cd ..
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务启动于 `http://localhost:8000`，手机访问 `http://<本机IP>:8000`，API 文档见 `http://localhost:8000/docs`。

### 开发模式

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## Project Structure

```
money.app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置
│   │   ├── database.py          # 数据库引擎 & session
│   │   ├── models/              # SQLModel 数据模型
│   │   │   ├── record.py        # 账单记录
│   │   │   ├── budget.py        # 预算
│   │   │   ├── category.py      # 分类
│   │   │   ├── tag.py           # 标签（支持软删除）
│   │   │   ├── quick_template.py # 快速记账模板
│   │   │   ├── attachment.py    # 附件
│   │   │   └── user.py          # 用户
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── routers/             # API 路由
│   │   │   ├── auth.py          # 注册/登录
│   │   │   ├── records.py       # 账单 CRUD + 快速模板
│   │   │   ├── categories.py    # 分类 CRUD
│   │   │   ├── tags.py          # 标签 CRUD（支持搜索）
│   │   │   ├── budgets.py       # 预算 CRUD
│   │   │   ├── statistics.py    # 统计数据
│   │   │   └── attachments.py   # 附件上传
│   │   ├── services/            # 业务逻辑层
│   │   └── utils/               # 工具（auth, response）
│   └── tests/                   # pytest 测试（78 个用例）
├── frontend/
│   └── src/
│       ├── pages/               # 页面组件
│       ├── components/          # 通用/布局组件
│       │   ├── common/
│       │   │   ├── ExpandTransition.vue    # 展开动画过渡组件
│       │   │   ├── DatePickerPopover.vue   # 日历弹出选择器
│       │   │   └── ConfirmDialog.vue       # 确认对话框
│       │   └── layout/
│       │       └── AppLayout.vue # 主布局（响应式侧边栏/底部导航）
│       ├── stores/              # Pinia 状态管理
│       ├── api/                 # Axios API 调用
│       ├── router/              # Vue Router 配置
│       ├── styles/              # SCSS 全局样式
│       └── utils/               # 工具函数
├── doc/                         # 设计文档
└── start.sh                     # 一键启动脚本
```

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/records` | 账单列表（支持筛选/分页） |
| POST | `/api/records` | 创建账单 |
| GET | `/api/records/quick-templates` | 快速记账模板（自动+手动） |
| POST | `/api/records/quick-templates` | 手动添加快速模板 |
| DELETE | `/api/records/quick-templates/{id}` | 删除快速模板 |
| GET/PUT/DELETE | `/api/records/{id}` | 账单详情/编辑/删除 |
| GET/POST | `/api/categories` | 分类列表/创建 |
| PUT/DELETE | `/api/categories/{id}` | 分类编辑/删除（级联） |
| GET | `/api/tags` | 标签列表（支持 `?q=` 搜索） |
| POST | `/api/tags` | 标签创建（需关联分类） |
| PUT/DELETE | `/api/tags/{id}` | 标签编辑/软删除 |
| GET/POST/PUT | `/api/budgets` | 预算管理 |
| POST | `/api/budgets/batch` | 批量设置预算 |
| GET | `/api/statistics/summary` | 统计总览 |
| GET | `/api/statistics/category-stats` | 分类统计 |
| GET | `/api/statistics/trend` | 月度趋势 |
| GET | `/api/statistics/budget-overview` | 预算概览 |

## Testing & Code Quality

```bash
# 后端测试（78 个用例）
cd backend
pytest tests/ -v

# 类型检查
mypy backend/app --strict

# 代码风格
ruff check backend/app
ruff format --check backend/app

# 前端测试（65 个用例）
cd frontend
npm run test

# 前端代码检查
npm run lint        # ESLint
npm run format      # Prettier

# 前端构建
npm run build
```

## Version History

| Version | Highlights |
|---------|------------|
| v1.3 | UI/UX 优化：未保存提醒、日历动画、详情展开动画、分类图标、模糊渐变、宽屏适配 |
| v1.2.2 | 移动端底部导航栏、设置页一体化管理、标签搜索联想、标签软删除、账单筛选自动触发、深色模式优化 |
| v1.2.1 | 数据隔离安全加固、分类级联删除、统计柱状图、预算编辑、月份切换横条、深色模式修复 |
| v1.2 | 数据隔离、预算编辑、统计柱状图、月份切换横条、快速记账标签化 |
| v1.1 | Bug 修复、UI 改进、消费时间、账单详情、预算管理 |
| v1.0 | MVP：基本记账功能、分类管理、统计图表 |

## Roadmap

- v1.4: CSV 导入导出、数据备份恢复、统计图表增强、超支提醒
- v2.0: 移动端应用、云端同步

## License

MIT
