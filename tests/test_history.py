"""Tests for /api/v1/history/* endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from tests.conftest import make_mock_db, make_user


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_history_row(**kwargs):
    """Build a minimal OperationHistory-like object for mock returns."""
    from app.db.models.operation_history import OperationHistory

    row = OperationHistory(
        user_id=kwargs.get("user_id", uuid.uuid4()),
        tool_id=kwargs.get("tool_id", "uppercase"),
        tool_label=kwargs.get("tool_label", "Uppercase"),
        tool_type=kwargs.get("tool_type", "api"),
        input_preview=kwargs.get("input_preview", "hello"),
        output_preview=kwargs.get("output_preview", "HELLO"),
        input_length=kwargs.get("input_length", 5),
        output_length=kwargs.get("output_length", 5),
        status=kwargs.get("status", "success"),
    )
    row.id = kwargs.get("id", uuid.uuid4())
    row.created_at = kwargs.get("created_at", datetime.now(UTC))
    return row


# ── GET /history ──────────────────────────────────────────────────────────────


def test_list_history_empty(client, mock_db):
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        return list_result

    mock_db.execute.side_effect = execute_side_effect

    resp = client.get("/api/v1/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["has_more"] is False


def test_list_history_with_items(client, mock_db, fake_user):
    row = make_history_row(user_id=fake_user.id)

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [row]

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        return list_result

    mock_db.execute.side_effect = execute_side_effect

    resp = client.get("/api/v1/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["tool_id"] == "uppercase"


def test_list_history_pagination(client, mock_db):
    count_result = MagicMock()
    count_result.scalar.return_value = 50

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        return list_result

    mock_db.execute.side_effect = execute_side_effect

    resp = client.get("/api/v1/history?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 50
    assert data["has_more"] is True


def test_list_history_filter_by_tool(client, mock_db):
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        return list_result

    mock_db.execute.side_effect = execute_side_effect

    resp = client.get("/api/v1/history?tool_id=uppercase")
    assert resp.status_code == 200


def test_list_history_requires_auth(unauth_client):
    resp = unauth_client.get("/api/v1/history")
    assert resp.status_code == 401


# ── POST /history ─────────────────────────────────────────────────────────────


def test_record_operation_success(client, mock_db, fake_user):
    resp = client.post(
        "/api/v1/history",
        json={
            "tool_id": "uppercase",
            "tool_label": "Uppercase",
            "tool_type": "api",
            "input_preview": "hello",
            "output_preview": "HELLO",
            "input_length": 5,
            "output_length": 5,
            "status": "success",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tool_id"] == "uppercase"
    assert data["status"] == "success"


def test_record_operation_missing_fields(client):
    resp = client.post("/api/v1/history", json={"tool_id": "uppercase"})
    assert resp.status_code == 422


def test_record_operation_requires_auth(unauth_client):
    resp = unauth_client.post(
        "/api/v1/history",
        json={
            "tool_id": "uppercase",
            "tool_label": "Uppercase",
            "tool_type": "api",
            "input_preview": "hello",
            "output_preview": "HELLO",
            "input_length": 5,
            "output_length": 5,
            "status": "success",
        },
    )
    assert resp.status_code == 401


# ── GET /history/stats/summary ────────────────────────────────────────────────


def test_get_stats_empty(client, mock_db):
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    breakdown_result = MagicMock()
    breakdown_result.all.return_value = []

    recent_result = MagicMock()
    recent_result.scalars.return_value.all.return_value = []

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        if call_count == 2:
            return breakdown_result
        return recent_result

    mock_db.execute.side_effect = execute_side_effect

    resp = client.get("/api/v1/history/stats/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_operations"] == 0
    assert data["tools_breakdown"] == {}
    assert data["recent_tools"] == []


def test_get_stats_with_data(client, mock_db):
    count_result = MagicMock()
    count_result.scalar.return_value = 10

    breakdown_result = MagicMock()
    breakdown_result.all.return_value = [("uppercase", 7), ("lowercase", 3)]

    recent_result = MagicMock()
    recent_result.scalars.return_value.all.return_value = ["uppercase", "lowercase"]

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        if call_count == 2:
            return breakdown_result
        return recent_result

    mock_db.execute.side_effect = execute_side_effect

    resp = client.get("/api/v1/history/stats/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_operations"] == 10
    assert "uppercase" in data["tools_breakdown"]


def test_get_stats_requires_auth(unauth_client):
    resp = unauth_client.get("/api/v1/history/stats/summary")
    assert resp.status_code == 401


# ── DELETE /history ───────────────────────────────────────────────────────────


def test_clear_history_success(client, mock_db):
    resp = client.delete("/api/v1/history")
    assert resp.status_code == 204
    mock_db.commit.assert_awaited()


def test_clear_history_requires_auth(unauth_client):
    resp = unauth_client.delete("/api/v1/history")
    assert resp.status_code == 401


# ── GET /history/{entry_id} ───────────────────────────────────────────────────


def test_get_single_entry_found(client, mock_db, fake_user):
    entry_id = uuid.uuid4()
    row = make_history_row(id=entry_id, user_id=fake_user.id)
    mock_db.get.return_value = row

    resp = client.get(f"/api/v1/history/{entry_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(entry_id)


def test_get_single_entry_not_found(client, mock_db):
    mock_db.get.return_value = None
    entry_id = uuid.uuid4()
    resp = client.get(f"/api/v1/history/{entry_id}")
    assert resp.status_code == 404


def test_get_single_entry_wrong_user(client, mock_db):
    # Row belongs to a different user
    row = make_history_row(user_id=uuid.uuid4())  # different user_id
    mock_db.get.return_value = row
    entry_id = row.id
    resp = client.get(f"/api/v1/history/{entry_id}")
    assert resp.status_code == 404


def test_get_single_entry_invalid_uuid(client):
    resp = client.get("/api/v1/history/not-a-uuid")
    assert resp.status_code == 422


def test_get_single_entry_requires_auth(unauth_client):
    resp = unauth_client.get(f"/api/v1/history/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── DELETE /history/{entry_id} ────────────────────────────────────────────────


def test_delete_entry_success(client, mock_db, fake_user):
    entry_id = uuid.uuid4()
    row = make_history_row(id=entry_id, user_id=fake_user.id)
    mock_db.get.return_value = row

    resp = client.delete(f"/api/v1/history/{entry_id}")
    assert resp.status_code == 204
    mock_db.delete.assert_awaited_once_with(row)
    mock_db.commit.assert_awaited()


def test_delete_entry_not_found(client, mock_db):
    mock_db.get.return_value = None
    resp = client.delete(f"/api/v1/history/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_delete_entry_wrong_user(client, mock_db):
    row = make_history_row(user_id=uuid.uuid4())
    mock_db.get.return_value = row
    resp = client.delete(f"/api/v1/history/{row.id}")
    assert resp.status_code == 404


def test_delete_entry_requires_auth(unauth_client):
    resp = unauth_client.delete(f"/api/v1/history/{uuid.uuid4()}")
    assert resp.status_code == 401
