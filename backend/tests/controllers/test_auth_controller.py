import pytest

@pytest.mark.asyncio
async def test_register_endpoint(client):
    payload = {
        "email": "api_test@example.com",
        "password": "password123",
        "role": "CANDIDATE",
        "fullname": "API Tester"
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "User registered successfully"

@pytest.mark.asyncio
async def test_login_endpoint(client):
    # First register
    reg_payload = {
        "email": "login_test@example.com",
        "password": "password123",
        "role": "CANDIDATE",
        "fullname": "Candidate User"
    }
    await client.post("/auth/register", json=reg_payload)
    
    # Then login
    login_payload = {
        "email": "login_test@example.com",
        "password": "password123"
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "CANDIDATE"

@pytest.mark.asyncio
async def test_register_hr_prohibited(client):
    reg_payload = {
        "email": "hr_attempt@example.com",
        "password": "password123",
        "role": "HR",
        "fullname": "HR Attempt"
    }
    response = await client.post("/auth/register", json=reg_payload)
    assert response.status_code == 400
    assert "Public registration is only available for Candidate accounts" in response.json()["detail"]

@pytest.mark.asyncio
async def test_forgot_password_endpoint(client):
    # Register user
    reg_payload = {
        "email": "forgot@example.com",
        "password": "password123",
        "role": "CANDIDATE",
        "fullname": "Forgot User"
    }
    await client.post("/auth/register", json=reg_payload)
    
    # Request reset
    response = await client.post("/auth/forgot-password", json={"email": "forgot@example.com"})
    assert response.status_code == 200
    assert "reset link has been sent" in response.json()["message"]

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]
