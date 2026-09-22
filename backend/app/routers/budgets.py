"""Budget API router（v1.4.3 M12：某自然月下的多条具名预算）.

接口契约（决策 D12 / 任务 2.1–2.7）：
  * ``GET /api/budgets?month=`` —— 去掉 ``type`` 参数，返回 BudgetDetail[] 按 id 升序；
  * ``POST /api/budgets`` —— 由 upsert 改**纯创建**（同月同名多条各自成行）；
  * ``PUT /api/budgets/{id}`` —— 全字段编辑，``month`` 传入即忽略；IDOR 403 保持；
  * ``DELETE /api/budgets/{id}`` —— 不变（IDOR 403）；
  * ``POST /api/budgets/batch`` —— **已下线**（调用方仅统计页，随 M12 重写重接单条 PUT）。
响应/错误口径未变：``success_response`` / ``error_response(Code.XXX)``、
服务层 ``ValueError`` → PARAM_ERROR、``PermissionError`` → 403。

v1.4.3-boot2 M3（决策 D3/D9/D10，任务 1.5）口径增补：
  * **「include + 空 category_ids」不再报错**（原 PARAM_ERROR「包含模式至少需要选择
    1 个分类」已删）——POST/PUT 一律 200，语义 = **动态全部分类**（后续新增分类自动计入）；
  * BudgetDetail 增 ``dormant: bool``：1 = 关联分类被删光的休眠预算（花费 0、无明细）；
  * ``GET /api/budgets`` **仍返回 dormant 行**（月视图卡片要置灰展示），
    而 ``GET /api/budgets/year-summary`` 的逐月 total 剔除 dormant（D10）；
  * 唤醒无独立接口：任何一次成功的 PUT 都把 dormant 清 0（D9）；
    ``DELETE`` 对休眠预算照常可用（用户摆脱休眠态的另一出口）。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.services import budget_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/budgets", tags=["预算管理"])


@router.get("")
async def list_budgets(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="月份 YYYY-MM"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get all named budgets for a given month, ordered by id (创建序)."""
    try:
        budgets = await budget_service.get_budgets(db, month, current_user)
    except ValueError as e:
        # 2026-13 过得了 query pattern、过不了月历：PARAM_ERROR 而非 500
        return error_response(Code.PARAM_ERROR, str(e))
    return success_response(data=budgets)


@router.get("/year-summary")
async def year_summary(
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get budgets grouped by each month of a year (fixed 12 months).

    逐月 ``total_amount`` / ``total_spent`` = Σ 该月各预算（决策 D4）。
    """
    data = await budget_service.get_year_summary(db, year, current_user)
    return success_response(data=data)


@router.post("")
async def create_budget(
    data: BudgetCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Create a named budget（纯创建：同月同名的多条互不覆盖）。"""
    try:
        detail = await budget_service.create_budget(db, data, current_user)
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    return success_response(data=detail, message="预算创建成功")


@router.put("/{budget_id}")
async def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Update a budget（全字段编辑；``month`` 不可改，传入一律忽略）。"""
    try:
        detail = await budget_service.update_budget(db, budget_id, data, current_user)
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)
    if detail is None:
        return error_response(Code.NOT_FOUND, "预算不存在")
    return success_response(data=detail, message="预算更新成功")


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Delete a budget."""
    try:
        deleted = await budget_service.delete_budget(db, budget_id, current_user)
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)
    if not deleted:
        return error_response(Code.NOT_FOUND, "预算不存在")
    return success_response(message="预算删除成功")
