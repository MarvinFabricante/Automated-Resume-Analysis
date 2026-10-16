import pytest
from app.repositories import admin_repository
from app.models.admin import Admin
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.job_description import JobDescription, JobType
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_admin_repo_admin_lifecycle(db_session):
    admin_data = {
        "fullname": "Repo Super Admin",
        "email": "repo_admin@example.com",
        "password": hash_password("pass123"),
        "role": "ADMIN",
        "department": "Security & IT",
        "position": "Lead Sysadmin"
    }

    # 1. Create admin
    created = await admin_repository.create_admin(db_session, admin_data)
    assert created.id is not None
    admin_id = created.id

    # 2. Get admin by id
    fetched = await admin_repository.get_admin_by_id(db_session, admin_id)
    assert fetched is not None
    assert fetched.email == "repo_admin@example.com"

    # 3. Update admin
    updated = await admin_repository.update_admin(db_session, fetched, {
        "position": "Chief Information Officer"
    })
    assert updated.position == "Chief Information Officer"


@pytest.mark.asyncio
async def test_admin_repo_user_directory_operations(db_session):
    cand = Candidate(
        fullname="Dir Cand User",
        email="dir_cand@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    hr = HR(
        fullname="Dir HR User",
        email="dir_hr@example.com",
        password=hash_password("pass123"),
        role="HR",
        company_name="Mariwasa"
    )
    db_session.add_all([cand, hr])
    await db_session.commit()
    cand_id = cand.id
    hr_id = hr.id

    # 1. Get all directory users
    users = await admin_repository.get_all_users(db_session)
    user_ids = [u.id for u in users]
    assert cand_id in user_ids
    assert hr_id in user_ids

    # 2. Get user by id
    fetched_cand = await admin_repository.get_user_by_id(db_session, cand_id)
    assert fetched_cand is not None
    assert fetched_cand.email == "dir_cand@example.com"

    # 3. Update user archive status
    archived_user = await admin_repository.update_user_archive_status(db_session, fetched_cand, True)
    assert archived_user.is_archived is True

    unarchived_user = await admin_repository.update_user_archive_status(db_session, fetched_cand, False)
    assert unarchived_user.is_archived is False

    # 4. Update user details
    updated_user = await admin_repository.update_user(db_session, fetched_cand, {
        "fullname": "Dir Cand Renamed",
        "location": "Quezon City"
    })
    assert updated_user.fullname == "Dir Cand Renamed"

    # 5. Delete user
    deleted = await admin_repository.delete_user(db_session, fetched_cand)
    assert deleted is True

    # Confirm deletion
    after_del = await admin_repository.get_user_by_id(db_session, cand_id)
    assert after_del is None


@pytest.mark.asyncio
async def test_admin_repo_system_stats(db_session):
    hr = HR(
        fullname="Stats HR",
        email="stats_hr@example.com",
        password=hash_password("pass123"),
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Stats Candidate",
        email="stats_cand@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    job = JobDescription(
        job_id="ADM-STATS-JOB-001",
        job_title="Ceramics Engineer",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Engineering role",
        skills_requirements="Ceramics, Quality"
    )
    db_session.add_all([hr, cand, job])
    await db_session.commit()

    stats = await admin_repository.get_system_stats(db_session)
    assert "total_users" in stats
    assert stats["hr_count"] >= 1
    assert stats["candidate_count"] >= 1
    assert stats["job_count"] >= 1
