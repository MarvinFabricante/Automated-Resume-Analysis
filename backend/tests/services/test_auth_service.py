import pytest
from unittest.mock import patch, AsyncMock
from app.services import auth_service
from app.models.user import User
from app.models.password_reset import PasswordReset
from sqlalchemy.future import select
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_register_user_success(db_session):
    email = "test@example.com"
    password = "password123"
    role = "CANDIDATE"
    
    user = await auth_service.register_user(db_session, email, password, role, "Test User")
    
    assert user.email == email
    assert user.role == role
    
    # Verify in DB
    result = await db_session.execute(select(User).where(User.email == email))
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.email == email


@pytest.mark.asyncio
async def test_register_user_invalid_role(db_session):
    with pytest.raises(Exception) as excinfo:
        await auth_service.register_user(db_session, "invalid_role@example.com", "pass", "SUPERUSER")
    assert "Invalid role" in str(excinfo.value)


@pytest.mark.asyncio
async def test_register_user_duplicate_email(db_session):
    email = "duplicate@example.com"
    await auth_service.register_user(db_session, email, "pass1", "CANDIDATE", "Dup User")
    
    with pytest.raises(Exception) as excinfo:
        await auth_service.register_user(db_session, email, "pass2", "CANDIDATE", "Dup User 2")
    assert "Email already registered" in str(excinfo.value)


@pytest.mark.asyncio
async def test_login_user_success(db_session):
    email = "login@example.com"
    password = "secretpassword"
    await auth_service.register_user(db_session, email, password, "HR", "Login User")
    
    login_data = await auth_service.login_user(db_session, email, password)
    
    assert "token" in login_data
    assert login_data["role"] == "HR"


@pytest.mark.asyncio
async def test_login_user_wrong_password(db_session):
    email = "wrongpass@example.com"
    await auth_service.register_user(db_session, email, "correctpass", "ADMIN", "Wrong Pass User")
    
    with pytest.raises(Exception) as excinfo:
        await auth_service.login_user(db_session, email, "wrongpass")
    assert "Invalid credentials" in str(excinfo.value)


@pytest.mark.asyncio
async def test_login_user_nonexistent(db_session):
    with pytest.raises(Exception) as excinfo:
        await auth_service.login_user(db_session, "nonexistent@example.com", "pass")
    assert "Invalid credentials" in str(excinfo.value)


@pytest.mark.asyncio
async def test_login_user_archived(db_session):
    email = "archived_user@example.com"
    user = await auth_service.register_user(db_session, email, "secretpass", "HR", "Archived User")
    user.is_archived = True
    await db_session.commit()

    with pytest.raises(Exception) as excinfo:
        await auth_service.login_user(db_session, email, "secretpass")
    assert "archived" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_request_password_reset(db_session):
    email = "reset@example.com"
    await auth_service.register_user(db_session, email, "pass123", "CANDIDATE", "Reset User")
    
    with patch("app.services.auth_service.send_reset_password_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = True
        result = await auth_service.request_password_reset(db_session, email)
        assert result is True
        mock_email.assert_called_once()


@pytest.mark.asyncio
async def test_reset_user_password_success_and_invalid(db_session):
    email = "reset_target@example.com"
    user = await auth_service.register_user(db_session, email, "oldpassword123", "CANDIDATE", "Target User")
    
    token = "valid_reset_token_123"
    pr = PasswordReset(
        email=email,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db_session.add(pr)
    await db_session.commit()

    # Successful reset
    success = await auth_service.reset_user_password(db_session, token, "newbrandpassword456")
    assert success is True

    # Login with new password should now succeed
    login_res = await auth_service.login_user(db_session, email, "newbrandpassword456")
    assert "token" in login_res

    # Using the same token again should fail
    with pytest.raises(Exception) as excinfo:
        await auth_service.reset_user_password(db_session, token, "anotherpassword789")
    assert "Invalid or expired reset token" in str(excinfo.value)


@pytest.mark.asyncio
async def test_change_password_and_set_password(db_session):
    email = "pwd_change@example.com"
    user = await auth_service.register_user(db_session, email, "original_pass_123", "CANDIDATE", "Pwd User")

    # Change password with wrong current password
    with pytest.raises(Exception) as excinfo:
        await auth_service.change_password(db_session, user.id, "wrong_current", "new_pwd_123")
    assert "Incorrect current password" in str(excinfo.value)

    # Change password with correct current password
    changed = await auth_service.change_password(db_session, user.id, "original_pass_123", "new_pwd_123")
    assert changed is True

    # Set password directly (admin override or reset flow)
    set_res = await auth_service.set_password(db_session, user.id, "direct_set_pwd_999")
    assert set_res is True

    # Login with directly set password
    login_res = await auth_service.login_user(db_session, email, "direct_set_pwd_999")
    assert "token" in login_res
