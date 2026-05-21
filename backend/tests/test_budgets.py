"""Tests for budget API."""

import pytest


@pytest.mark.asyncio
async def test_create_budget(client, expense_category_id):
    """Test creating a budget."""
    resp = await client.post(
        "/api/budgets",
        json={
            "category_id": expense_category_id,
            "month": "2026-06",
            "amount": 2000.00,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["category_id"] == expense_category_id
    assert data["data"]["month"] == "2026-06"
    assert data["data"]["amount"] == 2000.00
    assert data["data"]["spent"] == 0.0
    assert data["data"]["remaining"] == 2000.00


@pytest.mark.asyncio
async def test_create_budget_upsert(client, expense_category_id):
    """Test that creating a budget with same category and month updates it (upsert)."""
    # Create first
    resp = await client.post(
        "/api/budgets",
        json={
            "category_id": expense_category_id,
            "month": "2026-06",
            "amount": 2000.00,
        },
    )
    assert resp.status_code == 200
    budget_id = resp.json()["data"]["id"]

    # Create again with different amount - should update
    resp = await client.post(
        "/api/budgets",
        json={
            "category_id": expense_category_id,
            "month": "2026-06",
            "amount": 2500.00,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == budget_id
    assert data["data"]["amount"] == 2500.00


@pytest.mark.asyncio
async def test_get_budgets(client, expense_category_id, income_category_id):
    """Test getting budgets for a month."""
    # Create budgets
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-06", "amount": 2000.00},
    )
    await client.post(
        "/api/budgets",
        json={"category_id": income_category_id, "month": "2026-06", "amount": 5000.00},
    )

    # Get all budgets for the month
    resp = await client.get("/api/budgets?month=2026-06")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2

    # Filter by type
    resp = await client.get("/api/budgets?month=2026-06&type=expense")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["type"] == "expense"


@pytest.mark.asyncio
async def test_update_budget(client, expense_category_id):
    """Test updating a budget."""
    resp = await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-06", "amount": 2000.00},
    )
    budget_id = resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/budgets/{budget_id}",
        json={"amount": 3000.00},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["amount"] == 3000.00


@pytest.mark.asyncio
async def test_delete_budget(client, expense_category_id):
    """Test deleting a budget."""
    resp = await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-06", "amount": 2000.00},
    )
    budget_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/budgets/{budget_id}")
    assert resp.status_code == 200

    # Verify it's gone
    resp = await client.get(f"/api/budgets?month=2026-06")
    assert len(resp.json()["data"]) == 0


@pytest.mark.asyncio
async def test_batch_set_budgets(client, expense_category_id, income_category_id):
    """Test batch setting budgets."""
    resp = await client.post(
        "/api/budgets/batch",
        json={
            "month": "2026-07",
            "budgets": [
                {"category_id": expense_category_id, "amount": 1500.00},
                {"category_id": income_category_id, "amount": 6000.00},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2

    # Verify
    resp = await client.get("/api/budgets?month=2026-07")
    assert len(resp.json()["data"]) == 2


@pytest.mark.asyncio
async def test_budget_overview(client, expense_category_id, income_category_id):
    """Test budget overview."""
    # Create expense records
    await client.post(
        "/api/records",
        json={"amount": 500.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-15", "tags": []},
    )

    # Create budget
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-06", "amount": 2000.00},
    )

    # Get overview
    resp = await client.get("/api/statistics/budget-overview?month=2026-06")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["month"] == "2026-06"
    assert data["data"]["total_budget"] == 2000.00
    assert data["data"]["total_spent"] == 500.0
    assert len(data["data"]["categories"]) == 1
    assert data["data"]["categories"][0]["status"] == "normal"
    assert data["data"]["categories"][0]["percentage"] == 25.0


@pytest.mark.asyncio
async def test_budget_with_spending(client, expense_category_id):
    """Test budget with actual spending data."""
    # Create records
    for i in range(3):
        await client.post(
            "/api/records",
            json={
                "amount": 300.0,
                "type": "expense",
                "category_id": expense_category_id,
                "date": "2026-06-15",
                "tags": [],
            },
        )

    # Create budget
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-06", "amount": 1000.00},
    )

    # Get budget list
    resp = await client.get("/api/budgets?month=2026-06")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"][0]["spent"] == 900.0  # 3 * 300
    assert data["data"][0]["remaining"] == 100.0
    assert data["data"][0]["percentage"] == 90.0

    # Should be warning status in overview
    resp = await client.get("/api/statistics/budget-overview?month=2026-06")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["categories"][0]["status"] == "warning"


@pytest.mark.asyncio
async def test_budget_exceeded(client, expense_category_id):
    """Test budget exceeded status."""
    await client.post(
        "/api/records",
        json={"amount": 2500.0, "type": "expense", "category_id": expense_category_id, "date": "2026-06-15", "tags": []},
    )

    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-06", "amount": 2000.00},
    )

    resp = await client.get("/api/statistics/budget-overview?month=2026-06")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["categories"][0]["status"] == "exceeded"
    assert data["data"]["overall_percentage"] == 125.0


@pytest.mark.asyncio
async def test_budget_empty_month(client):
    """Test budget overview for month with no budgets."""
    resp = await client.get("/api/statistics/budget-overview?month=2026-06")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total_budget"] == 0
    assert data["data"]["total_spent"] == 0
    assert len(data["data"]["categories"]) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_budget(client):
    """Test deleting a non-existent budget."""
    resp = await client.delete("/api/budgets/99999")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002


@pytest.fixture
async def expense_category_id(client):
    """Create an expense category and return its ID."""
    resp = await client.post(
        "/api/categories",
        json={"name": "餐饮预算", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def income_category_id(client):
    """Create an income category and return its ID."""
    resp = await client.post(
        "/api/categories",
        json={"name": "工资预算", "type": "income", "icon": "mdi-wallet", "sort_order": 1},
    )
    return resp.json()["data"]["id"]
