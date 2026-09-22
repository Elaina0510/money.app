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

⚠ **v1.4.3-boot2 M3 口径反转**（决策 D3/D4/D9/D10；逐条登记旧用例的去向）：
  - 「include + 空分类集 → 400」的服务层校验**已删除** → 旧
    ``test_include_needs_at_least_one_category`` 改写为
    ``test_include_empty_category_is_dynamic_all``（200 + spent = 当月全额）；
  - 空集从此承载两义：**主动不选 = 动态全部分类**（dormant=0）/
    **关联被删光 = 休眠**（dormant=1，花费恒 0）→ BudgetDetail 增 ``dormant: bool``；
  - 「include 预算失去最后关联 → 预算删除」改「置 dormant=1 保留」→ 旧
    ``test_delete_last_include_category_deletes_budget`` 改写为
    ``test_delete_last_include_category_dormants_budget``，计数响应键
    ``deleted_budgets`` → ``dormant_budgets``（restore-defaults / 越权用例同键同改）；
  - 旧 ``test_migrated_orphan_budget_is_read_only``（钉死「include 空集 = 只读态、
    spent 恒 0、PUT 被 400 拦、删除是唯一出口」）与 M3 新语义逐条冲突 → 改写为
    ``test_orphan_empty_include_budget_is_dynamic_all``（spent = 当月全额 + PUT 200）；
  - 导入旧备份产出的「未知分类」空集预算：PUT 由 400 改 200（``dormant=0`` 时同样是
    动态全部口径），见 ``test_import_pre_m12_budget_rows`` 末段；
  - 新增：``_build_detail`` **四分支参数化**（分支顺序 = dormant → INCLUDE 空集 →
    INCLUDE 显式 → exclude，D5 要求 INCLUDE 空集与 exclude 空排除集逐位同值）、
    唤醒（PUT → dormant=0）、汇总剔除双向断言（overview/year 不计 dormant **且**
    月列表仍返回 dormant 行）；``dormant`` 迁移脚本用例另见
    ``test_migration_v143boot2_dormant.py``（任务 8.6）。
"""

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app as fastapi_app
from app.models.budget import UNKNOWN_CATEGORY_NAME, Budget, BudgetCategory
from app.services import budget_service

MONTH = "2026-06"

# BudgetDetail 契约（任务 2.7 + M3 任务 2.4）——前端渲染所需字段清单，多给/少给都算回归
BUDGET_DETAIL_KEYS = {
    "id",
    "month",
    "name",
    "amount",
    "spent",
    "remaining",
    "percentage",
    "scope_mode",
    "dormant",
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
    """按新契约 POST 一条预算（M3 起 include 空集合法 = 动态全部分类，默认即空集）."""
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


async def list_budgets(client, month: str = MONTH) -> list[dict]:
    """月视图卡片数据源：``GET /api/budgets?month=``（M3 起**含** dormant 行）."""
    resp = await client.get("/api/budgets", params={"month": month})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def budget_row(client, budget_id: int, month: str = MONTH) -> dict:
    """从月列表接口里按 id 取一条预算（不存在即失败）。"""
    rows = [x for x in await list_budgets(client, month) if x["id"] == budget_id]
    assert len(rows) == 1, f"预算 {budget_id} 不在列表里：{rows}"
    return rows[0]


async def db_dormant(db_session: AsyncSession, budget_id: int) -> int:
    """直读 ``budgets.dormant`` 列（落库真值，不看响应）。

    用**列投影**而非 ``db_session.get(Budget, id)``：接口写入走的是另一个会话
    （``conftest.override_get_session``），``get()`` 会命中本会话身份映射里的过期对象、
    读到陈旧 dormant；列查询绕过身份映射，取回的是库里当前那一列。
    """
    row = (
        await db_session.exec(select(Budget.dormant).where(Budget.id == budget_id))
    ).first()
    assert row is not None, "M3 后休眠预算**不得**被删除"
    return int(row)


async def force_dormant(db_session: AsyncSession, budget_id: int, value: int = 1) -> None:
    """直写 dormant 列：造出「级联产物」形态，无需绕道删分类（纯函数/汇总用例用）。

    先 ``refresh``：接口写入走另一个会话且 ``expire_on_commit=False``，身份映射里的
    过期对象会让「置 1」不产生脏字段 → UPDATE 不发、造形静默失败。
    """
    budget = await db_session.get(Budget, budget_id)
    assert budget is not None
    await db_session.refresh(budget)
    budget.dormant = value
    db_session.add(budget)
    await db_session.commit()


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
async def test_orphan_empty_include_budget_is_dynamic_all(client, db_session):
    """①任务 8.12（M3 改写）：空集 include **不再是只读态**——spent = 当月全额 + PUT 200.

    旧裁定（v1.4.3 任务 9.3）：「未知分类」= include 空集 → spent 恒 0、PUT 被
    「include ≥1」400 拦下、删除是唯一出口。M3（决策 D3/D5/D9）逐条反判：
      * 空集 + dormant=0 = **动态全部分类** → spent 与 exclude 空排除集同口径（全额）；
      * PUT 空集 → 200（校验已删）；休眠只能由分类删除级联置 1，任何成功保存清 0；
      * DELETE 仍可用，但**不再是**唯一出口（编辑保存即可自救）。
    造形方式沿用旧用例：先 POST 真预算，再按阶段 B 的产出改写名称并清空关联行
    （dormant 列保持默认 0 = 「非休眠的空集」）。
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

    await make_expense(client, 120.0, food)  # 分类还在，只是预算不再显式挂它

    orphan = await budget_row(client, bid)
    assert orphan["name"] == "未知分类"
    assert orphan["scope_mode"] == "include"
    assert orphan["category_ids"] == []
    assert orphan["category_names"] == []
    assert orphan["dormant"] is False, "空集两义由 dormant 列区分，导入/迁移态默认 0"
    assert orphan["spent"] == 120.0, "非休眠空集 = 动态全部 → 当月全额（D3/D5）"
    assert [d["category_id"] for d in orphan["details"]] == [food], "明细列有花费的类目"
    assert orphan["remaining"] == 380.0
    assert orphan["percentage"] == 24.0

    # 休眠态（dormant=1）才是「花费恒 0 + 无明细」，且**行仍在列表**（D4 不删）
    await force_dormant(db_session, bid)
    sleeping = await budget_row(client, bid)
    assert sleeping["dormant"] is True
    assert sleeping["spent"] == 0 and sleeping["details"] == []
    assert sleeping["remaining"] == 500.0

    # PUT 200 且**保存即唤醒**（旧断言：400 + PARAM_ERROR + 数据不变，已随校验删除作废）
    resp = await client.put(
        f"/api/budgets/{bid}",
        json={"name": "未知分类", "amount": 600.0, "scope_mode": "include", "category_ids": []},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dormant"] is False
    assert resp.json()["data"]["spent"] == 120.0, "唤醒后立刻恢复动态全部口径"
    assert await db_dormant(db_session, bid) == 0
    still = await budget_row(client, bid)
    assert still["amount"] == 600.0 and still["dormant"] is False

    # 删除接口零改动（7.4）：休眠/非休眠都能删，但它只是并列出口之一
    resp = await client.delete(f"/api/budgets/{bid}")
    assert resp.status_code == 200
    assert await list_budgets(client) == []


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
async def test_include_empty_category_is_dynamic_all(client):
    """②/① 任务 8.1（M3 改写旧「include 空集 → 400」）：空集 = 动态全部分类（D3）.

    旧断言：``include`` + 空 ``category_ids`` → 400 + PARAM_ERROR「包含模式至少需要选择
    1 个分类」（服务层 ``_validate_budget_fields``）。该校验已随 M3 删除，新口径：
      * POST/PUT 一律 200、正常落库（空关联行），``dormant=0``；
      * spent = 当月全部支出（与 exclude 空排除集**完全同口径**，D5 / 边界 7.2）；
      * **后续新建的分类自动计入**（边界 7.1 的动态语义，不重写关联行）；
      * 旧版前端缓存包不带 ``category_ids`` 字段 → 缺省即空集，同样 200（边界 7.7）。
    """
    resp = await post_budget(client, name="全开销", amount=1000.0, category_ids=[])
    assert resp.status_code == 200, resp.text
    b = resp.json()["data"]
    assert b["scope_mode"] == "include" and b["category_ids"] == []
    assert b["dormant"] is False, "主动不选 ≠ 休眠：两义由 dormant 列区分（D3）"
    assert b["spent"] == 0 and b["details"] == []

    resp = await client.post(
        "/api/budgets", json={"month": MONTH, "name": "无范围", "amount": 100.0}
    )
    assert resp.status_code == 200, "category_ids 缺省即空列表 = 动态全部（旧断言 400）"
    legacy = resp.json()["data"]
    assert legacy["scope_mode"] == "include" and legacy["category_ids"] == []

    first = await make_category(client, "M12D动1")
    await make_expense(client, 40.0, first)
    assert (await budget_row(client, b["id"]))["spent"] == 40.0

    # 7.1：事后新建分类并记账 → 该预算数字自动跟上（用户无需重选分类）
    later = await make_category(client, "M12D动2")
    await make_expense(client, 60.0, later)
    grown = await budget_row(client, b["id"])
    assert grown["spent"] == 100.0, "动态全部：新分类无需回填关联即计入"
    assert grown["category_ids"] == [], "动态口径是求和规则，不改写关联行"
    assert sorted(d["category_id"] for d in grown["details"]) == sorted([first, later])

    # 7.2 / D5：同月的 exclude 空排除集与之花费逐位同值（仅标签/明细语义不同）
    ex = (
        await post_budget(client, name="除零外", amount=1000.0, scope_mode="exclude")
    ).json()["data"]
    assert ex["spent"] == grown["spent"] == 100.0
    assert [d["category_id"] for d in ex["details"]] == [
        d["category_id"] for d in grown["details"]
    ]


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
# 分类删除的预算级联（v1.4.3 M12 任务 4.1–4.4 → **v1.4.3-boot2 M3 任务 3.1–3.3
# 改向**：include 预算失去最后关联不再删除，改置 dormant=1 休眠保留，计数键
# ``deleted_budgets`` → ``dormant_budgets``；边界 7.4/7.5 亦归本段）
# 变更端点 ``DELETE /api/categories/{id}`` 与 ``POST /api/categories/restore-defaults``
# 的四件套：①正常级联 ②提示口径 ③关联行不残留 ④见上文 401 段
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_category_removes_link_but_keeps_include_budget(client, db_session):
    """①任务 3.1：include 预算还有别的分类 → 只移出该分类，预算不删也**不休眠**."""
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
    # 计数键随级联改向：deleted_budgets → dormant_budgets（任务 3.3）
    assert body["data"] == {"deleted_records": 1, "dormant_budgets": 0}
    assert "同时删除了 1 条关联账单" in body["message"]
    # 任务 3.4：M=0 时「…被保留为休眠」整句不提
    assert "休眠" not in body["message"], body["message"]

    listed = await list_budgets(client)
    assert [x["id"] for x in listed] == [bid]
    assert listed[0]["category_ids"] == [b]
    assert listed[0]["category_names"] == ["M12级联B"]
    assert listed[0]["spent"] == 50.0  # a 的 100 随分类级联删除，不再计入
    assert listed[0]["dormant"] is False
    assert await db_dormant(db_session, bid) == 0
    assert await link_ids(db_session, bid) == [b]


@pytest.mark.asyncio
async def test_delete_last_include_category_dormants_budget(client, db_session):
    """①任务 3.1/3.3/3.4（M3 改写旧「预算随之删除」）：失去最后关联 → **休眠保留**."""
    a = await make_category(client, "M12唯一类")
    bid = (await post_budget(client, amount=600.0, category_ids=[a])).json()["data"]["id"]

    resp = await client.delete(f"/api/categories/{a}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["dormant_budgets"] == 1, "计数键改向（原 deleted_budgets）"
    assert "1 条预算因不再覆盖任何分类被保留为休眠" in body["message"], body["message"]

    # 预算**仍在列表**（月视图卡片要置灰展示，D10 的另一半）——旧断言是列表为空
    listed = await list_budgets(client)
    assert [x["id"] for x in listed] == [bid], "D4：不再删除预算行"
    dormant = listed[0]
    assert dormant["dormant"] is True
    assert dormant["spent"] == 0 and dormant["details"] == []
    assert dormant["remaining"] == 600.0 and dormant["percentage"] == 0
    assert dormant["category_ids"] == [] and dormant["category_names"] == []
    assert await db_dormant(db_session, bid) == 1
    # 关联行不得残留（连接未启用 foreign_keys，级联全靠服务层显式删）
    assert await link_ids(db_session, bid) == []
    leftover = (
        await db_session.exec(select(BudgetCategory).where(BudgetCategory.budget_id == bid))
    ).all()
    assert leftover == []


@pytest.mark.asyncio
async def test_deleting_custom_other_category_dormants_budget(client, db_session):
    """①边界 7.5：「其他」的 custom 副本被删 → 走**同一**休眠级联（不再连删预算）.

    级联函数不区分被删分类的身份（预设/副本/家族名），故挂唯一 custom「其他」的
    include 预算与 M2 合并后的 keeper 副本删除路径同形。
    """
    other = await make_category(client, "其他")  # 用户同名副本（可删）
    bid = (
        await post_budget(client, name="兜底预算", amount=300.0, category_ids=[other])
    ).json()["data"]["id"]
    await make_expense(client, 12.0, other)

    resp = await client.delete(f"/api/categories/{other}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"deleted_records": 1, "dormant_budgets": 1}

    row = await budget_row(client, bid)
    assert row["dormant"] is True and row["spent"] == 0 and row["details"] == []
    assert await db_dormant(db_session, bid) == 1


@pytest.mark.asyncio
async def test_delete_category_only_widens_exclude_budget(client, db_session):
    """①任务 3.2：exclude 预算仅移出排除集（语义自动扩大），**无休眠概念**、任何情况下不删."""
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
    assert bid["dormant"] is False

    resp = await client.delete(f"/api/categories/{ex1}")
    assert resp.json()["data"]["dormant_budgets"] == 0
    after = await list_budgets(client)
    assert [x["id"] for x in after] == [bid["id"]], "exclude 预算永不因删分类而消失"
    assert after[0]["category_ids"] == [ex2]
    assert after[0]["spent"] == 70.0
    assert after[0]["dormant"] is False, "移出排除集 = 覆盖扩大，不进休眠（任务 3.2）"
    assert await db_dormant(db_session, bid["id"]) == 0
    assert await link_ids(db_session, bid["id"]) == [ex2]

    # 再删最后一个排除类 → 空排除集 = 全部分类（预算覆盖自动扩大，仍不删也不休眠）
    await client.delete(f"/api/categories/{ex2}")
    widened = await list_budgets(client)
    assert [x["id"] for x in widened] == [bid["id"]]
    assert widened[0]["category_ids"] == []
    assert widened[0]["category_names"] == []
    assert widened[0]["spent"] == 70.0  # ex2 的 30 已随分类删除，仅剩 inc 的 70
    assert widened[0]["dormant"] is False
    assert [d["category_id"] for d in widened[0]["details"]] == [inc]
    assert await link_ids(db_session, bid["id"]) == []
    assert await db_dormant(db_session, bid["id"]) == 0


@pytest.mark.asyncio
async def test_restore_defaults_reuses_the_same_budget_cascade(client, db_session):
    """①任务 3.3：restore-defaults 复用同一休眠级联——include 转休眠、exclude 留.

    造形刻意把支出记在**预设**分类上：`restore_default_categories` 对自定义分类的
    账单走「category_id 置 NULL」老逻辑，而 ``Record.category_id`` 自 v1.2.3 起即
    NOT NULL（基线 8652bec 同形），该路径本模块未触碰、不属 M12/M3 范围（已在完成
    notes 上报）。预算级联与账单是否挂在自定义分类上无关，故此处仍完整覆盖 3.3。
    """
    only = await make_category(client, "M12复位A")  # 某 include 预算的唯一分类
    excl = await make_category(client, "M12复位B")  # 某 exclude 预算的排除项
    preset_food = await preset_category_id(client, "餐饮")
    b_include = (
        await post_budget(client, name="会休眠", amount=100.0, category_ids=[only])
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
    assert data["dormant_budgets"] == 1, "同一函数的返回键随级联改向（任务 3.3）"

    # include 预算**不删**，转 dormant=1 保留（旧断言：行已消失）
    assert await db_dormant(db_session, b_include) == 1
    assert await link_ids(db_session, b_include) == []
    listed = await list_budgets(client)
    assert [x["id"] for x in listed] == [b_include, b_exclude]
    assert listed[0]["dormant"] is True
    assert listed[0]["spent"] == 0 and listed[0]["details"] == []
    assert listed[1]["category_ids"] == [], "exclude 预算不受级联影响，仅移出排除集"
    assert listed[1]["dormant"] is False
    assert listed[1]["spent"] == 25.0
    assert [d["category_id"] for d in listed[1]["details"]] == [preset_food]


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
    assert resp.json()["data"]["dormant_budgets"] == 1, "只有 B 自己的预算被级联（置休眠）"
    b_listed = await list_budgets(auth_client_b)
    assert len(b_listed) == 1 and b_listed[0]["dormant"] is True, "B 的预算保留不删（D4）"

    mine = (await auth_client_a.get("/api/budgets", params={"month": MONTH})).json()["data"]
    assert [x["id"] for x in mine] == [budget_a]
    assert mine[0]["category_ids"] == [cat_a]
    assert mine[0]["dormant"] is False, "A 的预算既没被删也没被休眠"
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
    assert orphan["name"] == "未知分类", "与迁移阶段 B 同款的 include 空集形态（任务 9.3）"
    assert orphan["category_ids"] == [] and orphan["spent"] == 0
    assert orphan["dormant"] is False, "导入产物非休眠 → 空集即「动态全部分类」（M3/D3）"

    # M3 改向：该形态不再只读——事后记账自动计入（动态），PUT 空集亦 200（旧断言 400）
    await make_expense(client, 30.0, preset)
    assert (await budget_row(client, orphan["id"]))["spent"] == 30.0
    resp = await client.put(
        f"/api/budgets/{orphan['id']}",
        json={"name": "未知分类", "amount": 222.0, "scope_mode": "include", "category_ids": []},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dormant"] is False


# ===========================================================================
# v1.4.3-boot2 M3：不选 = 动态全部 + 分类删光转休眠
# （任务 8.2 `_build_detail` 四分支 / 8.4 唤醒 / 8.5 汇总剔除双向断言）
# ===========================================================================

# 分类展示信息 (name, icon, sort_order)——明细排序基准
_M3_INFO: dict[int, tuple[str, str, int]] = {
    1: ("餐饮", "mdi-food", 1),
    2: ("购物", "mdi-cart", 2),
    3: ("出行", "mdi-bus", 3),
}
# 当月「分类 → 支出」映射；**键 0 = 未分类桶**（category_id NULL / 失效的极端数据）
# → month_total = 100 + 50 + 25 + 10 = 185.0
_M3_SPENT: dict[int, float] = {1: 100.0, 2: 50.0, 3: 25.0, 0: 10.0}


def _m3_detail(
    scope_mode: str = "include",
    category_ids: list[int] | None = None,
    dormant: int = 0,
    amount: float = 1000.0,
) -> dict:
    """直接调纯函数 `_build_detail`（无 IO、无会话）——M3 分支表的钉死入口."""
    snap = budget_service._BudgetSnapshot(
        id=1,
        name="M3分支",
        month=MONTH,
        amount=amount,
        scope_mode=scope_mode,
        dormant=dormant,
        created_at="2026-01-01 00:00:00",
        updated_at="2026-01-01 00:00:00",
    )
    return budget_service._build_detail(
        snap, list(category_ids or []), _M3_INFO, dict(_M3_SPENT)
    )


# (用例名, scope_mode, category_ids, dormant, 期望 spent, 期望明细类目)
# **表序 = 分支判定序**（任务 2.3）：dormant → INCLUDE 空集 → INCLUDE 显式 → exclude
_M3_BRANCH_CASES = [
    ("branch1_dormant_include_empty", "include", [], 1, 0.0, []),
    ("branch1_dormant_include_explicit", "include", [1, 2], 1, 0.0, []),
    ("branch1_dormant_exclude", "exclude", [1], 1, 0.0, []),
    ("branch2_include_empty_is_month_total", "include", [], 0, 185.0, [1, 2, 3]),
    ("branch3_include_explicit", "include", [2, 3], 0, 75.0, [2, 3]),
    ("branch4_exclude_one", "exclude", [1], 0, 85.0, [2, 3]),
    ("branch4_exclude_empty_is_month_total", "exclude", [], 0, 185.0, [1, 2, 3]),
]


@pytest.mark.parametrize(
    "name,scope_mode,ids,dormant,expected_spent,expected_details",
    _M3_BRANCH_CASES,
    ids=[c[0] for c in _M3_BRANCH_CASES],
)
def test_build_detail_branch_table(
    name, scope_mode, ids, dormant, expected_spent, expected_details
):
    """任务 8.2：`_build_detail` 四分支表逐支钉死（表序即判定序）."""
    assert name.startswith("branch")  # 表内每支按分支槽位命名 → 读表即见判定序
    got = _m3_detail(scope_mode=scope_mode, category_ids=ids, dormant=dormant)
    assert got["spent"] == expected_spent
    assert [d["category_id"] for d in got["details"]] == expected_details
    assert got["dormant"] is bool(dormant)
    assert got["remaining"] == round(1000.0 - expected_spent, 2)
    assert got["percentage"] == round(expected_spent / 1000.0 * 100, 1)


def test_build_detail_dormant_precedes_every_branch():
    """任务 2.3/8.2：**分支 1 抢占**——同一载荷 dormant=1 与 dormant=0 结果必须不同.

    若把 dormant 判定挪到 include/exclude 之后，这些组合会退化成「全额 / Σ 所选」，
    休眠预算便又参与统计（违 D4/D10）。休眠行仍照常带出 name/amount/category_ids，
    供前端置灰卡片渲染（覆盖文案由前端按 dormant 出，后端不塞字符串）。
    """
    assert _m3_detail("include", [], dormant=1)["spent"] == 0.0
    assert _m3_detail("include", [], dormant=0)["spent"] == 185.0
    assert _m3_detail("exclude", [1], dormant=1)["spent"] == 0.0
    assert _m3_detail("exclude", [1], dormant=0)["spent"] == 85.0
    sleeping = _m3_detail("include", [1, 2], dormant=1)
    assert sleeping["details"] == [] and sleeping["category_ids"] == [1, 2]
    assert sleeping["remaining"] == 1000.0 and sleeping["percentage"] == 0
    assert sleeping["dormant"] is True, "响应须带 dormant，供前端置灰（任务 2.4）"


def test_build_detail_include_empty_equals_exclude_empty_bit_for_bit():
    """任务 8.2 / D5：INCLUDE 空集 spent 与 exclude 空排除集**完全同值**（含未分类桶）.

    D5 裁定「不另立第二口径」——两分支的 spent 与明细必须逐字段一致，仅 scope_mode
    标签不同；未分类桶（键 0）计入 spent 但**无名可列**，故不出现在 details。
    """
    inc = _m3_detail("include", [], dormant=0)
    exc = _m3_detail("exclude", [], dormant=0)
    assert inc["spent"] == exc["spent"] == 185.0, "含未分类桶 10.0 → 全额（D5）"
    assert sum(d["spent"] for d in inc["details"]) == 175.0, "明细合计不含未分类桶"
    assert {d["category_id"] for d in inc["details"]} == {1, 2, 3}
    assert {k: v for k, v in inc.items() if k != "scope_mode"} == {
        k: v for k, v in exc.items() if k != "scope_mode"
    }, "除标签外逐位同值（边界 7.2 的『非矛盾』）"


def test_build_detail_dangling_category_same_on_both_empty_branches():
    """任务 2.3 / D5：悬挂分类 id（不在 info 里，分类已被删）两支仍逐位同值.

    两支共用「花费 > 0 且非未分类桶」的同一份过滤 + 同一个 `_detail_entry` 兜底，
    故极端数据下也只可能长成同一个样（「未知分类」+ `mdi-cash`），不制造第二口径。
    """
    spent = {1: 60.0, 99: 40.0, 0: 5.0}  # 99 = 悬挂 id（分类不存在）
    built = [
        budget_service._build_detail(
            budget_service._BudgetSnapshot(
                id=7,
                name="悬挂",
                month=MONTH,
                amount=100.0,
                scope_mode=scope,
                dormant=0,
                created_at="2026-01-01 00:00:00",
                updated_at="2026-01-01 00:00:00",
            ),
            ids,
            _M3_INFO,
            dict(spent),
        )
        for scope, ids in (("include", []), ("exclude", []))
    ]
    first, second = built
    assert first["spent"] == second["spent"] == 105.0, "全额含悬挂桶与未分类桶"
    assert [d["category_id"] for d in first["details"]] == [
        d["category_id"] for d in second["details"]
    ]
    dangling = [d for d in first["details"] if d["category_id"] == 99][0]
    assert dangling["category_name"] == UNKNOWN_CATEGORY_NAME
    assert dangling["icon"] == "mdi-cash"


@pytest.mark.asyncio
async def test_dormant_budget_put_wakes_up(client, db_session):
    """①任务 3.5 / 8.4 + 边界 7.6：任何成功 PUT 一律 dormant=0（D9），无独立唤醒接口.

    三条唤醒路径逐一过：重选分类 / 一个都不选（= 动态全部）/ 改 scope_mode=exclude。
    """
    only = await make_category(client, "M12唤睡")
    later = await make_category(client, "M12唤醒新")
    await make_expense(client, 40.0, later)
    bid = (
        await post_budget(client, name="先睡后醒", amount=200.0, category_ids=[only])
    ).json()["data"]["id"]

    await client.delete(f"/api/categories/{only}")  # 级联 → 休眠
    assert await db_dormant(db_session, bid) == 1
    assert (await budget_row(client, bid))["spent"] == 0.0

    # 路径①：重选分类唤醒 → spent 恢复按所选求和
    resp = await client.put(
        f"/api/budgets/{bid}",
        json={"name": "醒着", "amount": 200.0, "scope_mode": "include", "category_ids": [later]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dormant"] is False
    assert resp.json()["data"]["spent"] == 40.0
    assert await db_dormant(db_session, bid) == 0

    # 路径②：再次休眠后**一个都不选**保存 → 唤醒即得动态全部（D3 + D9 的合力）
    await force_dormant(db_session, bid)
    assert (await budget_row(client, bid))["dormant"] is True
    resp = await client.put(
        f"/api/budgets/{bid}",
        json={"name": "全开销", "amount": 200.0, "scope_mode": "include", "category_ids": []},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dormant"] is False
    assert resp.json()["data"]["spent"] == 40.0, "空集 = 当月全额（此处仅 later 的 40）"
    assert await db_dormant(db_session, bid) == 0

    # 路径③（边界 7.6）：休眠态 PUT 改 exclude → dormant 清 0，exclude 无休眠语义
    await force_dormant(db_session, bid)
    resp = await client.put(
        f"/api/budgets/{bid}",
        json={"name": "除己外", "amount": 200.0, "scope_mode": "exclude", "category_ids": [later]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dormant"] is False
    assert resp.json()["data"]["scope_mode"] == "exclude"
    assert resp.json()["data"]["spent"] == 0.0, "排除 later 后当月无剩余支出"
    assert await db_dormant(db_session, bid) == 0

    # 唤醒**只有**这一条路：路由表里不存在 dormant/wake 相关端点（任务 3.5 核验）
    paths = [str(r.path) for r in fastapi_app.routes]
    assert not [p for p in paths if "dormant" in p or "wake" in p], paths
    assert (await client.post(f"/api/budgets/{bid}/wake")).status_code in (404, 405)


@pytest.mark.asyncio
async def test_dormant_excluded_from_summaries_but_still_listed(client, db_session):
    """①任务 4.1/4.2/4.3 / 8.5：汇总剔除 dormant **且** 列表仍返回它（双向断言）."""
    keep = await make_category(client, "M12计入月")
    gone = await make_category(client, "M12将被删")
    await make_expense(client, 100.0, keep)
    await make_expense(client, 30.0, gone)
    b_normal = (
        await post_budget(client, name="正常", amount=1000.0, category_ids=[keep])
    ).json()["data"]["id"]
    b_dormant = (
        await post_budget(client, name="将休眠", amount=500.0, category_ids=[gone])
    ).json()["data"]["id"]

    await client.delete(f"/api/categories/{gone}")  # → dormant=1（其 30 的账单随级联删除）
    assert await db_dormant(db_session, b_dormant) == 1

    # 方向 A：月列表接口（月视图卡片数据源）**不得**误过滤 dormant 行
    listed = await list_budgets(client)
    assert [x["id"] for x in listed] == [b_normal, b_dormant], "置灰展示需要它（任务 4.3）"
    assert [x["dormant"] for x in listed] == [False, True]
    assert listed[1]["amount"] == 500.0 and listed[1]["spent"] == 0.0

    # 方向 B：月概览（get_budget_overview，原书误作 get_month_summary）不计 dormant
    resp = await client.get("/api/statistics/budget-overview", params={"month": MONTH})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total_budget"] == 1000.0, "500 的休眠预算不进 total（D10）"
    assert data["total_spent"] == 100.0
    assert [c["budget_id"] for c in data["categories"]] == [b_normal]

    # 方向 B：年汇总同样剔除，但 budgets 数组保留 dormant 行
    resp = await client.get("/api/budgets/year-summary", params={"year": 2026})
    june = {m["month"]: m for m in resp.json()["data"]["months"]}["2026-06"]
    assert june["total_amount"] == 1000.0
    assert june["total_spent"] == 100.0
    assert [b["id"] for b in june["budgets"]] == [b_normal, b_dormant]
    assert [b["dormant"] for b in june["budgets"]] == [False, True]
    assert june["total_amount"] == sum(
        b["amount"] for b in june["budgets"] if not b["dormant"]
    )
    assert june["total_spent"] == sum(
        b["spent"] for b in june["budgets"] if not b["dormant"]
    )

    # 边界 7.4：用户摆脱休眠态的另一出口——既有 DELETE 接口**零改动**可用
    resp = await client.delete(f"/api/budgets/{b_dormant}")
    assert resp.status_code == 200, resp.text
    assert [x["id"] for x in await list_budgets(client)] == [b_normal]
    assert await link_ids(db_session, b_dormant) == []
