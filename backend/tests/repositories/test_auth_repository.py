import pytest
from datetime import datetime, timedelta
from app.repositories import auth_repository
from app.models.password_reset import PasswordReset
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_auth_repo_create_and_find_user(db_session):
    common_fields = {
        "fullname": "Auth Repo Candidate",
        "email": "auth_repo_cand@example.com",
        "password": hash_password("pass123"),
        "role": "CANDIDATE"
    }

    # 1. Create user
    created_user = await auth_repository.create_user(db_session, "CANDIDATE", common_fields)
    assert created_user.id is not None
    assert created_user.email == "auth_repo_cand@example.com"
    user_id = created_user.id

    # 2. Check email exists
    exists = await auth_repository.check_email_exists_raw(db_session, "auth_repo_cand@example.com")
    assert exists is True

    not_exists = await auth_repository.check_email_exists_raw(db_session, "non_existent@example.com")
    assert not_exists is False

    # 3. Get raw user by email
    raw_user = await auth_repository.get_raw_user_by_email(db_session, "auth_repo_cand@example.com")
    assert raw_user is not None
    assert raw_user.id == user_id

    # 4. Get user by email and role
    user_by_role = await auth_repository.get_user_by_email_and_role(db_session, "auth_repo_cand@example.com", "CANDIDATE")
    assert user_by_role is not None
    assert user_by_role.id == user_id

    # 5. Get user by email & id
    by_email = await auth_repository.get_user_by_email(db_session, "auth_repo_cand@example.com")
    assert by_email is not None
    assert by_email.id == user_id

    by_id = await auth_repository.get_user_by_id(db_session, user_id)
    assert by_id is not None
    assert by_id.email == "auth_repo_cand@example.com"


@pytest.mark.asyncio
async def test_auth_repo_create_hr_and_admin(db_session):
    hr_fields = {
        "fullname": "Auth Repo HR",
        "email": "auth_repo_hr@example.com",
        "password": hash_password("pass123"),
        "role": "HR"
    }
    hr_user = await auth_repository.create_user(db_session, "HR", hr_fields)
    assert hr_user.id is not None
    assert hr_user.role == "HR"

    admin_fields = {
        "fullname": "Auth Repo Admin",
        "email": "auth_repo_admin@example.com",
        "password": hash_password("pass123"),
        "role": "ADMIN"
    }
    admin_user = await auth_repository.create_user(db_session, "ADMIN", admin_fields)
    assert admin_user.id is not None
    assert admin_user.role == "ADMIN"


@pytest.mark.asyncio
async def test_auth_repo_online_status_and_password(db_session):
    fields = {
        "fullname": "Status Tester",
        "email": "status_test@example.com",
        "password": hash_password("oldpass123"),
        "role": "CANDIDATE"
    }
    user = await auth_repository.create_user(db_session, "CANDIDATE", fields)
    user_id = user.id

    now = datetime.utcnow()
    # Update online status raw
    await auth_repository.update_online_status_raw(db_session, user_id, now)

    # Update online status ORM
    await auth_repository.update_online_status_orm(db_session, user, now)
    assert user.is_online is True

    # Update password
    new_hashed = hash_password("brandnewpass456")
    await auth_repository.update_user_password(db_session, user, new_hashed)
    assert user.password == new_hashed


@pytest.mark.asyncio
async def test_auth_repo_password_reset_lifecycle(db_session):
    token = "repo_reset_token_abc"
    reset_entry = PasswordReset(
        email="reset_repo@example.com",
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    created_entry = await auth_repository.create_password_reset(db_session, reset_entry)
    assert created_entry.token == token

    found = await auth_repository.get_password_reset_by_token(db_session, token)
    assert found is not None
    assert found.email == "reset_repo@example.com"

    await auth_repository.delete_password_reset(db_session, found)
    after_del = await auth_repository.get_password_reset_by_token(db_session, token)
    assert after_del is None
