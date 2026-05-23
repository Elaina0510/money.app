"""File storage utilities for attachment management."""

import uuid
from pathlib import Path

from app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    IMAGE_SIGNATURES,
    MAX_FILE_SIZE,
    MAX_TOTAL_UPLOAD_SIZE,
    UPLOAD_DIR,
)


def ensure_upload_dir() -> None:
    """Ensure the upload root directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def generate_stored_path(original_filename: str) -> Path:
    """Generate a stored file path: uploads/{year}/{month}/{day}/{uuid}.{ext}."""
    from datetime import datetime

    now = datetime.now()
    ext = Path(original_filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    relative = Path(str(now.year)) / str(now.month).zfill(2) / str(now.day).zfill(2)
    full_dir = UPLOAD_DIR / relative
    full_dir.mkdir(parents=True, exist_ok=True)
    return relative / unique_name


def validate_file_type(filename: str, mime_type: str | None = None) -> bool:
    """Validate file type by extension and optionally by MIME type."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        return False
    return True


def validate_file_content(content: bytes) -> bool:
    """Validate file content by checking magic bytes (signature).

    通过检查文件头部的 Magic Bytes 来验证文件类型，
    防止客户端伪造 MIME 类型上传非图片文件。
    """
    for signature in IMAGE_SIGNATURES:
        if content.startswith(signature):
            return True
    return False


def validate_file_size(file_size: int) -> bool:
    """Validate that the file size does not exceed the maximum allowed."""
    return file_size <= MAX_FILE_SIZE


def validate_total_upload_size() -> tuple[bool, int]:
    """Validate that the total upload directory size does not exceed the limit.

    Returns:
        tuple[bool, int]: (is_within_limit, current_total_size)
    """
    total_size = 0
    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    return total_size <= MAX_TOTAL_UPLOAD_SIZE, total_size


def delete_file(stored_path: str | Path) -> bool:
    """Delete a physical file from the uploads directory."""
    full_path = UPLOAD_DIR / Path(stored_path)
    if full_path.exists():
        full_path.unlink()
        return True
    return False


def get_full_path(stored_path: str | Path) -> Path:
    """Get the full path for a stored file."""
    return UPLOAD_DIR / Path(stored_path)
