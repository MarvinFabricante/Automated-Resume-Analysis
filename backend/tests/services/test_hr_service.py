import pytest
from app.services import hr_service
from app.schemas.hr_schema import HRCreate, HRUpdate
from app.models.candidate import Candidate
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication


@pytest.mark.asyncio
async def test_create_and_get_hr_profile(db_session):
    hr_in = HRCreate(
        fullname="Elena Gomez",
        email="elena_gomez@example.com",
        password="secretpassword123",
        company_name="Mariwasa Siam Ceramics",
        department="Talent Acquisition"
    )

    hr = await hr_service.create_hr_profile(db_session, hr_in)
    assert hr.id is not None
    assert hr.fullname == "Elena Gomez"
    assert hr.email == "elena_gomez@example.com"
    assert hr.company_name == "Mariwasa Siam Ceramics"
    assert hr.department == "Talent Acquisition"
    assert hr.role == "HR"

    fetched = await hr_service.get_hr_profile(db_session, hr.id)
    assert fetched is not None
    assert fetched.id == hr.id
    assert fetched.email == "elena_gomez@example.com"


@pytest.mark.asyncio
async def test_update_hr_profile(db_session):
    hr_in = HRCreate(
        fullname="Carlos Reyes",
        email="carlos_reyes@example.com",
        password="password123",
        company_name="Mariwasa",
        department="Operations"
    )
    hr = await hr_service.create_hr_profile(db_session, hr_in)

    update_in = HRUpdate(
        fullname="Carlos Reyes Jr.",
        position="Senior Recruiter",
        phone="+639181112222",
        location="Batangas"
    )
    updated = await hr_service.update_hr_profile(db_session, hr.id, update_in)
    assert updated is not None
    assert updated.fullname == "Carlos Reyes Jr."
    assert updated.position == "Senior Recruiter"
    assert updated.phone == "+639181112222"
    assert updated.location == "Batangas"

    # Non-existent profile
    assert await hr_service.update_hr_profile(db_session, 999999, update_in) is None


@pytest.mark.asyncio
async def test_update_hr_duplicate_email(db_session):
    hr1 = await hr_service.create_hr_profile(
        db_session,
        HRCreate(fullname="HR 1", email="hr1@example.com", password="pass", company_name="M")
    )
    hr2 = await hr_service.create_hr_profile(
        db_session,
        HRCreate(fullname="HR 2", email="hr2@example.com", password="pass", company_name="M")
    )

    with pytest.raises(Exception) as excinfo:
        await hr_service.update_hr_profile(
            db_session,
            hr2.id,
            HRUpdate(email="hr1@example.com")
        )
    assert "already in use" in str(excinfo.value)


@pytest.mark.asyncio
async def test_hr_counts_and_stats(db_session):
    # Setup candidate
    cand = Candidate(
        fullname="Stat Candidate",
        email="stat_cand@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add(cand)

    # Setup Job and Application
    job = JobDescription(
        job_id="JOB-HR-001",
        job_title="Ceramic Specialist",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Ceramics production"
    )
    db_session.add(job)
    await db_session.flush()

    app1 = JobApplication(
        job_id=job.id,
        candidate_name="Stat Candidate",
        candidate_email="stat_cand@example.com",
        job_title="Ceramic Specialist",
        status="PENDING"
    )
    app2 = JobApplication(
        job_id=job.id,
        candidate_name="Stat Candidate 2",
        candidate_email="stat_cand2@example.com",
        job_title="Ceramic Specialist",
        status="ACCEPTED"
    )
    db_session.add_all([app1, app2])
    await db_session.commit()

    cand_count = await hr_service.get_total_candidates_count(db_session)
    assert cand_count >= 1

    stats = await hr_service.get_application_stats(db_session)
    assert stats["pending"] >= 1
    assert stats["accepted"] >= 1
    assert "reviewed" in stats
    assert "rejected" in stats

    trends = await hr_service.get_dashboard_trends(db_session)
    assert "weekly_trends" in trends
    assert len(trends["weekly_trends"]) == 7
    assert "department_distribution" in trends
    assert trends["total_applications"] >= 2


@pytest.mark.asyncio
async def test_hr_analytics_accuracy_10_seeded_applicants(db_session):
    """
    Seed 10 known applicants across 3 positions with known match scores and skills,
    and verify applicants per position, average score, and skills distribution match manual counts.
    """
    from sqlalchemy import select

    existing_rows = (await db_session.execute(select(JobApplication))).scalars().all()
    baseline_total = len(existing_rows)
    baseline_score_sum = sum(float(getattr(r, "match_score", 0.0) or 0.0) for r in existing_rows)

    j1 = JobDescription(
        job_id="JOB-ACC-1",
        job_title="Seeded Position A",
        department="Manufacturing",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Operate factory lines",
    )
    j2 = JobDescription(
        job_id="JOB-ACC-2",
        job_title="Seeded Position B",
        department="QA",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Inspect quality",
    )
    j3 = JobDescription(
        job_id="JOB-ACC-3",
        job_title="Seeded Position C",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Maintain machinery",
    )
    db_session.add_all([j1, j2, j3])
    await db_session.flush()

    seeded_specs = [
        # 5 applicants for Seeded Position A (scores: 80, 90, 70, 60, 50 -> avg 70.0)
        (j1.id, "Applicant 1", "a1@example.com", 80.0, ["SkillAlpha", "SkillGamma", "skillalpha"]),
        (j1.id, "Applicant 2", "a2@example.com", 90.0, ["SkillAlpha", "SkillGamma"]),
        (j1.id, "Applicant 3", "a3@example.com", 70.0, ["SkillAlpha", "SkillGamma"]),
        (j1.id, "Applicant 4", "a4@example.com", 60.0, ["SkillAlpha", "SkillBeta"]),
        (j1.id, "Applicant 5", "a5@example.com", 50.0, ["SkillAlpha"]),
        # 3 applicants for Seeded Position B (scores: 85, 75, 80 -> avg 80.0)
        (j2.id, "Applicant 6", "a6@example.com", 85.0, ["SkillBeta", "SkillAlpha"]),
        (j2.id, "Applicant 7", "a7@example.com", 75.0, ["SkillBeta"]),
        (j2.id, "Applicant 8", "a8@example.com", 80.0, ["SkillBeta"]),
        # 2 applicants for Seeded Position C (scores: 40, 60 -> avg 50.0)
        (j3.id, "Applicant 9", "a9@example.com", 40.0, ["SkillDelta", "SkillAlpha"]),
        (j3.id, "Applicant 10", "a10@example.com", 60.0, ["SkillDelta"]),
    ]

    for idx, (job_pk, name, email, score, skills) in enumerate(seeded_specs):
        db_session.add(
            JobApplication(
                job_id=job_pk,
                candidate_name=name,
                candidate_email=email,
                match_score=score,
                skills=skills,
                status="PENDING" if idx % 2 == 0 else "REVIEWED",
            )
        )
    await db_session.commit()

    stats = await hr_service.get_application_stats(db_session)
    trends = await hr_service.get_dashboard_trends(db_session)

    expected_total = baseline_total + 10
    seeded_score_sum = sum(item[3] for item in seeded_specs)  # 690.0
    expected_avg = round((baseline_score_sum + seeded_score_sum) / expected_total, 1)

    assert stats["total"] == expected_total
    assert trends["total_applications"] == expected_total
    assert stats["average_score"] == expected_avg
    assert trends["average_score"] == expected_avg

    pos_map = {item["label"]: item for item in trends["position_distribution"]}
    assert pos_map["Seeded Position A"]["value"] == 5
    assert pos_map["Seeded Position A"]["percentage"] == f"{round((5 / expected_total) * 100)}%"
    assert pos_map["Seeded Position A"]["avg_score"] == 70.0
    assert pos_map["Seeded Position B"]["value"] == 3
    assert pos_map["Seeded Position B"]["percentage"] == f"{round((3 / expected_total) * 100)}%"
    assert pos_map["Seeded Position B"]["avg_score"] == 80.0
    assert pos_map["Seeded Position C"]["value"] == 2
    assert pos_map["Seeded Position C"]["percentage"] == f"{round((2 / expected_total) * 100)}%"
    assert pos_map["Seeded Position C"]["avg_score"] == 50.0

    # Skills distribution counts unique applicants per skill accurately
    skills_map = {item["label"].lower(): item for item in trends["skills_distribution"]}
    assert skills_map["skillalpha"]["value"] == 7
    assert skills_map["skillalpha"]["percentage"] == f"{round((7 / expected_total) * 100)}%"
    assert skills_map["skillbeta"]["value"] == 4
    assert skills_map["skillbeta"]["percentage"] == f"{round((4 / expected_total) * 100)}%"
    assert skills_map["skillgamma"]["value"] == 3
    assert skills_map["skillgamma"]["percentage"] == f"{round((3 / expected_total) * 100)}%"
    assert skills_map["skilldelta"]["value"] == 2
    assert skills_map["skilldelta"]["percentage"] == f"{round((2 / expected_total) * 100)}%"
