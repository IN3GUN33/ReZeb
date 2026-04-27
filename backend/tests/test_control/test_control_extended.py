"""Extended control module tests."""
import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str = "ctrl_ext@example.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Control User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_session_full_lifecycle(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    resp = await client.post("/api/v1/control/sessions", json={}, headers=headers)
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Get session
    resp = await client.get(f"/api/v1/control/sessions/{session_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    # List sessions
    resp = await client.get("/api/v1/control/sessions", headers=headers)
    assert resp.status_code == 200
    assert any(s["id"] == session_id for s in resp.json())


@pytest.mark.asyncio
async def test_upload_photo_validation(client: AsyncClient) -> None:
    token = await _register_and_login(client, "ctrl_photo@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/control/sessions", json={}, headers=headers)
    session_id = resp.json()["id"]

    # Upload invalid file type
    files = {"file": ("test.txt", b"not an image", "text/plain")}
    resp = await client.post(
        f"/api/v1/control/sessions/{session_id}/photos",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_session_not_found(client: AsyncClient) -> None:
    token = await _register_and_login(client, "ctrl_notfound@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        "/api/v1/control/sessions/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/control/sessions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_export_session(client: AsyncClient) -> None:
    token = await _register_and_login(client, "ctrl_export@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/control/sessions", json={}, headers=headers)
    session_id = resp.json()["id"]

    # Export pending session (no verdict yet — still works)
    resp = await client.get(
        f"/api/v1/control/sessions/{session_id}/export",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert "defects" in data
    assert "disclaimer" in data
