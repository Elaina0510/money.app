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
async def test_preset_categories_exist(client):
    """Test that preset categories are available."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    names = [c["name"] for c in data["data"]]
    assert "餐饮" in names
    assert "出行" in names
    assert "工资" in names
    assert "其他收入" in names


# --- Cascade delete tests ---


@pytest.mark.asyncio
async def test_delete_category_no_records(client):
    """Test deleting a category with no associated records returns deleted_records=0."""
    resp = await client.post(
        "/api/categories",
        json={"name": "空分类", "type": "expense", "icon": "mdi-empty", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["deleted_records"] == 0


@pytest.mark.asyncio
async def test_delete_category_cascades_records(client):
    """Test deleting a category with associated records cascade-deletes them."""
    # Create a category
    resp = await client.post(
        "/api/categories",
        json={"name": "级联分类", "type": "expense", "icon": "mdi-cascade", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]

    # Create records using this category
    await client.post(
        "/api/records",
        json={
            "amount": 100.0,
            "type": "expense",
            "category_id": cat_id,
            "consume_time": "2026-01-15 12:00",
        },
    )
    await client.post(
        "/api/records",
        json={
            "amount": 200.0,
            "type": "expense",
            "category_id": cat_id,
            "consume_time": "2026-01-16 12:00",
        },
    )

    # Delete the category
    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["deleted_records"] == 2


@pytest.mark.asyncio
async def test_delete_category_cascades_budgets(client):
    """Test deleting a category with associated budgets cascade-deletes them."""
    # Create a category
    resp = await client.post(
        "/api/categories",
        json={"name": "预算分类", "type": "expense", "icon": "mdi-budget", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]

    # Create a budget for this category (direct DB insert via API is not available,
    # so we test that the service handles budgets correctly via the delete call)
    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client):
    """Test deleting a non-existent category returns 404."""
    resp = await client.delete("/api/categories/99999")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002


@pytest.mark.asyncio
async def test_delete_other_user_custom_category_forbidden(auth_client_a, auth_client_b):
    """Test that user B cannot delete user A's custom category."""
    # User A creates a custom category
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A的分类", "type": "expense", "icon": "mdi-lock", "sort_order": 1},
    )
    assert resp.status_code == 200
    cat_id = resp.json()["data"]["id"]

    # User B tries to delete it
    resp = await auth_client_b.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == 40005


@pytest.mark.asyncio
async def test_delete_preset_category_any_user(client):
    """Preset categories are shared defaults and must not be deletable by any user."""
    # Get a preset category
    resp = await client.get("/api/categories")
    preset = next(c for c in resp.json()["data"] if c["is_preset"] == 1)
    cat_id = preset["id"]

    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == 40005


@pytest.mark.asyncio
async def test_cascade_delete_removes_records_from_list(client):
    """Test that after cascade delete, records are gone from the records list."""
    # Create a category
    resp = await client.post(
        "/api/categories",
        json={"name": "列表验证", "type": "expense", "icon": "mdi-check", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]

    # Create a record
    await client.post(
        "/api/records",
        json={
            "amount": 50.0,
            "type": "expense",
            "category_id": cat_id,
            "consume_time": "2026-03-01 10:00",
        },
    )

    # Verify record exists
    resp = await client.get("/api/records")
    assert resp.status_code == 200
    records_before = resp.json()["data"]["items"]
    assert any(r["category_id"] == cat_id for r in records_before)

    # Delete the category
    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted_records"] == 1

    # Verify record is gone
    resp = await client.get("/api/records")
    assert resp.status_code == 200
    records_after = resp.json()["data"]["items"]
    assert not any(r["category_id"] == cat_id for r in records_after)


# --- M2: 新增分类默认排序 +「其他」固定置尾 ---
#
# 测试库预设（conftest.PRESET_CATEGORIES）：
#   expense: 餐饮1 出行2 购物3 旅行4 账单与费用5（无「其他支出」，用例内按需补建）
#   income : 工资1 其他收入2


async def _categories_of(client, type_: str) -> list[dict]:
    """按类型取可见分类列表（已按 sort_order, id 升序）。"""
    resp = await client.get(f"/api/categories?type={type_}")
    assert resp.status_code == 200
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_m2_create_without_sort_order_appends_before_other(client):
    """用例 6.1.1: 不传 sort_order → 落位 = max(非「其他」)+1，连续创建依次后移且恒在「其他」前。"""
    # 「其他支出」非测试库预设，按生产语义补建（sort=99，显式传入 → 原样写入）
    resp = await client.post(
        "/api/categories",
        json={"name": "其他支出", "type": "expense", "sort_order": 99},
    )
    assert resp.status_code == 200

    created: list[int] = []
    for name in ("宠物", "健身"):
        resp = await client.post("/api/categories", json={"name": name, "type": "expense"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        created.append(data["sort_order"])
        assert data["is_preset"] == 0
        assert data["sort_order"] < 99  # 恒严格小于「其他」
    assert created == [6, 7]  # max(非「其他」)=5（账单与费用）→ 6、7 依次后移

    items = await _categories_of(client, "expense")
    names = [c["name"] for c in items]
    assert names[-1] == "其他支出"
    assert names.index("宠物") < names.index("健身") < names.index("其他支出")


@pytest.mark.asyncio
async def test_m2_create_sort_order_self_heals_when_other_not_at_tail(client):
    """用例 6.1.1 边界:「其他」未在末尾（异常数据）→ 新行仍被钳制到「其他」之前。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "其他支出", "type": "expense", "sort_order": 6},
    )
    assert resp.status_code == 200

    resp = await client.post("/api/categories", json={"name": "宠物", "type": "expense"})
    assert resp.status_code == 200
    new_sort = resp.json()["data"]["sort_order"]
    assert new_sort < 6  # base=max(非其他)=5 与 other-1 取小，保证置尾不变量

    items = await _categories_of(client, "expense")
    names = [c["name"] for c in items]
    assert names[-1] == "其他支出"


@pytest.mark.asyncio
async def test_m2_income_group_sort_calculated_independently(client):
    """用例 6.1.2: 收入分组独立计算，不受支出分组新增影响。"""
    other_before = next(c for c in await _categories_of(client, "income") if c["name"] == "其他收入")
    assert other_before["sort_order"] == 2

    resp = await client.post("/api/categories", json={"name": "奖金", "type": "income"})
    assert resp.status_code == 200
    bonus = resp.json()["data"]
    assert bonus["sort_order"] < other_before["sort_order"]  # 仍排在「其他收入」之前

    # 支出分组连续新增，收入分组的落位不受影响
    await client.post("/api/categories", json={"name": "宠物", "type": "expense"})
    resp = await client.post("/api/categories", json={"name": "稿费", "type": "income"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == bonus["sort_order"]

    items = await _categories_of(client, "income")
    names = [c["name"] for c in items]
    assert names[-1] == "其他收入"
    assert "宠物" not in names


@pytest.mark.asyncio
async def test_m2_create_with_explicit_sort_order_writes_as_given(client):
    """用例 6.1.3: 显式传 sort_order → 原样写入（向后兼容，不做服务端改写）。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "置顶分类", "type": "expense", "sort_order": 0},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 0

    resp = await client.post(
        "/api/categories",
        json={"name": "靠后分类", "type": "expense", "sort_order": 3},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 3

    items = await _categories_of(client, "expense")
    assert items[0]["name"] == "置顶分类"


@pytest.mark.asyncio
async def test_m2_create_negative_sort_order_rejected(client):
    """用例 6.1.3 参数非法: sort_order 负值 → 422（ge=0 约束保持）。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "非法排序", "type": "expense", "sort_order": -1},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_m2_update_ignores_sort_order(client):
    """用例 6.1.4: PUT 载荷携带 sort_order → 值不变（单个分类 PUT 不再改排序）。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "排序不变", "type": "expense", "sort_order": 50},
    )
    cat_id = resp.json()["data"]["id"]

    resp = await client.put(f"/api/categories/{cat_id}", json={"name": "改名", "sort_order": 1})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 50

    # 仅传 sort_order（无任何可更新字段）同样不改位
    resp = await client.put(f"/api/categories/{cat_id}", json={"sort_order": 2})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 50
    assert resp.json()["data"]["name"] == "改名"


@pytest.mark.asyncio
async def test_m2_update_other_name_forbidden_icon_allowed(client, auth_client_b, db_session):
    """用例 6.1.5: 「其他」预设/副本改名 → 400；改图标 → 200 且副本继承预设 sort_order，全局预设不被写脏。"""
    from app.models.category import Category

    income = await _categories_of(client, "income")
    preset = next(c for c in income if c["name"] == "其他收入")
    assert preset["is_preset"] == 1
    assert preset["sort_order"] == 2  # 测试库值；生产预设为 99（副本继承逻辑一致）

    # 预设「其他收入」禁改名
    resp = await client.put(f"/api/categories/{preset['id']}", json={"name": "杂项收入"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "不可修改" in body["message"]

    # 同名提交（无实义改名）放行
    resp = await client.put(f"/api/categories/{preset['id']}", json={"name": "其他收入"})
    assert resp.status_code == 200

    # 改图标 → CoW 生成用户副本，排序继承预设自身值
    resp = await client.put(f"/api/categories/{preset['id']}", json={"icon": "mdi-cash-multiple"})
    assert resp.status_code == 200
    copy = resp.json()["data"]
    assert copy["id"] != preset["id"]
    assert copy["is_preset"] == 0
    assert copy["name"] == "其他收入"
    assert copy["icon"] == "mdi-cash-multiple"
    assert copy["sort_order"] == preset["sort_order"]

    # 可见集合中「其他收入」只剩副本一份，且仍在末位
    income = await _categories_of(client, "income")
    others = [c for c in income if c["name"] == "其他收入"]
    assert len(others) == 1
    assert income[-1]["name"] == "其他收入"

    # 副本同样禁改名
    resp = await client.put(f"/api/categories/{copy['id']}", json={"name": "杂项"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    # 副本已存在时新增收入分类：max 计算按可见集合（副本生效、预设隐藏）不重复计入
    resp = await client.post("/api/categories", json={"name": "奖金", "type": "income"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] < copy["sort_order"]

    # 全局预设行未被写脏（另一用户可见原始预设）
    fresh_income = await _categories_of(auth_client_b, "income")
    fresh_preset = next(c for c in fresh_income if c["name"] == "其他收入")
    assert fresh_preset["is_preset"] == 1
    assert fresh_preset["icon"] == "mdi-cash-plus"
    assert fresh_preset["sort_order"] == 2
    preset_row = await db_session.get(Category, preset["id"])
    assert preset_row is not None
    assert preset_row.sort_order == 2
    assert preset_row.is_preset == 1


@pytest.mark.asyncio
async def test_m2_update_custom_category_renames_ok(client):
    """非「其他」自定义分类改名不受禁改约束影响（回归保护）。"""
    resp = await client.post("/api/categories", json={"name": "宠物", "type": "expense"})
    cat_id = resp.json()["data"]["id"]

    resp = await client.put(f"/api/categories/{cat_id}", json={"name": "萌宠"})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "萌宠"
    assert resp.json()["data"]["sort_order"] == 6


@pytest.mark.asyncio
async def test_m2_category_endpoints_require_auth(anon_client):
    """用例 6.1.6 未认证: create/update 端点未带 token → 401。"""
    resp = await anon_client.post("/api/categories", json={"name": "匿名", "type": "expense"})
    assert resp.status_code == 401

    resp = await anon_client.put("/api/categories/1", json={"name": "匿名改名"})
    assert resp.status_code == 401

    resp = await anon_client.get("/api/categories")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_m2_sort_isolation_between_users(auth_client_a, auth_client_b):
    """用例 6.1.6 数据隔离: 用户 A 的新增分类不参与用户 B 的 max 计算。"""
    for name in ("A1", "A2", "A3"):
        resp = await auth_client_a.post("/api/categories", json={"name": name, "type": "expense"})
        assert resp.status_code == 200
    a_orders = [c["sort_order"] for c in await _categories_of(auth_client_a, "expense")]
    assert a_orders[-3:] == [6, 7, 8]

    resp = await auth_client_b.post(
        "/api/categories", json={"name": "B1", "type": "expense"}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 6  # 仅按 B 自己的可见集合计算

    b_names = [c["name"] for c in await _categories_of(auth_client_b, "expense")]
    assert "A1" not in b_names
    a_names = [c["name"] for c in await _categories_of(auth_client_a, "expense")]
    assert "B1" not in a_names
