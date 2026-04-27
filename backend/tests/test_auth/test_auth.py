import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient) -> None:
    # Register
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"

    # Login
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Me
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={
        "email": "user2@example.com",
        "password": "correctpass",
        "full_name": "User Two",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "user2@example.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 403
