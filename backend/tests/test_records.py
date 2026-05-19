"""Tests for record API."""

import pytest


@pytest.fixture
async def expense_category_id(client):
    """Create an expense category and return its ID."""
    resp = await client.post(
        "/api/categories",
        json={"name": "餐饮测试", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def income_category_id(client):
    """Create an income category and return its ID."""
    resp = await client.post(
        "/api/categories",
        json={"name": "工资测试", "type": "income", "icon": "mdi-wallet", "sort_order": 1},
    )
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_expense_record(client, expense_category_id):
    """Test creating an expense record."""
    resp = await client.post(
        "/api/records",
        json={
            "amount": 25.50,
            "type": "expense",
            "category_id": expense_category_id,
            "date": "2026-06-01",
            "tags": ["奶茶", "下午茶"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["amount"] == 25.50
    assert data["data"]["type"] == "expense"
    assert data["data"]["tags"] == ["奶茶", "下午茶"]
    assert data["data"]["category_name"] == "餐饮测试"


@pytest.mark.asyncio
async def test_create_income_record(client, income_category_id):
    """Test creating an income record."""
    resp = await client.post(
        "/api/records",
        json={
            "amount": 5000.00,
            "type": "income",
            "category_id": income_category_id,
            "date": "2026-06-01",
            "tags": ["工资"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["amount"] == 5000.00
    assert data["data"]["type"] == "income"


@pytest.mark.asyncio
async def test_create_record_with_zero_amount(client, expense_category_id):
    """Test that creating a record with zero amount returns error."""
    resp = await client.post(
        "/api/records",
        json={
            "amount": 0,
            "type": "expense",
            "category_id": expense_category_id,
            "date": "2026-06-01",
            "tags": [],
        },
    )
    assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_create_record_with_negative_amount(client, expense_category_id):
    """Test that creating a record with negative amount returns error."""
    resp = await client.post(
        "/api/records",
        json={
            "amount": -50,
            "type": "expense",
            "category_id": expense_category_id,
            "date": "2026-06-01",
            "tags": [],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_records(client, expense_category_id):
    """Test fetching records list."""
    # Create a record first
    await client.post(
        "/api/records",
        json={
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category_id,
            "date": "2026-06-01",
            "tags": ["测试"],
        },
    )

    resp = await client.get("/api/records")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    assert len(data["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_records_with_filters(client, expense_category_id, income_category_id):
    """Test filtering records."""
    # Create records
    await client.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-01", "tags": []},
    )
    await client.post(
        "/api/records",
        json={"amount": 200.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-02", "tags": []},
    )
    await client.post(
        "/api/records",
        json={"amount": 5000.0, "type": "income", "category_id": income_category_id, "date": "2026-06-01", "tags": []},
    )

    # Filter by type
    resp = await client.get("/api/records?type=expense")
    assert len(resp.json()["data"]["items"]) == 2

    resp = await client.get("/api/records?type=income")
    assert len(resp.json()["data"]["items"]) == 1

    # Filter by date range
    resp = await client.get("/api/records?start_date=2026-06-02&end_date=2026-06-02")
    assert len(resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_single_record(client, expense_category_id):
    """Test fetching a single record."""
    resp = await client.post(
        "/api/records",
        json={"amount": 50.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-01", "tags": ["午餐"]},
    )
    record_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/records/{record_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == record_id
    assert data["data"]["tags"] == ["午餐"]


@pytest.mark.asyncio
async def test_update_record(client, expense_category_id):
    """Test updating a record."""
    resp = await client.post(
        "/api/records",
        json={"amount": 50.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-01", "tags": ["旧标签"]},
    )
    record_id = resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/records/{record_id}",
        json={"amount": 75.0, "tags": ["新标签"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["amount"] == 75.0
    assert data["data"]["tags"] == ["新标签"]


@pytest.mark.asyncio
async def test_delete_record(client, expense_category_id):
    """Test deleting a record."""
    resp = await client.post(
        "/api/records",
        json={"amount": 50.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-01", "tags": []},
    )
    record_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/records/{record_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/api/records/{record_id}")
    assert resp.json()["code"] == 40002


@pytest.mark.asyncio
async def test_batch_delete(client, expense_category_id):
    """Test batch deleting records."""
    ids = []
    for i in range(3):
        resp = await client.post(
            "/api/records",
            json={"amount": float(i + 1), "type": "expense", "category_id": expense_category_id, "date": "2026-06-01", "tags": []},
        )
        ids.append(resp.json()["data"]["id"])

    resp = await client.post("/api/records/batch-delete", json={"ids": ids})
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted_count"] == 3


@pytest.mark.asyncio
async def test_batch_delete_empty(client):
    """Test batch deleting with empty list."""
    resp = await client.post("/api/records/batch-delete", json={"ids": []})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_quick_templates(client, expense_category_id):
    """Test getting quick accounting templates."""
    # Create multiple records
    for i in range(5):
        await client.post(
            "/api/records",
            json={
                "amount": float(i + 1) * 10,
                "type": "expense",
                "category_id": expense_category_id,
                "date": f"2026-06-{i + 1:02d}",
                "tags": [f"标签{i}"],
            },
        )

    resp = await client.get("/api/records/quick-templates")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 5
