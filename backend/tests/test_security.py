"""IDOR 与频率限制回归测试 (v1.4 安全加固)。"""

import io
import struct
import zlib

import pytest


def _make_png():
    """Create a minimal valid PNG file in memory."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    raw = b"\x00" + b"\xff\x00\x00"
    compressed = zlib.compress(raw)
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    idat_chunk = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)
    iend_crc = zlib.crc32(b"IEND")
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    return signature + ihdr_chunk + idat_chunk + iend_chunk


async def _create_record_for(client, category_name="默认分类"):
    resp = await client.post(
        "/api/categories",
        json={"name": category_name, "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await client.post(
        "/api/records",
        json={"amount": 100.0, "type": "expense", "category_id": cat_id, "consume_time": "2026-06-01 12:00"},
    )
    return resp.json()["data"]["id"], cat_id


@pytest.mark.asyncio
async def test_idor_get_other_user_record_404(auth_client_a, auth_client_b):
    """用户 B 读取用户 A 的记录 → 404(不泄露存在性)。"""
    record_id, _ = await _create_record_for(auth_client_a, "A分类")

    resp = await auth_client_b.get(f"/api/records/{record_id}")
    # 非归属者视为不存在:返回业务码 NOT_FOUND(40002),data 为空
    body = resp.json()
    assert body["code"] == 40002  # NOT_FOUND
    assert body.get("data") is None or "id" not in (body.get("data") or {})


@pytest.mark.asyncio
async def test_idor_get_other_user_tag_404(auth_client_a, auth_client_b):
    """用户 B 读取用户 A 的标签 → 404。"""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post("/api/tags", json={"name": "A标签", "category_id": cat_id})
    tag_id = resp.json()["data"]["id"]

    resp = await auth_client_b.get(f"/api/tags/{tag_id}")
    assert resp.json()["code"] == 40002


@pytest.mark.asyncio
async def test_idor_update_other_user_budget_403(auth_client_a, auth_client_b):
    """用户 B 修改用户 A 的预算 → 403。"""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/budgets",
        json={"category_id": cat_id, "month": "2026-06", "amount": 1000.0},
    )
    budget_id = resp.json()["data"]["id"]

    resp = await auth_client_b.put(
        f"/api/budgets/{budget_id}",
        json={"amount": 999.0},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_idor_delete_other_user_budget_403(auth_client_a, auth_client_b):
    """用户 B 删除用户 A 的预算 → 403。"""
    resp = await auth_client_a.post(
        "/api/categories",
        json={"name": "A分类2", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    cat_id = resp.json()["data"]["id"]
    resp = await auth_client_a.post(
        "/api/budgets",
        json={"category_id": cat_id, "month": "2026-07", "amount": 500.0},
    )
    budget_id = resp.json()["data"]["id"]

    resp = await auth_client_b.delete(f"/api/budgets/{budget_id}")
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_idor_get_other_user_attachment_404(auth_client_a, auth_client_b):
    """用户 B 读取用户 A 的附件 → 404。"""
    file_content = _make_png()
    files = {"file": ("receipt.jpg", io.BytesIO(file_content), "image/jpeg")}
    resp = await auth_client_a.post("/api/attachments/upload", files=files)
    att_id = resp.json()["data"]["id"]

    resp = await auth_client_b.get(f"/api/attachments/{att_id}")
    assert resp.json()["code"] == 40002


@pytest.mark.asyncio
async def test_idor_delete_other_user_attachment_forbidden(auth_client_a, auth_client_b):
    """用户 B 删除用户 A 的附件 → 403。"""
    file_content = _make_png()
    files = {"file": ("secret.jpg", io.BytesIO(file_content), "image/jpeg")}
    resp = await auth_client_a.post("/api/attachments/upload", files=files)
    att_id = resp.json()["data"]["id"]

    resp = await auth_client_b.delete(f"/api/attachments/{att_id}")
    assert resp.status_code == 403
    assert resp.json()["code"] == 40005


@pytest.mark.asyncio
async def test_unauthenticated_attachment_access_401(anon_client):
    """未带 token 访问附件端点 → 401。"""
    resp = await anon_client.get("/api/attachments/1")
    assert resp.status_code == 401
    resp = await anon_client.delete("/api/attachments/1")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit(anon_client):
    """同 IP 连发 login 超过限额 → 429。"""
    payload = {"username": "nouser", "password": "wrong"}
    codes = []
    for _ in range(6):
        resp = await anon_client.post("/api/auth/login", json=payload)
        codes.append(resp.status_code)
    # 前 5 次正常返回(401 凭证错误),第 6 次 429
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
