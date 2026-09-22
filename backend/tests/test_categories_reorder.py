"""Tests for batch category reordering (PUT /api/categories/reorder).

v1.4.3 M8：分类不再分收支两组，载荷由 `{type, ids}` 收敛为 `{ids}`（全量有序 id），
「其他」强制归一化到末位的设计不变，作用域从「组内」改「全列表」。

v1.4.3-boot2 M1（D2/D6）：置尾判据由「其他」单名放宽为**「其他家族」三名集合**，
家族整体移末尾并按固定名次排（其他支出 < 其他收入 < 其他）；「可见集合无其他行 →
ValueError」硬校验已删除（D8），防漏位由 ids 全量匹配唯一守门。

测试库预设（`conftest.PRESET_CATEGORIES`，过期 7 条副本——见 9.3a 登记）：
  餐饮1 出行2 购物3 旅行4 账单与费用5 工资1 其他收入2
  → 按 (sort_order, id) 排序的可见单列表为
    [餐饮(1), 工资(1), 出行(2), 其他收入(2), 购物(3), 旅行(4), 账单与费用(5)]
  注意三点，别把它们当成生产语义：
    * 旧语义两组的 sort_order 现在同处一列，**天然带重号**（1,1,2,2），
      重排归一化为 1..n 时必然整体后移；
    * 名为「其他」的行不存在，用例内补建（旧名「其他支出 / 其他收入」自 M1 起
      **判为家族成员**，会被名次置尾——本文件的次序断言一律按此新口径写）；
    * 夹具里的「其他收入」正处在中间位（sort 2），故它同时是「家族不在末位」的
      脏数据载体，可用来核验 D1「任何数据态拖拽都可用」。
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
    """9.2: 乱序全量 ids → 响应按提交序返回（「其他家族」除外），sort_order 归一化 1..n 连续。"""
    before = await _seed_other(client)
    assert [c["sort_order"] for c in before] == [1, 1, 2, 2, 3, 4, 5, 99]

    submitted = list(reversed(before))  # [其他, 账单与费用, 旅行, 购物, 其他收入, 出行, 工资, 餐饮]
    resp = await _reorder(client, [c["id"] for c in submitted])
    assert resp.status_code == 200
    data = resp.json()["data"]
    # M1（D6）：非家族行保持提交序；家族行（其他收入 rank1 / 其他 rank2）整体移末尾按名次排
    assert [c["name"] for c in data] == [
        "账单与费用",
        "旅行",
        "购物",
        "出行",
        "工资",
        "餐饮",
        "其他收入",
        "其他",
    ]
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))

    # 落库真值与响应一致（重新 GET）
    after = await _visible(client)
    assert [c["id"] for c in after] == [c["id"] for c in data]
    assert [c["sort_order"] for c in after] == list(range(1, len(after) + 1))


@pytest.mark.asyncio
async def test_reorder_forces_other_category_to_tail(client):
    """9.2「其他」强制置末（单名态，家族判据覆盖）：放中间提交 → 归一化到 n。

    M1（D6）：中间那行旧名家族「其他收入」同样被整体置尾，且名次恒在「其他」之前。
    """
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
        "购物",
        "旅行",
        "账单与费用",
        "其他收入",
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
    # M1（D6）：家族行「其他收入」不再停在提交序第 4 位，而是按名次置尾（第 7 位）——
    # 它因此改位（落副本），而「账单与费用」这次恰好回到自身原位数（不建副本）
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
        "购物",
        "账单与费用",
        "旅行",
        "其他收入",
        "其他",
    ]

    # 原位不动的预设行仍为预设原行（无谓的 CoW 膨胀被避免）
    assert by_name["餐饮"]["is_preset"] == 1
    assert by_name["餐饮"]["id"] == food["id"]
    assert by_name["账单与费用"]["is_preset"] == 1  # 本次目标位 = 原 5，同样不建副本
    assert by_name["账单与费用"]["id"] == next(
        c["id"] for c in before if c["name"] == "账单与费用"
    )

    # 改位的预设行落到用户副本上
    assert by_name["工资"]["is_preset"] == 0  # 1 → 2 亦属改位（旧语义重号被归一化）
    # 家族行被名次置尾而改位（2 → 7），预设旧名行同样走 CoW、全局预设不被写脏
    assert by_name["其他收入"]["is_preset"] == 0
    assert by_name["其他收入"]["id"] != next(c["id"] for c in before if c["name"] == "其他收入")
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
async def test_reorder_without_other_name_row_saves_and_normalizes_family_tail(client):
    """5.1 口径反转（附录 B / D8）：原 `test_reorder_requires_other_category_present`
    断言「可见集合缺『其他』→ 400」；该硬校验已删除，本用例改断言**正常保存**。

    夹具可见集合只有旧名家族行「其他收入」（无「其他」本名）——正是原实现死锁的形态。
    现在：可拖可保存，家族按名次置尾（家族唯一行 rank=1 即落末位），
    防漏位职责由 ids 全量匹配承接（另见 test_reorder_incomplete_ids_rejected）。
    """
    visible = await _visible(client)
    assert "其他" not in [c["name"] for c in visible]  # 无「其他」本名，只有旧名家族行
    ids = [c["id"] for c in visible]

    resp = await _reorder(client, list(reversed(ids)))
    assert resp.status_code == 200, "D8：缺「其他」本名不再被硬校验判失败"
    data = resp.json()["data"]
    names = [c["name"] for c in data]
    # 非家族行保持提交序（倒序），家族行「其他收入」整体置尾
    assert names == ["账单与费用", "旅行", "购物", "出行", "工资", "餐饮", "其他收入"]
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))
    assert (await _visible(client))[-1]["name"] == "其他收入"


@pytest.mark.asyncio
async def test_reorder_three_family_names_always_tail_in_fixed_rank(client):
    """5.2（D6）：三名家族并存（现场形态）→ 任意乱序提交，尾段恒
    ``[…, 其他支出, 其他收入, 其他]``，非家族行保持提交序。"""
    await _seed_other(client)  # 补建「其他」(sort 99)
    legacy_expense = await client.post(
        "/api/categories",
        json={"name": "其他支出", "icon": "mdi-cash-minus", "sort_order": 0},
    )
    assert legacy_expense.status_code == 200  # 4.3：显式建旧名 → 允许创建

    before = await _visible(client)
    by_name = {c["name"]: c["id"] for c in before}
    assert {"其他", "其他支出", "其他收入"} <= set(by_name)  # 三名齐全
    assert before[-1]["name"] == "其他"  # 「其他支出」(0) 与「其他收入」(2) 压在中间

    # 家族行拆散到列表各处提交：名次必须压过提交序
    shuffled = ["其他", "餐饮", "其他支出", "工资", "其他收入", "旅行", "出行", "购物", "账单与费用"]
    resp = await _reorder(client, [by_name[name] for name in shuffled])
    assert resp.status_code == 200
    data = resp.json()["data"]
    names = [c["name"] for c in data]
    assert names[-3:] == ["其他支出", "其他收入", "其他"]
    assert names[:-3] == ["餐饮", "工资", "旅行", "出行", "购物", "账单与费用"]
    assert [c["sort_order"] for c in data] == list(range(1, len(data) + 1))

    stored = await _visible(client)
    assert [c["name"] for c in stored] == names  # 落库真值与响应逐位一致（无二次跳变）


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


# ── v1.4.3-boot2 M1：`_next_sort_order` 家族钳制 + 家族常量一致性 ──────────────


async def _drop_family_rows(db_session) -> None:
    """删掉夹具里的家族行（测试内存库，**不碰真实库**），构造「可见集合无家族行」态。"""
    from sqlmodel import select

    from app.models.category import Category
    from app.services.category_service import LEGACY_OTHER_NAMES, OTHER_CATEGORY_NAME

    family_names = [OTHER_CATEGORY_NAME, *LEGACY_OTHER_NAMES]
    rows = (
        await db_session.exec(select(Category).where(Category.name.in_(family_names)))
    ).all()
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_next_sort_order_with_legacy_names_clamps_before_family(client):
    """5.3 态①：有旧名家族行、无「其他」本名 → 新行钳到**家族最小 sort** 之前。

    夹具态：非家族行最大 sort = 5、家族只有「其他收入」(2) → 结果取 min(6, 1) = 1；
    原实现（单名判据）会直接 max+1 落末位，把新行甩到家族行之后。
    """
    visible = await _visible(client)
    assert "其他收入" in [c["name"] for c in visible]
    assert "其他" not in [c["name"] for c in visible]

    resp = await client.post("/api/categories", json={"name": "宠物"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 1

    names = [c["name"] for c in await _visible(client)]
    assert names.index("宠物") < names.index("其他收入")  # 恒落在所有家族行之前


@pytest.mark.asyncio
async def test_next_sort_order_with_full_family_appends_before_family_block(client):
    """5.3 态②：三名齐全且家族已在尾（reorder 归一后）→ 新行追加到家族块之前。"""
    await _seed_other(client)
    legacy = await client.post(
        "/api/categories",
        json={"name": "其他支出", "icon": "mdi-cash-minus", "sort_order": 98},
    )
    assert legacy.status_code == 200
    before = await _visible(client)
    resp = await _reorder(client, [c["id"] for c in before])
    assert resp.status_code == 200
    tail = [c["name"] for c in resp.json()["data"]]
    assert tail[-3:] == ["其他支出", "其他收入", "其他"]  # 家族块 7/8/9

    created = await client.post("/api/categories", json={"name": "宠物"})
    assert created.status_code == 200
    # base = max(非家族) = 6，家族最小 sort = 7 → min(7, 6) = 6：与末位非家族行同值，
    # 按 (sort_order, id) 自然排在其后、家族块之前
    assert created.json()["data"]["sort_order"] == 6
    names = [c["name"] for c in await _visible(client)]
    assert names.index("宠物") < names.index("其他支出")


@pytest.mark.asyncio
async def test_next_sort_order_without_family_appends_at_tail(client, db_session):
    """5.3 态③：可见集合无家族行 → 直接 max+1 追加末位（原行为保持）。"""
    await _drop_family_rows(db_session)
    resp = await client.post("/api/categories", json={"name": "宠物"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 6
    assert (await _visible(client))[-1]["name"] == "宠物"


@pytest.mark.asyncio
async def test_next_sort_order_negative_result_is_clamped_to_zero_and_self_heals(client):
    """5.3 下钳：家族行 sort=0（导入建的散行）→ min-1 = -1 必须钳到 0，不落负值。

    §1.2.1-2 已知边界的处置：钳 0 与导入建的 sort=0 行同区，由下一次成功 reorder
    整体归一 1..n 自愈——本用例把「不残留 0 位」一并钉住。
    """
    other = await client.post(
        "/api/categories", json={"name": "其他", "icon": "mdi-cash-minus", "sort_order": 0}
    )
    assert other.status_code == 200

    resp = await client.post("/api/categories", json={"name": "宠物"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 0  # 未钳则得 -1

    dirty = await _visible(client)
    assert 0 in [c["sort_order"] for c in dirty]
    done = await _reorder(client, [c["id"] for c in dirty])
    assert done.status_code == 200
    assert [c["sort_order"] for c in done.json()["data"]] == list(range(1, len(dirty) + 1))


def test_other_family_rank_is_the_single_source_of_truth():
    """5.4（D6）：服务侧名次表自洽——三名 = 本名 + 两旧名、名次固定 0/1/2、「其他」恒最大。"""
    from app.services import category_service

    assert set(category_service.OTHER_FAMILY_RANK) == {
        category_service.OTHER_CATEGORY_NAME,
        *category_service.LEGACY_OTHER_NAMES,
    }
    assert category_service.OTHER_FAMILY_RANK == {"其他支出": 0, "其他收入": 1, "其他": 2}
    assert category_service.OTHER_FAMILY_RANK[category_service.OTHER_CATEGORY_NAME] == max(
        category_service.OTHER_FAMILY_RANK.values()
    )
    # 家族判据（含旧名）与非家族名
    assert category_service._is_other_row("其他") is True
    assert category_service._is_other_row("其他支出") is True
    assert category_service._is_other_row("其他收入") is True
    assert category_service._is_other_row("餐饮") is False


def test_other_family_rank_matches_m2_script_constants():
    """5.4：家族常量与 M2 脚本侧一致性（防两侧漂移）。

    任务指定的占位手法 `pytest.importorskip("migrate_to_v1.4.3boot2_categories")`
    实测**不可用**：脚本文件名含点号，import 机制把 dots 当包分隔符 → 抛 SyntaxError
    而非 ImportError，起不到 skip 作用。故按等价手法实现「文件不存在即 skip」的占位，
    M2 落文件后本用例自动转实断言（加载方式沿 `test_migration_v143.py` 的按路径加载）。
    """
    import importlib.util
    from pathlib import Path

    from app.services import category_service

    script_path = (
        Path(__file__).resolve().parents[1] / "migrate_to_v1.4.3boot2_categories.py"
    )
    if not script_path.exists():
        pytest.skip("M2 脚本 migrate_to_v1.4.3boot2_categories.py 尚未落文件（M1 先行占位）")

    spec = importlib.util.spec_from_file_location("migrate_to_v1_4_3_boot2_categories", script_path)
    assert spec and spec.loader
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    assert set(category_service.OTHER_FAMILY_RANK) == {
        script.OTHER_CATEGORY_NAME,
        *script.LEGACY_OTHER_NAMES,
    }
    assert category_service.OTHER_CATEGORY_NAME == script.OTHER_CATEGORY_NAME


@pytest.mark.asyncio
async def test_rename_legacy_family_rows_allowed_but_other_name_stays_locked(client):
    """2.5：禁改名判据**收窄回「其他」本名**——旧名两行允许改名（改出家族即普通行）。"""
    await _seed_other(client)
    legacy = await client.post(
        "/api/categories", json={"name": "其他支出", "icon": "mdi-cash-minus"}
    )
    assert legacy.status_code == 200
    legacy_id = legacy.json()["data"]["id"]

    renamed = await client.put(f"/api/categories/{legacy_id}", json={"name": "备用金"})
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "备用金"

    other_id = next(c["id"] for c in await _visible(client) if c["name"] == "其他")
    blocked = await client.put(f"/api/categories/{other_id}", json={"name": "杂项"})
    assert blocked.status_code == 400
    assert "其他" in blocked.json()["message"]


@pytest.mark.asyncio
async def test_reorder_owned_preset_flagged_row_updates_in_place(client, db_session):
    """回归（现场拖拽「有时候保存失败」根因）：历史「is_preset=1 且 user_id 非空」的
    用户自有形制行，重排时必须**就地改 sort_order**，不得走 CoW。

    旧实现 ``_set_sort_order`` 以 ``is_preset == 0`` 判「用户自有行」，把这类行误当全局
    预设 → 进 CoW 分支 → ``INSERT`` 一条同 ``(name, user_id)`` 的副本 → 撞
    ``UNIQUE(name,user_id)`` → IntegrityError → 500（前端表现为「排序保存失败」，
    因仅当该行被移动出原位才触发，故呈间歇性）。
    """
    from sqlalchemy import select

    from app.models.category import Category
    from app.models.user import User

    # 列投影取 id（本仓 exec(select(Model)).one() 返回 Row，非实体——沿用既有手法）
    uid = (await db_session.exec(select(User.id).where(User.username == "clientuser"))).one()[0]
    db_session.add(
        Category(
            name="历史形制分类",
            type="expense",
            icon="mdi-bag-suitcase",
            sort_order=999,
            is_preset=1,  # 关键：is_preset=1 但归属该用户（现场/迁移遗留形制）
            user_id=uid,
        )
    )
    await db_session.commit()

    visible = await _visible(client)
    mine = next((c["id"] for c in visible if c["name"] == "历史形制分类"), None)
    assert mine is not None, "owned is_preset=1 行应进入可见集"

    rest = [c["id"] for c in visible if c["id"] != mine]
    moved = [mine] + rest  # 从末位移到最前（改变 sort_order → 旧实现会触发 CoW 撞约束）
    resp = await _reorder(client, moved)
    assert resp.status_code == 200, f"重排自有 is_preset=1 行不应 500：{resp.status_code} {resp.text[:200]}"

    after = await _visible(client)
    assert sum(1 for c in after if c["name"] == "历史形制分类") == 1, "不得因 CoW 产生重复 (name,user_id) 行"
    assert after[0]["name"] == "历史形制分类"  # 非家族 → 提到首位
