"""Attachment API router."""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.services import attachment_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/attachments", tags=["附件管理"])


@router.post("/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    record_id: int | None = Query(default=None, description="关联的记账记录 ID"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
):
    """Upload an attachment file."""
    result = await attachment_service.upload_attachment(db, file, current_user, record_id)
    if isinstance(result, dict) and "code" in result:
        return error_response(result["code"], result["message"])

    # Build response with URL
    # 注意:/uploads/{stored_path} 为静态公开挂载,文件名为 uuid 不可枚举;
    # 非归属者无法通过 API 得知路径(记录已按 user 隔离)。残余风险见 README。
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
    current_user: User = Depends(require_auth),
):
    """Get attachment info."""
    attachment = await attachment_service.get_attachment(db, attachment_id, current_user)
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
    current_user: User = Depends(require_auth),
):
    """Delete an attachment."""
    result = await attachment_service.delete_attachment(db, attachment_id, current_user)
    if result:
        status_code = 403 if result["code"] == Code.FORBIDDEN else 400
        return error_response(result["code"], result["message"], status_code=status_code)
    return success_response(message="附件删除成功")
