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
    resp = await client.get("/api/budgets?month=2026-06")
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
        json={"amount": 500.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-15 12:00"},
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
                "consume_time": "2026-06-15 12:00",
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
        json={"amount": 2500.0, "type": "expense", "category_id": expense_category_id, "consume_time": "2026-06-15 12:00"},
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


@pytest.mark.asyncio
async def test_year_summary_fixed_12_ordered_months(
    client, expense_category_id, income_category_id
):
    """M6 用例 1：year-summary 固定返回 12 个月，顺序 01→12，每月 budgets 按 category_id 升序。"""
    # 查询年内两个月份 + 邻年月份（邻年不应参与聚合）
    await client.post(
        "/api/budgets",
        json={"category_id": income_category_id, "month": "2026-11", "amount": 900.0},
    )
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-11", "amount": 1200.0},
    )
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2026-03", "amount": 1500.0},
    )
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2025-12", "amount": 5000.0},
    )
    await client.post(
        "/api/budgets",
        json={"category_id": expense_category_id, "month": "2027-01", "amount": 7000.0},
    )

    resp = await client.get("/api/budgets/year-summary?year=2026")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0

    months = body["data"]["months"]
    assert body["data"]["year"] == 2026
    assert len(months) == 12
    assert [m["month"] for m in months] == [f"2026-{i:02d}" for i in range(1, 13)]

    # 无预算月份：空数组 + total 为 0
    empty = months[0]
    assert empty["month"] == "2026-01"
    assert empty["budgets"] == []
    assert empty["total_amount"] == 0
    assert empty["total_spent"] == 0

    # 有预算月份
    assert months[2]["total_amount"] == 1500.0
    assert months[10]["total_amount"] == 2100.0
    assert [b["category_id"] for b in months[10]["budgets"]] == sorted(
        [b["category_id"] for b in months[10]["budgets"]]
    )
    assert months[10]["total_amount"] == sum(b["amount"] for b in months[10]["budgets"])

    # 邻年预算不混入
    assert all(b["month"].startswith("2026-") for m in months for b in m["budgets"])


@pytest.mark.asyncio
async def test_year_summary_totals_and_spent_match_monthly_api(
    client, expense_category_id, income_category_id
):
    """M6 用例 2：各月 total 等于该月 budgets 求和；spent 与按月 GET /api/budgets 一致。

    同时覆盖易错点 7：年汇总行的 spent 必须按各 budget 自身月份统计，
    不得统一按查询年的某个月计算。
    """
    plan = {
        "2026-01": (1000.0, 2000.0),
        "2026-02": (1500.5, 3000.0),
        "2026-07": (800.0, 4000.0),
    }
    for month, (expense_amt, income_amt) in plan.items():
        await client.post(
            "/api/budgets",
            json={"category_id": expense_category_id, "month": month, "amount": expense_amt},
        )
        await client.post(
            "/api/budgets",
            json={"category_id": income_category_id, "month": month, "amount": income_amt},
        )

    # 每月各一笔支出（金额不同），用于校验 spent 的月份口径
    for month, amount in (("2026-01", 200.0), ("2026-01", 150.0), ("2026-02", 700.0), ("2026-07", 60.0)):
        await client.post(
            "/api/records",
            json={
                "amount": amount,
                "type": "expense",
                "category_id": expense_category_id,
                "consume_time": f"{month}-15 12:00",
            },
        )

    resp = await client.get("/api/budgets/year-summary?year=2026")
    assert resp.status_code == 200
    months = {m["month"]: m for m in resp.json()["data"]["months"]}

    for month, (expense_amt, income_amt) in plan.items():
        monthly = (await client.get(f"/api/budgets?month={month}")).json()["data"]
        entry = months[month]

        # 行结构与按月接口一致（category_id / spent 口径回归）
        assert {b["category_id"] for b in entry["budgets"]} == {b["category_id"] for b in monthly}
        by_cat = {b["category_id"]: b for b in monthly}
        for row in entry["budgets"]:
            assert row["spent"] == by_cat[row["category_id"]]["spent"]
            assert row["amount"] == by_cat[row["category_id"]]["amount"]
            assert row["month"] == month

        # total = 该月 budgets 求和
        assert entry["total_amount"] == round(sum(b["amount"] for b in entry["budgets"]), 2)
        assert entry["total_spent"] == round(sum(b["spent"] for b in entry["budgets"]), 2)
        assert entry["total_amount"] == round(expense_amt + income_amt, 2)

    # spent 只统计各自月份
    assert months["2026-01"]["total_spent"] == 350.0
    assert months["2026-02"]["total_spent"] == 700.0
    assert months["2026-07"]["total_spent"] == 60.0
    # 未设置预算的月份为空
    assert months["2026-03"]["budgets"] == []
    assert months["2026-03"]["total_amount"] == 0


@pytest.mark.asyncio
async def test_year_summary_data_isolation(auth_client_a, auth_client_b):
    """M6 用例 3：数据隔离——跨用户不可见。"""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A的预算分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    await auth_client_a.post(
        "/api/budgets",
        json={"category_id": cat_id, "month": "2026-05", "amount": 1111.0},
    )

    resp = await auth_client_a.get("/api/budgets/year-summary?year=2026")
    assert resp.status_code == 200
    a_months = resp.json()["data"]["months"]
    assert a_months[4]["total_amount"] == 1111.0
    assert len(a_months[4]["budgets"]) == 1

    resp = await auth_client_b.get("/api/budgets/year-summary?year=2026")
    assert resp.status_code == 200
    b_months = resp.json()["data"]["months"]
    assert len(b_months) == 12
    assert all(m["budgets"] == [] for m in b_months)
    assert all(m["total_amount"] == 0 for m in b_months)
    assert all(m["total_spent"] == 0 for m in b_months)


@pytest.mark.asyncio
async def test_year_summary_requires_auth(anon_client):
    """M6 用例 4a：未认证 → 401。"""
    resp = await anon_client.get("/api/budgets/year-summary?year=2026")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_year_summary_param_validation(client):
    """M6 用例 4b：year 缺失 / 非数字 / 超出范围 → 422。"""
    for url in (
        "/api/budgets/year-summary",
        "/api/budgets/year-summary?year=abc",
        "/api/budgets/year-summary?year=1999",
        "/api/budgets/year-summary?year=2101",
    ):
        resp = await client.get(url)
        assert resp.status_code == 422, url


@pytest.mark.asyncio
async def test_year_summary_without_any_budget(client):
    """M6 用例 5：无任何预算 → 12 个空月份，不报错。"""
    resp = await client.get("/api/budgets/year-summary?year=2030")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    months = body["data"]["months"]
    assert len(months) == 12
    assert [m["month"] for m in months] == [f"2030-{i:02d}" for i in range(1, 13)]
    assert all(m["budgets"] == [] for m in months)
    assert all(m["total_amount"] == 0 and m["total_spent"] == 0 for m in months)


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
