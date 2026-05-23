"""Attachment business logic."""

from pathlib import Path

from fastapi import UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.attachment import Attachment
from app.config import MAX_FILE_SIZE
from app.utils.file_utils import (
    ensure_upload_dir,
    generate_stored_path,
    validate_file_type,
    validate_file_content,
    validate_file_size,
    validate_total_upload_size,
    delete_file,
    get_full_path,
)
from app.utils.response import Code


async def upload_attachment(
    db: AsyncSession,
    file: UploadFile,
    record_id: int | None = None,
) -> Attachment | dict:
    """Upload an attachment file.

    Returns Attachment on success, or an error dict on failure.
    """
    # Validate file exists
    if not file.filename:
        return {"code": Code.PARAM_ERROR, "message": "未选择文件"}

    # Validate file type by extension
    if not validate_file_type(file.filename, file.content_type):
        return {
            "code": Code.FILE_INVALID,
            "message": "不支持的文件格式，仅支持 jpg/jpeg/png/gif/webp",
        }

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if not validate_file_size(file_size):
        return {
            "code": Code.FILE_INVALID,
            "message": f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024*1024)}MB）",
        }

    # Validate file content by magic bytes (防止伪造 MIME 类型)
    if not validate_file_content(content):
        return {
            "code": Code.FILE_INVALID,
            "message": "文件内容格式无效，请上传真实图片文件",
        }

    # Validate total upload size
    is_within_limit, current_total = validate_total_upload_size()
    if not is_within_limit:
        return {
            "code": Code.FILE_INVALID,
            "message": "上传空间已满，请删除部分附件后再试",
        }

    # Ensure upload directory exists
    ensure_upload_dir()

    # Generate stored path
    relative_path = generate_stored_path(file.filename)
    full_path = get_full_path(relative_path)

    # Save file
    full_path.write_bytes(content)

    # Create database record
    attachment = Attachment(
        record_id=record_id,
        filename=file.filename,
        stored_path=str(relative_path),
        file_size=file_size,
        mime_type=file.content_type or "image/jpeg",
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


async def get_attachment(db: AsyncSession, attachment_id: int) -> Attachment | None:
    """Get attachment by ID."""
    return await db.get(Attachment, attachment_id)


async def delete_attachment(
    db: AsyncSession, attachment_id: int
) -> dict | None:
    """Delete an attachment (file + DB record). Returns None on success."""
    attachment = await db.get(Attachment, attachment_id)
    if not attachment:
        return {"code": Code.NOT_FOUND, "message": "附件不存在"}

    # Delete physical file
    delete_file(attachment.stored_path)

    # Delete database record
    await db.delete(attachment)
    await db.commit()
    return None


async def get_record_attachments(
    db: AsyncSession, record_id: int
) -> list[Attachment]:
    """Get all attachments for a specific record."""
    stmt = (
        select(Attachment)
        .where(Attachment.record_id == record_id)
        .order_by(Attachment.created_at)
    )
    result = await db.exec(stmt)
    return list(result.all())
