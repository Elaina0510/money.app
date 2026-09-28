"""Tests for tag API."""

import re

import pytest
from httpx import AsyncClient

from app.models.tag import Tag


async def _create_tags(client: AsyncClient, names: list[str]) -> list[dict]:
    """批量建标签，返回创建响应体列表（顺序即 id 升序）。"""
    created = []
    for name in names:
        resp = await client.post("/api/tags", json={"name": name})
        assert resp.status_code == 200
        created.append(resp.json()["data"])
    return created


@pytest.mark.asyncio
async def test_get_tags(client):
    """Test fetching all tags."""
    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_create_tag(client):
    """Test creating a new tag."""
    resp = await client.post("/api/tags", json={"name": "测试标签"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试标签"


@pytest.mark.asyncio
async def test_update_tag(client):
    """Test updating a tag."""
    resp = await client.post("/api/tags", json={"name": "旧标签"})
    tag_id = resp.json()["data"]["id"]

    resp = await client.put(f"/api/tags/{tag_id}", json={"name": "新标签"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["name"] == "新标签"


@pytest.mark.asyncio
async def test_delete_tag(client):
    """Test deleting a tag."""
    resp = await client.post("/api/tags", json={"name": "待删除标签"})
    tag_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_tag(client):
    """Test deleting a non-existent tag."""
    resp = await client.delete("/api/tags/99999")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 40002


# ── M5：解除 20 条上限（裸数组契约不变）+ GET /api/tags/paged ──────────────

M5_NAMES = [f"标签{i:02d}" for i in range(1, 26)]  # 25 条，跨过旧 limit(20)


@pytest.mark.asyncio
async def test_m5_get_tags_returns_all_25_without_limit(client):
    """用例 6.1.1: 造 25 条 → GET /api/tags 返回 25（去上限回归），裸数组契约不变。"""
    await _create_tags(client, M5_NAMES)

    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert isinstance(data, list)  # 契约不变：仍是裸数组，未包成 {items,total}
    assert len(data) == 25
    assert [t["name"] for t in data] == M5_NAMES  # 按 id 升序，与创建序一致
    # 单条结构不变：仍为 TagResponse dump 的四个字段
    assert set(data[0]) == {"id", "name", "category_id", "created_at"}


@pytest.mark.asyncio
async def test_m5_get_tags_search_matches_whole_library(client):
    """用例 6.1.1: 带 q 的匹配范围为全库（25 条同名前缀）而非截断前 20。"""
    await _create_tags(client, [f"检索{i:02d}" for i in range(1, 26)])

    resp = await client.get("/api/tags", params={"q": "检索"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 25

    # 精确到个别名仍只匹配该条（search 语义未变）
    resp = await client.get("/api/tags", params={"q": "检索07"})
    assert [t["name"] for t in resp.json()["data"]] == ["检索07"]


@pytest.mark.asyncio
async def test_m5_paged_default_returns_20_of_25(client):
    """用例 6.1.2: 默认 page/page_size → items 20 + total 25 + 页码回显。"""
    created = await _create_tags(client, M5_NAMES)

    resp = await client.get("/api/tags/paged")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 25
    assert len(data["items"]) == 20
    assert [t["id"] for t in data["items"]] == [t["id"] for t in created[:20]]
    # items 结构与裸数组端点同源（TagResponse dump）
    assert set(data["items"][0]) == {"id", "name", "category_id", "created_at"}


@pytest.mark.asyncio
async def test_m5_paged_second_page_keeps_id_order(client):
    """用例 6.1.2: page=2 → 余 5 条，且与全量按 id 排序拼接一致、无重复无缺失。"""
    created = await _create_tags(client, M5_NAMES)

    resp = await client.get("/api/tags/paged", params={"page": 2})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 2
    assert data["total"] == 25
    assert [t["id"] for t in data["items"]] == [t["id"] for t in created[20:]]

    first = (await client.get("/api/tags/paged", params={"page": 1})).json()["data"]
    merged = [t["id"] for t in first["items"]] + [t["id"] for t in data["items"]]
    assert merged == [t["id"] for t in created]


@pytest.mark.asyncio
async def test_m5_paged_with_search_counts_matched_total(client):
    """用例 6.1.3: q + paged → total 为匹配总数，分页在匹配集内进行。"""
    await _create_tags(client, [f"日常{i:02d}" for i in range(1, 8)])  # 7 条
    await _create_tags(client, [f"出行{i:02d}" for i in range(1, 6)])  # 5 条

    resp = await client.get("/api/tags/paged", params={"q": "日常"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 7
    assert len(data["items"]) == 7
    assert all(t["name"].startswith("日常") for t in data["items"])

    # 匹配集内 page_size=3 → 第 2 页 3 条，total 仍为匹配总数
    resp = await client.get("/api/tags/paged", params={"q": "日常", "page": 2, "page_size": 3})
    data = resp.json()["data"]
    assert data["total"] == 7 and data["page"] == 2 and len(data["items"]) == 3

    # 无匹配 → items 空、total 0（非全库数）
    resp = await client.get("/api/tags/paged", params={"q": "不存在的前缀"})
    data = resp.json()["data"]
    assert data["total"] == 0 and data["items"] == []


@pytest.mark.asyncio
async def test_m5_paged_page_beyond_last_returns_empty_keeps_total(client):
    """用例 6.1.3 边界: page 越界 → items 空数组、total 不减（前端据 hasMore 隐藏按钮）。"""
    await _create_tags(client, M5_NAMES)

    resp = await client.get("/api/tags/paged", params={"page": 99})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 25
    assert data["page"] == 99


@pytest.mark.asyncio
async def test_m5_paged_rejects_invalid_page_params(client):
    """参数非法四件套: page/page_size 越界（0、负数、>100）→ 422，且不落库不改数据。"""
    await _create_tags(client, ["边界标签"])

    for params in ({"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": -5}, {"page_size": 101}):
        resp = await client.get("/api/tags/paged", params=params)
        assert resp.status_code == 422, f"参数 {params} 应被 Query 约束拒绝"

    # 合法边界值 page_size=1 / 100 正常返回
    assert (await client.get("/api/tags/paged", params={"page_size": 1})).status_code == 200
    assert (await client.get("/api/tags/paged", params={"page_size": 100})).status_code == 200
    assert (await client.get("/api/tags/paged", params={"page": 1})).status_code == 200


@pytest.mark.asyncio
async def test_m5_paged_route_not_shadowed_by_tag_id(client):
    """§7.2 路由顺序回归: /paged 必须先于 /{tag_id} 声明，错位时 "paged" 被 int 抢匹配 → 422。"""
    resp = await client.get("/api/tags/paged")
    assert resp.status_code == 200, "被 /{tag_id} 抢匹配时会返回 422"
    assert resp.json()["code"] == 0
    # 对照：真整数路径仍走详情端点（说明两条路由各自可达）
    created = await _create_tags(client, ["详情可达"])
    detail = await client.get(f"/api/tags/{created[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["name"] == "详情可达"


@pytest.mark.asyncio
async def test_m5_paged_excludes_soft_deleted_from_total(client):
    """用例 6.1.4: 软删标签既不出现在 items，也不计入 total。"""
    created = await _create_tags(client, M5_NAMES)
    victim = created[0]["id"]

    resp = await client.delete(f"/api/tags/{victim}")
    assert resp.status_code == 200

    data = (await client.get("/api/tags/paged", params={"page_size": 100})).json()["data"]
    assert data["total"] == 24
    assert victim not in [t["id"] for t in data["items"]]
    # 裸数组端点同口径（软删不计、上限已解除）
    assert len((await client.get("/api/tags")).json()["data"]) == 24


@pytest.mark.asyncio
async def test_m5_paged_isolates_user_data(auth_client_a, auth_client_b):
    """用例 6.1.4 数据隔离: A 的 25 条对 B 完全不可见，两端点均按 user_id 收窄。"""
    await _create_tags(auth_client_a, M5_NAMES)
    await _create_tags(auth_client_b, ["B独有标签"])

    a_data = (await auth_client_a.get("/api/tags/paged", params={"page_size": 100})).json()["data"]
    assert a_data["total"] == 25
    assert all(t["name"].startswith("标签") for t in a_data["items"])

    b_data = (await auth_client_b.get("/api/tags/paged", params={"page_size": 100})).json()["data"]
    assert b_data["total"] == 1
    assert [t["name"] for t in b_data["items"]] == ["B独有标签"]
    b_list = (await auth_client_b.get("/api/tags")).json()["data"]
    assert len(b_list) == 1 and b_list[0]["name"] == "B独有标签"


@pytest.mark.asyncio
async def test_m5_paged_requires_auth(anon_client):
    """用例 6.1.4 未认证: 无 token 访问 /paged → 401。"""
    resp = await anon_client.get("/api/tags/paged")
    assert resp.status_code == 401


# ── v1.4.4 M1：标签批量治理（POST /tags/batch-delete + POST /tags/clear-all）──
# 设计 §2.5 后端 6 条逐字对应 §7.1–§7.6；§7.2 原子性与 §7.5 全局行红线为必在场断言。
# 口径：软删（非物删）、单事务整批原子、**不写数据回溯**；归属严于单删——
# 刻意不开 `user_id IS NULL` 全局行口子，跨用户/全局 id 一律计入「不存在」→ 整单 400。
# §7.6 的 `tag=null` 依赖 M0 已合入的 `record_service._enrich_record` 收口（软删=对用户不存在）。

M1_NAMES = [f"批量{i:02d}" for i in range(1, 6)]  # 5 条：删 3 留 2
GHOST_MSG = "部分标签不存在或已被删除，请刷新后重试"


async def _mk_category(client: AsyncClient, name: str) -> int:
    """建一个用户分类（§7.6 记账所需），返回 id。"""
    resp = await client.post("/api/categories", json={"name": name, "icon": "mdi-food"})
    assert resp.status_code == 200
    return int(resp.json()["data"]["id"])


async def _mk_record(client: AsyncClient, category_id: int, tag_id: int, note: str) -> dict:
    """记一笔挂标签的账单，返回创建响应体（与列表同源经 `_enrich_record` 富化）。"""
    resp = await client.post(
        "/api/records",
        json={
            "amount": 12.5,
            "type": "expense",
            "category_id": category_id,
            "tag_id": tag_id,
            "consume_time": "2024-01-15 12:00",
            "note": note,
        },
    )
    assert resp.status_code == 200
    return resp.json()["data"]


async def _list_records(client: AsyncClient) -> list[dict]:
    resp = await client.get("/api/records", params={"page": 1, "page_size": 100})
    assert resp.status_code == 200
    return resp.json()["data"]["items"]


async def _live_tag_ids(client: AsyncClient) -> list[int]:
    """当前用户未软删标签 id（软删收口口径下，列表端点即「对用户存在」的集合）。"""
    return [t["id"] for t in (await client.get("/api/tags")).json()["data"]]


@pytest.mark.asyncio
async def test_m1_7_1_batch_delete_three_of_five_keeps_rest(client, db_session):
    """用例 7.1: 批量删 3 全命中 → 200、deleted_count=3、三行 deleted_at 非空（软删非物删）、
    其余标签不受影响；message 逐字「已删除 3 个标签」，时间格式沿既有单删手法。
    """
    created = await _create_tags(client, M1_NAMES)
    victims = [t["id"] for t in created[:3]]
    kept = [t["id"] for t in created[3:]]

    resp = await client.post("/api/tags/batch-delete", json={"ids": victims})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "已删除 3 个标签"
    assert body["data"] == {"deleted_count": 3}

    for tid in victims:
        tag = await db_session.get(Tag, tid)
        assert tag is not None, "批量接口为软删，行不应被物理删除"
        assert tag.deleted_at is not None
        assert tag.name  # 行内容保留（备份语义仍可见）
    # 软删时间格式与既有单删一致（%Y-%m-%d %H:%M:%S）
    first_victim = await db_session.get(Tag, victims[0])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", first_victim.deleted_at or "")

    # 其余标签不受影响（列表端点即剩余两条，id 与顺序保持）
    assert await _live_tag_ids(client) == kept


@pytest.mark.asyncio
async def test_m1_7_2_batch_delete_ghost_id_fails_whole_batch_atomically(client, db_session):
    """用例 7.2（原子性必在场）: ids 含一个不存在 id → 400 中文 message、
    **零行被软删**——同批内的合法 id 也一并不落删除。
    """
    created = await _create_tags(client, ["幽灵批一", "幽灵批二"])
    valid_ids = [t["id"] for t in created]
    payload = [*valid_ids, 999_999]  # 混入一个不存在的 id

    resp = await client.post("/api/tags/batch-delete", json={"ids": payload})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert body["message"] == GHOST_MSG

    for tid in valid_ids:
        tag = await db_session.get(Tag, tid)
        assert tag.deleted_at is None, f"整单失败后 id={tid} 不应被落删除（原子性破坏）"
    assert await _live_tag_ids(client) == valid_ids

    # 并发幽灵（设计 §2.4）：他端已软删的行同样计入「不存在」→ 整单 400，零行新落删除
    resp = await client.delete(f"/api/tags/{valid_ids[0]}")
    assert resp.status_code == 200
    resp = await client.post("/api/tags/batch-delete", json={"ids": valid_ids})
    assert resp.status_code == 400
    assert resp.json()["message"] == GHOST_MSG
    db_session.expire_all()  # 跨会话读回真值，不吃 identity map 缓存
    assert (await db_session.get(Tag, valid_ids[1])).deleted_at is None


@pytest.mark.asyncio
async def test_m1_7_3_batch_delete_rejects_other_users_tag(auth_client_a, auth_client_b, db_session):
    """用例 7.3: ids 含他人标签 id → 同 7.2 整单 400；
    跨用户 id 计入「不存在」，且他人标签零被触碰（归属口径严于单删）。
    """
    a_created = await _create_tags(auth_client_a, ["甲独占标签"])
    b_created = await _create_tags(auth_client_b, ["乙自有标签"])
    a_id = a_created[0]["id"]
    b_id = b_created[0]["id"]

    resp = await auth_client_b.post("/api/tags/batch-delete", json={"ids": [b_id, a_id]})
    assert resp.status_code == 400
    assert resp.json()["message"] == GHOST_MSG

    assert (await db_session.get(Tag, a_id)).deleted_at is None, "他人标签不得被触碰"
    assert (await db_session.get(Tag, b_id)).deleted_at is None, "整单失败：自己的也不落删除"
    assert await _live_tag_ids(auth_client_a) == [a_id]
    assert await _live_tag_ids(auth_client_b) == [b_id]


@pytest.mark.asyncio
async def test_m1_7_4_clear_all_soft_deletes_everything_then_idempotent(client, db_session):
    """用例 7.4: clear-all 有标签 → 全软删、计数正确；再点一次 → 200 + deleted_count=0（幂等，
    message 为「标签已全部清空」）。
    """
    created = await _create_tags(client, M1_NAMES)

    resp = await client.post("/api/tags/clear-all")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "已清空 5 个标签"
    assert body["data"] == {"deleted_count": 5}

    for tag in created:
        row = await db_session.get(Tag, tag["id"])
        assert row.deleted_at is not None, "清空为软删，逐行 deleted_at 应置值"
    assert await _live_tag_ids(client) == []

    resp = await client.post("/api/tags/clear-all")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == {"deleted_count": 0}
    assert body["message"] == "标签已全部清空"


@pytest.mark.asyncio
async def test_m1_7_5_clear_all_and_batch_delete_never_touch_global_rows(client, db_session):
    """用例 7.5（红线断言）: 全局预设标签行（user_id IS NULL）不被两个批量接口写脏——
    clear-all 全软删本人标签后全局行 deleted_at 仍为 None；
    batch-delete 把全局 id 计入「不存在」→ 整单 400，全局行依旧未被写。
    """
    # 直插 seed 一条全局标签行（沿 M0 §4.3 建法，不经任何写接口）
    global_tag = Tag(name="全局预设标签M1")
    db_session.add(global_tag)
    await db_session.commit()
    await db_session.refresh(global_tag)
    assert global_tag.user_id is None and global_tag.deleted_at is None

    created = await _create_tags(client, ["本人标签M1"])

    resp = await client.post("/api/tags/clear-all")
    assert resp.status_code == 200
    assert resp.json()["data"] == {"deleted_count": 1}  # 只算本人的，全局行不在范围内
    assert (await db_session.get(Tag, global_tag.id)).deleted_at is None
    assert (await db_session.get(Tag, created[0]["id"])).deleted_at is not None

    # 全局 id 混入 batch-delete → 计入「不存在」整单 400，且全局行零写入
    resp = await client.post("/api/tags/batch-delete", json={"ids": [global_tag.id]})
    assert resp.status_code == 400
    assert resp.json()["message"] == GHOST_MSG
    untouched = await db_session.get(Tag, global_tag.id)
    assert untouched.deleted_at is None, "批量接口刻意不开 user_id IS NULL 全局行口子"


@pytest.mark.asyncio
async def test_m1_7_6_batch_deleted_tag_disappears_from_records(client):
    """用例 7.6（M0→M1 软删口径联动，验 REQ-001「标记同步移除」）:
    账单挂标签 T → batch-delete T → `GET /api/records` 该行 `tag === null`；
    未选标签 U 的行标记不受影响（防过度过滤回归锚）。
    """
    cat_id = await _mk_category(client, "M1联动分类")
    created = await _create_tags(client, ["联动标签T", "保留标签U"])
    tag_t = created[0]["id"]
    tag_u = created[1]["id"]

    rec_t = await _mk_record(client, cat_id, tag_t, "M1联动账单")
    await _mk_record(client, cat_id, tag_u, "M1保留账单")

    resp = await client.post("/api/tags/batch-delete", json={"ids": [tag_t]})
    assert resp.status_code == 200
    assert resp.json()["data"] == {"deleted_count": 1}

    items = await _list_records(client)
    row_t = next(r for r in items if r["id"] == rec_t["id"])
    assert row_t["tag"] is None, "软删标签经 M0 收口即对用户不存在"
    row_u = next(r for r in items if r["note"] == "M1保留账单")
    assert row_u["tag"] is not None and row_u["tag"]["name"] == "保留标签U"
