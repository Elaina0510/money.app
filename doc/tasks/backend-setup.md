# 后端基础搭建任务


> **所属模块**：M0 — 项目基础设施  
> **前置依赖**：无  
> **预估工时**：1-2小时

## 任务清单

### 1. 项目初始化

- [ ] 创建 `backend/` 目录结构（`app/`, `app/models/`, `app/schemas/`, `app/routers/`, `app/services/`, `app/utils/`）
- [ ] 创建 `requirements.txt`，包含依赖：`fastapi>=0.110`, `sqlmodel>=0.14`, `aiosqlite>=0.20`, `uvicorn`, `python-multipart>=0.0.9`, `python-dotenv`
- [ ] 创建 `backend/.env` 配置文件

### 2. 应用入口

- [ ] 编写 `app/main.py` — FastAPI 应用入口，包含 CORS 中间件、静态文件挂载、路由注册
- [ ] 编写 `app/config.py` — 从 `.env` 和默认值加载配置（数据库路径、上传目录、最大文件大小等）
- [ ] 编写 `app/database.py` — SQLModel 数据库引擎、会话管理、`get_session` 依赖注入

### 3. 统一响应格式

- [ ] 编写 `app/utils/response.py` — 统一 JSON 响应格式 `{code, message, data}` 和错误码常量

### 4. 数据库初始化

- [ ] 在 `app/main.py` 中添加启动事件，执行 `create_all()` 建表
- [ ] 创建预设分类数据插入逻辑（14 条预设分类）

### 5. 验证

- [ ] 启动后端：`uvicorn app.main:app --reload --port 8000`
- [ ] 访问 `/docs` 确认 Swagger 文档正常打开
- [ ] 确认数据库文件 `money.db` 已创建且包含预设分类数据
