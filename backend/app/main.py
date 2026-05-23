from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pathlib import Path

from app.config import UPLOAD_DIR
from app.database import create_all_tables, engine
from app.models.category import Category
from app.models.record import Record
from app.models.record_tag import RecordTag
from app.models.tag import Tag
from app.models.attachment import Attachment
from app.models.user import User
from app.routers import records, categories, tags, attachments, statistics, budgets, auth
from app.utils.file_utils import ensure_upload_dir

# Determine frontend dist directory
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# Ensure upload directory exists at import time for StaticFiles mount
ensure_upload_dir()

# Preset categories data
PRESET_CATEGORIES = [
    # Expense categories
    {"name": "餐饮", "type": "expense", "icon": "mdi-food", "sort_order": 1, "is_preset": 1},
    {"name": "交通", "type": "expense", "icon": "mdi-bus", "sort_order": 2, "is_preset": 1},
    {"name": "购物", "type": "expense", "icon": "mdi-cart", "sort_order": 3, "is_preset": 1},
    {"name": "娱乐", "type": "expense", "icon": "mdi-gamepad", "sort_order": 4, "is_preset": 1},
    {"name": "医疗", "type": "expense", "icon": "mdi-hospital-box", "sort_order": 5, "is_preset": 1},
    {"name": "居住", "type": "expense", "icon": "mdi-home", "sort_order": 6, "is_preset": 1},
    {"name": "通讯", "type": "expense", "icon": "mdi-cellphone", "sort_order": 7, "is_preset": 1},
    {"name": "教育", "type": "expense", "icon": "mdi-school", "sort_order": 8, "is_preset": 1},
    {"name": "其他支出", "type": "expense", "icon": "mdi-cash-minus", "sort_order": 99, "is_preset": 1},
    # Income categories
    {"name": "工资", "type": "income", "icon": "mdi-wallet", "sort_order": 1, "is_preset": 1},
    {"name": "兼职", "type": "income", "icon": "mdi-briefcase", "sort_order": 2, "is_preset": 1},
    {"name": "红包", "type": "income", "icon": "mdi-gift", "sort_order": 3, "is_preset": 1},
    {"name": "理财", "type": "income", "icon": "mdi-finance", "sort_order": 4, "is_preset": 1},
    {"name": "其他收入", "type": "income", "icon": "mdi-cash-plus", "sort_order": 99, "is_preset": 1},
]


async def init_preset_data() -> None:
    """Insert preset categories if they don't exist."""
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select

    async with AsyncSession(engine) as session:
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
async def lifespan(app: FastAPI):
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Serve frontend static files if dist exists
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

# Register routers
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(tags.router)
app.include_router(records.router)
app.include_router(attachments.router)
app.include_router(statistics.router)
app.include_router(budgets.router)


@app.get("/")
async def root():
    """Root endpoint - serve frontend if available."""
    if FRONTEND_DIST.exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")
    return {"message": "Money App API", "version": "1.0.0", "docs": "/docs"}

