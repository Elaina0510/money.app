"""M0（v1.4.4）软删标签读链路收口用例 —— 任务文件 §4.1–4.5 五组 Given/Then。

口径（设计 D2 / REQ-001 前提）：软删标签对用户「不存在」，三处读链路各自一行级收口：
  1. `record_service._enrich_record` → 账单列表/详情/编辑回填/创建返回的 `tag` 落 null；
  2. `statistics_service.get_tag_stats` → 标签分布不再成组（响应结构零变化）；
  3. `export_service.export_csv` 标签查找原生 SQL → 其账单行 `tag_name` 落 `""`，
     且 `(user_id = :uid OR user_id IS NULL)` 两段**必须括号包住**（§4.3 按
     (归属 × 软删) 四格真值表钉住优先级：全局预设标签行仍出名字、
     用户与全局的已软删行都落 `""`）。

SQL 导出（文本 dump）= 备份语义，**一字不改**（D2 红线）：§4.4 除了断言软删标签行仍在、
`deleted_at` 列声明仍保留，还把「软删前后 SQL 导出文本逐字相同（仅时间戳头行除外）」
钉成回归锚——一旦有人给 SQL 导出加了 `deleted_at` 过滤，这条立刻变红。

既有 records/statistics/export 用例零修改零放宽，本文件只新增用例。
"""

import csv
import io
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.tag import Tag

pytestmark = pytest.mark.asyncio

# 统计区间：所有用例的账单都落在 2024-01-15，窗口内全覆盖
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"
CONSUME_TIME = "2024-01-15 12:00"

# CSV 导出列序（export_service 既定表头）：第 4 列即 tag_name
CSV_TAG_NAME_COL = 3


async def _mk_category(client: AsyncClient, name: str) -> int:
    """建一个用户分类，返回 id。"""
    resp = await client.post(
        "/api/categories",
        json={"name": name, "type": "expense", "icon": "mdi-food", "sort_order": 1},
    )
    assert resp.status_code == 200
    return int(resp.json()["data"]["id"])


async def _mk_tag(client: AsyncClient, name: str, category_id: int | None = None) -> int:
    """经既有 POST /api/tags 建**当前用户**标签，返回 id。"""
    payload: dict[str, Any] = {"name": name}
    if category_id is not None:
        payload["category_id"] = category_id
    resp = await client.post("/api/tags", json=payload)
    assert resp.status_code == 200
    return int(resp.json()["data"]["id"])


async def _mk_record(
    client: AsyncClient,
    category_id: int,
    tag_id: int | None,
    amount: float,
    note: str,
) -> dict[str, Any]:
    """经既有 POST /api/records 记账，返回富化后的账单行（创建返回同样经 `_enrich_record`）。"""
    payload: dict[str, Any] = {
        "amount": amount,
        "type": "expense",
        "category_id": category_id,
        "consume_time": CONSUME_TIME,
        "note": note,
    }
    if tag_id is not None:
        payload["tag_id"] = tag_id
    resp = await client.post("/api/records", json=payload)
    assert resp.status_code == 200
    return resp.json()["data"]


async def _list_records(client: AsyncClient) -> list[dict[str, Any]]:
    resp = await client.get("/api/records", params={"page": 1, "page_size": 100})
    assert resp.status_code == 200
    return list(resp.json()["data"]["items"])


def _row_of(items: list[dict[str, Any]], record_id: int) -> dict[str, Any]:
    return next(row for row in items if row["id"] == record_id)


async def _tag_stats(client: AsyncClient) -> dict[str, dict[str, Any]]:
    """GET /api/statistics/by-tag → {tag_name: item}；顺带钉响应结构零变化。"""
    resp = await client.get(
        "/api/statistics/by-tag", params={"start_date": START_DATE, "end_date": END_DATE}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    # 收口只减分组、不改结构：仍是 {"items": [{tag_name,total,count}]}
    assert set(data.keys()) == {"items"}
    for item in data["items"]:
        assert set(item.keys()) == {"tag_name", "total", "count"}
    return {str(item["tag_name"]): item for item in data["items"]}


async def _csv_rows(client: AsyncClient) -> list[list[str]]:
    resp = await client.get("/api/export/csv")
    assert resp.status_code == 200
    text = resp.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _csv_tag_name_of(rows: list[list[str]], note: str) -> str:
    header = rows[0]
    assert header == ["amount", "type", "category_name", "tag_name", "consume_time", "note"]
    assert header[CSV_TAG_NAME_COL] == "tag_name"
    row = next(r for r in rows[1:] if r and r[-1] == note)
    return row[CSV_TAG_NAME_COL]


async def _sql_text(client: AsyncClient) -> str:
    resp = await client.get("/api/export/sql")
    assert resp.status_code == 200
    return resp.content.decode("utf-8")


def _sql_without_date_header(sql: str) -> str:
    """剥掉唯一随时刻变化的 `-- Date:` 头行，其余逐字参与比对。"""
    return "\n".join(line for line in sql.splitlines() if not line.startswith("-- Date:"))


# ── §4.1 账单富化：软删后列表/详情 tag 均为 null ────────────────────────────


@pytest.mark.asyncio
async def test_4_1_records_tag_null_after_soft_delete(client: AsyncClient) -> None:
    """用例 4.1: Given 账单挂标签 T，When 软删 T，
    Then `GET /api/records` 该行 `tag === null`、`GET /api/records/{id}` 同（编辑回填同源）。
    边界顺带钉住：`record.tag_id` 为 None 的行行为不变（仍 tag=null）。
    """
    cat_id = await _mk_category(client, "收口用例分类41")
    tag_t = await _mk_tag(client, "待软删标签T41", cat_id)

    record_t = await _mk_record(client, cat_id, tag_t, 30.0, "T41账单")
    record_notag = await _mk_record(client, cat_id, None, 5.0, "无标签账单41")

    # 软删前：标签可见（否则本用例的 then 无意义）
    assert record_t["tag"] is not None
    assert record_t["tag"]["name"] == "待软删标签T41"
    assert record_notag["tag"] is None

    resp = await client.delete(f"/api/tags/{tag_t}")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    items = await _list_records(client)
    assert _row_of(items, record_t["id"])["tag"] is None
    # 无 tag_id 的行不受收口影响（行为不变）
    assert _row_of(items, record_notag["id"])["tag"] is None

    detail = await client.get(f"/api/records/{record_t['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["tag"] is None

    # 编辑回填走 PUT 的返回（同一 `_enrich_record`）
    put = await client.put(
        f"/api/records/{record_t['id']}", json={"note": "T41账单改备注"}
    )
    assert put.status_code == 200
    assert put.json()["data"]["tag"] is None


# ── §4.2 统计：软删标签不成组 + 未删标签分组数值逐字不变（防过度过滤回归锚）──


@pytest.mark.asyncio
async def test_4_2_tag_stats_excludes_soft_deleted_group(client: AsyncClient) -> None:
    """用例 4.2: Given 同上，Then `GET /api/statistics/by-tag` 不含 T 分组；
    **未删标签 U 的分组数值逐字不变**（防过度过滤回归锚，含具体数字钉死）。
    """
    cat_id = await _mk_category(client, "收口用例分类42")
    tag_t = await _mk_tag(client, "待软删标签T42", cat_id)
    tag_u = await _mk_tag(client, "保留标签U42", cat_id)

    await _mk_record(client, cat_id, tag_t, 30.0, "T42账单一")
    await _mk_record(client, cat_id, tag_t, 20.0, "T42账单二")
    await _mk_record(client, cat_id, tag_u, 12.5, "U42账单一")
    await _mk_record(client, cat_id, tag_u, 7.5, "U42账单二")

    before = await _tag_stats(client)
    assert before["待软删标签T42"] == {"tag_name": "待软删标签T42", "total": 50.0, "count": 2}
    u_snapshot = before["保留标签U42"]
    # 具体数值钉死（不是「差不多」）：U 收口前后必须逐字一致
    assert u_snapshot == {"tag_name": "保留标签U42", "total": 20.0, "count": 2}

    resp = await client.delete(f"/api/tags/{tag_t}")
    assert resp.status_code == 200

    after = await _tag_stats(client)
    assert "待软删标签T42" not in after
    assert after["保留标签U42"] == u_snapshot
    # 只减分组：其余分组数不变（此处仅 T 消失）
    assert set(after.keys()) == set(before.keys()) - {"待软删标签T42"}


# ── §4.3 CSV 导出：软删标签行 tag_name 为 ""，全局预设标签仍正常出名字 ──────


@pytest.mark.asyncio
async def test_4_3_csv_export_soft_deleted_tag_name_empty_preset_tag_kept(
    auth_client: AsyncClient, db_session
) -> None:
    """用例 4.3: Given 同上，Then CSV 导出 T 的账单行第 4 列 `tag_name` 为 `""`；U 的行不变；
    **含全局预设标签（`user_id IS NULL`）的行仍正常出名字**（括号优先级证据）。

    按 (归属 × 软删) 四格真值表钉死，两种错写各踩其中一格：
      * 漏括号 `WHERE user_id = :uid OR user_id IS NULL AND deleted_at IS NULL`
        ——AND 优先级更高，等价于 `user_id = :uid OR (user_id IS NULL AND deleted_at IS NULL)`，
        本用户已软删的 T 仍出名字 → T 格变红；
      * 把全局分支连同过滤写歪（如只留 `user_id = :uid AND deleted_at IS NULL` 的过度收口）
        → 未删的全局预设标签 G 丢名字 → G 格变红。
    """
    cat_id = await _mk_category(auth_client, "收口用例分类43")
    tag_t = await _mk_tag(auth_client, "待软删标签T43", cat_id)
    tag_u = await _mk_tag(auth_client, "保留标签U43", cat_id)

    # 全局预设标签行（user_id IS NULL，直插库 seed，沿 v1.4.4 导出热修的既有用建法）
    preset_tag = Tag(name="全局预设标签G43")
    # 全局行已软删（同样直插 seed，不经任何写接口——全局行不被本模块写脏）
    preset_tag_deleted = Tag(name="全局软删标签GD43", deleted_at="2024-01-01 00:00:00")
    db_session.add_all([preset_tag, preset_tag_deleted])
    await db_session.commit()
    await db_session.refresh(preset_tag)
    await db_session.refresh(preset_tag_deleted)
    assert preset_tag.user_id is None and preset_tag.deleted_at is None
    assert preset_tag_deleted.user_id is None and preset_tag_deleted.deleted_at

    await _mk_record(auth_client, cat_id, tag_t, 30.0, "T43账单")
    await _mk_record(auth_client, cat_id, tag_u, 12.5, "U43账单")
    await _mk_record(auth_client, cat_id, preset_tag.id, 8.0, "G43账单")
    await _mk_record(auth_client, cat_id, preset_tag_deleted.id, 9.0, "GD43账单")

    resp = await auth_client.delete(f"/api/tags/{tag_t}")
    assert resp.status_code == 200

    rows = await _csv_rows(auth_client)
    assert _csv_tag_name_of(rows, "T43账单") == ""            # 用户 · 已软删 → 无名
    assert _csv_tag_name_of(rows, "U43账单") == "保留标签U43"   # 用户 · 未删 → 名字不变
    assert _csv_tag_name_of(rows, "G43账单") == "全局预设标签G43"  # 全局 · 未删 → 仍出名字
    assert _csv_tag_name_of(rows, "GD43账单") == ""            # 全局 · 已软删 → 无名


# ── §4.4 SQL 导出：备份语义一字不改 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_4_4_sql_export_keeps_soft_deleted_tag_row(client: AsyncClient) -> None:
    """用例 4.4: Given 同上，Then SQL 导出文本仍含 T 行且 `deleted_at` 值保留——
    断言三件：① tags 段仍导出 T 的 INSERT 行；② tags 建表语句的 `deleted_at TEXT` 列声明
    原样在场（备份语义、非读链路，D2 明确「不加 deleted_at 过滤」）；
    ③ 软删前后 SQL 导出文本（除唯一时间戳头行）**逐字相同**——本模块对 SQL 导出零改动。
    """
    cat_id = await _mk_category(client, "收口用例分类44")
    tag_t = await _mk_tag(client, "待软删标签T44", cat_id)
    await _mk_record(client, cat_id, tag_t, 30.0, "T44账单")

    sql_before = _sql_without_date_header(await _sql_text(client))

    resp = await client.delete(f"/api/tags/{tag_t}")
    assert resp.status_code == 200

    sql_after_raw = await _sql_text(client)
    sql_after = _sql_without_date_header(sql_after_raw)

    # 软删标签行仍在备份里
    tag_insert_lines = [ln for ln in sql_after.splitlines() if ln.startswith("INSERT INTO tags")]
    assert any("'待软删标签T44'" in ln for ln in tag_insert_lines), sql_after
    # deleted_at 列声明保留（dump 结构不变，不据此过滤）
    assert "deleted_at TEXT" in sql_after
    # 挂该标签的账单行同样仍在备份里
    assert any("T44账单" in ln for ln in sql_after.splitlines() if ln.startswith("INSERT INTO records"))
    # 一字不改：软删前后除时间戳头行外逐字相同
    assert sql_after == sql_before


# ── §4.5 既有单删接口口径：三处表现同 4.1–4.3 ─────────────────────────────


@pytest.mark.asyncio
async def test_4_5_existing_single_delete_endpoint_covers_all_three_paths(
    client: AsyncClient, db_session
) -> None:
    """用例 4.5: 走既有 `DELETE /api/tags/{id}` 软删后，账单/统计/CSV 三处表现同 §4.1–§4.3
    （本模块同时修复既有单删口径）；顺带断言库里 `deleted_at` 已置值——
    即三处不可见来自「软删被正确识别」，不是行被物理删掉。
    """
    cat_id = await _mk_category(client, "收口用例分类45")
    tag_t = await _mk_tag(client, "待软删标签T45", cat_id)
    tag_u = await _mk_tag(client, "保留标签U45", cat_id)

    record_t = await _mk_record(client, cat_id, tag_t, 18.0, "T45账单")
    await _mk_record(client, cat_id, tag_u, 4.0, "U45账单")

    resp = await client.delete(f"/api/tags/{tag_t}")
    assert resp.status_code == 200

    # 软删确实落库（单删接口行为不变）
    deleted_tag = await db_session.get(Tag, tag_t)
    assert deleted_tag is not None
    assert deleted_tag.deleted_at  # 形如 "YYYY-MM-DD HH:MM:SS"
    assert deleted_tag.name == "待软删标签T45"

    # 读链路一：账单列表 + 详情
    items = await _list_records(client)
    assert _row_of(items, record_t["id"])["tag"] is None
    detail = await client.get(f"/api/records/{record_t['id']}")
    assert detail.json()["data"]["tag"] is None

    # 读链路二：统计（T 不成组、U 数值逐字不变）
    stats = await _tag_stats(client)
    assert "待软删标签T45" not in stats
    assert stats["保留标签U45"] == {"tag_name": "保留标签U45", "total": 4.0, "count": 1}

    # 读链路三：CSV 导出 tag_name 落 ""，U 不变
    rows = await _csv_rows(client)
    assert _csv_tag_name_of(rows, "T45账单") == ""
    assert _csv_tag_name_of(rows, "U45账单") == "保留标签U45"
