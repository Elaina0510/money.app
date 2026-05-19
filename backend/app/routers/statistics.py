"""Statistics API router."""

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.services import statistics_service
from app.utils.response import success_response, error_response, Code

router = APIRouter(prefix="/api/statistics", tags=["数据统计"])


@router.get("/summary")
async def get_summary(
    period: str = Query(..., description="统计周期: day/week/month/year"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_session),
):
    """Get income/expense summary."""
    if period not in ("day", "week", "month", "year"):
        return error_response(Code.PARAM_ERROR, "period 参数无效，可选: day/week/month/year")
    result = await statistics_service.get_summary(db, period, start_date, end_date)
    return success_response(data=result)


@router.get("/by-category")
async def get_by_category(
    type: str = Query("expense", description="类型: expense"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_session),
):
    """Get expense statistics by category."""
    if type != "expense":
        return error_response(Code.PARAM_ERROR, "分类统计仅支持 expense 类型")
    result = await statistics_service.get_category_stats(db, type, start_date, end_date)
    return success_response(data=result)


@router.get("/by-tag")
async def get_by_tag(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_session),
):
    """Get statistics by tag."""
    result = await statistics_service.get_tag_stats(db, start_date, end_date)
    return success_response(data=result)


@router.get("/trend")
async def get_trend(
    group_by: str = Query(..., description="分组方式: month/year"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_session),
):
    """Get income/expense trend."""
    if group_by not in ("month", "year"):
        return error_response(Code.PARAM_ERROR, "group_by 参数无效，可选: month/year")
    result = await statistics_service.get_trend(db, group_by, start_date, end_date)
    return success_response(data=result)
