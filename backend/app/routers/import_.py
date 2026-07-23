"""Import API router."""

import logging

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.import_ import ImportCsvRequest, ImportSqlRequest
from app.services import import_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["导入导出"])


@router.post("/csv/preview")
async def preview_csv_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Preview CSV import: detect format, extract categories/tags."""
    try:
        file_bytes = await file.read()
        if not file_bytes:
            return error_response(Code.PARAM_ERROR, "文件为空")
        result = await import_service.preview_csv(db, file_bytes)
        return success_response(data=result)
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    except Exception:
        logger.exception("CSV 预览失败")
        return error_response(Code.SERVER_ERROR, "文件解析失败")


@router.post("/csv")
async def import_csv(
    data: ImportCsvRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Confirm CSV import with mapping."""
    try:
        # Convert Pydantic models to dicts
        cat_mapping = {
            k: v.model_dump() for k, v in data.category_mapping.items()
        }
        tag_mapping = {
            k: v.model_dump() for k, v in data.tag_mapping.items()
        }
        result = await import_service.import_csv_data(
            db, current_user.id, data.cache_id, data.format,
            cat_mapping, tag_mapping,
        )
        return success_response(
            data=result,
            message=f"成功导入 {result['imported_count']} 条记录",
        )
    except FileNotFoundError:
        return error_response(Code.PARAM_ERROR, "缓存文件不存在或已过期")
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    except Exception:
        logger.exception("CSV 导入失败")
        return error_response(Code.SERVER_ERROR, "导入失败")


@router.post("/sql/preview")
async def preview_sql_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Preview SQL import: detect format, show table info."""
    try:
        file_bytes = await file.read()
        if not file_bytes:
            return error_response(Code.PARAM_ERROR, "文件为空")
        result = await import_service.preview_sql(db, file_bytes)
        return success_response(data=result)
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    except Exception:
        logger.exception("SQL 预览失败")
        return error_response(Code.SERVER_ERROR, "文件解析失败")


@router.post("/sql")
async def import_sql(
    data: ImportSqlRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Confirm SQL import."""
    try:
        # Convert Pydantic models to dicts if present
        cat_mapping = None
        tag_mapping = None
        if data.category_mapping:
            cat_mapping = {
                k: v.model_dump() for k, v in data.category_mapping.items()
            }
        if data.tag_mapping:
            tag_mapping = {
                k: v.model_dump() for k, v in data.tag_mapping.items()
            }
        result = await import_service.import_sql_data(
            db, current_user.id, data.cache_id, data.format,
            data.is_third_party,
            category_mapping=cat_mapping,
            tag_mapping=tag_mapping,
        )
        return success_response(
            data=result,
            message=f"成功导入 {result.get('records_imported', 0)} 条记录",
        )
    except FileNotFoundError:
        return error_response(Code.PARAM_ERROR, "缓存文件不存在或已过期")
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    except Exception:
        logger.exception("SQL 导入失败")
        return error_response(Code.SERVER_ERROR, "导入失败")
