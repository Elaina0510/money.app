"""Tests for statistics API."""

import pytest


@pytest.fixture
async def tag_lunch(client):
    """Create a tag for lunch."""
    resp = await client.post(
        "/api/tags",
        json={"name": "午餐"},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def tag_dinner(client):
    """Create a tag for dinner."""
    resp = await client.post(
        "/api/tags",
        json={"name": "晚餐"},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def tag_salary(client):
    """Create a tag for salary."""
    resp = await client.post(
        "/api/tags",
        json={"name": "月薪"},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def expense_category_id(client):
    """Create an expense category."""
    resp = await client.post(
        "/api/categories",
        json={"name": "餐饮统计", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def income_category_id(client):
    """Create an income category."""
    resp = await client.post(
        "/api/categories",
        json={"name": "工资统计", "type": "income", "icon": "mdi-wallet", "sort_order": 1},
    )
    return resp.json()["data"]["id"]


@pytest.fixture
async def setup_test_data(client, expense_category_id, income_category_id, tag_lunch, tag_dinner, tag_salary):
    """Create test records for statistics."""
    # Expense records
    await client.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-01-15 12:00", "tag_id": tag_lunch},
    )
    await client.post(
        "/api/records",
        json={"amount": 200.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-02-10 12:00", "tag_id": tag_dinner},
    )
    # Income records
    await client.post(
        "/api/records",
        json={"amount": 5000.0, "type": "income", "category_id": income_category_id, "consume_time": "2026-01-01 12:00", "tag_id": tag_salary},
    )
    await client.post(
        "/api/records",
        json={"amount": 5000.0, "type": "income", "category_id": income_category_id, "consume_time": "2026-02-01 12:00", "tag_id": tag_salary},
    )
    yield


@pytest.mark.asyncio
async def test_summary(client, setup_test_data):
    """Test getting summary statistics."""
    resp = await client.get(
        "/api/statistics/summary",
        params={"period": "month", "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total_income"] == 5000.0
    assert data["data"]["total_expense"] == 100.0
    assert data["data"]["balance"] == 4900.0
    assert data["data"]["transaction_count"] == 2
    assert data["data"]["period"] == "month"


@pytest.mark.asyncio
async def test_summary_full_period(client, setup_test_data):
    """Test summary for the entire period."""
    resp = await client.get(
        "/api/statistics/summary",
        params={"period": "month", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total_income"] == 10000.0
    assert data["data"]["total_expense"] == 300.0
    assert data["data"]["transaction_count"] == 4


@pytest.mark.asyncio
async def test_summary_empty_period(client):
    """Test summary for a period with no data."""
    resp = await client.get(
        "/api/statistics/summary",
        params={"period": "month", "start_date": "2025-01-01", "end_date": "2025-01-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total_income"] == 0
    assert data["data"]["total_expense"] == 0
    assert data["data"]["balance"] == 0
    assert data["data"]["transaction_count"] == 0


@pytest.mark.asyncio
async def test_by_category(client, setup_test_data, expense_category_id, income_category_id):
    """Test category statistics."""
    # Test with expense type
    resp = await client.get(
        "/api/statistics/by-category",
        params={"type": "expense", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["items"]) > 0
    assert data["data"]["total_expense"] == 300.0

    # Check percentage
    item = data["data"]["items"][0]
    assert item["category_name"] == "餐饮统计"
    assert item["total"] == 300.0
    assert item["percentage"] == 100.0  # Only one category
    assert item["count"] == 2


@pytest.mark.asyncio
async def test_by_tag(client, setup_test_data):
    """Test tag statistics."""
    resp = await client.get(
        "/api/statistics/by-tag",
        params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["items"]) == 3
    # Should have: 午餐 (100), 晚餐 (200), 月薪 (10000)


@pytest.mark.asyncio
async def test_trend_monthly(client, setup_test_data):
    """Test monthly trend."""
    resp = await client.get(
        "/api/statistics/trend",
        params={"group_by": "month", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["items"]) == 2  # Jan and Feb

    # Check January
    jan = data["data"]["items"][0]
    assert jan["period"] == "2026-01"
    assert jan["income"] == 5000.0
    assert jan["expense"] == 100.0
    assert jan["balance"] == 4900.0


@pytest.mark.asyncio
async def test_trend_yearly(client, setup_test_data):
    """Test yearly trend."""
    resp = await client.get(
        "/api/statistics/trend",
        params={"group_by": "year", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["items"]) == 1
    year = data["data"]["items"][0]
    assert year["period"] == "2026"
    assert year["income"] == 10000.0
    assert year["expense"] == 300.0


@pytest.mark.asyncio
async def test_invalid_period(client):
    """Test invalid period parameter."""
    resp = await client.get(
        "/api/statistics/summary",
        params={"period": "invalid", "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40001


@pytest.mark.asyncio
async def test_invalid_group_by(client):
    """Test invalid group_by parameter."""
    resp = await client.get(
        "/api/statistics/trend",
        params={"group_by": "invalid", "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40001
