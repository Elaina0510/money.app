import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, UPLOAD_DIR
from app.database import create_all_tables, engine
from app.models.category import Category
from app.models.operation_history import OperationHistory  # noqa: F401
from app.routers import (
    attachments,
    auth,
    budgets,
    categories,
    export,
    history,
    import_,
    records,
    statistics,
    tags,
)
from app.utils.file_utils import ensure_upload_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Determine frontend dist directory (supports FRONTEND_DIST env var for Docker)
_default_frontend = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(_default_frontend)))

# Ensure upload directory exists at import time for StaticFiles mount
ensure_upload_dir()

# Preset categories data
PRESET_CATEGORIES = [
    # Expense categories
    {"name": "餐饮", "type": "expense", "icon": "mdi-food", "sort_order": 1, "is_preset": 1},
    {"name": "出行", "type": "expense", "icon": "mdi-bus", "sort_order": 2, "is_preset": 1},
    {"name": "购物", "type": "expense", "icon": "mdi-cart", "sort_order": 3, "is_preset": 1},
    {"name": "娱乐", "type": "expense", "icon": "mdi-gamepad", "sort_order": 4, "is_preset": 1},
    {
        "name": "医疗",
        "type": "expense",
        "icon": "mdi-hospital-box",
        "sort_order": 5,
        "is_preset": 1,
    },
    {"name": "居住", "type": "expense", "icon": "mdi-home", "sort_order": 6, "is_preset": 1},
    {"name": "通讯", "type": "expense", "icon": "mdi-cellphone", "sort_order": 7, "is_preset": 1},
    {"name": "工作", "type": "expense", "icon": "mdi-briefcase", "sort_order": 8, "is_preset": 1},
    {"name": "旅行", "type": "expense", "icon": "mdi-bag-suitcase",
     "sort_order": 9, "is_preset": 1},
    {"name": "账单与费用", "type": "expense", "icon": "mdi-receipt-text",
     "sort_order": 10, "is_preset": 1},
    {
        "name": "其他支出",
        "type": "expense",
        "icon": "mdi-cash-minus",
        "sort_order": 99,
        "is_preset": 1,
    },
    # Income categories
    {"name": "工资", "type": "income", "icon": "mdi-wallet", "sort_order": 1, "is_preset": 1},
    {"name": "红包", "type": "income", "icon": "mdi-gift", "sort_order": 2, "is_preset": 1},
    {"name": "理财", "type": "income", "icon": "mdi-finance", "sort_order": 3, "is_preset": 1},
    {
        "name": "其他收入",
        "type": "income",
        "icon": "mdi-cash-plus",
        "sort_order": 99,
        "is_preset": 1,
    },
]


async def init_preset_data() -> None:
    """Insert preset categories if they don't exist."""
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(engine, expire_on_commit=False) as session:
        for cat_data in PRESET_CATEGORIES:
            stmt = select(Category).where(
                Category.name == cat_data["name"],
                Category.type == cat_data["type"],
            )
            result = await session.exec(stmt)
            existing = result.first()
            if not existing:
                category = Category(**cat_data)
                session.add(category)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup: create tables and insert preset data
    ensure_upload_dir()
    await create_all_tables()
    await init_preset_data()
    yield


app = FastAPI(
    title="Money App - 个人记账程序",
    description="个人记账程序 API V1.1",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS middleware —— 显式 origin 列表(allow_credentials=True 不能配 "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads.
# 残余风险说明:/uploads/{stored_path} 为公开静态挂载,无鉴权。文件名为 uuid
# 不可枚举,且记录接口已按 user 隔离(非归属者无法得知附件路径)。对"几个人用"
# 的服务器部署可接受;若需彻底隔离,改为鉴权下载端点 + 前端 blob。
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Serve frontend static files if dist exists
if FRONTEND_DIST.exists():
    assets_dir = str(FRONTEND_DIST / "assets")
    app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")

# Register routers
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(tags.router)
app.include_router(records.router)
app.include_router(attachments.router)
app.include_router(statistics.router)
app.include_router(budgets.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(import_.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底:记录未捕获异常的真实堆栈,避免静默吞掉。"""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": 50001, "message": "服务器内部错误", "data": None},
    )


@app.get("/health", response_model=None)
async def health() -> dict[str, str]:
    """健康检查端点(供 Docker HEALTHCHECK / 监控使用)。"""
    return {"status": "ok"}


@app.get("/", response_model=None)
async def root() -> FileResponse | dict[str, str]:
    """Root endpoint - serve frontend if available."""
    if FRONTEND_DIST.exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")
    return {"message": "Money App API", "version": "1.0.0", "docs": "/docs"}
