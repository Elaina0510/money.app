"""History API router."""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.services import history_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["历史回溯"])


@router.get("")
async def list_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get paginated history list."""
    result = await history_service.get_history_list(
        db, user_id=current_user.id, page=page, page_size=page_size
    )
    return success_response(data=result)


@router.get("/{history_id}")
async def get_history_detail(
    history_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get history detail with parsed snapshots."""
    detail = await history_service.get_history_detail(db, current_user.id, history_id)
    if not detail:
        return error_response(Code.NOT_FOUND, "历史记录不存在", status_code=404)
    return success_response(data=detail)


@router.post("/{history_id}/rollback")
async def rollback_history(
    history_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Execute rollback for a history entry."""
    try:
        result = await history_service.rollback_operation(db, current_user.id, history_id)
        return success_response(data=result, message="回溯成功")
    except ValueError as e:
        return error_response(Code.NOT_FOUND, str(e), status_code=404)
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)
