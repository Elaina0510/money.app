"""Tests for data isolation (v1.2 user_id filtering) and v1.4 auth hardening."""

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget, BudgetCategory
from app.models.category import Category
from app.models.record import Record
from app.models.user import User
from app.routers.auth import _migrate_orphan_data
from app.utils.auth import get_password_hash


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(anon_client):
    """1. v1.4: 所有业务端点要求登录,未带 token → 401。"""
    # 创建分类
    resp = await anon_client.post(
        "/api/categories",
        json={"name": "测试分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    assert resp.status_code == 401

    # 列表
    resp = await anon_client.get("/api/records")
    assert resp.status_code == 401

    # 附件
    resp = await anon_client.get("/api/attachments/1")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_orphan_legacy_data_migrated_to_first_user(db_session: AsyncSession):
    """2. v1.4: 历史遗留 user_id IS NULL 的数据,在首个用户注册时被接管。

    直接验证 _migrate_orphan_data(通过 API register 触发的内部逻辑)。
    """
    # 取一个预设分类
    cat = (await db_session.exec(select(Category).where(Category.is_preset == 1))).first()
    assert cat is not None

    # 插入一条历史遗留的 NULL-user 记录
    legacy = Record(
        amount=99.0,
        type="expense",
        category_id=cat.id,
        consume_time="2025-01-01 12:00",
        user_id=None,
    )
    db_session.add(legacy)
    await db_session.commit()
    await db_session.refresh(legacy)
    assert legacy.user_id is None

    # 创建首个用户并迁移孤儿数据
    user = User(username="firstuser", hashed_password=get_password_hash("pass"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await _migrate_orphan_data(db_session, user.id)

    await db_session.refresh(legacy)
    assert legacy.user_id == user.id


@pytest.mark.asyncio
async def test_auth_user_creates_and_sees_own_data(client, auth_client, auth_user):
    """2. Authenticated user creates records → user_id = current user, only visible to that user."""
    # Create a category as authenticated user
    resp = await auth_client.post(
        "/api/categories",
        json={"name": "用户分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    assert resp.status_code == 200
    cat_id = resp.json()["data"]["id"]

    # Create record as authenticated user
    resp = await auth_client.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    assert resp.status_code == 200

    # Authenticated user sees their own record
    resp = await auth_client.get("/api/records")
    assert resp.json()["data"]["total"] == 1

    # Anonymous user should not see it
    resp = await client.get("/api/records")
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_data_separation_between_users(db_session, client, auth_client, auth_user):
    """3. Data from different users is isolated."""
    # Create a preset category for setup
    resp = await client.post(
        "/api/categories",
        json={"name": "公共分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    assert resp.status_code == 200
    cat_id = resp.json()["data"]["id"]

    # Anonymous creates a record
    await client.post(
        "/api/records",
        json={"amount": 30.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )

    # Auth user creates a record with a different category
    resp = await auth_client.post(
        "/api/categories",
        json={"name": "用户分类2", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    auth_cat_id = resp.json()["data"]["id"]
    await auth_client.post(
        "/api/records",
        json={"amount": 200.0, "type": "expense", "category_id": auth_cat_id, "consume_time": "2026-06-01 12:00"},
    )

    # Each sees only their own
    resp = await client.get("/api/records")
    assert resp.json()["data"]["total"] == 1

    resp = await auth_client.get("/api/records")
    assert resp.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_first_user_inherits_anonymous_data(client, auth_client, auth_user):
    """4. (历史行为)首个用户接管孤儿数据的迁移逻辑,现由 test_orphan_legacy_data_migrated_to_first_user 直接覆盖。"""
    # v1.4 起 client 已认证,匿名共享池语义移除;保留本用例仅作占位,
    # 真正的迁移回归见 test_orphan_legacy_data_migrated_to_first_user。
    resp = await client.get("/api/records")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_preset_categories_visible_to_all(client, auth_client):
    """5. Preset categories (is_preset=1) are visible to all users."""
    # Preset categories are seeded in setup_database fixture
    # Both anonymous and authenticated should see them

    # Anonymous
    resp = await client.get("/api/categories")
    anon_data = resp.json()["data"]
    anon_names = {c["name"] for c in anon_data}
    assert "餐饮" in anon_names

    # Authenticated
    resp = await auth_client.get("/api/categories")
    auth_data = resp.json()["data"]
    auth_names = {c["name"] for c in auth_data}
    assert "餐饮" in auth_names


@pytest.mark.asyncio
async def test_custom_categories_visible_only_to_owner(client, auth_client):
    """6. Custom categories are visible only to their creator."""
    # Create a custom category as authenticated user
    resp = await auth_client.post(
        "/api/categories",
        json={"name": "我的私有分类", "type": "expense", "icon": "mdi-lock", "sort_order": 99},
    )
    assert resp.status_code == 200

    # Auth user sees it
    resp = await auth_client.get("/api/categories")
    names = {c["name"] for c in resp.json()["data"]}
    assert "我的私有分类" in names

    # Anonymous should NOT see it
    resp = await client.get("/api/categories")
    names = {c["name"] for c in resp.json()["data"]}
    assert "我的私有分类" not in names


@pytest.mark.asyncio
async def test_user_b_cannot_update_user_a_record(auth_client_a, auth_client_b):
    """7. User A creates record, User B tries to update → 403."""
    # User A creates category and record
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # User B tries to update → 403
    resp = await auth_client_b.put(
        f"/api/records/{record_id}",
        json={"amount": 999.0},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_record(auth_client_a, auth_client_b):
    """8. User A creates record, User B tries to delete → 403."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # User B tries to delete → 403
    resp = await auth_client_b.delete(f"/api/records/{record_id}")
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_user_b_cannot_batch_delete_user_a_records(auth_client_a, auth_client_b):
    """9. User A creates records, User B tries to batch delete → 403."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # User B tries to batch delete → 403
    resp = await auth_client_b.post(
        "/api/records/batch-delete",
        json={"ids": [record_id]},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_user_b_cannot_update_user_a_tag(auth_client_a, auth_client_b):
    """10. User A creates tag, User B tries to update → 403."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/tags",
        json={"name": "A标签", "category_id": cat_id},
    )
    tag_id = resp.json()["data"]["id"]

    # User B tries to update → 403
    resp = await auth_client_b.put(
        f"/api/tags/{tag_id}",
        json={"name": "被篡改"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_tag(auth_client_a, auth_client_b):
    """11. User A creates tag, User B tries to delete → 403."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/tags",
        json={"name": "A标签", "category_id": cat_id},
    )
    tag_id = resp.json()["data"]["id"]

    # User B tries to delete → 403
    resp = await auth_client_b.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_user_can_update_own_record(auth_client_a):
    """12. User updates own record → success (200)."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # User A updates own record → 200
    resp = await auth_client_a.put(
        f"/api/records/{record_id}",
        json={"amount": 200.0},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["amount"] == 200.0


@pytest.mark.asyncio
async def test_user_can_delete_own_record(auth_client_a):
    """13. User deletes own record → success (200)."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # User A deletes own record → 200
    resp = await auth_client_a.delete(f"/api/records/{record_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_can_update_own_tag(auth_client_a):
    """14. User updates own tag → success (200)."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/tags",
        json={"name": "A标签", "category_id": cat_id},
    )
    tag_id = resp.json()["data"]["id"]

    # User A updates own tag → 200
    resp = await auth_client_a.put(
        f"/api/tags/{tag_id}",
        json={"name": "新名称"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "新名称"


@pytest.mark.asyncio
async def test_user_can_delete_own_tag(auth_client_a):
    """15. User deletes own tag → success (200)."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/tags",
        json={"name": "A标签", "category_id": cat_id},
    )
    tag_id = resp.json()["data"]["id"]

    # User A deletes own tag → 200
    resp = await auth_client_a.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_anonymous_cannot_update_user_record(client, auth_client_a):
    """16. Anonymous user tries to update record with user_id → 403."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # Anonymous tries to update → 403
    resp = await client.put(
        f"/api/records/{record_id}",
        json={"amount": 999.0},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_anonymous_cannot_delete_user_record(client, auth_client_a):
    """17. Anonymous user tries to delete record with user_id → 403."""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    record_id = resp.json()["data"]["id"]

    # Anonymous tries to delete → 403
    resp = await client.delete(f"/api/records/{record_id}")
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


# ---------------------------------------------------------------------------
# 18–22：v1.4.3 M12 预算段（新表 budgets + budget_categories）
#
# 口径反转登记：旧预算段用例按「每 (分类,月) 一条」造数据（payload 带
# category_id），新模型下分类关联改走 budget_categories，故以下用例全部按
# 新契约 {month, name, amount, scope_mode, category_ids} 重写；22 为本版
# 新增的 **spent 跨用户隔离** 锁（任务 3.1 审查修订 / §11.2）。
# ---------------------------------------------------------------------------

BUDGET_MONTH = "2026-06"


async def preset_category_id(client, name: str) -> int:
    """取预设分类 id（两用户共享同一行，故可各自在同一分类下记账）."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    for cat in resp.json()["data"]:
        if cat["name"] == name:
            return int(cat["id"])
    raise AssertionError(f"预设分类缺失：{name}")


async def make_budget(client, category_ids: list[int], **overrides) -> dict:
    payload = {
        "month": BUDGET_MONTH,
        "name": "隔离测试预算",
        "amount": 1000.0,
        "scope_mode": "include",
        "category_ids": category_ids,
    }
    payload.update(overrides)
    resp = await client.post("/api/budgets", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def expense(client, amount: float, category_id: int) -> None:
    resp = await client.post(
        "/api/records",
        json={
            "amount": amount,
            "type": "expense",
            "category_id": category_id,
            "consume_time": f"{BUDGET_MONTH}-10 12:00",
        },
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_user_b_cannot_see_user_a_budgets(auth_client_a, auth_client_b):
    """18. 列表/年汇总均按 user_id 隔离：B 看不到 A 的命名预算."""
    cat_a = await preset_category_id(auth_client_a, "餐饮")
    created = await make_budget(auth_client_a, [cat_a], name="A的日常")

    resp = await auth_client_a.get("/api/budgets", params={"month": BUDGET_MONTH})
    assert resp.status_code == 200
    assert [b["id"] for b in resp.json()["data"]] == [created["id"]]

    resp = await auth_client_b.get("/api/budgets", params={"month": BUDGET_MONTH})
    assert resp.status_code == 200
    assert resp.json()["data"] == [], "B 不得看到 A 的预算"

    resp = await auth_client_b.get("/api/budgets/year-summary", params={"year": 2026})
    june = resp.json()["data"]["months"][5]
    assert june["month"] == BUDGET_MONTH
    assert june["budgets"] == []
    assert june["total_amount"] == 0 and june["total_spent"] == 0


@pytest.mark.asyncio
async def test_user_b_cannot_update_user_a_budget(auth_client_a, auth_client_b):
    """19. B 改 A 的预算 → 403/40005，且 A 的数据原样未动."""
    cat_a = await preset_category_id(auth_client_a, "餐饮")
    created = await make_budget(auth_client_a, [cat_a], amount=1000.0)

    resp = await auth_client_b.put(
        f"/api/budgets/{created['id']}",
        json={"name": "被篡改", "amount": 1.0, "scope_mode": "include", "category_ids": [cat_a]},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005

    mine = (await auth_client_a.get("/api/budgets", params={"month": BUDGET_MONTH})).json()["data"]
    assert mine[0]["name"] == "隔离测试预算"
    assert mine[0]["amount"] == 1000.0


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_budget(auth_client_a, auth_client_b, db_session):
    """20. B 删 A 的预算 → 403/40005，预算行与关联行都还在."""
    cat_a = await preset_category_id(auth_client_a, "餐饮")
    created = await make_budget(auth_client_a, [cat_a])

    resp = await auth_client_b.delete(f"/api/budgets/{created['id']}")
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005

    budget = (
        await db_session.exec(select(Budget).where(Budget.id == created["id"]))
    ).first()
    assert budget is not None, "越权删除必须不留痕迹地失败"
    assert budget.user_id is not None
    links = (
        await db_session.exec(
            select(BudgetCategory.category_id).where(
                BudgetCategory.budget_id == created["id"]
            )
        )
    ).all()
    assert [int(c) for c in links] == [cat_a]


@pytest.mark.asyncio
async def test_budget_spent_excludes_other_users_expenses(auth_client_a, auth_client_b):
    """21. 预算列表的 spent 只聚合本人支出（任务 3.1 的 user_id 谓词）."""
    cat_a = await preset_category_id(auth_client_a, "餐饮")
    created = await make_budget(auth_client_a, [cat_a], amount=1000.0)
    assert created["spent"] == 0

    await expense(auth_client_a, 100.0, cat_a)
    await expense(auth_client_b, 800.0, cat_a)  # 同一分类行、不同用户

    mine = (await auth_client_a.get("/api/budgets", params={"month": BUDGET_MONTH})).json()["data"]
    assert mine[0]["spent"] == 100.0, "B 的 800 不得并入 A 的 spent"
    assert mine[0]["remaining"] == 900.0

    theirs = (await auth_client_b.get("/api/budgets", params={"month": BUDGET_MONTH})).json()["data"]
    assert theirs == []


@pytest.mark.asyncio
async def test_budget_exclude_base_total_is_own_month_only(auth_client_a, auth_client_b):
    """22. exclude 的「当月全部支出」基数同样只取本人（含 details 与 year-summary）.

    锁死审查记录②：旧实现缺 user_id 谓词，会把他人同分类支出并进基数，
    导致 exclude 预算 spent 虚高。
    """
    food = await preset_category_id(auth_client_a, "餐饮")
    transport = await preset_category_id(auth_client_a, "出行")

    await expense(auth_client_a, 100.0, food)
    await expense(auth_client_a, 20.0, transport)
    await expense(auth_client_b, 999.0, food)
    await expense(auth_client_b, 777.0, transport)

    full = await make_budget(auth_client_a, [], scope_mode="exclude", name="全支出")
    assert full["spent"] == 120.0, "基数只能是 A 自己的当月支出 120，非 1896"
    assert {d["category_id"] for d in full["details"]} == {food, transport}
    assert sum(d["spent"] for d in full["details"]) == 120.0

    excluded = await make_budget(
        auth_client_a, [transport], scope_mode="exclude", name="除出行外"
    )
    assert excluded["spent"] == 100.0
    assert [d["category_id"] for d in excluded["details"]] == [food]

    months = (
        await auth_client_a.get("/api/budgets/year-summary", params={"year": 2026})
    ).json()["data"]["months"]
    june = months[5]
    assert june["total_amount"] == 2000.0
    assert june["total_spent"] == 220.0, "年汇总逐月 spent 亦为本人 Σ 各预算"

    overview = (
        await auth_client_a.get("/api/statistics/budget-overview", params={"month": BUDGET_MONTH})
    ).json()["data"]
    assert overview["total_spent"] == 220.0
