"""Application configuration loaded from .env and defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# Database
# ============================================================
# 生产环境建议设置 DATABASE_URL 指向项目外的路径
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'money.db'}",
)

# ============================================================
# Authentication
# ============================================================
SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "money-app-dev-secret-key-change-in-production-123456",
)
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))  # 默认7天
)

# ============================================================
# Upload
# ============================================================
UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10 MB
# 总上传容量限制（默认 500MB）
MAX_TOTAL_UPLOAD_SIZE: int = int(os.getenv("MAX_TOTAL_UPLOAD_SIZE", str(500 * 1024 * 1024)))

# Allowed image types
ALLOWED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
# 真实的图片 Magic Bytes 签名
IMAGE_SIGNATURES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WEBP 以 RIFF 开头
}
ALLOWED_MIME_TYPES: set[str] = set(IMAGE_SIGNATURES.values())
