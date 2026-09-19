"""Tests for M3 batch category reordering (PUT /api/categories/reorder).

测试库预设（conftest.PRESET_CATEGORIES）：
  expense: 餐饮1 出行2 购物3 旅行4 账单与费用5（无「其他支出」，用例内补建为 sort=99）
  income : 工资1 其他收入2
"""

import pytest
from httpx import AsyncClient


async def _visible(client: AsyncClient, type_: str) -> list[dict]:
    """按类型取可见分类列表（已按 sort_order, id 升序）。"""
    resp = await client.get(f"/api/categories?type={type_}")
    assert resp.status_code == 200
    return resp.json()["data"]


async def _reorder(client: AsyncClient, type_: str, ids: list[int]):
    return await client.put("/api/categories/reorder", json={"type": type_, "ids": ids})


async def _seed_expense_other(client: AsyncClient) -> list[dict]:
    """支出组补建「其他支出」（生产为预设，测试库缺省），返回重排前的可见列表。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "其他支出", "type": "expense", "icon": "mdi-cash-minus", "sort_order": 99},
    )
    assert resp.status_code == 200
    return await _visible(client, "expense")


@pytest.mark.asyncio
async def test_m3_reorder_route_order_returns_200_not_422(client):
    """§7.2 路由顺序回归: /reorder 必须先于 /{category_id} 声明，错位即被路径参数抢匹配 422。"""
    before = await _seed_expense_other(client)
    ids = [c["id"] for c in before]

    resp = await _reorder(client, "expense", ids)
    assert resp.status_code == 200, "被 /{category_id} 抢匹配时会返回 422"
    assert resp.json()["code"] == 0
    assert resp.json()["message"] == "排序已保存"


@pytest.mark.asyncio
async def test_m3_reorder_full_ids_normalizes_to_contiguous_1_n(client):
    """用例 7.1.1: 乱序全量 ids → 响应按提交序返回，sort_order 归一化为 1..n 连续。"""
    before = await _seed_expense_other(client)
    assert [c["sort_order"] for c in before] == [1, 2, 3, 4, 5, 99]

    submitted = list(reversed(before))  # [其他支出, 账单与费用, 旅行, 购物, 出行, 餐饮]
    resp = await _reorder(client, "expense", [c["id"] for c in submitted])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [c["name"] for c in data] == [
        "账单与费用",
        "旅行",
        "购物",
        "出行",
        "餐饮",
        "其他支出",
    ]
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))

    # 落库真值与响应一致（重新 GET）
    after = await _visible(client, "expense")
    assert [c["id"] for c in after] == [c["id"] for c in data]
    assert [c["sort_order"] for c in after] == list(range(1, len(after) + 1))


@pytest.mark.asyncio
async def test_m3_reorder_forces_other_category_to_tail(client):
    """用例 7.1.2:「其他」放在 ids 中间提交 → 响应与库中均被强制置尾（n）。"""
    before = await _seed_expense_other(client)
    ids = [c["id"] for c in before]
    other_id = next(c["id"] for c in before if c["name"] == "其他支出")
    assert other_id == ids[-1]

    # 人为把「其他」插到第 3 位：其余行相对次序保持不变
    middle = ids[:2] + [other_id] + ids[2:5]
    resp = await _reorder(client, "expense", middle)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[-1]["name"] == "其他支出"
    assert data[-1]["sort_order"] == len(data)
    assert [c["name"] for c in data] == ["餐饮", "出行", "购物", "旅行", "账单与费用", "其他支出"]

    stored = await _visible(client, "expense")
    assert stored[-1]["id"] == other_id
    assert stored[-1]["sort_order"] == 6


@pytest.mark.asyncio
async def test_m3_reorder_preset_rows_use_cow_and_keep_global_preset(client, db_session, auth_client_b):
    """用例 7.1.3: 含预设行 → 写用户副本；全局预设行 sort_order 不变（新用户 GET 回归）。"""
    from app.models.category import Category

    before = await _seed_expense_other(client)
    preset_food = next(c for c in before if c["name"] == "餐饮")
    assert preset_food["is_preset"] == 1
    preset_food_id = preset_food["id"]

    # 前两位互换：餐饮 ↔ 出行
    ids = [c["id"] for c in before]
    swapped = [ids[1], ids[0]] + ids[2:]
    resp = await _reorder(client, "expense", swapped)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [c["name"] for c in data][:2] == ["出行", "餐饮"]
    moved = {c["name"]: c for c in data}
    # 改位的预设行落在用户副本上
    assert moved["出行"]["is_preset"] == 0
    assert moved["出行"]["id"] != ids[1]
    assert moved["餐饮"]["is_preset"] == 0
    assert moved["餐饮"]["id"] != preset_food_id
    # 未改位的预设行仍为预设原行（无需 CoW）
    assert moved["购物"]["is_preset"] == 1

    # 全局预设行未被写脏
    preset_row = await db_session.get(Category, preset_food_id)
    assert preset_row is not None
    assert preset_row.sort_order == 1
    assert preset_row.is_preset == 1

    # 另一新验证用户看到的仍是原始预设顺序
    fresh = await _visible(auth_client_b, "expense")
    assert [c["sort_order"] for c in fresh] == [1, 2, 3, 4, 5]
    assert [c["name"] for c in fresh] == ["餐饮", "出行", "购物", "旅行", "账单与费用"]
    assert all(c["is_preset"] == 1 for c in fresh)
    assert "其他支出" not in [c["name"] for c in fresh]  # 属 test user 的自定义行

    # 再次重排：副本被更新而非再新建（同名列仍只有一份）
    resp = await _reorder(client, "expense", [data[1]["id"], data[0]["id"]] + ids[2:])
    assert resp.status_code == 200
    again = await _visible(client, "expense")
    assert [c["name"] for c in again][:2] == ["餐饮", "出行"]
    assert sum(1 for c in again if c["name"] == "餐饮") == 1
    assert sum(1 for c in again if c["name"] == "出行") == 1
    assert len(again) == len(before)


@pytest.mark.asyncio
async def test_m3_reorder_incomplete_ids_rejected(client):
    """用例 7.1.4 参数非法: ids 缺一项（漏位）→ 400 PARAM_ERROR。"""
    before = await _seed_expense_other(client)
    ids = [c["id"] for c in before]

    resp = await _reorder(client, "expense", ids[:-2] + ids[-1:])
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "排序列表与当前分类不一致" in body["message"]

    # 顺序未受影响
    after = await _visible(client, "expense")
    assert [c["id"] for c in after] == ids


@pytest.mark.asyncio
async def test_m3_reorder_duplicate_ids_rejected(client):
    """用例 7.1.4 参数非法: ids 含重复 → 400。"""
    before = await _seed_expense_other(client)
    ids = [c["id"] for c in before]

    resp = await _reorder(client, "expense", ids[:-1] + [ids[0], ids[0]])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    # 空提交同样拒绝（可见集合非空时不可能等价）
    resp = await _reorder(client, "expense", [])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


@pytest.mark.asyncio
async def test_m3_reorder_other_user_id_rejected(auth_client_a, auth_client_b):
    """用例 7.1.4 数据隔离: ids 含他人分类 id → 400，且他人顺序不被改写。"""
    await _seed_expense_other(auth_client_a)
    resp = await auth_client_b.post("/api/categories", json={"name": "宠物", "type": "expense"})
    assert resp.status_code == 200
    b_own = resp.json()["data"]

    a_visible = await _visible(auth_client_a, "expense")
    a_ids = [c["id"] for c in a_visible]
    # 用 B 的自定义行顶替 A 的一位
    resp = await _reorder(auth_client_a, "expense", a_ids[:-1] + [b_own["id"]])
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "排序列表与当前分类不一致" in body["message"]

    # B 的行排序未被 A 改写
    b_visible = await _visible(auth_client_b, "expense")
    assert next(c for c in b_visible if c["id"] == b_own["id"])["sort_order"] == b_own["sort_order"]
    # A 的可见顺序保持不变
    assert [c["id"] for c in await _visible(auth_client_a, "expense")] == a_ids


@pytest.mark.asyncio
async def test_m3_reorder_requires_other_category_present(client):
    """用例 7.1.4 异常数据: 可见集合中无「其他」行 → 400（拒绝保存而非静默丢位）。"""
    expense = await _visible(client, "expense")
    resp = await _reorder(client, "expense", [c["id"] for c in expense])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


@pytest.mark.asyncio
async def test_m3_reorder_invalid_type_returns_422(client):
    """用例 7.1.4 参数非法: type 非 expense/income → 422（Literal 校验）。"""
    income = await _visible(client, "income")
    resp = await _reorder(client, "other", [c["id"] for c in income])  # type: ignore[arg-type]
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_m3_reorder_unauthenticated_returns_401(anon_client):
    """用例 7.1.4 未认证: 无 token → 401。"""
    resp = await anon_client.put("/api/categories/reorder", json={"type": "income", "ids": [1]})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_m3_reorder_income_group_does_not_touch_expense_order(client):
    """用例 7.1.5: 收入组重排不影响支出组顺序（分组独立）。"""
    expense_before = await _seed_expense_other(client)
    income_before = await _visible(client, "income")
    assert [c["name"] for c in income_before] == ["工资", "其他收入"]

    resp = await _reorder(client, "income", [c["id"] for c in reversed(income_before)])
    assert resp.status_code == 200
    income_after = resp.json()["data"]
    assert [c["name"] for c in income_after] == ["工资", "其他收入"]
    assert [c["sort_order"] for c in income_after] == [1, 2]

    assert [c["id"] for c in await _visible(client, "expense")] == [
        c["id"] for c in expense_before
    ]
    assert [c["sort_order"] for c in await _visible(client, "expense")] == [1, 2, 3, 4, 5, 99]
