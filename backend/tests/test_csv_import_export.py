"""Tests for M1: CSV import and export.

v1.4.3-boot3 M3 追加落库层用例（`TestCsvBoot3Writer`，任务 §5.1–§5.10b）：
统一列角色 + 请求契约（`columns` / `type_source` / `fallback_category`）+
`skipped_reasons` 五键 + CSV 标签查重。既有 native/cashew 用例断言一字不改（§5.2）。
"""

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.models.category import Category

pytestmark = pytest.mark.asyncio


async def _create_record(
    auth_client: AsyncClient, category_id: int, tag_id: int | None = None
) -> dict:
    """Helper to create a record."""
    payload = {
        "amount": 50.0,
        "type": "expense",
        "category_id": category_id,
        "consume_time": "2024-01-15 12:00",
        "note": "测试账单",
    }
    if tag_id:
        payload["tag_id"] = tag_id
    resp = await auth_client.post("/api/records", json=payload)
    assert resp.status_code == 200
    return resp.json()["data"]


# ── CSV Export ─────────────────────────────────────────────────────


class TestCsvExport:
    """Test CSV export functionality."""

    async def test_export_csv_utf8_bom(self, auth_client: AsyncClient, db_session):
        """Exported CSV should have UTF-8 BOM header."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/export/csv")
        assert resp.status_code == 200
        content = resp.content
        assert content[:3] == b"\xef\xbb\xbf"  # UTF-8 BOM

    async def test_export_csv_filename(self, auth_client: AsyncClient):
        """Exported CSV filename should follow pattern."""
        resp = await auth_client.get("/api/export/csv")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert "money_export_" in disposition
        assert ".csv" in disposition

    async def test_export_csv_columns(self, auth_client: AsyncClient, db_session):
        """Exported CSV should have correct column order."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/export/csv")
        content = resp.content.decode("utf-8-sig")
        lines = content.strip().split("\n")
        headers = lines[0].strip().split(",")
        assert headers == ["amount", "type", "category_name", "tag_name", "consume_time", "note"]

    async def test_export_csv_category_tag_names(self, auth_client: AsyncClient, db_session):
        """Exported CSV should include category and tag names."""
        # Create category via API
        resp = await auth_client.post("/api/categories", json={
            "name": "餐饮",
            "type": "expense",
            "icon": "mdi-food",
            "sort_order": 1,
        })
        cat_id = resp.json()["data"]["id"]

        # Create tag via API
        resp = await auth_client.post("/api/tags", json={
            "name": "午餐",
            "category_id": cat_id,
        })
        tag_id = resp.json()["data"]["id"]

        await _create_record(auth_client, cat_id, tag_id)

        resp = await auth_client.get("/api/export/csv")
        content = resp.content.decode("utf-8-sig")
        lines = content.strip().split("\n")
        assert len(lines) >= 2
        row = lines[1].strip()
        assert "餐饮" in row
        assert "午餐" in row

    async def test_export_csv_empty_data(self, auth_client: AsyncClient):
        """Export with no data should return CSV with headers only."""
        resp = await auth_client.get("/api/export/csv")
        assert resp.status_code == 200
        content = resp.content.decode("utf-8-sig")
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Only headers

    async def test_export_csv_only_current_user(
        self, auth_client_a: AsyncClient, auth_client_b: AsyncClient, db_session
    ):
        """Each user should only export their own records."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client_a, cat.id)
        await _create_record(auth_client_b, cat.id)

        resp_a = await auth_client_a.get("/api/export/csv")
        resp_b = await auth_client_b.get("/api/export/csv")

        content_a = resp_a.content.decode("utf-8-sig")
        content_b = resp_b.content.decode("utf-8-sig")

        # Each should have exactly 1 data row + 1 header
        assert len(content_a.strip().split("\n")) == 2
        assert len(content_b.strip().split("\n")) == 2


# ── CSV Import Preview ─────────────────────────────────────────────


class TestCsvImportPreview:
    """Test CSV import preview."""

    async def test_preview_native_format(self, auth_client: AsyncClient):
        """Should detect native CSV format."""
        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,expense,餐饮,午餐,2024-01-15 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "native"
        assert data["row_count"] == 1
        assert "餐饮" in data["categories_in_file"]
        assert "午餐" in data["tags_in_file"]

    async def test_preview_cashew_format(self, auth_client: AsyncClient):
        """Should detect Cashew CSV format."""
        csv_content = (
            "title,category name,amount,income,note,date\n"
            "午餐,餐饮,-50.0,false,测试,2024-01-15 12:00:00.000"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "cashew"

    async def test_preview_unknown_format(self, auth_client: AsyncClient):
        """**口径反转**（M3 §5.1，设计附录 B 点名的本批唯一例外，需求 A 的直接目标）。

        原断言：`col1,col2,col3` → `code != 0`（「无法识别的 CSV 格式」整文件拒绝）。
        新口径：未知表头**照常进预览**，`format == "custom"`、`columns` 每项 `role is None`，
        由用户在前端手选列角色。理由：「识别不了就整份拒绝」正是用户发起本批的抱怨，
        也是需求 A 要消除的行为；业务校验改由确认阶段抛中文 `ValueError`（§2.4）。
        影响面：仅本例（其余预览/确认用例断言一字不改，见 §5.2 回归护栏）。
        """
        csv_content = "col1,col2,col3\na,b,c"
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["format"] == "custom"
        assert data["headers"] == ["col1", "col2", "col3"]
        assert [col["role"] for col in data["columns"]] == [None, None, None]

    async def test_preview_empty_file(self, auth_client: AsyncClient):
        """Should reject empty CSV file."""
        files = {"file": ("test.csv", b"", "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        assert resp.json()["code"] != 0


# ── CSV Import Confirm ─────────────────────────────────────────────


class TestCsvImportConfirm:
    """Test CSV import confirm."""

    async def test_import_native_format(self, auth_client: AsyncClient, db_session):
        """Should import native CSV format correctly."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,expense,餐饮,,2024-01-15 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {"餐饮": {"action": "map", "target_id": cat.id}},
            "tag_mapping": {},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["imported_count"] == 1

    async def test_import_cashew_format(self, auth_client: AsyncClient, db_session):
        """Should import Cashew CSV with mapping."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        csv_content = (
            "title,category name,amount,income,note,date\n"
            "午餐,餐饮,-50.0,false,测试,2024-01-15 12:00:00.000"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "cashew",
            "category_mapping": {"餐饮": {"action": "map", "target_id": cat.id}},
            "tag_mapping": {"午餐": {"action": "map", "target_id": None}},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["imported_count"] == 1

    async def test_import_creates_new_category(self, auth_client: AsyncClient):
        """v1.4.3 M8：action='create' 不再携带 type，新建分类落统一列表 + 占位 type。"""
        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,expense,新分类,,2024-01-15 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {"新分类": {"action": "create"}},
            "tag_mapping": {},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["imported_count"] == 1

        cats = (await auth_client.get("/api/categories")).json()["data"]
        created = [c for c in cats if c["name"] == "新分类"]
        assert len(created) == 1
        assert created[0]["type"] == "expense"  # 占位值（D2），收支语义已废弃
        # 导入的分类收支共用：同一分类可挂收入交易
        rec = await auth_client.post("/api/records", json={
            "amount": 10.0,
            "type": "income",
            "category_id": created[0]["id"],
            "consume_time": "2024-02-01 12:00",
        })
        assert rec.status_code == 200

    async def test_import_create_mapping_ignores_legacy_type_field(
        self, auth_client: AsyncClient
    ):
        """M8 兼容：旧前端仍发 `type: income` → 忽略；同名重复导入不产生第二行。"""
        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,income,工资外快,,2024-01-15 12:00,测试\n"
            "60.0,expense,工资外快,,2024-01-16 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {"工资外快": {"action": "create", "type": "income"}},
            "tag_mapping": {},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["imported_count"] == 2

        cats = (await auth_client.get("/api/categories")).json()["data"]
        rows = [c for c in cats if c["name"] == "工资外快"]
        assert len(rows) == 1, "同名两行（原收入/支出语义）在统一列表下必须合流"
        assert rows[0]["type"] == "expense"

    async def test_import_skips_unmapped_rows(self, auth_client: AsyncClient):
        """Should skip rows without category mapping."""
        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,expense,未映射,,2024-01-15 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {},
            "tag_mapping": {},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["imported_count"] == 0
        assert resp.json()["data"]["skipped_count"] == 1

    async def test_import_records_history(self, auth_client: AsyncClient, db_session):
        """Import should be recorded in history."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,expense,餐饮,,2024-01-15 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {"餐饮": {"action": "map", "target_id": cat.id}},
            "tag_mapping": {},
        })

        resp = await auth_client.get("/api/history")
        types = [item["operation_type"] for item in resp.json()["data"]["items"]]
        assert "csv_import" in types

    async def test_import_deletes_cache(self, auth_client: AsyncClient, db_session):
        """Cache should be deleted after successful import."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        csv_content = (
            "amount,type,category_name,tag_name,consume_time,note\n"
            "50.0,expense,餐饮,,2024-01-15 12:00,测试"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {"餐饮": {"action": "map", "target_id": cat.id}},
            "tag_mapping": {},
        })

        # Try importing again with same cache_id - should fail
        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": cache_id,
            "format": "native",
            "category_mapping": {"餐饮": {"action": "map", "target_id": cat.id}},
            "tag_mapping": {},
        })
        assert resp.json()["code"] != 0


# ── Edge Cases ─────────────────────────────────────────────────────


class TestCsvEdgeCases:
    """Test edge cases."""

    async def test_expired_cache(self, auth_client: AsyncClient):
        """Should return error for non-existent cache."""
        resp = await auth_client.post("/api/import/csv", json={
            "cache_id": "nonexistent",
            "format": "native",
            "category_mapping": {},
            "tag_mapping": {},
        })
        assert resp.json()["code"] != 0


# ── v1.4.3-boot3 M3：落库层（统一列角色 / 请求契约 / 跳过原因 / 标签查重）──
#
# 用例名后缀即任务条目编号。表头原文逐字取设计 §0.4-10 / D21，**数据行一律合成**
# （红线 11：不引用本机未跟踪的现场样例目录、不抄任何真实账单单元格）。

FIXTURE_CSV_DIR = Path(__file__).parent / "fixtures" / "csv"
CASHEW_TEMPLATE_FIXTURE = FIXTURE_CSV_DIR / "cashew_import_template.csv"

WECHAT_HEADER = (
    "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,"
    "交易单号,商户单号,备注"
)
ALIPAY_HEADER = (
    "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,"
    "交易状态,交易订单号,商家订单号,备注,"
)
# Cashew 全量导出形态：**沿用 M1 的 10 列合成口径**（6 角色列 + 4 丢弃列）。
# 设计 §0.4-10 实际未逐字登记全量 17 列表头原文（D21 自指落空，M1 已发现并登记勘误），
# 故不凭记忆编列名（D6 精神）、不引用本机未跟踪样例目录的真实文件。
CASHEW_EXPORT_HEADER = (
    "title,category name,amount,income,note,date,subcategory name,account,currency,wallet"
)

SKIPPED_REASON_KEYS = {
    "invalid_amount",
    "invalid_date",
    "type_ignored",
    "type_unresolved",
    "category_unresolved",
}


def _fixture_bytes() -> bytes:
    """读 §5.0 夹具的**原始字节**（不 hardcode 内容、不读未跟踪的现场样例目录，D21）。"""
    return CASHEW_TEMPLATE_FIXTURE.read_bytes()


async def _preview(
    auth_client: AsyncClient, raw: bytes, filename: str = "test.csv"
) -> dict:
    """预览并返回 `data`（预览必须成功：本批不再整文件拒绝，需求 A）。"""
    resp = await auth_client.post(
        "/api/import/csv/preview", files={"file": (filename, raw, "text/csv")}
    )
    body = resp.json()
    assert body["code"] == 0, body["message"]
    return body["data"]


async def _confirm(
    auth_client: AsyncClient, cache_id: str, format_: str, **extra: object
) -> dict:
    """确认导入，返回整个响应体（含 `code`/`message`/`data`）。"""
    resp = await auth_client.post("/api/import/csv", json={
        "cache_id": cache_id,
        "format": format_,
        "category_mapping": {},
        "tag_mapping": {},
        **extra,
    })
    return resp.json()


async def _records(auth_client: AsyncClient) -> list[dict]:
    body = await auth_client.get("/api/records", params={"page_size": 100})
    return body.json()["data"]["items"]


def _tag_id(record: dict) -> int | None:
    """`/api/records` 列表项里标签是**富化对象** `tag`（`{id,name,category_id}`）或 None，
    没有裸 `tag_id` 字段（`_enrich_record` 的既有契约）→ 取 id 走这里。
    """
    tag = record["tag"]
    return tag["id"] if tag else None


async def _tags(auth_client: AsyncClient) -> list[dict]:
    return (await auth_client.get("/api/tags")).json()["data"]


async def _category_names(auth_client: AsyncClient) -> list[str]:
    body = await auth_client.get("/api/categories")
    return [c["name"] for c in body.json()["data"]]


async def _new_category(auth_client: AsyncClient, name: str) -> int:
    resp = await auth_client.post("/api/categories", json={
        "name": name, "type": "expense", "icon": "mdi-circle", "sort_order": 9,
    })
    return resp.json()["data"]["id"]


async def _new_tag(auth_client: AsyncClient, name: str, category_id: int) -> int:
    resp = await auth_client.post(
        "/api/tags", json={"name": name, "category_id": category_id}
    )
    return resp.json()["data"]["id"]


class TestCsvBoot3Writer:
    """M3 落库层：列角色解析、契约扩展、跳过原因、标签查重（任务 §5.3–§5.10b）。"""

    async def test_5_3_cashew_template_full_chain(self, auth_client: AsyncClient):
        """§5.3 Cashew 模板全链路：夹具字节 → 预览 → 确认 → 逐字段落库核对。

        夹具是 §5.0 入库的可跟踪副本；`-50`→expense、`250`→income（D10 符号法 +
        D13 `abs()`），`Title` 列落 `tag`（D9 模板 roles），微秒 6 位日期归一为 16 字符。
        """
        raw = _fixture_bytes()
        data = await _preview(auth_client, raw, "cashew_import_template.csv")
        assert data["format"] == "cashew_template"
        assert data["suggested_type_source"] == "sign"
        assert data["row_count"] == 2

        body = await _confirm(
            auth_client, data["cache_id"], "cashew_template",
            category_mapping={
                "Groceries": {"action": "create"},
                "Bills & Fees": {"action": "create"},
            },
            tag_mapping={
                "Fruits and Vegetables": {"action": "create", "category_id": None},
                "Monthly Income": {"action": "create", "category_id": None},
            },
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 2
        assert body["data"]["skipped_count"] == 0

        rows = sorted(await _records(auth_client), key=lambda r: r["amount"])
        assert [(r["amount"], r["type"]) for r in rows] == [
            (50.0, "expense"),
            (250.0, "income"),
        ]
        assert [r["consume_time"] for r in rows] == [
            "2026-09-24 11:07",
            "2026-09-24 11:07",
        ]
        assert rows[0]["note"] == "Paid with cash"
        assert rows[1]["note"] is None

        cats = {c["name"]: c["id"] for c in (await auth_client.get("/api/categories")).json()["data"]}
        assert rows[0]["category_id"] == cats["Groceries"]
        assert rows[1]["category_id"] == cats["Bills & Fees"]

        tags = sorted(_t["name"] for _t in await _tags(auth_client))
        assert tags == ["Fruits and Vegetables", "Monthly Income"]
        fruit_id = next(t["id"] for t in await _tags(auth_client) if t["name"] == "Fruits and Vegetables")
        assert _tag_id(rows[0]) == fruit_id

    async def test_5_4_export_then_import_round_trip(self, auth_client: AsyncClient):
        """§5.4 导出→导入闭环（需求 D 的总验）：带 BOM 的真实导出字节必须原样导回。

        旧实现在此处必报「无法识别的 CSV 格式」——`export_csv` 写 BOM（需求 D 成因，
        §0.4-2），`detect_and_decode` 用 `utf-8` 解码使 BOM 粘上首列表头。
        """
        cat_id = await _new_category(auth_client, "餐饮")
        tag_id = await _new_tag(auth_client, "午餐", cat_id)
        times = ["2024-01-15 12:00", "2024-01-16 18:30"]
        for consume_time in times:
            resp = await auth_client.post("/api/records", json={
                "amount": 50.0,
                "type": "expense",
                "category_id": cat_id,
                "tag_id": tag_id,
                "consume_time": consume_time,
                "note": "测试账单",
            })
            assert resp.status_code == 200

        exported = await auth_client.get("/api/export/csv")
        raw = exported.content
        assert raw[:3] == b"\xef\xbb\xbf"  # 带 BOM 的真实产物
        expected_rows = len(raw.decode("utf-8-sig").strip().split("\n")) - 1
        assert expected_rows == 2

        data = await _preview(auth_client, raw, "money_export.csv")
        assert data["format"] == "native"
        assert data["encoding"] == "utf-8-sig"

        before = {r["id"] for r in await _records(auth_client)}
        body = await _confirm(
            auth_client, data["cache_id"], "native",
            category_mapping={"餐饮": {"action": "create"}},
            tag_mapping={"午餐": {"action": "map", "target_id": tag_id}},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == expected_rows
        assert body["data"]["skipped_count"] == 0

        rows = [r for r in await _records(auth_client) if r["id"] not in before]
        assert sorted(r["consume_time"] for r in rows) == times
        assert all(
            r["amount"] == 50.0
            and r["type"] == "expense"
            and r["category_id"] == cat_id
            and _tag_id(r) == tag_id
            and r["note"] == "测试账单"
            for r in rows
        )

    async def test_5_5_manual_columns_non_default_order(self, auth_client: AsyncClient):
        """§5.5 手选列角色（需求 A 的落点）：`columns` 是权威位，非默认列序也能入库。

        同一份文件**不发** `columns` 时分类列推不出来（`分类` 不在别名表内，D6）→
        全行 `category_unresolved`，两相对照即证「手选覆盖方言推导」。
        """
        raw = (
            "日期,说明,流水号,金额,收支,分类\n"
            "2024-03-01 09:30,手选列序测试,A001,88.88,支出,买菜\n"
            "2024-03-02 10:00,第二行,A002,-6.40,收入,买菜"
        ).encode()

        data = await _preview(auth_client, raw)
        assert data["format"] == "custom"

        body = await _confirm(
            auth_client, data["cache_id"], "custom",
            columns={"consume_time": 0, "amount": 3, "type": 4, "note": 1, "category": 5},
            category_mapping={"买菜": {"action": "create"}},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 2
        rows = sorted(await _records(auth_client), key=lambda r: r["consume_time"])
        assert [(r["amount"], r["type"], r["note"]) for r in rows] == [
            (88.88, "expense", "手选列序测试"),
            (6.4, "income", "第二行"),
        ]

        data = await _preview(auth_client, raw)
        body = await _confirm(
            auth_client, data["cache_id"], "custom",
            category_mapping={"买菜": {"action": "create"}},
        )
        assert body["code"] == 0
        assert body["data"]["imported_count"] == 0
        assert body["data"]["skipped_reasons"]["category_unresolved"] == 2

    async def test_5_5_column_index_out_of_range(self, auth_client: AsyncClient):
        """§5.5 索引越界 → 中文 `ValueError` 经路由转 `PARAM_ERROR`（不依赖 422）。"""
        raw = (
            "日期,说明,流水号,金额,收支,分类\n"
            "2024-03-01 09:30,越界用例,A001,88.88,支出,买菜"
        ).encode()

        data = await _preview(auth_client, raw)
        body = await _confirm(
            auth_client, data["cache_id"], "custom",
            columns={"consume_time": 0, "amount": 9},
        )
        assert body["code"] != 0
        assert "列索引" in body["message"]
        assert body["data"] is None or body["data"] == {}

        data = await _preview(auth_client, raw)
        body = await _confirm(
            auth_client, data["cache_id"], "custom",
            columns={"consume_time": 0, "amount": -1},
        )
        assert body["code"] != 0
        assert "列索引" in body["message"]

    async def test_5_5_missing_required_role(self, auth_client: AsyncClient):
        """§5.5 必需角色缺失（用户把金额/时间列改成「不导入」）→ 显式拒绝。"""
        raw = (
            "日期,说明,流水号,金额,收支,分类\n"
            "2024-03-01 09:30,缺时间列,A001,88.88,支出,买菜"
        ).encode()

        data = await _preview(auth_client, raw)
        body = await _confirm(
            auth_client, data["cache_id"], "custom", columns={"amount": 3}
        )
        assert body["code"] != 0
        assert "必需列" in body["message"]

        data = await _preview(auth_client, raw)
        body = await _confirm(
            auth_client, data["cache_id"], "custom", columns={"consume_time": 0}
        )
        assert body["code"] != 0
        assert "必需列" in body["message"]

    async def test_5_6_fallback_category(self, auth_client: AsyncClient):
        """§5.6 `fallback_category`：微信账单无分类列 → 全部行归入所选分类（D8）。"""
        cat_id = await _new_category(auth_client, "默认归入")
        raw = (
            WECHAT_HEADER + "\n"
            "2024-04-01 09:15:00,零钱支付,某便利店,早餐,支出,¥12.50,零钱,支付成功,T0001,/,/\n"
            "2024-04-02 12:30:00,零钱支付,某商户,午餐,支出,¥28.16,零钱,支付成功,T0002,/,/"
        ).encode()

        data = await _preview(auth_client, raw)
        assert data["format"] == "wechat"
        assert "未识别到分类列：需指定默认分类" in data["warnings"]

        body = await _confirm(
            auth_client, data["cache_id"], "wechat",
            fallback_category={"action": "map", "target_id": cat_id},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 2
        rows = await _records(auth_client)
        assert len(rows) == 2
        assert all(r["category_id"] == cat_id for r in rows)
        assert sorted(r["note"] for r in rows) == ["午餐", "早餐"]

    async def test_5_6_without_fallback_category(self, auth_client: AsyncClient):
        """§5.6 未发 `fallback_category` → 不抛异常，全部行计 `category_unresolved`。"""
        raw = (
            WECHAT_HEADER + "\n"
            "2024-04-01 09:15:00,零钱支付,某便利店,早餐,支出,¥12.50,零钱,支付成功,T0001,/,/\n"
            "2024-04-02 12:30:00,零钱支付,某商户,午餐,收入,¥28.16,零钱,支付成功,T0002,/,/"
        ).encode()

        data = await _preview(auth_client, raw)
        body = await _confirm(auth_client, data["cache_id"], "wechat")
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 0
        assert body["data"]["skipped_count"] == 2
        reasons = body["data"]["skipped_reasons"]
        assert reasons["category_unresolved"] == 2
        assert set(reasons) == SKIPPED_REASON_KEYS
        assert await _records(auth_client) == []
        assert "默认归入" not in await _category_names(auth_client)

    async def test_5_7_type_source_four_states(self, auth_client: AsyncClient):
        """§5.7 `type_source` 四态（D10）：`column` 不可判**不回落 sign**；`all_*` 覆盖符号法。

        同一份混合符号文件跑四态：`column` 下 `看不懂` 行被跳过（sign 会静默判成支出，
        正是 D10 要防的「整表静默变支/收」）；`all_expense` / `all_income` 把全正数与
        全负数一律压成同向；入库金额恒为 `abs()` 后的两位小数（D13）。
        """
        raw = (
            WECHAT_HEADER + "\n"
            "2024-04-08 08:00:00,零钱支付,甲店,早餐,看不懂,¥-30.00,零钱,支付成功,T0008,/,/\n"
            "2024-04-09 09:00:00,零钱支付,乙店,午餐,支出,¥50.00,零钱,支付成功,T0009,/,/"
        ).encode()
        cat_id = await _new_category(auth_client, "四态归入")
        fallback = {"action": "map", "target_id": cat_id}
        cases: dict[str, tuple[list[tuple[float, str]], dict[str, int]]] = {
            "column": ([(50.0, "expense")], {"type_unresolved": 1}),
            "sign": ([(30.0, "expense"), (50.0, "income")], {}),
            "all_expense": ([(30.0, "expense"), (50.0, "expense")], {}),
            "all_income": ([(30.0, "income"), (50.0, "income")], {}),
        }

        for source, (expected, expected_skips) in cases.items():
            before = {r["id"] for r in await _records(auth_client)}
            data = await _preview(auth_client, raw)
            body = await _confirm(
                auth_client, data["cache_id"], "wechat",
                type_source=source, fallback_category=fallback,
            )
            assert body["code"] == 0, (source, body["message"])
            rows = [r for r in await _records(auth_client) if r["id"] not in before]
            assert sorted((r["amount"], r["type"]) for r in rows) == sorted(expected), source
            reasons = body["data"]["skipped_reasons"]
            assert {k: v for k, v in reasons.items() if v} == expected_skips, source
            assert body["data"]["skipped_count"] == sum(expected_skips.values()), source

    async def test_5_8_skipped_reasons_five_keys(self, auth_client: AsyncClient):
        """§5.8 五键计数（D12）：各构造一条脏行，断言逐键**非串扰**。"""
        raw = (
            ALIPAY_HEADER + "\n"
            "2024-04-10 10:00:00,餐饮美食,甲店,a***@b.com,早餐,支出,-,余额宝,交易成功,P010,MP010,/,\n"
            "04/11/2024,餐饮美食,乙店,a***@b.com,午餐,支出,20.00,余额宝,交易成功,P011,MP011,/,\n"
            "2024-04-12 10:00:00,餐饮美食,丙店,a***@b.com,车费,不计收支,30.00,余额宝,交易成功,P012,MP012,/,\n"
            "2024-04-13 10:00:00,餐饮美食,丁店,a***@b.com,杂项,看不懂,40.00,余额宝,交易成功,P013,MP013,/,\n"
            "2024-04-14 10:00:00,未映射分类,戊店,a***@b.com,东西,支出,50.00,余额宝,交易成功,P014,MP014,/,\n"
            "2024-04-15 10:00:00,餐饮美食,己店,a***@b.com,正餐,收入,60.00,余额宝,交易成功,P015,MP015,/,"
        ).encode()
        # 脏行依次对应五键：`-` 金额（D13 归 None）、`04/11/2024` 歧义日期（D15 不猜）、
        # `不计收支`（D11 忽略集）、`看不懂`（列值不可判）、`未映射分类`（无 fallback）。

        data = await _preview(auth_client, raw)
        assert data["format"] == "alipay"
        body = await _confirm(
            auth_client, data["cache_id"], "alipay",
            category_mapping={"餐饮美食": {"action": "create"}},
        )
        assert body["code"] == 0, body["message"]
        result = body["data"]
        assert result["imported_count"] == 1
        assert result["skipped_count"] == 5
        assert result["skipped_reasons"] == {
            "invalid_amount": 1,
            "invalid_date": 1,
            "type_ignored": 1,
            "type_unresolved": 1,
            "category_unresolved": 1,
        }
        rows = await _records(auth_client)
        assert [(r["amount"], r["type"]) for r in rows] == [(60.0, "income")]

    async def test_5_9_same_tag_created_once(self, auth_client: AsyncClient):
        """§5.9 标签 create 分支补查重（§0.4-6 缺陷闭环）：同名两行 → `tags` 只 1 行。"""
        raw = (
            ALIPAY_HEADER + "\n"
            "2024-04-20 10:00:00,餐饮美食,同名标签,a***@b.com,午餐,支出,10.00,余额宝,交易成功,P020,MP020,/,\n"
            "2024-04-21 10:00:00,餐饮美食,同名标签,a***@b.com,晚餐,支出,20.00,余额宝,交易成功,P021,MP021,/,"
        ).encode()

        data = await _preview(auth_client, raw)
        body = await _confirm(
            auth_client, data["cache_id"], "alipay",
            category_mapping={"餐饮美食": {"action": "create"}},
            tag_mapping={"同名标签": {"action": "create", "category_id": None}},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 2

        tags = [t for t in await _tags(auth_client) if t["name"] == "同名标签"]
        assert len(tags) == 1, "CSV 分支同名标签出现两次不得建两行（对齐 SQL 路径查重手法）"
        rows = await _records(auth_client)
        assert len(rows) == 2
        assert {_tag_id(r) for r in rows} == {tags[0]["id"]}

    async def test_5_10_alipay_bill(self, auth_client: AsyncClient):
        """§5.10 支付宝合成账单：`交易分类` 列自动映射、`不计收支` 计 `type_ignored`。

        表头逐字取设计 §0.4-10（**含末尾逗号 = 第 13 个空列**）；数据行全合成。
        """
        food_id = await _new_category(auth_client, "餐饮美食")
        taxi_id = await _new_category(auth_client, "交通出行")
        gift_id = await _new_category(auth_client, "亲友转账")
        raw = (
            ALIPAY_HEADER + "\n"
            "2024-04-05 10:00:00,餐饮美食,某餐馆,a***@b.com,午餐,支出,45.90,余额宝,交易成功,P0001,MP0001,/,\n"
            "2024-04-06 08:20:00,交通出行,某出行,a***@b.com,打车,支出,6.90,余额宝,交易成功,P0002,MP0002,/,\n"
            "2024-04-07 09:00:00,文化休闲,某平台,a***@b.com,会员,不计收支,0.00,余额宝,交易关闭,P0003,MP0003,/,\n"
            "2024-04-08 20:15:00,亲友转账,亲友,a***@b.com,红包,收入,1200.00,余额宝,交易成功,P0004,MP0004,/,"
        ).encode()

        data = await _preview(auth_client, raw)
        assert data["format"] == "alipay"
        assert data["row_count"] == 4
        assert sorted(data["categories_in_file"]) == [
            "交通出行",
            "亲友转账",
            "文化休闲",
            "餐饮美食",
        ], "分类清单按 role 定位列取值（含 `不计收支` 行的分类，预览与入库是两件事）"

        body = await _confirm(
            auth_client, data["cache_id"], "alipay",
            category_mapping={
                "餐饮美食": {"action": "map", "target_id": food_id},
                "交通出行": {"action": "map", "target_id": taxi_id},
                "亲友转账": {"action": "map", "target_id": gift_id},
            },
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 3
        assert body["data"]["skipped_reasons"]["type_ignored"] == 1

        rows = {r["note"]: r for r in await _records(auth_client)}
        assert set(rows) == {"午餐", "打车", "红包"}
        assert rows["打车"]["amount"] == 6.9, "裸数字 6.90 清洗为两位小数（D13）"
        assert rows["午餐"]["amount"] == 45.9
        assert rows["红包"]["amount"] == 1200.0
        assert rows["红包"]["type"] == "income"
        assert rows["午餐"]["category_id"] == food_id
        assert rows["打车"]["category_id"] == taxi_id
        assert all(r["tag"] is None for r in rows.values())

    async def test_5_10_wechat_bill(self, auth_client: AsyncClient):
        """§5.10 微信合成账单：无分类列走 `fallback_category`；`/` 中性行计 `type_ignored`（D31）。

        表头逐字取设计 §0.4-10 的 11 列原文；金额列带 `¥`（`商品`→note、`交易对方`→tag，
        `交易类型` 按 D9 丢弃）。数据行全合成。
        """
        cat_id = await _new_category(auth_client, "账单归入")
        raw = (
            WECHAT_HEADER + "\n"
            "2024-04-01 09:15:00,零钱支付,某便利店,早餐,支出,¥12.50,零钱,支付成功,T0001,/,/\n"
            "2024-04-02 12:30:00,零钱支付,某商户,午餐,支出,¥28.16,零钱,支付成功,T0002,/,/\n"
            "2024-04-03 18:00:00,零钱支付,张三,转账,/,¥0.00,零钱,已到账,T0003,/,/\n"
            "2024-04-04 21:00:00,零钱支付,李四,退款,收入,¥6.60,零钱,已退款,T0004,/,/"
        ).encode()

        data = await _preview(auth_client, raw)
        assert data["format"] == "wechat"
        assert data["row_count"] == 4

        body = await _confirm(
            auth_client, data["cache_id"], "wechat",
            fallback_category={"action": "map", "target_id": cat_id},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 3
        assert body["data"]["skipped_reasons"]["type_ignored"] == 1, "`/` 记 type_ignored 而非 type_unresolved"

        rows = {r["note"]: r for r in await _records(auth_client)}
        assert set(rows) == {"早餐", "午餐", "退款"}
        assert rows["午餐"]["amount"] == 28.16, "`¥28.16` 剥货币符号后两位小数入库"
        assert rows["早餐"]["amount"] == 12.5
        assert rows["退款"]["type"] == "income"
        assert all(r["category_id"] == cat_id for r in rows.values())

    async def test_5_10b_slash_placeholder_creates_nothing(self, auth_client: AsyncClient):
        """§5.10b `/` 不再产生分类/标签（任务 §2.6 闭环，D31 一手实测占位符）。"""
        cat_id = await _new_category(auth_client, "斜杠归入")
        raw = (
            ALIPAY_HEADER + "\n"
            "2024-04-25 08:00:00,/,/,a***@b.com,打车,支出,9.90,余额宝,交易成功,P025,MP025,/,\n"
            "2024-04-26 08:00:00,购物,某店,a***@b.com,买书,支出,19.90,余额宝,交易成功,P026,MP026,/,"
        ).encode()

        data = await _preview(auth_client, raw)
        assert data["categories_in_file"] == ["购物"], "`/` 按空占位处理，不进 categories_in_file"
        assert "/" not in data["tags_in_file"]

        body = await _confirm(
            auth_client, data["cache_id"], "alipay",
            category_mapping={"购物": {"action": "create"}},
            tag_mapping={"某店": {"action": "create", "category_id": None}},
            fallback_category={"action": "map", "target_id": cat_id},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 2

        assert "/" not in await _category_names(auth_client), "禁止建出名为 `/` 的分类"
        assert "/" not in [t["name"] for t in await _tags(auth_client)], "禁止建出名为 `/` 的标签"
        rows = {r["note"]: r for r in await _records(auth_client)}
        assert rows["打车"]["category_id"] == cat_id, "分类列为 `/` 的行同样走 fallback"
        assert rows["买书"]["category_id"] != cat_id

    async def test_3_5_cashew_full_export_equivalence(self, auth_client: AsyncClient):
        """任务 §3.5：Cashew 全量导出形态经新路径解析，与旧路径**逐位一致**。

        形态 = `income` 布尔列 + 负数金额 + 3 位毫秒日期。旧口径：`convert_cashew_amount`
        的 `round(abs(float(x)), 2)`、`convert_cashew_type` 的 `=="true"`、
        `convert_cashew_date` 的 `value[:16]`；新口径：`parse_amount`+D13 `abs()`、
        `resolve_type` 的布尔集、`parse_time` 的 `%f` 白名单——三者在本用例上产出同值。
        列集按 M1 的 10 列合成口径（17 列原文未一手登记，见上方注释）。
        """
        raw = (
            CASHEW_EXPORT_HEADER + "\n"
            "午餐,餐饮,-50.0,false,测试,2024-01-15 12:00:00.000,子分类,账户,人民币,钱包\n"
            "工资,收入,1200.5,true,月薪,2024-01-16 09:05:00.123,,人民币,"
        ).encode()

        data = await _preview(auth_client, raw)
        assert data["format"] == "cashew"
        assert data["suggested_type_source"] == "column"

        body = await _confirm(
            auth_client, data["cache_id"], "cashew",
            category_mapping={"餐饮": {"action": "create"}, "收入": {"action": "create"}},
            tag_mapping={"午餐": {"action": "create", "category_id": None}},
        )
        assert body["code"] == 0, body["message"]
        assert body["data"]["imported_count"] == 2

        rows = sorted(await _records(auth_client), key=lambda r: r["consume_time"])
        assert [(r["amount"], r["type"], r["consume_time"]) for r in rows] == [
            (50.0, "expense", "2024-01-15 12:00"),
            (1200.5, "income", "2024-01-16 09:05"),
        ]
        assert _tag_id(rows[0]) is not None and _tag_id(rows[1]) is None
