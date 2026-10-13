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

@pytest.mark.asyncio
async def test_change_and_set_password_endpoints(client):
    email = "pwd_test@example.com"
    await client.post("/auth/register", json={
        "email": email,
        "password": "oldpassword123",
        "role": "CANDIDATE",
        "fullname": "Password Tester"
    })
    login_res = await client.post("/auth/login", json={
        "email": email,
        "password": "oldpassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test change password with incorrect current password returns 400
    wrong_res = await client.post("/auth/change-password", headers=headers, json={
        "current_password": "wrongcurrentpassword",
        "new_password": "brandnewpassword123"
    })
    assert wrong_res.status_code == 400
    assert "Incorrect current password" in wrong_res.json()["detail"]

    # Test change password with correct current password
    change_res = await client.post("/auth/change-password", headers=headers, json={
        "current_password": "oldpassword123",
        "new_password": "brandnewpassword123"
    })
    assert change_res.status_code == 200
    assert change_res.json()["message"] == "Password successfully updated."

    # Test set password directly (without current password)
    set_res = await client.post("/auth/set-password", headers=headers, json={
        "new_password": "directnewpassword123"
    })
    assert set_res.status_code == 200
    assert set_res.json()["message"] == "Password successfully established."

    # Verify login works with the newest password
    verify_login = await client.post("/auth/login", json={
        "email": email,
        "password": "directnewpassword123"
    })
    assert verify_login.status_code == 200
