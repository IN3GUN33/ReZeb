import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str = "proj@example.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Project User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_list_projects_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient) -> None:
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Жилой дом №1", "location": "Москва"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Жилой дом №1"
    assert data["location"] == "Москва"
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_project_name_required(client: AsyncClient) -> None:
    token = await _get_token(client, "proj2@example.com")
    resp = await client.post(
        "/api/v1/projects",
        json={"name": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient) -> None:
    token = await _get_token(client, "proj3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/projects", json={"name": "Объект А"}, headers=headers)
    await client.post("/api/v1/projects", json={"name": "Объект Б"}, headers=headers)

    resp = await client.get("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 2
    names = [p["name"] for p in projects]
    assert "Объект А" in names
    assert "Объект Б" in names


@pytest.mark.asyncio
async def test_get_project_by_id(client: AsyncClient) -> None:
    token = await _get_token(client, "proj4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Склад №3", "description": "Промышленный склад"},
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Склад №3"
    assert data["description"] == "Промышленный склад"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient) -> None:
    token = await _get_token(client, "proj5@example.com")
    resp = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient) -> None:
    token = await _get_token(client, "proj6@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Временный объект"},
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_resp.status_code == 204

    # After delete, project should not appear in list
    list_resp = await client.get("/api/v1/projects", headers=headers)
    ids = [p["id"] for p in list_resp.json()]
    assert project_id not in ids


@pytest.mark.asyncio
async def test_projects_isolated_between_users(client: AsyncClient) -> None:
    """Each user sees only their own projects."""
    token_a = await _get_token(client, "proj7a@example.com")
    token_b = await _get_token(client, "proj7b@example.com")

    await client.post(
        "/api/v1/projects",
        json={"name": "Только у пользователя A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp_b = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    names_b = [p["name"] for p in resp_b.json()]
    assert "Только у пользователя A" not in names_b
