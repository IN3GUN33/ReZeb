import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_forgot_password(client: AsyncClient) -> None:
    # First register a user
    await client.post("/api/v1/auth/register", json={
        "email": "forgot@example.com",
        "password": "password123",
        "full_name": "Forgot User",
    })

    with patch("app.modules.auth.service.create_pool", new_callable=AsyncMock) as mock_pool:
        mock_redis = AsyncMock()
        mock_pool.return_value = mock_redis

        resp = await client.post("/api/v1/auth/forgot-password", json={
            "email": "forgot@example.com"
        })
        assert resp.status_code == 202
        mock_redis.enqueue_job.assert_called_once()
        args, kwargs = mock_redis.enqueue_job.call_args
        assert args[0] == "send_email_task"
        assert kwargs["recipient"] == "forgot@example.com"
        assert "reset-password?token=" in kwargs["context"]["reset_url"]

@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient) -> None:
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "reset@example.com",
        "password": "oldpassword",
        "full_name": "Reset User",
    })

    # We need a token. We can get it by mocking forgot_password or just generating one
    from app.core.security import create_access_token
    from datetime import timedelta
    from sqlalchemy import select
    from app.modules.auth.models import User

    # This is a bit hacky because we need the actual user ID from the DB
    # But since we use overrides in conftest, we might not have easy access to the DB here
    # unless we use the 'db' fixture.

    # Let's try to login to get the user ID (it's in the token sub)
    resp = await client.post("/api/v1/auth/login", json={
        "email": "reset@example.com",
        "password": "oldpassword",
    })
    from app.core.security import decode_token
    user_id = decode_token(resp.json()["access_token"])["sub"]

    reset_token = create_access_token(user_id, {"type": "reset_password"}, expires_delta=timedelta(hours=1))

    # Reset password
    resp = await client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "newpassword123"
    })
    assert resp.status_code == 204

    # Try login with new password
    resp = await client.post("/api/v1/auth/login", json={
        "email": "reset@example.com",
        "password": "newpassword123",
    })
    assert resp.status_code == 200
