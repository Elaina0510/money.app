"""Tests for batch category reordering (PUT /api/categories/reorder).

v1.4.3 M8：分类不再分收支两组，载荷由 `{type, ids}` 收敛为 `{ids}`（全量有序 id），
「其他」强制归一化到末位的设计不变，作用域从「组内」改「全列表」。

测试库预设（`conftest.PRESET_CATEGORIES`，过期 7 条副本——见 9.3a 登记）：
  餐饮1 出行2 购物3 旅行4 账单与费用5 工资1 其他收入2
  → 按 (sort_order, id) 排序的可见单列表为
    [餐饮(1), 工资(1), 出行(2), 其他收入(2), 购物(3), 旅行(4), 账单与费用(5)]
  注意两点，别把它们当成生产语义：
    * 旧语义两组的 sort_order 现在同处一列，**天然带重号**（1,1,2,2），
      重排归一化为 1..n 时必然整体后移；
    * 名为「其他」的行不存在（旧名「其他收入」按 D11 不再判为「其他」），用例内补建。
"""

import pytest
from httpx import AsyncClient


async def _visible(client: AsyncClient) -> list[dict]:
    """可见分类列表（已按 sort_order, id 升序）。"""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    return resp.json()["data"]


async def _reorder(client: AsyncClient, ids: list[int]):
    return await client.put("/api/categories/reorder", json={"ids": ids})


async def _seed_other(client: AsyncClient) -> list[dict]:
    """补建「其他」（生产属预设、测试库缺省），返回重排前的全量可见列表。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "其他", "icon": "mdi-cash-minus", "sort_order": 99},
    )
    assert resp.status_code == 200
    return await _visible(client)


@pytest.mark.asyncio
async def test_reorder_route_order_returns_200_not_422(client):
    """路由顺序回归: /reorder 必须先于 /{category_id} 声明，错位即被路径参数抢匹配 422。"""
    before = await _seed_other(client)
    resp = await _reorder(client, [c["id"] for c in before])
    assert resp.status_code == 200, "被 /{category_id} 抢匹配时会返回 422"
    assert resp.json()["code"] == 0
    assert resp.json()["message"] == "排序已保存"


@pytest.mark.asyncio
async def test_reorder_full_ids_normalizes_to_contiguous_1_n(client):
    """9.2: 乱序全量 ids → 响应按提交序返回（「其他」除外），sort_order 归一化 1..n 连续。"""
    before = await _seed_other(client)
    assert [c["sort_order"] for c in before] == [1, 1, 2, 2, 3, 4, 5, 99]

    submitted = list(reversed(before))  # [其他, 账单与费用, 旅行, 购物, 其他收入, 出行, 工资, 餐饮]
    resp = await _reorder(client, [c["id"] for c in submitted])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [c["name"] for c in data] == [
        "账单与费用",
        "旅行",
        "购物",
        "其他收入",
        "出行",
        "工资",
        "餐饮",
        "其他",
    ]
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))

    # 落库真值与响应一致（重新 GET）
    after = await _visible(client)
    assert [c["id"] for c in after] == [c["id"] for c in data]
    assert [c["sort_order"] for c in after] == list(range(1, len(after) + 1))


@pytest.mark.asyncio
async def test_reorder_forces_other_category_to_tail(client):
    """9.2「其他」强制置末：放在列表中间提交 → 响应与库中均被归一化到 n。"""
    before = await _seed_other(client)
    ids = [c["id"] for c in before]
    other_id = next(c["id"] for c in before if c["name"] == "其他")
    assert other_id == ids[-1]

    # 人为把「其他」插到第 3 位：其余行相对次序保持不变
    middle = ids[:2] + [other_id] + ids[2:7]
    resp = await _reorder(client, middle)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[-1]["name"] == "其他"
    assert data[-1]["sort_order"] == len(data)
    assert [c["name"] for c in data] == [
        "餐饮",
        "工资",
        "出行",
        "其他收入",
        "购物",
        "旅行",
        "账单与费用",
        "其他",
    ]

    stored = await _visible(client)
    assert stored[-1]["id"] == other_id
    assert stored[-1]["sort_order"] == 8


@pytest.mark.asyncio
async def test_reorder_legacy_income_rows_share_the_single_sequence(client):
    """原「收入组重排不影响支出组」用例改写：统一列表后一次重排即全列表归一化。

    v1.4.2 用例 `test_m3_reorder_income_group_does_not_touch_expense_order` 断言两组各自
    独立重排——该语义随 M8 废弃。本用例改为断言：把旧收入侧预设「工资」提到首位，
    旧支出侧预设随之一并后移，最终只有一个 1..n 序列（不存在第二组编号）。
    """
    before = await _seed_other(client)
    salary = next(c for c in before if c["name"] == "工资")
    rest = [c for c in before if c["name"] != "工资"]
    resp = await _reorder(client, [salary["id"]] + [c["id"] for c in rest])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[0]["name"] == "工资"
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))
    assert data[-1]["name"] == "其他"
    # 全列表只有一段连续编号：不存在"另一组"从 1 重新开始
    assert sorted(c["sort_order"] for c in data) == list(range(1, len(data) + 1))


@pytest.mark.asyncio
async def test_reorder_preset_rows_use_cow_and_keep_global_preset(
    client, db_session, auth_client_b
):
    """9.2 预设行改序落副本：全局预设行 sort_order 不被写脏，新副本不再叠加。"""
    from app.models.category import Category

    before = await _seed_other(client)
    food = next(c for c in before if c["name"] == "餐饮")
    assert food["is_preset"] == 1
    # 末两位互换：旅行(4) ↔ 账单与费用(5)；「餐饮」保持首位（目标位 = 原 1，不该建副本）
    ids = [c["id"] for c in before]
    swapped = ids[:5] + [ids[6], ids[5]] + ids[7:]
    resp = await _reorder(client, swapped)
    assert resp.status_code == 200
    data = resp.json()["data"]
    by_name = {c["name"]: c for c in data}
    assert [c["name"] for c in data] == [
        "餐饮",
        "工资",
        "出行",
        "其他收入",
        "购物",
        "账单与费用",
        "旅行",
        "其他",
    ]

    # 原位不动的预设行仍为预设原行（无谓的 CoW 膨胀被避免）
    assert by_name["餐饮"]["is_preset"] == 1
    assert by_name["餐饮"]["id"] == food["id"]

    # 改位的预设行落到用户副本上
    assert by_name["账单与费用"]["is_preset"] == 0
    assert by_name["账单与费用"]["id"] != next(c["id"] for c in before if c["name"] == "账单与费用")
    assert by_name["工资"]["is_preset"] == 0  # 1 → 2 亦属改位（旧语义重号被归一化）
    # 「其他」是用户自有行：直接改位，不建副本
    assert by_name["其他"]["is_preset"] == 0
    assert by_name["其他"]["id"] == ids[-1]

    # 全局预设行未被写脏
    preset_row = await db_session.get(Category, food["id"])
    assert preset_row is not None
    assert preset_row.sort_order == 1
    assert preset_row.is_preset == 1

    # 另一用户看到的仍是原始预设集合与顺序
    fresh = await _visible(auth_client_b)
    assert [c["sort_order"] for c in fresh] == [1, 1, 2, 2, 3, 4, 5]
    assert [c["name"] for c in fresh] == [
        "餐饮",
        "工资",
        "出行",
        "其他收入",
        "购物",
        "旅行",
        "账单与费用",
    ]
    assert all(c["is_preset"] == 1 for c in fresh)
    assert "其他" not in [c["name"] for c in fresh]  # 属 test user 的自定义行

    # 再次重排：副本被更新而非再新建（同名列仍只有一份）
    resp = await _reorder(client, [data[1]["id"], data[0]["id"]] + [c["id"] for c in data[2:]])
    assert resp.status_code == 200
    again = await _visible(client)
    assert [c["name"] for c in again][:2] == ["工资", "餐饮"]
    assert sum(1 for c in again if c["name"] == "餐饮") == 1
    assert sum(1 for c in again if c["name"] == "工资") == 1
    assert len(again) == len(before)


@pytest.mark.asyncio
async def test_reorder_incomplete_ids_rejected(client):
    """参数非法: ids 缺一项（漏位）→ 400 PARAM_ERROR，且顺序未受影响。"""
    before = await _seed_other(client)
    ids = [c["id"] for c in before]

    resp = await _reorder(client, ids[:-2] + ids[-1:])
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "排序列表与当前分类不一致" in body["message"]

    after = await _visible(client)
    assert [c["id"] for c in after] == ids


@pytest.mark.asyncio
async def test_reorder_extra_or_duplicate_ids_rejected(client):
    """参数非法: 多项 / 重复 / 空提交 → 400。"""
    before = await _seed_other(client)
    ids = [c["id"] for c in before]

    # 含重复
    resp = await _reorder(client, ids[:-1] + [ids[0], ids[0]])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    # 多项（混入不存在的 id）
    resp = await _reorder(client, ids + [99999])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    # 空提交（可见集合非空时不可能等价）
    resp = await _reorder(client, [])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


@pytest.mark.asyncio
async def test_reorder_requires_other_category_present(client):
    """边界 8.5: 可见集合中无「其他」行 → 400（拒绝保存而非静默丢位）。"""
    resp = await _reorder(client, [c["id"] for c in await _visible(client)])
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "其他" in body["message"]


@pytest.mark.asyncio
async def test_reorder_other_user_id_rejected(auth_client_a, auth_client_b):
    """数据隔离: ids 含他人分类 id → 400，且他人顺序不被改写。"""
    await _seed_other(auth_client_a)
    resp = await auth_client_b.post("/api/categories", json={"name": "宠物"})
    assert resp.status_code == 200
    b_own = resp.json()["data"]

    a_ids = [c["id"] for c in await _visible(auth_client_a)]
    resp = await _reorder(auth_client_a, a_ids[:-1] + [b_own["id"]])
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "排序列表与当前分类不一致" in body["message"]

    # B 的行排序未被 A 改写
    b_visible = await _visible(auth_client_b)
    assert next(c for c in b_visible if c["id"] == b_own["id"])["sort_order"] == b_own["sort_order"]
    # A 的可见顺序保持不变
    assert [c["id"] for c in await _visible(auth_client_a)] == a_ids


@pytest.mark.asyncio
async def test_reorder_ignores_legacy_type_field_in_payload(client):
    """旧客户端载荷多带 `type` → pydantic 默认忽略，重排按全量集合正常执行。

    原 v1.4.2 用例 `test_m3_reorder_invalid_type_returns_422` 断言 `type` 的 Literal
    校验（非 expense/income → 422）；`CategoryReorder` 已收敛为 `{ids}`，该断言随
    字段一起废弃，本用例改为断言「type 字段不再参与校验、也不分组」。
    """
    before = await _seed_other(client)
    ids = [c["id"] for c in before]
    resp = await client.put(
        "/api/categories/reorder", json={"type": "whatever", "ids": list(reversed(ids))}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[-1]["name"] == "其他"
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))


@pytest.mark.asyncio
async def test_reorder_without_ids_returns_422(client):
    """参数非法: 缺 `ids` 必填字段 → 422（pydantic 层拦截，非业务 400）。"""
    resp = await client.put("/api/categories/reorder", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reorder_unauthenticated_returns_401(anon_client):
    """未认证: 无 token → 401。"""
    resp = await anon_client.put("/api/categories/reorder", json={"ids": [1]})
    assert resp.status_code == 401
