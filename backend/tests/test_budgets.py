"""预算接口测试（v1.4.3 M12：某自然月下的多条命名预算）.

覆盖任务书 §11.1 + prompt §7.1「接口四件套」（每个新增/变更端点各一套）：
  ① 正常路径；② 空数据 / 参数非法；③ 数据隔离；④ 401 未认证。

另含**分类删除的预算级联**（任务 4.1–4.4 / 边界 10.1）——变更端点
``DELETE /api/categories/{id}`` 与 ``POST /api/categories/restore-defaults``
的预算侧行为归本模块（分类侧其余断言见 test_categories.py）。

⚠ 口径反转（相对 M8 旧模型，逐条登记旧用例的去向）：
  - ``POST /api/budgets`` 由 **upsert** 改**纯创建**：旧 ``test_create_budget_upsert``
    （同 category+month 二次 POST 改金额）→ ``test_post_is_pure_create_not_upsert``，
    同 payload 两次 POST 得两条独立预算。
  - ``GET /api/budgets`` 去掉 ``type`` 参数：旧 ``test_get_budgets`` 的
    「按 type 过滤得 1 条」断言 → ``test_list_budgets_ignores_type_param``
    （type 传入被忽略、返回该月全部）。
  - ``POST /api/budgets/batch`` **已下线**（任务 2.5）：旧 ``test_batch_set_budgets``
    移除 → 编辑链路由 ``test_update_budget_all_fields`` 以单条全字段 PUT 覆盖
    （口径反转：批量 upsert → 单条全字段编辑）；端点本身由
    ``test_batch_endpoint_removed`` 锁 404/405。
  - 预算不再挂单分类：旧 payload ``{category_id, month, amount}`` 全部作废，
    新契约 ``{month, name, amount, scope_mode, category_ids}``（任务 2.2）；
    旧 ``test_create_budget`` / ``test_update_budget`` / ``test_delete_budget`` /
    ``test_delete_nonexistent_budget`` 相应改写为新 payload 版本。
  - 年汇总逐月 total = **Σ 各预算**（决策 D4，范围重叠时重复计入）：旧
    ``test_year_summary_fixed_12_ordered_months``（按 category_id 升序）→
    ``test_year_summary_totals_are_budget_sum``（按 id/创建序 + 重叠 Σ）；
    ``test_year_summary_totals_and_spent_match_monthly_api`` →
    ``test_year_summary_spent_uses_own_month``；隔离/401/参数校验三件保留原口径。
  - 旧 ``income_category_id`` fixture（直改 Category.type 造 income 行）随
    ``budget_service`` 的 type 过滤一并移除——预算的收支口径改由 spent 聚合定义。
"""

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget, BudgetCategory

MONTH = "2026-06"

# BudgetDetail 契约（任务 2.7）——前端渲染所需字段清单，多给/少给都算回归
BUDGET_DETAIL_KEYS = {
    "id",
    "month",
    "name",
    "amount",
    "spent",
    "remaining",
    "percentage",
    "scope_mode",
    "category_ids",
    "category_names",
    "details",
    "created_at",
    "updated_at",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def make_category(client, name: str) -> int:
    """建自建分类并返回 id（M8 起 POST 不收 type）."""
    resp = await client.post(
        "/api/categories", json={"name": name, "icon": "mdi-food-test"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


async def category_order(client) -> list[int]:
    """该用户可见分类的呈现顺序（sort_order, id）——category_ids/details 排序基准."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    return [c["id"] for c in resp.json()["data"]]


async def preset_category_id(client, name: str) -> int:
    """预设分类 id（user_id IS NULL、全用户共用同一行）."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    for cat in resp.json()["data"]:
        if cat["name"] == name and cat.get("is_preset") == 1:
            return int(cat["id"])
    raise AssertionError(f"预设分类缺失：{name}")


async def make_expense(client, amount: float, category_id: int, day: int = 15) -> None:
    resp = await client.post(
        "/api/records",
        json={
            "amount": amount,
            "type": "expense",
            "category_id": category_id,
            "consume_time": f"{MONTH}-{day:02d} 12:00",
        },
    )
    assert resp.status_code == 200, resp.text


async def make_income(client, amount: float, category_id: int, day: int = 15) -> None:
    resp = await client.post(
        "/api/records",
        json={
            "amount": amount,
            "type": "income",
            "category_id": category_id,
            "consume_time": f"{MONTH}-{day:02d} 12:00",
        },
    )
    assert resp.status_code == 200, resp.text


async def post_budget(client, **overrides):
    """按新契约 POST 一条预算（默认 include，需显式给 category_ids 才合法）."""
    payload = {
        "month": MONTH,
        "name": "日常开销",
        "amount": 3000.0,
        "scope_mode": "include",
        "category_ids": [],
    }
    payload.update(overrides)
    return await client.post("/api/budgets", json=payload)


async def link_ids(db_session: AsyncSession, budget_id: int) -> list[int]:
    """直读关联表（验证去重/级联/显式删除，不走接口）."""
    rows = (
        await db_session.exec(
            select(BudgetCategory.category_id)
            .where(BudgetCategory.budget_id == budget_id)
            .order_by(BudgetCategory.id)
        )
    ).all()
    return [int(r) for r in rows]


# ===========================================================================
# 四件套 ① 正常路径
# ===========================================================================


@pytest.mark.asyncio
async def test_create_budget_returns_full_detail(client):
    """①POST 正常路径：BudgetDetail 字段契约精确（任务 2.7）."""
    food = await make_category(client, "M12餐饮")
    shop = await make_category(client, "M12购物")

    resp = await post_budget(client, category_ids=[food, shop])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == 0
    assert data["message"] == "预算创建成功"
    b = data["data"]
    assert set(b) == BUDGET_DETAIL_KEYS
    assert b["name"] == "日常开销"
    assert b["month"] == MONTH
    assert b["amount"] == 3000.0
    assert b["scope_mode"] == "include"
    assert b["spent"] == 0
    assert b["remaining"] == 3000.0
    assert b["percentage"] == 0

    order = await category_order(client)
    expected = [i for i in order if i in {food, shop}]
    assert b["category_ids"] == expected
    assert b["category_names"] == ["M12餐饮", "M12购物"]
    # include：选中类逐一列出，0 花费显示 0（任务 3.3）
    assert [d["category_id"] for d in b["details"]] == expected
    assert {d["spent"] for d in b["details"]} == {0}
    assert set(b["details"][0]) == {"category_id", "category_name", "icon", "spent"}
    assert b["details"][0]["icon"] == "mdi-food-test"


@pytest.mark.asyncio
async def test_multiple_budgets_in_one_month(client):
    """①同月多条 + 同月同名多条（任务 1.1「name 同月不强制唯一」）；GET 按 id 升序."""
    a = await make_category(client, "M12A")
    b = await make_category(client, "M12B")

    r1 = await post_budget(client, name="日常开销", amount=3000.0, category_ids=[a])
    r2 = await post_budget(client, name="学习", amount=500.0, category_ids=[b])
    r3 = await post_budget(client, name="日常开销", amount=800.0, category_ids=[a])
    ids = [r.json()["data"]["id"] for r in (r1, r2, r3)]
    assert len(set(ids)) == 3, ids

    resp = await client.get("/api/budgets", params={"month": MONTH})
    assert resp.status_code == 200
    listed = resp.json()["data"]
    assert [x["id"] for x in listed] == sorted(ids)  # 创建序 = id 升序
    assert [x["name"] for x in listed] == ["日常开销", "学习", "日常开销"]
    assert [x["amount"] for x in listed] == [3000.0, 500.0, 800.0]


@pytest.mark.asyncio
async def test_post_is_pure_create_not_upsert(client):
    """①POST 非 upsert（口径反转：旧 test_create_budget_upsert）."""
    a = await make_category(client, "M12重复")
    payload = {"month": MONTH, "name": "同一条", "amount": 1000.0, "category_ids": [a]}

    r1 = await client.post("/api/budgets", json=payload)
    r2 = await client.post("/api/budgets", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["data"]["id"] != r2.json()["data"]["id"]
    assert r2.json()["data"]["amount"] == 1000.0  # 未被「更新」，而是新增一行

    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert len(listed) == 2


@pytest.mark.asyncio
async def test_include_spent_math(client):
    """①include：spent = Σ 选中类（4 分类流水精确核对，任务 3.2/3.6）."""
    food = await make_category(client, "M12I餐饮")
    shop = await make_category(client, "M12I购物")
    trans = await make_category(client, "M12I交通")
    fun = await make_category(client, "M12I娱乐")
    await make_expense(client, 100.50, food)
    await make_expense(client, 200.25, shop)
    await make_expense(client, 50.00, trans)
    await make_expense(client, 999.99, fun)
    await make_income(client, 5000.00, food)  # 收入不得进 spent

    resp = await post_budget(
        client, name="吃饭购物", amount=800.0, category_ids=[food, shop]
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()["data"]
    assert b["spent"] == 300.75
    assert b["remaining"] == 499.25
    assert b["percentage"] == 37.6
    detail_ids = {d["category_id"] for d in b["details"]}
    assert detail_ids == {food, shop}
    assert sorted(d["spent"] for d in b["details"]) == [100.5, 200.25]
    # 未选中的分类不进本预算明细
    assert trans not in detail_ids and fun not in detail_ids


@pytest.mark.asyncio
async def test_exclude_spent_math(client):
    """①exclude：spent = 当月全部支出 − Σ 排除类；details 只列计入且有花费的类（3.2/3.3）."""
    food = await make_category(client, "M12E餐饮")
    shop = await make_category(client, "M12E购物")
    trans = await make_category(client, "M12E交通")
    await make_expense(client, 100.50, food)
    await make_expense(client, 200.25, shop)
    await make_expense(client, 50.00, trans)
    await make_income(client, 7000.00, shop)  # 月总额只算支出

    resp = await post_budget(
        client,
        name="除餐饮购物外",
        amount=1000.0,
        scope_mode="exclude",
        category_ids=[food, shop],
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()["data"]
    assert b["spent"] == 50.0
    assert b["remaining"] == 950.0
    assert b["percentage"] == 5.0
    # 排除类即便有花费也不进 details；零花费的计入类也不列（任务 3.3）
    assert [d["category_id"] for d in b["details"]] == [trans]
    assert b["details"][0]["category_name"] == "M12E交通"
    order = await category_order(client)
    assert b["category_ids"] == [i for i in order if i in {food, shop}]


@pytest.mark.asyncio
async def test_exclude_without_category_is_full_amount(client):
    """①exclude + 空分类集 = 全额；零支出时 spent/percentage 均为 0（边界 10.2）."""
    resp = await post_budget(client, name="全支出", scope_mode="exclude")
    assert resp.status_code == 200, resp.text
    empty = resp.json()["data"]
    assert empty["spent"] == 0
    assert empty["percentage"] == 0
    assert empty["details"] == []

    food = await make_category(client, "M12F餐饮")
    await make_expense(client, 123.45, food)
    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert listed[0]["spent"] == 123.45, "exclude 空集应覆盖当月全部支出"


@pytest.mark.asyncio
async def test_migrated_orphan_budget_is_read_only(client, db_session):
    """①任务 9.3 迁移产出的只读态：名称「未知分类」+ include + 分类置空.

    口径登记：该形态**展示/删除正常、spent 恒 0**，仅 PUT 重保存被 include ≥1
    校验拦截（引导补选分类）——这是设计裁定，不是缺陷。
    造形方式：先 POST 真预算，再按阶段 B 的产出改写名称并清空关联行。
    """
    food = await make_category(client, "M12O餐饮")
    resp = await post_budget(client, name="M12O原", amount=500.0, category_ids=[food])
    assert resp.status_code == 200, resp.text
    bid = resp.json()["data"]["id"]

    budget = (
        await db_session.exec(select(Budget).where(Budget.id == bid))
    ).first()
    assert budget is not None
    budget.name = "未知分类"
    db_session.add(budget)
    for link in (
        await db_session.exec(
            select(BudgetCategory).where(BudgetCategory.budget_id == bid)
        )
    ).all():
        await db_session.delete(link)
    await db_session.commit()

    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert len(listed) == 1
    orphan = listed[0]
    assert orphan["name"] == "未知分类"
    assert orphan["scope_mode"] == "include"
    assert orphan["category_ids"] == []
    assert orphan["category_names"] == []
    assert orphan["details"] == []
    assert orphan["spent"] == 0, "只读态无分类可计，spent 恒 0"
    assert orphan["remaining"] == 500.0
    assert orphan["percentage"] == 0

    # 仅 PUT 被 include ≥1 拦下（400 + PARAM_ERROR），且不改数据
    resp = await client.put(
        f"/api/budgets/{bid}",
        json={"name": "未知分类", "amount": 600.0, "scope_mode": "include", "category_ids": []},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001
    assert "包含模式" in resp.json()["message"]
    still = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"][0]
    assert still["amount"] == 500.0

    # 可删（用户摆脱只读态的唯一出口）
    resp = await client.delete(f"/api/budgets/{bid}")
    assert resp.status_code == 200
    assert (await client.get("/api/budgets", params={"month": MONTH})).json()["data"] == []


@pytest.mark.asyncio
async def test_update_budget_all_fields(client):
    """①PUT 全字段编辑；month 传入被忽略（任务 2.3，替代旧 batch 的编辑链路）."""
    a = await make_category(client, "M12P原")
    b = await make_category(client, "M12P新")
    await make_expense(client, 100.0, a)
    await make_expense(client, 300.0, b)

    budget_id = (await post_budget(client, category_ids=[a])).json()["data"]["id"]

    resp = await client.put(
        f"/api/budgets/{budget_id}",
        json={
            "month": "2026-01",  # 不可改，须被忽略
            "name": "改名后",
            "amount": 1234.5,
            "scope_mode": "exclude",
            "category_ids": [b],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["message"] == "预算更新成功"
    edited = data["data"]
    assert set(edited) == BUDGET_DETAIL_KEYS
    assert edited["month"] == MONTH, "PUT 不得改月份"
    assert edited["name"] == "改名后"
    assert edited["amount"] == 1234.5
    assert edited["scope_mode"] == "exclude"
    assert edited["category_ids"] == [b]
    assert edited["spent"] == 100.0  # 排除 b → 只剩 a 的 100

    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in listed] == [budget_id]
    moved = (await client.get("/api/budgets", params={"month": "2026-01"})).json()["data"]
    assert moved == []


@pytest.mark.asyncio
async def test_update_budget_replaces_links_without_unique_clash(client, db_session):
    """①PUT 重写关联分类：保留项不得撞 UNIQUE(budget_id, category_id).

    回归锁：SQLAlchemy unit-of-work 在同一次 flush 里**先插后删**，
    故 ``_replace_budget_categories`` 必须在插前显式 flush DELETE。
    """
    a = await make_category(client, "M12L保留")
    b = await make_category(client, "M12L让位")
    c = await make_category(client, "M12L新增")
    budget_id = (await post_budget(client, category_ids=[a, b])).json()["data"]["id"]
    assert set(await link_ids(db_session, budget_id)) == {a, b}

    for ids in ([a, c], [a, c]):  # 第二次为幂等重写
        resp = await client.put(
            f"/api/budgets/{budget_id}",
            json={"name": "换范围", "amount": 900.0, "category_ids": ids},
        )
        assert resp.status_code == 200, resp.text
        assert sorted(await link_ids(db_session, budget_id)) == sorted(ids)


@pytest.mark.asyncio
async def test_delete_budget(client, db_session):
    """①DELETE 正常路径 + 关联行同步清空（显式级联，连接未开 foreign_keys）."""
    a = await make_category(client, "M12D餐饮")
    budget_id = (await post_budget(client, category_ids=[a])).json()["data"]["id"]

    resp = await client.delete(f"/api/budgets/{budget_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "预算删除成功"

    assert (await client.get("/api/budgets", params={"month": MONTH})).json()["data"] == []
    assert await db_session.get(Budget, budget_id) is None
    assert await link_ids(db_session, budget_id) == []


@pytest.mark.asyncio
async def test_year_summary_totals_are_budget_sum(client):
    """①年汇总：逐月 total = Σ 各预算，分类重叠重复计入（决策 D4，任务 2.6/边界 10.5）."""
    food = await make_category(client, "M12Y餐饮")
    shop = await make_category(client, "M12Y购物")
    for month in ("2026-01", "2026-02"):
        resp = await client.post(
            "/api/records",
            json={
                "amount": 400.0,
                "type": "expense",
                "category_id": food,
                "consume_time": f"{month}-10 12:00",
            },
        )
        assert resp.status_code == 200

    # 1 月两条：范围重叠（都含 food）→ 同一笔支出在 Σ 里算两次（已裁定的 D4 口径）
    for name, amount, ids in (("重叠A", 1000.0, [food]), ("重叠B", 500.0, [food, shop])):
        resp = await client.post(
            "/api/budgets",
            json={
                "month": "2026-01",
                "name": name,
                "amount": amount,
                "category_ids": ids,
            },
        )
        assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/api/budgets",
        json={
            "month": "2026-02",
            "name": "二月",
            "amount": 300.0,
            "category_ids": [food],
        },
    )
    assert resp.status_code == 200
    # 邻年不参与
    await client.post(
        "/api/budgets",
        json={
            "month": "2025-12",
            "name": "去年",
            "amount": 9999.0,
            "category_ids": [food],
        },
    )

    resp = await client.get("/api/budgets/year-summary", params={"year": 2026})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["year"] == 2026
    months = data["months"]
    assert len(months) == 12
    assert [m["month"] for m in months] == [f"2026-{i:02d}" for i in range(1, 13)]
    assert all(set(m) == {"month", "total_amount", "total_spent", "budgets"} for m in months)

    jan, feb = months[0], months[1]
    assert jan["total_amount"] == 1500.0
    assert jan["total_spent"] == 800.0
    assert jan["total_amount"] == sum(b["amount"] for b in jan["budgets"])
    assert jan["total_spent"] == sum(b["spent"] for b in jan["budgets"])
    assert [b["name"] for b in jan["budgets"]] == ["重叠A", "重叠B"]  # id 升序 = 创建序
    assert all(set(b) == BUDGET_DETAIL_KEYS for b in jan["budgets"])
    assert all(b["month"] == "2026-01" for b in jan["budgets"])
    assert feb["total_amount"] == 300.0
    assert feb["total_spent"] == 400.0
    assert months[2]["budgets"] == []
    assert months[2]["total_amount"] == 0
    assert months[2]["total_spent"] == 0


@pytest.mark.asyncio
async def test_year_summary_spent_uses_own_month(client):
    """①年汇总的 spent 按各预算自身月份（M6 易错点 7 的回归，模型改后仍成立）."""
    a = await make_category(client, "M12M餐饮")
    for month, amount in (("2026-03", 111.0), ("2026-04", 222.0)):
        resp = await client.post(
            "/api/records",
            json={
                "amount": amount,
                "type": "expense",
                "category_id": a,
                "consume_time": f"{month}-05 12:00",
            },
        )
        assert resp.status_code == 200
        resp = await client.post(
            "/api/budgets",
            json={
                "month": month,
                "name": f"{month} 预算",
                "amount": 1000.0,
                "category_ids": [a],
            },
        )
        assert resp.status_code == 200

    resp = await client.get("/api/budgets/year-summary", params={"year": 2026})
    months = {m["month"]: m for m in resp.json()["data"]["months"]}
    assert months["2026-03"]["total_spent"] == 111.0
    assert months["2026-04"]["total_spent"] == 222.0
    # 与按月接口逐条一致
    monthly = (await client.get("/api/budgets", params={"month": "2026-03"})).json()["data"]
    assert monthly[0]["spent"] == months["2026-03"]["budgets"][0]["spent"]
    assert monthly[0]["amount"] == months["2026-03"]["budgets"][0]["amount"]


@pytest.mark.asyncio
async def test_budget_overview_shape_kept(client):
    """①统计页 budget-overview：单分类 include 预算下输出与 v1.4.2 一致（附带适配）."""
    a = await make_category(client, "M12O餐饮")
    await make_expense(client, 500.0, a)
    assert (await post_budget(client, amount=2000.0, category_ids=[a])).status_code == 200

    resp = await client.get("/api/statistics/budget-overview", params={"month": MONTH})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["month"] == MONTH
    assert data["total_budget"] == 2000.0
    assert data["total_spent"] == 500.0
    assert len(data["categories"]) == 1
    entry = data["categories"][0]
    assert entry["category_id"] == a
    assert entry["budget"] == 2000.0
    assert entry["percentage"] == 25.0
    assert entry["status"] == "normal"
    # M12 新增的归属字段（一条预算可覆盖多分类，故须标明来自哪张卡）
    assert entry["budget_name"] == "日常开销"


@pytest.mark.asyncio
async def test_budget_overview_warning_and_exceeded(client):
    """①预警/超额口径与 remaining/percentage 沿用现规则（任务 3.4）."""
    a = await make_category(client, "M12W餐饮")
    await make_expense(client, 900.0, a)
    assert (await post_budget(client, amount=1000.0, category_ids=[a])).status_code == 200
    resp = await client.get("/api/statistics/budget-overview", params={"month": MONTH})
    assert resp.json()["data"]["categories"][0]["status"] == "warning"

    b = await make_category(client, "M12X餐饮")
    await make_expense(client, 2500.0, b)
    resp = await post_budget(client, name="超支", amount=2000.0, category_ids=[b])
    assert resp.json()["data"]["remaining"] == 0  # max(amt-spent, 0)
    assert resp.json()["data"]["percentage"] == 125.0
    resp = await client.get("/api/statistics/budget-overview", params={"month": MONTH})
    data = resp.json()["data"]
    assert data["total_budget"] == 3000.0
    assert data["total_spent"] == 3400.0
    assert data["overall_percentage"] == 113.3
    assert {c["status"] for c in data["categories"]} == {"warning", "exceeded"}


@pytest.mark.asyncio
async def test_budget_overview_empty_month(client):
    """①统计页 overview 空月：全 0、空明细，不报错."""
    resp = await client.get("/api/statistics/budget-overview", params={"month": MONTH})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_budget"] == 0
    assert data["total_spent"] == 0
    assert data["categories"] == []


# ===========================================================================
# 四件套 ② 空数据 / 参数非法
# ===========================================================================


@pytest.mark.asyncio
async def test_list_budgets_empty_month(client):
    """②空数据：该月无预算 → 空数组."""
    resp = await client.get("/api/budgets", params={"month": "2026-09"})
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_list_budgets_ignores_type_param(client):
    """②/① 旧 type 过滤参数已废弃（任务 2.1）：传入被忽略，返回该月全部."""
    a = await make_category(client, "M12T餐饮")
    assert (await post_budget(client, category_ids=[a])).status_code == 200
    resp = await client.get("/api/budgets", params={"month": MONTH, "type": "income"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_year_summary_empty_year(client):
    """②空数据：整年无预算 → 12 个空月份，不报错."""
    resp = await client.get("/api/budgets/year-summary", params={"year": 2031})
    assert resp.status_code == 200
    months = resp.json()["data"]["months"]
    assert [m["month"] for m in months] == [f"2031-{i:02d}" for i in range(1, 13)]
    assert all(m["budgets"] == [] and m["total_amount"] == 0 for m in months)


@pytest.mark.asyncio
async def test_year_summary_param_validation(client):
    """②year 缺失 / 非数字 / 越界 → 422."""
    for url in (
        "/api/budgets/year-summary",
        "/api/budgets/year-summary?year=abc",
        "/api/budgets/year-summary?year=1999",
        "/api/budgets/year-summary?year=2101",
    ):
        resp = await client.get(url)
        assert resp.status_code == 422, url


@pytest.mark.asyncio
async def test_month_param_validation(client):
    """②month 非法格式 → 422（GET 与 POST 同一 pattern）；缺必填 → 422."""
    assert (await client.get("/api/budgets", params={"month": "2026-6"})).status_code == 422
    assert (await client.get("/api/budgets")).status_code == 422
    resp = await post_budget(client, month="2026-6", category_ids=[1])
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_impossible_month_is_param_error_not_500(client):
    """②2026-13 过得了 pattern、过不了月历 → PARAM_ERROR（服务层兜底，GET 也不再 500）."""
    resp = await post_budget(client, month="2026-13", category_ids=[1])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    resp = await client.get("/api/budgets", params={"month": "2026-13"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


@pytest.mark.asyncio
async def test_name_validation(client):
    """②缺 name / 空 name / 超长 → 422；纯空白 → 40001（服务层 strip 后为空）."""
    resp = await client.post(
        "/api/budgets", json={"month": MONTH, "amount": 100.0, "category_ids": []}
    )
    assert resp.status_code == 422

    for bad in ("", "x" * 51):
        resp = await post_budget(client, name=bad, category_ids=[])
        assert resp.status_code == 422, bad

    resp = await post_budget(client, name="   ")
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001
    assert "预算名称" in resp.json()["message"]


@pytest.mark.asyncio
async def test_amount_validation(client):
    """②amount 缺失 / ≤ 0 / 越界 → 422（pydantic）."""
    for bad in (0, -1, None, 1e9):
        payload = {"month": MONTH, "name": "金额", "category_ids": []}
        if bad is not None:
            payload["amount"] = bad
        resp = await client.post("/api/budgets", json=payload)
        assert resp.status_code == 422, bad


@pytest.mark.asyncio
async def test_include_needs_at_least_one_category(client):
    """②include + 空分类集 → PARAM_ERROR（任务 1.3 的服务层权威校验）."""
    resp = await post_budget(client, category_ids=[])
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "包含模式" in body["message"]

    resp = await client.post(
        "/api/budgets", json={"month": MONTH, "name": "无范围", "amount": 100.0}
    )
    assert resp.status_code == 400, "category_ids 缺省即空列表，include 仍须 ≥1"


@pytest.mark.asyncio
async def test_scope_mode_validation(client):
    """②scope_mode 非法值 → 422（Literal）；PUT 同口径."""
    for bad in ("both", "", "INCLUDE"):
        resp = await post_budget(client, scope_mode=bad, category_ids=[1])
        assert resp.status_code == 422, bad

    a = await make_category(client, "M12S餐饮")
    budget_id = (await post_budget(client, category_ids=[a])).json()["data"]["id"]
    resp = await client.put(
        f"/api/budgets/{budget_id}",
        json={"name": "改", "amount": 100.0, "scope_mode": "everything", "category_ids": [a]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_category_rejected(client):
    """②引用不存在的分类 → PARAM_ERROR 且不留半成品预算、不破坏原关联."""
    resp = await post_budget(client, category_ids=[999999])
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001
    assert "分类不存在" in resp.json()["message"]
    assert (await client.get("/api/budgets", params={"month": MONTH})).json()["data"] == []

    a = await make_category(client, "M12C餐饮")
    budget_id = (await post_budget(client, category_ids=[a])).json()["data"]["id"]
    resp = await client.put(
        f"/api/budgets/{budget_id}",
        json={"name": "坏分类", "amount": 100.0, "category_ids": [999999]},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001
    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert listed[0]["category_ids"] == [a]  # 原关联未被破坏


@pytest.mark.asyncio
async def test_duplicate_category_ids_deduped(client, db_session):
    """②category_ids 重复 → 去重后入库，关联行不重复（不撞 UNIQUE）."""
    a = await make_category(client, "M12Q餐饮")
    resp = await post_budget(client, category_ids=[a, a, a])
    assert resp.status_code == 200, resp.text
    budget_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["category_ids"] == [a]
    assert await link_ids(db_session, budget_id) == [a]


@pytest.mark.asyncio
async def test_missing_budget_returns_not_found(client):
    """②不存在 id 的 PUT / DELETE → code 40002（响应口径未变）."""
    body = {"name": "不存在", "amount": 100.0, "category_ids": []}
    resp = await client.put("/api/budgets/999999", json=body)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    resp = await client.delete("/api/budgets/999999")
    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    resp = await client.delete("/api/budgets/abc")
    assert resp.status_code == 422  # 路径参数非整数


@pytest.mark.asyncio
async def test_batch_endpoint_removed(client, anon_client):
    """②POST /budgets/batch 已下线（任务 2.5）→ 404/405，不静默成功."""
    payload = {"month": MONTH, "budgets": [{"category_id": 1, "amount": 100.0}]}
    for c in (client, anon_client):
        resp = await c.post("/api/budgets/batch", json=payload)
        assert resp.status_code in (404, 405), resp.status_code


# ===========================================================================
# 四件套 ③ 数据隔离（跨用户行与 spent 的精确隔离见 test_data_isolation.py）
# ===========================================================================


@pytest.mark.asyncio
async def test_budgets_not_visible_across_users(auth_client_a, auth_client_b):
    """③A 的预算、年汇总与 overview 对 B 均不可见（预算行按 user_id 过滤）."""
    a = await make_category(auth_client_a, "M12隔离")
    resp = await auth_client_a.post(
        "/api/budgets",
        json={"month": MONTH, "name": "A的预算", "amount": 1000.0, "category_ids": [a]},
    )
    assert resp.status_code == 200, resp.text

    resp = await auth_client_b.get("/api/budgets", params={"month": MONTH})
    assert resp.json()["data"] == []
    resp = await auth_client_b.get("/api/budgets/year-summary", params={"year": 2026})
    assert all(m["budgets"] == [] for m in resp.json()["data"]["months"])
    resp = await auth_client_b.get("/api/statistics/budget-overview", params={"month": MONTH})
    assert resp.json()["data"]["total_budget"] == 0

    resp = await auth_client_a.get("/api/budgets", params={"month": MONTH})
    assert [x["name"] for x in resp.json()["data"]] == ["A的预算"]


# ===========================================================================
# 四件套 ④ 401 未认证
# ===========================================================================


@pytest.mark.asyncio
async def test_endpoints_require_auth(anon_client):
    """④全部预算端点未带 token → 401（载荷均为合法形态，确保失败原因只有鉴权）."""
    valid_create = {
        "month": MONTH,
        "name": "未认证",
        "amount": 100.0,
        "scope_mode": "include",
        "category_ids": [1],
    }
    valid_update = {"name": "未认证", "amount": 100.0, "category_ids": [1]}
    cases = [
        ("get", "/api/budgets?month=2026-06", None),
        ("get", "/api/budgets/year-summary?year=2026", None),
        # M12 改了 budget-overview 的 categories 明细结构 → 同属本模块变更端点
        ("get", "/api/statistics/budget-overview?month=2026-06", None),
        ("post", "/api/budgets", valid_create),
        ("put", "/api/budgets/1", valid_update),
        ("delete", "/api/budgets/1", None),
    ]
    for method, url, body in cases:
        kwargs = {} if body is None else {"json": body}
        resp = await getattr(anon_client, method)(url, **kwargs)
        assert resp.status_code == 401, f"{method} {url} → {resp.status_code}"


# ===========================================================================
# 分类删除的预算级联（任务 4.1–4.4 / 边界 10.1；变更端点
# ``DELETE /api/categories/{id}`` 与 ``POST /api/categories/restore-defaults``
# 的四件套：①正常级联 ②提示口径 ③关联行不残留 ④见上文 401 段）
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_category_removes_link_but_keeps_include_budget(client, db_session):
    """①任务 4.1：include 预算还有别的分类 → 只移出该分类，预算行不删."""
    a = await make_category(client, "M12级联A")
    b = await make_category(client, "M12级联B")
    await make_expense(client, 100.0, a)
    await make_expense(client, 50.0, b)
    bid = (await post_budget(client, amount=800.0, category_ids=[a, b])).json()["data"]["id"]
    assert set(await link_ids(db_session, bid)) == {a, b}

    resp = await client.delete(f"/api/categories/{a}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == {"deleted_records": 1, "deleted_budgets": 0}
    assert "同时删除了 1 条关联账单" in body["message"]

    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in listed] == [bid]
    assert listed[0]["category_ids"] == [b]
    assert listed[0]["category_names"] == ["M12级联B"]
    assert listed[0]["spent"] == 50.0  # a 的 100 随分类级联删除，不再计入
    assert await link_ids(db_session, bid) == [b]


@pytest.mark.asyncio
async def test_delete_last_include_category_deletes_budget(client, db_session):
    """①任务 4.2：include 预算失去最后一个分类 → 预算一并删除并在 message 提示."""
    a = await make_category(client, "M12唯一类")
    bid = (await post_budget(client, amount=600.0, category_ids=[a])).json()["data"]["id"]

    resp = await client.delete(f"/api/categories/{a}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["deleted_budgets"] == 1
    assert "1 条不再覆盖任何分类的预算" in body["message"]

    assert (await client.get("/api/budgets", params={"month": MONTH})).json()["data"] == []
    assert await db_session.get(Budget, bid) is None
    # 关联行不得残留（连接未启用 foreign_keys，级联全靠服务层显式删）
    assert await link_ids(db_session, bid) == []
    leftover = (
        await db_session.exec(select(BudgetCategory).where(BudgetCategory.budget_id == bid))
    ).all()
    assert leftover == []


@pytest.mark.asyncio
async def test_delete_category_only_widens_exclude_budget(client, db_session):
    """①任务 4.3：exclude 预算仅移出排除集（语义自动扩大），任何情况下都不删."""
    inc = await make_category(client, "M12计入")
    ex1 = await make_category(client, "M12排除1")
    ex2 = await make_category(client, "M12排除2")
    await make_expense(client, 70.0, inc)
    await make_expense(client, 30.0, ex2)
    bid = (
        await post_budget(
            client,
            name="除两类外",
            amount=500.0,
            scope_mode="exclude",
            category_ids=[ex1, ex2],
        )
    ).json()["data"]
    assert bid["spent"] == 70.0, "100 全部支出 − ex2 的 30（ex1 零花费）"

    resp = await client.delete(f"/api/categories/{ex1}")
    assert resp.json()["data"]["deleted_budgets"] == 0
    after = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in after] == [bid["id"]], "exclude 预算永不因删分类而消失"
    assert after[0]["category_ids"] == [ex2]
    assert after[0]["spent"] == 70.0
    assert await link_ids(db_session, bid["id"]) == [ex2]

    # 再删最后一个排除类 → 空排除集 = 全部分类（预算覆盖自动扩大，仍不删）
    await client.delete(f"/api/categories/{ex2}")
    widened = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in widened] == [bid["id"]]
    assert widened[0]["category_ids"] == []
    assert widened[0]["category_names"] == []
    assert widened[0]["spent"] == 70.0  # ex2 的 30 已随分类删除，仅剩 inc 的 70
    assert [d["category_id"] for d in widened[0]["details"]] == [inc]
    assert await link_ids(db_session, bid["id"]) == []


@pytest.mark.asyncio
async def test_restore_defaults_reuses_the_same_budget_cascade(client, db_session):
    """①任务 4.4：restore-defaults 复用同一级联——include 删、exclude 留.

    造形刻意把支出记在**预设**分类上：`restore_default_categories` 对自定义分类的
    账单走「category_id 置 NULL」老逻辑，而 ``Record.category_id`` 自 v1.2.3 起即
    NOT NULL（基线 8652bec 同形），该路径本模块未触碰、不属 M12 范围（已在完成
    notes 上报）。预算级联与账单是否挂在自定义分类上无关，故此处仍完整覆盖 4.4。
    """
    only = await make_category(client, "M12复位A")  # 某 include 预算的唯一分类
    excl = await make_category(client, "M12复位B")  # 某 exclude 预算的排除项
    preset_food = await preset_category_id(client, "餐饮")
    b_include = (
        await post_budget(client, name="会被删", amount=100.0, category_ids=[only])
    ).json()["data"]["id"]
    b_exclude = (
        await post_budget(
            client, name="除B外", amount=200.0, scope_mode="exclude", category_ids=[excl]
        )
    ).json()["data"]["id"]
    await make_expense(client, 25.0, preset_food)

    resp = await client.post("/api/categories/restore-defaults")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["deleted_categories"] == 2
    assert data["deleted_budgets"] == 1

    assert await db_session.get(Budget, b_include) is None, "include 失去唯一分类 → 删"
    assert await link_ids(db_session, b_include) == []
    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in listed] == [b_exclude], "exclude 预算不受级联删除影响"
    assert listed[0]["category_ids"] == []
    assert listed[0]["spent"] == 25.0
    assert [d["category_id"] for d in listed[0]["details"]] == [preset_food]


@pytest.mark.asyncio
async def test_delete_category_cascade_is_owner_scoped(auth_client_a, auth_client_b, db_session):
    """③级联不得越权：B 删自己的分类不能动 A 的预算关联行."""
    cat_a = await make_category(auth_client_a, "M12归属A")
    cat_b = await make_category(auth_client_b, "M12归属B")
    budget_a = (
        await auth_client_a.post(
            "/api/budgets",
            json={
                "month": MONTH,
                "name": "A的预算",
                "amount": 300.0,
                "scope_mode": "include",
                "category_ids": [cat_a],
            },
        )
    ).json()["data"]["id"]
    await auth_client_b.post(
        "/api/budgets",
        json={
            "month": MONTH,
            "name": "B的预算",
            "amount": 300.0,
            "scope_mode": "include",
            "category_ids": [cat_b],
        },
    )

    resp = await auth_client_b.delete(f"/api/categories/{cat_b}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["deleted_budgets"] == 1, "只有 B 自己的预算被级联"

    mine = (await auth_client_a.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in mine] == [budget_a]
    assert mine[0]["category_ids"] == [cat_a]
    assert await link_ids(db_session, budget_a) == [cat_a]


@pytest.mark.asyncio
async def test_changed_category_endpoints_require_auth(anon_client):
    """④本级联改动的两个分类端点未带 token → 401（响应形制变了，鉴权不得松）."""
    assert (await anon_client.delete("/api/categories/1")).status_code == 401
    assert (await anon_client.post("/api/categories/restore-defaults")).status_code == 401


# ===========================================================================
# 导入导出的预算段适配（export_service / import_service 的 budgets 侧）
#
# v1.4.2 的两段代码引用了本模块已删除的列（period / category_id），
# 带预算的库一旦导出即 AttributeError；M12 重写后必须有用例锁住新列形与往返一致性。
# ===========================================================================


async def _export_sql(client) -> str:
    resp = await client.get("/api/export/sql")
    assert resp.status_code == 200, resp.text
    return resp.content.decode("utf-8")


async def _import_sql(client, sql: str) -> dict:
    """走真实两步链路：preview 上传 → confirm（text_sql）."""
    files = {"file": ("backup.sql", sql.encode("utf-8"), "application/sql")}
    resp = await client.post("/api/import/sql/preview", files=files)
    assert resp.status_code == 200, resp.text
    cache_id = resp.json()["data"]["cache_id"]
    resp = await client.post(
        "/api/import/sql", json={"cache_id": cache_id, "format": "text_sql"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_export_sql_carries_named_budget_and_link_rows(client, auth_client_b):
    """①导出：budgets 按新列形（name/month/scope_mode）+ budget_categories 段."""
    food = await make_category(client, "M12导出餐饮")
    shop = await make_category(client, "M12导出购物")
    created = (
        await post_budget(client, name="日常开销", amount=1234.5, category_ids=[food, shop])
    ).json()["data"]
    # 他人的预算不得混入（③隔离）
    other_cat = await make_category(auth_client_b, "M12导出B")
    await post_budget(auth_client_b, name="B的预算", category_ids=[other_cat])

    content = await _export_sql(client)
    budget_lines = [
        ln for ln in content.splitlines() if ln.startswith("INSERT INTO budgets ")
    ]
    assert len(budget_lines) == 1, "只导出本人预算"
    line = budget_lines[0]
    assert "'日常开销'" in line and f"'{MONTH}'" in line and "1234.5" in line
    assert "'include'" in line
    assert "category_id" not in line.split("VALUES")[0], "budgets 段不得再写 category_id"
    assert "B的预算" not in content

    assert "CREATE TABLE IF NOT EXISTS budget_categories" in content
    link_lines = [
        ln for ln in content.splitlines() if ln.startswith("INSERT INTO budget_categories")
    ]
    assert len(link_lines) == 2, "一条预算两个分类 → 两条关联"
    assert f"VALUES ({created['id']}, " in link_lines[0], "关联行带原 budget_id 供重映射"


@pytest.mark.asyncio
async def test_budget_sql_roundtrip_between_users(auth_client_a, auth_client_b):
    """①往返：A 的备份导入 B 后卡片字段原样，分类关联落到 B 自己的副本."""
    food = await make_category(auth_client_a, "M12往返餐饮")
    shop = await make_category(auth_client_a, "M12往返购物")
    original = (
        await post_budget(
            auth_client_a, name="日常开销", amount=1234.5, category_ids=[food, shop]
        )
    ).json()["data"]

    summary = await _import_sql(auth_client_b, await _export_sql(auth_client_a))
    assert summary["total_imported"] >= 3, "分类 2 + 预算 1 至少三条"

    listed = (
        await auth_client_b.get("/api/budgets", params={"month": MONTH})
    ).json()["data"]
    assert len(listed) == 1
    restored = listed[0]
    assert restored["name"] == original["name"]
    assert restored["month"] == MONTH and restored["amount"] == 1234.5
    assert restored["scope_mode"] == "include"
    assert restored["category_names"] == original["category_names"]
    assert len(restored["category_ids"]) == 2
    assert not {food, shop} & set(restored["category_ids"]), "分类 id 须重映射，不指向 A 的行"
    assert restored["spent"] == 0, "A 的流水不得并进 B 的预算"


@pytest.mark.asyncio
async def test_import_pre_m12_budget_rows(client):
    """②旧备份行（无 name/scope_mode）→ include 单分类；分类不可解析→「未知分类」."""
    preset = await preset_category_id(client, "餐饮")
    sql = f"""CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category_id INTEGER,
    month TEXT NOT NULL,
    amount REAL NOT NULL,
    created_at TEXT,
    updated_at TEXT
);
INSERT INTO budgets (user_id, category_id, month, amount, created_at, updated_at)
VALUES (1, {preset}, '{MONTH}', 777.0, '2026-01-01 00:00:00', '2026-01-01 00:00:00');
INSERT INTO budgets (user_id, category_id, month, amount, created_at, updated_at)
VALUES (1, 999999, '{MONTH}', 222.0, '2026-01-01 00:00:00', '2026-01-01 00:00:00');
"""
    await _import_sql(client, sql)

    listed = (await client.get("/api/budgets", params={"month": MONTH})).json()["data"]
    by_amount = {b["amount"]: b for b in listed}
    assert set(by_amount) == {777.0, 222.0}

    legacy = by_amount[777.0]
    assert legacy["name"] == "餐饮" and legacy["scope_mode"] == "include"
    assert legacy["category_ids"] == [preset]

    orphan = by_amount[222.0]
    assert orphan["name"] == "未知分类", "与迁移阶段 B 同款的只读态（任务 9.3）"
    assert orphan["category_ids"] == [] and orphan["spent"] == 0
    resp = await client.put(
        f"/api/budgets/{orphan['id']}",
        json={"name": "未知分类", "amount": 222.0, "scope_mode": "include", "category_ids": []},
    )
    assert resp.status_code == 400 and resp.json()["code"] == 40001
