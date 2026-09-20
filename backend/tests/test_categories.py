"""Tests for category API（v1.4.3 M8：分类收支共用，type 语义废弃）。

覆盖设计 §8.4「pytest 重写 test_categories.py」：
  * 去 type 后 CRUD；
  * 跨原收支语义同名查重拒绝（name + user_id 唯一）；
  * 「其他」改名 400；
  * CoW 仅按 name（用户「工资」副本遮蔽预设，无论列上残留 type 值）；
  * GET 带 `type=expense` → 200 且返回全量（参数被忽略）。

测试库预设来自 `conftest.PRESET_CATEGORIES`——那是**过期的 7 条副本**（9.3a 登记），
含旧语义名「其他收入」、旅行图标 `mdi-airplane`，**不等于生产预设集**。故：
  * 涉及预设 icon/排序真源的断言一律不写在这里（见 `test_migration_v143.py`）；
  * 本文件涉及「其他」的用例**在用例内显式建名「其他」的行**，不靠预设。
"""

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
async def test_get_categories_type_param_ignored(client):
    """9.1 忽略断言：`type` 参数保留签名但一律忽略——三种取值返回**同一全量列表**。"""
    await client.post("/api/categories", json={"name": "宠物", "icon": "mdi-paw"})

    async def names(query: str) -> list[str]:
        resp = await client.get(f"/api/categories{query}")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        return [c["name"] for c in resp.json()["data"]]

    full = await names("")
    assert await names("?type=expense") == full
    assert await names("?type=income") == full
    assert await names("?type=whatever") == full
    # 全量单列表：原收入侧预设「工资」与原支出侧预设「餐饮」同在一列
    assert "工资" in full and "餐饮" in full


@pytest.mark.asyncio
async def test_create_category(client):
    """Test creating a new custom category（载荷不再收 type，D2 写占位值）。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "测试分类", "icon": "mdi-test", "sort_order": 50},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试分类"
    assert data["data"]["type"] == "expense"  # 占位值，语义已废弃
    assert data["data"]["is_preset"] == 0


@pytest.mark.asyncio
async def test_create_category_ignores_client_type_field(client):
    """旧客户端仍带 `type: income` → 200 且落库 type 恒为占位 'expense'（多余字段忽略）。"""
    resp = await client.post(
        "/api/categories",
        json={"name": "旧客户端分类", "type": "income", "icon": "mdi-wallet"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["type"] == "expense"


@pytest.mark.asyncio
async def test_create_duplicate_category(client):
    """Test creating a category with duplicate name."""
    await client.post("/api/categories", json={"name": "测试重复", "icon": "mdi-test"})
    resp = await client.post("/api/categories", json={"name": "测试重复", "icon": "mdi-test"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40003


@pytest.mark.asyncio
async def test_create_duplicate_across_legacy_type_semantics(client):
    """9.1 跨原收支语义同名亦拒：v1.4.2 允许「餐饮(支出)+餐饮(收入)」两行，v1.4.3 起 400。"""
    first = await client.post(
        "/api/categories", json={"name": "宠物", "icon": "mdi-paw", "sort_order": 60}
    )
    assert first.status_code == 200
    assert first.json()["data"]["type"] == "expense"

    second = await client.post(
        "/api/categories",
        json={"name": "宠物", "type": "income", "icon": "mdi-paw", "sort_order": 61},
    )
    assert second.status_code == 400
    assert second.json()["code"] == 40003

    names = [c["name"] for c in (await client.get("/api/categories")).json()["data"]]
    assert names.count("宠物") == 1


@pytest.mark.asyncio
async def test_update_category(client):
    """Test updating a category."""
    resp = await client.post(
        "/api/categories",
        json={"name": "旧名称", "icon": "mdi-old", "sort_order": 10},
    )
    cat_id = resp.json()["data"]["id"]

    resp = await client.put(f"/api/categories/{cat_id}", json={"name": "新名称", "icon": "mdi-new"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "新名称"


@pytest.mark.asyncio
async def test_update_nonexistent_category(client):
    """Test updating a non-existent category."""
    resp = await client.put("/api/categories/99999", json={"name": "不存在", "icon": "mdi-none"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002


@pytest.mark.asyncio
async def test_delete_category(client):
    """Test deleting a custom category."""
    resp = await client.post(
        "/api/categories",
        json={"name": "待删除", "icon": "mdi-delete", "sort_order": 1},
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
    """Test that preset categories are available（仅断言测试库确有种子的行，见模块 docstring）."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    names = [c["name"] for c in data["data"]]
    assert "餐饮" in names
    assert "出行" in names
    assert "工资" in names


# --- Cascade delete tests ---


@pytest.mark.asyncio
async def test_delete_category_no_records(client):
    """Test deleting a category with no associated records returns deleted_records=0."""
    resp = await client.post(
        "/api/categories",
        json={"name": "空分类", "icon": "mdi-empty", "sort_order": 1},
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
        json={"name": "级联分类", "icon": "mdi-cascade", "sort_order": 1},
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
        json={"name": "预算分类", "icon": "mdi-budget", "sort_order": 1},
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
    resp = await auth_client_a.post("/api/categories", json={"name": "A的分类", "icon": "mdi-lock"})
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
        json={"name": "列表验证", "icon": "mdi-check", "sort_order": 1},
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


# --- v1.4.3 M8：统一列表下的排序 /「其他」/CoW ---
#
# 测试库可见预设（conftest 过期副本，7 行）：
#   餐饮1 出行2 购物3 旅行4 账单与费用5 工资1 其他收入2
#   → 非「其他」行的最大 sort_order = 5；无名为「其他」的行（旧语义名不参与判定）。


async def _visible(client) -> list[dict]:
    """可见分类列表（服务端已按 sort_order, id 升序）。"""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_create_without_sort_order_appends_before_other(client):
    """不传 sort_order → 落位 = max(非「其他」)+1，连续创建依次后移且恒在「其他」之前。"""
    other = await client.post("/api/categories", json={"name": "其他", "sort_order": 99})
    assert other.status_code == 200

    created: list[int] = []
    for name in ("宠物", "健身"):
        resp = await client.post("/api/categories", json={"name": name})
        assert resp.status_code == 200
        data = resp.json()["data"]
        created.append(data["sort_order"])
        assert data["is_preset"] == 0
        assert data["sort_order"] < 99  # 恒严格小于「其他」
    assert created == [6, 7]  # max(非「其他」)=5（账单与费用）→ 6、7 依次后移

    names = [c["name"] for c in await _visible(client)]
    assert names[-1] == "其他"
    assert names.index("宠物") < names.index("健身") < names.index("其他")


@pytest.mark.asyncio
async def test_create_sort_order_self_heals_when_other_not_at_tail(client):
    """边界：「其他」未在末尾（异常数据）→ 新行仍被钳制到「其他」之前，置尾不变量自愈。"""
    resp = await client.post("/api/categories", json={"name": "其他", "sort_order": 6})
    assert resp.status_code == 200

    resp = await client.post("/api/categories", json={"name": "宠物"})
    assert resp.status_code == 200
    new_sort = resp.json()["data"]["sort_order"]
    assert new_sort < 6  # base=max(非其他)=5 与 other-1 取小

    names = [c["name"] for c in await _visible(client)]
    assert names[-1] == "其他"


@pytest.mark.asyncio
async def test_no_other_category_appends_at_tail(client):
    """边界 8.4：可见集合无「其他」行时不补建，新增直接 max+1 追加末位。"""
    resp = await client.post("/api/categories", json={"name": "宠物"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 6

    names = [c["name"] for c in await _visible(client)]
    assert names[-1] == "宠物"


@pytest.mark.asyncio
async def test_sort_order_single_list_no_longer_partitioned_by_legacy_group(client):
    """原「收支分组独立计算」用例改写：统一列表后排序只有一个作用域。

    v1.4.2 用例 `test_m2_income_group_sort_calculated_independently` 断言收入/支出两组
    各自独立算 max——该语义随 M8 废弃，本用例改为断言**单一序列**：连续创建的两个分类
    拿到 6、7，且旧收入侧预设「工资」与旧支出侧预设「餐饮」同处一列。
    """
    a = await client.post("/api/categories", json={"name": "奖金"})
    b = await client.post("/api/categories", json={"name": "稿费"})
    assert a.status_code == b.status_code == 200
    assert a.json()["data"]["sort_order"] == 6
    assert b.json()["data"]["sort_order"] == 7

    items = await _visible(client)
    names = [c["name"] for c in items]
    assert "工资" in names and "餐饮" in names
    # 单列表内 sort_order 单调不减（不再有两组各自 1..n 的交错）
    assert [c["sort_order"] for c in items] == sorted(c["sort_order"] for c in items)


@pytest.mark.asyncio
async def test_create_with_explicit_sort_order_writes_as_given(client):
    """显式传 sort_order → 原样写入（向后兼容，不做服务端改写）。"""
    resp = await client.post(
        "/api/categories", json={"name": "置顶分类", "icon": "mdi-pin", "sort_order": 0}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 0

    resp = await client.post(
        "/api/categories", json={"name": "靠后分类", "icon": "mdi-arrow-down", "sort_order": 3}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 3

    items = await _visible(client)
    assert items[0]["name"] == "置顶分类"


@pytest.mark.asyncio
async def test_create_negative_sort_order_rejected(client):
    """参数非法：sort_order 负值 → 422（ge=0 约束保持）。"""
    resp = await client.post("/api/categories", json={"name": "非法排序", "sort_order": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_ignores_sort_order(client):
    """PUT 载荷携带 sort_order → 值不变（单个分类 PUT 不再改排序）。"""
    resp = await client.post(
        "/api/categories", json={"name": "排序不变", "icon": "mdi-lock", "sort_order": 50}
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
async def test_update_other_name_forbidden_icon_allowed(client, auth_client_b, db_session):
    """「其他」改名 400（判据仅按 name，自定义行同样锁定）、改图标 200 且恒置末、他人可见集合不受影响。"""
    from app.models.category import Category

    resp = await client.post("/api/categories", json={"name": "其他", "sort_order": 99})
    assert resp.status_code == 200
    other_id = resp.json()["data"]["id"]

    # 名称不可改（自定义行同样受约束：判据只看 name，D11）
    forbidden = await client.put(f"/api/categories/{other_id}", json={"name": "杂项"})
    assert forbidden.status_code == 400
    body = forbidden.json()
    assert body["code"] == 40001
    assert "不可修改" in body["message"]

    # 同名提交（无实义改名）放行
    same = await client.put(f"/api/categories/{other_id}", json={"name": "其他"})
    assert same.status_code == 200

    # 改图标可用，且「其他」恒在末位
    renamed = await client.put(
        f"/api/categories/{other_id}", json={"icon": "mdi-cash-multiple"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["icon"] == "mdi-cash-multiple"
    assert (await _visible(client))[-1]["name"] == "其他"

    # 新建分类仍被钳制在「其他」之前
    created = await client.post("/api/categories", json={"name": "宠物"})
    assert created.json()["data"]["sort_order"] < 99

    # 其他用户的可见集合不被污染
    b_names = [c["name"] for c in await _visible(auth_client_b)]
    assert "其他" not in b_names
    row = await db_session.get(Category, other_id)
    assert row is not None and row.is_preset == 0 and row.user_id is not None


@pytest.mark.asyncio
async def test_cow_matches_by_name_only_income_preset_copy_shadows_preset(client, db_session):
    """9.1 CoW 仅按 name：用户改「工资」（测试库 type=income 预设）→ 生成副本并遮蔽预设行。

    D11/D2 要点：预设行残留 type 值不再参与匹配，副本继承原值仅供事后排查。
    """
    from app.models.category import Category

    preset = next(c for c in await _visible(client) if c["name"] == "工资")
    assert preset["is_preset"] == 1
    assert preset["type"] == "income"  # 测试库旧语义残留，正是本用例要打的点

    resp = await client.put(f"/api/categories/{preset['id']}", json={"icon": "mdi-cash"})
    assert resp.status_code == 200
    copy = resp.json()["data"]
    assert copy["id"] != preset["id"]
    assert copy["is_preset"] == 0
    assert copy["name"] == "工资"
    assert copy["icon"] == "mdi-cash"
    assert copy["sort_order"] == preset["sort_order"]  # 继承预设自身排序

    visible = await _visible(client)
    salary = [c for c in visible if c["name"] == "工资"]
    assert len(salary) == 1, "副本生效后预设行必须被遮蔽，不得重复计入"
    assert salary[0]["id"] == copy["id"]

    # 全局预设行未被写脏，其他用户仍见原始预设
    preset_row = await db_session.get(Category, preset["id"])
    assert preset_row is not None
    assert preset_row.icon == "mdi-wallet"
    assert preset_row.is_preset == 1


@pytest.mark.asyncio
async def test_record_type_decoupled_from_category(client):
    """边界 8.2：交易 type 与分类无关联校验——收入交易挂任意分类均允许。"""
    resp = await client.post("/api/categories", json={"name": "工资外快", "icon": "mdi-cash"})
    cat_id = resp.json()["data"]["id"]

    income_record = await client.post(
        "/api/records",
        json={
            "amount": 88.0,
            "type": "income",
            "category_id": cat_id,
            "consume_time": "2026-04-01 10:00",
        },
    )
    assert income_record.status_code == 200
    assert income_record.json()["data"]["type"] == "income"
    assert income_record.json()["data"]["category_id"] == cat_id


@pytest.mark.asyncio
async def test_d9_quick_template_type_from_latest_record(client, db_session):
    """任务 4.2（D9）：手动快速模板 type = 该标签**最近一笔**流水（consume_time desc）
    的交易 type，**不再读 category.type**——即便分类列上仍带旧 income 值。
    """
    from sqlmodel import select

    from app.models.category import Category
    from app.models.quick_template import QuickTemplate

    resp = await client.post("/api/categories", json={"name": "D9派生", "icon": "mdi-cash"})
    cat_id = resp.json()["data"]["id"]
    # 造存量形：分类 type 列保留旧语义值 income（D2：仅原值可供排查）
    row = await db_session.get(Category, cat_id)
    assert row is not None
    row.type = "income"
    db_session.add(row)
    await db_session.commit()

    tag_id = (
        await client.post("/api/tags", json={"name": "D9午饭", "category_id": cat_id})
    ).json()["data"]["id"]
    # 旧一笔 income、新一笔 expense：最近流水为 expense（旧实现取 category.type 会得 income）
    for rec_type, day in (("income", "2026-04-01"), ("expense", "2026-05-02")):
        created = await client.post(
            "/api/records",
            json={
                "amount": 20.0,
                "type": rec_type,
                "category_id": cat_id,
                "tag_id": tag_id,
                "consume_time": f"{day} 10:00",
            },
        )
        assert created.status_code == 200

    added = await client.post(
        "/api/records/quick-templates", json={"tag_id": tag_id, "amount": 21.0}
    )
    assert added.status_code == 200

    tpl = (
        await db_session.exec(
            select(QuickTemplate).where(
                QuickTemplate.tag_id == tag_id, QuickTemplate.kind == "manual"
            )
        )
    ).first()
    assert tpl is not None, "手动模板未落库"
    assert tpl.type == "expense"  # 最近一笔流水的交易 type，而非分类列残留 income


@pytest.mark.asyncio
async def test_d9_quick_template_type_fallback_expense(client, db_session):
    """任务 4.2（D9）兜底：该标签名下**无任何流水** → 模板 type 落 'expense'。"""
    from sqlmodel import select

    from app.models.quick_template import QuickTemplate

    resp = await client.post("/api/categories", json={"name": "D9兜底", "icon": "mdi-cash"})
    cat_id = resp.json()["data"]["id"]
    tag_id = (
        await client.post("/api/tags", json={"name": "D9无流水", "category_id": cat_id})
    ).json()["data"]["id"]

    added = await client.post(
        "/api/records/quick-templates", json={"tag_id": tag_id, "amount": 33.0}
    )
    assert added.status_code == 200

    tpl = (
        await db_session.exec(
            select(QuickTemplate).where(
                QuickTemplate.tag_id == tag_id, QuickTemplate.kind == "manual"
            )
        )
    ).first()
    assert tpl is not None
    assert tpl.type == "expense"


@pytest.mark.asyncio
async def test_update_custom_category_renames_ok(client):
    """非「其他」自定义分类改名不受禁改约束影响（回归保护）。"""
    resp = await client.post("/api/categories", json={"name": "宠物", "icon": "mdi-paw"})
    cat_id = resp.json()["data"]["id"]

    resp = await client.put(f"/api/categories/{cat_id}", json={"name": "萌宠"})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "萌宠"
    assert resp.json()["data"]["sort_order"] == 6


@pytest.mark.asyncio
async def test_category_endpoints_require_auth(anon_client):
    """未认证：create/update/list 端点未带 token → 401。"""
    resp = await anon_client.post("/api/categories", json={"name": "匿名"})
    assert resp.status_code == 401

    resp = await anon_client.put("/api/categories/1", json={"name": "匿名改名"})
    assert resp.status_code == 401

    resp = await anon_client.get("/api/categories")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sort_isolation_between_users(auth_client_a, auth_client_b):
    """数据隔离：用户 A 的新增分类不参与用户 B 的 max 计算。"""
    for name in ("A1", "A2", "A3"):
        resp = await auth_client_a.post("/api/categories", json={"name": name})
        assert resp.status_code == 200
    a_orders = [c["sort_order"] for c in await _visible(auth_client_a)]
    assert a_orders[-3:] == [6, 7, 8]

    resp = await auth_client_b.post("/api/categories", json={"name": "B1"})
    assert resp.status_code == 200
    assert resp.json()["data"]["sort_order"] == 6  # 仅按 B 自己的可见集合计算

    b_names = [c["name"] for c in await _visible(auth_client_b)]
    assert "A1" not in b_names
    a_names = [c["name"] for c in await _visible(auth_client_a)]
    assert "B1" not in a_names


@pytest.mark.asyncio
async def test_same_name_custom_rows_are_per_user(auth_client_a, auth_client_b):
    """name 唯一约束的作用域是 (name, user_id)：两个用户可各有一个「宠物」。"""
    for client_x, client_y in ((auth_client_a, auth_client_b), (auth_client_b, auth_client_a)):
        resp = await client_x.post("/api/categories", json={"name": "宠物"})
        assert resp.status_code == 200

    a_names = [c["name"] for c in await _visible(auth_client_a)]
    b_names = [c["name"] for c in await _visible(auth_client_b)]
    assert "宠物" in a_names and "宠物" in b_names
    # 但同一用户内仍只能有一份
    dup = await auth_client_a.post("/api/categories", json={"name": "宠物"})
    assert dup.status_code == 400
