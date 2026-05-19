# 模块三：附件管理模块 (M3) — 任务分解

> **对应需求**：2.1.1 记账条目字段中的附件（图片）  
> **前置依赖**：M0 后端基础搭建完成  
> **预估工时**：2-3小时

## 任务清单

### 1. 数据模型

- [ ] 创建 `app/models/attachment.py` — `Attachment` 模型（id, record_id, filename, stored_path, file_size, mime_type, created_at）
  - [ ] 外键 `record_id` → `records(id)` ON DELETE SET NULL
  - [ ] 索引 `idx_attachments_record`

### 2. Pydantic Schema

- [ ] 创建 `app/schemas/attachment.py`：
  - `AttachmentResponse`（id, filename, url, file_size, mime_type, created_at）
  - `AttachmentListResponse`

### 3. 文件存储工具

- [ ] 创建 `app/utils/file_utils.py`：
  - [ ] `ensure_upload_dir()` — 确保 `uploads/` 目录存在
  - [ ] `generate_stored_path(original_filename)` — 按 `uploads/{year}/{month}/{day}/{uuid}.{ext}` 生成存储路径
  - [ ] `validate_file_type(filename)` — 校验文件类型（仅允许 jpg/jpeg/png/gif/webp）
  - [ ] `validate_file_size(file_size)` — 校验文件大小（最大 10MB）
  - [ ] `delete_file(stored_path)` — 删除物理文件
- [ ] 配置上传目录路径（从 `config.py` 读取）

### 4. 业务逻辑层 (Service)

- [ ] 创建 `app/services/attachment_service.py`：
  - [ ] `upload_attachment(db, file, record_id=None)` — 上传附件
    - 验证文件类型和大小
    - 生成 UUID 文件名和日期目录
    - 保存文件到 `uploads/{date_path}/{uuid}.{ext}`
    - 写入数据库记录
    - 返回附件信息（含可通过静态路由访问的 URL）
  - [ ] `get_attachment(db, id)` — 获取附件信息
  - [ ] `delete_attachment(db, id)` — 删除附件（同时删除物理文件和数据库记录）
  - [ ] `get_record_attachments(db, record_id)` — 获取某条记录的所有附件

### 5. 路由层 (Router)

- [ ] 创建 `app/routers/attachments.py`，注册路由：
  - [ ] `POST /api/attachments/upload` — 上传附件（multipart/form-data）
  - [ ] `GET /api/attachments/{id}` — 获取附件信息
  - [ ] `DELETE /api/attachments/{id}` — 删除附件
  - [ ] `GET /api/records/{record_id}/attachments` — 获取记录的附件列表
- [ ] 配置静态文件路由 `/uploads` 指向 `uploads/` 目录，使图片可直接访问

### 6. 错误处理

- [ ] 上传不支持的文件格式 → 返回 `40004`
- [ ] 文件超过 10MB → 返回 `40004`
- [ ] 未上传文件 → 返回 400 错误
- [ ] 附件 ID 不存在 → 返回 404

### 7. 验证与测试

- [ ] 通过 Swagger 上传一张合法图片，确认返回正确信息
- [ ] 访问返回的 URL 确认图片可正常显示
- [ ] 上传不支持的格式（如 .txt, .exe）确认被拒绝
- [ ] 上传超过 10MB 的文件确认被拒绝
- [ ] 删除附件后确认物理文件已被删除
- [ ] 测试获取记录附件列表接口
