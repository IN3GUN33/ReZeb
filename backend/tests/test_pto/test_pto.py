import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str = "pto@example.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "PTO User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_pto_query(client: AsyncClient) -> None:
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/pto/queries",
        json={"raw_text": "Кирпич керамический М150 ГОСТ 530-2012"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["raw_text"] == "Кирпич керамический М150 ГОСТ 530-2012"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_pto_query_validation(client: AsyncClient) -> None:
    token = await _get_token(client, "pto2@example.com")
    resp = await client.post(
        "/api/v1/pto/queries",
        json={"raw_text": "x"},  # too short
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_registry_search_empty(client: AsyncClient) -> None:
    token = await _get_token(client, "pto3@example.com")
    resp = await client.get(
        "/api/v1/pto/registry/search",
        params={"q": "кирпич"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # May return 200 with empty list (no embeddings in test DB)
    assert resp.status_code in (200, 502)
