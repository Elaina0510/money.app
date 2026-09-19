"""Record API router."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.record import BatchDeleteRequest, RecordCreate, RecordUpdate
from app.services import record_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/records", tags=["记账管理"])


@router.post("")
async def create_record(
    data: RecordCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Create a new record."""
    try:
        record = await record_service.create_record(db, data, current_user)
        return success_response(
            data=await record_service.enrich_record(db, record),
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
    current_user: User = Depends(require_auth),
) -> JSONResponse:
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
        current_user=current_user,
    )
    return success_response(data=result)


class QuickTemplateCreate(BaseModel):
    """Schema for manually adding a quick template."""
    tag_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)


@router.get("/quick-templates")
async def quick_templates(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get quick-accounting templates (auto + manual)."""
    templates = await record_service.get_quick_templates(db, current_user=current_user)
    return success_response(data=templates)


@router.post("/quick-templates")
async def add_quick_template(
    data: QuickTemplateCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Manually add a quick template."""
    qt = await record_service.add_quick_template(db, data.tag_id, data.amount, current_user)
    if not qt:
        return error_response(Code.NOT_FOUND, "标签不存在")
    return success_response(message="快速记账模板添加成功")


@router.delete("/quick-templates/auto")
async def ignore_auto_quick_template(
    tag_id: int = Query(..., gt=0, description="标签 ID"),
    type: str = Query(..., pattern=r"^(income|expense)$", description="类型: income/expense"),
    amount_cents: int = Query(..., gt=0, description="金额，单位：分"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Suppress an auto quick-template signature from ever appearing again."""
    # 路由顺序强约束：本路由必须声明在 /quick-templates/{template_id} 之前，
    # 否则 "auto" 会被 int 路径参数抢匹配 → 422（易错点 1）
    ok = await record_service.ignore_auto_quick_template(
        db, tag_id=tag_id, type_=type, amount_cents=amount_cents, current_user=current_user
    )
    if not ok:
        return error_response(Code.NOT_FOUND, "标签不存在")
    return success_response(message="自动模板已忽略")


@router.delete("/quick-templates/{template_id}")
async def delete_quick_template(
    template_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Delete a manual quick template."""
    deleted = await record_service.delete_quick_template(db, template_id, current_user)
    if not deleted:
        return error_response(Code.NOT_FOUND, "模板不存在")
    return success_response(message="模板删除成功")


@router.get("/earliest-year")
async def earliest_year(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get the earliest year that has records for current user."""
    year = await record_service.get_earliest_year(db, current_user)
    return success_response(data={"earliest_year": year})


@router.get("/{record_id}")
async def get_record(
    record_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get a single record with full details."""
    record = await record_service.get_record(db, record_id, current_user)
    if not record:
        return error_response(Code.NOT_FOUND, "记录不存在")
    return success_response(data=record)


@router.put("/{record_id}")
async def update_record(
    record_id: int,
    data: RecordUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Update a record."""
    try:
        record = await record_service.update_record(db, record_id, data, current_user)
        if not record:
            return error_response(Code.NOT_FOUND, "记录不存在")
        return success_response(data=record, message="记录更新成功")
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)


@router.delete("/{record_id}")
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Delete a record."""
    try:
        deleted = await record_service.delete_record(db, record_id, current_user)
        if not deleted:
            return error_response(Code.NOT_FOUND, "记录不存在")
        return success_response(message="记录删除成功")
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)


@router.post("/batch-delete")
async def batch_delete_records(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Batch delete records."""
    try:
        count = await record_service.batch_delete_records(db, data.ids, current_user)
        return success_response(data={"deleted_count": count}, message=f"成功删除 {count} 条记录")
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)
