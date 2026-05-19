"""Tests for tag API."""

import pytest


@pytest.mark.asyncio
async def test_get_tags(client):
    """Test fetching all tags."""
    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_create_tag(client):
    """Test creating a new tag."""
    resp = await client.post("/api/tags", json={"name": "测试标签"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试标签"


@pytest.mark.asyncio
async def test_update_tag(client):
    """Test updating a tag."""
    resp = await client.post("/api/tags", json={"name": "旧标签"})
    tag_id = resp.json()["data"]["id"]

    resp = await client.put(f"/api/tags/{tag_id}", json={"name": "新标签"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["name"] == "新标签"


@pytest.mark.asyncio
async def test_delete_tag(client):
    """Test deleting a tag."""
    resp = await client.post("/api/tags", json={"name": "待删除标签"})
    tag_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_tag(client):
    """Test deleting a non-existent tag."""
    resp = await client.delete("/api/tags/99999")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002
