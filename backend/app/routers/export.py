"""Export API router."""

import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.services import export_service
from app.utils.auth import get_current_user
from app.utils.response import Code, error_response

router = APIRouter(prefix="/api/export", tags=["导入导出"])


@router.get("/csv", response_model=None)
async def export_csv(
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Export records as CSV file."""
    if not current_user:
        return error_response(Code.FORBIDDEN, "请先登录", status_code=401)
    try:
        csv_bytes, filename = await export_service.export_csv(
            db, current_user.id
        )
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception:
        return error_response(Code.SERVER_ERROR, "导出失败")


@router.get("/sql", response_model=None)
async def export_sql(
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Export user data as SQL backup."""
    if not current_user:
        return error_response(Code.FORBIDDEN, "请先登录", status_code=401)
    try:
        sql_bytes, filename = await export_service.export_sql(
            db, current_user.id
        )
        return StreamingResponse(
            io.BytesIO(sql_bytes),
            media_type="application/sql; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception:
        return error_response(Code.SERVER_ERROR, "导出失败")
