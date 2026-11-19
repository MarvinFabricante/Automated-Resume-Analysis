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


@pytest.mark.asyncio
async def test_security_status_reports_google_linked_for_candidate_hr_and_admin(client, db_session):
    from datetime import datetime, timedelta
    from app.models.admin import Admin
    from app.models.hr import HR
    from app.services.auth_service import login_with_google, register_candidate_with_google
    from app.utils.auth import create_access_token, hash_password

    # 1. Candidate registered via Google (no google_credentials stored)
    cand_res = await register_candidate_with_google(
        db_session,
        email="cand_google_status@gmail.com",
        fullname="Google Candidate",
        picture="",
    )
    cand_headers = {"Authorization": f"Bearer {cand_res['token']}"}
    cand_status = await client.get("/auth/security-status", headers=cand_headers)
    assert cand_status.status_code == 200
    assert cand_status.json()["is_google_linked"] is True
    assert cand_status.json()["google_email"] == "cand_google_status@gmail.com"
    assert cand_status.json()["has_calendar_sync"] is False

    # 2. HR logged in via basic Google Sign-In (no calendar scope, custom password already set)
    hr_user = HR(
        fullname="Marvin HR",
        email="marvin_hr_google@gmail.com",
        password=hash_password("custompass123"),
        role="HR",
        company_name="Mariwasa",
    )
    db_session.add(hr_user)
    await db_session.commit()

    hr_login = await login_with_google(
        db=db_session,
        email="marvin_hr_google@gmail.com",
        fullname="Marvin HR",
        picture="",
        google_credentials="",
        target_role="auto",
        granted_scopes=["openid", "email", "profile"],
    )
    hr_headers = {"Authorization": f"Bearer {hr_login['token']}"}
    hr_status = await client.get("/auth/security-status", headers=hr_headers)
    assert hr_status.status_code == 200
    assert hr_status.json()["is_google_linked"] is True
    assert hr_status.json()["google_email"] == "marvin_hr_google@gmail.com"
    assert hr_status.json()["has_calendar_sync"] is False

    # 3. Admin with expired calendar token still shows Google account linked
    admin_user = Admin(
        fullname="Google Admin",
        email="admin_google_status@gmail.com",
        password=hash_password("custompass123"),
        role="ADMIN",
        google_linked=True,
        google_token_expiry=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add(admin_user)
    await db_session.commit()
    admin_token = create_access_token({"sub": admin_user.email, "role": "ADMIN", "id": admin_user.id})
    admin_status = await client.get("/auth/security-status", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_status.status_code == 200
    assert admin_status.json()["is_google_linked"] is True
    assert admin_status.json()["google_email"] == "admin_google_status@gmail.com"

    # 4. Disconnecting Google sets is_google_linked back to False
    disc_res = await client.post("/auth/google/disconnect", headers=hr_headers)
    assert disc_res.status_code == 200
    hr_status_after = await client.get("/auth/security-status", headers=hr_headers)
    assert hr_status_after.status_code == 200
    assert hr_status_after.json()["is_google_linked"] is False
    assert hr_status_after.json()["google_email"] is None
