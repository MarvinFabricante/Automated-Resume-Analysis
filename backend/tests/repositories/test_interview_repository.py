import pytest
from datetime import datetime, timedelta
from app.repositories import interview_repository
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.models.hr import HR
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_interview_repo_crud_and_queries(db_session):
    # Setup HR, Job, Application
    hr = HR(
        fullname="Interview Repo HR",
        email="int_repo_hr@example.com",
        password=hash_password("pass123"),
        role="HR",
        company_name="Mariwasa"
    )
    job = JobDescription(
        job_id="INT-REPO-JOB-001",
        job_title="QA Tester",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Software testing",
        skills_requirements="Pytest, Selenium"
    )
    db_session.add_all([hr, job])
    await db_session.commit()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Interview Cand",
        candidate_email="int_cand@example.com",
        status="PENDING",
        created_at=datetime.utcnow()
    )
    db_session.add(app)
    await db_session.commit()
    app_id = app.id
    hr_id = hr.id

    # 1. Get job application
    fetched_app = await interview_repository.get_job_application(db_session, app_id)
    assert fetched_app is not None
    assert fetched_app.candidate_email == "int_cand@example.com"

    # 2. Create interview
    now = datetime.utcnow()
    int_data = {
        "job_application_id": app_id,
        "interviewer_id": hr_id,
        "start_time": now + timedelta(days=1),
        "end_time": now + timedelta(days=1, hours=1),
        "status": "SCHEDULED",
        "title": "Technical Interview",
        "google_event_id": "google_evt_12345"
    }
    interview = await interview_repository.create_interview(db_session, int_data)
    await interview_repository.commit_changes(db_session)
    assert interview.id is not None
    int_id = interview.id

    # 3. Add interview log
    await interview_repository.add_interview_log(db_session, int_id, "SCHEDULED", "Initial schedule")
    await interview_repository.commit_changes(db_session)

    # 4. Get by ID
    fetched_int = await interview_repository.get_interview_by_id(db_session, int_id)
    assert fetched_int is not None
    assert fetched_int.status == "SCHEDULED"

    # 5. Get interviews for application
    app_ints = await interview_repository.get_interviews_for_application(db_session, app_id)
    assert len(app_ints) == 1

    # 6. Get interviews in range
    range_ints = await interview_repository.get_interviews_in_range(
        db_session,
        now + timedelta(hours=20),
        now + timedelta(days=2),
        interviewer_id=hr_id
    )
    assert len(range_ints) == 1

    # 7. Get for candidate
    cand_ints = await interview_repository.get_interviews_for_candidate(db_session, "int_cand@example.com")
    assert len(cand_ints) == 1

    # 8. Get all interviews
    all_ints = await interview_repository.get_all_interviews(db_session)
    assert len(all_ints) >= 1

    # 9. Get by google event ID
    by_event = await interview_repository.get_interview_by_google_event_id(db_session, "google_evt_12345")
    assert by_event is not None
    assert by_event.id == int_id

    # 10. Range excluding
    excluding = await interview_repository.get_interviews_in_range_excluding(
        db_session,
        now + timedelta(hours=20),
        now + timedelta(days=2),
        exclude_interview_id=int_id
    )
    assert len(excluding) == 0

    # 11. Update interview
    fetched_int.status = "COMPLETED"
    updated = await interview_repository.update_interview(db_session, fetched_int)
    assert updated.status == "COMPLETED"

    # 12. Delete interview
    await interview_repository.delete_interview(db_session, updated)
    assert await interview_repository.get_interview_by_id(db_session, int_id) is None
