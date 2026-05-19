"""Tests for category API."""

import pytest


@pytest.mark.asyncio
async def test_get_categories(client):
    """Test fetching all categories."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_categories_by_type_expense(client):
    """Test filtering categories by type=expense."""
    resp = await client.get("/api/categories?type=expense")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    for cat in data["data"]:
        assert cat["type"] == "expense"


@pytest.mark.asyncio
async def test_get_categories_by_type_income(client):
    """Test filtering categories by type=income."""
    resp = await client.get("/api/categories?type=income")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    for cat in data["data"]:
        assert cat["type"] == "income"


@pytest.mark.asyncio
async def test_create_category(client):
    """Test creating a new custom category."""
    resp = await client.post(
        "/api/categories",
        json={"name": "测试分类", "type": "expense", "icon": "mdi-test", "sort_order": 50},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试分类"
    assert data["data"]["type"] == "expense"
    assert data["data"]["is_preset"] == 0


@pytest.mark.asyncio
async def test_create_duplicate_category(client):
    """Test creating a category with duplicate name/type."""
    await client.post(
        "/api/categories",
        json={"name": "测试重复", "type": "expense", "icon": "mdi-test", "sort_order": 50},
    )
    resp = await client.post(
        "/api/categories",
        json={"name": "测试重复", "type": "expense", "icon": "mdi-test", "sort_order": 50},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40003


@pytest.mark.asyncio
async def test_update_category(client):
    """Test updating a category."""
    # First create a category
    resp = await client.post(
        "/api/categories",
        json={"name": "旧名称", "type": "expense", "icon": "mdi-old", "sort_order": 10},
    )
    cat_id = resp.json()["data"]["id"]

    # Update it
    resp = await client.put(
        f"/api/categories/{cat_id}",
        json={"name": "新名称", "icon": "mdi-new"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "新名称"


@pytest.mark.asyncio
async def test_update_nonexistent_category(client):
    """Test updating a non-existent category."""
    resp = await client.put(
        "/api/categories/99999",
        json={"name": "不存在", "icon": "mdi-none"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002


@pytest.mark.asyncio
async def test_delete_category(client):
    """Test deleting a custom category."""
    resp = await client.post(
        "/api/categories",
        json={"name": "待删除", "type": "expense", "icon": "mdi-delete", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_category(client):
    """Test deleting a non-existent category."""
    resp = await client.delete("/api/categories/99999")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002


@pytest.mark.asyncio
async def test_delete_category_with_records(client):
    """Test that deleting a category with records returns conflict."""
    # Create a category
    resp = await client.post(
        "/api/categories",
        json={"name": "关联分类", "type": "expense", "icon": "mdi-link", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]

    # Create a record using this category
    await client.post(
        "/api/records",
        json={
            "amount": 100.0,
            "type": "expense",
            "category_id": cat_id,
            "date": "2026-01-01",
            "tags": [],
        },
    )

    # Try to delete the category
    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40003
    assert "记录" in data["message"]


@pytest.mark.asyncio
async def test_preset_categories_exist(client):
    """Test that preset categories are available."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    names = [c["name"] for c in data["data"]]
    assert "餐饮" in names
    assert "交通" in names
    assert "工资" in names
    assert "其他收入" in names
