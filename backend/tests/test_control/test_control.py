import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str = "ctrl@example.com") -> str:
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
async def test_create_session(client: AsyncClient) -> None:
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/control/sessions",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient) -> None:
    token = await _get_token(client, "ctrl2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/control/sessions", json={}, headers=headers)
    await client.post("/api/v1/control/sessions", json={}, headers=headers)

    resp = await client.get("/api/v1/control/sessions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
