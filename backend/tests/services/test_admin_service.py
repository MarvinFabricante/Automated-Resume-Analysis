import pytest
from app.services import admin_service
from app.schemas.admin_schema import AdminCreate, AdminUpdate
from app.models.user import User
from app.models.admin import Admin
from app.models.hr import HR
from app.models.candidate import Candidate


@pytest.mark.asyncio
async def test_create_and_get_admin_profile(db_session):
    admin_in = AdminCreate(
        fullname="Admin One",
        email="admin_one@example.com",
        password="secretpassword",
        managed_region="NCR"
    )
    admin = await admin_service.create_admin_profile(db_session, admin_in)
    assert admin.id is not None
    assert admin.email == "admin_one@example.com"
    assert admin.fullname == "Admin One"
    assert admin.role == "ADMIN"
    assert admin.managed_region == "NCR"

    fetched = await admin_service.get_admin_profile(db_session, admin.id)
    assert fetched is not None
    assert fetched.id == admin.id
    assert fetched.email == "admin_one@example.com"


@pytest.mark.asyncio
async def test_update_admin_profile(db_session):
    admin_in = AdminCreate(
        fullname="Admin Update Test",
        email="admin_update@example.com",
        password="password123",
        managed_region="Region IV-A"
    )
    admin = await admin_service.create_admin_profile(db_session, admin_in)

    # Valid update
    update_data = AdminUpdate(
        fullname="Admin Renamed",
        email="admin_newemail@example.com",
        managed_region="Region III"
    )
    updated = await admin_service.update_admin_profile(db_session, admin.id, update_data)
    assert updated.fullname == "Admin Renamed"
    assert updated.email == "admin_newemail@example.com"
    assert updated.managed_region == "Region III"

    # Non-existent admin returns None
    res = await admin_service.update_admin_profile(db_session, 999999, update_data)
    assert res is None


@pytest.mark.asyncio
async def test_update_admin_profile_duplicate_email(db_session):
    admin1 = await admin_service.create_admin_profile(
        db_session,
        AdminCreate(fullname="Admin A", email="admin_a@example.com", password="pass")
    )
    admin2 = await admin_service.create_admin_profile(
        db_session,
        AdminCreate(fullname="Admin B", email="admin_b@example.com", password="pass")
    )

    # Attempt to update admin2 with admin1's email
    with pytest.raises(Exception) as excinfo:
        await admin_service.update_admin_profile(
            db_session,
            admin2.id,
            AdminUpdate(email="admin_a@example.com")
        )
    assert "already in use" in str(excinfo.value)


@pytest.mark.asyncio
async def test_toggle_user_archive_and_user_crud(db_session):
    admin_in = AdminCreate(
        fullname="User To Manage",
        email="manage_me@example.com",
        password="password123"
    )
    admin = await admin_service.create_admin_profile(db_session, admin_in)
    user_id = admin.id

    # Toggle archive
    archived = await admin_service.toggle_user_archive_status(db_session, user_id, True)
    assert archived is not None
    assert archived.is_archived is True

    # Update user fields
    updated_user = await admin_service.update_user(
        db_session,
        user_id,
        {"fullname": "Updated User", "password": "newpassword123"}
    )
    assert updated_user.fullname == "Updated User"
    assert updated_user.password != "newpassword123"  # hashed

    # Fetch user by id
    fetched_user = await admin_service.get_user_by_id(db_session, user_id)
    assert fetched_user is not None
    assert fetched_user.id == user_id

    # Delete user
    deleted = await admin_service.delete_user(db_session, user_id)
    assert deleted is True

    # Attempt to delete non-existent user
    assert await admin_service.delete_user(db_session, 999999) is False


@pytest.mark.asyncio
async def test_get_all_users_and_stats(db_session):
    # Setup candidate and hr users
    candidate = Candidate(
        fullname="Candidate User",
        email="cand_stat@example.com",
        password="hash",
        role="CANDIDATE"
    )
    hr = HR(
        fullname="HR User",
        email="hr_stat@example.com",
        password="hash",
        role="HR",
        company_name="Mariwasa"
    )
    db_session.add_all([candidate, hr])
    await db_session.flush()

    all_users = await admin_service.get_all_users(db_session)
    assert isinstance(all_users, list)
    user_emails = [u.email for u in all_users]
    assert "cand_stat@example.com" in user_emails
    assert "hr_stat@example.com" in user_emails

    stats = await admin_service.get_system_stats(db_session)
    assert "total_users" in stats
    assert "hr_count" in stats
    assert "candidate_count" in stats
    assert "job_count" in stats
    assert stats["total_users"] >= 2
