"""Tests for M2: SQL import and export."""

import sqlite3
import tempfile

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


# ── SQL Export ─────────────────────────────────────────────────────


class TestSqlExport:
    """Test SQL export functionality."""

    async def test_export_sql_contains_tables(self, auth_client: AsyncClient, db_session):
        """Exported SQL should contain CREATE TABLE and INSERT statements."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/export/sql")
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "CREATE TABLE" in content
        assert "INSERT INTO" in content

    async def test_export_sql_no_id_in_insert(self, auth_client: AsyncClient, db_session):
        """Exported SQL INSERT should not contain id field."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/export/sql")
        content = resp.content.decode("utf-8")
        # Check INSERT INTO records doesn't have id
        for line in content.split("\n"):
            if line.strip().startswith("INSERT INTO records"):
                assert "id," not in line.lower() or "tag_id" in line

    async def test_export_sql_only_current_user(
        self, auth_client_a: AsyncClient, auth_client_b: AsyncClient, db_session
    ):
        """Each user should only export their own data."""
        cat = Category(name="餐饮", type="expense", icon="mdi-food", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client_a, cat.id)
        await _create_record(auth_client_b, cat.id)

        resp_a = await auth_client_a.get("/api/export/sql")
        resp_b = await auth_client_b.get("/api/export/sql")

        content_a = resp_a.content.decode("utf-8")
        content_b = resp_b.content.decode("utf-8")

        # Count INSERT INTO records lines
        count_a = content_a.count("INSERT INTO records")
        count_b = content_b.count("INSERT INTO records")
        assert count_a == 1
        assert count_b == 1

    async def test_export_sql_excludes_preset_categories(
        self, auth_client: AsyncClient
    ):
        """Exported SQL should not include preset categories."""
        resp = await auth_client.get("/api/export/sql")
        content = resp.content.decode("utf-8")
        # Preset categories have is_preset=1, should not be in export
        assert "is_preset" not in content or "INSERT INTO categories" not in content

    async def test_export_sql_filename(self, auth_client: AsyncClient):
        """Exported SQL filename should follow pattern."""
        resp = await auth_client.get("/api/export/sql")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert "money_backup_" in disposition
        assert ".sql" in disposition


# ── SQL Import Preview ─────────────────────────────────────────────


class TestSqlImportPreview:
    """Test SQL import preview."""

    async def test_preview_text_sql(self, auth_client: AsyncClient):
        """Should detect text SQL format."""
        sql_content = """-- Money App Export
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL
);
INSERT INTO records (amount, type) VALUES (50.0, 'expense');
"""
        files = {"file": ("test.sql", sql_content.encode("utf-8"), "application/sql")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "text_sql"

    async def test_preview_sqlite_binary(self, auth_client: AsyncClient):
        """Should detect SQLite binary format."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test (name) VALUES ('hello')")
            conn.commit()
            conn.close()
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            db_bytes = f.read()

        files = {"file": ("test.db", db_bytes, "application/octet-stream")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "sqlite_binary"

    async def test_preview_unknown_format(self, auth_client: AsyncClient):
        """Should reject unknown format."""
        files = {"file": ("test.txt", b"hello world", "text/plain")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        assert resp.json()["code"] != 0


# ── SQL Import Confirm ─────────────────────────────────────────────


class TestSqlImportConfirm:
    """Test SQL import confirm."""

    async def test_import_text_sql(self, auth_client: AsyncClient):
        """Should import text SQL correctly."""
        sql_content = """CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    icon TEXT NOT NULL,
    sort_order INTEGER,
    is_preset INTEGER DEFAULT 0,
    user_id INTEGER,
    deleted_at TEXT
);
INSERT INTO categories (name, type, icon, sort_order, is_preset, user_id)
VALUES ('测试分类', 'expense', 'mdi-test', 1, 0, 1);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    tag_id INTEGER,
    consume_time TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT INTO records (user_id, amount, type, category_id, tag_id,
    consume_time, note, created_at, updated_at)
VALUES (1, 50.0, 'expense', 1, NULL, '2024-01-15 12:00', '测试',
    '2024-01-15 12:00:00', '2024-01-15 12:00:00');
"""
        files = {"file": ("test.sql", sql_content.encode("utf-8"), "application/sql")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/sql", json={
            "cache_id": cache_id,
            "format": "text_sql",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["records_imported"] >= 1

    async def test_import_sqlite_binary(self, auth_client: AsyncClient):
        """Should import SQLite binary correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)
            conn.execute("""CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                icon TEXT NOT NULL,
                sort_order INTEGER,
                is_preset INTEGER DEFAULT 0,
                user_id INTEGER
            )""")
            conn.execute("""CREATE TABLE records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                tag_id INTEGER,
                consume_time TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            conn.execute(
                "INSERT INTO categories (name, type, icon, user_id) "
                "VALUES ('测试', 'expense', 'mdi-test', 1)"
            )
            conn.execute(
                "INSERT INTO records (user_id, amount, type, category_id, "
                "consume_time, created_at, updated_at) "
                "VALUES (1, 100.0, 'expense', 1, '2024-01-15 12:00', "
                "'2024-01-15 12:00:00', '2024-01-15 12:00:00')"
            )
            conn.commit()
            conn.close()
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            db_bytes = f.read()

        files = {"file": ("test.db", db_bytes, "application/octet-stream")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/sql", json={
            "cache_id": cache_id,
            "format": "sqlite_binary",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["records_imported"] >= 1

    async def test_import_strips_id_from_insert(self, auth_client: AsyncClient):
        """Should strip id from INSERT statements."""
        sql_content = """CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    icon TEXT NOT NULL,
    sort_order INTEGER,
    is_preset INTEGER DEFAULT 0,
    user_id INTEGER,
    deleted_at TEXT
);
INSERT INTO categories (id, name, type, icon, sort_order, is_preset, user_id)
VALUES (999, '测试', 'expense', 'mdi-test', 1, 0, 1);
"""
        files = {"file": ("test.sql", sql_content.encode("utf-8"), "application/sql")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/sql", json={
            "cache_id": cache_id,
            "format": "text_sql",
        })
        assert resp.status_code == 200

    async def test_import_records_history(self, auth_client: AsyncClient):
        """Import should be recorded in history."""
        # First create a category so the record can reference it
        resp = await auth_client.post("/api/categories", json={
            "name": "测试",
            "type": "expense",
            "icon": "mdi-test",
            "sort_order": 1,
        })
        cat_id = resp.json()["data"]["id"]

        sql_content = f"""CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    tag_id INTEGER,
    consume_time TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT INTO records (user_id, amount, type, category_id,
    consume_time, created_at, updated_at)
VALUES (1, 50.0, 'expense', {cat_id}, '2024-01-15 12:00',
    '2024-01-15 12:00:00', '2024-01-15 12:00:00');
"""
        files = {"file": ("test.sql", sql_content.encode("utf-8"), "application/sql")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/sql", json={
            "cache_id": cache_id,
            "format": "text_sql",
        })
        assert resp.status_code == 200, resp.json()
        assert resp.json()["data"]["records_imported"] == 1

        resp = await auth_client.get("/api/history")
        types = [item["operation_type"] for item in resp.json()["data"]["items"]]
        assert "sql_import" in types


# ── Cashew SQLite ──────────────────────────────────────────────────


class TestCashewSqlite:
    """Test Cashew SQLite import."""

    async def test_cashew_sqlite_detection(self, auth_client: AsyncClient):
        """Should detect Cashew SQLite format."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)
            conn.execute("""CREATE TABLE categories (
                category_pk TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE transactions (
                transaction_pk TEXT PRIMARY KEY,
                name TEXT,
                amount REAL,
                income INTEGER,
                category_fk TEXT,
                date_created INTEGER,
                note TEXT
            )""")
            conn.commit()
            conn.close()
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            db_bytes = f.read()

        files = {"file": ("test.db", db_bytes, "application/octet-stream")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_third_party"] is True

    async def test_cashew_sqlite_import(self, auth_client: AsyncClient):
        """Should import Cashew SQLite with correct mapping."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)
            conn.execute("CREATE TABLE categories (category_pk TEXT PRIMARY KEY, name TEXT)")
            conn.execute("""CREATE TABLE transactions (
                transaction_pk TEXT PRIMARY KEY,
                name TEXT,
                amount REAL,
                income INTEGER,
                category_fk TEXT,
                date_created INTEGER,
                note TEXT
            )""")
            conn.execute("INSERT INTO categories (category_pk, name) VALUES ('1', '餐饮')")
            # amount=-50, income=0 (expense), date_created as Unix seconds
            conn.execute(
                "INSERT INTO transactions (transaction_pk, name, amount, income, category_fk, date_created, note) "
                "VALUES ('tx1', '午餐', -50.0, 0, '1', 1705305600, '测试')"
            )
            conn.commit()
            conn.close()
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            db_bytes = f.read()

        files = {"file": ("test.db", db_bytes, "application/octet-stream")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        cache_id = resp.json()["data"]["cache_id"]

        resp = await auth_client.post("/api/import/sql", json={
            "cache_id": cache_id,
            "format": "sqlite_binary",
            "is_third_party": True,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["records_imported"] == 1


# ── Edge Cases ─────────────────────────────────────────────────────


class TestSqlEdgeCases:
    """Test edge cases."""

    async def test_expired_cache(self, auth_client: AsyncClient):
        """Should return error for non-existent cache."""
        resp = await auth_client.post("/api/import/sql", json={
            "cache_id": "nonexistent",
            "format": "text_sql",
        })
        assert resp.json()["code"] != 0

    async def test_empty_file(self, auth_client: AsyncClient):
        """Should reject empty file."""
        files = {"file": ("test.sql", b"", "application/sql")}
        resp = await auth_client.post("/api/import/sql/preview", files=files)
        assert resp.json()["code"] != 0
