"""Application configuration loaded from .env and defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# Environment
# ============================================================
# "production" 启用生产级安全守卫(如禁止默认 SECRET_KEY)。
# 本地开发与测试不设此变量,保持宽松行为。
APP_ENV: str = os.getenv("APP_ENV", "development")

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
_DEFAULT_SECRET_KEY = "money-app-dev-secret-key-change-in-production-123456"
SECRET_KEY: str = os.getenv("SECRET_KEY", _DEFAULT_SECRET_KEY)
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))  # 默认7天
)

# 生产环境禁止使用默认/示例占位 SECRET_KEY —— 部署时若忘记改,直接拒绝启动。
# 含开发默认值与 .env.example 里的占位值,避免照抄示例仍能启动。
_INSECURE_SECRET_KEYS = {
    _DEFAULT_SECRET_KEY,
    "money-app-change-this-secret-key-in-production",
}
if APP_ENV == "production" and SECRET_KEY in _INSECURE_SECRET_KEYS:
    raise RuntimeError(
        "生产环境(APP_ENV=production)禁止使用默认/示例 SECRET_KEY,请在 .env 中设置随机值。"
        "可用: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
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

# ============================================================
# CORS
# ============================================================
# 逗号分隔的允许来源,例如:
#   CORS_ORIGINS=https://money.example.com,http://192.168.1.10
# 生产环境务必设置为实际访问地址;留空则用本地开发默认值。
def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


CORS_ORIGINS: list[str] = _parse_cors_origins()
