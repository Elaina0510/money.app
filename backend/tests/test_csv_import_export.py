"""Tests for M1: CSV import and export."""

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
        """Should reject unknown CSV format."""
        csv_content = "col1,col2,col3\na,b,c"
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        resp = await auth_client.post("/api/import/csv/preview", files=files)
        assert resp.json()["code"] != 0

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
        """Should create new category when action='create'."""
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
            "category_mapping": {"新分类": {"action": "create", "type": "expense"}},
            "tag_mapping": {},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["imported_count"] == 1

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
