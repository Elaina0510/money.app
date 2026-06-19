# 本地开发测试注意事项

## 一、环境一致性

### 数据库

- 本地和服务器都使用 SQLite，确保 SQL 语法兼容
- **不要使用 PostgreSQL/MySQL 特有语法**，如：
  - `FILTER (WHERE ...)` → 改用 `CASE WHEN ... THEN ... ELSE ... END`
  - `DELETE ... RETURNING` → 改用分步操作（先查询再删除）
  - `SELECT ... FOR UPDATE` → SQLite 不支持行级锁
  - 注意：`ON CONFLICT ... DO UPDATE` 在 SQLite 3.24+ 中可用，Python 3.11+ 自带 SQLite 3.39+
- 测试时使用与服务器相同版本的 Python 和依赖

### Python 版本

- 服务器直接部署使用 Python 3.11+，本地开发也应使用 3.11+
- **Docker 模式使用 Python 3.12**（见 Dockerfile），与直接部署版本略有差异，注意测试兼容性
- 使用虚拟环境（`venv`）隔离依赖

---

## 二、测试清单

### 每次修改代码后，必须测试以下功能

| 功能      | 测试要点             | 常见问题       |
| --------- | -------------------- | -------------- |
| 登录/注册 | 正常登录、Token 过期 | SECRET_KEY 配置不一致 |
| 记账      | 新增、编辑、删除记录 | user_id 关联   |
| 主页      | 收支汇总、余额显示   | SQL 语法兼容性 |
| 统计页    | 趋势图、分类统计     | SQL 语法兼容性 |
| 预算      | 预算设置、超支提醒   | 日期范围计算   |
| 标签      | 标签管理、关联记录   | 外键约束       |
| 附件      | 上传、预览、删除     | 文件路径、权限 |
| 导入导出  | CSV/Excel 导入导出   | 编码、格式     |
| 数据回溯  | 操作历史、撤销功能   | 历史记录完整性 |
| **边界情况** | 空值、特殊字符、超长输入 | 数据验证、SQL 注入 |
| **并发测试** | 多用户同时操作       | 数据库锁、竞态条件 |
| **性能测试** | 大量数据下的响应时间 | SQL 查询效率   |

**代码中已实现的功能模块**（backend/app/routers/）：
- auth.py - 登录注册、JWT 认证
- records.py - 记账管理、快速模板
- categories.py - 分类管理
- tags.py - 标签管理
- statistics.py - 数据统计、趋势分析
- budgets.py - 预算管理
- attachments.py - 附件管理
- export.py - 数据导出
- import_.py - 数据导入
- history.py - 操作历史

### 测试步骤

```bash
# 1. 启动后端
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 2. 启动前端（新终端）
cd frontend
npm run dev

# 3. 浏览器访问
# 前端: http://localhost:5173
# 后端 API: http://localhost:8000/docs

# 4. 按测试清单逐项测试
```

**测试要点**：
- **登录注册**：测试新用户注册、登录、Token 过期后的行为
- **记账功能**：测试新增、编辑、删除记录，测试快速模板
- **统计功能**：测试日/周/月/年统计，测试分类统计、标签统计、趋势图
- **预算功能**：测试预算设置、超支提醒、预算概览
- **导入导出**：测试 CSV/Excel 导入导出，测试编码兼容性
- **附件功能**：测试图片上传、预览、删除，测试文件大小限制
- **数据回溯**：测试操作历史、撤销功能

**自动化测试**：

项目已包含 pytest 测试用例（`backend/tests/`），提交前应运行：

```bash
cd backend
python -m pytest -v
```

测试覆盖：记账、分类、标签、预算、附件、统计、导入导出、历史、数据隔离等。如果有测试失败，不要提交代码。

**API 测试**：
- 访问 http://localhost:8000/docs 查看 Swagger 文档
- 使用 Swagger UI 测试各个 API 端点
- 检查响应格式和错误处理

---

## 三、SQL 兼容性检查

### 禁止使用的语法

```sql
-- ❌ PostgreSQL 特有，SQLite 不支持
sum(amount) FILTER (WHERE type = 'income')

-- ❌ PostgreSQL 特有，SQLite 不支持（使用 INSERT OR IGNORE 或分步操作）
DELETE FROM ... RETURNING *

-- ❌ MySQL 特有，SQLite 不支持
INSERT IGNORE INTO ...

-- ❌ SQLite 不支持（无行级锁）
SELECT ... FOR UPDATE

-- ❌ SQLite 不支持（需先用 PRAGMA table_info 检查再 ALTER TABLE）
ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
```

### 正确的写法

```sql
-- ✅ SQLite 兼容：条件聚合
sum(CASE WHEN type = 'income' THEN amount ELSE 0 END)

-- ✅ SQLite 兼容：插入或更新（SQLite 3.24+）
INSERT INTO ... VALUES (...) ON CONFLICT (id) DO UPDATE SET ...

-- ✅ SQLite 兼容：插入或忽略
INSERT OR IGNORE INTO ... VALUES (...)

-- ✅ SQLite 兼容：删除并获取数据（分两步操作）
-- 第一步：查询要删除的数据
SELECT * FROM records WHERE id = 1;
-- 第二步：执行删除
DELETE FROM records WHERE id = 1;

-- ✅ SQLite 兼容：日期格式化
strftime('%Y-%m', consume_time)

-- ✅ SQLite 兼容：添加列（先检查是否存在）
PRAGMA table_info(records);
-- 如果列不存在，再执行 ALTER TABLE
ALTER TABLE records ADD COLUMN new_column TEXT;
```

> **注意**：
> - SQLite 不支持在子查询中使用 DELETE + RETURNING，请使用 Python 代码分两步执行
> - SQLite 3.24+ 支持 `ON CONFLICT ... DO UPDATE SET ...`，推荐使用
> - SQLite 3.35+ 支持 `RETURNING` 子句，但建议使用分步操作以确保兼容性

### 检查 SQLite 版本

```bash
# 命令行检查
sqlite3 --version

# Python 中检查
import sqlite3
print(sqlite3.sqlite_version)

# 在服务器上检查
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

**版本说明**：
- SQLite 3.24+ 支持 `INSERT ... ON CONFLICT ... DO UPDATE SET ...`（推荐使用）
- SQLite 3.35+ 支持 `RETURNING` 子句
- Python 3.11+ 自带 SQLite 3.39+
- Python 3.12+ 自带 SQLite 3.41+

**实际代码中的 SQLite 兼容写法**（statistics_service.py）：
```python
# 使用 case() 函数实现条件聚合（兼容 SQLite）
func.sum(case((Record.type == "income", Record.amount), else_=0))

# 使用 strftime() 进行日期格式化（SQLite 支持）
func.strftime(date_format, Record.consume_time)
```

### 自检方法

在写 SQL 或使用 ORM 的聚合函数时，问自己：

1. 这个语法在 SQLite 中能跑吗？
2. 我在本地用 SQLite 测试过吗？
3. 这个查询在服务器上会报错吗？

---

## 四、部署前检查

### 代码提交前

- [ ] 本地测试通过（所有功能正常）
- [ ] **自动化测试通过**（`cd backend && python -m pytest -v`）
- [ ] 没有使用数据库特定语法（FILTER、RETURNING 等）
- [ ] 前端代码已构建（`npm run build`）
- [ ] `frontend/dist/` 已提交到 git
- [ ] 确认 SECRET_KEY 已配置（生产环境不要使用默认值）
- [ ] **隐私文件检查**：`git status` 确认没有 `.env`、`money.db`、`uploads/`、`*.tar.gz` 被意外加入
- [ ] 没有产生意外文件（如 `backend/=5.0` 之类的命令误输出）

### 部署到服务器后

- [ ] 浏览器访问正常
- [ ] 登录功能正常
- [ ] 主页统计数据正常
- [ ] 统计页图表正常
- [ ] 记账功能正常（新增、编辑、删除）
- [ ] 数据库数据完整

---

## 五、常见部署问题

| 问题                | 原因                  | 解决方案                 |
| ------------------- | --------------------- | ------------------------ |
| 统计数据为 0        | SQL 语法不兼容 SQLite | 改用 CASE WHEN           |
| 端口 80 被占用      | nginx 占用端口        | `systemctl stop nginx` |
| supervisor 启动失败 | 配置文件路径错误      | 检查 `/etc/supervisord.d/money-app.ini` |
| 数据库只读          | 文件权限问题          | `chmod` 或用 root 执行 |
| pip 安装超时        | 服务器访问外网较慢    | 使用阿里云镜像加速       |
| git clone 失败      | 服务器访问 GitHub 慢  | 用 tar 包上传或配置代理  |
| SECRET_KEY 未配置   | .env 文件缺失         | 运行 `deploy.sh` 自动生成 |
| 端口 8000 无法访问  | Docker 模式端口映射   | 检查 `docker-compose.yml` 端口映射 |

---

## 六、调试技巧

### 查看服务器日志

```bash
# 实时查看输出日志
tail -f /var/log/money-app.out.log

# 实时查看错误日志
tail -f /var/log/money-app.err.log

# 查看最近的错误
tail -30 /var/log/money-app.err.log
```

### 查看数据库状态

```bash
# 查看表结构
sqlite3 money.db ".schema records"

# 查看记录数
sqlite3 money.db "SELECT COUNT(*) FROM records;"

# 查看 user_id 分布
sqlite3 money.db "SELECT user_id, COUNT(*) FROM records GROUP BY user_id;"

# 检查数据库完整性
sqlite3 money.db "PRAGMA integrity_check;"

# 查看数据库大小
ls -lh money.db

# 查看所有表
sqlite3 money.db ".tables"

# 查看表的索引
sqlite3 money.db ".indices records"
```

### 查看进程状态

```bash
# 查看 supervisor 进程状态
supervisorctl status

# 查看 uvicorn 进程
ps aux | grep uvicorn

# 查看端口占用（Python 模式监听 80 端口，Docker 模式监听 8000 端口）
netstat -tlnp | grep :80
netstat -tlnp | grep :8000

# 查看系统资源使用
top -p $(pgrep -f uvicorn)

# 查看 Docker 容器状态（Docker 模式）
docker compose ps
docker compose logs -f
```

### 重启应用

```bash
supervisorctl restart money-app
```

---

## 七、开发流程总结

```
本地修改代码
    ↓
本地测试（所有功能 + pytest）
    ↓
构建前端（如修改了前端）
    ↓
git status 检查隐私文件
    ↓
提交代码到 git + push
    ↓
服务器 git pull
    ↓
服务器重启应用（如改了后端）
    ↓
浏览器验证
```

---

## 八、隐私与文件安全

### 绝对不能提交到 git 的文件

| 文件 | 内容 | 风险 |
|------|------|------|
| `.env` | SECRET_KEY、数据库配置 | Token 可被伪造 |
| `money.db` | 所有财务记录 | 个人隐私泄露 |
| `backend/uploads/` | 上传的图片 | 个人隐私泄露 |
| `*.tar.gz` | 可能包含上述所有文件 | 打包泄露 |

### `.gitignore` 已配置排除

项目 `.gitignore` 已排除以上文件，但以下情况仍需注意：

1. **tar 包部署**：如果用 `tar -czf` 打包代码，确保先删除 `.env`、`money.db`、`uploads/`
2. **误操作文件**：命令行误操作可能产生意外文件（如 `backend/=5.0`），提交前用 `git status` 检查
3. **文档中的敏感信息**：服务器 IP、仓库地址等在文档中使用占位符，不要写入实际值

---

## 九、数据迁移注意事项

### 数据库路径说明

- **本地开发**：`backend/money.db`
- **Python 部署模式**：`backend/money.db`
- **Docker 部署模式**：`data/db/money.db`（通过 volume 挂载）

### 本地数据迁移到服务器（Python 模式）

1. **备份服务器数据**：先备份服务器的 `money.db`
   ```bash
   cp /www/wwwroot/money-app/backend/money.db /www/wwwroot/money-app/backend/money.db.bak
   ```

2. **停止应用**：
   ```bash
   supervisorctl stop money-app
   ```

3. **上传数据库**：通过宝塔面板上传本地 `money.db` 到 `/www/wwwroot/money-app/backend/`

4. **设置权限**：
   ```bash
   chmod 664 /www/wwwroot/money-app/backend/money.db
   chown root:root /www/wwwroot/money-app/backend/money.db
   ```

5. **启动应用**：
   ```bash
   supervisorctl start money-app
   ```

6. **验证数据**：检查数据是否完整
   ```bash
   sqlite3 /www/wwwroot/money-app/backend/money.db "SELECT COUNT(*) FROM records;"
   ```

### 本地数据迁移到服务器（Docker 模式）

1. **备份服务器数据**：
   ```bash
   cp /www/wwwroot/money-app/data/db/money.db /www/wwwroot/money-app/data/db/money.db.bak
   ```

2. **停止容器**：
   ```bash
   cd /www/wwwroot/money-app
   docker compose down
   ```

3. **上传数据库**：通过宝塔面板上传本地 `money.db` 到 `/www/wwwroot/money-app/data/db/`

4. **启动容器**：
   ```bash
   docker compose up -d
   ```

5. **验证数据**：
   ```bash
   docker compose exec app sqlite3 /data/db/money.db "SELECT COUNT(*) FROM records;"
   ```

### 服务器数据迁移到本地

1. **下载数据库**：
   - Python 模式：通过宝塔面板下载 `/www/wwwroot/money-app/backend/money.db`
   - Docker 模式：通过宝塔面板下载 `/www/wwwroot/money-app/data/db/money.db`

2. **备份本地数据库**：
   ```bash
   cd h:\code\money.app\backend
   copy money.db money.db.local_backup
   ```

3. **替换本地数据库**：将下载的 `money.db` 替换到 `backend/` 目录

4. **重启本地应用**：重新启动 uvicorn 和前端

5. **验证数据**：检查数据是否完整

### 数据迁移注意事项

- ⚠️ **迁移前必须备份**：无论本地还是服务器，迁移前都要备份原数据库
- ⚠️ **停止应用再迁移**：避免数据库锁导致迁移失败
- ⚠️ **检查文件权限**：确保应用有权限读写数据库文件
- ⚠️ **版本兼容性**：确保本地和服务器的 SQLite 版本兼容
- ⚠️ **区分部署模式**：Python 模式和 Docker 模式的数据库路径不同
