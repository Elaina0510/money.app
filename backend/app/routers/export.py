"""Export API router."""

import io
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.services import export_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["导入导出"])


@router.get("/csv", response_model=None)
async def export_csv(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
):
    """Export records as CSV file."""
    try:
        csv_bytes, filename = await export_service.export_csv(db, current_user.id)
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception:
        logger.exception("CSV 导出失败")
        return error_response(Code.SERVER_ERROR, "导出失败")


@router.get("/sql", response_model=None)
async def export_sql(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
):
    """Export user data as SQL backup."""
    try:
        sql_bytes, filename = await export_service.export_sql(db, current_user.id)
        return StreamingResponse(
            io.BytesIO(sql_bytes),
            media_type="application/sql; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception:
        logger.exception("SQL 导出失败")
        return error_response(Code.SERVER_ERROR, "导出失败")
