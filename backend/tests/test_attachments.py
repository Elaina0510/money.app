"""Tests for attachment API."""

import io
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_upload_image(client):
    """Test uploading a valid image file."""
    file_content = b"fake_image_content"
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
    file_content = b"test_image"
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
    file_content = b"test_image_for_delete"
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
        json={"amount": 100.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-01", "tags": []},
    )
    record_id = resp.json()["data"]["id"]

    # Upload attachment with record_id
    file_content = b"record_image"
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


@pytest.fixture
async def expense_category_id(client):
    """Create an expense category and return its ID."""
    resp = await client.post(
        "/api/categories",
        json={"name": "附件测试分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    return resp.json()["data"]["id"]
