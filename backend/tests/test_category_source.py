"""v1.4.4 M2 测试：分类出身徽章（`categories.source`）+ 恢复默认连定制复原.

覆盖设计 §3.8 后端十条（任务 §8.1.1–8.1.10），逐号对应：

  1. 预设换图标/改序 → CoW 副本行 `source==1`（REQ-003 双时点）；
  2. 同名「餐饮」自建重建 → `source==0`（REQ-004）；
  3. 恢复默认黄金链路（REQ-005 三验收逐字对）；
  4. 自建分类账单改挂「其他」全局行 id + 影子未命中行计数；
  5. 副本单删 → 403 `FORBIDDEN`；全局行删除行为不变（D8）；
  6. 原子性：mock 步骤 3（自建堆）抛错 → 零变更；
  7. `GET /categories/presets` 与 `presets.py` 逐字一致；新库 seed 后全局行 `source==1`；
  8. 迁移脚本（临时库注入旧形制数据）：幂等 no-op + 三类回填断言 + 常量一致性；
  9. 恢复默认后 `PRAGMA foreign_key_check` 零新增违规；
  10. 序尾记判据用例表（**具体整数写死**，与前端 §8.2.3 同表逐字同源）。

手法要点（沿仓内既有惯例）：
  * `conftest.PRESET_CATEGORIES` 是 v1.4.3 前的 **7 条旧形**（9.3a 已登记其过期，且不含
    `source`），故本模块用 `aseeded` fixture 自建 14 条新形 seed（逐条 `source=1`），
    以免徽章/判据断言落在过期数据上；conftest 不在 M2 文件面内，不改它；
  * 迁移用例只在 `tmp_path`（系统临时目录下的 pytest 沙盒，用后自清）的**文件库**上跑，
    **绝不对 `backend/money.db` 做任何写操作或迁移**（红线）；
  * seed 路径用例另起**独立内存引擎**并 monkeypatch `app.main.engine`，与 conftest 的
    `test_engine` 及现场库彻底隔离。
"""

import asyncio
import importlib.util
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget, BudgetCategory
from app.models.category import LEGACY_CATEGORY_TYPE, Category
from app.models.record import Record
from app.models.tag import Tag
from app.presets import PRESET_CATEGORIES, PRESET_SPECS
from app.services import category_service
from app.services.category_service import compute_discarded_customizations

MONTH = "2026-06"

# 预设名/默认图标（判据输入，逐字取 presets.py，不在测试里自带第二份常量）
PRESET_NAMES: list[str] = [name for name, _icon, _sort in PRESET_SPECS]
DEFAULT_ICON: dict[str, str] = {name: icon for name, icon, _sort in PRESET_SPECS}


# ── 共用小工具 ────────────────────────────────────────────────────────────
async def _visible(client: Any) -> list[dict[str, Any]]:
    resp = await client.get("/api/categories")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _row(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(r for r in rows if r["name"] == name)


async def _global_row(db: AsyncSession, name: str) -> Category:
    row = (
        await db.exec(select(Category).where(Category.name == name, Category.user_id.is_(None)))
    ).first()
    assert row is not None, f"全局预设行「{name}」必须存在"
    return row


async def _refresh(db: AsyncSession) -> None:
    """丢掉身份映射，确保后续读取走库（API 的提交发生在另一个会话）。"""
    await db.rollback()
    db.expire_all()


async def _record_count(db: AsyncSession) -> int:
    await _refresh(db)
    return int((await db.exec(select(func.count(Record.id)))).one() or 0)


async def _fk_violations(db: AsyncSession) -> list[tuple[Any, ...]]:
    """`PRAGMA foreign_key_check` 全量违规行（运行期未开 FK 开关，SQLite 仍照报）。"""
    await _refresh(db)
    result = await db.execute(text("PRAGMA foreign_key_check"))
    return [tuple(r) for r in result.all()]


@pytest_asyncio.fixture
async def aseeded(db_session: AsyncSession) -> AsyncSession:
    """用 14 条**新形**预设（逐条 `source=1`）替换 conftest 的 7 条过期 seed。"""
    for row in (await db_session.exec(select(Category))).all():
        await db_session.delete(row)
    await db_session.commit()

    for cat_data in PRESET_CATEGORIES:
        db_session.add(Category(**cat_data))
    await db_session.commit()
    return db_session


# ===========================================================================
# 8.1.1 预设换图标 / 改序 → CoW 副本行 source==1（REQ-003 双时点）
# ===========================================================================


@pytest.mark.asyncio
async def test_cow_copy_from_icon_edit_carries_source_one(auth_client, aseeded):
    """时点一：预设换图标 → CoW 副本行 `is_preset==0` 而 `source==1`（徽章不丢）。"""
    before = await _visible(auth_client)
    food = _row(before, "餐饮")
    assert food["source"] == 1 and food["is_preset"] == 1, "seed 的全局预设行出身即 1"

    resp = await auth_client.put(f"/api/categories/{food['id']}", json={"icon": "mdi-coffee"})
    assert resp.status_code == 200, resp.text
    copy = resp.json()["data"]
    assert copy["id"] != food["id"], "CoW：写的是用户副本，不是全局行"
    assert copy["is_preset"] == 0, "副本的 is_preset 语义一字不动（§0.6 红线）"
    assert copy["source"] == 1, "副本出身仍为预设（D3 徽章口径）"
    assert copy["icon"] == "mdi-coffee" and copy["name"] == "餐饮"

    rows = await _visible(auth_client)
    cur = _row(rows, "餐饮")
    assert cur["id"] == copy["id"] and cur["source"] == 1, "列表刷新后徽章源仍在"
    global_food = await _global_row(aseeded, "餐饮")
    assert global_food.icon == DEFAULT_ICON["餐饮"] and global_food.source == 1, (
        "全局预设行未被写脏"
    )


@pytest.mark.asyncio
async def test_cow_copy_from_rename_attempt_carries_source_one(auth_client, aseeded):
    """预设改名请求（CoW 路径按 name 定位全局行，副本沿用预设名）同样落 `source==1`。"""
    food = _row(await _visible(auth_client), "餐饮")
    resp = await auth_client.put(f"/api/categories/{food['id']}", json={"name": "美食"})
    assert resp.status_code == 200, resp.text
    copy = resp.json()["data"]
    assert copy["source"] == 1
    assert _row(await _visible(auth_client), copy["name"])["source"] == 1


@pytest.mark.asyncio
async def test_reordered_presets_become_copies_still_source_one(auth_client, aseeded):
    """时点二：拖序保存 → 被移位的预设落为副本，重取仍 `source==1`（REQ-003 双时点）。"""
    rows = await _visible(auth_client)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(PRESET_NAMES), "seed 后恰 14 条可见预设"

    # 首两行互换（餐饮 ↔ 出行）：出行由全局行 CoW 成副本
    swapped = [ids[1], ids[0], *ids[2:]]
    resp = await auth_client.put("/api/categories/reorder", json={"ids": swapped})
    assert resp.status_code == 200, resp.text

    after = await _visible(auth_client)
    assert [r["name"] for r in after][:2] == ["出行", "餐饮"], "拖序生效"
    moved = _row(after, "出行")
    assert moved["is_preset"] == 0, "全局预设移位 → 生成用户副本"
    assert moved["source"] == 1, "拖序副本出身仍为预设"
    untouched = _row(after, "购物")
    assert untouched["id"] == ids[2] and untouched["source"] == 1, "未移位的行仍是全局预设"
    assert all(r["source"] == 1 for r in after), "全列表徽章源恒 1（拖动/刷新后不丢徽章）"


# ===========================================================================
# 8.1.2 同名重建 → source==0（REQ-004）
# ===========================================================================


@pytest.mark.asyncio
async def test_recreated_same_name_category_is_source_zero(auth_client, aseeded):
    """用户自建同名「餐饮」：新行 `source==0`（无徽章、可单删）。"""
    food = _row(await _visible(auth_client), "餐饮")
    resp = await auth_client.post(
        "/api/categories", json={"name": "餐饮", "icon": "mdi-silverware-fork-knife"}
    )
    assert resp.status_code == 200, resp.text
    created = resp.json()["data"]
    assert created["source"] == 0, "服务层新建 = 用户自建，显式 0（§0.4-6 造行点）"
    assert created["is_preset"] == 0 and created["id"] != food["id"]

    mine = [r for r in await _visible(auth_client) if r["name"] == "餐饮"]
    assert [r["source"] for r in mine] == [0], "遮蔽语义：可见列表里那条自建行 source=0（REQ-004）"


# ===========================================================================
# 8.1.3 恢复默认黄金链路（REQ-005 三验收）
# ===========================================================================


@pytest.mark.asyncio
async def test_restore_default_golden_path_merges_copy(auth_client, aseeded):
    """定制「餐饮」（换图标 + 5 条账单 + 1 条 include 预算关联）→ 恢复默认后原样复原。

    断言逐条对齐设计 §3.8-3 / REQ-005 三验收：账单 `category_id == 全局餐饮 id`、
    副本行消失、全局行名/图标/序 = 默认、预算关联存在且 `dormant==0`、
    `merged_presets==1 / discarded_customizations==1`、账单总数前后相等。

    偏离登记（见完成 notes）：任务原文的「改序」与 `merged_presets==1` 在 CoW +
    reorder 归一化 1..n 下互斥——任一预设移位都会为**被挤动的每个预设**各建一份副本，
    merged 随之 >1；「改名」则使副本无同名全局行可并（§3.7 宁删不错并），merged=0。
    故本用例取「换图标」形态（name 保持可并、M 仍为 1），改序的判据覆盖见 §8.1.10 表，
    改名入自建堆见下一条用例。
    """
    db = aseeded
    global_food = await _global_row(db, "餐饮")
    global_id = global_food.id

    resp = await auth_client.put(f"/api/categories/{global_id}", json={"icon": "mdi-coffee"})
    copy_id = resp.json()["data"]["id"]
    assert copy_id != global_id

    for i in range(5):
        rec = await auth_client.post(
            "/api/records",
            json={
                "amount": 10.5 + i,
                "type": "expense",
                "category_id": copy_id,
                "consume_time": f"{MONTH}-0{i + 1} 10:00",
            },
        )
        assert rec.status_code == 200, rec.text

    budget = await auth_client.post(
        "/api/budgets",
        json={
            "month": MONTH,
            "name": "餐饮月预算",
            "amount": 800.0,
            "scope_mode": "include",
            "category_ids": [copy_id],
        },
    )
    assert budget.status_code == 200, budget.text
    budget_id = budget.json()["data"]["id"]

    total_before = await _record_count(db)
    assert total_before == 5

    res = await auth_client.post("/api/categories/restore-defaults")
    assert res.status_code == 200, res.text
    body = res.json()
    data = body["data"]
    assert data["merged_presets"] == 1, "副本合并回全局行（REQ-005①）"
    assert data["discarded_customizations"] == 1, "换图标 = 1 条定制被丢弃"
    assert data["deleted_categories"] == 0, "自建堆为空：无分类被删"
    assert data["affected_records"] == 0, "账单不迁移、不乱动（REQ-005②）"
    assert data["dormant_budgets"] == 0, "改指后预算关联仍有效 → 不触发休眠"
    assert await _record_count(db) == total_before, "恢复前后账单总数相等（REQ-005③）"

    rows = await _visible(auth_client)
    assert [r["id"] for r in rows if r["name"] == "餐饮"] == [global_id], "副本已不存在"
    assert _row(rows, "餐饮")["icon"] == DEFAULT_ICON["餐饮"], "全局行图标复位默认"
    assert _row(rows, "餐饮")["source"] == 1

    await _refresh(db)
    recs = (await db.exec(select(Record).where(Record.category_id == global_id))).all()
    assert len(recs) == 5, "账单改指全局行 id 且一条不少"

    links = (
        await db.exec(select(BudgetCategory).where(BudgetCategory.category_id == global_id))
    ).all()
    assert [int(link.budget_id) for link in links] == [budget_id], "预算关联改指全局行"
    stored_budget = await db.get(Budget, budget_id)
    assert stored_budget is not None and stored_budget.dormant == 0, "预算未休眠"

    # message 由路由按五键拼装（任务 6.3：M≠0 提「预设定制已复原」，N/K=0 省略该段）
    message = body["message"]
    assert "已恢复默认分类" in message and "1 个预设定制已复原" in message
    assert "自定义分类" not in message and "归入「其他」" not in message


@pytest.mark.asyncio
async def test_restore_default_relink_dedups_already_linked_budget(auth_client, aseeded):
    """预算同时关联「全局行 + 副本行」→ 恢复默认改指时须按 UNIQUE 去重（任务 4.2-② 第二分支）。

    `budget_categories` 有 `UNIQUE(budget_id, category_id)`（§0.4-8）：黄金链路只走「改指」
    分支，本用例走「目标关联本就在 → 删副本侧关联行」分支。该分支要求改指前先取目标侧
    已有预算集合（`exec(select(BudgetCategory.budget_id))` 返回**标量**而非 Row 元组，
    按 `row[0]` 取值会在这一支抛 TypeError），故本用例同时是该口径的回归锁。
    两条分支都必须保证受影响预算仍至少关联一条分类 → `dormant==0`（不误休眠）。
    """
    db = aseeded
    global_food = await _global_row(db, "餐饮")
    global_id = global_food.id

    budget = await auth_client.post(
        "/api/budgets",
        json={
            "month": MONTH,
            "name": "餐饮月预算",
            "amount": 800.0,
            "scope_mode": "include",
            "category_ids": [global_id],
        },
    )
    assert budget.status_code == 200, budget.text
    budget_id = budget.json()["data"]["id"]

    # 定制「餐饮」→ CoW 副本；再补一条指向副本的关联（与全局行侧并存，现场可由
    # 「先建预算关联、后别端定制出副本」产生，故直接落库造形）
    resp = await auth_client.put(f"/api/categories/{global_id}", json={"icon": "mdi-coffee"})
    copy_id = resp.json()["data"]["id"]
    assert copy_id != global_id
    db.add(BudgetCategory(budget_id=budget_id, category_id=copy_id))
    await db.commit()

    res = await auth_client.post("/api/categories/restore-defaults")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["merged_presets"] == 1
    assert data["dormant_budgets"] == 0, "仍关联全局行 → 不休眠"

    await _refresh(db)
    links = (await db.exec(select(BudgetCategory).where(BudgetCategory.budget_id == budget_id))).all()
    assert [int(link.category_id) for link in links] == [global_id], (
        "副本侧重复关联被丢弃，预算关联收敛到全局行一条"
    )
    stored_budget = await db.get(Budget, budget_id)
    assert stored_budget is not None and stored_budget.dormant == 0


@pytest.mark.asyncio
async def test_restore_default_rename_break_counts_one_without_merge(auth_client, aseeded):
    """副本名不在预设名集内（改名/历史形制）→ 不可并，落自建堆删除，并计 1 条定制。"""
    db = aseeded
    global_food = await _global_row(db, "餐饮")
    await auth_client.put(f"/api/categories/{global_food.id}", json={"icon": "mdi-coffee"})
    copy = _row(await _visible(auth_client), "餐饮")

    # 服务层 CoW 路径不改名，故直接落库模拟「预设改名史遗留」的病态形态（§3.7）
    stored = await db.get(Category, copy["id"])
    assert stored is not None
    stored.name = "美食"
    db.add(stored)
    await db.commit()

    res = await auth_client.post("/api/categories/restore-defaults")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["merged_presets"] == 0, "名字不在预设集内 → 宁删不错并（§3.7）"
    assert data["discarded_customizations"] == 1, "改名破坏计 1（一行至多计一次）"
    assert data["deleted_categories"] == 1, "影子行入自建堆被删除"

    after = await _visible(auth_client)
    assert "美食" not in [r["name"] for r in after]
    assert _row(after, "餐饮")["id"] == global_food.id, "全局预设重现"
    assert _row(after, "餐饮")["source"] == 1


# ===========================================================================
# 8.1.4 自建分类账单改挂「其他」全局行 + 影子行计数
# ===========================================================================


@pytest.mark.asyncio
async def test_restore_moves_custom_records_to_other_and_counts_shadow(
    auth_client, auth_user, aseeded
):
    db = aseeded
    uid = auth_user.id
    other_id = (await _global_row(db, "其他")).id

    custom = await auth_client.post("/api/categories", json={"name": "宠物", "icon": "mdi-paw"})
    custom_id = custom.json()["data"]["id"]
    rec = await auth_client.post(
        "/api/records",
        json={
            "amount": 66.0,
            "type": "expense",
            "category_id": custom_id,
            "consume_time": f"{MONTH}-02 10:00",
        },
    )
    rec_id = rec.json()["data"]["id"]

    # 影子行：source==1 但无同名全局预设（预设改名史遗留）→ 步骤 2 未命中 → 入自建堆
    shadow = Category(
        name="已消失的预设",
        type=LEGACY_CATEGORY_TYPE,
        icon="mdi-ghost",
        sort_order=90,
        is_preset=0,
        source=1,
        user_id=uid,
    )
    db.add(shadow)
    await db.commit()
    await db.refresh(shadow)
    shadow_id = shadow.id
    db.add(
        Record(amount=7.0, type="expense", category_id=shadow_id, consume_time=f"{MONTH}-03 10:00")
    )
    await db.commit()

    total_before = await _record_count(db)
    res = await auth_client.post("/api/categories/restore-defaults")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["deleted_categories"] == 2, "自建行 + 影子未命中行一并计数"
    assert data["merged_presets"] == 0
    assert data["affected_records"] == 2, "两行各 1 条账单改挂「其他」"
    assert data["discarded_customizations"] == 1, "影子行（名不在预设集）计 1 条定制"
    assert await _record_count(db) == total_before, "账单只改指不删除 → 总数不变"

    await _refresh(db)
    moved = await db.get(Record, rec_id)
    assert moved is not None and moved.category_id == other_id, "改挂「其他」全局行 id"
    assert await db.get(Category, custom_id) is None
    assert await db.get(Category, shadow_id) is None


# ===========================================================================
# 8.1.5 副本不可单删（D8）
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_cow_copy_is_forbidden(auth_client, aseeded):
    global_id = (await _global_row(aseeded, "餐饮")).id
    resp = await auth_client.put(f"/api/categories/{global_id}", json={"icon": "mdi-coffee"})
    copy = resp.json()["data"]

    dele = await auth_client.delete(f"/api/categories/{copy['id']}")
    assert dele.status_code == 403, "副本不可单删（D8 连坐裁定）"
    body = dele.json()
    assert body["code"] == 40005, "路由转 Code.FORBIDDEN"
    assert body["message"] == "预设分类不可删除"
    assert _row(await _visible(auth_client), "餐饮")["id"] == copy["id"], "数据零变化"


@pytest.mark.asyncio
async def test_delete_global_preset_behaviour_unchanged(auth_client, aseeded):
    """全局预设行仍是 403（现状保持），且行不被删。"""
    global_id = (await _global_row(aseeded, "出行")).id
    dele = await auth_client.delete(f"/api/categories/{global_id}")
    assert dele.status_code == 403
    assert dele.json()["message"] == "预设分类不可删除"
    await _refresh(aseeded)
    assert await aseeded.get(Category, global_id) is not None


@pytest.mark.asyncio
async def test_delete_own_custom_category_still_works(auth_client, aseeded):
    resp = await auth_client.post("/api/categories", json={"name": "随手"})
    cid = resp.json()["data"]["id"]
    dele = await auth_client.delete(f"/api/categories/{cid}")
    assert dele.status_code == 200, dele.text
    assert dele.json()["data"]["deleted_records"] == 0


# ===========================================================================
# 8.1.6 原子性：步骤 3 抛错 → 整体回滚零变更
# ===========================================================================


@pytest.mark.asyncio
async def test_restore_default_rolls_back_wholly_when_step_three_fails(
    auth_client, aseeded, monkeypatch
):
    db = aseeded
    global_food = await _global_row(db, "餐饮")
    global_food_id = global_food.id
    # 把全局行弄脏（**仅测试构造**：运行期唯一合法写点是步骤 4），用以证明「未复位」
    global_food.sort_order = 42
    db.add(global_food)
    await db.commit()

    resp = await auth_client.put(f"/api/categories/{global_food_id}", json={"icon": "mdi-coffee"})
    copy_id = resp.json()["data"]["id"]
    rec = await auth_client.post(
        "/api/records",
        json={
            "amount": 12.0,
            "type": "expense",
            "category_id": copy_id,
            "consume_time": f"{MONTH}-04 10:00",
        },
    )
    rec_id = rec.json()["data"]["id"]
    custom = await auth_client.post("/api/categories", json={"name": "会被连坐"})
    custom_id = custom.json()["data"]["id"]

    async def boom(*_args: Any, **_kwargs: Any) -> int:
        raise RuntimeError("注入：步骤 3（自建堆）崩溃")

    monkeypatch.setattr(category_service, "_dormant_budgets_for_deleted_category", boom)
    with pytest.raises(RuntimeError, match="注入"):
        await auth_client.post("/api/categories/restore-defaults")

    monkeypatch.undo()
    rows = await _visible(auth_client)
    assert _row(rows, "餐饮")["id"] == copy_id, "副本仍在（步骤 2 的合并已回滚）"
    assert _row(rows, "会被连坐")["id"] == custom_id, "自建行仍在"
    await _refresh(db)
    record = await db.get(Record, rec_id)
    assert record is not None and record.category_id == copy_id, "账单仍挂副本（未改指）"
    dirty = await db.get(Category, global_food_id)
    assert dirty is not None and dirty.sort_order == 42, "全局行未被复位（步骤 4 未提交）"
    assert await _record_count(db) == 1, "账单一条不少不多"


# ===========================================================================
# 8.1.7 presets 端点 + 新库 seed + main.py 指向 SSOT
# ===========================================================================


@pytest.mark.asyncio
async def test_presets_endpoint_matches_presets_module_verbatim(auth_client):
    resp = await auth_client.get("/api/categories/presets")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert len(data) == 14
    assert data == [
        {"name": name, "icon": icon, "sort_order": sort} for name, icon, sort in PRESET_SPECS
    ], "逐字取 presets.py（其顺序即默认排序）"


@pytest.mark.asyncio
async def test_presets_endpoint_requires_auth(anon_client):
    resp = await anon_client.get("/api/categories/presets")
    assert resp.status_code == 401


def test_main_module_imports_shared_presets_ssot():
    """任务 2.2：main.py 的本地常量已删，改指 `app.presets`（同一对象，无第二份定义）。"""
    import app.main as main_mod

    assert main_mod.PRESET_CATEGORIES is PRESET_CATEGORIES


@pytest.mark.asyncio
async def test_new_library_seed_marks_global_rows_source_one(monkeypatch):
    """新库（create_all + init_preset_data）路径无需脚本：seed 后全局行 `source==1`。"""
    import app.main as main_mod

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        monkeypatch.setattr(main_mod, "engine", engine)
        await main_mod.init_preset_data()

        async with AsyncSession(engine) as session:
            rows = list((await session.exec(select(Category).order_by(Category.sort_order))).all())
    finally:
        await engine.dispose()

    assert len(rows) == len(PRESET_NAMES)
    assert all(r.source == 1 and r.is_preset == 1 and r.user_id is None for r in rows), (
        "seed 的 14 条全局预设行出身恒 1（任务 2.1 seed dict 内嵌 source）"
    )
    assert [(r.name, r.icon, r.sort_order) for r in rows] == PRESET_SPECS


# ===========================================================================
# 8.1.8 迁移脚本：幂等 + 三类回填 + 常量一致性（tmp_path 文件库，绝不碰 money.db）
# ===========================================================================

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "migrate_to_v1.4.4_source.py"


def _load_source_migration() -> Any:
    spec = importlib.util.spec_from_file_location("migrate_to_v1_4_4_source", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


source_migration = _load_source_migration()

# 现场形态（v1.4.3 M12 之后、M2 之前）：categories **无 source 列**
_CATEGORIES_DDL_NO_SOURCE = """
CREATE TABLE categories (
    id INTEGER NOT NULL,
    user_id INTEGER,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    icon VARCHAR NOT NULL,
    sort_order INTEGER NOT NULL,
    is_preset INTEGER NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT idx_categories_name_user UNIQUE (name, user_id)
)
"""

_CATEGORIES_DDL_WITH_SOURCE = _CATEGORIES_DDL_NO_SOURCE.replace(
    "    is_preset INTEGER NOT NULL,",
    "    is_preset INTEGER NOT NULL,\n    source INTEGER NOT NULL DEFAULT 0,",
)

# (id, user_id, name, icon, sort, is_preset) —— 三类回填判据与「不回填」对照组混排
_MIGRATION_ROWS: list[tuple[int, int | None, str, str, int, int]] = [
    (1, None, "餐饮", "mdi-food", 1, 1),  # 全局预设 → 1
    (2, None, "其他", "mdi-cash-minus", 14, 1),  # 全局预设（家族）→ 1
    (3, 1, "餐饮", "mdi-coffee", 1, 0),  # CoW 副本（同名预设）→ 1
    (4, 1, "出行", "mdi-bus", 2, 0),  # CoW 副本（图标未定制）→ 1
    (5, 1, "宠物", "mdi-paw", 20, 0),  # 无关自建 → 0
    (6, 1, "工资", "mdi-wallet", 11, 0),  # 收入侧副本 → 1
    (7, None, "匿名自建", "mdi-help", 30, 0),  # 匿名自建行 → 0
    (8, 1, "其他支出", "mdi-cash-minus", 99, 0),  # 旧家族副本，名不在 14 集内 → 0
    (9, 1, "我的理财笔记", "mdi-note", 40, 0),  # 名字含预设子串但非预设名 → 0
]
_OTHER_COLUMNS = "id, user_id, name, type, icon, sort_order, is_preset"


def _execute(path: Path, statements: list[str]) -> None:
    conn = sqlite3.connect(path)
    try:
        for sql in statements:
            conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def _query(path: Path, sql: str) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _columns(path: Path, table: str) -> list[str]:
    return [str(r[1]) for r in _query(path, f"PRAGMA table_info({table})")]


def _source_map(path: Path) -> dict[int, int]:
    return {int(r[0]): int(r[1]) for r in _query(path, "SELECT id, source FROM categories")}


def _prepare_site_db(
    tmp_path: Path,
    *,
    name: str = "site_v144.db",
    ddl: str = _CATEGORIES_DDL_NO_SOURCE,
) -> Path:
    """造「现场形态」文件库：默认 = M2 之前的 categories 列形（**无 source**）+ 9 行混排数据。"""
    db = tmp_path / name
    statements = [ddl]
    for cid, uid, name_, icon, sort, is_preset in _MIGRATION_ROWS:
        user_literal = "NULL" if uid is None else str(uid)
        statements.append(
            "INSERT INTO categories (id, user_id, name, type, icon, sort_order, is_preset,"
            f" created_at, updated_at) VALUES ({cid}, {user_literal}, '{name_}', 'expense',"
            f" '{icon}', {sort}, {is_preset}, '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )
    _execute(db, statements)
    return db


def _run(db: Path) -> dict[str, Any]:
    return asyncio.run(source_migration.run_migration(str(db)))


def test_migration_adds_column_and_backfills_three_classes(tmp_path):
    db = _prepare_site_db(tmp_path)
    assert "source" not in _columns(db, "categories"), "前置：现场库确无该列"
    before = _query(db, f"SELECT {_OTHER_COLUMNS} FROM categories ORDER BY id")

    stats = _run(db)

    assert stats["column_added"] == 1
    assert stats["backfilled_presets"] == 2, "两条全局预设行（含家族「其他」）"
    assert stats["backfilled_cow_copies"] == 3, "餐饮/出行/工资 三条同名副本"
    assert stats["scanned_categories"] == len(_MIGRATION_ROWS)
    assert stats["skipped_reason"] == ""
    assert _source_map(db) == {1: 1, 2: 1, 3: 1, 4: 1, 5: 0, 6: 1, 7: 0, 8: 0, 9: 0}
    assert _query(db, f"SELECT {_OTHER_COLUMNS} FROM categories ORDER BY id") == before, (
        "只加列 + 回填出身，其余列逐字段不损（is_preset 语义未动）"
    )


def test_migration_second_run_is_noop(tmp_path):
    db = _prepare_site_db(tmp_path)
    first = _run(db)
    assert not source_migration.is_noop(first)
    after_first = _source_map(db)
    cols = _columns(db, "categories")

    second = _run(db)

    assert source_migration.is_noop(second), f"二次执行必须归 0：{second}"
    assert second["column_added"] == 0
    assert second["skipped_reason"] == "categories 已含 source 列"
    assert _columns(db, "categories") == cols, "不再重复加列"
    assert _source_map(db) == after_first, "数据零变化"


def test_migration_on_library_already_having_column_is_direct_noop(tmp_path):
    db = _prepare_site_db(tmp_path, name="already_v144.db", ddl=_CATEGORIES_DDL_WITH_SOURCE)
    stats = _run(db)
    assert source_migration.is_noop(stats)
    assert stats["column_added"] == 0 and stats["scanned_categories"] == len(_MIGRATION_ROWS)
    assert _source_map(db) == {r[0]: 0 for r in _MIGRATION_ROWS}, "已含列 → 整体 no-op 不改写"


def test_migration_warns_but_never_rewrites_when_backfill_was_interrupted(
    tmp_path, capsys, monkeypatch
):
    """「加列已提交、回填被回滚」的中断终态：重跑按幂等判据只 WARN 不改写。"""

    async def boom(conn: Any) -> tuple[int, int]:
        raise RuntimeError("注入：加列之后、回填之前中断")

    db = _prepare_site_db(tmp_path, name="interrupted_v144.db")
    monkeypatch.setattr(source_migration, "_backfill", boom)
    with pytest.raises(RuntimeError):
        _run(db)
    monkeypatch.undo()

    assert "source" in _columns(db, "categories"), "SQLite DDL 由驱动即时提交"
    assert _source_map(db) == {r[0]: 0 for r in _MIGRATION_ROWS}, "回填 UPDATE 已回滚"

    stats = _run(db)
    assert source_migration.is_noop(stats), "重跑走幂等 no-op 分支"
    assert _source_map(db) == {r[0]: 0 for r in _MIGRATION_ROWS}, "只告警，不自动改写"
    out = capsys.readouterr().out
    assert "PRAGMA integrity_check" in out, "前置只读检查在跑（非 ok 时也只 WARN 不中止）"
    assert "[WARN] source 列已存在但回填未收敛" in out


def test_migration_skips_when_categories_table_absent(tmp_path):
    db = tmp_path / "empty_v144.db"
    _execute(db, ["CREATE TABLE users (id INTEGER PRIMARY KEY)"])
    stats = _run(db)
    assert source_migration.is_noop(stats)
    assert stats["skipped_reason"] == "categories 表不存在"
    assert _columns(db, "users") == ["id"]


def test_script_constants_match_presets_module() -> None:
    """脚本不 import app/ → 用一致性断言钉住 14 个预设名与列 DDL（任务 3.3）。"""
    assert tuple(PRESET_NAMES) == source_migration.PRESET_NAMES, (
        "脚本内置的 14 个预设名必须与 app.presets.PRESET_SPECS 同序同值"
    )
    assert len(source_migration.PRESET_NAMES) == 14
    assert source_migration.SOURCE_COLUMN_DDL == (
        "ALTER TABLE categories ADD COLUMN source INTEGER NOT NULL DEFAULT 0"
    ), "加列语句与模型列定义同形（NOT NULL + 默认 0）"
    assert source_migration.BACKFILL_PRESET_DDL == (
        "UPDATE categories SET source = 1 WHERE is_preset = 1"
    ), "回填判据 1 只看 is_preset（其语义一字不动，§0.6 红线）"

    column = Category.__table__.columns["source"]
    assert column.nullable is False
    from sqlalchemy.dialects import sqlite

    built = str(CreateTable(Category.__table__).compile(dialect=sqlite.dialect()))
    assert "source INTEGER DEFAULT '0' NOT NULL" in built, "create_all 路径同样落 NOT NULL 默认 0"


def test_migration_cli_entrypoint_prints_stats(tmp_path, capsys):
    db = _prepare_site_db(tmp_path, name="cli_v144.db")
    code = asyncio.run(source_migration.migrate(["migrate_to_v1.4.4_source.py", str(db)]))
    assert code == 0
    out = capsys.readouterr().out
    assert "必须先于新版后端服务启动执行" in out, "发布窗口执行序在运行时也提醒"
    assert "回填副本 3" in out


# ===========================================================================
# 8.1.9 恢复默认后 foreign_key_check 零新增违规
# ===========================================================================


@pytest.mark.asyncio
async def test_restore_default_leaves_no_new_foreign_key_violations(
    auth_client, auth_user, user_b, aseeded
):
    db = aseeded
    uid = auth_user.id
    other_uid = user_b.id
    global_food = await _global_row(db, "餐饮")
    global_food_id = global_food.id
    copy_id = (
        await auth_client.put(f"/api/categories/{global_food_id}", json={"icon": "mdi-coffee"})
    ).json()["data"]["id"]
    custom_id = (await auth_client.post("/api/categories", json={"name": "标签连坐"})).json()[
        "data"
    ]["id"]

    db.add_all(
        [
            Tag(name="本用户-副本", user_id=uid, category_id=copy_id),
            Tag(name="本用户-自建", user_id=uid, category_id=custom_id),
            Tag(name="他人-副本", user_id=other_uid, category_id=copy_id),
            Tag(name="匿名-自建", user_id=None, category_id=custom_id),
        ]
    )
    await db.commit()

    before = await _fk_violations(db)
    assert before == [], "前置：构造数据本身不留违规，违规比对才有意义"

    res = await auth_client.post("/api/categories/restore-defaults")
    assert res.status_code == 200, res.text

    assert await _fk_violations(db) == [], "恢复默认后零新增 FK 违规（任务 8.1.9）"

    await _refresh(db)
    tags = {t.name: t.category_id for t in (await db.exec(select(Tag))).all()}
    assert tags["本用户-副本"] == global_food_id, "本用户的标签改指全局行"
    assert tags["他人-副本"] is None, "跨用户引用无从改指 → 置 NULL"
    assert tags["本用户-自建"] is None and tags["匿名-自建"] is None

    assert set(res.json()["data"]) == {
        "deleted_categories",
        "affected_records",
        "dormant_budgets",
        "merged_presets",
        "discarded_customizations",
    }, "响应契约恰五键（任务 6.3）"


# ===========================================================================
# 8.1.10 序尾记判据用例表（与前端 §8.2.3 **逐字同源**，期望值必须是具体整数）
# ===========================================================================
# 行元组 = (分类名, 图标, source)；图标 "d" 表示取该名对应的预设默认图标。
# 列表顺序即输入顺序（= 可见列表按 sort_order, id 升序的形态），source 恒 1 除非显式 0。
# 期望值按设计 §3.4「名/图标破坏（一行至多计一次）+ 贪心序尾记」逐行人工推演写死。
ORDER_TAIL_CASES: list[tuple[str, list[tuple[str, str, int]], int]] = [
    ("空表（无任何行）", [], 0),
    ("单调：14 条预设原序原图标", [(name, "d", 1) for name in PRESET_NAMES], 0),
    (
        "单行改名（餐饮→美食，其余默认）",
        [("美食", "mdi-food", 1)] + [(name, "d", 1) for name in PRESET_NAMES[1:]],
        1,
    ),
    (
        "单行换图标（餐饮→mdi-coffee）",
        [("餐饮", "mdi-coffee", 1)] + [(name, "d", 1) for name in PRESET_NAMES[1:]],
        1,
    ),
    (
        "相邻两行互换（出行, 餐饮, 购物…）",
        [("出行", "d", 1), ("餐饮", "d", 1)] + [(name, "d", 1) for name in PRESET_NAMES[2:]],
        1,
    ),
    (
        "改名 + 换图标（美食 + mdi-coffee，只计一次）",
        [("美食", "mdi-coffee", 1)] + [(name, "d", 1) for name in PRESET_NAMES[1:]],
        1,
    ),
    (
        "换图标 + 改序（出行, 餐饮(coffee), 购物…）",
        [("出行", "d", 1), ("餐饮", "mdi-coffee", 1)]
        + [(name, "d", 1) for name in PRESET_NAMES[2:]],
        1,
    ),
    (
        "三行轮转（购物, 餐饮, 出行, 娱乐…）",
        [("购物", "d", 1), ("餐饮", "d", 1), ("出行", "d", 1)]
        + [(name, "d", 1) for name in PRESET_NAMES[3:]],
        2,
    ),
    (
        "首行移到末位（出行…理财, 餐饮, 其他）",
        [(name, "d", 1) for name in PRESET_NAMES[1:13]]
        + [("餐饮", "d", 1), ("其他", "d", 1)],
        1,
    ),
    ("整表逆序（其他…出行, 餐饮）", [(name, "d", 1) for name in reversed(PRESET_NAMES)], 12),
    (
        "「其他」置首 + 其余默认",
        [("其他", "d", 1)] + [(name, "d", 1) for name in PRESET_NAMES[:-1]],
        0,
    ),
    (
        "家族过渡旧行混入（其他支出…其他收入, 其他）",
        [("其他支出", "mdi-cash-minus", 1)]
        + [(name, "d", 1) for name in PRESET_NAMES[:-1]]
        + [("其他收入", "mdi-cash-plus", 1), ("其他", "d", 1)],
        2,
    ),
    (
        "自建行混入（source=0 不参与判据）",
        [("宠物", "mdi-paw", 0)] + [(name, "d", 1) for name in PRESET_NAMES],
        0,
    ),
    (
        "改名破坏 + 乱序（美食, 购物, 出行, 娱乐…）",
        [("美食", "mdi-food", 1), ("购物", "d", 1), ("出行", "d", 1)]
        + [(name, "d", 1) for name in PRESET_NAMES[3:]],
        2,
    ),
]


def _rows_for(spec: Sequence[tuple[str, str, int]]) -> list[Category]:
    return [
        Category(
            name=name,
            type=LEGACY_CATEGORY_TYPE,
            icon=DEFAULT_ICON.get(name, "mdi-circle") if icon == "d" else icon,
            sort_order=position,
            is_preset=0,
            source=source,
            user_id=1,
        )
        for position, (name, icon, source) in enumerate(spec, start=1)
    ]


@pytest.mark.parametrize(
    "label,spec,expected",
    ORDER_TAIL_CASES,
    ids=[case[0] for case in ORDER_TAIL_CASES],
)
def test_order_tail_judgement_table(label: str, spec: list[tuple[str, str, int]], expected: int):
    """§8.1.10 = §8.2.3 同一张表：期望值为**具体整数**，禁止「或」字多解。"""
    assert compute_discarded_customizations(_rows_for(spec), PRESET_SPECS) == expected, label


def test_order_tail_judgement_ignores_custom_rows_entirely():
    """全表自建（source=0）时 M 恒 0 —— 恢复默认不动自建行，也就无「丢弃定制」。"""
    spec = [(f"随手{i}", "mdi-x", 0) for i in range(6)]
    assert compute_discarded_customizations(_rows_for(spec), PRESET_SPECS) == 0


def _rows_from_api(rows: list[dict[str, Any]]) -> list[Category]:
    return [
        Category(
            name=r["name"],
            type=r["type"],
            icon=r["icon"],
            sort_order=r["sort_order"],
            is_preset=r["is_preset"],
            source=r["source"],
            user_id=r.get("user_id"),
        )
        for r in rows
    ]


@pytest.mark.asyncio
async def test_restore_reported_discarded_matches_shared_table(auth_client, aseeded):
    """服务层返回值与共享判据同输入同结果（黄金链路的 M=1 由 API 端到端复核）。"""
    global_food = await _global_row(aseeded, "餐饮")
    await auth_client.put(f"/api/categories/{global_food.id}", json={"icon": "mdi-coffee"})
    rows = await _visible(auth_client)
    expected = compute_discarded_customizations(_rows_from_api(rows), PRESET_SPECS)

    res = await auth_client.post("/api/categories/restore-defaults")
    assert res.json()["data"]["discarded_customizations"] == expected == 1
