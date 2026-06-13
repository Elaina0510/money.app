"""File cache utilities for import preview/confirm flow."""

import os
import tempfile
import uuid

IMPORT_CACHE_DIR = os.path.join(tempfile.gettempdir(), "money_app_imports")


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    os.makedirs(IMPORT_CACHE_DIR, exist_ok=True)


def _cache_path(cache_id: str, suffix: str) -> str:
    """Get the full path for a cached file."""
    return os.path.join(IMPORT_CACHE_DIR, f"{cache_id}{suffix}")


def save_to_cache(file_bytes: bytes, suffix: str) -> str:
    """Save file bytes to cache and return a cache_id."""
    _ensure_cache_dir()
    cache_id = uuid.uuid4().hex
    path = _cache_path(cache_id, suffix)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return cache_id


def read_from_cache(cache_id: str, suffix: str) -> bytes:
    """Read cached file bytes by cache_id. Raises FileNotFoundError if expired."""
    path = _cache_path(cache_id, suffix)
    if not os.path.exists(path):
        raise FileNotFoundError("缓存文件不存在或已过期")
    with open(path, "rb") as f:
        return f.read()


def delete_cache(cache_id: str, suffix: str) -> None:
    """Delete a cached file."""
    path = _cache_path(cache_id, suffix)
    if os.path.exists(path):
        os.remove(path)
