import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import HTTPException

from app.utils.database import Base
from app.models.user import User
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
from app.models.interview import Interview
from app.models.notification import Notification
from app.schemas.job_application_schema import JobApplicationCreate
from app.services import (
    job_application_service,
    applicant_profile_service,
    candidate_comparison_service,
    shortlist_roster_service,
    interview_service,
)
from app.controllers import candidate_controller, job_application_controller
from scripts.report_email_mismatch_records import generate_email_mismatch_report


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_a1_application_linked_by_user_id_and_dashboard_shows_active_app(db_session: AsyncSession):
    """
    A1 Core Scenario:
    - Candidate logs in with login.gmail@gmail.com (user_id=101)
    - Resume contains resume.contact@yahoo.com
    - Candidate chooses resume.contact@yahoo.com for HR contact
    - Application is linked to user_id=101
    - Login email on User account is NOT overwritten
    - Candidate dashboard & profile stats find the active application by user_id
    - Notifications are sent to login.gmail@gmail.com (account email)
    """
    cand = Candidate(
        id=101,
        email="login.gmail@gmail.com",
        password="hashed_password",
        fullname="Maria Santos",
        role="CANDIDATE",
        phone="09171234567",
    )
    job1 = JobDescription(
        id=1,
        job_id="JOB-101",
        job_title="Quality Control Engineer",
        department="Quality Assurance",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Quality inspection and ISO compliance",
        is_active=True,
    )
    job2 = JobDescription(
        id=2,
        job_id="JOB-102",
        job_title="Process Engineer",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Process optimization and ceramic production",
        is_active=True,
    )
    db_session.add_all([cand, job1, job2])
    await db_session.commit()

    current_user_jwt = {
        "id": 101,
        "sub": "login.gmail@gmail.com",
        "email": "login.gmail@gmail.com",
        "role": "CANDIDATE",
    }

    app_create = JobApplicationCreate(
        job_id="1",
        candidate_name="Maria Santos",
        candidate_email="resume.contact@yahoo.com",
        contact_email="resume.contact@yahoo.com",
        resume_email="resume.contact@yahoo.com",
        phone="09171234567",
        location="Batangas",
        job_title="Quality Control Engineer",
        skills=["ISO 9001", "Quality Control"],
    )

    with patch("app.tasks.analyze_application_task.delay"):
        created_app = await job_application_service.create_job_application(
            db_session,
            app_create,
            db_job_id=1,
            current_user=current_user_jwt,
        )

    assert created_app.user_id == 101
    assert created_app.applicant_id == 101
    assert created_app.contact_email == "resume.contact@yahoo.com"
    assert created_app.resume_email == "resume.contact@yahoo.com"

    # 1. Verify User login email was NOT overwritten
    await db_session.refresh(cand)
    assert cand.email == "login.gmail@gmail.com"

    # 2. Verify Candidate Dashboard query (by login email OR user_id) returns the active application
    apps_via_controller_email = await job_application_controller.get_applications_for_candidate(
        email="login.gmail@gmail.com",
        db=db_session,
        current_user=current_user_jwt,
    )
    assert len(apps_via_controller_email) == 1
    assert apps_via_controller_email[0].id == created_app.id

    apps_via_controller_uid = await job_application_controller.get_applications_for_candidate(
        email="101",
        db=db_session,
        current_user=current_user_jwt,
    )
    assert len(apps_via_controller_uid) == 1
    assert apps_via_controller_uid[0].id == created_app.id

    # Even without JWT (legacy email lookup by account email), it resolves User -> user_id
    apps_via_service_email = await job_application_service.get_applications_by_email(
        db_session, "login.gmail@gmail.com"
    )
    assert len(apps_via_service_email) == 1
    assert apps_via_service_email[0].id == created_app.id

    # 3. Verify Candidate Profile counts use user_id and reflect applications_count = 1
    profile_data = await candidate_controller.get_profile(101, db=db_session)
    assert profile_data.applications_count == 1
    assert profile_data.email == "login.gmail@gmail.com"

    # 4. Verify in-app notification was sent to account email (login.gmail@gmail.com), NOT resume email
    from sqlalchemy import select
    notif_res = await db_session.execute(
        select(Notification).where(Notification.target_role == "CANDIDATE")
    )
    cand_notifs = notif_res.scalars().all()
    assert len(cand_notifs) >= 1
    assert all(n.target_email == "login.gmail@gmail.com" for n in cand_notifs)

    # 5. Verify duplicate check uses user_id even if candidate submits a different email on second attempt
    dup_res = await job_application_controller.check_duplicate_application(
        job_id=1,
        email="another.resume@outlook.com",
        db=db_session,
        current_user=current_user_jwt,
    )
    assert dup_res["is_duplicate"] is True
    assert dup_res["existing_application_id"] == created_app.id

    # 6. Verify status update email & notification go to account login email
    with patch(
        "app.services.email_service.send_application_status_update_email",
        new_callable=AsyncMock,
    ) as mock_send_email:
        await job_application_service.update_application_status(
            db_session,
            created_app.id,
            "SHORTLISTED",
        )
        mock_send_email.assert_called_once()
        assert mock_send_email.call_args.kwargs["to_email"] == "login.gmail@gmail.com"


@pytest.mark.asyncio
async def test_a1_interviews_linked_by_user_id_when_emails_differ(db_session: AsyncSession):
    """
    Verify candidate interviews lookup and reschedule permission work by user_id
    even when application contact/candidate email is the resume email.
    """
    cand = Candidate(
        id=202,
        email="applicant.account@gmail.com",
        password="hashed_password",
        fullname="Juan Dela Cruz",
        role="CANDIDATE",
        phone="09181112233",
    )
    job = JobDescription(
        id=10,
        job_id="JOB-202",
        job_title="Maintenance Supervisor",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Sto. Tomas, Batangas",
        description="Plant maintenance",
        is_active=True,
    )
    app = JobApplication(
        id=501,
        job_id=10,
        user_id=202,
        candidate_name="Juan Dela Cruz",
        candidate_email="juan.old.resume@yahoo.com",
        contact_email="juan.old.resume@yahoo.com",
        resume_email="juan.old.resume@yahoo.com",
        status="INTERVIEW SCHEDULED",
    )
    iv = Interview(
        id=801,
        job_application_id=501,
        title="Initial HR Interview",
        start_time=datetime.utcnow() + timedelta(days=2),
        end_time=datetime.utcnow() + timedelta(days=2, hours=1),
        status="SCHEDULED",
    )
    db_session.add_all([cand, job, app, iv])
    await db_session.commit()

    # Lookup by account login email or user_id returns the interview
    ivs_by_uid = await interview_service.get_interviews_for_candidate(
        db_session, "applicant.account@gmail.com", user_id=202
    )
    assert len(ivs_by_uid) == 1
    assert ivs_by_uid[0].id == 801

    ivs_by_account_email = await interview_service.get_interviews_for_candidate(
        db_session, "applicant.account@gmail.com"
    )
    assert len(ivs_by_account_email) == 1
    assert ivs_by_account_email[0].id == 801


@pytest.mark.asyncio
async def test_a1_hr_views_do_not_duplicate_or_lose_person(db_session: AsyncSession):
    """
    Verify HR views (comprehensive profile/history, universal search, candidate comparison,
    and shortlist roster) treat one logged-in user (user_id=303) with two different emails
    across applications as a single person without duplication or loss.
    """
    cand = Candidate(
        id=303,
        email="ana.login@gmail.com",
        password="hashed_password",
        fullname="Ana Reyes",
        role="CANDIDATE",
        phone="09190001111",
    )
    other_cand = Candidate(
        id=304,
        email="ben.login@gmail.com",
        password="hashed_password",
        fullname="Ben Lim",
        role="CANDIDATE",
        phone="09192223333",
    )
    job1 = JobDescription(
        id=21,
        job_id="JOB-21",
        job_title="HR Specialist",
        department="Human Resources",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="HR operations",
        is_active=True,
    )
    job2 = JobDescription(
        id=22,
        job_id="JOB-22",
        job_title="Training Coordinator",
        department="Human Resources",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Employee training",
        is_active=True,
    )
    # Ana submits App 1 choosing her resume email for HR contact, and App 2 choosing her account email
    app1 = JobApplication(
        id=601,
        job_id=21,
        user_id=303,
        candidate_name="Ana Reyes",
        candidate_email="ana.resume@hotmail.com",
        contact_email="ana.resume@hotmail.com",
        resume_email="ana.resume@hotmail.com",
        phone="09190001111",
        status="SHORTLISTED",
        match_score=84.0,
    )
    app2 = JobApplication(
        id=602,
        job_id=22,
        user_id=303,
        candidate_name="Ana Reyes",
        candidate_email="ana.login@gmail.com",
        contact_email="ana.login@gmail.com",
        resume_email="ana.resume@hotmail.com",
        phone="09190001111",
        status="PENDING",
        match_score=78.0,
    )
    app3 = JobApplication(
        id=603,
        job_id=21,
        user_id=304,
        candidate_name="Ben Lim",
        candidate_email="ben.login@gmail.com",
        contact_email="ben.login@gmail.com",
        phone="09192223333",
        status="SHORTLISTED",
        match_score=80.0,
    )
    db_session.add_all([cand, other_cand, job1, job2, app1, app2, app3])
    await db_session.commit()

    # 1. Comprehensive Profile / History: looking up by EITHER email returns BOTH applications
    profile_by_resume_email = await applicant_profile_service.get_applicant_comprehensive_profile(
        db_session, "ana.resume@hotmail.com"
    )
    assert profile_by_resume_email is not None
    assert profile_by_resume_email["total_applications"] == 2
    assert profile_by_resume_email["candidate"]["account_email"] == "ana.login@gmail.com"
    assert profile_by_resume_email["candidate"]["resume_email"] == "ana.resume@hotmail.com"

    profile_by_account_email = await applicant_profile_service.get_applicant_comprehensive_profile(
        db_session, "ana.login@gmail.com"
    )
    assert profile_by_account_email is not None
    assert profile_by_account_email["total_applications"] == 2

    # 2. Universal Search HR: searching "Ana" returns Ana ONCE (not duplicated)
    search_res = await applicant_profile_service.universal_search_hr(db_session, "Ana")
    ana_hits = [a for a in search_res["applicants"] if a["name"] == "Ana Reyes"]
    assert len(ana_hits) == 1

    # 3. Candidate Comparison: comparing app1 and app2 (same person with different emails) is rejected with 422
    with pytest.raises(HTTPException) as exc_info:
        await candidate_comparison_service.compare_candidates_service(
            db_session, [601, 602], reference_job_id=21
        )
    assert exc_info.value.status_code == 422

    # Comparing Ana (601) and Ben (603) succeeds
    comp_res = await candidate_comparison_service.compare_candidates_service(
        db_session, [601, 603], reference_job_id=21
    )
    assert len(comp_res["candidates"]) == 2

    # 4. Shortlist Roster: adding both app1 and app2 to the same roster does not duplicate the person
    roster = await shortlist_roster_service.create_shortlist_roster(
        db_session,
        job_id=21,
        name="HR Shortlist",
        created_by="hr@mariwasa.com",
        application_ids=[601, 602],
    )
    roster_detail = await shortlist_roster_service.get_shortlist_roster_by_id(db_session, roster.id)
    assert roster_detail["total_candidates"] == 1
    assert roster_detail["items"][0]["user_id"] == 303


@pytest.mark.asyncio
async def test_a1_reporting_script_finds_mismatched_records_without_modifying_data(db_session: AsyncSession):
    """
    Verify the diagnostic reporting script identifies resumes and applications
    with email mismatches or missing user_id linkage without merging accounts
    or changing application statuses.
    """
    cand = Candidate(
        id=404,
        email="owner.account@gmail.com",
        password="hashed_password",
        fullname="Carlo Mendoza",
        role="CANDIDATE",
    )
    resume = Resume(
        id=901,
        candidate_id=404,
        filename="carlo_cv.pdf",
        file_url="/uploads/resumes/carlo_cv.pdf",
        parsed_data={"email": "carlo.cv@yahoo.com", "fullname": "Carlo Mendoza"},
    )
    job = JobDescription(
        id=31,
        job_id="JOB-31",
        job_title="Safety Officer",
        department="HSE",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Plant safety",
        is_active=True,
    )
    # Legacy application matched by resume email with no user_id
    legacy_app = JobApplication(
        id=701,
        job_id=31,
        user_id=None,
        candidate_name="Carlo Mendoza",
        candidate_email="carlo.cv@yahoo.com",
        resume_url="/uploads/resumes/carlo_cv.pdf",
        status="PENDING",
    )
    db_session.add_all([cand, resume, job, legacy_app])
    await db_session.commit()

    # Run report twice to verify re-runnability and read-only safety
    report1 = await generate_email_mismatch_report(db_session)
    report2 = await generate_email_mismatch_report(db_session)
    assert report1 == report2

    assert report1["summary"]["mismatched_resumes_count"] == 1
    assert report1["mismatched_resumes"][0]["resume_id"] == 901
    assert report1["mismatched_resumes"][0]["account_email"] == "owner.account@gmail.com"
    assert report1["mismatched_resumes"][0]["extracted_resume_email"] == "carlo.cv@yahoo.com"

    assert report1["summary"]["reported_applications_count"] == 1
    rep_app = report1["reported_applications"][0]
    assert rep_app["application_id"] == 701
    assert rep_app["inferred_accounts"] == [{"user_id": 404, "account_email": "owner.account@gmail.com"}]

    # Confirm no status or ownership was mutated automatically
    await db_session.refresh(legacy_app)
    assert legacy_app.user_id is None
    assert legacy_app.status == "PENDING"
