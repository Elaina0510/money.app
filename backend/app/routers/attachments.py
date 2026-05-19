"""Attachment API router."""

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.schemas.attachment import AttachmentResponse
from app.services import attachment_service
from app.utils.response import success_response, error_response, Code
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/api/attachments", tags=["附件管理"])


@router.post("/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    record_id: int | None = Query(default=None, description="关联的记账记录 ID"),
    db: AsyncSession = Depends(get_session),
):
    """Upload an attachment file."""
    result = await attachment_service.upload_attachment(db, file, record_id)
    if isinstance(result, dict) and "code" in result:
        return error_response(result["code"], result["message"])
    
    # Build response with URL
    url = f"/uploads/{result.stored_path}"
    resp = AttachmentResponse(
        id=result.id,
        record_id=result.record_id,
        filename=result.filename,
        url=url,
        file_size=result.file_size,
        mime_type=result.mime_type,
        created_at=result.created_at,
    )
    return success_response(data=resp.model_dump(), message="上传成功")


@router.get("/{attachment_id}")
async def get_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get attachment info."""
    attachment = await attachment_service.get_attachment(db, attachment_id)
    if not attachment:
        return error_response(Code.NOT_FOUND, "附件不存在")
    url = f"/uploads/{attachment.stored_path}"
    resp = AttachmentResponse(
        id=attachment.id,
        record_id=attachment.record_id,
        filename=attachment.filename,
        url=url,
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        created_at=attachment.created_at,
    )
    return success_response(data=resp.model_dump())


@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete an attachment."""
    result = await attachment_service.delete_attachment(db, attachment_id)
    if result:
        return error_response(result["code"], result["message"])
    return success_response(message="附件删除成功")

