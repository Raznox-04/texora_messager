import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    username = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"

    r = await client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "display_name": "کاربر تست",
        "password": "Test12345",
    })
    assert r.status_code == 201, r.text

    r = await client.post("/api/auth/login", json={
        "username": username,
        "password": "Test12345",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    r = await client.post("/api/auth/login", json={
        "username": "nonexistent_user_xyz",
        "password": "wrong",
    })
    assert r.status_code == 401