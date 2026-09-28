"""Version API router (v1.4.4 M4 / 设计 §5.1、REQ-008).

唯一职责 = 把 `app.constants.APP_VERSION`（全仓版本真值）经统一响应外壳下发给前端
「关于」页。**无鉴权**：版本号为只读公开信息，且「关于」页在未登录可达场景下也不白屏
（任务 §1.2 口径）。
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.constants import APP_VERSION
from app.utils.response import success_response

router = APIRouter(prefix="/api/version", tags=["版本"])


@router.get("")
async def get_version() -> JSONResponse:
    """Get the single-source application version (no auth)."""
    return success_response(data={"version": APP_VERSION}, message="ok")
