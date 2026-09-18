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
            "consume_time": "2026-06-01 12:00",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["amount"] == 25.50
    assert data["data"]["type"] == "expense"
    assert data["data"]["tag"] is None
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
            "consume_time": "2026-06-01 12:00",
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
            "consume_time": "2026-06-01 12:00",
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
            "consume_time": "2026-06-01 12:00",
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
            "consume_time": "2026-06-01 12:00",
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
        json={"amount": 100.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-01 12:00"},
    )
    await client.post(
        "/api/records",
        json={"amount": 200.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-02 12:00"},
    )
    await client.post(
        "/api/records",
        json={"amount": 5000.0, "type": "income", "category_id": income_category_id, "consume_time": "2026-06-01 12:00"},
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
        json={"amount": 50.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/records/{record_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == record_id
    assert data["data"]["tag"] is None


@pytest.mark.asyncio
async def test_update_record(client, expense_category_id):
    """Test updating a record."""
    resp = await client.post(
        "/api/records",
        json={"amount": 50.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/records/{record_id}",
        json={"amount": 75.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["amount"] == 75.0


@pytest.mark.asyncio
async def test_delete_record(client, expense_category_id):
    """Test deleting a record."""
    resp = await client.post(
        "/api/records",
        json={"amount": 50.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-01 12:00"},
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
            json={"amount": float(i + 1), "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-01 12:00"},
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
    """Test getting quick accounting templates (requires count >= 2)."""
    # Create a tag first
    tag_resp = await client.post(
        "/api/tags",
        json={"name": "午餐", "category_id": expense_category_id},
    )
    tag_id = tag_resp.json()["data"]["id"]

    # Create 2 records with same tag, type, and amount to trigger >= 2 threshold
    for _ in range(2):
        await client.post(
            "/api/records",
            json={
                "amount": 25.0,
                "type": "expense",
                "category_id": expense_category_id,
                "tag_id": tag_id,
                "consume_time": "2026-06-01 12:00",
            },
        )

    resp = await client.get("/api/records/quick-templates")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["tag_id"] == tag_id
    assert data["data"][0]["amount"] == 25.0


# ---------------------------------------------------------------------------
# M3: GET /api/records/earliest-year — 账单页年份切换的最早记录年份接口
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_earliest_year_returns_min_year(client, expense_category_id):
    """用例 1: 登录用户有 2023/2025 两年记录 → 返回 2023。"""
    for year in (2025, 2023):
        resp = await client.post(
            "/api/records",
            json={
                "amount": 10.0,
                "type": "expense",
                "category_id": expense_category_id,
                "consume_time": f"{year}-06-01 12:00",
            },
        )
        assert resp.status_code == 200

    resp = await client.get("/api/records/earliest-year")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["earliest_year"] == 2023


@pytest.mark.asyncio
async def test_earliest_year_null_when_no_records(client):
    """用例 2: 无记录用户 → earliest_year 为 null。"""
    resp = await client.get("/api/records/earliest-year")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["earliest_year"] is None


@pytest.mark.asyncio
async def test_earliest_year_isolated_per_user(auth_client_a, auth_client_b):
    """用例 3: 数据隔离——用户 A 的最早年份不受用户 B 记录影响。"""
    # 用户 A 建一条 2021 年记录
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_a = resp.json()["data"]["id"]
    await auth_client_a.post(
        "/api/records",
        json={"amount": 20.0, "type": "expense", "category_id": cat_a, "consume_time": "2021-03-05 08:00"},
    )

    # 用户 B 建一条更早的 1999 年记录
    resp = await auth_client_b.post(
        "/api/categories",
        json={"name": "B分类", "type": "expense", "icon": "mdi-cart", "sort_order": 1},
    )
    cat_b = resp.json()["data"]["id"]
    await auth_client_b.post(
        "/api/records",
        json={"amount": 30.0, "type": "expense", "category_id": cat_b, "consume_time": "1999-01-01 09:00"},
    )

    resp_a = await auth_client_a.get("/api/records/earliest-year")
    assert resp_a.status_code == 200
    assert resp_a.json()["data"]["earliest_year"] == 2021

    resp_b = await auth_client_b.get("/api/records/earliest-year")
    assert resp_b.status_code == 200
    assert resp_b.json()["data"]["earliest_year"] == 1999


@pytest.mark.asyncio
async def test_earliest_year_requires_auth(anon_client):
    """用例 4: 未认证 → 401（沿用 require_auth 行为）。"""
    resp = await anon_client.get("/api/records/earliest-year")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_earliest_year_not_shadowed_by_record_id_route(client):
    """用例 5: 路径不被 {record_id} 抢占（返回 200 而非 422）——回归路由声明顺序。"""
    resp = await client.get("/api/records/earliest-year")
    assert resp.status_code == 200, "被 /{record_id} 抢占会返回 422"
    body = resp.json()
    assert body["code"] == 0
    assert "earliest_year" in body["data"]

    # 数字路径仍应走 {record_id}：不存在的记录返回业务 404 码而非最早年份
    resp = await client.get("/api/records/999999")
    assert resp.json()["code"] == 40002
