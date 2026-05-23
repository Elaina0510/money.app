"""Tests for attachment API."""

import io
import struct
import zlib

import pytest


def _make_png(width=1, height=1):
    """Create a minimal valid PNG file in memory."""
    # PNG signature
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

    # IDAT chunk (raw pixel data: filter byte + RGB for each row)
    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00" + b"\xff\x00\x00" * width  # Red pixels
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    idat_chunk = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)

    # IEND chunk
    iend_crc = zlib.crc32(b"IEND")
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    return signature + ihdr_chunk + idat_chunk + iend_chunk


@pytest.fixture
async def expense_category_id(client):
    """Create an expense category and return its ID."""
    resp = await client.post(
        "/api/categories",
        json={"name": "附件测试分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_upload_image(client):
    """Test uploading a valid image file."""
    file_content = _make_png()
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
    resp = await client.post("/api/attachments/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["filename"] == "test.jpg"
    assert data["data"]["file_size"] == len(file_content)


@pytest.mark.asyncio
async def test_upload_invalid_type(client):
    """Test uploading an unsupported file type."""
    file_content = b"fake_exe"
    files = {"file": ("virus.exe", io.BytesIO(file_content), "application/x-msdownload")}
    resp = await client.post("/api/attachments/upload", files=files)
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40004


@pytest.mark.asyncio
async def test_get_attachment(client):
    """Test getting attachment info."""
    file_content = _make_png()
    files = {"file": ("photo.png", io.BytesIO(file_content), "image/png")}
    resp = await client.post("/api/attachments/upload", files=files)
    att_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/attachments/{att_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == att_id
    assert data["data"]["filename"] == "photo.png"


@pytest.mark.asyncio
async def test_delete_attachment(client):
    """Test deleting an attachment."""
    file_content = _make_png()
    files = {"file": ("delete_me.png", io.BytesIO(file_content), "image/png")}
    resp = await client.post("/api/attachments/upload", files=files)
    att_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/attachments/{att_id}")
    assert resp.status_code == 200

    # Verify it's gone
    resp = await client.get(f"/api/attachments/{att_id}")
    assert resp.json()["code"] == 40002


@pytest.mark.asyncio
async def test_get_record_attachments(client, expense_category_id):
    """Test getting attachments for a record."""
    # Create a record
    resp = await client.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # Upload attachment with record_id
    file_content = _make_png()
    files = {"file": ("receipt.jpg", io.BytesIO(file_content), "image/jpeg")}
    resp = await client.post(
        f"/api/attachments/upload?record_id={record_id}",
        files=files,
    )
    assert resp.status_code == 200

    # Get record's attachments via records router
    resp = await client.get(f"/api/records/{record_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["attachment_ids"]) > 0
