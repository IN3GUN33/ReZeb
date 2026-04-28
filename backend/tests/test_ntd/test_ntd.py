import io

import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str = "ntd@example.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "NTD User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_list_documents_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/ntd/documents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient) -> None:
    token = await _get_token(client)
    resp = await client.get(
        "/api/v1/ntd/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/ntd/search?q=бетон")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_short_query_rejected(client: AsyncClient) -> None:
    token = await _get_token(client, "ntd2@example.com")
    resp = await client.get(
        "/api/v1/ntd/search?q=ab",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_results(client: AsyncClient) -> None:
    token = await _get_token(client, "ntd3@example.com")
    resp = await client.get(
        "/api/v1/ntd/search?q=несуществующий+термин+xyz",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_upload_document_unsupported_format(client: AsyncClient) -> None:
    token = await _get_token(client, "ntd4@example.com")
    resp = await client.post(
        "/api/v1/ntd/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("document.exe", io.BytesIO(b"binary content"), "application/octet-stream")},
        data={"code": "ГОСТ-12345", "title": "Тестовый документ"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_document_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/ntd/documents",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")},
        data={"code": "СП-001", "title": "Test"},
    )
    assert resp.status_code == 401
