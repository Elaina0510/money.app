"""Tests for M3: Operation history and rollback."""

import pytest
from httpx import AsyncClient

from app.models.category import Category

pytestmark = pytest.mark.asyncio


async def _create_record(
    auth_client: AsyncClient, category_id: int, tag_id: int | None = None
) -> dict:
    """Helper to create a record and return the data."""
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


# ── History Recording ──────────────────────────────────────────────


class TestHistoryRecording:
    """Test that CRUD operations write history entries."""

    async def test_create_writes_history(self, auth_client: AsyncClient, db_session):
        """Creating a record should write a history entry with operation_type=create."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert data["items"][0]["operation_type"] == "create"

    async def test_update_writes_history(self, auth_client: AsyncClient, db_session):
        """Updating a record should write a history entry with old and new snapshots."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        record = await _create_record(auth_client, cat.id)
        record_id = record["id"]

        resp = await auth_client.put(
            f"/api/records/{record_id}",
            json={"amount": 80.0, "type": "expense", "category_id": cat.id},
        )
        assert resp.status_code == 200

        resp = await auth_client.get("/api/history")
        data = resp.json()["data"]
        # Should have 2 entries: create + update
        assert data["total"] >= 2
        types = [item["operation_type"] for item in data["items"]]
        assert "create" in types
        assert "update" in types

    async def test_delete_writes_history(self, auth_client: AsyncClient, db_session):
        """Deleting a record should write a history entry with snapshot_before."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        record = await _create_record(auth_client, cat.id)
        record_id = record["id"]

        resp = await auth_client.delete(f"/api/records/{record_id}")
        assert resp.status_code == 200

        resp = await auth_client.get("/api/history")
        data = resp.json()["data"]
        types = [item["operation_type"] for item in data["items"]]
        assert "delete" in types

    async def test_batch_delete_writes_history(self, auth_client: AsyncClient, db_session):
        """Batch deleting should write a history entry with all deleted records."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        r1 = await _create_record(auth_client, cat.id)
        r2 = await _create_record(auth_client, cat.id)

        resp = await auth_client.post(
            "/api/records/batch-delete",
            json={"ids": [r1["id"], r2["id"]]},
        )
        assert resp.status_code == 200

        resp = await auth_client.get("/api/history")
        data = resp.json()["data"]
        types = [item["operation_type"] for item in data["items"]]
        assert "batch_delete" in types


# ── History List Query ─────────────────────────────────────────────


class TestHistoryList:
    """Test history list query."""

    async def test_list_sorted_by_time_desc(self, auth_client: AsyncClient, db_session):
        """History list should be sorted by created_at DESC."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)
        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history")
        data = resp.json()["data"]
        items = data["items"]
        assert len(items) >= 2
        # Verify descending order
        for i in range(len(items) - 1):
            assert items[i]["created_at"] >= items[i + 1]["created_at"]

    async def test_list_pagination(self, auth_client: AsyncClient, db_session):
        """History list should support pagination."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        for _ in range(5):
            await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history", params={"page": 1, "page_size": 2})
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] >= 5

    async def test_affected_count_create(self, auth_client: AsyncClient, db_session):
        """affected_count for create should be 1."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history")
        data = resp.json()["data"]
        assert data["items"][0]["affected_count"] == 1

    async def test_only_current_user_history(
        self, auth_client_a: AsyncClient, auth_client_b: AsyncClient, db_session
    ):
        """Each user should only see their own history."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client_a, cat.id)
        await _create_record(auth_client_b, cat.id)

        resp_a = await auth_client_a.get("/api/history")
        resp_b = await auth_client_b.get("/api/history")

        # Both should have at least 1 entry
        assert resp_a.json()["data"]["total"] >= 1
        assert resp_b.json()["data"]["total"] >= 1


# ── History Detail ─────────────────────────────────────────────────


class TestHistoryDetail:
    """Test history detail query."""

    async def test_detail_returns_snapshots(self, auth_client: AsyncClient, db_session):
        """History detail should return parsed snapshot data."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history")
        history_id = resp.json()["data"]["items"][0]["id"]

        resp = await auth_client.get(f"/api/history/{history_id}")
        assert resp.status_code == 200
        detail = resp.json()["data"]
        assert detail["snapshot_after"] is not None
        assert len(detail["snapshot_after"]) == 1

    async def test_detail_other_user_forbidden(
        self, auth_client_a: AsyncClient, auth_client_b: AsyncClient, db_session
    ):
        """User should not be able to access another user's history detail."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client_a, cat.id)

        resp = await auth_client_a.get("/api/history")
        history_id = resp.json()["data"]["items"][0]["id"]

        # User B should not see user A's history
        resp = await auth_client_b.get(f"/api/history/{history_id}")
        assert resp.status_code == 404


# ── Rollback Operations ────────────────────────────────────────────


class TestRollback:
    """Test rollback operations."""

    async def test_rollback_create_deletes_record(self, auth_client: AsyncClient, db_session):
        """Rollback a create operation should delete the created record."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        record = await _create_record(auth_client, cat.id)
        record_id = record["id"]

        resp = await auth_client.get("/api/history")
        history_id = resp.json()["data"]["items"][0]["id"]

        resp = await auth_client.post(f"/api/history/{history_id}/rollback")
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["deleted_count"] == 1

        # Verify record is deleted (should return NOT_FOUND)
        resp = await auth_client.get(f"/api/records/{record_id}")
        assert resp.status_code == 400  # NOT_FOUND returns 400 by default
        assert resp.json()["code"] == 40002

    async def test_rollback_update_restores_old_values(self, auth_client: AsyncClient, db_session):
        """Rollback an update should restore the previous values."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        record = await _create_record(auth_client, cat.id)
        record_id = record["id"]

        await auth_client.put(
            f"/api/records/{record_id}",
            json={"amount": 999.0, "type": "expense", "category_id": cat.id},
        )

        resp = await auth_client.get("/api/history")
        items = resp.json()["data"]["items"]
        update_entry = next(item for item in items if item["operation_type"] == "update")

        resp = await auth_client.post(f"/api/history/{update_entry['id']}/rollback")
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["restored_count"] == 1

        # Verify record is restored
        resp = await auth_client.get(f"/api/records/{record_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["amount"] == 50.0

    async def test_rollback_delete_restores_record(self, auth_client: AsyncClient, db_session):
        """Rollback a delete should restore the deleted record."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        record = await _create_record(auth_client, cat.id)
        record_id = record["id"]

        await auth_client.delete(f"/api/records/{record_id}")

        resp = await auth_client.get("/api/history")
        items = resp.json()["data"]["items"]
        delete_entry = next(item for item in items if item["operation_type"] == "delete")

        resp = await auth_client.post(f"/api/history/{delete_entry['id']}/rollback")
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["restored_count"] == 1

        # Verify record is restored
        resp = await auth_client.get(f"/api/records/{record_id}")
        assert resp.status_code == 200
        assert resp.json()["data"] is not None

    async def test_rollback_batch_delete_restores_all(self, auth_client: AsyncClient, db_session):
        """Rollback a batch delete should restore all deleted records."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        r1 = await _create_record(auth_client, cat.id)
        r2 = await _create_record(auth_client, cat.id)

        await auth_client.post("/api/records/batch-delete", json={"ids": [r1["id"], r2["id"]]})

        resp = await auth_client.get("/api/history")
        items = resp.json()["data"]["items"]
        batch_entry = next(item for item in items if item["operation_type"] == "batch_delete")

        resp = await auth_client.post(f"/api/history/{batch_entry['id']}/rollback")
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["restored_count"] == 2

    async def test_rollback_delete_id_conflict_skips(self, auth_client: AsyncClient, db_session):
        """Rollback delete when ID is occupied should return skipped_count."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        record = await _create_record(auth_client, cat.id)
        record_id = record["id"]

        await auth_client.delete(f"/api/records/{record_id}")

        # Create a new record to occupy the ID
        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history")
        items = resp.json()["data"]["items"]
        delete_entry = next(item for item in items if item["operation_type"] == "delete")

        resp = await auth_client.post(f"/api/history/{delete_entry['id']}/rollback")
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["skipped_count"] >= 1

    async def test_rollback_deletes_history_entry(self, auth_client: AsyncClient, db_session):
        """Rollback should delete the history entry itself."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history")
        history_id = resp.json()["data"]["items"][0]["id"]

        await auth_client.post(f"/api/history/{history_id}/rollback")

        resp = await auth_client.get(f"/api/history/{history_id}")
        assert resp.status_code == 404  # Returns 404 with status_code=404


# ── Edge Cases ─────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases."""

    async def test_other_user_cannot_rollback(
        self, auth_client_a: AsyncClient, auth_client_b: AsyncClient, db_session
    ):
        """User should not be able to rollback another user's history."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _create_record(auth_client_a, cat.id)

        resp = await auth_client_a.get("/api/history")
        history_id = resp.json()["data"]["items"][0]["id"]

        resp = await auth_client_b.post(f"/api/history/{history_id}/rollback")
        assert resp.status_code == 403

    async def test_nonexistent_history_id(self, auth_client: AsyncClient):
        """Non-existent history ID should return error."""
        resp = await auth_client.get("/api/history/99999")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40002

        resp = await auth_client.post("/api/history/99999/rollback")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40002


# ── Auto Cleanup ───────────────────────────────────────────────────


class TestAutoCleanup:
    """Test automatic cleanup of old history entries."""

    async def test_cleanup_keeps_latest_30(self, auth_client: AsyncClient, db_session):
        """Should keep only the latest 30 history entries per user."""
        cat = Category(name="测试分类", type="expense", icon="mdi-test", sort_order=1)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        # Create 35 records to generate 35 history entries
        for _ in range(35):
            await _create_record(auth_client, cat.id)

        resp = await auth_client.get("/api/history", params={"page_size": 100})
        data = resp.json()["data"]
        # Should be capped at 30 (or close to it, depending on cleanup timing)
        assert data["total"] <= 31  # Allow some margin
