"""Tests for record API."""

import importlib.util
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlmodel import SQLModel, func, select

from app.models.quick_template import QuickTemplate
from app.models.user import User
from app.services.export_service import export_sql


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


# ---------------------------------------------------------------------------
# M6: 快速记账删除模板修复（自动模板按签名忽略 + quick_templates.kind）
# ---------------------------------------------------------------------------

AUTO_URL = "/api/records/quick-templates/auto"


async def _m6_tag(client, category_id: int, name: str = "午餐") -> int:
    """建标签并返回 id。"""
    resp = await client.post("/api/tags", json={"name": name, "category_id": category_id})
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


async def _m6_category(client, name: str) -> int:
    """建支出分类并返回 id（跨用户用例各自建，保证 user_id 隔离真实生效）。"""
    resp = await client.post(
        "/api/categories",
        json={"name": name, "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


async def _m6_records(client, category_id: int, tag_id: int, amount: float, times: int = 2) -> None:
    """记 times 笔同标签同类型同金额账单（自动模板按 (tag,type,amount) 聚合需 count>=2）。"""
    for _ in range(times):
        resp = await client.post(
            "/api/records",
            json={
                "amount": amount,
                "type": "expense",
                "category_id": category_id,
                "tag_id": tag_id,
                "consume_time": "2026-06-01 12:00",
            },
        )
        assert resp.status_code == 200


async def _m6_list(client) -> list[dict]:
    """取快速记账模板列表（自动 + 手动）。"""
    resp = await client.get("/api/records/quick-templates")
    assert resp.status_code == 200
    return resp.json()["data"]


def _m6_sig(items: list[dict]) -> set[tuple[str, float]]:
    """列表 → {(source, 分单位金额)}，避免断言里出现浮点 ==。"""
    return {(t["source"], int(round(float(t["amount"]) * 100))) for t in items}


async def _m6_db_rows(db_session, tag_id: int) -> list[tuple[int, str, float]]:
    """ORM 直读 quick_templates → [(id, kind, amount)]（忽略行只在库层可见，故按表断言）。"""
    rows = (
        await db_session.exec(
            select(QuickTemplate)
            .where(QuickTemplate.tag_id == tag_id)
            .order_by(QuickTemplate.id)
        )
    ).all()
    return [(r.id, r.kind, float(r.amount)) for r in rows]


async def _m6_uid(db_session) -> int:
    """client fixture 预置用户（clientuser）的 id。"""
    user = (await db_session.exec(select(User).where(User.username == "clientuser"))).first()
    assert user is not None and user.id is not None
    return user.id


@pytest.mark.asyncio
async def test_m6_ignore_auto_template_suppresses_permanently(client, expense_category_id):
    """用例 7.2.1: 忽略签名 → 200 + 列表即时无该自动项 + 追加同签名账单仍不复活（永久抑制）。"""
    tag_id = await _m6_tag(client, expense_category_id)
    await _m6_records(client, expense_category_id, tag_id, 25.0)

    items = await _m6_list(client)
    assert _m6_sig(items) == {("auto", 2500)}
    assert "id" not in items[0]  # 自动项无 id（现状口径，响应结构不变）

    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "自动模板已忽略"

    assert _m6_sig(await _m6_list(client)) == set()

    # 继续记同标签同金额同类型账单：count 增长但该签名永久不再自动出现
    await _m6_records(client, expense_category_id, tag_id, 25.0, times=2)
    assert _m6_sig(await _m6_list(client)) == set()


@pytest.mark.asyncio
async def test_m6_ignore_signature_covers_decimal_and_whole_yuan(client, expense_category_id):
    """用例 7.2.2: 小数 12.34 与整元 25 两类签名均可匹配；同 tag+type 不同金额不受牵连。"""
    tag_id = await _m6_tag(client, expense_category_id)
    await _m6_records(client, expense_category_id, tag_id, 12.34)
    await _m6_records(client, expense_category_id, tag_id, 25.0)

    assert _m6_sig(await _m6_list(client)) == {("auto", 1234), ("auto", 2500)}

    # 小数值（REAL 存储有浮点表示误差）按分换算精确命中，整元值不被牵连
    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 1234}
    )
    assert resp.status_code == 200
    assert _m6_sig(await _m6_list(client)) == {("auto", 2500)}

    # 整元值同样命中（SQLite 整元值可能被存为 INTEGER 的口径回归）
    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 200
    assert _m6_sig(await _m6_list(client)) == set()


@pytest.mark.asyncio
async def test_m6_ignore_deletes_same_signature_manual_row(client, expense_category_id, db_session):
    """用例 7.2.3 + §6.5 边界: 同签名手动行随删；其他签名手动/自动项不受影响。"""
    tag_id = await _m6_tag(client, expense_category_id)
    await _m6_records(client, expense_category_id, tag_id, 25.0)
    # 同签名手动模板（现状被 seen_keys 分签名去重隐藏，只在库中可见）
    same = await client.post(
        "/api/records/quick-templates", json={"tag_id": tag_id, "amount": 25.0}
    )
    assert same.status_code == 200
    before = await _m6_db_rows(db_session, tag_id)
    same_id = [rid for rid, kind, amt in before if kind == "manual" and int(round(amt * 100)) == 2500]
    assert len(same_id) == 1
    # 另一签名手动模板（正常展示）
    other = await client.post(
        "/api/records/quick-templates", json={"tag_id": tag_id, "amount": 30.0}
    )
    assert other.status_code == 200

    items = await _m6_list(client)
    assert _m6_sig(items) == {("auto", 2500), ("manual", 3000)}

    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 200

    items = await _m6_list(client)
    assert _m6_sig(items) == {("manual", 3000)}

    rows = await _m6_db_rows(db_session, tag_id)
    kinds = [(k, a) for _rid, k, a in rows]
    # 忽略行仅一行、category_id 不纳入签名；同签名手动行已删；异签名手动行留存
    assert kinds.count(("auto_ignored", 25.0)) == 1
    assert ("manual", 25.0) not in kinds
    assert ("manual", 30.0) in kinds
    assert same_id[0] not in {rid for rid, _k, _a in rows}


@pytest.mark.asyncio
async def test_m6_ignore_matches_integer_stored_whole_yuan_manual_row(
    client, expense_category_id, db_session
):
    """用例 7.2.2 补充: 手动行金额以整数字面量写入（INTEGER 存储风险）仍按分签名精确命中。"""
    tag_id = await _m6_tag(client, expense_category_id)
    uid = await _m6_uid(db_session)
    await db_session.exec(
        text(
            "INSERT INTO quick_templates (user_id, tag_id, category_id, type, amount, kind, "
            "created_at) VALUES (:u, :t, NULL, 'expense', 25, 'manual', '2026-06-01 12:00:00')"
        ).bindparams(u=uid, t=tag_id)
    )
    await db_session.commit()

    stored = await _m6_db_rows(db_session, tag_id)
    assert [k for _rid, k, a in stored if int(round(a * 100)) == 2500] == ["manual"]

    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 200

    after = await _m6_db_rows(db_session, tag_id)
    assert [k for _rid, k, a in after if int(round(a * 100)) == 2500] == ["auto_ignored"]
    assert _m6_sig(await _m6_list(client)) == set()


@pytest.mark.asyncio
async def test_m6_ignore_is_idempotent(client, expense_category_id, db_session):
    """用例 7.2.4: 连删两次同签名 → 均 200，库中忽略行只有一行。"""
    tag_id = await _m6_tag(client, expense_category_id)
    await _m6_records(client, expense_category_id, tag_id, 25.0)
    params = {"tag_id": tag_id, "type": "expense", "amount_cents": 2500}

    for _ in range(2):
        resp = await client.delete(AUTO_URL, params=params)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    rows = await _m6_db_rows(db_session, tag_id)
    assert [k for _rid, k, _a in rows] == ["auto_ignored"]

    # 第三次仍 200 且不产生新行
    assert (await client.delete(AUTO_URL, params=params)).status_code == 200
    assert [k for _rid, k, _a in await _m6_db_rows(db_session, tag_id)] == ["auto_ignored"]


@pytest.mark.asyncio
async def test_m6_auto_route_not_shadowed_by_template_id(client, expense_category_id):
    """用例 7.2.5: /quick-templates/auto 返回 200 非 422；原 DELETE /{template_id} 行为不变。"""
    tag_id = await _m6_tag(client, expense_category_id)
    resp = await client.post(
        "/api/records/quick-templates", json={"tag_id": tag_id, "amount": 30.0}
    )
    assert resp.status_code == 200
    items = await _m6_list(client)
    manual_id = [t for t in items if t["source"] == "manual"][0]["id"]

    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 1234}
    )
    assert resp.status_code == 200, "错位声明会被 int 路径参数抢匹配 → 422"

    # 原手动模板删除端点行为不变：删除 200，重复删除走业务 NOT_FOUND
    resp = await client.delete(f"/api/records/quick-templates/{manual_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "模板删除成功"
    resp = await client.delete(f"/api/records/quick-templates/{manual_id}")
    assert resp.json()["code"] == 40002


@pytest.mark.asyncio
async def test_m6_ignore_rejects_invalid_params(client, expense_category_id):
    """四件套·参数非法: tag_id/type/amount_cents 越界或非法值 → 422；合法值仍 200。"""
    tag_id = await _m6_tag(client, expense_category_id)
    bad_cases = [
        {"tag_id": tag_id, "type": "expense", "amount_cents": 0},
        {"tag_id": tag_id, "type": "expense", "amount_cents": -2500},
        {"tag_id": tag_id, "type": "transfer", "amount_cents": 2500},
        {"tag_id": tag_id, "amount_cents": 2500},
        {"type": "expense", "amount_cents": 2500},
        {"tag_id": 0, "type": "expense", "amount_cents": 2500},
        {"tag_id": tag_id, "type": "expense"},
    ]
    for params in bad_cases:
        resp = await client.delete(AUTO_URL, params=params)
        assert resp.status_code == 422, params

    assert (
        await client.delete(
            AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_m6_ignore_returns_not_found_for_missing_or_soft_deleted_tag(
    client, expense_category_id
):
    """四件套·数据不存在: 不存在的 tag_id 与已软删标签 → 业务 NOT_FOUND（服务返回 False）。"""
    resp = await client.delete(
        AUTO_URL, params={"tag_id": 999999, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    assert resp.json()["message"] == "标签不存在"

    tag_id = await _m6_tag(client, expense_category_id, name="将被删")
    assert (await client.delete(f"/api/tags/{tag_id}")).status_code == 200
    resp = await client.delete(
        AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 40002


@pytest.mark.asyncio
async def test_m6_ignore_requires_auth(anon_client):
    """四件套·未认证: 无 token 访问 → 401。"""
    resp = await anon_client.delete(
        AUTO_URL, params={"tag_id": 1, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_m6_ignore_signature_isolated_between_users(auth_client_a, auth_client_b):
    """用例 7.2.6: 跨用户签名隔离——A 的忽略（含借 B 的 tag_id 越权尝试）不影响 B 的同签名自动项。"""
    cat_a, cat_b = await _m6_category(auth_client_a, "A分类"), await _m6_category(auth_client_b, "B分类")
    tag_a = await _m6_tag(auth_client_a, cat_a, "A标签")
    tag_b = await _m6_tag(auth_client_b, cat_b, "B标签")
    await _m6_records(auth_client_a, cat_a, tag_a, 25.0)
    await _m6_records(auth_client_b, cat_b, tag_b, 25.0)

    # A 用 B 的 tag_id 发忽略请求：即使被接受也只落 A 名下，B 的自动项不受牵连
    resp = await auth_client_a.delete(
        AUTO_URL, params={"tag_id": tag_b, "type": "expense", "amount_cents": 2500}
    )
    assert resp.status_code == 200
    assert _m6_sig(await _m6_list(auth_client_b)) == {("auto", 2500)}

    # A 忽略自己的签名 → A 空、B 仍正常
    assert (
        await auth_client_a.delete(
            AUTO_URL, params={"tag_id": tag_a, "type": "expense", "amount_cents": 2500}
        )
    ).status_code == 200
    assert _m6_sig(await _m6_list(auth_client_a)) == set()
    assert _m6_sig(await _m6_list(auth_client_b)) == {("auto", 2500)}


@pytest.mark.asyncio
async def test_m6_ignored_rows_neither_in_list_nor_sql_export(
    client, expense_category_id, db_session
):
    """任务 1.4 隔离性核查: auto_ignored 行不混入 GET 列表，也不混入 SQL 备份出口。"""
    tag_id = await _m6_tag(client, expense_category_id)
    await _m6_records(client, expense_category_id, tag_id, 25.0)
    await client.post("/api/records/quick-templates", json={"tag_id": tag_id, "amount": 30.0})
    assert (
        await client.delete(
            AUTO_URL, params={"tag_id": tag_id, "type": "expense", "amount_cents": 2500}
        )
    ).status_code == 200

    items = await _m6_list(client)
    assert _m6_sig(items) == {("manual", 3000)}
    assert all(t.get("kind") is None for t in items)  # 响应结构不变（红线 3）

    uid = await _m6_uid(db_session)
    sql_bytes, _name = await export_sql(db_session, uid)
    sql_text = sql_bytes.decode("utf-8")
    inserts = [ln for ln in sql_text.splitlines() if ln.startswith("INSERT INTO quick_templates")]
    assert len(inserts) == 1, "忽略行不应进备份：导入侧会按手动模板建出幽灵行"
    assert "30.0" in inserts[0]


@pytest.mark.asyncio
async def test_m6_new_db_has_kind_column(db_session):
    """D4 前提: pytest 走 create_all 自带 kind 列，不依赖迁移脚本；旧代码路径默认 manual。"""
    table = SQLModel.metadata.tables["quick_templates"]
    assert "kind" in table.columns
    assert table.columns["kind"].nullable is False
    assert table.columns["kind"].default.arg == "manual"
    # 现网建表语句由 create_all 生成，列已存在（迁移脚本只服务旧库）
    assert (await db_session.exec(select(func.count(QuickTemplate.id)))).one() == 0


# ── 7.1.1 迁移脚本自测（临时旧表结构 SQLite） ────────────────────────────

MIGRATE_SCRIPT = Path(__file__).resolve().parents[1] / "migrate_to_v1.4.2.py"


def _load_migrate_module():
    """按文件路径加载 migrate_to_v1.4.2（文件名含点号，不能直接 import）。"""
    spec = importlib.util.spec_from_file_location("migrate_to_v1_4_2", MIGRATE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _legacy_db(path: Path) -> None:
    """造 v1.4.2 之前的旧表结构（无 kind 列）+ 两行手动模板。"""
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE quick_templates ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tag_id INTEGER, "
        "category_id INTEGER, type TEXT NOT NULL, amount REAL NOT NULL, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO quick_templates (user_id, tag_id, category_id, type, amount, created_at) "
        "VALUES (1, 1, 1, 'expense', 25.0, '2026-06-01 12:00:00')"
    )
    conn.execute(
        "INSERT INTO quick_templates (user_id, tag_id, category_id, type, amount, created_at) "
        "VALUES (1, 2, 1, 'income', 12.34, '2026-06-01 12:00:00')"
    )
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_m6_migration_adds_kind_column_and_is_idempotent(tmp_path, capsys):
    """用例 7.1.1: 旧库跑一次 → kind 列存在且旧行全 manual；重跑输出 SKIP 不报错。"""
    assert MIGRATE_SCRIPT.exists(), "migrate_to_v1.4.2.py 缺失"
    db_path = tmp_path / "legacy.db"
    _legacy_db(db_path)
    module = _load_migrate_module()

    rc = await module.migrate(["migrate_to_v1.4.2.py", db_path.as_posix()])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[SKIP]" not in out
    assert "[OK]" in out

    conn = sqlite3.connect(db_path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(quick_templates)")]
    kinds = [r[0] for r in conn.execute("SELECT kind FROM quick_templates ORDER BY id")]
    conn.close()
    assert "kind" in cols
    assert kinds == ["manual", "manual"]  # 旧行全部回填为 manual

    # 重跑幂等：列已存在 → SKIP，不报错、不重复加列、数据不变
    rc = await module.migrate(["migrate_to_v1.4.2.py", db_path.as_posix()])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[SKIP]" in out and "kind" in out
    conn = sqlite3.connect(db_path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(quick_templates)")]
    kinds = [r[0] for r in conn.execute("SELECT kind FROM quick_templates ORDER BY id")]
    conn.close()
    assert cols.count("kind") == 1
    assert kinds == ["manual", "manual"]


@pytest.mark.asyncio
async def test_m6_migration_skips_when_table_absent(tmp_path, capsys):
    """用例 7.1.1 补充: 新库无 quick_templates 表 → 输出 SKIP 且不报错（由应用 create_all 建表）。"""
    db_path = tmp_path / "fresh.db"
    sqlite3.connect(db_path).close()
    module = _load_migrate_module()

    rc = await module.migrate(["migrate_to_v1.4.2.py", db_path.as_posix()])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[SKIP]" in out and "quick_templates" in out
