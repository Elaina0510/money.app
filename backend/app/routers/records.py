"""Record API router."""

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.schemas.record import RecordCreate, RecordUpdate, BatchDeleteRequest
from app.schemas.record import RecordResponse, RecordListResponse
from app.services import record_service
from app.utils.response import success_response, error_response, Code

router = APIRouter(prefix="/api/records", tags=["记账管理"])


@router.post("")
async def create_record(
    data: RecordCreate,
    db: AsyncSession = Depends(get_session),
):
    """Create a new record."""
    try:
        record = await record_service.create_record(db, data)
        return success_response(
            data=await record_service._enrich_record(db, record),
            message="记账成功",
        )
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.get("")
async def list_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    category_id: int | None = Query(None, description="分类 ID"),
    type: str | None = Query(None, description="类型: income/expense"),
    tag_id: int | None = Query(None, description="标签 ID"),
    keyword: str | None = Query(None, description="全文搜索(备注)"),
    sort_by: str = Query("consume_time", description="排序字段: consume_time/amount"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    db: AsyncSession = Depends(get_session),
):
    """Get paginated records with filters."""
    result = await record_service.get_records(
        db,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        type_filter=type,
        tag_id=tag_id,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return success_response(data=result)


@router.get("/quick-templates")
async def quick_templates(
    db: AsyncSession = Depends(get_session),
):
    """Get recent records as quick-accounting templates."""
    templates = await record_service.get_quick_templates(db)
    return success_response(data=templates)


@router.get("/{record_id}")
async def get_record(
    record_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get a single record with full details."""
    record = await record_service.get_record(db, record_id)
    if not record:
        return error_response(Code.NOT_FOUND, "记录不存在")
    return success_response(data=record)


@router.put("/{record_id}")
async def update_record(
    record_id: int,
    data: RecordUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update a record."""
    try:
        record = await record_service.update_record(db, record_id, data)
        if not record:
            return error_response(Code.NOT_FOUND, "记录不存在")
        return success_response(data=record, message="记录更新成功")
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.delete("/{record_id}")
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a record."""
    deleted = await record_service.delete_record(db, record_id)
    if not deleted:
        return error_response(Code.NOT_FOUND, "记录不存在")
    return success_response(message="记录删除成功")


@router.post("/batch-delete")
async def batch_delete_records(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_session),
):
    """Batch delete records."""
    count = await record_service.batch_delete_records(db, data.ids)
    return success_response(data={"deleted_count": count}, message=f"成功删除 {count} 条记录")
