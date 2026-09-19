"""Tests for tag API."""

import pytest
from httpx import AsyncClient


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
